# CLAUDE.md — AI Health Check-in Copilot (Hackathon Prototype)

## What this project is

An AI copilot for at-home chronic-condition management. It combines objective
wearable/home-measurement data with subjective info from short AI-led phone
check-ins, compares both against a personal baseline, detects subtle
multi-signal deterioration, and produces patient-facing + clinician-facing
(SBAR) summaries. **Decision-support prototype, not a medical device — never
label output as a diagnosis.**

The full original product spec (screens, safety requirements, data model,
assessment logic, priorities) was supplied by the user as a long prompt — the
key points are captured here and in [PROGRESS.md](PROGRESS.md). Current
progress and next steps live in **[PROGRESS.md](PROGRESS.md)** — read it
before doing anything.

## Demo story (P0)

Fictional patient **Maya Patel**, 46, type 2 diabetes, recently started GLP-1
programme. 14-day personal baseline. Over the last 4 days: resting HR slightly
up, sleep down, steps down, food/fluid intake down, weight falling slightly
faster than expected — **no single value crosses an emergency threshold**.
A check-in call uncovers reduced intake + dizziness → status "Needs review" →
safe predefined next step + clinician SBAR summary → event on timeline.
Story must land in ~90 seconds.

## Decisions already made with the user (do NOT re-ask)

1. **LLM provider: Runware.ai** (`RUNWARE_API_KEY`). Runware's `textInference`
   task offers Claude/GPT-class models via REST/WebSocket with OpenAI
   compatibility. It has TTS but **no STT and no realtime speech-to-speech**.
   Use a fast model for live conversation turns, a stronger model for
   post-call extraction/SBAR. Make model ids configurable in `.env`.
2. **Telephony: full live AI voice call is the headline goal**, via **Twilio
   ConversationRelay** (Twilio does STT+TTS on the call, streams caller text
   to our WebSocket; we reply with text from the LLM → no extra voice keys).
   User has **no Twilio account yet** — build the adapter so credentials can
   just be pasted into `.env`; document exactly what to buy/configure
   (trial account, voice-capable number, verify own mobile as destination).
3. **Also build the in-browser simulated call** as an instant fallback demo
   mode (same UI/pipeline, scripted branching patient responses, browser TTS
   via Web Speech API so it's audible). Demo mode must work with zero keys.
4. **Webhooks**: GitHub Codespaces public port forwarding (this is a
   Codespace). Demo call target: the user's own phone.
5. **Old repo content (flute/music notebooks) deleted** — already `git rm`'d,
   not yet committed. This is now a greenfield Next.js app at the repo root.
6. **Stack: Next.js 15 + TypeScript (strict, no `any`) + Tailwind, SQLite +
   Prisma, Zod, Recharts, Vitest, lucide-react.** src-dir layout, `@/*` alias,
   npm, no turbopack.

## Architecture (planned)

Provider interfaces keep integrations replaceable:
`CallProvider`, `TranscriptionProvider`, `ConversationAgent`,
`HealthDataProvider`, `AssessmentEngine`.

- **Demo mode (no keys)**: simulated call in browser, scripted adaptive
  conversation, streaming transcript, browser TTS, seeded wearable data.
- **Live mode (keys present)**: server endpoint initiates Twilio outbound
  call → ConversationRelay WebSocket ⇄ our Node server ⇄ Runware LLM.
  Next.js API routes don't do raw WebSockets — use a custom `server.js`
  (Node + `ws`) alongside Next, or a small standalone ws server. Validate
  Twilio webhook signatures. Never expose credentials to the browser.
  Never auto-dial: explicit button + recipient confirmation required.
- **Assessment is deterministic** (safety-critical): personal-baseline
  deviation calcs, multi-signal deterioration score (label as demo
  heuristic), red-flag rules in a separate auditable config module,
  explanation of evidence, explicit uncertainty. LLM only summarizes/
  extracts — it must never be the sole trigger for urgent escalation.
- Statuses: Stable / Monitor / Needs review / Urgent escalation.

### Screens (all responsive, calm clinical design, no dashboard clutter)

1. **Patient dashboard** — identity, status+confidence, "Start check-in call",
   last contact, alerts, baseline-vs-current, 7/14-day charts (RHR, sleep,
   steps, weight, glucose, fluid intake), "simulated data" labels.
2. **Live call workspace** — call state machine (ready/dialling/connected/
   completed/failed), duration, live transcript (Patient vs AI), current
   question, incoming metrics, structured facts extracted live, operator
   emergency/escalation control.
3. **Post-call assessment** — summary, structured answers, red flags,
   objective trend evidence, subjective/objective reconciliation, status +
   confidence + missing info, recommended next step, patient explanation,
   clinician SBAR, full transcript + metadata.
4. **Patient timeline** — readings, symptoms, calls, assessments, alerts,
   interventions, subsequent trajectory.

## Safety requirements (must be visible in UI)

- "Prototype — not a medical device." / "This assessment does not provide a
  diagnosis."
- Emergency symptoms → clear urgent-help instruction (UK framing: 999 for
  emergency, NHS 111 for urgent advice).
- Agent identifies itself as an automated health assistant; consent before
  collecting health info / recording; support opt-out & ending the call.
- Never dismiss subjective symptoms because wearables look normal.
- No autonomous medication changes; recommendations only from predefined
  care-plan rules. Minimise sensitive data in logs. Fictional data only.

## Commands

- `npm run dev` — dev server
- `npm run build` / `npm run lint` — must pass before "done"
- Vitest for tests (`npx vitest run`) — test baseline deviations,
  multi-signal score, every red-flag rule, malformed/missing observations,
  conflicting evidence, transcript→structured parsing, webhook validation,
  full seeded demo flow.

## Working conventions

- Extend, don't replace, working code. Small verifiable stages.
- `.env.example` always up to date; never commit secrets.
- Deliverables include README (concept, architecture, setup, demo script,
  env vars, live-call setup, safety boundaries, real-vs-simulated), Mermaid
  architecture diagram, list of deliberate shortcuts.
- Keep [PROGRESS.md](PROGRESS.md) updated as stages complete.
