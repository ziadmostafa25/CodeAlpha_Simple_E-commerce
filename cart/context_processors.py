from .cart import CART_SESSION_KEY


def cart(request):
    """Cart item count for the header (reads the session without creating one)."""
    session = getattr(request, 'session', None)
    items = session.get(CART_SESSION_KEY, {}) if session is not None else {}
    return {'cart_item_count': sum(items.values())}
