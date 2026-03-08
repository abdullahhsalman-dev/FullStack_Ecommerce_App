from django.db import models

# ─────────────────────────────────────────────────────────────────────────────
# PAYMENTS APP — MODELS
#
# This app intentionally has NO custom models.
# All payment data (card info, transaction records, order records) is stored in
# the `account` app's models:
#   - StripeModel     → saved card details (account/models.py)
#   - OrderModel      → order + payment confirmation record (account/models.py)
#
# Stripe-side data (customers, cards, charges) is managed entirely by Stripe's API.
# This app purely contains the VIEW LOGIC that talks to Stripe.
# ─────────────────────────────────────────────────────────────────────────────
