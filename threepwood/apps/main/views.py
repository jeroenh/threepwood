__author__ = 'cdumitru'

from django.views.generic import TemplateView

class HomePage(TemplateView):
    template_name = "main/index.html"