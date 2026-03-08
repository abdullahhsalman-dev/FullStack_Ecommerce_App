from .models import Product
from rest_framework import status
from django.shortcuts import render
from rest_framework.views import APIView               # DRF base class for class-based API views
from .serializers import ProductSerializer
from rest_framework.response import Response           # DRF's JSON-serializable response wrapper
from rest_framework import authentication, permissions
from rest_framework.decorators import permission_classes


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCT VIEW
# Endpoint: GET /api/products/
# Public endpoint — no authentication required.
# Returns all products as a JSON array.
# ─────────────────────────────────────────────────────────────────────────────
class ProductView(APIView):

    def get(self, request):
        products = Product.objects.all()  # SELECT * FROM product_product
        serializer = ProductSerializer(products, many=True)  # many=True → serialize a queryset (list of objects)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCT DETAIL VIEW
# Endpoint: GET /api/product/<pk>/
# Returns a single product by its primary key (id).
# <str:pk> in the URL accepts any string, giving flexibility if pk format changes.
# ─────────────────────────────────────────────────────────────────────────────
class ProductDetailView(APIView):

    def get(self, request, pk):
        product = Product.objects.get(id=pk)  # raises DoesNotExist if not found (no try/except here — improvement opportunity)
        serializer = ProductSerializer(product, many=False)  # many=False → single object
        return Response(serializer.data, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCT CREATE VIEW
# Endpoint: POST /api/product-create/
# Admin-only — only staff/superusers can create products (IsAdminUser).
# Validates incoming data via the serializer before writing to the DB.
# ─────────────────────────────────────────────────────────────────────────────
class ProductCreateView(APIView):

    permission_classes = [permissions.IsAdminUser]  # 403 Forbidden for non-admin users

    def post(self, request):
        user = request.user  # available but not used here (could be used for audit logs)
        data = request.data  # parsed JSON body from the request

        # Build dict explicitly to control exactly which fields get set
        product = {
            "name": data["name"],
            "description": data["description"],
            "price": data["price"],
            "stock": data["stock"],
            "image": data["image"],
        }

        # Pass data= to serializer → triggers deserialization + validation
        serializer = ProductSerializer(data=product, many=False)
        if serializer.is_valid():  # runs field validators (type checks, max_length, etc.)
            serializer.save()      # calls serializer's .create() → INSERT INTO product_product
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({"detail": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCT DELETE VIEW
# Endpoint: DELETE /api/product-delete/<pk>/
# Admin-only. Deletes a product by PK.
# Wrapped in try/except to handle the case where the product doesn't exist.
# ─────────────────────────────────────────────────────────────────────────────
class ProductDeleteView(APIView):

    permission_classes = [permissions.IsAdminUser]

    def delete(self, request, pk):
        try:
            product = Product.objects.get(id=pk)
            product.delete()  # DELETE FROM product_product WHERE id=pk
            return Response({"detail": "Product successfully deleted."}, status=status.HTTP_204_NO_CONTENT)
            # 204 No Content → standard HTTP response for successful DELETE (no response body)
        except:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCT EDIT VIEW
# Endpoint: PUT /api/product-update/<pk>/
# Admin-only. Updates an existing product.
# Partial update pattern: if a field is empty in the request, the existing value is kept.
# ─────────────────────────────────────────────────────────────────────────────
class ProductEditView(APIView):

    permission_classes = [permissions.IsAdminUser]

    def put(self, request, pk):
        data = request.data
        product = Product.objects.get(id=pk)  # fetch the current product from DB

        # Partial update: use incoming value if provided, else fall back to existing DB value
        # Note: stock is always taken from request (no fallback) because False is falsy
        updated_product = {
            "name": data["name"] if data["name"] else product.name,
            "description": data["description"] if data["description"] else product.description,
            "price": data["price"] if data["price"] else product.price,
            "stock": data["stock"],          # BooleanField — always overwrite (False would be skipped with `if`)
            "image": data["image"] if data["image"] else product.image,
        }

        # Pass instance=product so the serializer knows to UPDATE, not create
        # Internally calls serializer.update() → UPDATE product_product SET ... WHERE id=pk
        serializer = ProductSerializer(product, data=updated_product)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({"detail": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
