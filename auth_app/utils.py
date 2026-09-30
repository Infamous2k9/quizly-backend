from django.conf import settings
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken


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


def blacklist_refresh_token(raw_token):
    """Blacklist the given refresh token so it can no longer be used."""
    if raw_token is None:
        return
    try:
        RefreshToken(raw_token).blacklist()
    except TokenError:
        # Token is already invalid or expired, nothing left to revoke.
        return


def delete_auth_cookies(response):
    """Remove the access and refresh token cookies from the client."""
    response.delete_cookie("access_token", samesite="Lax")
    response.delete_cookie("refresh_token", samesite="Lax")
