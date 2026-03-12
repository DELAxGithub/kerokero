# kerokero 🐸

Automated speaking practice pipeline for language learners.

Generate prompts from your profile → Record yourself → Transcribe with Whisper → Get AI feedback → Track progress. All from the terminal.

## Why

Speaking practice is the hardest part of language learning to automate. You can drill vocabulary with flashcards and read articles all day, but there's no easy way to practice *speaking* on your own and get meaningful feedback. kerokero fixes that.

## How it works

```
Profile (IELTS / TOEFL / Business / Custom)
  ↓
Topic Generator (LLM creates a prompt based on your level & weak areas)
  ↓
[Optional] Model Audio (Edge-TTS generates reference audio)
  ↓
Recording (you speak into your mic)
  ↓
Transcription (Whisper converts speech to text)
  ↓
Evaluation (LLM scores & gives feedback)
  ↓
Log (JSON log with transcript, scores, feedback, timestamps)
```

## Modes

| Mode | Description | Time |
|------|-------------|------|
| `ielts-part2` | IELTS Speaking Part 2 — cue card → 1 min prep → 2 min speech | 3 min |
| `toefl-integrated` | TOEFL iBT integrated speaking — read + listen → respond | 1 min |
| `business` | Business presentation / meeting simulation | configurable |
| `shadow` | Shadowing — listen to model audio, repeat, compare | per sentence |
| `free` | Free talk on any topic | configurable |

## Quick start

```bash
# Install
pip install kerokero

# Configure API keys
kerokero init

# Run a practice session
kerokero run --mode ielts-part2

# Review past sessions
kerokero log --last 5
```

## Configuration

kerokero uses `~/.kerokero/config.toml` for settings:

```toml
[profile]
target_exam = "ielts"        # ielts / toefl / business / general
current_level = "B2"         # CEFR level
native_language = "ja"       # for feedback language
target_score = 7.0           # exam-specific target

[ai]
evaluator = "claude"         # claude / openai / gemini
evaluator_model = "claude-sonnet-4-20250514"

[transcription]
engine = "whisper"           # whisper / whisper-api
model = "base"               # tiny / base / small / medium / large

[tts]
engine = "edge-tts"          # edge-tts (free) / google-cloud
voice = "en-US-AriaNeural"

[audio]
sample_rate = 16000
format = "wav"
```

API keys are stored in `~/.kerokero/.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AI...
```

## Project structure

```
kerokero/
├── src/
│   └── kerokero/
│       ├── __init__.py
│       ├── cli.py              # CLI entry point (click)
│       ├── config.py           # Config loading & validation
│       ├── pipeline.py         # Orchestrates the full session flow
│       ├── recorder.py         # Mic recording (sounddevice)
│       ├── transcriber.py      # Whisper transcription
│       ├── evaluator/
│       │   ├── __init__.py
│       │   ├── base.py         # Abstract evaluator interface
│       │   ├── claude.py
│       │   ├── openai.py
│       │   └── gemini.py
│       ├── generator/
│       │   ├── __init__.py
│       │   ├── base.py         # Abstract topic generator
│       │   ├── ielts.py
│       │   ├── toefl.py
│       │   ├── business.py
│       │   └── free.py
│       ├── tts/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   └── edge.py         # Edge-TTS (free)
│       └── log.py              # Session logging (JSON)
├── tests/
│   ├── test_pipeline.py
│   ├── test_transcriber.py
│   └── test_evaluator.py
├── pyproject.toml
├── LICENSE
└── README.md
```

## Requirements

- Python 3.11+
- A microphone
- At least one AI API key (Anthropic, OpenAI, or Google)
- ffmpeg (for audio processing)

## License

MIT
