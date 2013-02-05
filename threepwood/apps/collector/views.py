from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.utils.simplejson import dumps, loads
from django.views.decorators.csrf import csrf_exempt
from threepwood.apps.collector.forms import TorrentForm, ClientCreateForm, ClientUpdateForm, TorrentAddClientForm, ConfirmDelete, TorrentRemoveClientForm, TorrentUpdateForm, ClientAddTorrentForm
from threepwood.apps.collector.models import Client, Torrent, PeerRecord, Session, RawPeerRecord
from threepwood.settings.base import MAX_PEERS_THRESHOLD, REPORT_INTERVAL, CHECK_FOR_UPDATES_INTERVAL

__author__ = 'cdumitru'

from django import http
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView

class ClientList(ListView):
    queryset = Client.objects.all()
    context_object_name = "client_list"

class ClientCreate(CreateView):
    model = Client
    form_class = ClientCreateForm
    success_url=reverse_lazy('collector_client_list')

class ClientUpdate(UpdateView):
    model = Client
    form_class = ClientUpdateForm

    def get_success_url(self):
        return reverse_lazy('collector_client_detail', kwargs={'pk':self.kwargs['pk']})

class ClientDetail(DetailView):
    model = Client
    context_object_name = 'client'


class TorrentList(ListView):
    queryset = Torrent.objects.all()
    context_object_name = "torrent_list"

class ClientDelete(DeleteView):
    model = Client
    success_url = reverse_lazy('collector_client_list')
    def get_context_data(self, **kwargs):
        context = super(DeleteView, self).get_context_data(**kwargs)
        context['form'] = ConfirmDelete()
        return context


class TorrentCreate(CreateView):
    model = Torrent
    form_class = TorrentForm
    success_url=reverse_lazy('collector_torrent_list')


class TorrentUpdate(UpdateView):
    model = Torrent
    form_class = TorrentUpdateForm

    def get_success_url(self):
        return reverse_lazy('collector_torrent_detail', kwargs={'pk': self.kwargs['pk']})

class TorrentDetail(DetailView):
    model = Torrent
    context_object_name = "torrent"


class TorrentDelete(DeleteView):
    model = Torrent
    success_url = reverse_lazy('collector_torrent_list')

    def get_context_data(self, **kwargs):
        context = super(DeleteView, self).get_context_data(**kwargs)
        context['form'] = ConfirmDelete()
        return context

def get_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@csrf_exempt
#this view is used by lechuck to report pirates/peers. no need for csrf prottection
def post_peers(request):
    res = {'success':False, 'client_active':False, 'session_active':False}
    ip = get_ip(request)

    if request.method == 'POST':

        data =  loads(request.body)

        if not 'session_key' in data.keys():
            res['message'] = "Missing session key"
            return http.HttpResponse(content=dumps(res), mimetype='application/json')

        try:
            session = Session.objects.get(key=data['session_key'])

        except ObjectDoesNotExist:
            res['message'] = "Invalid session"
            return http.HttpResponse(content=dumps(res), mimetype='application/json')


        if 'metadata' in data.keys():
            torrent_metadata = session.torrent.torrentmetadata
            #assuming that if the name is fresh then we need to update the metadata
            if torrent_metadata.name != data['metadata']['name']:
                cleaned_metadata = data['metadata']

                #store the file list as a JSON encoded field. yay!
                cleaned_metadata['files'] =  dumps(data['metadata']['files'])
                for meta in cleaned_metadata.keys():
                    setattr(torrent_metadata, meta, cleaned_metadata[meta])
                torrent_metadata.save()

        #save data coming only from active clients
        if 'peers' in data.keys() and session.client.active:
            for peer in data['peers']:
                record = {'ip':peer, 'session':session}
                PeerRecord(**record).save()

                #FIXME this should be temporary until cascading deletes are well understood
                record  = {
                    'ip':peer,
                    'info_hash':session.torrent.info_hash ,
                    'client_ip':ip,
                    'client_key':session.client.key,
                    'session_key':session.key
                }
                RawPeerRecord(**record).save()

        res['success'] = True
        res['client_active'] = session.client.active
        res['session_active'] = session.is_active()

        #this will create a new session every max_liftime seconds
        #this creates some stress on the db. maybe the client should get a new session only via GET ?
        if session.client.get_active_session(session.torrent) != session:
            session = Session(client=session.client, ip=ip, torrent = session.torrent, version = session.version)
            session.save()

        res['session_key'] = session.key

    return http.HttpResponse(content=dumps(res), mimetype='application/json')


