import hashlib
import uuid
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.simplejson import loads

def _generate_key():
    """
    @return: generates uuid
    """
    sha = hashlib.sha1()
    sha.update(uuid.uuid4().bytes)
    return sha.hexdigest()


class Client(models.Model):

    key = models.CharField(max_length=40, editable=False)
    description = models.CharField(max_length=1024, blank=True, null=True)
    active = models.BooleanField(default=True)

    def __unicode__(self):
        return u"{0}".format(self.key)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = _generate_key()

        super(Client, self).save(*args, **kwargs)

    def last_session(self, hash):
        sessions = [session for session in self.session_set.filter(torrent__info_hash=hash).order_by('-date_created')]
        if len(sessions) > 0:
            return sessions[0]
        else:
            return None

    def last_seen(self):
        sessions = self.session_set.all().order_by('-date_created')
        if len(sessions)>0:
            return sessions[0].date_created
        else:
            return None

    def last_ip(self):
        sessions = self.session_set.all().order_by('-date_created')
        if len(sessions)>0:
            return sessions[0].ip
        else:
            return None

class Torrent(models.Model):
    info_hash = models.CharField(max_length=40)
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

class TorrentMetadata(models.Model):
    name = models.CharField(max_length=256, blank=True, null=True)
    comment = models.CharField(max_length=1500, blank=True,  null=True)
    creator = models.CharField(max_length=300, blank=True,  null=True)
    files = models.CharField(max_length=65535, blank=True,  null=True)
    size = models.IntegerField(default=0)
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

    LIFETIME = 6000

    client = models.ForeignKey(Client)
    ip = models.GenericIPAddressField()
    key = models.CharField(max_length=40, editable=False)
    date_created = models.DateTimeField(auto_now_add=True)
    torrent = models.ForeignKey(Torrent)


    def is_active(self):
        return self.torrent.active and (self.client in self.torrent.clients.all())


    def save(self, *args, **kwargs):
        if not self.key:
            self.key = _generate_key()
        super(Session, self).save(*args, **kwargs)

    def __unicode__(self):
        return u"{0} {1} {2}".format(self.client, self.torrent.torrentmetadata.name, self.date_created)

class PeerRecord(models.Model):
    ip = models.GenericIPAddressField()
    date_added = models.DateTimeField(auto_now_add=True)
    session = models.ForeignKey(Session)

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
