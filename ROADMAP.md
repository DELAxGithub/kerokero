# kerokero Roadmap

## Current: v0.3 — Coach Mode

「会話エンジンを作らない。採点エンジンに徹する」 → [docs/specs/v0.3-coach-mode.md](docs/specs/v0.3-coach-mode.md)

### Week 1
- [x] `kerokero analyze --audio FILE [--profile NAME] [--topic ...]`
- [x] `profiles/sales_english.toml`
- [x] v0.3 spec doc
- [x] `export_shadow_drills()` を ShadowMaster v1.2 importer 互換のフラット配列形式に修正 (default accent=en-GB)

### Week 2
- [ ] iPhone 録音 → analyze → ShadowMaster Tab 1 取り込み の手動運用1週間
- [ ] `<ts>_drills.json` を実機 ShadowMaster で動作確認

### Week 3+ (条件付き)
- [ ] `kerokero progress --weeks N`
- [ ] `kerokero examiner --backend gemini-live` (realtime API ラッパー)
- [ ] iOS 録音 → Mac inbox 自動転送経路
- [ ] 着手条件: Week 1-2 ループが実運用で回っていること

## ShadowMaster (iOS) との関係

ShadowMaster v1.2 は3タブ構成 (Shadowing / Speaking / Instant Translation) に進化済み。Tab 2 は kerokero test mode と機能が重なるが、**並走させて場面で使い分け**る方針。詳細は [docs/specs/v0.3-coach-mode.md](docs/specs/v0.3-coach-mode.md#shadowmaster-ios-との役割分担) を参照。

`kerokero drill` サブコマンドは **ShadowMaster Tab 3 (瞬間英作文) がカバー済みのため永久封印**。代わりに `kerokero analyze` の弱点フレーズを ShadowMaster 互換 JSON で出力 → Tab 1 でシャドーイング、というパイプを使う。

## Past

### v0.2 (released)
- Test mode (60s prep + 120s record + IELTS evaluation)
- Practice mode (Structure → Priming → Production の3段階)
- ShadowMaster 互換ドリル出力

## Sealed (永久封印)

撤退判断の根拠: `../scratch/localtts/RESULTS.md`

- ローカル Examiner 会話モード (双方向ストリーミング)
- Kokoro MLX / その他ローカル TTS 統合
- Silero VAD / barge-in
- 低遅延 TTS 一般

理由: ChatGPT Advanced Voice (~320ms) や Gemini Live (~600ms) に段組みパイプラインで勝つのは構造的に不可能。会話エンジンは外部に外注し、kerokero は採点に集中する。
