from threepwood.apps.collector.models import PeerRecord, PeerInfo, ASN
from django.core.exceptions import ObjectDoesNotExist
from celery import task
import bulkwhois.cymru
import pygeoip
import os

@task()
def add(x,y):
    return x+y

@task()
def fillPeerInfo():
    newPeers = PeerRecord.objects.filter(peerinfo__isnull=True)
    for p in newPeers:
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