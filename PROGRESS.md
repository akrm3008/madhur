# PROGRESS.md — build state as of 2026-07-18

Companion to [CLAUDE.md](CLAUDE.md) (read that first for context/decisions).

## Done

- [x] Inspected repo: old content was unrelated flute/music notebooks; git
      history (Gradio/Gemini audio streaming) is from a different experiment.
- [x] Clarifying Q&A with user — all decisions recorded in CLAUDE.md
      ("Decisions already made", do not re-ask).
- [x] Verified Runware capabilities (LLM chat + TTS; **no STT**, no realtime
      voice) → chose Twilio ConversationRelay for the live voice layer.
- [x] `git rm -r madhur/` (notebooks deleted; **not yet committed**).
- [x] Scaffolded Next.js 15 + TS + Tailwind + ESLint, src-dir, `@/*` alias,
      npm, no turbopack, at repo root (create-next-app@15). `node_modules`
      installed by the scaffold.

## Not done yet (next step first)

- [ ] **NEXT:** install remaining deps —
      `npm install @prisma/client zod recharts lucide-react twilio ws`
      and `npm install -D prisma vitest tsx @types/ws`
- [ ] Prisma schema (SQLite) + seed script for Maya's 14-day dataset
      (models: Patient, Condition, PatientBaseline, HealthObservation, Call,
      TranscriptSegment, QuestionnaireResponse, Assessment, RiskFactor,
      Intervention, TimelineEvent, ConsentRecord; observations carry metric
      type/value/unit/timestamp/source/provenance/isSimulated/quality)
- [ ] Assessment engine (deterministic): baseline deviation, multi-signal
      score (demo-heuristic label), red-flag rules in separate auditable
      config, evidence explanations, uncertainty handling
- [ ] Provider interfaces (CallProvider, TranscriptionProvider,
      ConversationAgent, HealthDataProvider, AssessmentEngine)
- [ ] Demo conversation agent: scripted adaptive branching + structured
      extraction; optional Runware LLM adapter behind env flag
- [ ] Screen 1: patient dashboard + Recharts baseline-vs-current charts
- [ ] Screen 2: live call workspace (simulated call, streaming transcript,
      browser TTS, operator escalation control)
- [ ] Screen 3: post-call assessment (+ patient & SBAR summaries)
- [ ] Screen 4: patient timeline
- [ ] Live mode: Twilio ConversationRelay adapter — outbound call endpoint,
      webhook signature validation, ws server (custom server.js), Runware
      textInference client; explicit confirm-before-dial UX
- [ ] Vitest tests (see CLAUDE.md test list)
- [ ] README + .env.example + Mermaid diagram + shortcuts list
- [ ] `npm run lint` + `npm run build` + tests green; run app end-to-end
      and fix what's found
- [ ] Commit(s) — nothing has been committed yet, including the notebook
      deletion

## Environment notes

- GitHub Codespace, Node v24.14.0, npm 11.9.0. Git branch: `emed`
  (remote default branch: `audio-streaming`).
- User will supply `RUNWARE_API_KEY`; Twilio account/number not yet created —
  live-call adapter must be paste-creds-and-go, with setup docs.
- Codespaces public port forwarding will expose webhook/ws endpoints for
  Twilio (`gh codespace ports visibility <port>:public`).
