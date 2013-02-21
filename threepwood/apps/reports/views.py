# Create your views here.
from django.views.generic import TemplateView, DetailView, ListView
from threepwood.apps.collector.models import Torrent, PeerRecord, Client

class ClientReport(TemplateView):
    template_name = "reports/client_report.html"


class ClientReportList(ListView):
    queryset = Client.objects.all()
    template_name = "reports/client_list.html"

class ClientReportDetail(DetailView):
    model = Client
    context_object_name = 'client'
    template_name = "reports/client_detail.html"


class TorrentReportList(ListView):
    queryset = Torrent.objects.all()
    context_object_name = "torrent_list"
    template_name = "reports/torrent_list.html"

class TorrentReport(DetailView):
    model = Torrent
    template_name = "reports/torrent_report.html"
    context_object_name = "torrent"

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
#        torrent = self.get_object()
        return context


class TorrentReportDetail(DetailView):
    model = Torrent
    context_object_name = "torrent"
    template_name = "reports/torrent_detail.html"