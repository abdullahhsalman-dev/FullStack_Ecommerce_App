from .models import StripeModel, BillingAddress, OrderModel
from django.http import Http404
from rest_framework import status
from rest_framework.views import APIView               # base class for all class-based API views in DRF
from django.contrib.auth.models import User            # Django's built-in User model
from rest_framework.response import Response           # DRF's JSON-aware response object
from django.contrib.auth.hashers import make_password  # hashes a plain-text password using Django's default hasher (PBKDF2)
from rest_framework import authentication, permissions
from rest_framework.decorators import permission_classes
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer  # base JWT login serializer
from rest_framework_simplejwt.views import TokenObtainPairView             # base JWT login view we override
from django.contrib.auth.hashers import check_password  # verifies a plain-text password against a stored hash
from django.shortcuts import get_object_or_404
from .serializers import (
    UserSerializer,
    UserRegisterTokenSerializer,
    CardsListSerializer,
    BillingAddressSerializer,
    AllOrdersListSerializer
)


# ─────────────────────────────────────────────────────────────────────────────
# USER REGISTER VIEW
# Endpoint: POST /account/register/
# Creates a new Django User from request data.
# Immediately returns a JWT token so the frontend can log the user in
# right after registration without a second /login/ call.
# ─────────────────────────────────────────────────────────────────────────────
class UserRegisterView(APIView):
    """To Register the User"""

    def post(self, request, format=None):
        data = request.data  # holds incoming JSON body (username, email, password)
        username = data["username"]
        email = data["email"]

        # Guard: reject empty username or email early
        if username == "" or email == "":
            return Response({"detial": "username or email cannot be empty"}, status=status.HTTP_400_BAD_REQUEST)

        else:
            # Check uniqueness — .count() is more efficient than .exists() and avoids fetching the object
            check_username = User.objects.filter(username=username).count()
            check_email = User.objects.filter(email=email).count()

            if check_username:
                message = "A user with that username already exist!"
                return Response({"detail": message}, status=status.HTTP_403_FORBIDDEN)
            if check_email:
                message = "A user with that email address already exist!"
                return Response({"detail": message}, status=status.HTTP_403_FORBIDDEN)
            else:
                # make_password() hashes the password before storing it — NEVER store plain text passwords
                user = User.objects.create(
                    username=username,
                    email=email,
                    password=make_password(data["password"]),
                )
                # Return the user data + a freshly generated JWT token in one response
                serializer = UserRegisterTokenSerializer(user, many=False)
                return Response(serializer.data)


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM JWT LOGIN — SERIALIZER + VIEW
# Endpoint: POST /account/login/
#
# By default, TokenObtainPairView only returns {"access": "...", "refresh": "..."}.
# We override the serializer to also inject user profile data (id, username, email, admin)
# into the login response — so the frontend gets everything it needs in one request.
# ─────────────────────────────────────────────────────────────────────────────
class MyTokenObtainPairSerializer(TokenObtainPairSerializer):

    def validate(self, attrs):
        data = super().validate(attrs)  # calls the parent: validates credentials, generates tokens

        # Serialize the authenticated user and merge their data into the token response
        serializer = UserRegisterTokenSerializer(self.user).data
        for k, v in serializer.items():
            data[k] = v  # injects: id, username, email, admin, token

        return data


class MyTokenObtainPairView(TokenObtainPairView):
    # Swap in our custom serializer — Django REST framework picks it up automatically
    serializer_class = MyTokenObtainPairSerializer


