from threepwood.apps.collector.models import PeerRecord, PeerInfo, ASN
from celery import task
import bulkwhois.cymru

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
        newPeerInfo = PeerInfo(ip=convertedIP,iptype=iptype)
        newPeerInfo.save()


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

# @task()
# def massLookup():
#     ips = threepwod.apps.collector.models.all()
#     cymru = bulkwhois.lookup_ips(ips)
#     for ip in ips:
#         try:
#             country = GEOIP.country_code_by_name(ip)
#             result = (cymru[ip]['asn'],country, cymru[ip]['as_name'], ip)
#         except socket.gaierror:
#             result = (cymru[ip]['asn'],cymru[ip]['cc'], cymru[ip]['as_name'], ip)
#         return result
