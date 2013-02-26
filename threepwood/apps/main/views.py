from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

__author__ = 'cdumitru'

from django.views.generic import TemplateView, View


class ProtectedView(View):
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(ProtectedView, self).dispatch(*args, **kwargs)

class HomePage(TemplateView):
    template_name = "main/index.html"