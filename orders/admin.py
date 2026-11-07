from django import forms
from django.contrib import admin, messages

from .models import Order, OrderItem
from .services import cancel_order


class OrderItemInline(admin.TabularInline):
    """The purchase snapshot: shown for reference, never edited."""

    model = OrderItem
    extra = 0
    can_delete = False
    fields = ('product_name', 'color_name', 'size_label', 'quantity', 'unit_price', 'line_total')
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description='Line total')
    def line_total(self, obj):
        return obj.line_total


class OrderAdminForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = '__all__'

    def clean_status(self):
        status = self.cleaned_data['status']
        if (
            self.instance.pk
            and self.instance.status == Order.Status.CANCELLED
            and status != Order.Status.CANCELLED
        ):
            raise forms.ValidationError(
                'A cancelled order cannot be reopened. Ask the customer to place a new order.'
            )
        return status


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    form = OrderAdminForm
    list_display = (
        'reference',
        'customer_name',
        'governorate',
        'status',
        'payment_method',
        'payment_status',
        'total',
        'created_at',
    )
    list_filter = ('status', 'payment_method', 'payment_status', 'governorate', 'created_at')
    search_fields = ('reference', 'customer_name', 'phone', 'email')
    date_hierarchy = 'created_at'
    inlines = [OrderItemInline]
    readonly_fields = (
        'reference', 'user', 'subtotal', 'shipping_fee', 'total',
        'stock_reserved', 'created_at', 'updated_at',
    )
    fieldsets = (
        ('Order', {'fields': ('reference', 'user', 'status', 'created_at', 'updated_at')}),
        ('Payment', {'fields': ('payment_method', 'payment_status')}),
        ('Customer and delivery', {
            'fields': ('customer_name', 'phone', 'email', 'governorate', 'address'),
        }),
        ('Amounts (EGP)', {'fields': ('subtotal', 'shipping_fee', 'total', 'stock_reserved')}),
    )
    actions = (
        'mark_confirmed', 'mark_processing', 'mark_shipped', 'mark_delivered',
        'mark_payment_confirmed', 'cancel_orders',
    )

    def has_delete_permission(self, request, obj=None):
        # Deleting would lose the sales record and leave stock unrestored.
        return False

    def save_model(self, request, obj, form, change):
        cancelling = (
            change
            and 'status' in form.changed_data
            and obj.status == Order.Status.CANCELLED
        )
        if cancelling:
            # Save the other edits first, then cancel through the service so the
            # stock is restored exactly once.
            obj.status = Order.objects.get(pk=obj.pk).status
        super().save_model(request, obj, form, change)
        if cancelling:
            cancel_order(obj)

    def _set_status(self, request, queryset, status, label):
        changed = queryset.exclude(status=Order.Status.CANCELLED).update(status=status)
        self.message_user(request, f'{changed} order(s) marked as {label}.')

    @admin.action(description='Mark selected orders as Confirmed')
    def mark_confirmed(self, request, queryset):
        self._set_status(request, queryset, Order.Status.CONFIRMED, 'confirmed')

    @admin.action(description='Mark selected orders as Processing')
    def mark_processing(self, request, queryset):
        self._set_status(request, queryset, Order.Status.PROCESSING, 'processing')

    @admin.action(description='Mark selected orders as Shipped')
    def mark_shipped(self, request, queryset):
        self._set_status(request, queryset, Order.Status.SHIPPED, 'shipped')

    @admin.action(description='Mark selected orders as Delivered')
    def mark_delivered(self, request, queryset):
        self._set_status(request, queryset, Order.Status.DELIVERED, 'delivered')

    @admin.action(description='Confirm payment for selected orders')
    def mark_payment_confirmed(self, request, queryset):
        changed = queryset.update(payment_status=Order.PaymentStatus.PAID)
        self.message_user(request, f'Payment confirmed for {changed} order(s).')

    @admin.action(description='Cancel selected orders and restore their stock')
    def cancel_orders(self, request, queryset):
        cancelled = sum(1 for order in queryset if cancel_order(order))
        self.message_user(
            request,
            f'{cancelled} order(s) cancelled and stock restored.',
            level=messages.SUCCESS,
        )
