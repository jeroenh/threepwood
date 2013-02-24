from threepwood.apps.collector.models import PeerRecord, PeerInfo, ASN
from django.core.exceptions import ObjectDoesNotExist
from celery import task
import bulkwhois.cymru
import pygeoip
import os
import gc

@task()
def add(x,y):
    return x+y

@task()
def fillPeerInfo():
    for p in queryset_iterator(PeerRecord.objects.filter(peerinfo__isnull=True)):
        convertedIP = convert6to4(p.ip)
        if ":" in convertedIP:
            iptype = 6
        else:
            iptype = 4
        try:
            newPeerInfo = PeerInfo.objects.get(ip=convertedIP)
        except ObjectDoesNotExist:
            newPeerInfo = PeerInfo(ip=convertedIP,iptype=iptype)
            newPeerInfo.save()
        p.peerinfo_id = newPeerInfo.id
        p.save()

# Taken from: http://djangosnippets.org/snippets/1949/
def queryset_iterator(queryset, chunksize=1000):
    '''''
    Iterate over a Django Queryset ordered by the primary key

    This method loads a maximum of chunksize (default: 1000) rows in it's
    memory at the same time while django normally would load all rows in it's
    memory. Using the iterator() method only causes it to not preload all the
    classes.

    Note that the implementation of the iterator does not support ordered query sets.
    '''
    pk = 0
    last_pk = queryset.order_by('-pk')[0].pk
    queryset = queryset.order_by('pk')
    while pk < last_pk:
        for row in queryset.filter(pk__gt=pk)[:chunksize]:
            pk = row.pk
            yield row
        gc.collect()
        
def convert6to4(ip):
    if not ":" in ip:
        return ip
    if not ip.startswith("2002:"):
        return ip
    s = ip.split(":")
    first,last = s[1:3]
    if len(first) < 4:
        first = "0"+first
    if len(last) < 4:
        last = "0"+last
    return "%s.%s.%s.%s" % (int(first[0:2],16),int(first[2:4],16),int(last[0:2],16),int(last[2:4],16))

@task()
def massLookup():
    localdir = os.path.dirname(os.path.realpath(__file__))
    GEOIP = pygeoip.GeoIP(os.path.join(localdir,'GeoIP.dat'))
    peers = PeerInfo.objects.filter(asnumber__isnull=True, iptype=4)
    ippeers = {}
    for p in peers:
        ippeers[str(p.ip)] = p
    if ippeers:
        cymru = bulkwhois.cymru.BulkWhoisCymru()
        cymruresult = cymru.lookup_ips(ippeers.keys())
        for ip,peer in ippeers.iteritems():
            try:
                country = GEOIP.country_code_by_name(ip)
            except socket.gaierror:
                country = cymruresult[ip]['cc']
            peer.country = country
            asn = ASN(number=cymruresult[ip]['asn'], name=cymruresult[ip]['as_name'])
            asn.save()
            peer.asnumber = asn
            peer.save()