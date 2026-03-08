from django.urls import path
from account import views
from rest_framework_simplejwt.views import TokenObtainPairView  # standard JWT login view (we override it below)


# ─────────────────────────────────────────────────────────────────────────────
# ACCOUNT APP — URL ROUTING
#
# All routes here are prefixed with /account/ (set in the root my_project/urls.py).
# .as_view() converts a class-based view (APIView subclass) into a callable
# that Django's URL dispatcher can call for incoming requests.
# ─────────────────────────────────────────────────────────────────────────────

urlpatterns = [

    # ── User Auth ─────────────────────────────────────────────────────────────
    path('register/', views.UserRegisterView.as_view(), name="register-page"),
    # POST /account/register/ → creates user + returns JWT token

    path('login/', views.MyTokenObtainPairView.as_view(), name="login-page"),
    # POST /account/login/ → validates credentials, returns access + refresh tokens + user info

    path('user/<int:pk>/', views.UserAccountDetailsView.as_view(), name="user-details"),
    # GET /account/user/1/ → returns profile data for user with id=1

    path('user_update/<int:pk>/', views.UserAccountUpdateView.as_view(), name="user-update"),
    # PUT /account/user_update/1/ → updates username, email, password for user id=1

    path('user_delete/<int:pk>/', views.UserAccountDeleteView.as_view(), name="user-delete"),
    # POST /account/user_delete/1/ → deletes account after password confirmation

    # ── Billing Address ────────────────────────────────────────────────────────
    path('all-address-details/', views.UserAddressesListView.as_view(), name="all-address-details"),
    # GET /account/all-address-details/ → all addresses for the logged-in user

    path('address-details/<int:pk>/', views.UserAddressDetailsView.as_view(), name="address-details"),
    # GET /account/address-details/3/ → single address with id=3

    path('create-address/', views.CreateUserAddressView.as_view(), name="create-address"),
    # POST /account/create-address/ → saves a new delivery address

    path('update-address/<int:pk>/', views.UpdateUserAddressView.as_view(), name="update-address-details"),
    # PUT /account/update-address/3/ → edits address with id=3

    path('delete-address/<int:pk>/', views.DeleteUserAddressView.as_view(), name="delete-address"),
    # DELETE /account/delete-address/3/ → removes address with id=3

    # ── Orders ─────────────────────────────────────────────────────────────────
    path('all-orders-list/', views.OrdersListView.as_view(), name="all-orders-list"),
    # GET /account/all-orders-list/ → user's orders (admin gets all orders)

    path('change-order-status/<int:pk>/', views.ChangeOrderStatus.as_view(), name="change-order-status"),
    # PUT /account/change-order-status/5/ → admin marks order id=5 as delivered

    # ── Stripe Cards ───────────────────────────────────────────────────────────
    path('stripe-cards/', views.CardsListView.as_view(), name="stripe-cards-list-page"),
    # GET /account/stripe-cards/ → returns all saved Stripe card records for the logged-in user
]