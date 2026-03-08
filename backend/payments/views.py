import stripe
from rest_framework import status
from rest_framework import permissions
from rest_framework.views import APIView               # DRF base class for class-based API views
from rest_framework.response import Response           # DRF JSON response wrapper
from account.models import StripeModel, OrderModel    # cross-app import — payment data lives in account app
from rest_framework.decorators import permission_classes
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
# STRIPE API KEY
# Set the global Stripe secret key used for all Stripe API calls in this file.
# ⚠️  In production, load this from an environment variable (never hardcode it):
#      stripe.api_key = os.environ.get("STRIPE_TEST_SECRET_KEY")
# ─────────────────────────────────────────────────────────────────────────────
stripe.api_key = "your secret key here"


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: SAVE CARD IN DB
# Called after a card is successfully tokenized and attached to a Stripe customer.
# Stores a local copy of the card in StripeModel so we don't need to
# call Stripe's API every time we want to display the user's saved cards.
# ─────────────────────────────────────────────────────────────────────────────
def save_card_in_db(cardData, email, cardId, customer_id, user):
    StripeModel.objects.create(
        email=email,
        customer_id=customer_id,     # Stripe Customer ID (e.g. cus_Xxx) — used to charge later
        card_number=cardData["number"],  # stored as last 4 digits for display
        exp_month=cardData["exp_month"],
        exp_year=cardData["exp_year"],
        card_id=cardId,              # Stripe Card Source ID (e.g. card_Xxx) — used to delete/update
        user=user,                   # links the card to the Django user
    )