# ─────────────────────────────────────────────────────────────────────────────
# CARDS LIST VIEW
# Endpoint: GET /account/stripe-cards/
# Returns all saved Stripe cards for the currently authenticated user.
# IsAuthenticated ensures unauthenticated requests are rejected with 401.
# ─────────────────────────────────────────────────────────────────────────────
class CardsListView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Filter by request.user so users only see THEIR OWN cards (not others')
        stripeCards = StripeModel.objects.filter(user=request.user)
        serializer = CardsListSerializer(stripeCards, many=True)  # many=True → serialize a queryset (list)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────────────────────
# USER ACCOUNT DETAILS VIEW
# Endpoint: GET /account/user/<pk>/
# Returns a single user's profile data.
# Only authenticated users can access this (prevents public profile scraping).
# ─────────────────────────────────────────────────────────────────────────────
class UserAccountDetailsView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            user = User.objects.get(id=pk)  # fetch user by primary key from URL
            serializer = UserSerializer(user, many=False)  # many=False → single object
            return Response(serializer.data, status=status.HTTP_200_OK)

        except:
            return Response({"details": "User not found"}, status=status.HTTP_404_NOT_FOUND)


# ─────────────────────────────────────────────────────────────────────────────
# USER ACCOUNT UPDATE VIEW
# Endpoint: PUT /account/user_update/<pk>/
# Lets a user update their username, email, and optionally their password.
# Ownership check: request.user.id == user.id ensures users can't edit others.
# ─────────────────────────────────────────────────────────────────────────────
class UserAccountUpdateView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, pk):
        user = User.objects.get(id=pk)
        data = request.data

        if user:
            if request.user.id == user.id:  # ownership guard — you can only update your own account
                user.username = data["username"]
                user.email = data["email"]

                # Only update password if a new one is provided (empty string = keep old password)
                if data["password"] != "":
                    user.password = make_password(data["password"])  # hash the new password

                user.save()  # .save() triggers Django's model-level validation before writing to DB
                serializer = UserSerializer(user, many=False)
                message = {"details": "User Successfully Updated.", "user": serializer.data}
                return Response(message, status=status.HTTP_200_OK)
            else:
                return Response({"details": "Permission Denied."}, status.status.HTTP_403_FORBIDDEN)
        else:
            return Response({"details": "User not found."}, status=status.HTTP_404_NOT_FOUND)


# ─────────────────────────────────────────────────────────────────────────────
# USER ACCOUNT DELETE VIEW
# Endpoint: POST /account/user_delete/<pk>/
# Deletes the user's account. Requires the user to confirm their password first
# — an extra security layer so stolen tokens alone can't delete accounts.
# ─────────────────────────────────────────────────────────────────────────────
class UserAccountDeleteView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):

        try:
            user = User.objects.get(id=pk)
            data = request.data

            if request.user.id == user.id:  # ownership guard
                # check_password() compares plain-text input against the stored hash safely
                if check_password(data["password"], user.password):
                    user.delete()  # CASCADE delete removes all related StripeModel, BillingAddress, OrderModel rows too
                    return Response({"details": "User successfully deleted."}, status=status.HTTP_204_NO_CONTENT)
                else:
                    return Response({"details": "Incorrect password."}, status=status.HTTP_401_UNAUTHORIZED)
            else:
                return Response({"details": "Permission Denied."}, status=status.HTTP_403_FORBIDDEN)
        except:
            return Response({"details": "User not found."}, status=status.HTTP_404_NOT_FOUND)


