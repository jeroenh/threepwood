# Create your views here.
from django.views.generic import TemplateView, DetailView
from threepwood.apps.collector.models import Torrent, PeerRecord

class ClientReport(TemplateView):
    template_name = "reports/client_report.html"


class TorrentReport(DetailView):
    model = Torrent
    template_name = "reports/torrent_report.html"
    context_object_name = "torrent"

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
#        torrent = self.get_object()
        return context
