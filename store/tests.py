from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import Category, Product, ProductSize
from .views import categories_with_products


def create_product(category, name, price='100', stock=None, **extra):
    """Create a product (with sizes) without needing a real image file."""
    product = Product.objects.create(
        category=category,
        name=name,
        slug=name.lower().replace(' ', '-'),
        price=Decimal(price),
        image=extra.pop('image', 'products/test.jpg'),
        **extra,
    )
    for size, amount in (stock if stock is not None else {'M': 5}).items():
        ProductSize.objects.create(product=product, size=size, stock=amount)
    return product


class ProductModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Jackets', slug='jackets')

    def test_sizes_are_ordered_s_m_l_xl(self):
        product = create_product(
            self.category, 'Coat', stock={'XL': 1, 'S': 1, 'L': 1, 'M': 1}
        )
        self.assertEqual(
            [item.size for item in product.ordered_sizes], ['S', 'M', 'L', 'XL']
        )

    def test_sold_out_sizes_are_not_available(self):
        product = create_product(self.category, 'Coat', stock={'S': 0, 'M': 3})
        self.assertEqual([item.size for item in product.available_sizes], ['M'])
        self.assertTrue(product.is_in_stock)

    def test_product_with_no_stock_is_not_in_stock(self):
        product = create_product(self.category, 'Coat', stock={'S': 0, 'M': 0})
        self.assertFalse(product.is_in_stock)

    def test_absolute_url_uses_slug(self):
        product = create_product(self.category, 'Classic Jacket')
        self.assertEqual(
            product.get_absolute_url(),
            reverse('store:product_detail', kwargs={'slug': 'classic-jacket'}),
        )


class HomeViewTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Jackets', slug='jackets')

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
        self.jackets = Category.objects.create(name='Jackets', slug='jackets')
        self.shirts = Category.objects.create(name='Shirts', slug='shirts')
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
        self.assertEqual(
            list(ascending.context['products']), [self.shirt, self.coat]
        )
        descending = self.client.get(self.url, {'sort': 'price_desc'})
        self.assertEqual(
            list(descending.context['products']), [self.coat, self.shirt]
        )

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
        self.category = Category.objects.create(name='Jackets', slug='jackets')

    def test_shows_product_details(self):
        product = create_product(
            self.category, 'Classic Jacket', price='850.50', stock={'S': 0, 'M': 2}
        )
        response = self.client.get(product.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Classic Jacket')
        self.assertContains(response, 'EGP 850.50')
        self.assertContains(response, '(sold out)')

    def test_inactive_product_returns_404(self):
        product = create_product(self.category, 'Old Coat', is_active=False)
        response = self.client.get(product.get_absolute_url())
        self.assertEqual(response.status_code, 404)

    def test_unknown_slug_returns_404(self):
        response = self.client.get(
            reverse('store:product_detail', kwargs={'slug': 'missing'})
        )
        self.assertEqual(response.status_code, 404)

    def test_sold_out_product_shows_notice(self):
        product = create_product(self.category, 'Coat', stock={'M': 0})
        response = self.client.get(product.get_absolute_url())
        self.assertContains(response, 'currently sold out')


class CategoryCoverTests(TestCase):
    def test_cover_is_the_newest_active_product_image(self):
        category = Category.objects.create(name='Jackets', slug='jackets')
        create_product(category, 'Old Coat', image='products/old.jpg')
        create_product(category, 'New Coat', image='products/new.jpg')
        create_product(
            category, 'Hidden Coat', image='products/hidden.jpg', is_active=False
        )
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
        other = Category.objects.create(name='Shirts', slug='shirts')
        create_product(other, 'Shirt', is_active=False)
        self.assertEqual(categories_with_products(), [])
