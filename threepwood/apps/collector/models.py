from datetime import timedelta
import hashlib
import uuid
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.simplejson import loads
from django.utils.timezone import now
from django.core.exceptions import ObjectDoesNotExist


def _generate_key():
    """
    @return: generates uuid
    """
    sha = hashlib.sha1()
    sha.update(uuid.uuid4().bytes)
    return sha.hexdigest()


class Client(models.Model):
    key = models.CharField(max_length=40, editable=False, db_index=True)
    description = models.CharField(max_length=1024, blank=True, null=True)
    active = models.BooleanField(default=True)


    def __unicode__(self):
        return u"{0}".format(self.key)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = _generate_key()

        super(Client, self).save(*args, **kwargs)

    def get_active_session(self, torrent):
        sessions = self.session_set.filter(torrent=torrent).order_by("-date_created")
        if sessions.count() > 0 and now() - sessions[0].date_created < timedelta(seconds=Session.LIFETIME):
            return sessions[0]
        else:
            return None

    def last_session(self, torrent):
        sessions = torrent.session_set.all().order_by("-date_created")
        if sessions.count() > 0:
            return sessions[0]
        else:
            return None

    def last_seen(self):
        sessions = self.session_set.all().order_by('-date_created')
        if sessions.count() > 0:
            return sessions[0].date_created
        else:
            return None

    def last_ip(self):
        sessions = self.session_set.all().order_by('-date_created')
        if len(sessions) > 0:
            return sessions[0].ip
        else:
            return None


class Torrent(models.Model):
    info_hash = models.CharField(max_length=40, db_index=True)
    magnet = models.CharField(max_length=2048)
    clients = models.ManyToManyField(Client, null=True, blank=True)
    description = models.CharField(max_length=256)
    active = models.BooleanField(default=True)
    date_added = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return u"{0} | {1} | {2}".format(self.info_hash, self.active, self.date_added)

    def save(self, *args, **kwargs):
        if not self.info_hash:
            self.info_hash = self.magnet.split("&")[0].split(':')[-1]

        super(Torrent, self).save(*args, **kwargs)

    def distinct_peers(self):

        #TODO optimize this
        return PeerRecord.objects.filter(session__in=self.session_set.all()).values_list('ip',
                                                                                         flat=True).distinct().count()

    def dutch_peers(self):
        dutch_asnumbers = [9143, 6830, 8737, 5615, 3265]
        dutch_peers = PeerRecord.objects.filter(session__in=self.session_set.all(), peerinfo__country="NL").distinct()

        dutch_peers_count = dutch_peers.count()
        result = {"total": dutch_peers_count}
        for asn in dutch_asnumbers:
            result[ASN.objects.get(asn).name] = dutch_peers.filter(
                peerinfo__asnumber__number=asn).count() / dutch_peers_count
            try:
                asname = ASN.objects.get(number=asn).name
            except ObjectDoesNotExist:
                asname = str(asn)
            result[asname] = (dutch_peers.filter(peerinfo__asnumber__number=asn).count() / float(
                dutch_peers_count)) * 100
        return result

    @property
    def sorted_session_set(self):
        return self.session_set.order_by('-date_created')


class TorrentMetadata(models.Model):
    name = models.CharField(max_length=256, blank=True, null=True)
    comment = models.CharField(max_length=1500, blank=True, null=True)
    creator = models.CharField(max_length=300, blank=True, null=True)
    files = models.TextField(blank=True, null=True)
    size = models.BigIntegerField(default=0)
    torrent = models.OneToOneField(Torrent)

    def files_as_list(self):
        print self.files
        if self.files:
            return loads(self.files)
        else:
            return None


@receiver(post_save, sender=Torrent)
def create_metadata(sender, instance, created, **kwargs):
    if created:
        TorrentMetadata.objects.create(torrent=instance)


class Session(models.Model):
    LIFETIME = 3600

    client = models.ForeignKey(Client)
    ip = models.GenericIPAddressField()
    key = models.CharField(max_length=40, editable=False, db_index=True)
    date_created = models.DateTimeField(auto_now_add=True)
    torrent = models.ForeignKey(Torrent, db_index=True)
    version = models.CharField(max_length=32)


    def is_active(self):
        return self.torrent.active and (self.client in self.torrent.clients.all())


    def save(self, *args, **kwargs):
        if not self.key:
            self.key = _generate_key()
        super(Session, self).save(*args, **kwargs)

    def get_size(self):
        return self.peerrecord_set.values_list('ip', flat=True).distinct().count()

    def __unicode__(self):
        return u"{0} {1} {2}".format(self.client, self.torrent.torrentmetadata.name, self.date_created)


class ASN(models.Model):
    number = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)

    def __unicode__(self):
        if self.name:
            return self.name
        else:
            return str(self.number)


class PeerInfo(models.Model):
    IP_TYPE = ((4, u"IPv4"), (6, u"IPv6"))
    ip = models.GenericIPAddressField(db_index=True)
    asnumber = models.ForeignKey("ASN", null=True, blank=True, on_delete=models.SET_NULL)
    iptype = models.IntegerField(choices=IP_TYPE)
    country = models.CharField(max_length=255, default="", null=True, db_index=True)

    def __unicode__(self):
        return self.ip


def convert6to4(ip):
    if not ":" in ip:
        return ip
    if not ip.startswith("2002:"):
        return ip
    s = ip.split(":")
    first, last = s[1:3]
    if len(first) < 4:
        first = "0" + first
    if len(last) < 4:
        last = "0" + last
    return "%s.%s.%s.%s" % (int(first[0:2], 16), int(first[2:4], 16), int(last[0:2], 16), int(last[2:4], 16))


class PeerRecord(models.Model):
    ip = models.GenericIPAddressField()
    date_added = models.DateTimeField(auto_now_add=True)
    session = models.ForeignKey(Session)
    peerinfo = models.ForeignKey(PeerInfo, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.peerinfo:
            convertedIP = convert6to4(self.ip)
            if ":" in convertedIP:
                iptype = 6
            else:
                iptype = 4
            try:
                self.peerinfo = PeerInfo.objects.get_or_create(ip=convertedIP, defaults={'iptype': iptype})[0]
            except:
                self.peerinfo = None
        super(PeerRecord, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.ip


class RawPeerRecord(models.Model):
    #this is used to store raw data until i figure out what to do on delete cascades
    ip = models.GenericIPAddressField()
    date_added = models.DateTimeField(auto_now_add=True)
    info_hash = models.CharField(max_length=40)
    client_ip = models.GenericIPAddressField()
    client_key = models.CharField(max_length=40)
    session_key = models.CharField(max_length=40)

