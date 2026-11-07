from django.contrib import admin
from django.db.models import Sum

from .models import Category, Product, ProductSize


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


class ProductSizeInline(admin.TabularInline):
    model = ProductSize
    extra = 4


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
    inlines = [ProductSizeInline]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(_total_stock=Sum('sizes__stock'))

    @admin.display(description='Total stock', ordering='_total_stock')
    def total_stock(self, obj):
        return obj._total_stock or 0
