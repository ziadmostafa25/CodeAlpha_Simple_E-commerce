from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings

from store.models import ProductSize

CART_SESSION_KEY = 'cart'
TWO_PLACES = Decimal('0.01')


class CartError(Exception):
    """A problem the customer can fix; the message is safe to show to them."""


@dataclass
class CartLine:
    """One product colour and size in the cart. Prices always come from the database."""

    size: ProductSize
    quantity: int

    @property
    def color(self):
        return self.size.color

    @property
    def product(self):
        return self.size.color.product

    @property
    def unit_price(self):
        return self.product.price

    @property
    def subtotal(self):
        return self.unit_price * self.quantity

    @property
    def image_url(self):
        urls = self.color.gallery_urls
        return urls[0] if urls else ''

    @property
    def image_name(self):
        first = next(iter(self.color.images.all()), None)
        if first:
            return first.image.name
        return self.product.image.name

    @property
    def issue(self):
        """Why this line cannot be ordered right now, or an empty string."""
        if self.size.stock <= 0:
            return 'This size is sold out.'
        if self.quantity > self.size.stock:
            return f'Only {self.size.stock} left.'
        return ''


class Cart:
    """Session-based cart: {size id: quantity}. Works for guests and signed-in users."""

    def __init__(self, request):
        self.session = request.session
        self._items = {
            str(key): int(value)
            for key, value in self.session.get(CART_SESSION_KEY, {}).items()
        }
        self._lines = None
        self.pruned = False

    # -- changing the cart -------------------------------------------------
    def add(self, size, quantity):
        self._set(size, self._items.get(str(size.pk), 0) + quantity)

    def set_quantity(self, size, quantity):
        if quantity <= 0:
            self.remove(size.pk)
        else:
            self._set(size, quantity)

    def remove(self, size_id):
        self._items.pop(str(size_id), None)
        self._save()

    def clear(self):
        self._items = {}
        self._lines = None
        self.session.pop(CART_SESSION_KEY, None)
        self.session.modified = True

    def _set(self, size, quantity):
        self._check(size, quantity)
        self._items[str(size.pk)] = quantity
        self._save()

    @staticmethod
    def _check(size, quantity):
        color = size.color
        product = color.product
        label = f'{product.name} ({color.name}, {size.size})'
        if not product.is_active:
            raise CartError(f'{product.name} is no longer available.')
        if size.stock <= 0:
            raise CartError(f'{label} is sold out.')
        if quantity > settings.CART_MAX_QUANTITY:
            raise CartError(
                f'You can order at most {settings.CART_MAX_QUANTITY} of one item.'
            )
        if quantity > size.stock:
            raise CartError(f'Only {size.stock} left of {label}.')

    def _save(self):
        self._lines = None
        self.session[CART_SESSION_KEY] = self._items
        self.session.modified = True

    # -- reading the cart --------------------------------------------------
    @property
    def count(self):
        return sum(self._items.values())

    @property
    def is_empty(self):
        return not self._items

    def lines(self):
        if self._lines is None:
            ids = [int(key) for key in self._items]
            sizes = (
                ProductSize.objects.filter(pk__in=ids, color__product__is_active=True)
                .select_related('color__product')
                .prefetch_related('color__images')
            )
            by_id = {size.pk: size for size in sizes}
            self._lines = [
                CartLine(by_id[int(key)], quantity)
                for key, quantity in self._items.items()
                if int(key) in by_id
            ]
            if len(self._lines) != len(self._items):
                # Some products were deleted or hidden since they were added.
                self._items = {str(line.size.pk): line.quantity for line in self._lines}
                self.pruned = True
                self._save_without_reset()
        return self._lines

    def _save_without_reset(self):
        self.session[CART_SESSION_KEY] = self._items
        self.session.modified = True

    @property
    def has_issues(self):
        return any(line.issue for line in self.lines())

    @property
    def subtotal(self):
        return sum((line.subtotal for line in self.lines()), Decimal('0.00'))

    @property
    def shipping(self):
        if not self.lines():
            return Decimal('0.00')
        threshold = settings.FREE_SHIPPING_THRESHOLD
        if threshold is not None and self.subtotal >= threshold:
            return Decimal('0.00')
        return Decimal(settings.SHIPPING_FEE).quantize(TWO_PLACES)

    @property
    def total(self):
        return self.subtotal + self.shipping
