import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from cart.cart import Cart
from store.testing import create_category, create_product, get_size

from .admin import OrderAdminForm
from .models import Order, OrderItem
from .services import DuplicateSubmission, OrderError, cancel_order, create_order

User = get_user_model()
PASSWORD = 'a-Strong-pass-2026'
MANUAL_PAYMENTS = {
    'VODAFONE_CASH_NUMBER': 'TEST-WALLET-NUMBER',
    'INSTAPAY_ADDRESS': 'test-handle@instapay-test',
}


class OrderTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('sara', 'sara@example.com', PASSWORD, first_name='Sara')
        self.other = User.objects.create_user('omar', 'omar@example.com', PASSWORD)
        self.product = create_product(
            create_category(),
            'Classic Jacket',
            price='850',
            colors={'Black': {'S': 5, 'M': 3}, 'Brown': {'S': 2}},
        )
        self.black_s = get_size(self.product, 'S', 'Black')
        self.black_m = get_size(self.product, 'M', 'Black')
        self.brown_s = get_size(self.product, 'S', 'Brown')
        self.client.force_login(self.user)

    def add_to_cart(self, size, quantity=1):
        self.client.post(reverse('cart:add'), {'size': size.pk, 'quantity': quantity})

    def checkout_data(self, **overrides):
        data = {
            'customer_name': 'Sara Ali',
            'phone': '01012345678',
            'email': 'sara@example.com',
            'governorate': 'Cairo',
            'address': '12 Nile Street, building 4, apartment 9, Cairo',
            'payment_method': 'cod',
        }
        data.update(overrides)
        return data

    def place_order(self, **overrides):
        return self.client.post(reverse('orders:checkout'), self.checkout_data(**overrides))

    def stock(self, size):
        size.refresh_from_db()
        return size.stock

    def make_order(self, user=None, quantity=2, size=None):
        """Create an order straight through the service."""
        size = size or self.black_s
        request = RequestFactory().get('/')
        request.session = self.client.session
        cart = Cart(request)
        cart.add(size, quantity)
        return create_order(
            user=user or self.user, cart=cart, data=self.checkout_data(), token=uuid.uuid4()
        )


class CheckoutAccessTests(OrderTestCase):
    def test_checkout_needs_a_signed_in_customer(self):
        self.client.logout()
        self.add_to_cart(self.black_s)
        response = self.client.get(reverse('orders:checkout'))
        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={reverse('orders:checkout')}",
            fetch_redirect_response=False,
        )

    def test_empty_cart_goes_back_to_the_cart(self):
        response = self.client.get(reverse('orders:checkout'))
        self.assertRedirects(response, reverse('cart:detail'))

    def test_a_cart_with_a_stock_problem_cannot_reach_checkout(self):
        self.add_to_cart(self.black_m, 3)
        self.black_m.stock = 1
        self.black_m.save()
        response = self.client.get(reverse('orders:checkout'))
        self.assertRedirects(response, reverse('cart:detail'))

    def test_checkout_page_shows_the_summary_policy_and_prefilled_details(self):
        self.add_to_cart(self.black_s, 2)
        response = self.client.get(reverse('orders:checkout'))
        self.assertContains(response, 'Black, size S')
        self.assertContains(response, 'EGP 1700')
        self.assertContains(response, 'Return and exchange shipping costs are paid by the customer.')
        self.assertContains(response, 'value="Sara"')
        self.assertContains(response, 'csrfmiddlewaretoken')
        self.assertContains(response, 'Place order')


