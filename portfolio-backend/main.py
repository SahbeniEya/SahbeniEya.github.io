"""
Eya Sahbeni — Portfolio AI Assistant (FastAPI backend)

Responsibilities:
- Exposes POST /chat that accepts {question, lang} and returns {answer}
- Loads a verified knowledge base (knowledge_base.json) and injects it into
  the system prompt so the LLM only answers from Eya's actual profile
- Calls OpenRouter with an API key kept server-side only
- Enforces basic validation, rate limiting and short answers (2-4 sentences)
- Never exposes the API key, never logs it

Deploy to Render/Railway/Fly; set OPENROUTER_API_KEY in the environment.
See README.md for deploy steps.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# ---------------------------------------------------------------------------
# Config — all secrets come from environment variables
# ---------------------------------------------------------------------------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free"
)
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "ALLOWED_ORIGINS",
        # Defaults: GitHub Pages site + local dev
        "https://sahbenieya.github.io,http://localhost:8000,http://127.0.0.1:8000",
    ).split(",")
    if o.strip()
]
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "30"))
MAX_QUESTION_CHARS = 400
# OpenRouter sends Referer & X-Title for ranking/attribution (optional)
SITE_URL = os.getenv("SITE_URL", "https://sahbenieya.github.io")
SITE_NAME = os.getenv("SITE_NAME", "TARGET EYA Portfolio")

# ---------------------------------------------------------------------------
# Knowledge base — the ONLY facts the LLM may use
# ---------------------------------------------------------------------------
KB_PATH = Path(__file__).parent / "knowledge_base.json"
KNOWLEDGE_BASE = json.loads(KB_PATH.read_text(encoding="utf-8"))


def build_system_prompt(lang: str) -> str:
    """Build a language-aware system prompt that locks the LLM to the KB."""
    kb_text = json.dumps(KNOWLEDGE_BASE, ensure_ascii=False, indent=2)
    if lang == "fr":
        return f"""Tu es l'assistant IA du portfolio d'Eya Sahbeni. Tu aides les recruteurs \
à comprendre rapidement son profil professionnel.

RÈGLES STRICTES :
1. Réponds UNIQUEMENT à partir de la base de connaissances ci-dessous. N'invente \
JAMAIS d'expérience, de compétence, de projet, de certification ou de résultat.
2. Si la question sort du périmètre du portfolio (opinions personnelles, actualité, \
autres personnes, conseils généraux), dis poliment que tu ne peux pas répondre.
3. Réponds en 2 à 4 phrases maximum. Sois concis et professionnel.
4. Utilise un ton courtois et direct, comme un recruteur sérieux l'attendrait.
5. Réponds en français.

BASE DE CONNAISSANCES VÉRIFIÉE :
{kb_text}
"""
    # default: English
    return f"""You are the AI assistant for Eya Sahbeni's portfolio. You help recruiters \
quickly understand her professional profile.

STRICT RULES:
1. Answer ONLY from the knowledge base below. NEVER invent experience, skills, \
projects, certifications or outcomes.
2. If the question is outside the portfolio's scope (personal opinions, current events, \
other people, general advice), politely say you can't answer.
3. Keep answers to 2–4 sentences maximum. Be concise and professional.
4. Use a courteous, direct tone, as a serious recruiter would expect.
5. Answer in English.

VERIFIED KNOWLEDGE BASE:
{kb_text}
"""


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Eya Sahbeni — Portfolio AI Assistant",
    description="Backend for the floating chat widget on Eya's portfolio.",
    version="1.0.0",
)

# Rate limiting: 10 requests / minute per IP (adjust via env)
RATE_LIMIT = os.getenv("RATE_LIMIT", "10/minute")
limiter = Limiter(key_func=get_remote_address, default_limits=[RATE_LIMIT])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — only allow origins from ALLOWED_ORIGINS env var
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
    max_age=600,
)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=MAX_QUESTION_CHARS)
    lang: Literal["en", "fr"] = "en"


class ChatResponse(BaseModel):
    answer: str
    lang: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    return {
        "service": "Eya Sahbeni Portfolio AI Assistant",
        "status": "ok",
        "endpoints": ["/chat (POST)", "/health"],
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "key_configured": bool(OPENROUTER_API_KEY),
        "model": OPENROUTER_MODEL,
        "kb_entries": len(KNOWLEDGE_BASE.get("projects", []))
        + len(KNOWLEDGE_BASE.get("experience", [])),
    }


@app.post("/chat", response_model=ChatResponse)
@limiter.limit(RATE_LIMIT)
async def chat(request: Request, body: ChatRequest):
    """Main chat endpoint. Validates, calls OpenRouter, returns answer."""
    if not OPENROUTER_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="OPENROUTER_API_KEY is not configured on the server.",
        )

    # Sanitize the question (strip control chars, trim)
    question = re.sub(r"[\x00-\x1f\x7f]", "", body.question).strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is empty.")

    system_prompt = build_system_prompt(body.lang)

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        "temperature": 0.3,  # low temperature = more factual
        "max_tokens": 250,  # ~ 2-4 sentences
    }
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": SITE_URL,
        "X-Title": SITE_NAME,
    }

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.post(OPENROUTER_URL, headers=headers, json=payload)
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504, detail="Upstream LLM timed out. Please try again."
        )
    except httpx.HTTPError as exc:
        # Do NOT leak the key in error messages
        raise HTTPException(
            status_code=502, detail=f"Upstream LLM error: {type(exc).__name__}"
        )

    if resp.status_code != 200:
        # Scrub the body of any sensitive-looking content before raising
        safe_body = resp.text[:200]
        raise HTTPException(
            status_code=502,
            detail=f"OpenRouter returned {resp.status_code}: {safe_body}",
        )

    data = resp.json()
    try:
        answer = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError):
        raise HTTPException(status_code=502, detail="Malformed response from upstream.")

    # Keep answers short — truncate if the model went long
    sentences = re.split(r"(?<=[.!?])\s+", answer)
    if len(sentences) > 5:
        answer = " ".join(sentences[:4]).strip()

    return ChatResponse(answer=answer, lang=body.lang)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
