# PsicoChat

A web app to talk with an AI (via the OpenAI API) as a therapeutic
support space. Minimal onboarding (name + age only, so as not to bias
the system with extra data), sessions that feel discrete day-to-day but
share memory in the background.

See also [`CASE_STUDY.md`](./CASE_STUDY.md) — a portfolio-style summary
of the design decisions behind this project.

## Status: all 4 phases complete, plus a login/signup split

**Phase 1 — core functionality:**
- FastAPI backend with an age gate (`/onboarding`) and a chat endpoint (`/chat`)
- The system prompt lives in `backend/prompts/system_prompt.txt` (kept out
  of the public repo — see `system_prompt.example.txt`)
- React (Vite) frontend with two screens: onboarding and chat

**Phase 2 — memory and continuity:**
- `username` + `password` fields at onboarding identify the person's
  evolving profile across sessions and devices. The password is stored
  hashed (PBKDF2-HMAC-SHA256 with a salt) — never in plain text.
- An evolving profile per `username`, with a `profile_summary` updated
  every time a session is closed.
- A "Finalizar sesión de hoy" (end today's session) button, plus an
  automatic fallback via `navigator.sendBeacon` if the tab is closed
  without pressing it.
- The `profile_summary` is always appended AFTER the static block of the
  system prompt, so it doesn't break OpenAI's prompt caching.

**Phase 3 — risk detection, robustness and streaming:**
- **Risk detection** (`backend/app/risk.py`): every message is classified
  with the cheaper auxiliary model to detect signs of self-harm, suicidal
  ideation, risk toward others, or immediate danger. This is an
  ADDITIONAL layer on top of what the system prompt itself already asks
  for in its own "CUANDO ESTÉ MUY ANGUSTIADO" section — it doesn't
  replace it. If the classifier fails technically, it doesn't block the
  conversation (fail-safe).
- **Geolocated help resources** (`backend/app/resources.py`): if risk is
  detected, a list of resources is put together based on the city
  entered at onboarding (simple keyword matching — currently only
  distinguishes Argentina from a generic international fallback). Shown
  as a fixed banner in the UI, not just as text from the model.
- **Streaming responses** (`POST /chat/stream`): the model's reply is
  shown token by token via Server-Sent Events. `POST /chat` (no
  streaming) still exists as a simpler alternative for debugging.
- **Error handling**: configurable timeout on OpenAI calls, friendly
  error messages if the API fails, without breaking the session.

**Phase 4 — SQLite and deploy:**
- Storage migrated from plain JSON files to **SQLite**
  (`backend/promptpsyco.db`, a single file), with the same public
  interface the rest of the code already used — no need to touch
  `chat.py`.
- `Procfile` and `render.yaml` to deploy the backend on Render or
  Railway.
- Ready to deploy the frontend on Vercel (auto-detects Vite, no extra
  config beyond one environment variable).

**Added afterward — separate login/signup:**
- The onboarding screen now asks first whether the person already has an
  account ("Ya tengo cuenta") or is new ("Soy nuevo/a"). Returning users
  only need username + password; new users also provide name, age and
  city.
- No password recovery — acceptable for personal, single-user use;
  flagged as a real gap if this were ever opened to more people.

## Running it locally

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # on Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# fill in OPENAI_API_KEY in .env, and provide your own
# prompts/system_prompt.txt (see system_prompt.example.txt)
uvicorn main:app --reload --port 8000
```

`backend/promptpsyco.db` (SQLite) is created automatically on first run
— no manual migration step needed.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open `http://localhost:5173`.

## How to test the full flow

1. Start backend and frontend (steps above).
2. On the onboarding screen, choose "Soy nuevo/a" and complete name,
   username, password, age, and optionally city.
3. Send a couple of messages — the reply should appear word by word
   (streaming), not all at once.
4. Click "Finalizar sesión de hoy" — it should return automatically to
   the initial screen.
5. Choose "Ya tengo cuenta" this time, with the same username and
   password. In the next message, mention something related to the
   previous session to check whether the model picks it up (cross-session
   memory).
6. Try logging in with the right username but a wrong password — it
   should be rejected.
7. Write a message with an explicit risk signal — a help-resources banner
   should appear above the messages, in addition to the model's normal
   reply. Also try a clearly non-literal phrase to confirm the banner
   doesn't trigger unnecessarily.

## How to deploy (when you're ready to make it public)

### Backend (Render or Railway)

- **Render**: connect the repo, pick `backend/` as the service root.
  `render.yaml` already defines the environment variables
  (`OPENAI_API_KEY` has to be entered manually in the dashboard, never in
  the repo). **Important**: Render's free tier has an ephemeral
  filesystem — `promptpsyco.db` is lost on every redeploy or restart
  unless you add a persistent disk (a paid feature). Acceptable for a
  portfolio demo; for real use, add the disk or migrate to a managed
  database.
- **Railway**: auto-detects the `Procfile`. Railway's persistent volumes
  are available even on its free tier with limits — a better option if
  you want the SQLite file to survive restarts without paying upfront.

### Frontend (Vercel)

- Connect the repo, pick `frontend/` as the root. Vercel auto-detects
  Vite.
- Set the `VITE_API_BASE` environment variable in the Vercel dashboard,
  pointing to the deployed backend's public URL.
- On the backend, update `FRONTEND_ORIGIN` to the Vercel URL (so CORS
  allows it).

## About cost (personal use, with your own API key)

- The system prompt (~5,000 tokens) is sent on every call, but OpenAI
  automatically caches the repeated static prefix across calls (a large
  discount on that portion) — that's why the profile summary is always
  appended AFTER the fixed block, never mixed in.
- Session summaries and risk detection use the cheaper model
  (`gpt-4o-mini`), not the main one.
- For occasional personal use, total estimated cost is a few dollars a
  month. Setting a monthly spending cap in the OpenAI dashboard is still
  good practice, just in case.

## Design decisions worth keeping in mind

- **Only name and age at onboarding**: a deliberate choice to avoid
  biasing the system with extra information.
- **Underage → doesn't start**: if the entered age is under 18, no
  session or profile is created, and nothing about the attempt is
  stored.
- **Session (UI) vs. memory (context)**: every visit is a fresh session
  visually (a new greeting), but in the background the system accumulates
  an evolving profile from summaries of previous sessions.
- **Own API key, not built to scale to other users**: accepted on
  purpose for this stage (portfolio / personal use). Evaluate a paid
  membership (Stripe) or a bring-your-own-key (BYOK) scheme later if this
  ever opens up to more people.
- **Username + password with no recovery**: enough for personal use; not
  real auth if this project were opened up to more people.
- **Optional city at onboarding**: so geolocated help resources can be
  suggested without asking for exact browser location.
