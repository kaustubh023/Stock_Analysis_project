"""
ASGI config for stocksite project.
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "stocksite.settings")
application = get_asgi_application()
