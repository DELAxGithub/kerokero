# ADR 0002: External Triggers and Async Evaluation Loop

- Status: Proposed
- Date: 2026-05-01
- Deciders: project owner（AI と協議）

## Context

kerokero v0.3 Coach Mode は CLI として完成しているが、**ユーザー（プロジェクトオーナー本人）が
そもそも録音を始めない**ことが Week 2 進捗停滞の根本原因になっている
（`docs/specs/v0.3-coach-mode.md` Week 2 ⏳ 進行中、kerokero メモリ参照）。

観察された事実:

- shadow_master は streak / FSRS / fluency points で継続している
- delax100daysworkout は fitness chart で見える化、自転車到着で再開予定
- tachi-tracker は **cron で勝手に snapshot** することで、ユーザー opt-in 不要で動いている
- kerokero は「思い立ったときに `kerokero analyze` を叩く」設計で、思い立たないと動かない

達成要素（streak / バッジ / グラフ）は **既にやっている行動の継続** には効くが、
**やらない行動を始めさせる** 効果は薄い。kerokero の現状は後者なので、
ゲーミフィケーションだけ足しても達成バッジが貯まらない画面が増えるだけになる。

先に解くべきは活性化エネルギー — **外から殴ってくる仕組み** が必要。

## Decision

kerokero に以下の3層を導入する:

1. **外部トリガー層 (Cron + Prompt 配信)**
   - Cloudflare Worker + KV + cron（tachi-tracker と同じ stack）で毎朝お題を生成
   - 配信先: メール / Push 通知 / Obsidian Daily Note の `## 今日の kerokero お題` セクション
   - お題は profile（sales_english / ielts-part2 など）と直近の弱点傾向から選ぶ

2. **録音 inbox 層 (iPhone → Mac 自動転送)**
   - iPhone のボイスメモ or Shortcuts で録音 → iCloud Drive / Dropbox の `kerokero-inbox/` に置く
   - Mac 側で `launchd` または `fswatch` で inbox を監視
   - 新ファイル検知 → 自動で `kerokero analyze --audio FILE` をキック

3. **非同期評価 + 翌朝ダイジェスト層**
   - analyze 結果は寝てる間に走る（人間のリアルタイム待機は不要）
   - 翌朝の Daily Note に **昨日の録音 → 採点結果 → drill カード** をまとめて表示
   - ここで初めて達成要素（連続日数 / 累計分数 / fluency 推移）を載せる
     ※ 報酬は「やった後」に効くため、活性化問題が解けた後に意味を持つ

## Alternatives Considered

1. **達成要素（streak / バッジ）から先に実装** — 却下。
   ユーザー opt-in しない問題を解いていない。達成バッジが貯まらない画面が増えるだけ。

2. **shadow_master Tab 2 に kerokero を統合** — 却下。
   v0.3 Coach Mode で「採点エンジンに徹する」と決めた責務分離（ADR 相当の方針）を崩す。
   shadow_master 側で録音、kerokero 側で深い採点という責務は維持する。

3. **Realtime API (gemini-live) で対話練習に進む** — 却下（少なくとも今は）。
   Week 3+ の examiner モード候補だが、活性化問題が解けていない段階で realtime に進んでも
   「レアな思い立ち」を増やすだけ。realtime は活性化が解けた後の上積み。

4. **既存 CLI のまま放置** — 却下。
   Week 2 で停止して 2 週間以上経っており、**自分の腰が重いプロダクトは
   ユーザー視点の検証不足のサイン**（fixing UX 観点）。

## Consequences

**Pros**:

- ユーザー opt-in 不要で「録音する → 結果が翌朝出る」ループが回る
- 達成要素を後から載せたとき、報酬として効く土台ができる
- Cloudflare Worker + cron は `reference_cloudflare-baseline` / tachi-tracker で踏破済、新規学習コスト低
- kerokero CLI 本体（v0.3 採点エンジン）は触らない — 周辺 inbox + 通知だけ追加するので責務分離が保たれる
- iPhone 録音 → Mac inbox の経路が完成すれば、**他の音声系プロジェクト
  (platto / tachi-shorts / walking-tour) でも再利用できる汎用インフラ** になる

**Cons**:

- Cloudflare Worker / inbox 監視 / Daily Note 連携と **3つの新しい層** を導入するため、
  失敗ポイントが増える（特に inbox 監視の信頼性）
- 録音は iPhone のボイスメモ依存、ファイル形式・命名規則の標準化が必要
- 「毎朝お題が来る」が **uninstall を増やす圧力** にもなりうる
  → スヌーズ / 一時停止フラグを最初から仕込む

## Related

- ADR-0001 — Record architecture decisions（このリポの ADR 運用）
- `docs/specs/v0.3-coach-mode.md` — Week 2 停滞の現状、Week 3+ 候補
- tachi-tracker（DELAxGithub/tachi-tracker）— Cloudflare Worker + KV + cron の参照実装
- メモリ `reference_cloudflare-baseline` — 弊社 Cloudflare ベース構成
- メモリ `cloudflare-workers-stripe-stack` — ソロ開発の最小コスト stack
- shadow_master — 達成要素（streak / FSRS）の参照実装、後段で借りる

## Open Questions

このまま実装に進む前に決めるべき点（Conflict Report 候補）:

1. **配信先は何にするか** — メール / Push / Obsidian Daily Note のどれを first delivery にするか
2. **inbox の置き場所** — iCloud Drive / Dropbox / `~/Documents/agent-work`（Syncthing）どれにするか
3. **Cloudflare Worker は新規 worker を立てるか、tachi-tracker に同居させるか**
4. **analyze 自動実行のリスク** — inbox に意図せぬ音声（家族の声 / 他人の会話）が入った場合の扱い
