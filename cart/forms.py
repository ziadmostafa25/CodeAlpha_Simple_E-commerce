from django import forms

from store.models import ProductSize

SIZE_QUERYSET = ProductSize.objects.select_related('color__product')


class AddToCartForm(forms.Form):
    size = forms.ModelChoiceField(
        queryset=SIZE_QUERYSET,
        error_messages={
            'required': 'Please choose a size.',
            'invalid_choice': 'Please choose a valid size.',
        },
    )
    quantity = forms.IntegerField(
        min_value=1,
        error_messages={
            'required': 'Enter a quantity.',
            'invalid': 'Enter a quantity of 1 or more.',
            'min_value': 'Enter a quantity of 1 or more.',
        },
    )


class UpdateCartForm(forms.Form):
    size = forms.ModelChoiceField(
        queryset=SIZE_QUERYSET,
        error_messages={'invalid_choice': 'That item is not available.'},
    )
    quantity = forms.IntegerField(
        min_value=0,
        error_messages={
            'invalid': 'Enter a valid quantity.',
            'min_value': 'Enter a valid quantity.',
        },
    )
