# wsgi.py

from app import create_app

# This is the application instance that Gunicorn will look for.
app = create_app()

