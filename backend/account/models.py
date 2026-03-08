from django.db import models
from django.contrib.auth.models import User  # Django's built-in User model (handles username, email, password, is_staff, etc.)
from django.core.validators import RegexValidator  # utility to validate field values against a regex pattern


# ─────────────────────────────────────────────────────────────────────────────
# STRIPE MODEL
# Stores a user's saved card info (synced with Stripe's API).
# This acts as a local mirror of Stripe data so we don't have to call Stripe
# every time we need card details — reducing API latency.
# ─────────────────────────────────────────────────────────────────────────────
class StripeModel(models.Model):
    email = models.EmailField(null=True, blank=True)  # email associated with the Stripe customer
    name_on_card = models.CharField(max_length=200, null=True, blank=True)  # cardholder name
    customer_id = models.CharField(max_length=200, blank=True, null=True)  # Stripe Customer ID (e.g. cus_Xxx)
    card_number = models.CharField(max_length=16, unique=True, null=True, blank=True)  # last 4 digits stored (unique so no duplicate saved cards)
    exp_month = models.CharField(max_length=2, validators=[RegexValidator(r'^\d{0,9}$')], null=True, blank=True)  # expiry month — regex ensures only digits
    exp_year = models.CharField(max_length=4, validators=[RegexValidator(r'^\d{0,9}$')], null=True, blank=True)   # expiry year — regex ensures only digits
    card_id = models.TextField(max_length=100, null=True, blank=True)  # Stripe Card Source ID (e.g. card_Xxx) — used to charge/delete the card via Stripe API
    user = models.ForeignKey(
        User,
        related_name="stripemodel",       # allows reverse lookup: user.stripemodel.all()
        on_delete=models.CASCADE,         # if the user is deleted, their card records are also deleted
        null=True, blank=True
    )
    address_city = models.CharField(max_length=120, null=True, blank=True)      # billing address fields (optional, used for card verification)
    address_country = models.CharField(max_length=120, null=True, blank=True)
    address_state = models.CharField(max_length=120, null=True, blank=True)
    address_zip = models.CharField(max_length=6, validators=[RegexValidator(r'^\d{0,9}$')], null=True, blank=True)  # zip/pin code — digits only

    def __str__(self):
        return self.email  # shown in Django admin list view


# ─────────────────────────────────────────────────────────────────────────────
# BILLING ADDRESS MODEL
# Stores shipping/billing addresses for a user.
# A user can have multiple addresses (one-to-many via ForeignKey).
# ─────────────────────────────────────────────────────────────────────────────
class BillingAddress(models.Model):
    name = models.CharField(max_length=200, null=False, blank=False)  # recipient name (required)
    user = models.ForeignKey(
        User,
        related_name="billingmodel",      # allows: user.billingmodel.all() to get all addresses
        on_delete=models.CASCADE,         # delete addresses when user is deleted
        null=True, blank=True
    )
    phone_number = models.CharField(
        max_length=10,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$')],  # validates international phone format
        null=False, blank=False
    )
    pin_code = models.CharField(
        max_length=6,
        validators=[RegexValidator(r'^\d{0,9}$')],  # only numeric pin codes allowed
        null=False, blank=False
    )
    house_no = models.CharField(max_length=300, null=False, blank=False)   # house/flat/street number
    landmark = models.CharField(max_length=120, null=False, blank=False)   # nearby landmark for delivery
    city = models.CharField(max_length=120, null=False, blank=False)
    state = models.CharField(max_length=120, null=False, blank=False)

    def __str__(self):
        return self.name  # shown in Django admin list view


# ─────────────────────────────────────────────────────────────────────────────
# ORDER MODEL
# Created when a payment is successfully charged via Stripe.
# Tracks what was ordered, delivery status, and which user placed the order.
# Admin can mark orders as delivered from the Django admin panel or via API.
# ─────────────────────────────────────────────────────────────────────────────
class OrderModel(models.Model):
    name = models.CharField(max_length=120)                                              # customer name at time of order
    ordered_item = models.CharField(max_length=200, null=True, blank=True, default="Not Set")  # product/item description
    card_number = models.CharField(max_length=16, null=True, blank=True)                 # last 4 digits of card used
    address = models.CharField(max_length=300, null=True, blank=True)                   # delivery address string
    paid_status = models.BooleanField(default=False)                                     # True once payment is confirmed
    paid_at = models.DateTimeField(auto_now_add=False, null=True, blank=True)            # timestamp of payment (set manually in view)
    total_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)  # amount charged
    is_delivered = models.BooleanField(default=False)                                    # admin toggles this to mark delivery
    delivered_at = models.CharField(max_length=200, null=True, blank=True)              # delivery timestamp as string (admin sets this)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,    # if user is deleted, their orders are also deleted
        null=True, blank=True
    )