class PaymentMethodTests(OrderTestCase):
    def test_cash_on_delivery_is_selected_by_default(self):
        self.add_to_cart(self.black_s)
        response = self.client.get(reverse('orders:checkout'))
        self.assertEqual(response.context['selected_method'], 'cod')
        self.assertContains(response, 'You pay in cash when your order is delivered.')

    def test_manual_methods_are_unavailable_until_details_are_configured(self):
        self.add_to_cart(self.black_s)
        response = self.client.get(reverse('orders:checkout'))
        options = {option.code: option for option in response.context['payment_options']}
        self.assertTrue(options['cod'].available)
        self.assertFalse(options['vodafone_cash'].available)
        self.assertFalse(options['instapay'].available)
        self.assertContains(response, 'Not available yet')
        self.assertNotContains(response, 'TEST-WALLET-NUMBER')

    def test_an_unavailable_method_cannot_be_ordered_even_if_the_form_is_tampered_with(self):
        self.add_to_cart(self.black_s)
        response = self.place_order(payment_method='vodafone_cash')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Order.objects.exists())
        self.assertContains(response, 'Please choose an available payment method.')

    @override_settings(**MANUAL_PAYMENTS)
    def test_configured_methods_show_their_instructions_and_details(self):
        self.add_to_cart(self.black_s)
        response = self.client.get(reverse('orders:checkout'))
        self.assertContains(response, 'TEST-WALLET-NUMBER')
        self.assertContains(response, 'test-handle@instapay-test')
        self.assertContains(response, 'confirmed by the store after it reviews your transfer')

    @override_settings(**MANUAL_PAYMENTS)
    def test_a_manual_payment_is_saved_and_never_marked_as_verified(self):
        self.add_to_cart(self.black_s)
        self.place_order(payment_method='vodafone_cash')
        order = Order.objects.get()
        self.assertEqual(order.payment_method, 'vodafone_cash')
        self.assertEqual(order.payment_status, Order.PaymentStatus.PENDING)
        response = self.client.get(reverse('orders:success', args=[order.reference]))
        self.assertContains(response, 'TEST-WALLET-NUMBER')
        self.assertNotContains(response, 'verified')

    @override_settings(**MANUAL_PAYMENTS)
    def test_instapay_orders_are_saved_too(self):
        self.add_to_cart(self.black_s)
        self.place_order(payment_method='instapay')
        self.assertEqual(Order.objects.get().payment_method, 'instapay')

    def test_a_payment_method_is_required(self):
        self.add_to_cart(self.black_s)
        data = self.checkout_data()
        del data['payment_method']
        response = self.client.post(reverse('orders:checkout'), data)
        self.assertContains(response, 'Please choose a payment method.')
        self.assertFalse(Order.objects.exists())


class CheckoutValidationTests(OrderTestCase):
    def test_required_fields_are_checked_on_the_server(self):
        self.add_to_cart(self.black_s)
        response = self.client.post(reverse('orders:checkout'), {})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Order.objects.exists())
        self.assertContains(response, 'Please correct the highlighted fields.')
        self.assertEqual(self.stock(self.black_s), 5)

    def test_invalid_values_are_rejected(self):
        self.add_to_cart(self.black_s)
        bad_values = {
            'phone': ['12345', 'abcdefghijk', '01312345678', '0101234567'],
            'email': ['not-an-email'],
            'governorate': ['Atlantis', ''],
            'address': ['short'],
            'customer_name': [''],
        }
        for field, values in bad_values.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    response = self.place_order(**{field: value})
                    self.assertEqual(response.status_code, 200)
        self.assertFalse(Order.objects.exists())

    def test_phone_numbers_are_normalised(self):
        for typed in ('+20 101 234 5678', '0020-101-234-5678', '201012345678', '010 1234 5678'):
            with self.subTest(phone=typed):
                self.add_to_cart(self.black_s)
                self.place_order(phone=typed)
                self.assertEqual(Order.objects.latest('pk').phone, '01012345678')

    def test_every_governorate_is_offered(self):
        self.add_to_cart(self.black_s)
        response = self.client.get(reverse('orders:checkout'))
        self.assertContains(response, '<option value="Cairo">', html=False)
        self.assertContains(response, 'South Sinai')
        self.assertEqual(len(response.context['form'].fields['governorate'].choices), 28)


