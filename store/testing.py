"""Helpers shared by the test modules of every app (not a test module itself)."""

from decimal import Decimal

from .models import Category, Product, ProductColor, ProductSize

COLOR_HEX = {'Black': '#1A1A1A', 'Brown': '#7E5C3C', 'Beige': '#D8C8B0'}


def create_category(name='Jackets'):
    category, _ = Category.objects.get_or_create(
        slug=name.lower().replace(' ', '-'), defaults={'name': name}
    )
    return category


def create_product(category, name, price='100', stock=None, colors=None, **extra):
    """Create a product without needing real image files.

    `colors` is {colour name: {size: stock}}. Without it the product gets one
    colour called "Default" whose sizes come from `stock` (default: M with 5).
    """
    product = Product.objects.create(
        category=category,
        name=name,
        slug=extra.pop('slug', name.lower().replace(' ', '-')),
        price=Decimal(price),
        image=extra.pop('image', 'products/test.jpg'),
        **extra,
    )
    if colors is None:
        colors = {'Default': stock if stock is not None else {'M': 5}}
    for order, (color_name, sizes) in enumerate(colors.items()):
        color = ProductColor.objects.create(
            product=product,
            name=color_name,
            hex_code=COLOR_HEX.get(color_name, '#292821'),
            sort_order=order,
        )
        for size, amount in sizes.items():
            ProductSize.objects.create(color=color, size=size, stock=amount)
    return product


def get_size(product, size, color='Default'):
    return ProductSize.objects.get(color__product=product, color__name=color, size=size)
