from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, ButtonHolder, Submit
from django import forms
from django.forms import Textarea, Form
from threepwood.apps.collector.models import Torrent, Client
from django.utils.translation import ugettext as _

__author__ = 'cdumitru'


class TorrentForm(forms.ModelForm):
    title = _('Add a new torrent')
    show_fields = ['magnet', 'description', 'active']
    def __init__(self,  *args, **kwargs):
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(self.title, *self.show_fields ),
            ButtonHolder(
                Submit('save', _('Submit'), css_class='btn btn-primary '),
            )
        )
        self.helper.form_id = 'id-torrent-form'
        self.helper.form_method = 'post'
        super(TorrentForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Torrent
        exclude = ('date_added', 'clients', 'info_hash')
        widgets = {
            'magnet':Textarea(attrs={'cols': 80, 'rows': 2}),
            'description': Textarea(attrs={'cols': 80, 'rows': 5}),}

    class Media:
        css = {
            'all': ('uni_form/uni-form.css',)
        }


class TorrentUpdateForm(TorrentForm):
    show_fields = ['description', 'active']
    title = _('Edit torrent')
    class Meta(TorrentForm.Meta):
        exclude = ('date_added', 'clients', 'info_hash','magnet')





class TorrentAddClientForm(Form):
    title = _("Assign to clients")

    clients = forms.ModelMultipleChoiceField(widget=forms.CheckboxSelectMultiple, queryset=None)

    def __init__(self, *args, **kwargs):
        torrent = kwargs.pop('torrent')

        super(TorrentAddClientForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(self.title, 'clients'),
            ButtonHolder(
                Submit('save', _('Submit'), css_class='btn btn-primary '),
            )
        )
        self.helper.form_id = 'id-clients-form'
        self.helper.form_method = 'post'


        active_clients = torrent.clients.all().values_list('id')
        self.fields['clients'].queryset = Client.objects.filter(active=True).exclude(id__in=active_clients)


class ClientAddTorrentForm(Form):
    title = _("Add torrents to client")
    torrents = forms.ModelMultipleChoiceField(widget=forms.CheckboxSelectMultiple, queryset=None)

    def __init__(self, *args, **kwargs):
        client = kwargs.pop('client')

        super(ClientAddTorrentForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(self.title, 'torrents'),
            ButtonHolder(
                Submit('save', _('Submit'), css_class='btn btn-primary '),
            )
        )
        self.helper.form_id = 'id-torrents-form'
        self.helper.form_method = 'post'

        active_torrents = client.torrent_set.all().values_list('id')
        self.fields['torrents'].queryset = Torrent.objects.filter(active=True).exclude(id__in=active_torrents)

#TODO cleanup forms

class ClientCreateForm(forms.ModelForm):
    title = _('Add a new client')
    show_fields = [ 'description',]
    def __init__(self,  *args, **kwargs):
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(self.title, *self.show_fields),
            ButtonHolder(
                Submit('save', _('Submit'), css_class='btn btn-primary '),
            )
        )
        self.helper.form_id = 'id-client-form'
        self.helper.form_method = 'post'
        super(ClientCreateForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Client
        exclude = ('last_seen', 'key')
        widgets = {
            'description': Textarea(attrs={'cols': 80, 'rows': 5}),}

    class Media:
        css = {
            'all': ('uni_form/uni-form.css',)
        }


class ClientUpdateForm(ClientCreateForm):
    title = _('Edit client')
    show_fields = ['description', 'active']

    class Meta(ClientCreateForm.Meta):
        def __init__(self, *args, **kwargs):
            self.exclude += ('key',)
            super(ClientCreateForm.Meta, self).__init__(*args, **kwargs)

class ConfirmDelete(Form):
    title = _("Are you sure you want to delete this entry?")
    show_fields = []
    def __init__(self, *args, **kwargs):

        self.title = self.title
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(self.title, *self.show_fields),
            ButtonHolder(
                Submit('delete', _('Delete'), css_class='btn btn-danger'),
                Submit('back', _('Cancel'), css_class='btn'),
            )
        )
        self.helper.form_id = 'id-delete-form'
        self.helper.form_method = 'post'
        super(ConfirmDelete, self).__init__(*args, **kwargs)

class TorrentRemoveClientForm(ConfirmDelete):
    client = forms.IntegerField(widget=forms.HiddenInput())
    show_fields = ['client']

