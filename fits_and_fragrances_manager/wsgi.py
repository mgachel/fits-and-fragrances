"""
WSGI config for fits_and_fragrances_manager project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os
from pathlib import Path
from django.core.wsgi import get_wsgi_application

# Try to load .env file if it exists
try:
    import dotenv
    dotenv.load_dotenv()
except:
    pass

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fits_and_fragrances_manager.settings')

application = get_wsgi_application()
