from django.conf import settings
from rest_framework_simplejwt.settings import api_settings


def set_auth_cookies(response, refresh):
    """Attach access and refresh tokens as HTTP-only cookies."""
    set_token_cookie(
        response,
        "access_token",
        str(refresh.access_token),
        api_settings.ACCESS_TOKEN_LIFETIME,
    )
    set_token_cookie(
        response,
        "refresh_token",
        str(refresh),
        api_settings.REFRESH_TOKEN_LIFETIME,
    )


def set_token_cookie(response, name, value, lifetime):
    """Set a single HTTP-only token cookie on the response."""
    response.set_cookie(
        key=name,
        value=value,
        max_age=int(lifetime.total_seconds()),
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
    )
