from django.apps import AppConfig


# ─────────────────────────────────────────────────────────────────────────────
# PAYMENTS APP CONFIG
#
# Django reads this class on startup when 'payments' is listed in INSTALLED_APPS.
# Even though this app has no models of its own, it still needs an AppConfig
# so Django can discover its views, URLs, and migrations folder.
# ─────────────────────────────────────────────────────────────────────────────
class PaymentsConfig(AppConfig):
    # 64-bit auto-increment PK — avoids 2-billion row limit of the old 32-bit AutoField.
    # Applies to any future models added to this app.
    default_auto_field = 'django.db.models.BigAutoField'

    # Must match the folder name exactly so Django can locate this app's resources.
    name = 'payments'
