# ⚠️ Sentinel Insight — Multimodal Emotion Analysis

> **Part of the [Sentinel Health](../../README.md) platform.**
> Module path inside the monorepo: `modules/insight/`.
>
> **Quick run (standalone):**
> ```bash
> # Configure OPENAI_API_KEY from the template:
> cp emotion-recognizer/.env.example emotion-recognizer/.env
> $EDITOR emotion-recognizer/.env   # paste your sk-... key
> docker-compose up -d
> # → http://localhost:8501/insight/
> ```
>
> **Integrated run (with Surgical + nginx):** see [`../../deploy/README.md`](../../deploy/README.md).

A Streamlit-based tool that combines **video facial emotion detection** and **audio speech emotion analysis** to support the identification of signs of emotional distress — with a focus on potential domestic violence indicators. Designed for integration with telemedicine systems to assist healthcare professionals in monitoring patients' psychological well-being.

---

## Table of Contents

- [Objective](#objective)
- [Features](#features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Analysis Modes](#analysis-modes)
- [Testing](#testing)
- [Technical Details](#technical-details)
- [Limitations & Disclaimer](#limitations--disclaimer)

---

## Objective

This application is intended to support the identification of signs of domestic violence by analyzing emotional cues from both video and audio sources. Key objectives include:

- **Identifying signs of emotional distress** through facial emotion detection and speech analysis.
- **Supporting the monitoring of women's psychological well-being** in telemedicine settings.
- **Leveraging pre-trained AI models** (DeepFace, Whisper, GPT) for specialized data processing.
- **Providing actionable AI-generated summaries** that highlight risk levels and recommended actions.

---

## Features

| Feature | Description |
|---|---|
| **Facial Emotion Detection** | OpenCV Haar cascades for face detection + DeepFace for emotion classification (happy, sad, angry, fear, surprise, neutral, disgust) |
| **Speech Transcription** | Whisper API (OpenAI) for speech-to-text conversion |
| **Voice Emotion Analysis** | LLM-based sentiment, risk level, and distress signal detection from speech content |
| **AI Summarization** | GPT-powered natural-language summaries combining video and audio emotion data |
| **Multiple Input Sources** | Webcam recording, YouTube URL download, or direct audio file upload |
| **Three Analysis Modes** | Video + Audio, Video Only, or Audio Only |
| **Export** | Download results as JSON for further processing |
| **Interactive UI** | Streamlit dashboard with charts, frame previews, and configurable parameters |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Streamlit UI (app.py)                    │
│   ┌──────────┐  ┌──────────────┐  ┌──────────────────────────┐ │
│   │  Webcam   │  │  YouTube URL  │  │  Audio File Upload      │ │
│   └────┬─────┘  └──────┬───────┘  └───────────┬──────────────┘ │
│        │               │                      │                 │
│        ▼               ▼                      │                 │
│   ┌─────────────────────────┐                 │                 │
│   │   Video Pipeline        │                 │                 │
│   │  ┌───────────────────┐  │                 │                 │
│   │  │ OpenCV Haar Cascade│  │                 │                 │
│   │  │ (face detection)   │  │                 │                 │
│   │  └────────┬──────────┘  │                 │                 │
│   │           ▼             │                 │                 │
│   │  ┌───────────────────┐  │                 │                 │
│   │  │ DeepFace           │  │                 │                 │
│   │  │ (emotion classify) │  │                 │                 │
│   │  └───────────────────┘  │                 │                 │
│   └────────────┬────────────┘                 │                 │
│                │                              │                 │
│                ▼                              ▼                 │
│   ┌──────────────────────────────────────────────┐              │
│   │   Audio Pipeline                             │              │
│   │  ┌─────────────┐  ┌────────┐  ┌───────────┐ │              │
│   │  │ ffmpeg       │→│Whisper │→│ LLM Voice  │ │              │
│   │  │ (extract)    │  │(STT)   │  │ Analyzer  │ │              │
│   │  └─────────────┘  └────────┘  └───────────┘ │              │
│   └──────────────────────────┬───────────────────┘              │
│                              │                                  │
│                              ▼                                  │
│   ┌──────────────────────────────────────────────┐              │
│   │   LLM Summarizer (GPT via OpenAI)            │              │
│   │   Combines video + audio → unified summary   │              │
│   └──────────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
emotion-detector/
├── requirements.txt               # Python dependencies
├── emotion-recognizer/
│   ├── app.py                     # Main Streamlit entry point
│   ├── .env                       # API keys (not committed)
│   ├── README.md                  # This file
│   │
│   ├── analysis/                  # Video analysis & visualization
│   │   ├── __init__.py
│   │   ├── analyzer.py            # Haar cascade + DeepFace emotion pipeline
│   │   ├── summarizer.py          # LLM summarization via OpenAI (gpt-5.4-nano)
│   │   └── visualizer.py          # Streamlit UI components (tables, charts, etc.)
│   │
│   ├── audio/                     # Audio processing pipeline
│   │   ├── __init__.py
│   │   ├── extractor.py           # ffmpeg-based audio extraction from video
│   │   ├── transcriber.py         # Whisper API speech-to-text
│   │   └── voice_analyzer.py      # LLM + keyword-based voice emotion analysis
│   │
│   ├── video/                     # Video input sources
│   │   ├── __init__.py
│   │   ├── recorder.py            # Webcam recording via OpenCV
│   │   └── youtube.py             # YouTube download via yt-dlp
│   │
│   ├── utils/                     # Utilities
│   │   ├── __init__.py
│   │   └── export.py              # JSON export with NumPy type handling
│   │
│   ├── tests/                     # Unit tests (pytest)
│   │   ├── test_api_key.py        # Live API key validation
│   │   ├── test_extractor.py      # Audio extraction tests
│   │   ├── test_transcriber.py    # Whisper transcription tests
│   │   ├── test_voice_analyzer.py # Voice emotion analysis tests
│   │   ├── test_summarizer.py     # LLM summarizer tests
│   │   └── test_multimodal.py     # Multimodal integration tests
│   │
│   └── archive/                   # Reference scripts (not used at runtime)
│       ├── audio_whisper.py       # Original Whisper reference implementation
│       ├── llm-response.py        # LLM response exploration script
│       ├── emotion_results.json   # Sample emotion detection output
│       ├── test.py                # Original standalone test script
│       └── multimodal-reference/  # Reference project (health monitoring)
```

---

## Prerequisites

- **Python 3.12+**
- **ffmpeg** — required for audio extraction from video
  - Windows: `winget install ffmpeg` or download from [ffmpeg.org](https://ffmpeg.org/download.html)
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt install ffmpeg`
  - Fallback: the app can use `imageio-ffmpeg` if system ffmpeg is not found
- **OpenAI API key** (`OPENAI_API_KEY`) — required for Whisper transcription, voice analysis, and LLM summaries

---

## Installation

```bash
# Clone the repository
git clone https://github.com/<your-org>/emotion-detector.git
cd emotion-detector

# Create and activate a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Configuration

Create a `.env` file inside the `emotion-recognizer/` directory:

```env
OPENAI_API_KEY=sk-your-openai-api-key
```

This single key is used for:
- **Whisper API** — speech-to-text transcription
- **OpenAI (GPT)** — voice emotion analysis and LLM summarization

Obtain your key from the [OpenAI Platform](https://platform.openai.com/api-keys).

---

## Usage

From the repository root directory:

```bash
streamlit run emotion-recognizer/app.py
```

The app will open in your browser at `http://localhost:8501`.

### Sample Video for Testing

```
https://www.youtube.com/watch?v=O-xjW_ig1KI
```

---

## Analysis Modes

### 🎬 Video + Audio (default)

Full multimodal pipeline:
1. Downloads or records video
2. Samples every N frames → face detection (Haar cascades) → emotion classification (DeepFace)
3. Extracts audio → transcribes speech (Whisper) → analyzes voice emotions (LLM + keyword fallback)
4. Generates a unified AI summary combining both video and audio findings
5. Displays: summary table, emotion-over-time chart, frame previews, voice analysis metrics, AI summary, JSON export

### 🎥 Video Only

Video emotion detection without audio processing:
1. Same video pipeline as above
2. No audio extraction or speech analysis
3. LLM summary based on video emotions only

### 🎤 Audio Only

Speech emotion analysis without video:
1. Upload an audio file (WAV, MP3, M4A, etc.) or extract audio from a YouTube URL
2. Transcribes speech via Whisper API
3. Analyzes transcription for emotional signals, sentiment, and risk level
4. Generates an AI summary based on voice analysis only
5. Results persist across Streamlit reruns via session state

---

## Testing

Run all unit tests (excluding the live API test):

```bash
pytest emotion-recognizer/tests/ --ignore=emotion-recognizer/tests/test_api_key.py -v
```

Run only the live API key validation test:

```bash
pytest emotion-recognizer/tests/test_api_key.py -v
```

### Test Coverage

| Test File | Tests | What It Covers |
|---|---|---|
| `test_transcriber.py` | 6 | Whisper API key loading, transcription success/error/empty, missing key |
| `test_extractor.py` | 5 | ffmpeg resolution, file-not-found, mocked extraction, failure, no-ffmpeg |
| `test_voice_analyzer.py` | 11 | Local keyword fallback (6), JSON parsing (3), empty input, mocked LLM, LLM fallback |
| `test_summarizer.py` | 8 | Env/key loading, JSON payload, compact payload, mocked LLM, missing key, content extraction, live test |
| `test_multimodal.py` | 4 | Video-only, multimodal, empty voice, compact payload keys |
| `test_api_key.py` | 2 | Live API key validation and chat completion |

---

## Technical Details

### Video Pipeline

- **Face Detection**: OpenCV `CascadeClassifier` with `haarcascade_frontalface_default.xml`. Minimum face size: 30×30 px.
- **Emotion Classification**: DeepFace with grayscale→RGB preprocessing and `enforce_detection=False`.
- **Frame Sampling**: Configurable via sidebar slider (every N frames). Frames resized to max 960 px wide.
- **Emotions Detected**: angry, disgust, fear, happy, sad, surprise, neutral (with confidence scores).

### Audio Pipeline

- **Audio Extraction**: ffmpeg converts video → WAV (PCM 16-bit, mono, 16 kHz). Falls back to `imageio-ffmpeg`.
- **Speech-to-Text**: Whisper API (`whisper-1` model) via the OpenAI SDK. Supports MP3, WAV, M4A, MP4, WebM (max 25 MB).
- **Voice Analysis**: LLM-first approach with local keyword-based fallback. Detects sentiment (positive/neutral/negative), risk level (low/moderate/high), distress score (0–10), emotional signals, and keywords.

### LLM Integration

- **Endpoint**: default OpenAI API (no custom base URL)
- **Model**: `gpt-5.4-nano`
- **Token Management**: Automatic payload compaction and token estimation to stay within model limits.
- **Multimodal Summary**: Combines video emotion timeline with voice analysis into a unified natural-language assessment.

---

## Limitations & Disclaimer

> **⚠️ This tool is intended for research and support purposes only.** It is **not** a diagnostic tool and should not be used as the sole basis for any clinical or legal decision. Results should always be interpreted by qualified professionals.

- Emotion detection accuracy depends on video quality, lighting, and face visibility.
- Speech analysis requires clear audio; noisy environments may reduce accuracy.
- The LLM summary is AI-generated and may contain errors or biases.
- Requires network access to OpenAI API endpoints for transcription and summarization.
- Webcam recording requires a connected camera and browser permissions.