# kerokero Day 2 — Practice Mode Implementation

## Today's Story

Day 1: Built pipeline, ran 2 sessions, scored Band 4.5 twice.
Problem identified: content generation + English production simultaneously = cognitive overload.
Overnight: commissioned AI research on pre-task planning in L2 speaking.
Research confirms: separating content planning from L2 production is well-supported.
Day 2: implement practice mode, then PRACTICE WITH IT (minimum 3 sessions).

**CRITICAL RULE: Implementation must be done by lunch. Afternoon = speaking practice.**

---

## Research Summary (for context, not for implementation)

Key findings from L2 speaking research:

1. **Cognitive load theory supports staged approach**
   - Levelt's Speech Production Model: "conceptualization" (what to say) and
     "formulation" (how to say it in L2) compete for cognitive resources
   - Pre-task planning in L1 frees resources for L2 formulation
   - Ellis (2005, 2009): planning time improves fluency and complexity

2. **Critical insight from IELTS teaching professionals**
   - L1 planning should NOT be free-form sentences (creates translation habit)
   - L1 planning should be BULLET POINTS / LOGIC NODES only
   - Structure: Main Idea → Reason → Example → Closing
   - "You're not writing a script, you're building a skeleton"

3. **Recommended implementation: 3-stage pipeline**
   - Stage 1 (Structure): L1 bullet points, AI checks logic only
   - Stage 2 (Priming): AI suggests 3-5 English keywords from the L1 plan
   - Stage 3 (Production): Full L2 speaking with standard IELTS evaluation

Save full research to `docs/research/pre-task-planning.md` (content at bottom of this file).

---

## Implementation Spec

### CLI interface

```
kerokero              → test mode (existing, unchanged)
kerokero practice     → new 3-stage practice mode
```

Simple `sys.argv` check in `main()`. No click, no argparse.

### Stage 1: Structure (L1 Content Planning)

**User experience:**
1. Topic card displayed (same as test mode)
2. Prompt: "60秒で構成を声に出して考えてください（日本語OK）"
3. Display framework on screen:
   ```
   🎯 Main Idea — 何について話す？
   💡 Reason   — なぜ？
   📖 Example  — 具体的には？
   🔚 Closing  — まとめ・感想
   ```
4. Record 60 seconds (same recorder as test mode)
5. Transcribe with Whisper (language=None for auto-detect, or config native_language)
6. Send to Claude for LOGIC-ONLY evaluation

**Stage 1 evaluation prompt:**

```
You are evaluating the LOGICAL STRUCTURE of an IELTS Speaking Part 2 response plan.
The plan is in the speaker's native language. Do NOT evaluate language quality.

Evaluate ONLY:
1. Topic Coverage (0-9): Does the plan address all parts of the topic card?
2. Idea Development (0-9): Are ideas specific enough? (not vague/generic)
3. Logical Flow (0-9): Is there a clear progression? (not random jumping)
4. Completeness (0-9): Could this fill 2 minutes when spoken in English?

Topic card: {topic_prompt}
Speaker's plan (transcribed, may be in Japanese or mixed language):
{transcript}

Respond in JSON:
{
  "content_score": 7.0,
  "scores": {
    "topic_coverage": 7,
    "idea_development": 6,
    "logical_flow": 7,
    "completeness": 8
  },
  "feedback": "Brief feedback in Japanese on the logical structure",
  "suggested_outline_en": "If you were to say this in English, a strong structure would be: ...",
  "gate_pass": true
}

Set gate_pass to true if content_score >= 6.0.
```

### Stage 2: Lexical Priming

**User experience:**
1. Display Stage 1 results briefly
2. If gate_pass is false: show feedback, offer to retry Stage 1 or continue anyway
3. Extract 5 English keywords/phrases from the suggested_outline_en
4. Display them prominently:
   ```
   ╭─ 🔑 Key phrases to use ─╮
   │  • exceeded expectations  │
   │  • cultural depth         │
   │  • what struck me was     │
   │  • in contrast to         │
   │  • looking back           │
   ╰───────────────────────────╯
   ```
5. Brief pause (10 seconds) for user to absorb

**Implementation:**
- Keywords come from a second Claude call OR extract from suggested_outline_en
- Simpler option: include keyword extraction in Stage 1 prompt (add to JSON output):
  ```
  "key_phrases_en": ["exceeded expectations", "cultural depth", "what struck me was", "in contrast to", "looking back"]
  ```
  This saves an API call. Do this.

So update Stage 1 prompt to also output `key_phrases_en` (5 Band 7+ phrases the speaker should try to use).

### Stage 3: Production (L2 Speaking)

