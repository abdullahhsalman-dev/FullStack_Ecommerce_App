from django.contrib import admin
from .models import Product


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCT APP — ADMIN CONFIGURATION
#
# admin.site.register(Product) tells Django's admin interface:
# "make this model manageable from the /admin panel."
#
# Once registered, Django auto-generates a full CRUD UI for Product:
#   ✅ Create new products
#   📋 List all products
#   ✏️ Edit existing products
#   🗑️ Delete products
#
# Note: Unlike the account/admin.py, this doesn't use a custom ModelAdmin subclass.
# That means the admin list view shows only the __str__ output ("Product name")
# instead of individual columns. To add column-level display, you would do:
#
#   class ProductAdmin(admin.ModelAdmin):
#       list_display = ("id", "name", "price", "stock")
#   admin.site.register(Product, ProductAdmin)
# ─────────────────────────────────────────────────────────────────────────────

admin.site.register(Product)