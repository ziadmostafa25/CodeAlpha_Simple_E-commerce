import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0003_attach_existing_sizes_to_default_colour'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='productsize',
            name='unique_size_per_product',
        ),
        migrations.AlterField(
            model_name='productsize',
            name='color',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='sizes',
                to='store.productcolor',
            ),
        ),
        migrations.RemoveField(
            model_name='productsize',
            name='product',
        ),
        migrations.AddConstraint(
            model_name='productsize',
            constraint=models.UniqueConstraint(
                fields=('color', 'size'),
                name='unique_size_per_color',
            ),
        ),
    ]
