"""kerokero — Day 1 pipeline: topic → record → transcribe → evaluate → feedback."""

import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from random import choice

import numpy as np
import sounddevice as sd
import whisper
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from scipy.io import wavfile

try:
    import tomllib
except ImportError:
    import tomli as tomllib

console = Console()

KEROKERO_DIR = Path.home() / ".kerokero"
SESSIONS_DIR = KEROKERO_DIR / "sessions"
CONFIG_PATH = KEROKERO_DIR / "config.toml"
TOPICS_PATH = Path(__file__).parent.parent.parent / "topics" / "ielts.json"


# --- Config ---


def load_config() -> dict:
    """Load config or run first-time setup."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "rb") as f:
            return tomllib.load(f)

    console.print("\n[bold green]Welcome to kerokero![/] Let's set up your config.\n")
    console.print("[dim]Evaluation uses 'claude' CLI by default (Claude Code MAX plan).[/]")
    console.print("[dim]To use API instead, add anthropic_api_key to config later.[/]\n")

    whisper_model = console.input("[bold]Whisper model[/] (tiny/base/small) [dim]\\[tiny][/]: ").strip() or "tiny"
    duration = console.input("[bold]Max recording seconds[/] [dim]\\[120][/]: ").strip() or "120"
    language = console.input("[bold]Feedback language[/] (ja/en/es) [dim]\\[ja][/]: ").strip() or "ja"

    KEROKERO_DIR.mkdir(parents=True, exist_ok=True)
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    config_text = f"""[ai]
whisper_model = "{whisper_model}"

[recording]
duration_seconds = {duration}
sample_rate = 16000

[display]
language = "{language}"
"""
    CONFIG_PATH.write_text(config_text)
    console.print(f"\n[green]Config saved to {CONFIG_PATH}[/]\n")

    with open(CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


# --- Topic ---


def pick_topic() -> dict:
    """Pick a random IELTS topic card."""
    with open(TOPICS_PATH) as f:
        topics = json.load(f)
    return choice(topics)


def display_topic(topic: dict):
    """Display topic card with rich formatting."""
    angles = "\n".join(f"  • {a}" for a in topic["suggested_angles"])
    content = f"[bold]{topic['prompt']}[/]\n\n[dim]Topic linking hints:[/]\n{angles}"
    console.print(Panel(content, title=f"[bold cyan]{topic['topic']}[/]", border_style="cyan"))


def prep_countdown(seconds: int = 15):
    """Countdown timer for preparation."""
    console.print(f"\n[yellow]Preparation time: {seconds} seconds[/]")
    for i in range(seconds, 0, -1):
        console.print(f"  [dim]{i}...[/]", end="\r")
        time.sleep(1)
    console.print("[bold green]Start speaking![/]            \n")


# --- Recording ---


def record_audio(duration: int = 120, sample_rate: int = 16000) -> tuple[np.ndarray, float]:
    """Record from microphone. Ctrl+C to stop early."""
    console.print(f"[bold red]● Recording[/] (max {duration}s, Ctrl+C to stop)\n")

    recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype="int16")

    start_time = time.time()
    stopped_early = False

    original_handler = signal.getsignal(signal.SIGINT)

    def stop_handler(sig, frame):
        nonlocal stopped_early
        stopped_early = True
        sd.stop()

    signal.signal(signal.SIGINT, stop_handler)

    try:
        while sd.get_stream().active and not stopped_early:
            elapsed = time.time() - start_time
            mins, secs = divmod(int(elapsed), 60)
            console.print(f"  [dim]{mins:02d}:{secs:02d}[/]", end="\r")
            time.sleep(0.5)
    finally:
        signal.signal(signal.SIGINT, original_handler)

    sd.stop()
    actual_duration = time.time() - start_time

    # Trim to actual recorded length
    samples_recorded = int(actual_duration * sample_rate)
    recording = recording[:samples_recorded]

    console.print(f"\n[green]Recording complete ({actual_duration:.1f}s)[/]\n")
    return recording, actual_duration


def save_wav(audio: np.ndarray, path: Path, sample_rate: int = 16000):
    """Save numpy array as WAV file."""
    wavfile.write(str(path), sample_rate, audio)


# --- Transcription ---


def transcribe(audio_path: Path, model_name: str = "tiny") -> str:
    """Transcribe audio file using Whisper."""
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        progress.add_task("Transcribing with Whisper...", total=None)
        model = whisper.load_model(model_name)
        result = model.transcribe(str(audio_path), language="en")

    transcript = result["text"].strip()
    console.print(Panel(transcript, title="[bold]Transcript[/]", border_style="blue"))
    return transcript


# --- Evaluation ---


EVALUATOR_SYSTEM_PROMPT = """You are an IELTS Speaking examiner. Evaluate the following Part 2 response.

