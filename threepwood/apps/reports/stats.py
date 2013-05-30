__author__ = 'cdumitru'

import os


if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "threepwood.local_settings")

from threepwood.apps.collector.models import *


def get_torrent_stats():
    #get only dutch torrents
    dutch_as = PeerInfo.objects.filter(country='NL').values_list('asnumber', flat=True).distinct()



    for t in Torrent.objects.all()[6:]:
        results = {}
        print "=======\nTorrent:{0}\n=======".format(t.torrentmetadata.name)
        total_ip = PeerRecord.objects.filter(session__torrent__id=t.id).values_list('ip', flat=True).distinct().count()
        total_dutch = PeerRecord.objects.filter(session__torrent__id=t.id, peerinfo__country="NL").values_list('ip',
                                                                                                               flat=True).distinct().count()
        for as_number in dutch_as:
            total_as = PeerRecord.objects.filter(session__torrent__id=t.id, peerinfo__country="NL",
                                                 peerinfo__asnumber=as_number).values_list('ip',
                                                                                           flat=True).distinct().count()
            results[as_number] = total_as
        sort = sorted(results, key=lambda as_number: results[as_number], reverse=True)
        print "Total IPs:{0} Total DutchIPs:{1}\nAS_NAME:AS_NUMBER, UNIQUE DUTCH, PERCENT of DUTCH, PERCENT of TOTAL\n=================".format(
            total_ip, total_dutch)
        for asn in sort:
            value = results[asn]
            percent_dutch = float(results[asn]) / total_dutch * 100.0
            percent_total = float(results[asn]) / total_ip * 100.0
            as_name = ASN.objects.get(number=asn).name
            #just print relevant results
            if percent_dutch > 1:
                print "{0}:AS{1}:{2},{3:2.2f},{4:2.2f}".format(as_name, asn, value, percent_dutch, percent_total)


get_torrent_stats()