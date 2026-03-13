# kerokero 🐸

An open-source, multilingual speech training framework.
Bring your own AI, your own content, your own goals.

## Quick Start

```bash
pip install -e .
kerokero
```

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
whisper_model = "tiny"
# anthropic_api_key = "sk-ant-..."  # optional: use API instead of CLI

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
- [Claude Code](https://claude.com/claude-code) CLI (default evaluator, works with MAX plan)
- ffmpeg (for Whisper)

**Alternative**: If you don't have Claude Code, install with API support:

```bash
pip install -e ".[api]"
```

Then add `anthropic_api_key` to your config.

## Current Status

Day 1 of a 100-day build.

## License

MIT
