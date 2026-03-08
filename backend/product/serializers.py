from rest_framework import serializers
from .models import Product


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCT SERIALIZER
# Converts Product model instances ↔ JSON (both directions).
#
# Serialization   (Python object → JSON): used in GET responses
# Deserialization (JSON → Python object): used in POST/PUT requests, runs validation
#
# ModelSerializer auto-generates fields from the model definition,
# so you don't have to manually declare each field's type.
# ─────────────────────────────────────────────────────────────────────────────
class ProductSerializer(serializers.ModelSerializer):

    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'price', 'stock', 'image']
        # Explicitly listing fields (instead of "__all__") is a security best practice —
        # it prevents accidentally exposing unexpected fields if new columns are added to the model.
        # 'id' is the auto-generated primary key Django adds to every model.
