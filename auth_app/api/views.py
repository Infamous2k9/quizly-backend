from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from auth_app.utils import set_auth_cookies

from .serializers import LoginSerializer, RegistrationSerializer, UserSerializer


class RegistrationView(APIView):
    """Register a new user account."""

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
