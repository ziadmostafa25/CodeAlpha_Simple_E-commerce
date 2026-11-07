from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .cart import Cart, CartError
from .forms import AddToCartForm, UpdateCartForm


def _first_error(form):
    for errors in form.errors.values():
        return errors[0]
    return 'Something went wrong. Please try again.'


def _safe_next(request, default):
    target = request.POST.get('next', '')
    allowed = url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    )
    return target if target and allowed else default


def cart_detail(request):
    cart = Cart(request)
    lines = cart.lines()
    if cart.pruned:
        messages.info(
            request, 'Some items were removed because they are no longer available.'
        )
    return render(request, 'cart/cart_detail.html', {'cart': cart, 'lines': lines})


@require_POST
def cart_add(request):
    back = _safe_next(request, reverse('store:product_list'))
    form = AddToCartForm(request.POST)
    if not form.is_valid():
        messages.error(request, _first_error(form))
        return redirect(back)

    size = form.cleaned_data['size']
    try:
        Cart(request).add(size, form.cleaned_data['quantity'])
    except CartError as error:
        messages.error(request, str(error))
        return redirect(back)

    messages.success(request, f'{size.color.product.name} was added to your cart.')
    return redirect('cart:detail')


@require_POST
def cart_update(request):
    form = UpdateCartForm(request.POST)
    if not form.is_valid():
        messages.error(request, _first_error(form))
        return redirect('cart:detail')
    try:
        Cart(request).set_quantity(form.cleaned_data['size'], form.cleaned_data['quantity'])
    except CartError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, 'Your cart was updated.')
    return redirect('cart:detail')


@require_POST
def cart_remove(request):
    size_id = request.POST.get('size', '')
    if size_id.isdigit():
        Cart(request).remove(int(size_id))
        messages.success(request, 'The item was removed from your cart.')
    return redirect('cart:detail')
