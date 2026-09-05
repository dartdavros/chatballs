import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chatballs_backend.settings_platform")

application = get_asgi_application()
