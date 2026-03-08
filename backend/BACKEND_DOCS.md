# Backend Documentation — Django REST API

## Tech Stack

| Package | Version | Purpose |
|---|---|---|
| Django | 3.2.4 | Core framework |
| Django REST Framework | 3.12.4 | REST API layer |
| djangorestframework-simplejwt | 4.7.1 | JWT authentication |
| django-cors-headers | 3.7.0 | CORS support |
| Stripe | 2.60.0 | Payment processing |
| Pillow | 8.3.1 | Image uploads |
| SQLite | built-in | Database |

---

## Folder Structure

```
backend/
├── manage.py              # Entry point — CLI for running server, migrations, etc.
├── db.sqlite3             # SQLite database file
├── requirements.txt       # Python dependencies
├── static/images/         # Media root — user-uploaded product images
│
├── my_project/            # Project configuration package
│   ├── settings.py        # All project settings
│   ├── urls.py            # Root URL router
│   ├── wsgi.py            # WSGI server entry point (production)
│   └── asgi.py            # ASGI server entry point (async support)
│
├── account/               # App: User auth, addresses, orders
├── product/               # App: Product CRUD
└── payments/              # App: Stripe payment integration
```

---

## Entry Point

- **Development server:** `python manage.py runserver`
- **`manage.py`** bootstraps Django by pointing to `my_project.settings` then delegates to Django's CLI.
- **WSGI entry point:** `my_project.wsgi.application` (used by Gunicorn/uWSGI in production)
- **Root URL config** is declared in `settings.py` as `ROOT_URLCONF = 'my_project.urls'`

---

## How Routing Works

Django uses a two-level URL routing pattern — a root router delegates to each app's own `urls.py`.

### Root `my_project/urls.py`

```python
urlpatterns = [
    path('admin/',    admin.site.urls),
    path('api/',      include('product.urls')),   # → /api/products/, etc.
    path('payments/', include('payments.urls')),  # → /payments/charge-customer/, etc.
    path('account/',  include('account.urls')),   # → /account/login/, etc.
]
```

Media files are also served in dev mode:
```python
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

---

## Apps & Their Responsibilities

### 1. `account/` — User, Address & Orders

| File | Task |
|---|---|
| `models.py` | Defines `StripeModel`, `BillingAddress`, `OrderModel` |
| `serializers.py` | Converts models ↔ JSON; generates JWT tokens on registration |
| `views.py` | APIView classes for register/login/profile/addresses/orders |
| `urls.py` | Maps URLs to views |
| `admin.py` | Registers models for Django admin panel |
| `migrations/` | DB schema migration history (50 files) |

**Key Endpoints (`/account/`)**

| Method | URL | Action |
|---|---|---|
| POST | `register/` | Register new user |
| POST | `login/` | Login → returns JWT tokens |
| GET | `user/<pk>/` | Get user profile |
| PUT | `user_update/<pk>/` | Update username/email/password |
| POST | `user_delete/<pk>/` | Delete account (requires password) |
| GET | `all-address-details/` | List all saved addresses |
| POST | `create-address/` | Save new billing address |
| PUT | `update-address/<pk>/` | Edit address |
| DELETE | `delete-address/<pk>/` | Remove address |
| GET | `all-orders-list/` | User's orders (admin sees all orders) |
| PUT | `change-order-status/<pk>/` | Mark order delivered (admin only) |
| GET | `stripe-cards/` | List saved Stripe cards |

---

### 2. `product/` — Product Catalog

| File | Task |
|---|---|
| `models.py` | Single `Product` model (name, description, price, stock, image) |
| `serializers.py` | Serializes `Product` |
| `views.py` | CRUD views for products |
| `urls.py` | Maps product endpoints |

**Key Endpoints (`/api/`)**

| Method | URL | Action |
|---|---|---|
| GET | `products/` | List all products |
| GET | `product/<pk>/` | Get single product |
| POST | `product-create/` | Create product (admin) |
| PUT | `product-update/<pk>/` | Edit product (admin) |
| DELETE | `product-delete/<pk>/` | Delete product (admin) |

---

### 3. `payments/` — Stripe Integration

| File | Task |
|---|---|
| `views.py` | Full Stripe card lifecycle: create, charge, update, delete |
| `urls.py` | Maps payment endpoints |

**Key Endpoints (`/payments/`)**

| Method | URL | Action |
|---|---|---|
| POST | `create-card/` | Tokenize card with Stripe, optionally save |
| POST | `charge-customer/` | Charge saved card & save `OrderModel` |
| POST | `update-card/` | Update Stripe card + sync local DB |
| POST | `delete-card/` | Delete from Stripe & local DB |
| GET | `card-details/` | Retrieve card from Stripe |
| GET | `check-token/` | Validate JWT token is still active |

---

## Database Setup

- **Engine:** SQLite (`django.db.backends.sqlite3`), file: `db.sqlite3`
- **Configured in** `settings.py`:
  ```python
  DATABASES = {
      'default': {
          'ENGINE': 'django.db.backends.sqlite3',
          'NAME': BASE_DIR / 'db.sqlite3',
      }
  }
  ```
- **ORM:** Django's built-in ORM — no raw SQL needed.
- **Migrations:** Each app has a `migrations/` folder. Run `python manage.py makemigrations && python manage.py migrate` to apply schema changes.
- **Default PK:** `BigAutoField` (64-bit auto-increment integer).
- **Media storage:** User-uploaded images saved to `static/images/` via `MEDIA_ROOT`.

---

## Authentication

Uses **JWT (JSON Web Tokens)** via `djangorestframework-simplejwt`.

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    )
}
```

