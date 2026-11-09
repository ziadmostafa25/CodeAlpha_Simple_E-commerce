from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from .models import Category, ColorImage, Product, ProductColor, ProductSize
from .testing import create_category, create_product, get_size
from .views import categories_with_products


class ProductModelTests(TestCase):
    def setUp(self):
        self.category = create_category()

    def test_sizes_are_ordered_numerically(self):
        product = create_product(
            self.category, 'Coat', stock={'54': 1, '48': 1, '52': 1, '50': 1}
        )
        color = product.colors.get()
        self.assertEqual([item.size for item in color.ordered_sizes], ['48', '50', '52', '54'])

    def test_sold_out_sizes_are_not_available(self):
        product = create_product(self.category, 'Coat', stock={'48': 0, '50': 3})
        self.assertEqual(product.available_sizes, ['50'])
        self.assertTrue(product.is_in_stock)

    def test_product_with_no_stock_is_not_in_stock(self):
        product = create_product(self.category, 'Coat', stock={'48': 0, '50': 0})
        self.assertFalse(product.is_in_stock)

    def test_product_without_colours_is_not_in_stock(self):
        product = create_product(self.category, 'Coat', colors={})
        self.assertFalse(product.is_in_stock)

    def test_absolute_url_uses_slug(self):
        product = create_product(self.category, 'Classic Jacket')
        self.assertEqual(
            product.get_absolute_url(),
            reverse('store:product_detail', kwargs={'slug': 'classic-jacket'}),
        )


