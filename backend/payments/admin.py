from django.contrib import admin

# ─────────────────────────────────────────────────────────────────────────────
# PAYMENTS APP — ADMIN CONFIGURATION
#
# No models are registered here because the payments app has no own models.
# Payment-related data (StripeModel, OrderModel) lives in the `account` app
# and is registered in account/admin.py instead.
#
# If you ever add a payments-specific model (e.g. TransactionLog), register it here:
#   from .models import TransactionLog
#   admin.site.register(TransactionLog)
# ─────────────────────────────────────────────────────────────────────────────
