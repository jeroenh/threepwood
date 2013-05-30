from django.contrib.auth.forms import AuthenticationForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.utils.translation import ugettext as _

__author__ = 'cdumitru'

class ThreepwoodAuthenticationForm(AuthenticationForm):
    title = "Login form"
    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_id = 'id-login-form'
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', _('Login')))

        super(ThreepwoodAuthenticationForm, self).__init__(*args, **kwargs)


    class Media:
        css = {
            'all': ('uni_form/uni-form.css',)
        }