# ─────────────────────────────────────────────────────────────────────────────
# USER ADDRESSES LIST VIEW
# Endpoint: GET /account/all-address-details/
# Returns ALL billing addresses saved by the currently logged-in user.
# ─────────────────────────────────────────────────────────────────────────────
class UserAddressesListView(APIView):

    def get(self, request):
        user = request.user  # the authenticated user from the JWT
        user_address = BillingAddress.objects.filter(user=user)  # only this user's addresses
        serializer = BillingAddressSerializer(user_address, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────────────────────
# USER ADDRESS DETAILS VIEW
# Endpoint: GET /account/address-details/<pk>/
# Fetches a single billing address by its primary key.
# ─────────────────────────────────────────────────────────────────────────────
class UserAddressDetailsView(APIView):

    def get(self, request, pk):
        user_address = BillingAddress.objects.get(id=pk)
        serializer = BillingAddressSerializer(user_address, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────────────────────
# CREATE USER ADDRESS VIEW
# Endpoint: POST /account/create-address/
# Creates a new billing address for the logged-in user.
# The user FK is injected server-side (not trusted from the client).
# ─────────────────────────────────────────────────────────────────────────────
class CreateUserAddressView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        data = request.data

        # Build the address dict manually so we can inject request.user.id
        # (never let the client set the user FK — that's a security risk)
        new_address = {
            "name": request.data["name"],
            "user": request.user.id,  # server-side injection of authenticated user
            "phone_number": request.data["phone_number"],
            "pin_code": request.data["pin_code"],
            "house_no": request.data["house_no"],
            "landmark": request.data["landmark"],
            "city": request.data["city"],
            "state": request.data["state"],
        }

        # Pass data= to serializer for deserialization + validation
        # is_valid() runs field-level and model-level validators (e.g. RegexValidator on phone_number)
        serializer = BillingAddressSerializer(data=new_address, many=False)
        if serializer.is_valid():
            serializer.save()  # calls .create() internally -> INSERT INTO
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ─────────────────────────────────────────────────────────────────────────────
# UPDATE USER ADDRESS VIEW
# Endpoint: PUT /account/update-address/<pk>/
# Updates an existing billing address.
# Ownership check + partial update pattern (keep old value if new value is empty).
# ─────────────────────────────────────────────────────────────────────────────
class UpdateUserAddressView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, pk):
        data = request.data

        try:
            user_address = BillingAddress.objects.get(id=pk)

            if request.user.id == user_address.user.id:  # ownership check

                # Partial update: if new value provided → use it; else → keep existing value
                # This avoids wiping fields the user didn't intend to change
                updated_address = {
                    "name": data["name"] if data["name"] else user_address.name,
                    "user": request.user.id,
                    "phone_number": data["phone_number"] if data["phone_number"] else user_address.phone_number,
                    "pin_code": data["pin_code"] if data["pin_code"] else user_address.pin_code,
                    "house_no": data["house_no"] if data["house_no"] else user_address.house_no,
                    "landmark": data["landmark"] if data["landmark"] else user_address.landmark,
                    "city": data["city"] if data["city"] else user_address.city,
                    "state": data["state"] if data["state"] else user_address.state,
                }

                # Pass instance= so serializer knows to UPDATE (not create) this record
                serializer = BillingAddressSerializer(user_address, data=updated_address)
                if serializer.is_valid():
                    serializer.save()  # calls .update() internally → UPDATE SET
                    return Response(serializer.data, status=status.HTTP_200_OK)
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"details": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        except:
            return Response({"details": "Not found."}, status=status.HTTP_404_NOT_FOUND)


# ─────────────────────────────────────────────────────────────────────────────
# DELETE USER ADDRESS VIEW
# Endpoint: DELETE /account/delete-address/<pk>/
# Deletes a billing address. Ownership is verified before deletion.
# ─────────────────────────────────────────────────────────────────────────────
class DeleteUserAddressView(APIView):

    def delete(self, request, pk):

        try:
            user_address = BillingAddress.objects.get(id=pk)

            if request.user.id == user_address.user.id:  # only the owner can delete
                user_address.delete()  # DELETE FROM billing_address WHERE id=pk
                return Response({"details": "Address successfully deleted."}, status=status.HTTP_204_NO_CONTENT)
            else:
                return Response({"details": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        except:
            return Response({"details": "Not found."}, status=status.HTTP_404_NOT_FOUND)


# ─────────────────────────────────────────────────────────────────────────────
# ORDERS LIST VIEW
# Endpoint: GET /account/all-orders-list/
# Role-based data access pattern:
#   - Staff/admin → sees ALL orders across all users
#   - Regular user → sees ONLY their own orders
# This is a clean alternative to writing two separate endpoints.
# ─────────────────────────────────────────────────────────────────────────────
class OrdersListView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):

        user_staff_status = request.user.is_staff  # True if the user is admin/superuser

        if user_staff_status:
            # Admin view: fetch all orders from all users
            all_users_orders = OrderModel.objects.all()
            serializer = AllOrdersListSerializer(all_users_orders, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            # Regular user: filter to only their own orders
            all_orders = OrderModel.objects.filter(user=request.user)
            serializer = AllOrdersListSerializer(all_orders, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────────────────────
# CHANGE ORDER STATUS VIEW
# Endpoint: PUT /account/change-order-status/<pk>/
# Admin-only endpoint (IsAdminUser) to mark an order as delivered.
# Only updates is_delivered and delivered_at — not the financial data.
# ─────────────────────────────────────────────────────────────────────────────
class ChangeOrderStatus(APIView):

    permission_classes = [permissions.IsAdminUser]  # restricts to staff/superuser accounts only

    def put(self, request, pk):
        data = request.data
        order = OrderModel.objects.get(id=pk)

        # Update only the delivery-related fields (not price, card, etc.)
        order.is_delivered = data["is_delivered"]   # True/False
        order.delivered_at = data["delivered_at"]   # timestamp string set by admin
        order.save()  # only saves changes, doesn't touch other fields

        serializer = AllOrdersListSerializer(order, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)
