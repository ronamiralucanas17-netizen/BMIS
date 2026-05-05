"""
ASGI config for bmis project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
import sys

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bmis.settings')

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PYPKGS_DIR = os.path.join(_BASE_DIR, '.pypkgs')
if os.path.isdir(_PYPKGS_DIR) and _PYPKGS_DIR not in sys.path:
    sys.path.insert(0, _PYPKGS_DIR)

application = get_asgi_application()
