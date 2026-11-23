# Eya Sahbeni — Portfolio AI Assistant Backend

FastAPI backend for the floating AI chat widget on Eya's TARGET EYA portfolio.
It receives questions from the frontend, builds a knowledge-base-locked prompt,
and forwards them to OpenRouter. The API key stays server-side.

## Files

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app with `/chat`, `/health`, CORS, rate limiting |
| `knowledge_base.json` | The only facts the LLM may use (profile, projects, experience, skills) |
| `requirements.txt` | Python dependencies |
| `.env.example` | Template — copy to `.env` and fill in |
| `.env` | **DO NOT COMMIT** — contains your real API key |
| `.gitignore` | Keeps `.env` out of git |
| `Procfile` | For Render/Railway/Heroku-style deploys |

## Endpoints

- `GET /` → service info
- `GET /health` → `{status, key_configured, model, kb_entries}`
- `POST /chat` → body `{question: str, lang: "en"|"fr"}` → `{answer, lang}`

The frontend calls `POST /chat`. No other endpoint is used from the browser.

## Local development

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and paste your OpenRouter key

python main.py
# or: uvicorn main:app --reload --port 8080
```

Open `http://localhost:8080/health` to verify.

## Deploy on Render (free tier)

1. Push the `backend/` folder to a **separate GitHub repo** (don't commit `.env`).
2. On https://render.com → **New +** → **Web Service** → connect the repo.
3. **Build command:** `pip install -r requirements.txt`
4. **Start command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. **Environment variables** (Dashboard → Environment):
   - `OPENROUTER_API_KEY` = your real key (from https://openrouter.ai/keys)
   - `ALLOWED_ORIGINS` = `https://sahbenieya.github.io` (your deployed portfolio URL)
   - (optional) `OPENROUTER_MODEL`, `RATE_LIMIT`, `SITE_URL`, `SITE_NAME`
6. Deploy. Render gives you a URL like `https://eya-chat-backend.onrender.com`.

**Note:** Render free tier sleeps after 15 min of inactivity. First request after sleep
takes 30–60 s to wake. The chat widget shows a friendly "unavailable" message if the
backend takes too long — that's expected on first wake-up.

## Deploy on Railway

1. Push `backend/` to a GitHub repo.
2. railway.app → **New Project** → **Deploy from GitHub repo**.
3. Add environment variables (same as Render).
4. Railway auto-detects the `Procfile` and deploys.

## Connecting the frontend

After deploying, tell the chat widget where to find the backend. Open `index.html`
and add this line near the top of `<body>` (or in a `<script>` tag before the main
one):

```html
<script>window.CHAT_BACKEND_URL = 'https://eya-chat-backend.onrender.com';</script>
```

- If `window.CHAT_BACKEND_URL` is **set**, the widget calls your FastAPI backend.
- If it's **empty or missing**, the widget uses a built-in local knowledge base
  (10 EN + 10 FR answers). The portfolio works either way.

The API key is **never** needed in the frontend. The widget only sends the user's
question and language — nothing else.

## Rotating the key

To replace the OpenRouter key without touching the frontend:
1. In your hosting provider's dashboard, update the `OPENROUTER_API_KEY` env var.
2. Redeploy (Render/Railway auto-redeploy on env var change).
3. No frontend changes needed.

## Rate limiting

Default: 10 requests per minute per IP, via `slowapi`. Adjust by setting the
`RATE_LIMIT` env var (e.g. `30/minute`, `5/minute`, `100/hour`).

## Changing the knowledge base

Edit `knowledge_base.json`, redeploy. The LLM will immediately start using the
new facts. Keep it factual — the whole security model depends on this file being
the single source of truth.

## Security notes

- The API key is read from the environment, never from source code.
- `.env` is in `.gitignore` — committing it will fail by default.
- CORS allows only origins listed in `ALLOWED_ORIGINS`.
- Rate limiting prevents abuse of your OpenRouter quota.
- Input is length-capped (400 chars) and sanitized (control chars stripped).
- Error messages don't leak the API key; HTTP errors return generic messages.
- Answers are truncated to ~4 sentences in the backend to prevent runaway responses.
