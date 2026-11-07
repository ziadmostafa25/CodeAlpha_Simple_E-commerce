import uuid

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse

from .constants import GOVERNORATE_CHOICES


def generate_reference():
    return 'ZS-' + uuid.uuid4().hex[:8].upper()


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        PROCESSING = 'processing', 'Processing'
        SHIPPED = 'shipped', 'Shipped'
        DELIVERED = 'delivered', 'Delivered'
        CANCELLED = 'cancelled', 'Cancelled'

    class PaymentMethod(models.TextChoices):
        COD = 'cod', 'Cash on delivery'
        VODAFONE_CASH = 'vodafone_cash', 'Vodafone Cash'
        INSTAPAY = 'instapay', 'InstaPay'

    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', 'Awaiting payment'
        PAID = 'paid', 'Payment confirmed'

    reference = models.CharField(max_length=20, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='orders',
    )

    # Customer and delivery details, copied at checkout.
    customer_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    governorate = models.CharField(max_length=40, choices=GOVERNORATE_CHOICES)
    address = models.TextField()

    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    payment_status = models.CharField(
        max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )

    # Amounts at the time of purchase.
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_fee = models.DecimalField(max_digits=8, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    # True while this order's stock is held. Cancelling gives it back exactly once.
    stock_reserved = models.BooleanField(default=True, editable=False)
    # One checkout form can create one order only (blocks double submissions).
    checkout_token = models.UUIDField(null=True, unique=True, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-pk']

    def __str__(self):
        return self.reference

    def save(self, *args, **kwargs):
        if not self.reference:
            reference = generate_reference()
            while Order.objects.filter(reference=reference).exists():
                reference = generate_reference()
            self.reference = reference
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('orders:detail', kwargs={'reference': self.reference})

    @property
    def is_cancelled(self):
        return self.status == self.Status.CANCELLED

    @property
    def customer_can_cancel(self):
        return self.status == self.Status.PENDING


class OrderItem(models.Model):
    """What was bought, copied from the catalogue so old orders never change."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    # Kept only to give stock back on cancellation; the snapshot below is what is shown.
    size = models.ForeignKey(
        'store.ProductSize',
        on_delete=models.SET_NULL,
        null=True,
        related_name='+',
    )
    product_name = models.CharField(max_length=150)
    color_name = models.CharField(max_length=60)
    size_label = models.CharField(max_length=2)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    image_name = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f'{self.quantity} x {self.product_name} ({self.color_name}, {self.size_label})'

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    @property
    def image_url(self):
        return default_storage.url(self.image_name) if self.image_name else ''
