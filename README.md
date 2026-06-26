# IELTS Writing Bot

Telegram bot for IELTS Writing Task 1 & 2: AI-generated band-9 sample answers
(Write mode) and real IELTS-criteria band scoring + feedback (Assess mode).

## Stack
- Python 3.11+ / aiogram 3 (webhook mode)
- SQLite (via SQLAlchemy async) — swap `DATABASE_URL` for Postgres later if needed
- OpenRouter (free models, with automatic fallback list) for all AI calls
- Render free tier for hosting + an external keep-alive ping

## Local setup

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# now edit .env with your real BOT_TOKEN, LOG_CHANNEL_ID, OPENROUTER_API_KEY
```

### Getting the values you need

1. **BOT_TOKEN** — message [@BotFather](https://t.me/BotFather) on Telegram, `/newbot`, follow prompts.
2. **LOG_CHANNEL_ID** — create a private Telegram channel, add your bot as an
   admin (needs "Post Messages" permission), then get the channel ID. Easiest
   way: forward any message from the channel to [@JsonDumpBot](https://t.me/JsonDumpBot)
   or similar, look for `"chat":{"id": -100...}`. It will be a negative number.
3. **OPENROUTER_API_KEY** — sign up free at [openrouter.ai](https://openrouter.ai),
   go to Keys, create one. No credit card needed for free models.
4. **WEBHOOK_BASE_URL** — leave blank for local testing (see "Local testing"
   below); set to your Render URL once deployed.

## Local testing (without a public webhook)

Webhooks need a public HTTPS URL, which you don't have on localhost. Easiest
fix for local dev: use a tunnel tool (e.g. `ngrok http 8080`) and set
`WEBHOOK_BASE_URL` to the ngrok URL it gives you, then run:

```bash
python main.py
```

## Deploying to Render (free tier)

1. Push this code to a GitHub repo.
2. On [render.com](https://render.com), create a new **Web Service**, connect
   the repo.
3. Build command: `pip install -r requirements.txt`
   Start command: `python main.py`
4. Add all the environment variables from `.env` in Render's dashboard
   (Environment tab). Set `WEBHOOK_BASE_URL` to the `.onrender.com` URL
   Render assigns you (you'll see it after the first deploy).
5. Redeploy once `WEBHOOK_BASE_URL` is set, so the webhook actually registers
   with Telegram on startup.
6. **Keep-alive (important):** Render's free tier sleeps after inactivity.
   Sign up free at [UptimeRobot](https://uptimerobot.com) or
   [cron-job.org](https://cron-job.org) and set up a monitor that pings
   `https://your-app.onrender.com/health` every 5 minutes. This stops the
   service from ever fully spinning down.

## Maintaining the free AI models

`config.py` has `VISION_MODELS` and `TEXT_MODELS` lists. OpenRouter's free
model roster changes — sometimes weekly. If the bot starts failing AI
requests:

1. Check [openrouter.ai/models](https://openrouter.ai/models), filter by
   Price = Free.
2. Update the lists in `config.py`. That's the only file that needs editing.
3. For Task 1 (image-based) you need a model that supports vision/image
   input — check the model's capability tags on OpenRouter before adding it
   to `VISION_MODELS`.

**Strongly recommended:** once you have any spare cash, buy $10 of OpenRouter
credit (one-time, never expires). This raises your free-model daily limit
from 50 requests/day to 1000 requests/day — the single best reliability
upgrade available, and it's not a subscription.

## Project structure

```
main.py                  Entry point, webhook server, router registration
config.py                All env vars + the swappable AI model lists
handlers/
  start.py                /start command, resume-or-restart logic
  mode_selection.py        Write/Assess and Task 1/2 button handlers
  submission_flow.py       Image/text collection, review/edit screen
  results.py                AI calls, DB writes, channel logging, results
services/
  ai_client.py             OpenRouter wrapper with model fallback
  prompts.py                The actual IELTS rubric instructions sent to AI
  channel_logger.py         Two-message threaded posts to the log channel
states/
  flow_states.py            aiogram FSM states matching our state diagram
db/
  models.py                 SQLAlchemy models (users, submissions, etc.)
  database.py                Engine/session + state-persistence helpers
utils/
  keyboards.py               Inline keyboard builders
```

## Known limitations / things to revisit as you grow

- Free OpenRouter models can be slow (peak-hour throttling) or occasionally
  ignore the "JSON only" instruction — `ai_client.py` already strips common
  wrapping artifacts, but very unusual outputs could still fail to parse.
  If a model consistently misbehaves, remove it from the config list.
- SQLite is fine at this scale (~100 users) but doesn't handle concurrent
  writes well at higher volume — migrate `DATABASE_URL` to a free-tier
  Postgres (Neon, Supabase) before scaling past a few hundred active users.
- No payment/subscription system yet — the schema and flow don't block this,
  but it isn't built. Worth a separate planning pass when you're ready.
