import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from cart.cart import Cart
from store.constants import RETURN_POLICY

from .forms import CheckoutForm
from .payments import get_payment_option, payment_options
from .services import DuplicateSubmission, OrderError, cancel_order, create_order

CHECKOUT_TOKEN_KEY = 'checkout_token'


def _own_order(request, reference):
    """Orders are only ever looked up through their owner."""
    return get_object_or_404(
        request.user.orders.prefetch_related('items'), reference=reference
    )


@login_required
def checkout(request):
    cart = Cart(request)
    if cart.is_empty:
        messages.info(request, 'Your cart is empty.')
        return redirect('cart:detail')
    if cart.has_issues:
        messages.error(request, 'Please fix the items in your cart before checking out.')
        return redirect('cart:detail')

    token = request.session.get(CHECKOUT_TOKEN_KEY)
    if not token:
        token = request.session[CHECKOUT_TOKEN_KEY] = str(uuid.uuid4())

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                order = create_order(
                    user=request.user,
                    cart=cart,
                    data=form.cleaned_data,
                    token=uuid.UUID(token),
                )
            except DuplicateSubmission as duplicate:
                if duplicate.order.user_id != request.user.pk:
                    messages.error(request, 'Something went wrong. Please try again.')
                    return redirect('cart:detail')
                return redirect('orders:success', reference=duplicate.order.reference)
            except OrderError as error:
                messages.error(request, str(error))
                return redirect('cart:detail')
            request.session.pop(CHECKOUT_TOKEN_KEY, None)
            return redirect('orders:success', reference=order.reference)
    else:
        form = CheckoutForm(
            initial={
                'customer_name': request.user.get_full_name(),
                'email': request.user.email,
            }
        )

    return render(
        request,
        'orders/checkout.html',
        {
            'form': form,
            'cart': cart,
            'lines': cart.lines(),
            'payment_options': payment_options(),
            'selected_method': form['payment_method'].value() or 'cod',
            'return_policy': RETURN_POLICY,
        },
    )


@login_required
def order_success(request, reference):
    order = _own_order(request, reference)
    return render(
        request,
        'orders/order_success.html',
        {
            'order': order,
            'payment': get_payment_option(order.payment_method),
            'return_policy': RETURN_POLICY,
        },
    )


@login_required
def order_list(request):
    return render(request, 'orders/order_list.html', {'orders': request.user.orders.all()})


@login_required
def order_detail(request, reference):
    order = _own_order(request, reference)
    return render(
        request,
        'orders/order_detail.html',
        {
            'order': order,
            'payment': get_payment_option(order.payment_method),
            'return_policy': RETURN_POLICY,
        },
    )


@login_required
@require_POST
def order_cancel(request, reference):
    order = _own_order(request, reference)
    try:
        if cancel_order(order, by_customer=True):
            messages.success(request, f'Order {order.reference} was cancelled.')
        else:
            messages.info(request, 'This order was already cancelled.')
    except OrderError as error:
        messages.error(request, str(error))
    return redirect('orders:detail', reference=order.reference)