class ColourVariantTests(TestCase):
    def setUp(self):
        self.category = create_category()
        self.product = create_product(
            self.category,
            'Classic Jacket',
            colors={
                'Black': {'48': 5, '50': 3, '52': 0},
                'Brown': {'48': 2, '50': 0, '52': 4},
                'Beige': {'48': 0, '50': 0, '52': 0},
            },
        )

    def test_each_colour_keeps_its_own_stock(self):
        self.assertEqual(get_size(self.product, '48', 'Black').stock, 5)
        self.assertEqual(get_size(self.product, '48', 'Brown').stock, 2)
        self.assertEqual(get_size(self.product, '52', 'Beige').stock, 0)

    def test_product_sizes_combine_every_colour_that_has_stock(self):
        self.assertEqual(self.product.available_sizes, ['48', '50', '52'])

    def test_a_colour_with_no_stock_is_sold_out(self):
        colors = {color.name: color for color in self.product.colors.all()}
        self.assertTrue(colors['Black'].is_in_stock)
        self.assertFalse(colors['Beige'].is_in_stock)

    def test_gallery_falls_back_to_the_product_image(self):
        black = self.product.colors.get(name='Black')
        self.assertEqual(black.gallery_urls, ['/media/products/test.jpg'])

    def test_gallery_uses_only_that_colours_images(self):
        black = self.product.colors.get(name='Black')
        brown = self.product.colors.get(name='Brown')
        ColorImage.objects.create(color=black, image='products/colors/black-1.jpg', sort_order=1)
        ColorImage.objects.create(color=black, image='products/colors/black-2.jpg', sort_order=2)
        ColorImage.objects.create(color=brown, image='products/colors/brown-1.jpg')
        self.assertEqual(
            black.gallery_urls,
            ['/media/products/colors/black-1.jpg', '/media/products/colors/black-2.jpg'],
        )
        self.assertEqual(brown.gallery_urls, ['/media/products/colors/brown-1.jpg'])

    def test_colour_code_must_be_a_hex_value(self):
        color = ProductColor(product=self.product, name='Odd', hex_code='red')
        with self.assertRaises(ValidationError):
            color.full_clean()

    def test_a_size_cannot_repeat_inside_one_colour(self):
        black = self.product.colors.get(name='Black')
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProductSize.objects.create(color=black, size='48', stock=1)

    def test_the_same_size_can_exist_in_two_colours(self):
        self.assertEqual(
            ProductSize.objects.filter(color__product=self.product, size='48').count(), 3
        )

    def test_a_colour_name_cannot_repeat_for_one_product(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProductColor.objects.create(product=self.product, name='Black')

    def test_product_page_shows_swatches_and_a_size_group_for_each_colour(self):
        response = self.client.get(self.product.get_absolute_url())
        self.assertContains(response, 'data-color-input', count=3)
        self.assertContains(response, 'data-sizes-for', count=3)
        self.assertContains(response, 'Black')
        self.assertContains(response, 'Brown')

    def test_sold_out_colour_and_size_are_disabled_and_labelled(self):
        response = self.client.get(self.product.get_absolute_url())
        self.assertContains(response, 'Beige (sold out)')
        self.assertContains(response, '(sold out)')

    def test_product_page_starts_on_the_first_colour_with_stock(self):
        create_product(
            self.category,
            'Second',
            colors={'Black': {'48': 0}, 'Brown': {'48': 3}},
        )
        response = self.client.get(reverse('store:product_detail', kwargs={'slug': 'second'}))
        self.assertEqual(response.context['selected_color'].name, 'Brown')


class HomeViewTests(TestCase):
    def setUp(self):
        self.category = create_category()

    def test_empty_shop_shows_message(self):
        response = self.client.get(reverse('store:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'The shop is being stocked')

    def test_active_product_is_listed_and_inactive_is_hidden(self):
        create_product(self.category, 'Visible Coat')
        create_product(self.category, 'Hidden Coat', is_active=False)
        response = self.client.get(reverse('store:home'))
        self.assertContains(response, 'Visible Coat')
        self.assertNotContains(response, 'Hidden Coat')

    def test_featured_product_is_not_repeated_in_new_arrivals(self):
        create_product(self.category, 'Star Coat', is_featured=True)
        response = self.client.get(reverse('store:home'))
        self.assertEqual(len(response.context['featured_products']), 1)
        self.assertEqual(response.context['new_arrivals'], [])


class ProductListViewTests(TestCase):
    def setUp(self):
        self.jackets = create_category('Jackets')
        self.shirts = create_category('Shirts')
        self.coat = create_product(self.jackets, 'Wool Coat', price='900')
        self.shirt = create_product(self.shirts, 'Linen Shirt', price='300')
        self.url = reverse('store:product_list')

    def test_lists_all_active_products(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total'], 2)

    def test_filters_by_category(self):
        response = self.client.get(self.url, {'category': 'shirts'})
        self.assertEqual(list(response.context['products']), [self.shirt])

    def test_unknown_category_is_ignored(self):
        response = self.client.get(self.url, {'category': 'nope'})
        self.assertEqual(response.context['total'], 2)

    def test_search_matches_name(self):
        response = self.client.get(self.url, {'q': 'linen'})
        self.assertEqual(list(response.context['products']), [self.shirt])

    def test_search_with_no_match_shows_empty_state(self):
        response = self.client.get(self.url, {'q': 'zzz'})
        self.assertContains(response, 'No products match your search.')

    def test_sorts_by_price(self):
        ascending = self.client.get(self.url, {'sort': 'price_asc'})
        self.assertEqual(list(ascending.context['products']), [self.shirt, self.coat])
        descending = self.client.get(self.url, {'sort': 'price_desc'})
        self.assertEqual(list(descending.context['products']), [self.coat, self.shirt])

    def test_invalid_sort_falls_back_to_default(self):
        response = self.client.get(self.url, {'sort': 'drop table'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['sort'], 'newest')

    def test_paginates_twelve_per_page(self):
        for number in range(11):
            create_product(self.jackets, f'Extra {number}')
        first = self.client.get(self.url)
        second = self.client.get(self.url, {'page': 2})
        self.assertEqual(len(first.context['products']), 12)
        self.assertEqual(len(second.context['products']), 1)

    def test_invalid_page_does_not_crash(self):
        response = self.client.get(self.url, {'page': 'abc'})
        self.assertEqual(response.status_code, 200)


class ProductDetailViewTests(TestCase):
    def setUp(self):
        self.category = create_category()

    def test_shows_product_details(self):
        product = create_product(
            self.category, 'Classic Jacket', price='850.50', stock={'48': 0, '50': 2}
        )
        response = self.client.get(product.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Classic Jacket')
        self.assertContains(response, 'EGP 850.50')
        self.assertContains(response, '(sold out)')

    def test_inactive_product_returns_404(self):
        product = create_product(self.category, 'Old Coat', is_active=False)
        self.assertEqual(self.client.get(product.get_absolute_url()).status_code, 404)

    def test_unknown_slug_returns_404(self):
        response = self.client.get(reverse('store:product_detail', kwargs={'slug': 'missing'}))
        self.assertEqual(response.status_code, 404)

    def test_sold_out_product_shows_notice_and_no_purchase_form(self):
        product = create_product(self.category, 'Coat', stock={'50': 0})
        response = self.client.get(product.get_absolute_url())
        self.assertContains(response, 'currently sold out')
        self.assertNotContains(response, 'data-purchase')

    def test_purchase_form_posts_to_the_cart_and_has_csrf(self):
        product = create_product(self.category, 'Coat')
        response = self.client.get(product.get_absolute_url())
        self.assertContains(response, 'data-purchase')
        self.assertContains(response, 'csrfmiddlewaretoken')
        self.assertContains(response, reverse('cart:add'))

    def test_return_policy_is_shown(self):
        product = create_product(self.category, 'Coat')
        response = self.client.get(product.get_absolute_url())
        self.assertContains(response, 'Return and exchange shipping costs are paid by the customer.')


class CategoryCoverTests(TestCase):
    def test_cover_is_the_newest_active_product_image(self):
        category = create_category()
        create_product(category, 'Old Coat', image='products/old.jpg')
        create_product(category, 'New Coat', image='products/new.jpg')
        create_product(category, 'Hidden Coat', image='products/hidden.jpg', is_active=False)
        [result] = categories_with_products()
        self.assertEqual(result.cover_url, '/media/products/new.jpg')

    def test_category_image_wins_over_product_image(self):
        category = Category.objects.create(
            name='Jackets', slug='jackets', image='categories/jackets.jpg'
        )
        create_product(category, 'Coat', image='products/coat.jpg')
        response = self.client.get(reverse('store:home'))
        self.assertContains(response, '/media/categories/jackets.jpg')

    def test_categories_without_active_products_are_hidden(self):
        Category.objects.create(name='Empty', slug='empty')
        other = create_category('Shirts')
        create_product(other, 'Shirt', is_active=False)
        self.assertEqual(categories_with_products(), [])


class SiteChromeTests(TestCase):
    """Header, footer and hero behave as designed on every page."""

    def setUp(self):
        self.category = create_category()
        self.product = create_product(self.category, 'Classic Jacket')
        self.pages = [
            reverse('store:home'),
            reverse('store:product_list'),
            self.product.get_absolute_url(),
            reverse('cart:detail'),
        ]

    def test_header_has_all_main_links(self):
        for url in self.pages:
            response = self.client.get(url)
            for label in ('>Home<', '>Shop<', '>New Arrivals<', '>Categories<'):
                self.assertContains(response, label)

    def test_header_links_to_account_and_cart(self):
        response = self.client.get(reverse('store:home'))
        self.assertContains(response, reverse('accounts:login'))
        self.assertContains(response, reverse('cart:detail'))

    def test_no_announcement_bar_and_no_payment_text_outside_checkout(self):
        for url in self.pages:
            response = self.client.get(url)
            self.assertNotContains(response, 'announcement')
            self.assertNotContains(response, 'Vodafone')
            self.assertNotContains(response, 'InstaPay')
            self.assertNotContains(response, 'Cash on delivery')

    def test_wordmark_is_split_into_two_colours(self):
        response = self.client.get(reverse('store:home'))
        self.assertContains(response, 'logo-word-z')
        self.assertContains(response, 'logo-word-store')

    def test_current_page_is_marked_in_the_navigation(self):
        home = self.client.get(reverse('store:home'))
        self.assertContains(home, 'aria-current="page">Home<')
        newest = self.client.get(reverse('store:product_list'), {'sort': 'newest'})
        self.assertContains(newest, 'aria-current="page">New Arrivals<')

    def test_hero_uses_dedicated_hero_banner_image(self):
        featured = create_product(
            self.category, 'Hero Coat', is_featured=True, image='products/hero.jpg'
        )
        response = self.client.get(reverse('store:home'))
        self.assertEqual(response.context['hero_product'], featured)
        self.assertContains(response, 'hero/hero-banner.jpg')

    def test_cart_count_in_header_follows_the_cart(self):
        size = get_size(self.product, '50')
        self.client.post(reverse('cart:add'), {'size': size.pk, 'quantity': 2})
        response = self.client.get(reverse('store:home'))
        self.assertContains(response, 'aria-label="Cart, 2 items"')


class RoutingTests(TestCase):
    def setUp(self):
        self.category = create_category()
        self.product = create_product(self.category, 'Classic Jacket')

    def test_public_pages_respond(self):
        for url in (
            reverse('store:home'),
            reverse('store:product_list'),
            self.product.get_absolute_url(),
            reverse('cart:detail'),
            reverse('accounts:login'),
            reverse('accounts:register'),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_private_pages_send_visitors_to_sign_in(self):
        for url in (
            reverse('accounts:profile'),
            reverse('orders:list'),
            reverse('orders:checkout'),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(
                    response, f"{reverse('accounts:login')}?next={url}", fetch_redirect_response=False
                )

    def test_unknown_pages_show_the_branded_404_page(self):
        response = self.client.get('/no-such-page/')
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'Page not found', status_code=404)
        self.assertContains(response, 'logo-word-z', status_code=404)


class StoreAdminTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser('boss', 'boss@example.com', 'pass-12345')
        self.product = create_product(
            create_category(), 'Classic Jacket', colors={'Black': {'48': 5, '50': 0}}
        )

    def test_staff_can_open_the_catalogue_pages(self):
        self.client.force_login(self.admin)
        color = self.product.colors.get()
        for url in (
            reverse('admin:store_product_changelist'),
            reverse('admin:store_product_change', args=[self.product.pk]),
            reverse('admin:store_productcolor_changelist'),
            reverse('admin:store_productcolor_change', args=[color.pk]),
            reverse('admin:store_productsize_changelist'),
            reverse('admin:store_productsize_changelist') + '?stock_level=out',
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_product_list_shows_total_stock_across_colours(self):
        create_product(create_category(), 'Other', colors={'Black': {'48': 2}, 'Brown': {'48': 3}})
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin:store_product_changelist'))
        self.assertContains(response, '<td class="field-total_stock">5</td>', count=2)

    def test_catalogue_admin_is_closed_to_the_public(self):
        response = self.client.get(reverse('admin:store_product_changelist'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response['Location'])