**Token config (in `settings.py`):**
- Access token lifetime: **300 minutes**
- Refresh token lifetime: **1 day**
- Algorithm: **HS256**
- Header: `Authorization: Bearer <token>`

**Advanced pattern — Custom Token Serializer:**
```python
class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)             # get default tokens
        serializer = UserRegisterTokenSerializer(self.user).data
        for k, v in serializer.items():
            data[k] = v                           # inject user info into token response
        return data
```
On login, instead of just `access` + `refresh`, the response also includes `id`, `username`, `email`, `admin` — by overriding `TokenObtainPairView`, avoiding a second network call from the frontend.

---

## Advanced Django Concepts Used

### 1. Class-Based Views (APIView)
All views extend DRF's `APIView` directly (not `ViewSet`/`ModelViewSet`), giving full manual control over HTTP method handlers (`get`, `post`, `put`, `delete`).

### 2. SerializerMethodField for Computed Properties
```python
class UserSerializer(serializers.ModelSerializer):
    admin = serializers.SerializerMethodField(read_only=True)

    def get_admin(self, obj):
        return obj.is_staff   # computed field, not a DB column
```

### 3. JWT Auto-Generation on Registration
On register, `UserRegisterTokenSerializer` calls `RefreshToken.for_user(obj)` to issue a JWT token immediately — no separate login step required.

### 4. Permission-Based Access Control
- `permissions.IsAuthenticated` — any logged-in user
- `permissions.IsAdminUser` — staff/superuser only (e.g., `ChangeOrderStatus`)
- Manual ownership checks: `request.user.id == user_address.user.id` to prevent cross-user data access

### 5. Custom Validators on Models
```python
phone_number = models.CharField(
    validators=[RegexValidator(r'^\+?1?\d{9,15}$')]
)
```
Validation runs at the DB model level via Django's validator framework.

### 6. ForeignKey with `related_name`
```python
user = models.ForeignKey(User, related_name="stripemodel", on_delete=models.CASCADE)
```
`related_name` enables **reverse lookup**: `user.stripemodel.all()` from a User instance.

### 7. Role-Based Order Visibility
```python
def get(self, request):
    if request.user.is_staff:
        return OrderModel.objects.all()          # admin sees everything
    return OrderModel.objects.filter(user=request.user)  # user sees own orders
```

### 8. CORS Configuration
`django-cors-headers` middleware is used with `CORS_ALLOW_ALL_ORIGINS = True` (dev only). In production this should be restricted to specific frontend origins.

### 9. Stripe Dual-Sync Pattern
The app keeps Stripe and the local SQLite DB in sync:  
- Card create → saved in both Stripe and `StripeModel`  
- Card update → patched on Stripe via API **and** updated in local `StripeModel`  
- Card delete → removed from Stripe, then `stripe.Customer.delete()` called, then local record deleted

---

## How to Run

```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
# Server runs at http://127.0.0.1:8000/
```

Set Stripe keys as environment variables:
```bash
export STRIPE_TEST_PUBLISHABLE_KEY=pk_test_...
export STRIPE_TEST_SECRET_KEY=sk_test_...
```