class PlacingAnOrderTests(OrderTestCase):
    def test_a_successful_order_is_saved_with_its_snapshot(self):
        self.add_to_cart(self.black_s, 2)
        self.add_to_cart(self.brown_s, 1)
        response = self.place_order()
        order = Order.objects.get()
        self.assertRedirects(response, reverse('orders:success', args=[order.reference]))

        self.assertEqual(order.user, self.user)
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.payment_method, 'cod')
        self.assertEqual((order.customer_name, order.phone, order.governorate), ('Sara Ali', '01012345678', 'Cairo'))
        self.assertTrue(order.reference.startswith('ZS-'))
        self.assertTrue(order.stock_reserved)

        items = {(item.color_name, item.size_label): item for item in order.items.all()}
        self.assertEqual(set(items), {('Black', 'S'), ('Brown', 'S')})
        black = items[('Black', 'S')]
        self.assertEqual((black.product_name, black.quantity, black.unit_price), ('Classic Jacket', 2, Decimal('850')))
        self.assertEqual(order.subtotal, Decimal('2550'))
        self.assertEqual(order.total, Decimal('2550'))

    @override_settings(SHIPPING_FEE=Decimal('60'), FREE_SHIPPING_THRESHOLD=Decimal('3000'))
    def test_delivery_fee_is_part_of_the_saved_total(self):
        self.add_to_cart(self.black_s, 1)
        self.place_order()
        order = Order.objects.get()
        self.assertEqual((order.subtotal, order.shipping_fee, order.total), (Decimal('850'), Decimal('60'), Decimal('910')))

    @override_settings(SHIPPING_FEE=Decimal('60'), FREE_SHIPPING_THRESHOLD=Decimal('1000'))
    def test_orders_over_the_threshold_ship_free(self):
        self.add_to_cart(self.black_s, 2)
        self.place_order()
        order = Order.objects.get()
        self.assertEqual((order.shipping_fee, order.total), (Decimal('0'), Decimal('1700')))

    def test_stock_is_reduced_for_the_exact_colour_and_size(self):
        self.add_to_cart(self.black_s, 2)
        self.place_order()
        self.assertEqual(self.stock(self.black_s), 3)
        self.assertEqual(self.stock(self.black_m), 3)
        self.assertEqual(self.stock(self.brown_s), 2)

    def test_the_cart_is_emptied_after_ordering(self):
        self.add_to_cart(self.black_s)
        self.place_order()
        self.assertEqual(self.client.session.get('cart', {}), {})

    def test_later_price_changes_do_not_alter_an_existing_order(self):
        self.add_to_cart(self.black_s, 1)
        self.place_order()
        self.product.price = Decimal('1200')
        self.product.name = 'Renamed Jacket'
        self.product.save()
        order = Order.objects.get()
        item = order.items.get()
        self.assertEqual((item.unit_price, item.product_name), (Decimal('850'), 'Classic Jacket'))
        response = self.client.get(order.get_absolute_url())
        self.assertContains(response, 'Classic Jacket')
        self.assertNotContains(response, 'Renamed Jacket')

    def test_the_browser_cannot_choose_the_price_or_total(self):
        self.add_to_cart(self.black_s, 1)
        self.place_order(total='1', subtotal='1', unit_price='1', shipping_fee='-500')
        order = Order.objects.get()
        self.assertEqual(order.total, Decimal('850'))

    def test_confirmation_page_shows_the_reference_and_colour_and_size(self):
        self.add_to_cart(self.black_s, 1)
        response = self.place_order()
        page = self.client.get(response['Location'])
        order = Order.objects.get()
        self.assertContains(page, order.reference)
        self.assertContains(page, 'Black, size S')
        self.assertContains(page, 'Return and exchange shipping costs')


