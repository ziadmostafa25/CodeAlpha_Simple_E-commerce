from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from store.testing import create_category, create_product, get_size

from .cart import CART_SESSION_KEY


class CartTestCase(TestCase):
    def setUp(self):
        self.category = create_category()
        self.product = create_product(
            self.category,
            'Classic Jacket',
            price='850',
            colors={'Black': {'48': 5, '50': 3, '52': 0}, 'Brown': {'48': 2}},
        )
        self.black_s = get_size(self.product, '48', 'Black')
        self.black_m = get_size(self.product, '50', 'Black')
        self.black_l = get_size(self.product, '52', 'Black')
        self.brown_s = get_size(self.product, '48', 'Brown')

    def add(self, size, quantity=1, **extra):
        return self.client.post(
            reverse('cart:add'), {'size': size.pk, 'quantity': quantity, **extra}
        )

    def stored_cart(self):
        return self.client.session.get(CART_SESSION_KEY, {})

    def messages_of(self, response):
        return [str(message) for message in response.context['messages']] if response.context else []


class AddToCartTests(CartTestCase):
    def test_adding_a_colour_and_size_creates_one_line(self):
        response = self.add(self.black_s, 2)
        self.assertRedirects(response, reverse('cart:detail'))
        self.assertEqual(self.stored_cart(), {str(self.black_s.pk): 2})

    def test_the_same_variant_is_never_duplicated(self):
        self.add(self.black_s, 1)
        self.add(self.black_s, 2)
        self.assertEqual(self.stored_cart(), {str(self.black_s.pk): 3})

    def test_different_colours_of_the_same_size_are_separate_lines(self):
        self.add(self.black_s)
        self.add(self.brown_s)
        self.assertEqual(len(self.stored_cart()), 2)

    def test_a_size_is_required(self):
        response = self.client.post(reverse('cart:add'), {'quantity': 1}, follow=True)
        self.assertEqual(self.stored_cart(), {})
        self.assertContains(response, 'Please choose a size.')

    def test_unknown_size_is_rejected(self):
        response = self.client.post(reverse('cart:add'), {'size': 99999, 'quantity': 1}, follow=True)
        self.assertEqual(self.stored_cart(), {})
        self.assertContains(response, 'Please choose a valid size.')

    def test_invalid_quantities_are_rejected(self):
        for quantity in ('0', '-1', 'abc', ''):
            with self.subTest(quantity=quantity):
                self.add(self.black_s, quantity)
                self.assertEqual(self.stored_cart(), {})

    def test_cannot_add_more_than_the_stock(self):
        response = self.add(self.black_m, 4, next=self.product.get_absolute_url())
        self.assertRedirects(response, self.product.get_absolute_url())
        self.assertEqual(self.stored_cart(), {})

    def test_stock_limit_applies_to_the_total_of_repeated_adds(self):
        self.add(self.black_m, 2)
        self.add(self.black_m, 2)
        self.assertEqual(self.stored_cart(), {str(self.black_m.pk): 2})

    def test_a_sold_out_size_cannot_be_added(self):
        self.add(self.black_l, 1)
        self.assertEqual(self.stored_cart(), {})

    def test_an_inactive_product_cannot_be_added(self):
        self.product.is_active = False
        self.product.save()
        self.add(self.black_s)
        self.assertEqual(self.stored_cart(), {})

    @override_settings(CART_MAX_QUANTITY=3)
    def test_per_item_limit_is_configurable(self):
        self.add(self.black_s, 4)
        self.assertEqual(self.stored_cart(), {})
        self.add(self.black_s, 3)
        self.assertEqual(self.stored_cart(), {str(self.black_s.pk): 3})

    def test_adding_requires_post(self):
        self.assertEqual(self.client.get(reverse('cart:add')).status_code, 405)

    def test_open_redirects_are_ignored(self):
        response = self.add(self.black_l, 1, next='https://evil.example/')
        self.assertRedirects(response, reverse('store:product_list'), fetch_redirect_response=False)


class UpdateAndRemoveTests(CartTestCase):
    def test_quantity_can_be_changed(self):
        self.add(self.black_s, 1)
        self.client.post(reverse('cart:update'), {'size': self.black_s.pk, 'quantity': 4})
        self.assertEqual(self.stored_cart(), {str(self.black_s.pk): 4})

    def test_quantity_above_stock_is_refused_and_keeps_the_old_value(self):
        self.add(self.black_m, 1)
        self.client.post(reverse('cart:update'), {'size': self.black_m.pk, 'quantity': 9})
        self.assertEqual(self.stored_cart(), {str(self.black_m.pk): 1})

    def test_quantity_zero_removes_the_line(self):
        self.add(self.black_s, 2)
        self.client.post(reverse('cart:update'), {'size': self.black_s.pk, 'quantity': 0})
        self.assertEqual(self.stored_cart(), {})

    def test_negative_or_text_quantities_are_refused(self):
        self.add(self.black_s, 2)
        for quantity in ('-3', 'x'):
            self.client.post(reverse('cart:update'), {'size': self.black_s.pk, 'quantity': quantity})
        self.assertEqual(self.stored_cart(), {str(self.black_s.pk): 2})

    def test_remove_deletes_only_that_line(self):
        self.add(self.black_s)
        self.add(self.brown_s)
        self.client.post(reverse('cart:remove'), {'size': self.black_s.pk})
        self.assertEqual(self.stored_cart(), {str(self.brown_s.pk): 1})

    def test_removing_something_not_in_the_cart_is_harmless(self):
        response = self.client.post(reverse('cart:remove'), {'size': 12345})
        self.assertRedirects(response, reverse('cart:detail'))

    def test_update_and_remove_require_post(self):
        self.assertEqual(self.client.get(reverse('cart:update')).status_code, 405)
        self.assertEqual(self.client.get(reverse('cart:remove')).status_code, 405)


