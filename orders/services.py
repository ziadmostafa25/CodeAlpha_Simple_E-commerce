from django.db import IntegrityError, transaction
from django.db.models import F

from store.models import ProductSize

from .models import Order, OrderItem


class OrderError(Exception):
    """A problem the customer can understand; the message is safe to show."""


class DuplicateSubmission(OrderError):
    """The same checkout form was submitted twice; `order` is the first result."""

    def __init__(self, order):
        super().__init__('This order was already placed.')
        self.order = order


def create_order(*, user, cart, data, token):
    """Turn the cart into an order and take its stock, all in one transaction.

    Stock is taken with a conditional UPDATE (`stock >= quantity`), so two
    customers can never buy the last item. If anything fails, nothing is saved.
    """
    lines = cart.lines()
    if not lines:
        raise OrderError('Your cart is empty.')
    for line in lines:
        if line.issue:
            raise OrderError(
                f'{line.product.name} ({line.color.name}, {line.size.size}): {line.issue}'
            )

    try:
        with transaction.atomic():
            order = Order.objects.create(
                user=user,
                checkout_token=token,
                customer_name=data['customer_name'],
                phone=data['phone'],
                email=data['email'],
                governorate=data['governorate'],
                address=data['address'],
                payment_method=data['payment_method'],
                subtotal=cart.subtotal,
                shipping_fee=cart.shipping,
                total=cart.total,
            )
            for line in lines:
                taken = ProductSize.objects.filter(
                    pk=line.size.pk, stock__gte=line.quantity
                ).update(stock=F('stock') - line.quantity)
                if not taken:
                    raise OrderError(
                        f'{line.product.name} ({line.color.name}, {line.size.size}) '
                        'is no longer available in that quantity.'
                    )
                OrderItem.objects.create(
                    order=order,
                    size=line.size,
                    product_name=line.product.name,
                    color_name=line.color.name,
                    size_label=line.size.size,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                    image_name=line.image_name,
                )
    except IntegrityError:
        existing = Order.objects.filter(checkout_token=token).first()
        if existing:
            raise DuplicateSubmission(existing)
        raise

    cart.clear()
    return order


def cancel_order(order, *, by_customer=False):
    """Cancel an order and give its stock back once. Returns False if already cancelled."""
    with transaction.atomic():
        locked = Order.objects.select_for_update().get(pk=order.pk)
        if locked.status == Order.Status.CANCELLED:
            return False
        if by_customer and locked.status != Order.Status.PENDING:
            raise OrderError('This order can no longer be cancelled online.')

        if locked.stock_reserved:
            for item in locked.items.exclude(size=None):
                ProductSize.objects.filter(pk=item.size_id).update(
                    stock=F('stock') + item.quantity
                )
            locked.stock_reserved = False
        locked.status = Order.Status.CANCELLED
        locked.save(update_fields=['status', 'stock_reserved', 'updated_at'])

    order.refresh_from_db()
    return True