# ─────────────────────────────────────────────────────────────────────────────
# TEST STRIPE IMPLEMENTATION
# Endpoint: POST /payments/test-payment/
# Sanity-check endpoint used during development to verify Stripe connectivity.
# Creates a PaymentIntent of ₹1.20 — not used in production flow.
# ─────────────────────────────────────────────────────────────────────────────
class TestStripeImplementation(APIView):

    def post(self, request):
        test_payment_process = stripe.PaymentIntent.create(
            amount=120,                          # amount in smallest currency unit (paise) → ₹1.20
            currency='inr',
            payment_method_types=['card'],
            receipt_email='yash@gmail.com'
        )
        return Response(data=test_payment_process, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────────────────────
# CHECK TOKEN VALIDATION
# Endpoint: GET /payments/check-token/
# A lightweight endpoint the frontend calls to verify the JWT token is still valid.
# If the token is expired or invalid, DRF's JWTAuthentication will reject the request
# automatically (returns 401) before this view even runs.
# ─────────────────────────────────────────────────────────────────────────────
class CheckTokenValidation(APIView):

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response("Token is Valid", status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────────────────────
# CREATE CARD TOKEN VIEW
# Endpoint: POST /payments/create-card/
#
# Full card creation flow:
# 1. Validate that the submitted email matches the card owner's email on Stripe
# 2. Create a Stripe Token from the raw card details (tokenization hides raw numbers)
# 3. Create or retrieve the Stripe Customer for this email
# 4. Attach the tokenized card to the Customer (creates a Card Source on Stripe)
# 5. Optionally save the card locally in StripeModel (if save_card=True)
#
# Why tokenize? Raw card numbers never touch our server after tokenization — Stripe
# handles PCI compliance. We only store the Stripe-issued card_id.
# ─────────────────────────────────────────────────────────────────────────────
class CreateCardTokenView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        card_invalid = False
        data = request.data
        email = request.data["email"]
        cardStatus = request.data["save_card"]  # bool — whether to save card locally in DB

        card_info = data["number"]
        client_card = card_info[slice(12, 16)]  # extract last 4 digits from the submitted card number

        # ── Step 1: Email-card ownership validation ───────────────────────────
        # Fetch all customers from Stripe and build a lookup of card_last4 → email.
        # If this card's last4 already exists on Stripe under a DIFFERENT email,
        # reject immediately — the provided email doesn't own this card.
        customer_data = stripe.Customer.list().data
        user_data = []
        for each in customer_data:
            the_card = each.sources.data[0].last4
            user_data.append({"user": {"card_num": the_card, "card_holder": each.email}})

        for each in user_data:
            user_info = each["user"]
            user_card_info = user_info["card_num"]
            user_email_info = user_info["card_holder"]

            if user_card_info == client_card:
                if user_email_info != email:
                    return Response({
                        "detail": "Your email address does not belong to the provided card."},
                        status=status.HTTP_400_BAD_REQUEST)

        # ── Step 2: Tokenize the card via Stripe ─────────────────────────────
        # stripe.Token.create() validates the card with Stripe's network.
        # A CardError means the card is declined/invalid.
        try:
            stripeToken = stripe.Token.create(
                card={
                    "number": data["number"],
                    "exp_month": data["exp_month"],
                    "exp_year": data["exp_year"],
                    "cvc": data["cvc"]
                },
            )
        except stripe.error.CardError as e:
            errorMessage = e.user_message  # human-readable error from Stripe (e.g. "Card declined")
            return Response({"detail": errorMessage}, status=status.HTTP_400_BAD_REQUEST)

        except stripe.error.APIConnectionError:
            return Response({"detail": "Network error, Failed to establish a new connection."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # ── Step 3: Create or retrieve Stripe Customer ────────────────────────
        # Stripe Customers are identified by email. If one already exists, reuse it.
        customer_data = stripe.Customer.list(email=email).data

        if len(customer_data) == 0:
            # First time this user adds a card — create a new Stripe Customer
            customer = stripe.Customer.create(
                email=request.data["email"],
                description="My new customer"
            )
        else:
            customer = customer_data[0]  # reuse existing customer

            # ── Existing customer: verify card details match ──────────────────
            # Stripe only allows one card per customer in this implementation.
            # Compare the last4 + exp_month + exp_year to guard against
            # someone attaching a different card to an existing customer.
            actual_cn = customer.sources.data[0].last4
            actual_em = customer.sources.data[0].exp_month
            actual_ey = customer.sources.data[0].exp_year

            recieved_cn = data["number"]
            last4_recieved_cn = recieved_cn[-4:]  # Python slice — last 4 chars
            recieved_em = data["exp_month"]
            recieved_ey = data["exp_year"]

            if actual_cn != last4_recieved_cn or actual_em != recieved_em or actual_ey != recieved_ey:
                card_invalid = True

        if card_invalid:
            return Response({"detail": "Invalid Card Details Provided."}, status=status.HTTP_400_BAD_REQUEST)

        else:
            # ── Step 4: Attach the tokenized card to the Stripe Customer ──────
            # create_source() attaches the Stripe Token to the customer profile.
            # Stripe validates the token here — generates a permanent card_id (e.g. card_Xxx).
            create_user_card = stripe.Customer.create_source(
                customer["id"],
                source=stripeToken.id,  # the token ID generated in Step 2
            )

            # ── Step 5: Optionally persist card locally ───────────────────────
            if cardStatus:
                try:
                    # Save to local StripeModel (card_number unique constraint enforced)
                    save_card_in_db(data, email, create_user_card.id, customer["id"], request.user)
                    message = {"customer_id": customer["id"], "email": email, "card_data": create_user_card}
                    return Response(message, status=status.HTTP_200_OK)
                except:
                    return Response({
                        "detail": "Card already in use, please uncheck save card option or select a card from saved card list."},
                        status=status.HTTP_400_BAD_REQUEST)
            else:
                # Card used for this transaction only — not saved locally
                try:
                    message = {"customer_id": customer["id"], "email": email, "card_data": create_user_card}
                    return Response(message, status=status.HTTP_200_OK)
                except:
                    return Response({"detail": "Network Error, please check your internet connection."})


# ─────────────────────────────────────────────────────────────────────────────
# CHARGE CUSTOMER VIEW
# Endpoint: POST /payments/charge-customer/
#
# Charges the Stripe customer's card and saves the order to the DB.
# Uses stripe.Charge (older Charges API — newer apps use PaymentIntents).
# Amount is multiplied by 100 because Stripe works in the smallest currency unit (paise).
# On success, an OrderModel record is saved to track the purchase.
# ─────────────────────────────────────────────────────────────────────────────
class ChargeCustomerView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            data = request.data
            email = request.data["email"]

            # Lookup the Stripe customer by email
            customer_data = stripe.Customer.list(email=email).data
            customer = customer_data[0]

            customer_data = stripe.Customer.list(email=request.data["email"]).data

            # Charge the customer's default card
            # amount = price * 100 (Stripe uses smallest unit: paise for INR)
            stripe.Charge.create(
                customer=customer_data[0],
                amount=int(float(request.data["amount"]) * 100),  # e.g. ₹499.00 → 49900 paise
                currency="inr",
                description='Software development services',  # required field for Indian transactions (RBI regulation)
            )

            # Save the order record in our local DB after successful charge
            # datetime.now() captures the exact payment timestamp
            new_order = OrderModel.objects.create(
                name=data["name"],
                card_number=data["card_number"],     # last 4 digits for display
                address=data["address"],
                ordered_item=data["ordered_item"],   # product/cart summary string
                paid_status=data["paid_status"],     # True (payment succeeded)
                paid_at=datetime.now(),              # server-side timestamp — not trusted from client
                total_price=data["total_price"],
                is_delivered=data["is_delivered"],   # False by default (admin changes this later)
                delivered_at=data["delivered_at"],
                user=request.user                   # FK to authenticated user
            )

            return Response(data={
                "data": {
                    "customer_id": customer.id,
                    "message": "Payment Successfull",
                }
            }, status=status.HTTP_200_OK)

        except stripe.error.APIConnectionError:
            return Response({
                "detail": "Network error, Failed to establish a new connection."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ─────────────────────────────────────────────────────────────────────────────
# RETRIEVE CARD VIEW
# Endpoint: GET /payments/card-details/
# Fetches full card details from Stripe using custom headers:
#   - Customer-Id: the Stripe customer ID
#   - Card-Id: the specific card source ID
# Headers are used instead of URL params to avoid exposing sensitive IDs in logs.
# ─────────────────────────────────────────────────────────────────────────────
class RetrieveCardView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        card_details = stripe.Customer.retrieve_source(
            request.headers["Customer-Id"],  # e.g. cus_Xxx — passed in request header
            request.headers["Card-Id"]       # e.g. card_Xxx — passed in request header
        )
        return Response(card_details, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────────────────────
# CARD UPDATE VIEW
# Endpoint: POST /payments/update-card/
#
# Dual-sync update pattern:
# 1. Update the card on Stripe via modify_source() API
# 2. Update the local StripeModel record to keep both in sync
#
# Conditional update: only fields with non-empty values are updated on both sides,
# using Python's inline ternary (`x if x else None`).
# ─────────────────────────────────────────────────────────────────────────────
class CardUpdateView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        data = request.data

        # ── Step 1: Update card on Stripe ─────────────────────────────────────
        # None fields are ignored by Stripe (no-op for that attribute)
        update_card = stripe.Customer.modify_source(
            data["customer_id"],
            data["card_id"],
            exp_month=data["exp_month"] if data["exp_month"] else None,
            exp_year=data["exp_year"] if data["exp_year"] else None,
            name=data["name_on_card"] if data["name_on_card"] else None,
            address_city=data["address_city"] if data["address_city"] else None,
            address_country=data["address_country"] if data["address_country"] else None,
            address_state=data["address_state"] if data["address_state"] else None,
            address_zip=data["address_zip"] if data["address_zip"] else None,
        )

        # ── Step 2: Sync update to local StripeModel ──────────────────────────
        # Locate the local record by card_number (last 4 digits)
        obj = StripeModel.objects.get(card_number=request.data["card_number"])

        if obj:
            # Only overwrite if new value provided; else keep existing value
            obj.name_on_card = data["name_on_card"] if data["name_on_card"] else obj.name_on_card
            obj.exp_month = data["exp_month"] if data["exp_month"] else obj.exp_month
            obj.exp_year = data["exp_year"] if data["exp_year"] else obj.exp_year
            obj.address_city = data["address_city"] if data["address_city"] else obj.address_city
            obj.address_country = data["address_country"] if data["address_country"] else obj.address_country
            obj.address_state = data["address_state"] if data["address_state"] else obj.address_state
            obj.address_zip = data["address_zip"] if data["address_zip"] else obj.address_zip
            obj.save()  # UPDATE the local StripeModel record
        else:
            pass  # card not in local DB — update only happened on Stripe side

        return Response({
            "detail": "card updated successfully",
            "data": {"Updated Card": update_card},
        }, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────────────────────
# DELETE CARD VIEW
# Endpoint: POST /payments/delete-card/
#
# Full cleanup flow:
# 1. Find the card in local StripeModel by card_number (last 4 digits)
# 2. Delete the card source from Stripe (detaches card from customer)
# 3. Delete the local StripeModel record
# 4. Delete the Stripe Customer entirely
#    → Required because Stripe keeps the deleted card as the "default" otherwise.
#    → On next card add, a fresh Stripe Customer will be recreated for this email.
# ─────────────────────────────────────────────────────────────────────────────
class DeleteCardView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        data = request.data

        # Fetch the local card record to get the Stripe IDs we need
        obj_card = StripeModel.objects.get(card_number=request.data["card_number"])

        customerId = obj_card.customer_id  # Stripe Customer ID (e.g. cus_Xxx)
        cardId = obj_card.card_id          # Stripe Card Source ID (e.g. card_Xxx)

        # ── Step 1: Delete card from Stripe ───────────────────────────────────
        stripe.Customer.delete_source(customerId, cardId)

        # ── Step 2: Delete from local Django DB ───────────────────────────────
        obj_card.delete()

        # ── Step 3: Delete the Stripe Customer ────────────────────────────────
        # Stripe doesn't reset the default_source after card deletion.
        # Deleting the customer ensures a clean slate — next card add will
        # recreate the customer via stripe.Customer.create() in CreateCardTokenView.
        stripe.Customer.delete(customerId)

        return Response("Card deleted successfully.", status=status.HTTP_200_OK)