import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chatballs_backend.settings_admin")

application = get_wsgi_application()
