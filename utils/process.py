__author__ = 'cdumitru'

import os
import pprint
from collections import defaultdict

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

    #holds numeric values
    torrent_stats_raw = defaultdict(list)
    torrent_stats_percentages = defaultdict(list)


    #a list of country codes
    countries = sorted(PeerInfo.objects.values_list('country', flat=True).distinct())

    for t in Torrent.objects.all()[6:]:
        #for each torrent
        for country_code in countries:
            #for each country
            #add to the torrent stats
            #       select all the peer records for this torrent
            #       but only from the current country
            #       extract the ip
            #       filter out duplicates and count
            #   append it to the torrent stats
            #order in which we walk the countries array is important!
            torrent_stats_raw[t].append(PeerRecord.objects.filter(session__torrent__id=t.id,
                                                                      peerinfo__country=country_code)
            .values_list('ip', flat=True).distinct().count())

        #count total ips for this torrent
        total_ip_count = PeerRecord.objects.filter(session__torrent__id=t.id).values_list('ip', flat=True).distinct().count()

        #compute percentage
        for country_value in torrent_stats_raw[t]:
            if total_ip_count:
                torrent_stats_percentages[t].append(float(country_value) / total_ip_count * 100)
            else:
                #some torrents might have no data
                torrent_stats_percentages[t].append(0)

        #append a last column with totals for the raw values
        torrent_stats_raw[t].append(total_ip_count)


    f = open("countries-percentage.txt", 'w')

    f.write("# each column is a country , each line is a torrent . values are percentage of ips from country for that torrent\n")

    line = "torrent\t\t" + " ".join(countries)
    f.write("%s\n" % line)

    for t in Torrent.objects.all()[6:]:
        line = t.description.strip().replace(' ', '_') + "\t\t" + " ".join(str(s) for s in torrent_stats_percentages[t])
        f.write("%s\n" % line)
    f.close()



def get_torrent_csv_out():
    country_code = 'NL'
    version='1204'
    totals = defaultdict(list)
    country_as = PeerInfo.objects.filter(country=country_code).values_list('asnumber', flat=True).distinct()

    clean_asn =[]
    done_clean_asn = False

    for t in Torrent.objects.all()[6:]:
        #a list of all the ASs from this country
        torrent_name = t.description.strip().replace(' ', '_')

        #all the ips for this country
        total_ip_country = PeerRecord.objects.filter(session__torrent__id=t.id,
                                                     peerinfo__country=country_code, session__version=version).values_list('ip',
                                                                                                 flat=True).distinct().count()
        total_ip_global = PeerRecord.objects.filter(session__torrent__id=t.id, session__version=version).values_list('ip',
                                                                                                 flat=True).distinct().count()


        #count ips for each as
        total_kpn = 0
        for as_number in country_as:
            if as_number in [5615, 49562, 286, 1134, 12469, 8737]:
                total_kpn += PeerRecord.objects.filter(session__torrent__id=t.id,
                                                       peerinfo__asnumber=as_number, session__version=version).values_list('ip',
                                                                                                 flat=True).distinct().count()
            else:
                totals[torrent_name].append(PeerRecord.objects.filter(session__torrent__id=t.id, peerinfo__asnumber=as_number, session__version=version).values_list('ip',
                                                                                           flat=True).distinct().count())
                if not done_clean_asn:
                    clean_asn.append(as_number)

        if not done_clean_asn:
            clean_asn.append(286)
            done_clean_asn = True
        totals[torrent_name].append(total_kpn)
        totals[torrent_name].append(total_ip_country)
        totals[torrent_name].append(total_ip_global)

    f = open("dutch-totals-" + version +".csv", 'w')
    as_names = []
    for s in clean_asn:
        as_names.append(ASN.objects.get(number=s).name.split()[0])

    line = "torrent," + ",".join(as_names) + ',dutch_total,global_total\n'
    f.write(line)
    for t in totals.keys():
        if totals[t][-1]:
            line = t + "," + ",".join(str(s) for s in totals[t]) + "\n"
            f.write(line)
    f.close()






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

    # get_country_stats_new()

    get_torrent_csv_out()