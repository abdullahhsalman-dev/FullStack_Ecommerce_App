from django.apps import AppConfig


# ─────────────────────────────────────────────────────────────────────────────
# ACCOUNT APP CONFIG
#
# This class is the app's configuration descriptor — Django reads it during
# startup when 'account' is listed in INSTALLED_APPS in settings.py.
#
# AppConfig lets you:
#   - Set app-level metadata (name, label, verbose_name)
#   - Override ready() to run startup code (e.g. connect signals)
# ─────────────────────────────────────────────────────────────────────────────
class AccountConfig(AppConfig):
    # default_auto_field: sets the default primary key type for all models in this app.
    # BigAutoField = 64-bit integer auto-increment PK (handles billions of records).
    # Without this, older Django versions default to 32-bit AutoField.
    default_auto_field = 'django.db.models.BigAutoField'

    # name must exactly match the folder name of the app.
    # Django uses this to locate the app's models, views, migrations, etc.
    name = 'account'
