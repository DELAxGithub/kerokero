# kerokero - Speaking Practice CLI (OSS)

自動スピーキング練習パイプライン。Profile → Topic生成 → 録音 → Whisper文字起こし → LLM採点。

## Stack
Python 3.11+ CLI, PyPI公開 (hatchling), MIT License
Dependencies: sounddevice, numpy, scipy, openai-whisper, rich, anthropic

## Modes
ielts-part2 / toefl-integrated / business / shadow / free

## Commands
| コマンド | 用途 |
|---------|------|
| `pytest` | テスト |
| `pip install -e ".[dev,api]"` | 開発インストール |
| `kerokero` | CLI実行 |
