from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from quiz_app.utils import create_quiz_from_url

from .serializers import QuizCreateResponseSerializer, QuizCreateSerializer


class QuizListCreateView(APIView):
    """Create quizzes from YouTube videos."""

    def post(self, request):
        """Generate a quiz from the given YouTube URL for the current user."""
        serializer = QuizCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quiz = create_quiz_from_url(request.user, serializer.validated_data["url"])
        return Response(
            QuizCreateResponseSerializer(quiz).data,
            status=status.HTTP_201_CREATED,
        )


from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from quiz_app.models import Quiz
from quiz_app.utils import create_quiz_from_url

from .permissions import IsQuizOwner
from .serializers import (
    QuizCreateResponseSerializer,
    QuizCreateSerializer,
    QuizSerializer,
)


class QuizListCreateView(APIView):
    """List the user's quizzes or create a new one from a YouTube video."""

    def get(self, request):
        """Return all quizzes of the current user including questions."""
        quizzes = Quiz.objects.filter(user=request.user).prefetch_related("questions")
        return Response(QuizSerializer(quizzes, many=True).data)

    def post(self, request):
        """Generate a quiz from the given YouTube URL for the current user."""
        serializer = QuizCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quiz = create_quiz_from_url(request.user, serializer.validated_data["url"])
        return Response(
            QuizCreateResponseSerializer(quiz).data,
            status=status.HTTP_201_CREATED,
        )


class QuizDetailView(generics.RetrieveAPIView):
    """Retrieve a single quiz that belongs to the current user."""

    queryset = Quiz.objects.prefetch_related("questions")
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated, IsQuizOwner]
