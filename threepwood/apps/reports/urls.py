__author__ = 'cdumitru'

from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse_lazy
from django.views.generic import RedirectView
from threepwood.apps.reports.views import *

urlpatterns = patterns('',
                       url(r'^$', RedirectView.as_view(url=reverse_lazy("reports_torrent_list")), name="reports"),
                       url(r'^client/(?P<pk>\d+)/$', ClientReport.as_view(), name='reports_client_report'),
                       url(r'^client/detail/(?P<pk>\d+)$', ClientReportDetail.as_view(), name='reports_client_detail'),
                       url(r'^client/list/$', ClientReportList.as_view(), name='reports_client_list'),

                       url(r'^asn/detail/(?P<pk>\d+)$', ASNReportDetail.as_view(), name='reports_asn_detail'),
                       url(r'^asn/list/$', ASNReportList.as_view(), name='reports_asn_list'),

                       url(r'^torrent/(?P<pk>\d+)/$', TorrentReport.as_view(), name='reports_torrent_report'),
                       url(r'^torrent/detail/(?P<pk>\d+)$', TorrentReportDetail.as_view(),
                           name='reports_torrent_detail'),
                       url(r'^torrent/detail/(?P<pk>\d+)/(?P<page>\d+)/$', TorrentReportDetail.as_view(),
                           name='reports_torrent_detail_paginate'),
                       url(r'^torrent/list/$', TorrentReportList.as_view(), name='reports_torrent_list'),


)
