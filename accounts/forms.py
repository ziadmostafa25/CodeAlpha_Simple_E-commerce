from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

User = get_user_model()


class StyledFormMixin:
    """Gives every text-like field the shared `input` CSS class."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.RadioSelect)):
                field.widget.attrs.setdefault('class', 'input')


def _unique_email(value, exclude_pk=None):
    value = value.strip().lower()
    users = User.objects.filter(email__iexact=value)
    if exclude_pk:
        users = users.exclude(pk=exclude_pk)
    if users.exists():
        raise forms.ValidationError('An account with this email already exists.')
    return value


class RegistrationForm(StyledFormMixin, UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    def clean_email(self):
        return _unique_email(self.cleaned_data['email'])


class LoginForm(StyledFormMixin, AuthenticationForm):
    pass


class ProfileForm(StyledFormMixin, forms.ModelForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')

    def clean_email(self):
        return _unique_email(self.cleaned_data['email'], exclude_pk=self.instance.pk)
