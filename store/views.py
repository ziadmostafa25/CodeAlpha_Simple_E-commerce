from urllib.parse import urlencode

from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db.models import Count, OuterRef, Q, Subquery
from django.shortcuts import get_object_or_404, render

from .models import Category, Product

HOME_SECTION_SIZE = 4
PRODUCTS_PER_PAGE = 12
SEARCH_MAX_LENGTH = 100

# key -> (label shown in the sort menu, database ordering)
SORT_OPTIONS = {
    'newest': ('Newest', '-created_at'),
    'price_asc': ('Price: low to high', 'price'),
    'price_desc': ('Price: high to low', '-price'),
}
DEFAULT_SORT = 'newest'


def active_products():
    """Products visible in the shop, with the data the templates need."""
    return (
        Product.objects.filter(is_active=True)
        .select_related('category')
        .prefetch_related('sizes')
    )


def categories_with_products():
    """Categories that have active products, each with a cover image URL.

    The cover is the category's own image when it has one, otherwise the
    image of its newest active product.
    """
    newest_image = (
        Product.objects.filter(category=OuterRef('pk'), is_active=True)
        .order_by('-created_at', '-pk')
        .values('image')[:1]
    )
    categories = list(
        Category.objects.annotate(
            product_count=Count('products', filter=Q(products__is_active=True)),
            newest_product_image=Subquery(newest_image),
        ).filter(product_count__gt=0)
    )
    for category in categories:
        cover_name = category.image.name or category.newest_product_image
        category.cover_url = default_storage.url(cover_name) if cover_name else ''
    return categories


def home(request):
    featured = list(active_products().filter(is_featured=True)[:HOME_SECTION_SIZE])
    new_arrivals = list(
        active_products()
        .exclude(pk__in=[product.pk for product in featured])[:HOME_SECTION_SIZE]
    )
    context = {
        'hero_product': next(iter(featured or new_arrivals), None),
        'categories': categories_with_products(),
        'featured_products': featured,
        'new_arrivals': new_arrivals,
    }
    return render(request, 'store/home.html', context)


def product_list(request):
    query = request.GET.get('q', '').strip()[:SEARCH_MAX_LENGTH]
    sort = request.GET.get('sort', DEFAULT_SORT)
    if sort not in SORT_OPTIONS:
        sort = DEFAULT_SORT

    categories = categories_with_products()
    category_slug = request.GET.get('category', '')
    selected_category = next(
        (category for category in categories if category.slug == category_slug),
        None,
    )

    products = active_products()
    if selected_category:
        products = products.filter(category=selected_category)
    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
    products = products.order_by(SORT_OPTIONS[sort][1], '-pk')

    page = Paginator(products, PRODUCTS_PER_PAGE).get_page(request.GET.get('page'))

    # Filters carried over to the pagination links.
    params = {'sort': sort}
    if query:
        params['q'] = query
    if selected_category:
        params['category'] = selected_category.slug

    context = {
        'products': page,
        'total': page.paginator.count,
        'categories': categories,
        'selected_category': selected_category,
        'query': query,
        'sort': sort,
        'sort_options': [(key, label) for key, (label, _) in SORT_OPTIONS.items()],
        'base_query': urlencode(params),
    }
    return render(request, 'store/product_list.html', context)


def product_detail(request, slug):
    product = get_object_or_404(active_products(), slug=slug)
    related_products = (
        active_products()
        .filter(category=product.category)
        .exclude(pk=product.pk)[:HOME_SECTION_SIZE]
    )
    return render(
        request,
        'store/product_detail.html',
        {'product': product, 'related_products': related_products},
    )
