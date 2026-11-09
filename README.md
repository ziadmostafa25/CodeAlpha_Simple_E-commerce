# nice-store — Premium Clothing E-Commerce

A modern, high-end clothing e-commerce web application built with Python and Django. Designed with a **Quiet Luxury / Modern Minimal** visual identity, nice-store provides a seamless editorial shopping experience with product variants, a session-based shopping cart, secure checkout with Egyptian regional validation, manual transfer and Cash on Delivery workflows, customer order management, and a comprehensive Django administration back-office.

---

## Brand & UI/UX Direction

- **Aesthetic:** Quiet Luxury & Modern Minimal, tailored for premium fashion brands.
- **Palette:**
  - Charcoal (`#292821`)
  - Warm Ivory (`#F8F6F1`)
  - Soft Beige (`#E8E0D5`)
  - Muted Brown (`#A17B55`)
  - Clean White (`#FFFFFF`)
- **Typography:**
  - Headings & Brand: `Cormorant Garamond` (editorial serif)
  - Interface & Body: `Jost` (clean geometric sans-serif)
- **Design Principles:** Generous breathing room, subtle borders (`1px solid #E2DBD0`), 2px crisp tailoring radii, refined hover micro-interactions, responsive editorial hero section with dedicated campaign imagery.

---

## Key Features

### Storefront & Catalogue
- **Editorial Homepage:** Two-column hero featuring dedicated campaign imagery (`media/hero/hero-banner.jpg`), curated category showcases, featured pieces, and new arrivals.
- **Shop & Filtering:** Dynamic category filters, search by title and description, sorting by newest / price asc / price desc, and pagination.
- **Product Details:**
  - Interactive multi-photo gallery per color variant.
  - Live color swatches with dynamic gallery and size switcher.
  - Numeric suit/blazer sizes (48 to 58) with real-time stock indicators and low-stock urgency hints (`Only X left`).
  - Interactive quantity selector and single-submit protected Add-to-Cart.
  - Tailored return and exchange policy transparency.
  - "You may also like" related product recommendations.

### Cart & Checkout
- **Session-based Cart:** Frictionless shopping experience for guest visitors without premature session database bloat.
- **Inventory Protection:** Dynamic pruning and notifications if an item in the cart sells out before checkout.
- **Tailored Checkout:**
  - Egyptian mobile phone validation (Vodafone, Orange, Etisalat, WE).
  - Egyptian governorate selection.
  - Payment methods: **Cash on Delivery (COD)**, **Vodafone Cash**, and **InstaPay** with interactive instruction accordions.
  - Order snapshots preserving unit prices, colors, sizes, and product titles against future catalog changes.
  - Atomic stock reservations and automated restocking on customer cancellation.

### Customer Accounts & Orders
- **Customer Authentication:** Login, registration, and user profile management.
- **Order History:** Complete customer order tracking with status badges (`Pending`, `Processing`, `Shipped`, `Delivered`, `Cancelled`).
- **Customer Self-Service:** Single-click order cancellation while order status is still pending.

### Administration & Operations
- **Django Admin:** Comprehensive catalogue, variant, inventory, and order management dashboard.
- **Custom Admin Actions:** Single-click batch status updates (mark as processing, shipped, delivered, or confirmed payment).

---

## Technology Stack

- **Backend:** Python 3.12+, Django 5.x
- **Frontend:** Semantic HTML5, Modular CSS3 (BEM-inspired custom design system), Vanilla JavaScript (ES6+)
- **Database:** SQLite (development) / PostgreSQL (production via `dj-database-url`)
- **Static & Media Storage:** WhiteNoise (static assets), Cloudinary or Local FileSystem (media)
- **Server / WSGI:** Gunicorn, ASGI/WSGI compatible

---

## Local Installation (Windows PowerShell)

### 1. Clone the repository
```powershell
git clone https://github.com/ziadmostafa25/CodeAlpha_Simple_E-commerce.git
cd CodeAlpha_Simple_E-commerce
```

### 2. Set up virtual environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies
```powershell
pip install -r requirements.txt
```

### 4. Run migrations
```powershell
python manage.py migrate
```

### 5. Create a superuser (for Django Admin)
```powershell
python manage.py createsuperuser
```

### 6. Run the local development server
```powershell
python manage.py runserver
```

Open your browser at [http://127.0.0.1:8000/](http://127.0.0.1:8000/) for the store, and [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/) for the administration portal.

---

## Running the Automated Test Suite

The project includes an extensive test suite covering models, views, cart calculations, checkout flows, security policies, and administrative actions:

```powershell
python manage.py test
```

To run a fast system check:
```powershell
python manage.py check
```

---

## Configuration & Environment Variables

Create a `.env` file in the project root (reference `.env.example`):

| Variable | Description | Default |
|---|---|---|
| `DJANGO_DEBUG` | `1` for development, `0` for production | `1` |
| `DJANGO_SECRET_KEY` | Secret cryptographic key for Django | Built-in dev key |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated list of allowed hostnames | `127.0.0.1,localhost` |
| `DATABASE_URL` | PostgreSQL connection URL | SQLite fallback |
| `nice-store_SHIPPING_FEE` | Flat delivery fee in EGP | `0` (Free delivery) |
| `nice-store_FREE_SHIPPING_THRESHOLD` | Subtotal amount for free shipping qualification | Unset |
| `nice-store_VODAFONE_CASH_NUMBER` | Vodafone Cash merchant wallet number | Displayed at checkout |
| `nice-store_INSTAPAY_ADDRESS` | InstaPay username/address | Displayed at checkout |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary Cloud name (production) | Unset |
| `CLOUDINARY_API_KEY` | Cloudinary API Key (production) | Unset |
| `CLOUDINARY_API_SECRET` | Cloudinary API Secret (production) | Unset |

---

## Project Structure

```
CodeAlpha_Simple_E-commerce/
├── accounts/           # User authentication, profiles, registration
├── cart/               # Session-based cart, cart calculations, line management
├── orders/             # Checkout, order processing, snapshots, payment handlers
├── store/              # Catalogue, categories, products, color variants, sizes
├── templates/          # Responsive Django templates
│   ├── accounts/       # Login, register, profile
│   ├── cart/           # Shopping cart view
│   ├── orders/         # Checkout, order confirmation, detail, history
│   ├── partials/       # Header, footer, logo, field widgets, product cards
│   └── store/          # Homepage, product list, product detail
├── static/             # Static assets
│   ├── css/            # base.css, components.css, pages.css
│   ├── js/             # main.js (swatches, galleries, checkout tabs)
│   └── images/         # Brand logos and payment badges
├── media/              # Uploaded media (products, hero campaign image)
├── nice-store/             # Project settings, URLs, WSGI/ASGI configuration
├── manage.py           # Django management script
└── requirements.txt    # Project dependencies
```

---

## License

This project was developed by Ziad Mostafa as part of the CodeAlpha Full Stack Development Internship. Reusable as a template for clothing and fashion e-commerce applications.
