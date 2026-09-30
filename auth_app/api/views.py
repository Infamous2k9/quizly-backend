from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from auth_app.utils import (
    blacklist_refresh_token,
    create_access_token,
    delete_auth_cookies,
    set_access_cookie,
    set_auth_cookies,
)

from .serializers import LoginSerializer, RegistrationSerializer, UserSerializer


class RegistrationView(APIView):
    """Register a new user account."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        """Create a user from the submitted registration data."""
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "User created successfully!"},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """Log in a user and set JWT tokens as HTTP-only cookies."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        """Validate credentials and return the user with auth cookies."""
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        response = Response(
            {"detail": "Login successfully!", "user": UserSerializer(user).data}
        )
        set_auth_cookies(response, RefreshToken.for_user(user))
        return response


class LogoutView(APIView):
    """Log out the user by blacklisting the refresh token and clearing cookies."""

    def post(self, request):
        """Invalidate the refresh token and delete all auth cookies."""
        blacklist_refresh_token(request.COOKIES.get("refresh_token"))
        response = Response(
            {
                "detail": "Log-Out successfully! All Tokens will be deleted. "
                "Refresh token is now invalid."
            }
        )
        delete_auth_cookies(response)
        return response


class CookieTokenRefreshView(APIView):
    """Issue a new access token using the refresh token cookie."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        """Validate the refresh cookie and set a new access token cookie."""
        access_token = create_access_token(request.COOKIES.get("refresh_token"))
        response = Response({"detail": "Token refreshed"})
        set_access_cookie(response, access_token)
        return response
