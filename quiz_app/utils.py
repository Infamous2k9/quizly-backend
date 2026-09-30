import re
from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import whisper
import yt_dlp
from django.conf import settings

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
