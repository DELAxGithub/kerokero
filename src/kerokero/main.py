"""kerokero — IELTS speaking practice with content-first methodology."""

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


def pick_topic(prefix: str = "") -> dict:
    """Pick a random topic card, optionally filtered by id prefix."""
    with open(TOPICS_PATH) as f:
        topics = json.load(f)
    if prefix:
        topics = [t for t in topics if t["id"].startswith(prefix)]
        if not topics:
            console.print(f"[red]No topics found with prefix: {prefix}[/]")
            sys.exit(1)
    return choice(topics)


def display_topic(topic: dict):
    """Display topic card with rich formatting."""
    angles = "\n".join(f"  • {a}" for a in topic["suggested_angles"])
    content = f"[bold]{topic['prompt']}[/]\n\n[dim]Topic linking hints:[/]\n{angles}"
    console.print(Panel(content, title=f"[bold cyan]{topic['topic']}[/]", border_style="cyan"))


# --- Recording ---


def prep_countdown(seconds: int = 60):
    """Countdown timer for preparation."""
    console.print(f"\n[yellow]Preparation time: {seconds} seconds[/]")
    for i in range(seconds, 0, -1):
        console.print(f"  [dim]{i}...[/]", end="\r")
        time.sleep(1)
    console.print("[bold green]Start speaking![/]            \n")


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

    samples_recorded = int(actual_duration * sample_rate)
    recording = recording[:samples_recorded]

    console.print(f"\n[green]Recording complete ({actual_duration:.1f}s)[/]\n")
    return recording, actual_duration


def save_wav(audio: np.ndarray, path: Path, sample_rate: int = 16000):
    """Save numpy array as WAV file."""
    wavfile.write(str(path), sample_rate, audio)


# --- Transcription ---


def transcribe(audio_path: Path, model_name: str = "tiny", language: str | None = "en") -> str:
    """Transcribe audio file using Whisper."""
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        lang_label = language or "auto"
        progress.add_task(f"Transcribing with Whisper ({lang_label})...", total=None)
        model = whisper.load_model(model_name)
        kwargs = {"language": language} if language else {}
        result = model.transcribe(str(audio_path), **kwargs)

    transcript = result["text"].strip()
    console.print(Panel(transcript, title="[bold]Transcript[/]", border_style="blue"))
    return transcript


# --- Claude call (shared) ---


def call_claude(system_prompt: str, user_message: str, api_key: str = "") -> str:
    """Call Claude via API (config key or ANTHROPIC_API_KEY env var) or CLI fallback."""
    resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if resolved_key:
        return _call_api(system_prompt, user_message, resolved_key)
    return _call_cli(system_prompt, user_message)


def _call_cli(system_prompt: str, user_message: str) -> str:
    """Call Claude CLI (claude -p)."""
    prompt = f"{system_prompt}\n\n---\n\n{user_message}"

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        progress.add_task("Claude is thinking...", total=None)
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=120,
        )

    if result.returncode != 0:
        console.print(f"[red]Claude CLI error:[/] {result.stderr.strip()}")
        console.print("[dim]Hint: Install Claude Code or set anthropic_api_key in config[/]")
        sys.exit(1)

    return result.stdout.strip()


def _call_api(system_prompt: str, user_message: str, api_key: str) -> str:
    """Call Anthropic API directly."""
    try:
        import anthropic
    except ImportError:
        console.print("[red]anthropic package not installed.[/] Run: pip install anthropic")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        progress.add_task("Claude is thinking (API)...", total=None)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

    return response.content[0].text


def parse_json_response(raw: str) -> dict:
    """Extract JSON from Claude response, handling markdown fences."""
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0]
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0]
    return json.loads(raw.strip())


# --- Test Mode Evaluation ---


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
  "examiner_comment": "Brief overall comment",
  "shadow_drills": ["phrase1 (5-10 words)", "phrase2", "phrase3"]
}

