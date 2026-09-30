from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken


def set_auth_cookies(response, refresh):
    """Attach access and refresh tokens as HTTP-only cookies."""
    set_access_cookie(response, str(refresh.access_token))
    set_token_cookie(
        response,
        "refresh_token",
        str(refresh),
        api_settings.REFRESH_TOKEN_LIFETIME,
    )


def set_access_cookie(response, access_token):
    """Attach only the access token as an HTTP-only cookie."""
    set_token_cookie(
        response,
        "access_token",
        access_token,
        api_settings.ACCESS_TOKEN_LIFETIME,
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


def delete_auth_cookies(response):
    """Remove the access and refresh token cookies from the client."""
    response.delete_cookie("access_token", samesite="Lax")
    response.delete_cookie("refresh_token", samesite="Lax")


def create_access_token(raw_refresh_token):
    """Return a new access token for a valid, non-blacklisted refresh token."""
    if raw_refresh_token is None:
        raise AuthenticationFailed("Refresh token missing.")
    try:
        refresh = RefreshToken(raw_refresh_token)
    except TokenError:
        raise AuthenticationFailed("Refresh token invalid or expired.")
    return str(refresh.access_token)


def blacklist_refresh_token(raw_token):
    """Blacklist the given refresh token so it can no longer be used."""
    if raw_token is None:
        return
    try:
        RefreshToken(raw_token).blacklist()
    except TokenError:
        # Token is already invalid or expired, nothing left to revoke.
        return
