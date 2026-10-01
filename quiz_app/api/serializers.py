from rest_framework import serializers

from quiz_app.models import Question, Quiz
from quiz_app.utils import normalize_youtube_url


class QuestionSerializer(serializers.ModelSerializer):
    """Represent a question without timestamps (used for GET and PATCH)."""

    class Meta:
        model = Question
        fields = ["id", "question_title", "question_options", "answer"]


class QuestionDetailSerializer(QuestionSerializer):
    """Represent a question including timestamps (used for POST)."""

    class Meta(QuestionSerializer.Meta):
        fields = QuestionSerializer.Meta.fields + ["created_at", "updated_at"]


class QuizSerializer(serializers.ModelSerializer):
    """Represent a quiz with its questions."""

    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = [
            "id",
            "title",
            "description",
            "created_at",
            "updated_at",
            "video_url",
            "questions",
        ]


class QuizCreateResponseSerializer(QuizSerializer):
    """Represent a newly created quiz with detailed questions."""

    questions = QuestionDetailSerializer(many=True, read_only=True)


class QuizCreateSerializer(serializers.Serializer):
    """Validate and normalize the YouTube URL for quiz creation."""

    url = serializers.CharField()

    def validate_url(self, value):
        """Accept only supported YouTube links and return the canonical URL."""
        normalized_url = normalize_youtube_url(value)
        if normalized_url is None:
            raise serializers.ValidationError("Please provide a valid YouTube URL.")
        return normalized_url
