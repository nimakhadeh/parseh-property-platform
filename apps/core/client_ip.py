"""Resolve client addresses for the bundled trusted Nginx/Unix-socket setup."""
from django.core.exceptions import ImproperlyConfigured


def get_client_ip(request):
    # TCP deployments keep their peer address; never trust arbitrary forwarded headers.
    address = request.META.get("REMOTE_ADDR")
    if address:
        return address
    # Gunicorn leaves REMOTE_ADDR empty on Unix sockets. The bundled Nginx
    # overwrites X-Real-IP, and the socket is private to the application host.
    address = request.META.get("HTTP_X_REAL_IP")
    if address:
        return address
    raise ImproperlyConfigured("Client IP missing; use the bundled Nginx proxy configuration.")
