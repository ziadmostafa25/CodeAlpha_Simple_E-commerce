# NICE-STORE

A modern clothing e-commerce web application built with Python and Django as part of the CodeAlpha Full Stack Development Internship.

NICE-STORE provides customers with a clean shopping experience where they can browse clothing products, explore colour variants, select available sizes, manage their shopping cart, and place orders. Store administrators can manage products, inventory, and customer orders through Django Admin.

## Features

### Storefront
- Product catalogue with categories, search, sorting, and pagination.
- Detailed product pages with product images and colour variants.
- Size selection with size-specific stock availability.
- Featured products and curated homepage sections.
- Related product recommendations.

### Shopping Cart & Checkout
- Session-based shopping cart for guest visitors.
- Quantity management and stock validation.
- Egyptian mobile number and governorate validation.
- Customer address collection.
- Cash on Delivery (COD), Vodafone Cash, and InstaPay payment options.
- Manual payment verification. No online payment gateway is integrated.

### Customer Accounts & Orders
- Customer registration and authentication.
- Customer profile and order history.
- Order details and status tracking.
- Order cancellation when eligible.

### Inventory & Administration
- Product, category, colour variant, and size management.
- Stock tracking and availability validation.
- Order snapshots preserving purchased product details and prices.
- Inventory restoration for eligible cancelled orders.
- Django Admin interface for managing products, inventory, and orders.

## Technology Stack

- **Backend:** Python 3.14, Django 6.1.1
- **Frontend:** HTML5, CSS3, JavaScript (ES6+)
- **Database:** SQLite (local development), PostgreSQL (production configuration)
- **Database Configuration:** dj-database-url
- **Image Processing:** Pillow
- **Media Storage:** Local FileSystem (development), Cloudinary (production configuration)
- **Static Files:** WhiteNoise
- **Production Server:** Gunicorn
- **Version Control:** Git and GitHub

## Requirements

- Python 3.12 or newer
- Git
- Packages listed in `requirements.txt`

## Local Installation (Windows PowerShell)

### 1. Clone the repository

```powershell
git clone https://github.com/ziadmostafa25/CodeAlpha_Simple_E-commerce.git
cd CodeAlpha_Simple_E-commerce
```

### 2. Create and activate a virtual environment

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Apply database migrations

```powershell
python manage.py migrate
```

### 5. Create an administrator account

```powershell
python manage.py createsuperuser
```

### 6. Start the development server

```powershell
python manage.py runserver
```

Open the following addresses:

- **Storefront:** http://127.0.0.1:8000/
- **Admin Dashboard:** http://127.0.0.1:8000/admin/

During local development, uploaded media files are stored in the local `media/` directory.

## Running Tests

Run the following commands to check the project and execute its automated test suite:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

## Environment Variables

The project uses environment variables for configuration.

The `.env.example` file provides a reference template. It is not loaded automatically by Django; configure the variables directly in your environment or hosting provider.

| Variable | Purpose |
|---|---|
| `DJANGO_DEBUG` | Enables or disables debug mode |
| `DJANGO_SECRET_KEY` | Django secret key; required for production |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed hostnames |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Trusted HTTPS origins |
| `DJANGO_SSL_REDIRECT` | Controls HTTPS redirection |
| `DJANGO_HSTS_SECONDS` | HSTS duration |
| `DJANGO_BEHIND_PROXY` | Enables proxy HTTPS handling when required |
| `DATABASE_URL` | PostgreSQL database connection URL |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary cloud name |
| `CLOUDINARY_API_KEY` | Cloudinary API key |
| `CLOUDINARY_API_SECRET` | Cloudinary API secret |
| `ZSTORE_SHIPPING_FEE` | Delivery fee in EGP |
| `ZSTORE_FREE_SHIPPING_THRESHOLD` | Order subtotal required for free delivery |
| `ZSTORE_VODAFONE_CASH_NUMBER` | Vodafone Cash payment number |
| `ZSTORE_INSTAPAY_ADDRESS` | InstaPay payment address |

See `.env.example` for the configuration template.

**Security:** Never commit `.env` files, production credentials, secret keys, API credentials, or database passwords.

## Managing the Store

1. **Products:** Create and manage products through Django Admin.
2. **Categories:** Organize products into categories.
3. **Colour Variants:** Configure product colours and their associated images.
4. **Sizes & Inventory:** Set available sizes and stock quantities.
5. **Orders:** Review customer orders and update their statuses.
6. **Payments:** Review and verify manual payment transfers.

## Deployment

The project includes configuration for production deployment using:

- **Render:** Web application hosting.
- **Neon / PostgreSQL:** Production database.
- **Cloudinary:** Product image and media storage.
- **WhiteNoise:** Static file serving.
- **Gunicorn:** Production application server.

Before deployment:

1. Configure the required production environment variables.
2. Set `DJANGO_DEBUG=0`.
3. Generate and configure a secure `DJANGO_SECRET_KEY`.
4. Configure allowed hosts and trusted CSRF origins.
5. Set up PostgreSQL through `DATABASE_URL`.
6. Configure Cloudinary credentials.
7. Run database migrations:

```bash
python manage.py migrate
```

8. Collect static files:

```bash
python manage.py collectstatic --noinput
```

9. Run Django deployment checks:

```bash
python manage.py check --deploy
```

**Deployment Status:** Production configuration is included in the project, but hosting, database, storage credentials, and production environment variables must be configured before public deployment.

Free hosting services may sleep after inactivity and may not be suitable for uninterrupted commercial order processing.

## Project Structure

```text
CodeAlpha_Simple_E-commerce/
│
├── accounts/       # Authentication and customer accounts
├── cart/           # Shopping cart functionality
├── orders/         # Checkout, orders, and payment workflows
├── store/          # Products, categories, variants, and inventory
├── templates/      # Django HTML templates
├── static/         # CSS, JavaScript, and static assets
├── zstore/         # Django settings, URLs, and configuration
├── manage.py
├── requirements.txt
├── .env.example
└── README.md
```

## Developer

**Ziad Mostafa**

Computer Science and Information Systems Graduate  
Modern Academy — 2026

GitHub: https://github.com/ziadmostafa25

---

Developed as part of the CodeAlpha Full Stack Development Internship.

Never commit `db.sqlite3`, `media/`, `venv/`, `.env`, or production credentials.