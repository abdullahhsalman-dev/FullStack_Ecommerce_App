from django.apps import AppConfig


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCT APP CONFIG
#
# Django reads this class during startup when 'product' is listed in
# INSTALLED_APPS in settings.py. It provides metadata about this app.
#
# AppConfig is also the place to hook into the ready() signal for startup
# logic (e.g., registering signal handlers) — not needed here but worth knowing.
# ─────────────────────────────────────────────────────────────────────────────
class ProductConfig(AppConfig):
    # BigAutoField = 64-bit auto-increment primary key for all models in this app.
    # Avoids the 2-billion row limit of the older 32-bit AutoField.
    default_auto_field = 'django.db.models.BigAutoField'

    # Must match the folder name exactly — Django uses this to discover models,
    # migrations, templates, and other app-level resources.
    name = 'product'
