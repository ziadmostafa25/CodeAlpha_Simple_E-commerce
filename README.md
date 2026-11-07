# Z-Store

A clothing e-commerce store built with Django. Customers browse products by
colour and size, fill a cart, sign in, and place orders paid by cash on
delivery or by a manual transfer (Vodafone Cash, InstaPay). The store owner
manages products, stock and orders in Django Admin.

Built as part of the CodeAlpha Full Stack Development internship.

## Features

- Catalogue: categories, search, sorting, pagination, product pages
- Colour variants: each colour has its own photos, sizes (S to XL) and stock
- Session cart for guests; sign in (or register) to check out
- Checkout for Egypt: mobile number, governorate and address validation
- Payment methods: Cash on delivery, Vodafone Cash, InstaPay (manual transfers,
  confirmed by the store; no payment gateway is integrated)
- Orders keep a snapshot of what was bought, so later price changes never
  alter an old order. Customers see only their own orders and can cancel
  while an order is still pending
- Stock is taken safely when an order is placed and returned exactly once if
  it is cancelled
- Django Admin: products, colours, photos, stock overview, orders and
  status actions

## Requirements

Python 3.12 or newer, and the packages in `requirements.txt` (Django, Pillow).

## Run it on Windows (PowerShell)

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/ for the store and http://127.0.0.1:8000/admin/ to
add categories and products. Uploaded photos are saved in `media/`.

## Run the tests

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

## Settings you control

Nothing is required for local development. Set these as environment
variables when you need them (`.env.example` lists them). In PowerShell:
`$env:ZSTORE_SHIPPING_FEE = "60"` before `python manage.py runserver`.

| Variable | Meaning | Default |
|---|---|---|
| `ZSTORE_SHIPPING_FEE` | Delivery fee in EGP | `0` (free) |
| `ZSTORE_FREE_SHIPPING_THRESHOLD` | Subtotal from which delivery is free | not set |
| `ZSTORE_VODAFONE_CASH_NUMBER` | Number customers transfer to | empty: method shown as unavailable |
| `ZSTORE_INSTAPAY_ADDRESS` | InstaPay address customers transfer to | empty: method shown as unavailable |
| `DJANGO_DEBUG` | `0` in production | `1` |
| `DJANGO_SECRET_KEY` | Required when `DJANGO_DEBUG=0` | development key |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated host names | empty |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Comma-separated origins, e.g. `https://shop.example.com` | empty |
| `DJANGO_HSTS_SECONDS` | HSTS lifetime once HTTPS works | `0` |
| `DJANGO_BEHIND_PROXY` | `1` if a proxy sends `X-Forwarded-Proto` | `0` |

Payment logos: put the official files in `static/images/payments/` named
`vodafone-cash.svg` and `instapay.svg` (`.png` or `.webp` also work). They
appear on the checkout cards automatically.

## Managing the store

1. **Products:** Admin, Products, add a product with its default photo, then
   add its colours (name and colour code).
2. **Colour page:** open a colour with its "Change" link to upload that
   colour's photos and set the stock of every size.
3. **Stock overview:** Admin, Product sizes. Filter by "Out of stock" or "Low".
4. **Orders:** Admin, Orders. Use the actions to confirm, ship or deliver, and
   to confirm a transfer once you have checked it. Cancelling an order
   returns its stock. A cancelled order cannot be reopened.

## Deployment notes

The app is not deployed anywhere. Before going live:

- Set `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS` and
  `DJANGO_CSRF_TRUSTED_ORIGINS`, and serve the site over HTTPS.
- Run `python manage.py collectstatic --noinput`. It copies all static files
  into `staticfiles/`, which your web server must serve at `/static/`.
- Serve `media/` (uploaded photos) from your web server too. Django serves it
  only while `DJANGO_DEBUG=1`.
- SQLite is fine for a small shop on one server. Move to PostgreSQL if you
  need several servers.
- Run `python manage.py check --deploy` with the production variables set.

## Project layout

```
zstore/      project settings and URLs
store/       catalogue: categories, products, colours, sizes, stock
cart/        session cart
orders/      checkout, orders, payment methods, order admin
accounts/    registration, sign in, profile
templates/   HTML (base, partials, one folder per app)
static/      CSS (base, components, pages) and JavaScript (main.js)
```

Never commit `db.sqlite3`, `media/`, `venv/` or `.env` (already in `.gitignore`).
