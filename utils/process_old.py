__author__ = 'cdumitru'

import os
import pprint
from collections import defaultdict

if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "threepwood.local_settings")

from django.db.models import Count
from threepwood.apps.collector.models import *


def get_country_counts(version="1204"):
    tcountries = defaultdict(list)
    for t in Torrent.objects.all()[6:]:
        countries = defaultdict(int)
        pi = PeerInfo.objects.filter(peerrecord__session__torrent__id=t.id,
                                     peerrecord__session__version=version).distinct().annotate(
            countrycount=Count('country')).order_by('-countrycount')
        for p in pi:
            countries[p.country] += p.countrycount
        for k in countries:
            tcountries[k].append(countries[k])
    for k in tcountries:
        tcountries[k] += ([0] * (len(tcountries["NL"]) - len(tcountries[k])))

    return tcountries


def get_torrent_stats(torrent, version="1205", countries=None, asns=None):
    """
    :param torrent: @Torrent
    :return:
    """
    results = {}
    #    kpn_as = [5615, 49562, 286, 1134, 12469]
    kpn_as = [5615, 49562, 286, ]

    #default behavior is to get stats for all countries
    if not countries:
        countries = PeerInfo.objects.values_list('country', flat=True).distinct()

    total_ip = PeerRecord.objects.filter(session__version=version, session__torrent__id=torrent.id).values_list('ip',
                                                                                                                flat=True).distinct().count()
    if not total_ip:
        return

    for country_code in countries:

        others = {'total_unique_ips': 0, 'percent_of_country': 0, 'percent_of_total': 0, 'name': 'others',
                  'country': country_code}
        #   	kpn_stats = {'total_unique_ips':0,'percent_of_country':0,'percent_of_total':0, 'name':'PT Koninklijke KPN N.V.', 'country':country_code, 'asn':[5615, 49562, 286, 1134, 12469]}
        kpn_stats = {'total_unique_ips': 0, 'percent_of_country': 0, 'percent_of_total': 0,
                     'name': 'PT Koninklijke KPN N.V.', 'country': country_code, 'asn': [5615, 49562, 286]}

        #gets all the unique ips for this torrent that come from this country
        total_ip_country = PeerRecord.objects.filter(session__torrent__id=torrent.id,
                                                     peerinfo__country=country_code).values_list('ip',
                                                                                                 flat=True).distinct().count()

        #all the AS' that come from this country
        if not asns:
            country_as = PeerInfo.objects.filter(country=country_code).values_list('asnumber', flat=True).distinct()
        else:
            country_as = asns

        result = {}
        #count all the ips belonging to an as
        for as_number in country_as:
            total_as = PeerRecord.objects.filter(session__torrent__id=torrent.id, peerinfo__country=country_code,
                                                 peerinfo__asnumber=as_number).values_list('ip',
                                                                                           flat=True).distinct().count()
            result[as_number] = total_as

        #sort the dict by ip count
        sorted_as_by_ips = sorted(result, key=lambda as_number: result[as_number], reverse=True)

        results[country_code] = []
        for asn in sorted_as_by_ips:
            stats = {}
            stats['total_unique_ips'] = result[asn]
            stats['percent_of_country'] = float(result[asn]) / total_ip_country * 100.0
            stats['percent_of_total'] = float(result[asn]) / total_ip * 100.0
            stats['name'] = ASN.objects.get(number=asn).name
            stats['asn'] = asn
            stats['country'] = country_code
            if asn in kpn_as:
                kpn_stats['total_unique_ips'] += stats['total_unique_ips']
                kpn_stats['percent_of_country'] += stats['percent_of_country']
                kpn_stats['percent_of_total'] += stats['percent_of_total']
            elif stats['percent_of_country'] > 1 or asn in asns:
                results[country_code].append(stats)
            else:
                others['total_unique_ips'] += stats['total_unique_ips']
                others['percent_of_country'] += stats['percent_of_country']
                others['percent_of_total'] += stats['percent_of_total']

        results[country_code].append(kpn_stats)
        if others['percent_of_country'] > 0:
            results[country_code].append(others)

    return results


if __name__ == "__main__":

#global tele2 as is AS1257, NL is 13127
#	asns = [31615, 9143, 3265, 6830, 31615, 5615, 49562, 286, 1134, 12469, 13127]
    asns = [31615, 9143, 3265, 6830, 31615, 5615, 49562, 286, 13127]
    stats = get_country_counts("1204")
    f = open("1204-countries.txt", 'w')
    for country in stats.keys():
        f.write("%s: %s\n" % (country, stats[country]))
    f.close()
    for t in Torrent.objects.all()[6:]:
        stats = get_torrent_stats(t, countries=['NL'], asns=asns)
        if stats:
            result = {'name': t.torrentmetadata.name, 'stats': stats}
            #pprint.pprint(result)
            sorted_stats = sorted(result['stats']['NL'], key=lambda k: k['name'])
            #print(sorted_stats)
            for k in sorted_stats:
                print "{0:2.2f},".format(k['percent_of_country']),
            print ""
        sum = 0
    for k in sorted_stats:
        print "\"{0}\",".format(k['name']),

	
