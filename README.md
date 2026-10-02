# Quizly – Backend

Quizly turns YouTube videos into interactive quizzes. The backend downloads the audio of a video, transcribes it locally with Whisper and lets Google Gemini generate a quiz with 10 questions and 4 answer options each.

This repository contains the **backend only** (Django REST Framework). The frontend is provided separately and communicates with this API via REST.

---

## Features

- User registration, login and logout
- JWT authentication via **HTTP-only cookies** (access and refresh token)
- Access token refresh via the refresh token cookie and token blacklisting on logout
- Quiz generation from YouTube URLs (all common link formats are supported and normalized)
- Pipeline: **yt-dlp** (audio download) → **Whisper** (local transcription) → **Gemini Flash** (quiz generation)
- List, retrieve, partially update and delete your own quizzes
- Django admin for managing quizzes and individual questions

---

## Tech Stack

| Area | Technology |
| --- | --- |
| Framework | Django, Django REST Framework |
| Authentication | djangorestframework-simplejwt (HTTP-only cookies) |
| Audio download | yt-dlp + FFmpeg |
| Transcription | OpenAI Whisper (runs locally) |
| Quiz generation | Google Gemini Flash via `google-genai` |
| Database | SQLite (development) |

---

## Prerequisites

Make sure the following tools are installed **globally** on your system before you start.

### 1. Python

Python **3.12 or newer** is required (the project is developed with Python 3.14).

```bash
python3 --version
```

### 2. FFmpeg (required)

FFmpeg is **required by Whisper and yt-dlp** to convert and read audio files. Without it, quiz generation will fail.

| OS | Command |
| --- | --- |
| macOS (Homebrew) | `brew install ffmpeg` |
| Windows (winget) | `winget install ffmpeg` |
| Ubuntu / Debian | `sudo apt install ffmpeg` |

Verify the installation:

```bash
ffmpeg -version
```

### 3. Deno (required)

yt-dlp needs a JavaScript runtime to download videos from YouTube. Deno is the default runtime.

| OS | Command |
| --- | --- |
| macOS (Homebrew) | `brew install deno` |
| Windows (winget) | `winget install DenoLand.Deno` |
| Linux | `curl -fsSL https://deno.land/install.sh \| sh` |

Verify the installation:

```bash
deno --version
```

### 4. Gemini API key

Create a free API key in [Google AI Studio](https://aistudio.google.com/apikey).

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Infamous2k9/quizly-backend.git
cd quizly-backend
```

### 2. Create and activate a virtual environment

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows**

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** Whisper installs PyTorch, which is a large download. This step can take a few minutes.

### 4. Configure environment variables

Copy the template and fill in your own values:

```bash
cp .env.template .env
```

| Variable | Description | Example |
| --- | --- | --- |
| `SECRET_KEY` | Django secret key | see below |
| `DEBUG` | Debug mode (`True` for local development) | `True` |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hosts | `127.0.0.1,localhost` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated list of frontend origins | `http://127.0.0.1:5500` |
| `WHISPER_MODEL` | Whisper model size (`tiny`, `base`, `small`, `medium`, `turbo`) | `base` |
| `GEMINI_API_KEY` | Your Gemini API key | `your_gemini_api_key` |
| `GEMINI_MODEL` | Gemini model used for quiz generation | `gemini-3.7-flash` |

Generate a new secret key with:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

> **Important:** Never commit your `.env` file. It is already listed in `.gitignore`.

### 5. Apply migrations

```bash
python manage.py migrate
```

### 6. Create an admin user (optional)

```bash
python manage.py createsuperuser
```

### 7. Start the development server

```bash
python manage.py runserver
```

The API is now available at `http://127.0.0.1:8000/api/` and the admin panel at `http://127.0.0.1:8000/admin/`.

---

## Connecting the Frontend

- Serve the frontend on the origin you configured in `CORS_ALLOWED_ORIGINS`, e.g. `http://127.0.0.1:5500` (VS Code Live Server).
- Use **the same host** for frontend and backend (`127.0.0.1` for both, or `localhost` for both). Otherwise the browser will not send the authentication cookies.
- If the frontend reloads unexpectedly after login, open it in a separate VS Code window so Live Server does not watch the backend files (e.g. `db.sqlite3`).

---

## API Endpoints

All endpoints are prefixed with `/api/`. Authentication is handled automatically via HTTP-only cookies set on login.

### Authentication

| Method | Endpoint | Description | Auth |
| --- | --- | --- | --- |
| POST | `/api/register/` | Register a new user | No |
| POST | `/api/login/` | Log in and set `access_token` and `refresh_token` cookies | No |
| POST | `/api/logout/` | Log out, blacklist the refresh token and delete the cookies | Yes |
| POST | `/api/token/refresh/` | Issue a new access token using the refresh token cookie | Refresh cookie |

### Quizzes

| Method | Endpoint | Description | Auth |
| --- | --- | --- | --- |
| POST | `/api/quizzes/` | Create a quiz from a YouTube URL | Yes |
| GET | `/api/quizzes/` | List all quizzes of the current user | Yes |
| GET | `/api/quizzes/{id}/` | Retrieve a single quiz | Owner |
| PATCH | `/api/quizzes/{id}/` | Update `title` and/or `description` | Owner |
| DELETE | `/api/quizzes/{id}/` | Delete a quiz and all its questions | Owner |

**Example request – create a quiz**

```json
POST /api/quizzes/
{
  "url": "https://www.youtube.com/watch?v=example"
}
```

Supported URL formats include `youtube.com/watch?v=`, `youtu.be/`, `m.youtube.com`, `music.youtube.com`, `/shorts/`, `/embed/` and `/live/`. All URLs are stored in the canonical format `https://www.youtube.com/watch?v=<video_id>`.

> **Note:** Quiz generation runs synchronously and can take one to several minutes depending on the video length and the Whisper model. Short videos are recommended.

---

## Project Structure

```
backend/
├── core/                   # Project settings and root URL configuration
├── auth_app/
│   ├── api/
│   │   ├── authentication.py   # Cookie-based JWT authentication
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   └── views.py
│   └── utils.py            # Cookie and token helper functions
├── quiz_app/
│   ├── api/
│   │   ├── permissions.py  # Owner permission
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   └── views.py
│   ├── admin.py            # Quiz admin with inline questions
│   ├── models.py           # Quiz and Question models
│   ├── schemas.py          # Pydantic schema for the Gemini response
│   └── utils.py            # Quiz generation pipeline
├── manage.py
├── requirements.txt
└── .env.template
```

---

## Troubleshooting

| Problem | Solution |
| --- | --- |
| `ffmpeg not found` | Install FFmpeg globally and restart your terminal. |
| `Video could not be downloaded.` | Update yt-dlp with `pip install -U "yt-dlp[default]"` and make sure Deno is installed. Private, age-restricted or region-locked videos cannot be downloaded. |
| `No supported JavaScript runtime could be found` | Install Deno (see prerequisites). |
| `AI service is currently unavailable.` | The Gemini model may be overloaded (`503`) or no longer available (`404`). Set a different Flash model in `GEMINI_MODEL` and restart the server. |
| `CERTIFICATE_VERIFY_FAILED` when Whisper downloads its model (macOS) | Run `Install Certificates.command` from your Python installation folder, e.g. `/Applications/Python 3.14/`. |
| CORS errors in the browser | Check that the frontend origin exactly matches `CORS_ALLOWED_ORIGINS` (no trailing slash) and restart the server. |

> **First run:** Whisper downloads the selected model on the first quiz generation (e.g. about 140 MB for `base`) and caches it in `~/.cache/whisper`.
