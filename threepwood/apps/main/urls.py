__author__ = 'cdumitru'

from django.conf.urls import patterns, url
from django.views.generic.base import RedirectView
from views import HomePage

urlpatterns = patterns('',
    #redirect to home
    url(r'^home/', HomePage.as_view(), name='home'),
)