class StockSafetyTests(OrderTestCase):
    def test_not_enough_stock_at_checkout_creates_no_order(self):
        self.add_to_cart(self.black_m, 3)
        self.black_m.stock = 1
        self.black_m.save()
        response = self.place_order()
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Order.objects.exists())
        self.assertEqual(self.stock(self.black_m), 1)

    def test_a_failure_part_way_rolls_everything_back(self):
        """Two lines: the second runs out after the cart was checked."""
        request = RequestFactory().get('/')
        request.session = self.client.session
        cart = Cart(request)
        cart.add(self.black_s, 2)
        cart.add(self.black_m, 3)
        cart.lines()  # the cart was valid when it was last read
        self.black_m.stock = 1
        self.black_m.save()

        with self.assertRaises(OrderError):
            create_order(user=self.user, cart=cart, data=self.checkout_data(), token=uuid.uuid4())

        self.assertFalse(Order.objects.exists())
        self.assertFalse(OrderItem.objects.exists())
        self.assertEqual(self.stock(self.black_s), 5)
        self.assertEqual(self.stock(self.black_m), 1)

    def test_the_last_item_can_only_be_bought_once(self):
        self.black_m.stock = 1
        self.black_m.save()
        request = RequestFactory().get('/')
        request.session = self.client.session
        first_cart = Cart(request)
        first_cart.add(self.black_m, 1)
        second_cart = Cart(request)
        second_cart.lines()
        create_order(user=self.user, cart=first_cart, data=self.checkout_data(), token=uuid.uuid4())
        with self.assertRaises(OrderError):
            create_order(user=self.other, cart=second_cart, data=self.checkout_data(), token=uuid.uuid4())
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(self.stock(self.black_m), 0)

    def test_stock_never_goes_below_zero(self):
        order = self.make_order(quantity=5)
        self.assertEqual(self.stock(self.black_s), 0)
        self.assertEqual(order.items.get().quantity, 5)


class DuplicateSubmissionTests(OrderTestCase):
    def test_submitting_twice_creates_one_order_and_takes_stock_once(self):
        self.add_to_cart(self.black_s, 2)
        first = self.place_order()
        second = self.place_order()
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(self.stock(self.black_s), 3)
        self.assertEqual(second['Location'], reverse('cart:detail'))
        self.assertEqual(first.status_code, 302)

    def test_the_same_checkout_form_cannot_create_two_orders(self):
        token = uuid.uuid4()
        request = RequestFactory().get('/')
        request.session = self.client.session
        cart = Cart(request)
        cart.add(self.black_s, 1)
        first = create_order(user=self.user, cart=cart, data=self.checkout_data(), token=token)
        cart.add(self.black_s, 1)
        with self.assertRaises(DuplicateSubmission) as caught:
            create_order(user=self.user, cart=cart, data=self.checkout_data(), token=token)
        self.assertEqual(caught.exception.order, first)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(self.stock(self.black_s), 4)

    def test_a_new_order_needs_a_new_checkout_form(self):
        self.add_to_cart(self.black_s)
        self.place_order()
        self.add_to_cart(self.black_s)
        self.client.get(reverse('orders:checkout'))
        self.place_order()
        self.assertEqual(Order.objects.count(), 2)
        self.assertEqual(self.stock(self.black_s), 3)


