from .models import StripeModel, BillingAddress, OrderModel
from rest_framework import serializers
from django.contrib.auth.models import User      # Django's built-in User model
from rest_framework_simplejwt.tokens import RefreshToken  # used to programmatically generate JWT tokens


# ─────────────────────────────────────────────────────────────────────────────
# USER SERIALIZER
# Converts the built-in Django User model → JSON.
# Adds a computed `admin` field so the frontend knows if the user is staff.
# ─────────────────────────────────────────────────────────────────────────────
class UserSerializer(serializers.ModelSerializer):
    # SerializerMethodField = a read-only computed field, NOT a DB column.
    # Django calls get_<field_name>() automatically to compute its value.
    admin = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "admin"]  # only expose these fields (hides password hash, etc.)

    def get_admin(self, obj):
        # obj = the User instance being serialized
        # is_staff is True for admin/superusers — exposed as "admin" to the frontend
        return obj.is_staff


# ─────────────────────────────────────────────────────────────────────────────
# USER REGISTER TOKEN SERIALIZER
# Extends UserSerializer to also return a JWT access token.
# Used during REGISTRATION so the user is immediately logged in
# (frontend gets user info + token in one response — no separate login call needed).
# ─────────────────────────────────────────────────────────────────────────────
class UserRegisterTokenSerializer(UserSerializer):
    # Another computed field — generates a fresh JWT access token for this user
    token = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "admin", "token"]  # includes token on top of UserSerializer fields

    def get_token(self, obj):
        # RefreshToken.for_user(obj) creates a refresh token for the given user,
        # then we extract and return the access token as a string.
        # This is the same JWT the frontend will use in the Authorization header.
        token = RefreshToken.for_user(obj)
        return str(token.access_token)


# ─────────────────────────────────────────────────────────────────────────────
# CARDS LIST SERIALIZER
# Serializes StripeModel objects (saved card records) → JSON.
# Used by CardsListView to return all saved cards for a logged-in user.
# ─────────────────────────────────────────────────────────────────────────────
class CardsListSerializer(serializers.ModelSerializer):

    class Meta:
        model = StripeModel
        fields = "__all__"  # expose all columns (email, card_number, customer_id, card_id, etc.)


# ─────────────────────────────────────────────────────────────────────────────
# BILLING ADDRESS SERIALIZER
# Serializes BillingAddress objects → JSON (and deserializes for create/update).
# Used for CRUD operations on user delivery addresses.
# ─────────────────────────────────────────────────────────────────────────────
class BillingAddressSerializer(serializers.ModelSerializer):

    class Meta:
        model = BillingAddress
        fields = "__all__"  # includes: id, name, user, phone_number, pin_code, house_no, landmark, city, state


# ─────────────────────────────────────────────────────────────────────────────
# ALL ORDERS LIST SERIALIZER
# Serializes OrderModel objects → JSON.
# Used by both regular users (see their own orders) and admin (sees all orders).
# ─────────────────────────────────────────────────────────────────────────────
class AllOrdersListSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrderModel
        fields = "__all__"  # includes: id, name, card_number, address, paid_status, paid_at, total_price, is_delivered, delivered_at, user