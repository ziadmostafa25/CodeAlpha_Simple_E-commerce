from django.db import migrations

DEFAULT_COLOR_NAME = 'Default'
DEFAULT_COLOR_HEX = '#292821'


def attach_sizes_to_a_default_colour(apps, schema_editor):
    """Give every product that already has sizes one colour that holds them.

    Existing sizes and stock are kept exactly as they are; the store owner
    can rename the colour or add more colours later in Django Admin.
    """
    Product = apps.get_model('store', 'Product')
    ProductColor = apps.get_model('store', 'ProductColor')
    ProductSize = apps.get_model('store', 'ProductSize')

    for product in Product.objects.filter(sizes__isnull=False).distinct():
        color, _ = ProductColor.objects.get_or_create(
            product=product,
            name=DEFAULT_COLOR_NAME,
            defaults={'hex_code': DEFAULT_COLOR_HEX, 'sort_order': 0},
        )
        ProductSize.objects.filter(product=product, color__isnull=True).update(
            color=color
        )


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0002_add_colors_and_images'),
    ]

    operations = [
        # Reversing is safe: the old product link is still in place until 0004.
        migrations.RunPython(attach_sizes_to_a_default_colour, migrations.RunPython.noop),
    ]
