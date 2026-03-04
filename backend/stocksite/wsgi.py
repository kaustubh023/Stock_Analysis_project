"""
WSGI config for stocksite project.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "stocksite.settings")
application = get_wsgi_application()
