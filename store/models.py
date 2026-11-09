
from decimal import Decimal

from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.urls import reverse

from .validators import IMAGE_VALIDATORS


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)
    image = models.ImageField(
        upload_to='categories/',
        blank=True,
        validators=IMAGE_VALIDATORS,
    )

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
    image = models.ImageField(
        upload_to='products/',
        validators=IMAGE_VALIDATORS,
    )
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
    def available_sizes(self):
        """Numeric sizes that are in stock in at least one colour."""
        in_stock = {
            item.size
            for color in self.colors.all()
            for item in color.sizes.all()
            if item.stock > 0
        }
        return [
            size for size in ProductSize.Size.values
            if size in in_stock
        ]

    @property
    def is_in_stock(self):
        return bool(self.available_sizes)


class ProductColor(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='colors',
    )
    name = models.CharField(max_length=60)
    hex_code = models.CharField(
        'colour code',
        max_length=7,
        default='#292821',
        validators=[
            RegexValidator(
                r'^#[0-9A-Fa-f]{6}$',
                'Enter a colour code like #A17B55.',
            )
        ],
        help_text='Used for the colour swatch, for example #A17B55.',
    )
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'pk']
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'name'],
                name='unique_color_name_per_product',
            ),
        ]

    def __str__(self):
        return f'{self.product.name} - {self.name}'

    @property
    def ordered_sizes(self):
        """Numeric sizes in ascending order."""
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
    def is_in_stock(self):
        return any(item.stock > 0 for item in self.sizes.all())

    @property
    def gallery_urls(self):
        """This colour's photos, or the product's default image."""
        urls = [
            image.image.url
            for image in self.images.all()
            if image.image
        ]
        if not urls and self.product.image:
            urls = [self.product.image.url]
        return urls


class ColorImage(models.Model):
    color = models.ForeignKey(
        ProductColor,
        on_delete=models.CASCADE,
        related_name='images',
    )
    image = models.ImageField(
        upload_to='products/colors/',
        validators=IMAGE_VALIDATORS,
    )
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'pk']

    def __str__(self):
        return f'{self.color} image {self.pk}'


class ProductSize(models.Model):
    class Size(models.TextChoices):
        SIZE_48 = '48', '48'
        SIZE_50 = '50', '50'
        SIZE_52 = '52', '52'
        SIZE_54 = '54', '54'
        SIZE_56 = '56', '56'
        SIZE_58 = '58', '58'

    color = models.ForeignKey(
        ProductColor,
        on_delete=models.CASCADE,
        related_name='sizes',
    )
    size = models.CharField(
        max_length=2,
        choices=Size.choices,
    )
    stock = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['color', 'size'],
                name='unique_size_per_color',
            ),
        ]

    def __str__(self):
        return f'{self.color} / {self.size}'

    @property
    def product(self):
        return self.color.product

    @property
    def is_in_stock(self):
        return self.stock > 0

