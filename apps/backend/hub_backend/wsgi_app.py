import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hub_backend.settings_app")

application = get_wsgi_application()
