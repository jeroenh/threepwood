from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.core.urlresolvers import reverse_lazy
from django.views.generic import RedirectView


admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', RedirectView.as_view(url=reverse_lazy("home"))),
    url(r'^main/', include('threepwood.apps.main.urls')),
    url(r'^collector/', include('threepwood.apps.collector.urls')),
    url(r'^reports/', include('threepwood.apps.reports.urls')),
    url(r'^admin/', include(admin.site.urls)),
)


urlpatterns += staticfiles_urlpatterns()