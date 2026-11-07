from dataclasses import dataclass

from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static

from .models import Order

LOGO_EXTENSIONS = ('svg', 'png', 'webp')


@dataclass(frozen=True)
class PaymentOption:
    code: str
    label: str
    summary: str
    instructions: str
    details: str
    details_label: str
    available: bool
    logo_url: str


def _logo_url(slug):
    """Official logo, if you added it as static/images/payments/<slug>.svg|png|webp."""
    for extension in LOGO_EXTENSIONS:
        path = f'images/payments/{slug}.{extension}'
        if finders.find(path):
            return static(path)
    return ''


def _manual_option(code, label, slug, details, details_label, how_to_pay):
    available = bool(details)
    return PaymentOption(
        code=code,
        label=label,
        summary='Pay by transfer' if available else 'Not available yet',
        instructions=(
            f'{how_to_pay} Your payment is confirmed by the store after it '
            'reviews your transfer.'
            if available
            else 'This payment method has not been set up yet.'
        ),
        details=details,
        details_label=details_label,
        available=available,
        logo_url=_logo_url(slug),
    )


def payment_options():
    return [
        PaymentOption(
            code=Order.PaymentMethod.COD,
            label='Cash on delivery',
            summary='Pay when you receive your order',
            instructions=(
                'You pay in cash when your order is delivered. '
                'Please have the exact amount ready.'
            ),
            details='',
            details_label='',
            available=True,
            logo_url='',
        ),
        _manual_option(
            Order.PaymentMethod.VODAFONE_CASH,
            'Vodafone Cash',
            'vodafone-cash',
            settings.VODAFONE_CASH_NUMBER,
            'Vodafone Cash number',
            'Send the order total to this Vodafone Cash number and keep your receipt.',
        ),
        _manual_option(
            Order.PaymentMethod.INSTAPAY,
            'InstaPay',
            'instapay',
            settings.INSTAPAY_ADDRESS,
            'InstaPay address',
            'Send the order total to this InstaPay address and keep your receipt.',
        ),
    ]


def get_payment_option(code):
    return next((option for option in payment_options() if option.code == code), None)