class CancellationTests(OrderTestCase):
    def test_a_customer_can_cancel_a_pending_order_and_the_stock_returns(self):
        order = self.make_order(quantity=2)
        self.assertEqual(self.stock(self.black_s), 3)
        response = self.client.post(reverse('orders:cancel', args=[order.reference]))
        self.assertRedirects(response, order.get_absolute_url())
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertFalse(order.stock_reserved)
        self.assertEqual(self.stock(self.black_s), 5)

    def test_cancelling_twice_gives_the_stock_back_only_once(self):
        order = self.make_order(quantity=2)
        self.client.post(reverse('orders:cancel', args=[order.reference]))
        self.client.post(reverse('orders:cancel', args=[order.reference]))
        self.assertEqual(self.stock(self.black_s), 5)
        self.assertTrue(cancel_order(Order.objects.get()) is False)
        self.assertEqual(self.stock(self.black_s), 5)

    def test_the_service_is_safe_to_call_repeatedly(self):
        order = self.make_order(quantity=3)
        self.assertTrue(cancel_order(order))
        self.assertFalse(cancel_order(order))
        self.assertFalse(cancel_order(order))
        self.assertEqual(self.stock(self.black_s), 5)

    def test_a_customer_cannot_cancel_after_the_store_has_confirmed(self):
        order = self.make_order(quantity=1)
        Order.objects.filter(pk=order.pk).update(status=Order.Status.SHIPPED)
        self.client.post(reverse('orders:cancel', args=[order.reference]))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.SHIPPED)
        self.assertEqual(self.stock(self.black_s), 4)

    def test_cancelling_needs_post(self):
        order = self.make_order()
        self.assertEqual(self.client.get(reverse('orders:cancel', args=[order.reference])).status_code, 405)

    def test_cancelling_does_not_touch_stock_changed_for_other_reasons(self):
        order = self.make_order(quantity=2)
        self.black_s.refresh_from_db()
        self.black_s.stock += 10  # the store restocked meanwhile
        self.black_s.save()
        cancel_order(order)
        self.assertEqual(self.stock(self.black_s), 15)

    def test_an_item_whose_size_was_deleted_does_not_break_cancellation(self):
        order = self.make_order(quantity=1, size=self.brown_s)
        self.brown_s.delete()
        self.assertTrue(cancel_order(order))
        self.assertEqual(order.items.get().size_label, 'S')


class OrderPrivacyTests(OrderTestCase):
    def setUp(self):
        super().setUp()
        self.mine = self.make_order(quantity=1)
        self.theirs = self.make_order(user=self.other, quantity=1, size=self.black_m)

    def test_my_order_list_only_has_my_orders(self):
        response = self.client.get(reverse('orders:list'))
        self.assertContains(response, self.mine.reference)
        self.assertNotContains(response, self.theirs.reference)

    def test_someone_elses_order_pages_are_not_found(self):
        for name in ('orders:detail', 'orders:success', 'orders:cancel'):
            with self.subTest(page=name):
                url = reverse(name, args=[self.theirs.reference])
                response = self.client.post(url) if name == 'orders:cancel' else self.client.get(url)
                self.assertEqual(response.status_code, 404)
        self.theirs.refresh_from_db()
        self.assertEqual(self.theirs.status, Order.Status.PENDING)

    def test_visitors_cannot_open_any_order(self):
        self.client.logout()
        for url in (
            reverse('orders:list'),
            reverse('orders:detail', args=[self.mine.reference]),
            reverse('orders:success', args=[self.mine.reference]),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 302)

    def test_an_unknown_reference_is_not_found(self):
        self.assertEqual(self.client.get(reverse('orders:detail', args=['ZS-NOPE0000'])).status_code, 404)

    def test_references_are_unique_and_not_sequential(self):
        references = {order.reference for order in Order.objects.all()}
        self.assertEqual(len(references), 2)
        self.assertTrue(all(len(ref) == 11 and ref.startswith('ZS-') for ref in references))

    def test_order_detail_shows_the_details_a_customer_needs(self):
        response = self.client.get(self.mine.get_absolute_url())
        self.assertContains(response, 'Black, size S')
        self.assertContains(response, 'Pending')
        self.assertContains(response, 'Cash on delivery')
        self.assertContains(response, 'Cancel this order')
        self.assertContains(response, '12 Nile Street')


