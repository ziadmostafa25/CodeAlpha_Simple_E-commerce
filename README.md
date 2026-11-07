# Z-Store

A modern clothing e-commerce web application built with Django as part of the CodeAlpha Full Stack Development Internship.

Z-Store allows customers to browse clothing products, choose colour and size variants, manage a shopping cart, and place orders. Store administrators can manage products, inventory, and orders through Django Admin.

## Features

- Product catalogue with categories, search, sorting, and pagination.
- Colour variants with individual photos, sizes (S to XL), and stock quantities.
- Session-based shopping cart for guest visitors.
- User registration, sign-in, and customer order history.
- Checkout with Egyptian mobile number, governorate, and address validation.
- Cash on Delivery, Vodafone Cash, and InstaPay manual payment methods.
- Order snapshots preserve purchased prices and product details.
- Safe inventory updates when orders are placed or cancelled.
- Django Admin dashboard for products, stock, and order management.

## Technology Stack

- Python
- Django
- HTML5 and CSS3
- JavaScript
- SQLite for local development
- PostgreSQL for production
- Cloudinary for production media storage
- WhiteNoise for static files
- Gunicorn for production serving

## Requirements

- Python 3.12 or newer
- Git
- Packages listed in requirements.txt

## Local Installation (Windows PowerShell)

Clone the repository:

```powershell
git clone https://github.com/ziadmostafa25/CodeAlpha_Simple_E-commerce.git
cd CodeAlpha_Simple_E-commerce
