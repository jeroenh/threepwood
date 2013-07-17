from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse_lazy
from django.views.generic import RedirectView
from threepwood.apps.collector.views import ClientList, ClientUpdate, TorrentList, TorrentCreate, ClientCreate, TorrentDetail, TorrentUpdate, ClientDelete, TorrentDelete, ClientDetail

urlpatterns = patterns('threepwood.apps.collector.views',
    url(r'^$', RedirectView.as_view(url=reverse_lazy("collector_client_list")), name="collector"),

    #torrent CRUD
    url(r'^torrent/$',RedirectView.as_view(url=reverse_lazy("collector_torrent_list")), name="collector_torrent"),
    url(r'^torrent/list/$', TorrentList.as_view(), name='collector_torrent_list'),
    url(r'^torrent/create/$', TorrentCreate.as_view(), name='collector_torrent_add'),
    url(r'^torrent/update/(?P<pk>\d+)$', TorrentUpdate.as_view(), name='collector_torrent_update'),
    url(r'^torrent/detail/(?P<pk>\d+)$', TorrentDetail.as_view(), name='collector_torrent_detail'),
    url(r'^torrent/delete/(?P<pk>\d+)$', TorrentDelete.as_view(), name='collector_torrent_delete'),

    url(r'^torrent/(?P<pk>\d+)/assign_client/$', 'assign_client',  name='collector_torrent_assign_client'),
    url(r'^torrent/(?P<pk>\d+)/remove_client/$', 'remove_client',  name='collector_torrent_remove_client'),

    #client CRUD
    url(r'^client/$',RedirectView.as_view(url=reverse_lazy("collector_client_list")), name="collector_client"),
    url(r'^client/list$', ClientList.as_view(), name='collector_client_list'),
    url(r'^client/create$', ClientCreate.as_view(), name='collector_client_create'),
    url(r'^client/update/(?P<pk>\d+)$', ClientUpdate.as_view(), name='collector_client_update'),
    url(r'^client/delete/(?P<pk>\d+)$', ClientDelete.as_view(), name='collector_client_delete'),
    url(r'^client/detail/(?P<pk>\d+)$', ClientDetail.as_view(), name='collector_client_detail'),
    url(r'^client/(?P<pk>\d+)/assign_torrents/$', 'assign_torrents',  name='collector_client_assign_torrents'),



    url(r'^post_peers/$', 'post_peers',  name='collector_post_peers'),
    url(r'^post_torrents/$', 'post_torrents',  name='collector_post_torrents'),
    url(r'^get_torrents/$', 'get_torrents',  name='collector_get_torrents'),

)