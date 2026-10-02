import re
import tempfile
from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import whisper
import yt_dlp
from django.conf import settings
from django.db import transaction
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from rest_framework.exceptions import APIException, ValidationError

from .models import Question, Quiz
from .schemas import GeneratedQuiz

# ------------------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------------------

AUDIO_FILENAME = "audio"
YOUTUBE_HOSTS = {
    "youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtube-nocookie.com",
}
SHORT_LINK_HOST = "youtu.be"
VIDEO_ID_PATH_PREFIXES = ("/shorts/", "/embed/", "/live/", "/v/")
VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")
CANONICAL_VIDEO_URL = "https://www.youtube.com/watch?v={}"

QUESTION_COUNT = 10
OPTION_COUNT = 4
QUIZ_PROMPT = """
Create a quiz based on the following video transcript.

Requirements:
- Exactly {question_count} questions.
- Each question has exactly {option_count} distinct answer options.
- Exactly one option is correct, and "answer" must match it character for character.
- The title is short and describes the topic (max. 80 characters).
- The description summarizes the quiz in one or two sentences (max. 150 characters).
- Write everything in the same language as the transcript.

Transcript:
{transcript}
"""


# ------------------------------------------------------------------------------
# Exceptions
# ------------------------------------------------------------------------------


class QuizGenerationError(APIException):
    """Raised when the AI response cannot be turned into a valid quiz."""

    status_code = 500
    default_detail = "Quiz could not be generated."
    default_code = "quiz_generation_failed"


# ------------------------------------------------------------------------------
# Pipeline
# ------------------------------------------------------------------------------


def create_quiz_from_url(user, video_url):
    """Run the full pipeline and store the generated quiz for the user."""
    quiz_data = generate_quiz_from_video(video_url)
    return save_quiz(user, video_url, quiz_data)


def generate_quiz_from_video(video_url):
    """Download, transcribe and turn a YouTube video into quiz data."""
    with tempfile.TemporaryDirectory() as temp_dir:
        audio_path = download_audio(video_url, temp_dir)
        transcript = transcribe_audio(audio_path)
    return generate_quiz_data(transcript)


@transaction.atomic
def save_quiz(user, video_url, quiz_data):
    """Store the quiz and all its questions in a single transaction."""
    quiz = Quiz.objects.create(
        user=user,
        title=quiz_data.title,
        description=quiz_data.description,
        video_url=video_url,
    )
    Question.objects.bulk_create(
        [Question(quiz=quiz, **q.model_dump()) for q in quiz_data.questions]
    )
    return quiz


# ------------------------------------------------------------------------------
# YouTube URL normalization
# ------------------------------------------------------------------------------


def normalize_youtube_url(url):
    """Return the canonical watch URL for a supported YouTube link, else None."""
    video_id = extract_video_id(url)
    if video_id is None or not VIDEO_ID_PATTERN.match(video_id):
        return None
    return CANONICAL_VIDEO_URL.format(video_id)


def extract_video_id(url):
    """Extract the raw video id from any supported YouTube URL, or None."""
    url = url.strip()
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = parsed.netloc.lower().removeprefix("www.")
    if host == SHORT_LINK_HOST:
        return parsed.path.lstrip("/").split("/")[0]
    if host in YOUTUBE_HOSTS:
        return extract_id_from_youtube_path(parsed)
    return None


def extract_id_from_youtube_path(parsed):
    """Extract the video id from a youtube.com path or query string."""
    if parsed.path == "/watch":
        return parse_qs(parsed.query).get("v", [None])[0]
    for prefix in VIDEO_ID_PATH_PREFIXES:
        if parsed.path.startswith(prefix):
            return parsed.path[len(prefix) :].split("/")[0]
    return None


# ------------------------------------------------------------------------------
# Audio download (yt-dlp)
# ------------------------------------------------------------------------------


def download_audio(video_url, target_dir):
    """Download the audio track of a YouTube video and return the mp3 path."""
    try:
        with yt_dlp.YoutubeDL(build_download_options(target_dir)) as ydl:
            ydl.download([video_url])
    except yt_dlp.utils.DownloadError:
        raise ValidationError({"url": "Video could not be downloaded."})
    return Path(target_dir) / f"{AUDIO_FILENAME}.mp3"


def build_download_options(target_dir):
    """Return yt-dlp options for extracting the audio as an mp3 file."""
    return {
        "format": "bestaudio/best",
        "outtmpl": str(Path(target_dir) / f"{AUDIO_FILENAME}.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}],
    }


# ------------------------------------------------------------------------------
# Transcription (Whisper)
# ------------------------------------------------------------------------------


def transcribe_audio(audio_path):
    """Transcribe an audio file to plain text using a local Whisper model."""
    result = get_whisper_model().transcribe(str(audio_path), fp16=False)
    return result["text"].strip()


@lru_cache(maxsize=1)
def get_whisper_model():
    """Load the configured Whisper model once and reuse it afterwards."""
    return whisper.load_model(settings.WHISPER_MODEL)


# ------------------------------------------------------------------------------
# Quiz generation (Gemini)
# ------------------------------------------------------------------------------


def generate_quiz_data(transcript):
    """Create a quiz from the transcript via Gemini and return validated data."""
    try:
        quiz_data = request_quiz_from_gemini(transcript)
    except genai_errors.APIError:
        raise QuizGenerationError("AI service is currently unavailable.")
    validate_quiz_data(quiz_data)
    return quiz_data


def request_quiz_from_gemini(transcript):
    """Send the quiz prompt to Gemini and return the parsed response."""
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=build_quiz_prompt(transcript),
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=GeneratedQuiz,
        ),
    )
    return response.parsed


def build_quiz_prompt(transcript):
    """Insert the transcript and quiz rules into the prompt template."""
    return QUIZ_PROMPT.format(
        question_count=QUESTION_COUNT,
        option_count=OPTION_COUNT,
        transcript=transcript,
    )


def validate_quiz_data(quiz_data):
    """Ensure the generated quiz has the expected number of questions."""
    if quiz_data is None:
        raise QuizGenerationError("AI response could not be parsed.")
    if len(quiz_data.questions) != QUESTION_COUNT:
        raise QuizGenerationError("Quiz does not contain 10 questions.")
    for question in quiz_data.questions:
        validate_question(question)


def validate_question(question):
    """Ensure a question has four options and a valid answer."""
    if len(question.question_options) != OPTION_COUNT:
        raise QuizGenerationError("A question does not have 4 options.")
    if question.answer not in question.question_options:
        raise QuizGenerationError("An answer is not one of its options.")
