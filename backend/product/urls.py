from django.urls import path
from product import views


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCT APP — URL ROUTING
#
# All routes are prefixed with /api/ (set in the root my_project/urls.py).
# <str:pk> is used instead of <int:pk> to allow string-type identifiers
# if the product ID format ever changes (currently IDs are integers from SQLite).
# ─────────────────────────────────────────────────────────────────────────────

urlpatterns = [
    path('products/', views.ProductView.as_view(), name="products-list"),
    # GET /api/products/ → returns all products (public, no auth needed)

    path('product/<str:pk>/', views.ProductDetailView.as_view(), name="product-details"),
    # GET /api/product/3/ → returns a single product with id=3

    path('product-create/', views.ProductCreateView.as_view(), name="product-create"),
    # POST /api/product-create/ → creates a new product (admin only)

    path('product-update/<str:pk>/', views.ProductEditView.as_view(), name="product-update"),
    # PUT /api/product-update/3/ → updates product with id=3 (admin only)

    path('product-delete/<str:pk>/', views.ProductDeleteView.as_view(), name="product-delete"),
    # DELETE /api/product-delete/3/ → deletes product with id=3 (admin only)
]