# Create your views here.
from django.views.generic import TemplateView, DetailView, ListView
from django.views.generic.detail import SingleObjectMixin
from threepwood.apps.collector.models import Torrent, PeerRecord, Client
from threepwood.apps.main.views import ProtectedView


class ClientReport(TemplateView, ProtectedView):
    template_name = "reports/client_report.html"


class ClientReportList(ListView, ProtectedView):
    queryset = Client.objects.all()
    template_name = "reports/client_list.html"


class ClientReportDetail(DetailView, ProtectedView):
    model = Client
    context_object_name = 'client'
    template_name = "reports/client_detail.html"


class TorrentReportList(ListView, ProtectedView):
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


class TorrentReportDetail(SingleObjectMixin, ListView, ProtectedView):
    paginate_by = 20
    context_object_name = "torrent"
    template_name = "reports/torrent_report.html"

    def get_context_data(self, **kwargs):
        kwargs['torrent'] = self.object
        return super(TorrentReportDetail, self).get_context_data(**kwargs)

    def get_queryset(self):
        self.object = self.get_object(Torrent.objects.all())
        return self.object.session_set.all().order_by('-date_created')