Scoring criteria (each 1-9):
- Fluency and Coherence
- Lexical Resource
- Grammatical Range and Accuracy
- Pronunciation (based on transcript patterns only)

Respond in this exact JSON format:
{
  "overall_band": 6.5,
  "scores": {
    "fluency_coherence": 6.0,
    "lexical_resource": 7.0,
    "grammatical_range": 6.5,
    "pronunciation_estimate": 6.5
  },
  "strengths": ["...", "..."],
  "weaknesses": ["...", "..."],
  "corrected_version_en": "A more natural version in English of what the speaker was trying to say",
  "corrected_version": "Same model answer translated to the feedback language",
  "specific_improvements": [
    {
      "original": "what they said",
      "improved": "better way to say it",
      "reason": "why this is better"
    }
  ],
  "examiner_comment": "Brief overall comment"
}"""


def evaluate(
    topic_prompt: str, transcript: str, display_lang: str = "ja",
    api_key: str = "", duration: float = 0,
) -> dict:
    """Evaluate via Claude CLI (default) or Anthropic API (if api_key set)."""
    lang_instruction = ""
    if display_lang != "en":
        lang_instruction = f"\n\nIMPORTANT: Write the examiner_comment, strengths, weaknesses, specific_improvements reasons, and corrected_version in {display_lang}. Write corrected_version_en in English. Keep the JSON keys in English."

    duration_info = ""
    if duration > 0:
        duration_info = f"\nRecording duration: {duration:.0f} seconds (note: transcript may be shorter due to pauses/silence)"

    user_message = f"""Topic: {topic_prompt}

Candidate's response (transcribed from audio):
{transcript}{duration_info}

Evaluate this IELTS Speaking Part 2 response.{lang_instruction}