Identify 3 phrases the speaker struggled with or avoided.
Provide natural English alternatives as shadow_drills.
Each phrase must be 5-10 words. Conversational, not textbook."""


def evaluate_test(
    topic_prompt: str, transcript: str, display_lang: str = "ja",
    api_key: str = "", duration: float = 0, key_phrases: list[str] | None = None,
) -> dict:
    """IELTS evaluation for test mode (and practice Stage 3)."""
    lang_instruction = ""
    if display_lang != "en":
        lang_instruction = (
            f"\n\nIMPORTANT: Write the examiner_comment, strengths, weaknesses, "
            f"specific_improvements reasons, and corrected_version in {display_lang}. "
            f"Write corrected_version_en in English. Keep the JSON keys in English."
        )

    duration_info = ""
    if duration > 0:
        duration_info = f"\nRecording duration: {duration:.0f} seconds"

    phrases_info = ""
    if key_phrases:
        phrases_list = ", ".join(f'"{p}"' for p in key_phrases)
        phrases_info = (
            f"\n\nThe speaker was given these key phrases to incorporate: {phrases_list}\n"
            f"Note which phrases were used and which were missed. "
            f'Add a "key_phrases_used" list to your JSON response.'
        )

    user_message = (
        f"Topic: {topic_prompt}\n\n"
        f"Candidate's response (transcribed from audio):\n"
        f"{transcript}{duration_info}\n\n"
        f"Evaluate this IELTS Speaking Part 2 response.{lang_instruction}{phrases_info}\n\n"
        f"Respond ONLY with the JSON object, no markdown fences."
    )

    raw = call_claude(EVALUATOR_SYSTEM_PROMPT, user_message, api_key)
    return parse_json_response(raw)


def display_evaluation(evaluation: dict):
    """Display test mode evaluation results."""
    scores = evaluation["scores"]

    score_lines = [
        f"[bold yellow]Overall Band: {evaluation['overall_band']}[/]\n",
        f"  Fluency & Coherence:    {scores['fluency_coherence']}",
        f"  Lexical Resource:       {scores['lexical_resource']}",
        f"  Grammatical Range:      {scores['grammatical_range']}",
        f"  Pronunciation (est.):   {scores['pronunciation_estimate']}",
    ]
    console.print(Panel("\n".join(score_lines), title="[bold]IELTS Band Scores[/]", border_style="yellow"))

    strengths = "\n".join(f"  [green]✓[/] {s}" for s in evaluation["strengths"])
    weaknesses = "\n".join(f"  [red]✗[/] {w}" for w in evaluation["weaknesses"])
    console.print(Panel(
        f"[bold green]Strengths[/]\n{strengths}\n\n[bold red]Areas to Improve[/]\n{weaknesses}",
        border_style="white",
    ))

    if evaluation.get("specific_improvements"):
        improvements = []
        for imp in evaluation["specific_improvements"]:
            improvements.append(f'  [red]"{imp["original"]}"[/] → [green]"{imp["improved"]}"[/]')
            improvements.append(f"  [dim]{imp['reason']}[/]\n")
        console.print(Panel("\n".join(improvements), title="[bold]Specific Improvements[/]", border_style="magenta"))

    if evaluation.get("corrected_version_en"):
        console.print(Panel(evaluation["corrected_version_en"], title="[bold]Model Answer (EN)[/]", border_style="green"))
    if evaluation.get("corrected_version"):
        console.print(Panel(evaluation["corrected_version"], title="[bold]Model Answer (翻訳)[/]", border_style="green"))

    # Key phrases tracking (practice mode Stage 3)
    if evaluation.get("key_phrases_used"):
        used = "\n".join(f"  [green]✓[/] {p}" for p in evaluation["key_phrases_used"])
        console.print(Panel(used, title="[bold]Key Phrases Used[/]", border_style="cyan"))

    if evaluation.get("examiner_comment"):
        console.print(f"\n[bold]Examiner:[/] {evaluation['examiner_comment']}\n")


def export_shadow_drills(evaluation: dict, topic: dict) -> Path | None:
    """Export shadow drills from evaluation as ShadowMaster-compatible JSON."""
    drills = evaluation.get("shadow_drills", [])
    if not drills:
        return None

    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    date_str = datetime.now().strftime("%Y-%m-%d")

    shadow = {
        "folder": {
            "name": f"{topic['topic']} — ドリル {date_str}",
            "sentences": [
                {"id": f"drill-{i+1:03d}", "text": phrase, "translation": "", "chunks": []}
                for i, phrase in enumerate(drills)
            ],
        }
    }

    path = SESSIONS_DIR / f"{ts}_drills.json"
    path.write_text(json.dumps(shadow, ensure_ascii=False, indent=2))
    console.print(f"\n[dim]Shadow drills saved: {path}[/]")
    console.print("[bold cyan]→ ShadowMasterにインポートして反復練習[/]")
    return path


# --- Practice Mode: Stage 1 (Structure) ---


STRUCTURE_SYSTEM_PROMPT = """You are evaluating the LOGICAL STRUCTURE of an IELTS Speaking Part 2 response plan.
The plan is in the speaker's native language. Do NOT evaluate language quality.