def get_sessions_and_torrents_for_client(client, ip, version):
    result = []

    torrents  = client.torrent_set.filter(active=True)
    for t in torrents:
        session = client.get_active_session(t)
        #if the last session expired create a new one
        if not session:
            session = Session(client=client, ip=ip, torrent=t, version=version)
            session.save()
        result.append({'session_key': session.key,
                       'info_hash': t.info_hash,
                       'magnet':t.magnet,
        })

    return result


def get_torrents(request):

    #TODO get magic values from db
    res = {'success':'false',
           'torrents':[],
            'settings':{
            'MAX_PEERS_THRESHOLD': MAX_PEERS_THRESHOLD,
            'REPORT_INTERVAL': REPORT_INTERVAL,
            'CHECK_FOR_UPDATES_INTERVAL': CHECK_FOR_UPDATES_INTERVAL
            }
    }
    ip = get_ip(request)
    if request.method == "GET":
        key = request.GET.get('key',"")
        version = request.GET.get('version',"")
        try:
            client = Client.objects.get(key=key)

            if not client.active:
                res['message'] = "Client not active"
                return http.HttpResponse(content=dumps(res), mimetype='application/json')

            res['torrents'] = get_sessions_and_torrents_for_client(client, ip, version)
            res['success'] = 'true'
        except ObjectDoesNotExist:
            res['message'] = "Unknown client"
            return http.HttpResponse(content=dumps(res), mimetype='application/json')

    return http.HttpResponse(content=dumps(res), mimetype='application/json')



def assign_client(request, pk):

    torrent = get_object_or_404(Torrent, pk=pk)

    form = TorrentAddClientForm(torrent=torrent)

    if request.method == 'POST':
        form = TorrentAddClientForm(request.POST, torrent=torrent)
        if form.is_valid():
            for client in form.cleaned_data['clients']:
                torrent.clients.add(client)

            return HttpResponseRedirect(reverse_lazy('collector_torrent_detail', kwargs={'pk': pk},))

    return render_to_response('collector/torrent_assign_client.html', {'form': form}, context_instance=RequestContext(request) )


def assign_torrents(request, pk):
    client = get_object_or_404(Client, pk=pk)
    form = ClientAddTorrentForm(client=client)

    if request.method == 'POST':
        form = ClientAddTorrentForm(request.POST,client=client)
        if form.is_valid():
            for torrent in form.cleaned_data['torrents']:
                client.torrent_set.add(torrent)

            return HttpResponseRedirect(reverse_lazy('collector_client_detail', kwargs={'pk': pk}, ))

    return render_to_response('collector/client_assign_torrents.html', {'form': form}, context_instance=RequestContext(request) )


def remove_client(request, pk):
    torrent = get_object_or_404(Torrent, pk=pk)

    if request.method == 'POST':
        client_id = request.POST.get('client')
        client = Client.objects.get(id=client_id)
        torrent.clients.remove(client)
        return HttpResponseRedirect(reverse_lazy('collector_torrent_detail', kwargs={'pk': pk},))

    form = TorrentRemoveClientForm(initial={'client':request.GET.get('client')})

    return render_to_response('collector/torrent_remove_client.html', {'form': form}, context_instance=RequestContext(request) )
