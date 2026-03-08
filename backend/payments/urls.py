from django.urls import path
from payments import views


# ─────────────────────────────────────────────────────────────────────────────
# PAYMENTS APP — URL ROUTING
#
# All routes here are prefixed with /payments/ (set in root my_project/urls.py).
# This app handles the full Stripe card lifecycle:
# tokenize → charge → retrieve → update → delete
# ─────────────────────────────────────────────────────────────────────────────

urlpatterns = [
    path('test-payment/', views.TestStripeImplementation.as_view()),
    # POST /payments/test-payment/ → dev-only sanity check, creates a ₹1.20 PaymentIntent

    path('create-card/', views.CreateCardTokenView.as_view()),
    # POST /payments/create-card/
    # → tokenizes card with Stripe, creates/retrieves customer, attaches card source
    # → optionally saves card in local StripeModel if save_card=True

    path('charge-customer/', views.ChargeCustomerView.as_view()),
    # POST /payments/charge-customer/
    # → charges the customer's card via stripe.Charge, saves OrderModel on success

    path('update-card/', views.CardUpdateView.as_view()),
    # POST /payments/update-card/
    # → updates card on Stripe AND syncs changes to local StripeModel (dual-sync)

    path('delete-card/', views.DeleteCardView.as_view()),
    # POST /payments/delete-card/
    # → deletes card source from Stripe, removes local StripeModel record,
    #   then deletes the Stripe Customer to avoid stale default card issue

    path('card-details/', views.RetrieveCardView.as_view()),
    # GET /payments/card-details/
    # → fetches card info from Stripe using Customer-Id and Card-Id request headers

    path('check-token/', views.CheckTokenValidation.as_view()),
    # GET /payments/check-token/
    # → lightweight JWT validity check (JWT auth middleware does the real work)
]