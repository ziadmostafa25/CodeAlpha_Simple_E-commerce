from django.contrib import admin
from django.db.models import Sum
from django.utils.html import format_html

from .models import Category, ColorImage, Product, ProductColor, ProductSize

LOW_STOCK_LIMIT = 3


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


class ProductColorInline(admin.TabularInline):
    """Colours of a product. Photos, sizes and stock are edited per colour."""

    model = ProductColor
    extra = 1
    fields = ('name', 'hex_code', 'sort_order')
    show_change_link = True


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'category',
        'price',
        'total_stock',
        'is_active',
        'is_featured',
    )
    list_editable = ('is_active', 'is_featured')
    list_filter = ('category', 'is_active', 'is_featured')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductColorInline]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(_total_stock=Sum('colors__sizes__stock'))

    @admin.display(description='Total stock', ordering='_total_stock')
    def total_stock(self, obj):
        return obj._total_stock or 0


class ColorImageInline(admin.TabularInline):
    model = ColorImage
    extra = 2
    fields = ('image', 'sort_order')


class ProductSizeInline(admin.TabularInline):
    model = ProductSize
    extra = 4
    fields = ('size', 'stock')


@admin.register(ProductColor)
class ProductColorAdmin(admin.ModelAdmin):
    """One page per colour: its photos, its sizes and the stock of each size."""

    list_display = ('product', 'name', 'swatch', 'total_stock')
    list_filter = ('product__category',)
    search_fields = ('product__name', 'name')
    autocomplete_fields = ('product',)
    inlines = [ColorImageInline, ProductSizeInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_total_stock=Sum('sizes__stock'))

    @admin.display(description='Colour')
    def swatch(self, obj):
        return format_html(
            '<span style="display:inline-block;width:1.25rem;height:1.25rem;'
            'border:1px solid #999;background:{}"></span>',
            obj.hex_code,
        )

    @admin.display(description='Total stock', ordering='_total_stock')
    def total_stock(self, obj):
        return obj._total_stock or 0


class LowStockFilter(admin.SimpleListFilter):
    title = 'stock level'
    parameter_name = 'stock_level'

    def lookups(self, request, model_admin):
        return [('out', 'Out of stock'), ('low', f'Low (1 to {LOW_STOCK_LIMIT})')]

    def queryset(self, request, queryset):
        if self.value() == 'out':
            return queryset.filter(stock=0)
        if self.value() == 'low':
            return queryset.filter(stock__gt=0, stock__lte=LOW_STOCK_LIMIT)
        return queryset


@admin.register(ProductSize)
class ProductSizeAdmin(admin.ModelAdmin):
    """Stock overview: every colour and size, sortable by quantity."""

    list_display = ('product_name', 'color', 'size', 'stock')
    list_editable = ('stock',)
    list_filter = (LowStockFilter, 'size', 'color__product__category')
    search_fields = ('color__product__name', 'color__name')
    ordering = ('stock',)
    list_select_related = ('color__product',)

    @admin.display(description='Product', ordering='color__product__name')
    def product_name(self, obj):
        return obj.color.product.name

    def has_add_permission(self, request):
        # Sizes are added from the colour page, where they belong to a colour.
        return False