Respond ONLY with the JSON object, no markdown fences."""

    if api_key:
        raw = _evaluate_api(user_message, api_key)
    else:
        raw = _evaluate_cli(user_message)

    # Extract JSON from response (handle markdown code blocks)
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0]
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0]

    return json.loads(raw.strip())


def _evaluate_cli(user_message: str) -> str:
    """Evaluate using Claude CLI (claude -p). Works with MAX plan, no API key needed."""
    prompt = f"{EVALUATOR_SYSTEM_PROMPT}\n\n---\n\n{user_message}"

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        progress.add_task("Claude is evaluating (CLI)...", total=None)
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=120,
        )

    if result.returncode != 0:
        console.print(f"[red]Claude CLI error:[/] {result.stderr.strip()}")
        console.print("[dim]Hint: Install Claude Code (npm install -g @anthropic-ai/claude-code) "
                      "or set anthropic_api_key in ~/.kerokero/config.toml[/]")
        sys.exit(1)

    return result.stdout.strip()


def _evaluate_api(user_message: str, api_key: str) -> str:
    """Evaluate using Anthropic API directly. Requires anthropic_api_key in config."""
    try:
        import anthropic
    except ImportError:
        console.print("[red]anthropic package not installed.[/] Run: pip install anthropic")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        progress.add_task("Claude is evaluating (API)...", total=None)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=EVALUATOR_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

    return response.content[0].text


def display_evaluation(evaluation: dict):
    """Display evaluation results with rich formatting."""
    scores = evaluation["scores"]

    # Band scores
    score_lines = [
        f"[bold yellow]Overall Band: {evaluation['overall_band']}[/]\n",
        f"  Fluency & Coherence:    {scores['fluency_coherence']}",
        f"  Lexical Resource:       {scores['lexical_resource']}",
        f"  Grammatical Range:      {scores['grammatical_range']}",
        f"  Pronunciation (est.):   {scores['pronunciation_estimate']}",
    ]
    console.print(Panel("\n".join(score_lines), title="[bold]IELTS Band Scores[/]", border_style="yellow"))

    # Strengths & Weaknesses
    strengths = "\n".join(f"  [green]✓[/] {s}" for s in evaluation["strengths"])
    weaknesses = "\n".join(f"  [red]✗[/] {w}" for w in evaluation["weaknesses"])
    console.print(Panel(f"[bold green]Strengths[/]\n{strengths}\n\n[bold red]Areas to Improve[/]\n{weaknesses}", border_style="white"))

    # Specific improvements
    if evaluation.get("specific_improvements"):
        improvements = []
        for imp in evaluation["specific_improvements"]:
            improvements.append(f'  [red]"{imp["original"]}"[/] → [green]"{imp["improved"]}"[/]')
            improvements.append(f"  [dim]{imp['reason']}[/]\n")
        console.print(Panel("\n".join(improvements), title="[bold]Specific Improvements[/]", border_style="magenta"))

    # Corrected version (English + translated)
    if evaluation.get("corrected_version_en"):
        console.print(Panel(evaluation["corrected_version_en"], title="[bold]Model Answer (EN)[/]", border_style="green"))
    if evaluation.get("corrected_version"):
        console.print(Panel(evaluation["corrected_version"], title="[bold]Model Answer (翻訳)[/]", border_style="green"))

    # Examiner comment
    if evaluation.get("examiner_comment"):
        console.print(f"\n[bold]Examiner:[/] {evaluation['examiner_comment']}\n")


# --- Session Log ---


def save_session(topic: dict, transcript: str, evaluation: dict, duration: float, audio_path: Path):
    """Save session as JSON."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    session = {
        "timestamp": datetime.now().isoformat(),
        "topic_id": topic["id"],
        "topic": topic["topic"],
        "prompt": topic["prompt"],
        "transcript": transcript,
        "evaluation": evaluation,
        "duration_seconds": round(duration, 1),
        "audio_path": str(audio_path),
    }

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    session_path = SESSIONS_DIR / f"{timestamp}.json"
    session_path.write_text(json.dumps(session, ensure_ascii=False, indent=2))
    console.print(f"[dim]Session saved: {session_path}[/]")


# --- Main ---


def main():
    """Run kerokero speaking practice session."""
    console.print("\n[bold green]kerokero[/] [dim]v0.1.0[/] — IELTS Speaking Practice\n")

    # 1. Config
    config = load_config()
    whisper_model = config.get("ai", {}).get("whisper_model", "tiny")
    api_key = config.get("ai", {}).get("anthropic_api_key", "")
    duration = config.get("recording", {}).get("duration_seconds", 120)
    sample_rate = config.get("recording", {}).get("sample_rate", 16000)
    display_lang = config.get("display", {}).get("language", "ja")

    # 2. Topic
    topic = pick_topic()
    display_topic(topic)
    prep_countdown(60)

    # 3. Record
    audio, actual_duration = record_audio(duration=duration, sample_rate=sample_rate)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    audio_path = SESSIONS_DIR / f"{timestamp}.wav"
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    save_wav(audio, audio_path, sample_rate)

    # 4. Transcribe
    transcript = transcribe(audio_path, model_name=whisper_model)

    if not transcript:
        console.print("[red]No speech detected. Try again.[/]")
        return

    # 5. Evaluate
    evaluation = evaluate(topic["prompt"], transcript, display_lang, api_key=api_key, duration=actual_duration)
    display_evaluation(evaluation)

    # 6. Save
    save_session(topic, transcript, evaluation, actual_duration, audio_path)

    console.print("[bold green]Session complete![/] Keep practicing.\n")


if __name__ == "__main__":
    main()
