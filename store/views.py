
from urllib.parse import urlencode

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db.models import Count, OuterRef, Q, Subquery
from django.shortcuts import get_object_or_404, render

from .constants import RETURN_POLICY
from .models import Category, Product

HOME_SECTION_SIZE = 5
PRODUCTS_PER_PAGE = 12
SEARCH_MAX_LENGTH = 100

SORT_OPTIONS = {
    'newest': ('Newest', '-created_at'),
    'price_asc': ('Price: low to high', 'price'),
    'price_desc': ('Price: high to low', '-price'),
}
DEFAULT_SORT = 'newest'


HERO_BANNER_IMAGE = 'hero/hero-banner.jpg'


def active_products():
    return (
        Product.objects.filter(is_active=True)
        .select_related('category')
        .prefetch_related('colors__sizes', 'colors__images')
    )


def categories_with_products():
    newest_image = (
        Product.objects.filter(category=OuterRef('pk'), is_active=True)
        .order_by('-created_at', '-pk')
        .values('image')[:1]
    )

    categories = list(
        Category.objects.annotate(
            product_count=Count(
                'products',
                filter=Q(products__is_active=True),
            ),
            newest_product_image=Subquery(newest_image),
        ).filter(product_count__gt=0)
    )

    for category in categories:
        cover_name = category.image.name or category.newest_product_image
        category.cover_url = (
            default_storage.url(cover_name) if cover_name else ''
        )

    return categories


def home(request):
    featured_products = list(
        active_products()
        .filter(is_featured=True)
        .order_by('-created_at', '-pk')[:HOME_SECTION_SIZE]
    )

    new_arrivals = list(
        active_products()
        .filter(is_featured=False)
        .order_by('-created_at', '-pk')[:HOME_SECTION_SIZE]
    )

    hero_product = (
        featured_products[0]
        if featured_products
        else new_arrivals[0] if new_arrivals
        else None
    )

    try:
        if default_storage.exists(HERO_BANNER_IMAGE):
            hero_image_url = default_storage.url(HERO_BANNER_IMAGE)
        else:
            hero_image_url = f'{settings.MEDIA_URL}{HERO_BANNER_IMAGE}'
    except Exception:
        hero_image_url = f'{settings.MEDIA_URL}{HERO_BANNER_IMAGE}'

    context = {
        'hero_product': hero_product,
        'hero_image_url': hero_image_url,
        'categories': categories_with_products(),
        'featured_products': featured_products,
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
        (
            category
            for category in categories
            if category.slug == category_slug
        ),
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

    page = Paginator(products, PRODUCTS_PER_PAGE).get_page(
        request.GET.get('page')
    )

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
        'sort_options': [
            (key, label)
            for key, (label, _) in SORT_OPTIONS.items()
        ],
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

    colors = list(product.colors.all())

    selected_color = next(
        (color for color in colors if color.is_in_stock),
        colors[0] if colors else None,
    )

    return render(
        request,
        'store/product_detail.html',
        {
            'product': product,
            'colors': colors,
            'selected_color': selected_color,
            'max_quantity': settings.CART_MAX_QUANTITY,
            'return_policy': RETURN_POLICY,
            'related_products': related_products,
        },
    )
