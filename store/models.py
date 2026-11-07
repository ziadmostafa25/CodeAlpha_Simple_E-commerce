
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)
    image = models.ImageField(upload_to='categories/', blank=True)

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products',
    )
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    image = models.ImageField(upload_to='products/')
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('store:product_detail', kwargs={'slug': self.slug})

    @property
    def ordered_sizes(self):
        size_order = ProductSize.Size.values
        return sorted(
            self.sizes.all(),
            key=lambda item: (
                size_order.index(item.size)
                if item.size in size_order
                else len(size_order)
            ),
        )

    @property
    def available_sizes(self):
        return [item for item in self.ordered_sizes if item.stock > 0]

    @property
    def is_in_stock(self):
        return bool(self.available_sizes)


class ProductSize(models.Model):
    class Size(models.TextChoices):
        SMALL = 'S', 'S'
        MEDIUM = 'M', 'M'
        LARGE = 'L', 'L'
        EXTRA_LARGE = 'XL', 'XL'

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='sizes',
    )
    size = models.CharField(max_length=2, choices=Size.choices)
    stock = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'size'],
                name='unique_size_per_product',
            ),
        ]

    def __str__(self):
        return f'{self.product.name} - {self.size}'

    @property
    def is_in_stock(self):
        return self.stock > 0
