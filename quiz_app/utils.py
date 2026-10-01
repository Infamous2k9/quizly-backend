import re
from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import whisper
import yt_dlp
from django.conf import settings
from google import genai
from google.genai import types

from .schemas import GeneratedQuiz

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


def download_audio(video_url, target_dir):
    """Download the audio track of a YouTube video and return the mp3 path."""
    with yt_dlp.YoutubeDL(build_download_options(target_dir)) as ydl:
        ydl.download([video_url])
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


def transcribe_audio(audio_path):
    """Transcribe an audio file to plain text using a local Whisper model."""
    result = get_whisper_model().transcribe(str(audio_path), fp16=False)
    return result["text"].strip()


@lru_cache(maxsize=1)
def get_whisper_model():
    """Load the configured Whisper model once and reuse it afterwards."""
    return whisper.load_model(settings.WHISPER_MODEL)


class QuizGenerationError(Exception):
    """Raised when the AI response cannot be turned into a valid quiz."""


def generate_quiz_data(transcript):
    """Ask Gemini to create a quiz from the transcript and return validated data."""
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=build_quiz_prompt(transcript),
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=GeneratedQuiz,
        ),
    )
    validate_quiz_data(response.parsed)
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