Evaluate ONLY:
1. Topic Coverage (0-9): Does the plan address all parts of the topic card?
2. Idea Development (0-9): Are ideas specific enough? (not vague/generic)
3. Logical Flow (0-9): Is there a clear progression? (not random jumping)
4. Completeness (0-9): Could this fill 2 minutes when spoken in English?

Also provide 5 Band 7+ English key phrases the speaker should try to use
when delivering this content in English.

Respond in this exact JSON format:
{
  "content_score": 7.0,
  "scores": {
    "topic_coverage": 7,
    "idea_development": 6,
    "logical_flow": 7,
    "completeness": 8
  },
  "feedback": "Brief feedback on the logical structure",
  "suggested_outline_en": "If you were to say this in English, a strong structure would be: ...",
  "key_phrases_en": ["phrase 1", "phrase 2", "phrase 3", "phrase 4", "phrase 5"],
  "gate_pass": true
}

Set gate_pass to true if content_score >= 6.0."""


def evaluate_structure(
    topic_prompt: str, transcript_l1: str, display_lang: str = "ja",
    api_key: str = "", duration: float = 0,
) -> dict:
    """Evaluate L1 content structure (practice mode Stage 1)."""
    lang_instruction = ""
    if display_lang != "en":
        lang_instruction = (
            f"\n\nIMPORTANT: Write feedback and suggested_outline in {display_lang}. "
            f"Write suggested_outline_en and key_phrases_en in English. "
            f"Keep JSON keys in English."
        )

    duration_info = ""
    if duration > 0:
        duration_info = f"\nPlanning duration: {duration:.0f} seconds"

    user_message = (
        f"Topic card: {topic_prompt}\n\n"
        f"Speaker's plan (transcribed, may be in Japanese or mixed language):\n"
        f"{transcript_l1}{duration_info}\n\n"
        f"Evaluate this content plan.{lang_instruction}\n\n"
        f"Respond ONLY with the JSON object, no markdown fences."
    )

    raw = call_claude(STRUCTURE_SYSTEM_PROMPT, user_message, api_key)
    return parse_json_response(raw)


def display_structure_result(evaluation: dict):
    """Display Stage 1 structure evaluation."""
    scores = evaluation["scores"]

    gate = "[bold green]PASS[/]" if evaluation.get("gate_pass") else "[bold red]RETRY RECOMMENDED[/]"

    score_lines = [
        f"[bold yellow]Content Score: {evaluation['content_score']}[/]  {gate}\n",
        f"  Topic Coverage:    {scores['topic_coverage']}",
        f"  Idea Development:  {scores['idea_development']}",
        f"  Logical Flow:      {scores['logical_flow']}",
        f"  Completeness:      {scores['completeness']}",
    ]
    console.print(Panel("\n".join(score_lines), title="[bold]Stage 1: Content Structure[/]", border_style="yellow"))

    if evaluation.get("feedback"):
        console.print(f"\n[bold]Feedback:[/] {evaluation['feedback']}\n")

    if evaluation.get("suggested_outline_en"):
        console.print(Panel(
            evaluation["suggested_outline_en"],
            title="[bold]Suggested English Outline[/]",
            border_style="green",
        ))


def display_key_phrases(phrases: list[str]):
    """Display key phrases prominently for Stage 2 priming."""
    lines = "\n".join(f"  • {p}" for p in phrases)
    console.print(Panel(lines, title="[bold cyan]Key Phrases to Use[/]", border_style="cyan"))


# --- Session Log ---


def save_test_session(topic: dict, transcript: str, evaluation: dict, duration: float, audio_path: Path):
    """Save test mode session."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    session = {
        "mode": "test",
        "timestamp": datetime.now().isoformat(),
        "topic_id": topic["id"],
        "topic": topic["topic"],
        "prompt": topic["prompt"],
        "transcript": transcript,
        "evaluation": evaluation,
        "duration_seconds": round(duration, 1),
        "audio_path": str(audio_path),
    }

    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    path = SESSIONS_DIR / f"{ts}.json"
    path.write_text(json.dumps(session, ensure_ascii=False, indent=2))
    console.print(f"[dim]Session saved: {path}[/]")


