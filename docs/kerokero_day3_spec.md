# kerokero Day 3 — TLR会話シナリオ + ShadowMaster連携

## Today's Story

Day 2: practiceモード実装、Band 4.5×2。発話量・タスク要件・時制が課題。
月曜にTLR（Tandem Language Reunion）で初対面会話がある。
Day 3: TLR用の会話シナリオ4本を追加し、土日で集中練習できるようにする。
追加で、採点フィードバックからShadowMaster用ドリルを自動生成する機能を実装。

---

## 実装済み

### 1. TLR会話シナリオ追加 [DONE]

**ファイル**: `topics/ielts.json`

| ID | Topic |
|----|-------|
| tlr-001 | Where are you from? |
| tlr-002 | How long have you been in Malaga? |
| tlr-003 | What do you do? |
| tlr-004 | How did you end up in Malaga? |

既存IELTSフォーマット（id/topic/prompt/suggested_angles）にそのまま追加。
全24トピック（IELTS 20 + TLR 4）。

### 2. プレフィックスフィルタ選択 [DONE]

**ファイル**: `src/kerokero/main.py`

```
kerokero practice tlr   → tlr-*** のみ選択
kerokero practice       → 全トピックからランダム
kerokero test           → 従来通り
```

- `pick_topic(prefix="")` — 第2引数でIDプレフィックスフィルタ
- `main()` で `sys.argv[2]` をタグとして取得
- `main_practice(config, tag="")` に渡す

### 3. ShadowMaster連携ドリル自動生成 [DONE]

**ファイル**: `src/kerokero/main.py`

- EVALUATOR_SYSTEM_PROMPT に `shadow_drills` フィールド追加
  - 「苦手だった/避けたフレーズ3つを自然な英語で提示」
  - 各フレーズ5〜10語、会話調
- `export_shadow_drills(evaluation, topic)` 関数追加
  - ShadowMaster互換JSON出力: `~/.kerokero/sessions/{ts}_drills.json`
- test/practice 両モードの `display_evaluation()` 直後に呼び出し

出力フォーマット:
```json
{
  "folder": {
    "name": "{topic} — ドリル {YYYY-MM-DD}",
    "sentences": [
      {"id": "drill-001", "text": "フレーズ", "translation": "", "chunks": []}
    ]
  }
}
```

---

## やらなかったこと（スコープ外）

- 評価プロンプトのTLR専用分岐（既存IELTS採点で練習は成立する）
- テスト更新
- YAML移行
- CLIコマンド追加（argparse等）
- ShadowMaster側の変更
- translation・chunksの自動生成

---

## 検証

```bash
# TLRフィルタ確認
.venv/bin/python -c "
from kerokero.main import pick_topic
for _ in range(10):
    t = pick_topic('tlr')
    assert t['id'].startswith('tlr-')
    print(t['id'], t['topic'])
"

# ShadowMasterドリル出力確認
.venv/bin/python -c "
import json
from kerokero.main import export_shadow_drills
eval_data = {'shadow_drills': ['I moved here for a fresh start', 'That sounds great', 'What brought you here']}
topic = {'id': 'tlr-001', 'topic': 'Where are you from?'}
path = export_shadow_drills(eval_data, topic)
print(json.dumps(json.loads(path.read_text()), indent=2, ensure_ascii=False))
path.unlink()
"

# 実際に練習
kerokero practice tlr
```