**User experience:**
1. Key phrases remain displayed on screen during recording
2. "Now speak in English. 120 seconds. Use the key phrases above."
3. Record 120 seconds (same as test mode)
4. Transcribe with Whisper (language="en")
5. Evaluate with FULL IELTS criteria (same prompt as test mode)
6. ADDITIONAL evaluation: did the speaker use any of the key phrases?

**Modification to existing test mode evaluation prompt:**
Add to the user message:
```
The speaker was given these key phrases to incorporate: {key_phrases}
In your evaluation, note which phrases were used and which were missed.
Add a "key_phrases_used" field to your JSON response listing the phrases that appeared.
```

### Session Log

Extend existing session JSON:

```json
{
  "mode": "practice",
  "timestamp": "...",
  "topic": { ... },
  "stages": {
    "structure": {
      "transcript_l1": "...",
      "content_score": 7.0,
      "scores": { ... },
      "key_phrases_en": [ ... ],
      "gate_pass": true
    },
    "production": {
      "transcript_en": "...",
      "band_score": 5.5,
      "scores": { ... },
      "key_phrases_used": [ ... ]
    }
  }
}
```

### Display Functions

Two new display functions:

1. `display_structure_result(evaluation)` — Stage 1 results
   - Content score panel
   - 4 criteria with scores
   - Gate pass/fail indicator
   - Suggested English outline
   - Key phrases for next stage

2. `display_practice_result(structure_eval, production_eval)` — Final results
   - Side by side: content score vs band score
   - Key phrases: used ✓ / missed ✗
   - Combined feedback
   - "Your content was X, your English delivery was Y"

---

## Files to Create/Modify

- `src/kerokero/main.py` — add practice mode flow, new prompts, new display functions
- `topics/ielts.json` — no changes
- `docs/research/pre-task-planning.md` — new file (research findings)
- `README.md` — add Practice Mode section

---

## What NOT to do

- No separate files for practice mode (keep it all in main.py for now)
- No abstract classes or base evaluators
- No async
- No TTS
- No `kerokero log` (save for later)
- No config changes needed (reuse existing anthropic_api_key and whisper_model)

---

## Verification

```bash
# Test mode still works
kerokero

# Practice mode works end-to-end
kerokero practice
# → Topic appears
# → 60s L1 recording (talk about structure in Japanese)
# → AI evaluates logic, shows key phrases
# → 120s L2 recording (speak in English)
# → Full IELTS evaluation
# → Session saved

# Run practice mode minimum 3 times today
```

---

## Appendix: Research Findings (save as docs/research/pre-task-planning.md)

```markdown
# Pre-Task Planning Research for kerokero Practice Mode

## Core Question
Is separating content planning (L1) from L2 production an effective strategy
for improving IELTS Speaking Part 2 performance?

## Key Findings

### 1. Cognitive Load & Pre-task Planning
- Levelt's Speech Production Model identifies three stages: Conceptualization
  (deciding what to say), Formulation (encoding in L2), Articulation (speaking)
- For non-native speakers, Conceptualization and Formulation compete for
  working memory resources
- Ellis (2005, 2009): pre-task planning significantly improves fluency and
  syntactic complexity in L2 oral output
- Skehan & Foster: planning leads to greater complexity but not always accuracy
- **Implication for kerokero**: Separating content planning from L2 production
  is theoretically sound

### 2. IELTS-Specific Methods
- Established IELTS prep methods emphasize "note-taking" during 1-minute prep
- Top instructors recommend bullet points, NOT full sentences
- "Topic linking" (steering topics to prepared stories) is a recognized and
  legitimate strategy
- Common progression: structure first → fluency → accuracy → naturalness
- **Implication for kerokero**: bullet-point structure check aligns with best practice

### 3. Content-First Approaches (TBLT)
- Task-Based Language Teaching uses pre-task → task → post-task stages
- L1 use in pre-task phase is debated but generally accepted for lower levels
- Risk: L1 dependency / translation habits if L1 planning involves full sentences
- Mitigation: restrict L1 planning to logical structure, not linguistic content
- **Implication for kerokero**: L1 planning must be NODE-based (bullet points),
  not sentence-based

### 4. Counterarguments & Risks
- Over-reliance on L1 planning may slow development of L2 thinking
- Translation habits: planning in L1 sentences → unnatural L2 output
- Some research suggests L2 planning is more effective for advanced learners
- **Risk mitigation**: gate system that graduates users to L2-only planning
  as scores improve. Restrict L1 input to logical structure only.

### 5. Verdict
- Research supports kerokero's practice mode design: YES
- Key modification: L1 planning must be bullet-point logic, not full sentences
- Lexical priming (providing L2 keywords) bridges the L1→L2 gap
- Confidence level: HIGH for the staged approach, MEDIUM for specific implementation
```

---

## Reminder

Implementation = morning.
Practice sessions (minimum 3) = afternoon.
Note post = evening.
If you finish early, do more practice sessions, not more features.
