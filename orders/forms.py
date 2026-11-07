import re

from django import forms

from accounts.forms import StyledFormMixin

from .constants import GOVERNORATE_CHOICES
from .models import Order
from .payments import payment_options

PHONE_PATTERN = re.compile(r'01[0125]\d{8}')


class CheckoutForm(StyledFormMixin, forms.Form):
    customer_name = forms.CharField(label='Full name', max_length=120)
    phone = forms.CharField(
        label='Mobile number',
        max_length=20,
        help_text='An Egyptian mobile number, for example 01012345678.',
    )
    email = forms.EmailField(label='Email')
    governorate = forms.ChoiceField(
        label='Governorate',
        choices=[('', 'Select governorate')] + GOVERNORATE_CHOICES,
    )
    address = forms.CharField(
        label='Full delivery address',
        min_length=10,
        widget=forms.Textarea(attrs={'rows': 3}),
        help_text='Street, building, floor and apartment, and a nearby landmark.',
    )
    payment_method = forms.ChoiceField(
        label='Payment method',
        choices=Order.PaymentMethod.choices,
        widget=forms.RadioSelect,
        error_messages={
            'required': 'Please choose a payment method.',
            'invalid_choice': 'Please choose an available payment method.',
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only methods that are set up can be chosen, even if a form is tampered with.
        self.fields['payment_method'].choices = [
            (option.code, option.label) for option in payment_options() if option.available
        ]

    def clean_phone(self):
        number = re.sub(r'[\s\-().]', '', self.cleaned_data['phone'])
        if number.startswith('+20'):
            number = '0' + number[3:]
        elif number.startswith('0020'):
            number = '0' + number[4:]
        elif number.startswith('20') and len(number) == 12:
            number = '0' + number[2:]
        if not PHONE_PATTERN.fullmatch(number):
            raise forms.ValidationError(
                'Enter a valid Egyptian mobile number, for example 01012345678.'
            )
        return number
