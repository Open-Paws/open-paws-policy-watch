# open-paws-policy-watch — Agent Instructions

Legislative intelligence platform for animal advocacy coalitions.
Monitors bills, classifies by welfare impact, alerts coalition partners, enables rapid response.

## Architecture
- `backend/src/monitor.py` — Multi-jurisdiction bill monitoring (US federal + state via Open States API, India via PRS Legislative Research, EU via Eur-Lex)
- `backend/src/classifier.py` — AI classification: does this bill help or harm animals? Hybrid keyword + LLM approach (93.75% accuracy baseline from LegiTrack-AI)
- `backend/src/scorer.py` — Urgency scoring: how fast must we respond? Deterministic 100-point model (keyword density + committee + sponsor history)
- `backend/src/drafter.py` — Auto-generates coalition testimony and public comment letters
- `backend/src/notifier.py` — Webhook alerts to Telegram coalition channels
- `backend/src/models.py` — Core data models (Bill, Coalition, WelfareImpact, UrgencyLevel)
- `backend/main.py` — FastAPI app entry point
- `frontend/` — Next.js 14 + React + TypeScript dashboard with contact-your-rep flow

## Classification Schema

Bills are classified into:
- `HELPS_ANIMALS` — strengthens welfare protections, bans cruel practices
- `HARMS_ANIMALS` — ag-gag, weakens inspection, preempts local protections
- `MIXED` — contains both helpful and harmful provisions
- `UNRELATED` — no animal welfare impact

Urgency levels:
- `IMMEDIATE` — public comment period closing within 72 hours
- `HIGH` — committee vote within 7 days
- `MEDIUM` — floor vote within 30 days
- `MONITOR` — early stage, watch for amendments

## Domain Language
- "bill" or "legislation" not "law" until enacted
- "factory farm" not "farm" or "agricultural operation"
- "ag-gag" is the precise term for laws criminalizing undercover investigation
- "farmed animal" not "livestock"
- "coalition" for multi-org alliances
- "testimony" for witness statements in legislative proceedings
- "slaughterhouse" not "processing facility" or "packing plant"

## Key Design Decisions
- Keyword pre-filter runs before LLM classification (reduces API cost 60-80%)
- NEUTRAL stance classification applies 0.3x dampening multiplier on urgency score
- Coalition alert thresholds are per-org configurable (`min_urgency` field)
- Data never crosses bounded context boundaries without explicit anti-corruption translation
- All sensitive investigation data stays in Investigation Operations context; this repo is Public Campaigns context only

## Running

```bash
# Backend
cd backend && pip install -e ".[dev]"
uvicorn main:app --reload

# Monitor new bills (run as cron)
python -m src.monitor --fetch --classify

# Frontend
cd frontend && npm install && npm run dev
```

## Environment Variables

```
OPENSTATES_API_KEY=         # openstates.org free tier
OPENROUTER_API_KEY=         # openrouter.ai — routes to cheapest capable model
TELEGRAM_BOT_TOKEN=         # for coalition webhook alerts
DATABASE_URL=               # defaults to sqlite:///./policy_watch.db
```

## Task Routing

| You're doing... | Read... |
|-----------------|---------|
| Adding a new jurisdiction | `docs/jurisdictions.md`, then `backend/src/monitor.py` |
| Improving classification | `backend/src/classifier.py` — add keywords or tune LLM prompt |
| Adding coalition | POST `/coalitions` endpoint, see `backend/main.py` |
| Contact-rep flow | `frontend/src/components/ContactRep.tsx` |
| Drafting testimony | `backend/src/drafter.py` |
