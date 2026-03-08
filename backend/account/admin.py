from django.contrib import admin
from .models import StripeModel, BillingAddress, OrderModel


# ─────────────────────────────────────────────────────────────────────────────
# ACCOUNT APP — ADMIN CONFIGURATION
#
# This file controls what the Django /admin panel shows for each model.
# admin.ModelAdmin lets you customize which columns appear in the list view,
# enable search/filter, and control form layout — all without writing HTML.
# ─────────────────────────────────────────────────────────────────────────────


class StripeModelAdmin(admin.ModelAdmin):
    # list_display = columns shown in the admin list table for StripeModel
    # Admins can see card owner, card number, Stripe IDs at a glance
    list_display = ("id", "email", "card_number", "user", "exp_month", "exp_year", "customer_id", "card_id")


class BillingAddressModelAdmin(admin.ModelAdmin):
    # Shows all address fields in the admin list so admins can quickly review delivery info
    list_display = ("id", "name", "user", "phone_number", "pin_code", "house_no", "landmark", "city", "state")


class OrderModelAdmin(admin.ModelAdmin):
    # Full order snapshot visible from admin panel:
    # - paid_status / is_delivered = key booleans admins need to track
    # - delivered_at = manually set by admin when order ships
    list_display = ("id", "name", "card_number", "address", "ordered_item", "paid_status", "paid_at", "total_price", "is_delivered", "delivered_at", "user")


# Register each model with its custom admin class.
# This hooks the model into the Django admin site at /admin
admin.site.register(StripeModel, StripeModelAdmin)
admin.site.register(BillingAddress, BillingAddressModelAdmin)
admin.site.register(OrderModel, OrderModelAdmin)