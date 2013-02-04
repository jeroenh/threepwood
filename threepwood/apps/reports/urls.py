from threepwood.apps.reports.views import ClientReport, TorrentReport

__author__ = 'cdumitru'


from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse_lazy
from django.views.generic import RedirectView

urlpatterns = patterns('',
#    url(r'^$', RedirectView.as_view(url=reverse_lazy("reports_dashboard")), name="reports"),

    url(r'^client/(?P<pk>\d+)/$',ClientReport.as_view(), name='reports_client_report'),
    url(r'^torrent/(?P<pk>\d+)/$',TorrentReport.as_view(), name='reports_torrent_report'),
)
