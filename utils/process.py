__author__ = 'cdumitru'

import os
import pprint
from collections import defaultdict
import numpy

if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "threepwood.local_settings")

from django.db.models import Count
from threepwood.apps.collector.models import *


def get_country_counts():
    #TODO matrix style

    tcountries = defaultdict(list)
    all_countries = PeerInfo.objects.values_list('country', flat=True).distinct()
    for t in Torrent.objects.all()[6:]:

        countries = defaultdict(int)

        pi = PeerInfo.objects.filter(peerrecord__session__torrent__id=t.id).distinct().annotate(
            countrycount=Count('country')).order_by('-countrycount')
        for p in pi:
            countries[p.country] = p.countrycount
        for k in countries:
            tcountries[k].append(countries[k])
    for k in tcountries:
        tcountries[k] += ([0] * (len(tcountries["NL"]) - len(tcountries[k])))

    #TODO
    # IN: matrix(torrent, country)
    # OUT: Totals (torrent)
    #      Percentage of country per torrent
    #      Mean + deviation for each country percentage
    #   https://stat.ethz.ch/pipermail/r-help/2006-June/108227.html
    # http://data.princeton.edu/R/readingData.html


    return tcountries


def get_country_stats_new():
    tcountries = defaultdict(list)

    #a list of country codes
    countries = PeerInfo.objects.values_list('country', flat=True).distinct()
    total_ips_torrent = []

    for t in Torrent.objects.all()[6:]:
        #for each torrent
        for country_code in countries:
            #for each country
            #add to the torrent stats
            #       select all the peer records for this torrent
            #       but only from the current country
            #       extract the ip
            #       filter out duplicates and count
            tcountries[country_code].append(PeerRecord.objects.filter(session__torrent__id=t.id,
                                                                      peerinfo__country=country_code)
            .values_list('ip', flat=True).distinct().count())

        #count total ips for this torrent
        total_ips_torrent.append(
            PeerRecord.objects.filter(session__torrent__id=t.id).values_list('ip', flat=True).distinct().count())

    #compute percentage of country per torrent

    pcountries = defaultdict(list)

    for country_code in tcountries.keys():

        #the index is used to retreive the totals for that torrent from the total_ips_torrent array
        # the asumption here is that the ip values were added in the same order for both the country list and the
        # totals list so similar position
        for value, idx in enumerate(tcountries[country_code]):
            pcountries[country_code] = float(value) / total_ips_torrent[idx] * 100

    pp = pprint.PrettyPrinter(indent=4)

    pp.pprint(pcountries)


def get_torrent_stats(torrent, countries=None, asns=None):
    """
    :param torrent: @Torrent
    :return:
    """
    results = {}
    kpn_as = [5615, 49562, 286, 1134, 12469]

    #default behavior is to get stats for all countries
    if not countries:
        countries = PeerInfo.objects.values_list('country', flat=True).distinct()

    total_ip = PeerRecord.objects.filter(session__torrent__id=torrent.id).values_list('ip',
                                                                                      flat=True).distinct().count()

    for country_code in countries:

        others = {'total_unique_ips': 0, 'percent_of_country': 0, 'percent_of_total': 0, 'name': 'others',
                  'country': country_code}
        kpn_stats = {'total_unique_ips': 0, 'percent_of_country': 0, 'percent_of_total': 0,
                     'name': 'PT Koninklijke KPN N.V.', 'country': country_code, 'asn': [5615, 49562, 286, 1134, 12469]}

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
    # asns = [31615, 9143, 3265, 6830, 31615, 5615, 49562, 286, 1134, 12469, 13127]
    #
    # stats = get_country_counts()
    # f = open("new-countries.txt", 'w')
    # for country in stats.keys():
    #     f.write("%s: %s\n" % (country, stats[country]))
    # f.close()
    # print "-=" * 40
    # for t in Torrent.objects.all()[6:]:
    #     #stats = get_torrent_stats(t,countries=['NL'], asns=asns)
    #     result = {'name': t.torrentmetadata.name, 'stats': stats}
    #     #pprint.pprint(result)
    #     sum = 0
    #     sorted_stats = sorted(result['stats']['NL'], key=lambda k: k['name'])
    #     #print(sorted_stats)
    #     for k in sorted_stats:
    #         print "{0:2.2f}".format(k['percent_of_country']),
    #     print "\n"
    # for k in sorted_stats:
    #     print "\"{0}\"".format(k['name']),

    get_country_stats_new()
