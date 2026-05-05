#!/usr/bin/env python
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.dont_write_bytecode = True

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_PYPKGS_DIR = os.path.join(_BASE_DIR, '.pypkgs')
if os.path.isdir(_PYPKGS_DIR) and _PYPKGS_DIR not in sys.path:
    sys.path.insert(0, _PYPKGS_DIR)

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bmis.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