def save_practice_session(
    topic: dict, structure_eval: dict, structure_transcript: str, structure_duration: float,
    production_eval: dict, production_transcript: str, production_duration: float,
    structure_audio: Path, production_audio: Path,
):
    """Save practice mode session with both stages."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    session = {
        "mode": "practice",
        "timestamp": datetime.now().isoformat(),
        "topic_id": topic["id"],
        "topic": topic["topic"],
        "prompt": topic["prompt"],
        "stages": {
            "structure": {
                "transcript_l1": structure_transcript,
                "content_score": structure_eval.get("content_score"),
                "scores": structure_eval.get("scores"),
                "key_phrases_en": structure_eval.get("key_phrases_en", []),
                "gate_pass": structure_eval.get("gate_pass"),
                "duration_seconds": round(structure_duration, 1),
                "audio_path": str(structure_audio),
            },
            "production": {
                "transcript_en": production_transcript,
                "evaluation": production_eval,
                "duration_seconds": round(production_duration, 1),
                "audio_path": str(production_audio),
            },
        },
    }

    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    path = SESSIONS_DIR / f"{ts}_practice.json"
    path.write_text(json.dumps(session, ensure_ascii=False, indent=2))
    console.print(f"[dim]Session saved: {path}[/]")


# --- Main: Test Mode ---


def main_test(config: dict):
    """Test mode: full IELTS Part 2 simulation in English."""
    whisper_model = config.get("ai", {}).get("whisper_model", "tiny")
    api_key = config.get("ai", {}).get("anthropic_api_key", "")
    duration = config.get("recording", {}).get("duration_seconds", 120)
    sample_rate = config.get("recording", {}).get("sample_rate", 16000)
    display_lang = config.get("display", {}).get("language", "ja")

    # 1. Topic
    topic = pick_topic()
    display_topic(topic)
    prep_countdown(60)

    # 2. Record
    audio, actual_duration = record_audio(duration=duration, sample_rate=sample_rate)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    audio_path = SESSIONS_DIR / f"{ts}.wav"
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    save_wav(audio, audio_path, sample_rate)

    # 3. Transcribe
    transcript = transcribe(audio_path, model_name=whisper_model, language="en")
    if not transcript:
        console.print("[red]No speech detected. Try again.[/]")
        return

    # 4. Evaluate
    evaluation = evaluate_test(
        topic["prompt"], transcript, display_lang, api_key=api_key, duration=actual_duration,
    )
    display_evaluation(evaluation)
    export_shadow_drills(evaluation, topic)

    # 5. Save
    save_test_session(topic, transcript, evaluation, actual_duration, audio_path)
    console.print("[bold green]Session complete![/] Keep practicing.\n")


# --- Main: Practice Mode (3-Stage) ---


def main_practice(config: dict, tag: str = ""):
    """Practice mode: Structure (L1) → Priming → Production (L2)."""
    whisper_model = config.get("ai", {}).get("whisper_model", "tiny")
    api_key = config.get("ai", {}).get("anthropic_api_key", "")
    duration = config.get("recording", {}).get("duration_seconds", 120)
    sample_rate = config.get("recording", {}).get("sample_rate", 16000)
    display_lang = config.get("display", {}).get("language", "ja")

    # --- Topic ---
    topic = pick_topic(prefix=tag)
    display_topic(topic)

    # === STAGE 1: Structure (L1 Content Planning) — with retry loop ===
    while True:
        console.print("\n[bold magenta]━━━ Stage 1: Structure ━━━[/]")
        console.print("[dim]Speak in your native language. Plan your answer structure.[/]")
        console.print(Panel(
            "[bold]Main Idea[/] — What are you going to talk about?\n"
            "[bold]Reason[/]    — Why is it significant?\n"
            "[bold]Example[/]   — Specific details or story\n"
            "[bold]Closing[/]   — Summary or reflection",
            title="[bold]Framework[/]",
            border_style="magenta",
        ))

        console.print(f"\n[yellow]Record your plan (60s, any language, Ctrl+C to stop)[/]")
        s1_audio, s1_duration = record_audio(duration=60, sample_rate=sample_rate)
        ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        s1_audio_path = SESSIONS_DIR / f"{ts}_s1.wav"
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        save_wav(s1_audio, s1_audio_path, sample_rate)

        # Transcribe L1 (use display language, typically Japanese)
        l1_lang = display_lang if display_lang != "en" else None
        s1_transcript = transcribe(s1_audio_path, model_name=whisper_model, language=l1_lang)
        if not s1_transcript:
            console.print("[red]No speech detected. Try again.[/]")
            return

        # Evaluate structure
        structure_eval = evaluate_structure(
            topic["prompt"], s1_transcript, display_lang, api_key=api_key, duration=s1_duration,
        )
        display_structure_result(structure_eval)

        # === STAGE 2: Lexical Priming ===
        console.print("\n[bold magenta]━━━ Stage 2: Lexical Priming ━━━[/]")

        key_phrases = structure_eval.get("key_phrases_en", [])
        if key_phrases:
            display_key_phrases(key_phrases)
        else:
            console.print("[dim]No key phrases generated. Proceeding to production.[/]")

        # Gate check — retry same topic if structure is weak
        if not structure_eval.get("gate_pass", True):
            choice_input = console.input(
                "[yellow]Content score below 6. Retry structure (r) or continue anyway (c)?[/] "
            ).strip().lower()
            if choice_input == "r":
                console.print("[dim]Retrying Stage 1 with the same topic...[/]")
                continue
        break

    console.print("\n[dim]Take 10 seconds to absorb the key phrases...[/]")
    for i in range(10, 0, -1):
        console.print(f"  [dim]{i}...[/]", end="\r")
        time.sleep(1)

    # === STAGE 3: Production (L2 Speaking) ===
    console.print("\n[bold magenta]━━━ Stage 3: Production ━━━[/]")
    console.print("[bold]Now speak in English.[/] Use the key phrases above.\n")

    if key_phrases:
        display_key_phrases(key_phrases)

    s3_audio, s3_duration = record_audio(duration=duration, sample_rate=sample_rate)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    s3_audio_path = SESSIONS_DIR / f"{ts}_s3.wav"
    save_wav(s3_audio, s3_audio_path, sample_rate)

    # Transcribe L2 (English)
    s3_transcript = transcribe(s3_audio_path, model_name=whisper_model, language="en")
    if not s3_transcript:
        console.print("[red]No speech detected. Try again.[/]")
        return

    # Full IELTS evaluation with key phrases tracking
    production_eval = evaluate_test(
        topic["prompt"], s3_transcript, display_lang,
        api_key=api_key, duration=s3_duration, key_phrases=key_phrases,
    )
    display_evaluation(production_eval)
    export_shadow_drills(production_eval, topic)

    # === Summary ===
    content_score = structure_eval.get("content_score", "?")
    band_score = production_eval.get("overall_band", "?")
    console.print(Panel(
        f"Content Structure: [bold]{content_score}[/]  →  IELTS Band: [bold]{band_score}[/]",
        title="[bold]Practice Session Summary[/]",
        border_style="green",
    ))

    # Save
    save_practice_session(
        topic, structure_eval, s1_transcript, s1_duration,
        production_eval, s3_transcript, s3_duration,
        s1_audio_path, s3_audio_path,
    )
    console.print("[bold green]Practice session complete![/] Keep going.\n")


# --- Entry Point ---


def main():
    """Entry point for kerokero CLI."""
    mode = "test"
    tag = ""
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode not in ("test", "practice"):
            console.print(f"[red]Unknown mode: {mode}[/]")
            console.print("[dim]Usage: kerokero [test|practice] [tag][/]")
            sys.exit(1)
    if len(sys.argv) > 2:
        tag = sys.argv[2]

    mode_label = "Test" if mode == "test" else "Practice (3-Stage)"
    tag_label = f" [{tag}]" if tag else ""
    console.print(f"\n[bold green]kerokero[/] [dim]v0.2.0[/] — IELTS Speaking {mode_label}{tag_label}\n")

    config = load_config()

    if mode == "test":
        main_test(config)
    else:
        main_practice(config, tag=tag)


if __name__ == "__main__":
    main()
