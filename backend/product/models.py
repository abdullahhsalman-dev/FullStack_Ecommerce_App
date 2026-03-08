from django.db import models


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCT MODEL
# The core catalog model. Represents a single purchasable item in the store.
# Stored in the DB as a single "product_product" table (app_model naming).
# ─────────────────────────────────────────────────────────────────────────────
class Product(models.Model):
    name = models.CharField(max_length=200, blank=False, null=False)
    # Product name — required (blank=False prevents empty strings, null=False prevents NULL in DB)

    description = models.TextField(blank=True)
    # Long product description — optional (blank=True allows empty strings)
    # TextField = no maximum length limit, unlike CharField

    price = models.DecimalField(max_digits=8, decimal_places=2)
    # Stored as a fixed-precision decimal (e.g. 1999.99)
    # max_digits=8 allows up to 999999.99 — use DecimalField for money, NEVER FloatField
    # (FloatField has floating-point precision errors which cause wrong money calculations)

    stock = models.BooleanField(default=False)
    # True = in stock, False = out of stock
    # Simple flag — no quantity tracking in this version

    image = models.ImageField(null=True, blank=True)
    # Stores the path to the uploaded image file (not the binary data itself)
    # File is physically saved to MEDIA_ROOT (static/images/) defined in settings.py
    # Requires Pillow to be installed (handles image validation + processing)

    def __str__(self):
        return self.name  # human-readable representation shown in Django admin list view