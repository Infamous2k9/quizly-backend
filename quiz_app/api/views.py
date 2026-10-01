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