class OrderAdminTests(OrderTestCase):
    def setUp(self):
        super().setUp()
        self.staff = User.objects.create_superuser('boss', 'boss@example.com', PASSWORD)
        self.order = self.make_order(quantity=2)
        self.changelist = reverse('admin:orders_order_changelist')
        self.client.logout()

    def test_visitors_and_customers_cannot_open_the_order_admin(self):
        self.assertEqual(self.client.get(self.changelist).status_code, 302)
        self.client.force_login(self.user)
        response = self.client.get(self.changelist)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response['Location'])

    def test_staff_with_the_right_permissions_can_see_orders(self):
        self.client.force_login(self.staff)
        response = self.client.get(self.changelist)
        self.assertContains(response, self.order.reference)
        detail = self.client.get(reverse('admin:orders_order_change', args=[self.order.pk]))
        self.assertContains(detail, 'Classic Jacket')
        self.assertContains(detail, 'Black')

    def test_order_lines_are_read_only_in_the_admin(self):
        self.client.force_login(self.staff)
        detail = self.client.get(reverse('admin:orders_order_change', args=[self.order.pk]))
        self.assertNotContains(detail, 'name="items-0-quantity"')
        self.assertNotContains(detail, 'name="items-0-unit_price"')

    def test_orders_cannot_be_deleted_from_the_admin(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse('admin:orders_order_delete', args=[self.order.pk]))
        self.assertEqual(response.status_code, 403)

    def test_status_actions_update_orders_but_skip_cancelled_ones(self):
        cancelled = self.make_order(quantity=1, size=self.black_m)
        cancel_order(cancelled)
        self.client.force_login(self.staff)
        self.client.post(
            self.changelist,
            {'action': 'mark_shipped', '_selected_action': [self.order.pk, cancelled.pk]},
        )
        self.order.refresh_from_db()
        cancelled.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.SHIPPED)
        self.assertEqual(cancelled.status, Order.Status.CANCELLED)

    def test_payment_can_be_confirmed_from_the_list(self):
        self.client.force_login(self.staff)
        self.client.post(
            self.changelist, {'action': 'mark_payment_confirmed', '_selected_action': [self.order.pk]}
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, Order.PaymentStatus.PAID)

    def test_the_cancel_action_restores_stock_once_even_if_run_twice(self):
        self.client.force_login(self.staff)
        data = {'action': 'cancel_orders', '_selected_action': [self.order.pk]}
        self.client.post(self.changelist, data)
        self.client.post(self.changelist, data)
        self.assertEqual(self.stock(self.black_s), 5)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CANCELLED)

    def test_setting_the_status_to_cancelled_on_the_edit_page_restores_stock(self):
        self.client.force_login(self.staff)
        url = reverse('admin:orders_order_change', args=[self.order.pk])
        item = self.order.items.get()
        data = {
            'status': 'cancelled',
            'payment_method': 'cod',
            'payment_status': 'pending',
            'customer_name': 'Sara Ali',
            'phone': '01012345678',
            'email': 'sara@example.com',
            'governorate': 'Cairo',
            'address': '12 Nile Street, building 4, apartment 9, Cairo',
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '1',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-id': item.pk,
            'items-0-order': self.order.pk,
        }
        self.client.post(url, data)
        self.client.post(url, data)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CANCELLED)
        self.assertEqual(self.stock(self.black_s), 5)

    def test_a_cancelled_order_cannot_be_reopened(self):
        cancel_order(self.order)
        self.order.refresh_from_db()
        form = OrderAdminForm(
            instance=self.order,
            data={
                'status': 'pending',
                'payment_method': 'cod',
                'payment_status': 'pending',
                'customer_name': 'Sara Ali',
                'phone': '01012345678',
                'email': 'sara@example.com',
                'governorate': 'Cairo',
                'address': '12 Nile Street, building 4, apartment 9, Cairo',
            },
        )
        self.assertFalse(form.is_valid())
        self.assertIn('status', form.errors)

    def test_the_order_list_can_be_filtered_and_searched(self):
        self.client.force_login(self.staff)
        for query in ('?status__exact=pending', '?payment_method__exact=cod', f'?q={self.order.reference}', '?q=01012345678'):
            with self.subTest(query=query):
                self.assertContains(self.client.get(self.changelist + query), self.order.reference)
        self.assertNotContains(
            self.client.get(self.changelist + '?status__exact=shipped'), self.order.reference
        )
