from pathlib import Path

import yt_dlp

AUDIO_FILENAME = "audio"


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