class CartPageTests(CartTestCase):
    def test_empty_cart_shows_an_empty_state(self):
        response = self.client.get(reverse('cart:detail'))
        self.assertContains(response, 'Your cart is empty.')

    def test_lines_show_colour_size_price_quantity_and_totals(self):
        self.add(self.black_s, 2)
        self.add(self.brown_s, 1)
        response = self.client.get(reverse('cart:detail'))
        self.assertContains(response, 'Black, size 48')
        self.assertContains(response, 'Brown, size 48')
        self.assertContains(response, 'EGP 1700')
        self.assertContains(response, 'EGP 2550')
        cart = response.context['cart']
        self.assertEqual(cart.subtotal, Decimal('2550'))
        self.assertEqual(cart.count, 3)

    def test_prices_always_come_from_the_database(self):
        self.add(self.black_s, 1)
        self.product.price = Decimal('900')
        self.product.save()
        response = self.client.get(reverse('cart:detail'))
        self.assertEqual(response.context['cart'].subtotal, Decimal('900'))

    def test_a_price_sent_by_the_browser_is_ignored(self):
        self.add(self.black_s, 1, price='1', unit_price='1', total='1')
        response = self.client.get(reverse('cart:detail'))
        self.assertEqual(response.context['cart'].subtotal, Decimal('850'))

    def test_a_line_that_lost_its_stock_is_flagged_and_blocks_checkout(self):
        self.add(self.black_m, 3)
        self.black_m.stock = 1
        self.black_m.save()
        response = self.client.get(reverse('cart:detail'))
        self.assertContains(response, 'Only 1 left.')
        self.assertTrue(response.context['cart'].has_issues)
        self.assertNotContains(response, reverse('orders:checkout'))

    def test_hidden_products_are_removed_from_the_cart(self):
        self.add(self.black_s, 1)
        self.product.is_active = False
        self.product.save()
        response = self.client.get(reverse('cart:detail'))
        self.assertContains(response, 'no longer available')
        self.assertEqual(self.stored_cart(), {})

    def test_forms_carry_csrf_tokens(self):
        self.add(self.black_s, 1)
        response = self.client.get(reverse('cart:detail'))
        self.assertContains(response, 'csrfmiddlewaretoken', count=2)


class ShippingTests(CartTestCase):
    def totals(self):
        return self.client.get(reverse('cart:detail')).context['cart']

    def test_delivery_is_free_until_a_fee_is_configured(self):
        self.add(self.black_s, 1)
        cart = self.totals()
        self.assertEqual(cart.shipping, Decimal('0.00'))
        self.assertEqual(cart.total, Decimal('850'))

    @override_settings(SHIPPING_FEE=Decimal('60'), FREE_SHIPPING_THRESHOLD=None)
    def test_flat_fee_is_added_to_the_total(self):
        self.add(self.black_s, 1)
        cart = self.totals()
        self.assertEqual(cart.shipping, Decimal('60.00'))
        self.assertEqual(cart.total, Decimal('910.00'))

    @override_settings(SHIPPING_FEE=Decimal('60'), FREE_SHIPPING_THRESHOLD=Decimal('1000'))
    def test_free_delivery_threshold(self):
        self.add(self.black_s, 1)
        self.assertEqual(self.totals().shipping, Decimal('60.00'))
        self.add(self.black_s, 1)
        cart = self.totals()
        self.assertEqual(cart.subtotal, Decimal('1700'))
        self.assertEqual(cart.shipping, Decimal('0.00'))

    @override_settings(SHIPPING_FEE=Decimal('60'))
    def test_an_empty_cart_has_no_delivery_fee(self):
        self.assertEqual(self.totals().shipping, Decimal('0.00'))


class GuestCartTests(CartTestCase):
    def test_a_guest_cart_survives_signing_in(self):
        from django.contrib.auth import get_user_model

        get_user_model().objects.create_user('sara', 'sara@example.com', 'pass-12345')
        self.add(self.black_s, 2)
        self.client.post(reverse('accounts:login'), {'username': 'sara', 'password': 'pass-12345'})
        self.assertEqual(self.stored_cart(), {str(self.black_s.pk): 2})

    def test_browsing_does_not_create_a_session(self):
        self.client.get(reverse('store:home'))
        self.assertNotIn('sessionid', self.client.cookies)


