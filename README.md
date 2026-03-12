# kerokero 🐸

An open-source, multilingual speech training framework.
Bring your own AI, your own content, your own goals.

## Quick Start

```bash
pip install -e .
kerokero
```

On first run, you'll be asked for your Anthropic API key.
Then: topic appears → you speak → AI evaluates → feedback displayed.

## What It Does

kerokero automates the speaking practice loop:

1. **Random topic** from your profile deck (IELTS Part 2 cue cards)
2. **Timed recording** from your microphone
3. **Whisper transcription** (local, private)
4. **AI evaluation** with detailed feedback (band scores, corrections, improvements)
5. **Session log** saved for progress tracking

```
Topic Card → 15s Prep → Record (up to 2min) → Transcribe → Evaluate → Feedback
```

## Why kerokero?

Apps like ELSA are great for pronunciation. kerokero is different:

- **Open**: MIT license, bring your own AI, customize everything
- **Test-focused**: IELTS, TOEFL, DELE — add any exam profile
- **Multilingual**: Whisper + LLMs support 100+ languages
- **Private**: Audio stays on your machine, transcription runs locally
- **Composable**: A Unix-style tool, not a walled garden

## Configuration

First run creates `~/.kerokero/config.toml`:

```toml
[ai]
anthropic_api_key = "sk-ant-..."
whisper_model = "tiny"

[recording]
duration_seconds = 120
sample_rate = 16000

[display]
language = "ja"
```

Sessions are saved to `~/.kerokero/sessions/` as JSON + WAV.

## Requirements

- Python 3.11+
- A microphone
- Anthropic API key
- ffmpeg (for Whisper)

## Current Status

Day 1 of a 100-day build.

## License

MIT
