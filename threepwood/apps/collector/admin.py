from threepwood.apps.collector.models import Client, Torrent, Session, PeerRecord, ASN, PeerInfo
from django.contrib import admin

admin.site.register(Client)
admin.site.register(Torrent)
admin.site.register(Session)
admin.site.register(PeerRecord)
admin.site.register(ASN)
admin.site.register(PeerInfo)