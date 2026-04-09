# open-paws-policy-watch

Legislative intelligence and policy monitoring for animal advocacy coalitions.

Monitors bills across US states and federal, India, and EU — classifies them by animal welfare impact using a hybrid AI + keyword pipeline — and enables one-click contact with representatives.

## Why This Exists

Every year, hundreds of bills that directly affect farmed animals, wildlife, and companion animals pass through legislatures without advocacy organizations knowing they exist. By the time someone spots a relevant bill, the comment window has often closed.

This platform provides automated intelligence so coalitions can act fast — not just find bills, but understand their impact, prioritize by urgency, draft responses, and contact representatives in a single flow.

## Architecture

```
Open States API (US) + PRS Legislative Research (India) + Eur-Lex (EU)
     ↓
monitor.py — fetches bills across jurisdictions
     ↓
classifier.py — keyword pre-filter → LLM stance classification
                (HELPS_ANIMALS / HARMS_ANIMALS / MIXED / UNRELATED)
     ↓
scorer.py — deterministic 100-point urgency score
            (keyword density + committee impact + sponsor history)
            NEUTRAL bills get 0.3x dampening to prevent false alarms
     ↓
SQLite (local dev) / Postgres (production)
     ↓
FastAPI REST API
     ↓
notifier.py — Telegram webhook alerts to coalition partners
     ↓
Next.js dashboard + ContactRep component
```

## Classification

Bills are classified into four categories:

| Category | Meaning |
|----------|---------|
| `HELPS_ANIMALS` | Strengthens welfare protections, bans cruel practices |
| `HARMS_ANIMALS` | Ag-gag laws, weakens inspection, preempts local protections |
| `MIXED` | Contains both helpful and harmful provisions |
| `UNRELATED` | No animal welfare impact |

Urgency levels drive alert routing:

| Level | Trigger |
|-------|---------|
| `IMMEDIATE` | Comment period closing within 72 hours |
| `HIGH` | Committee vote within 7 days |
| `MEDIUM` | Floor vote within 30 days |
| `MONITOR` | Early stage, watch for amendments |

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- API keys: [Open States](https://openstates.org/api/) + [OpenRouter](https://openrouter.ai)

### Backend

```bash
cd backend
pip install -e ".[dev]"
cp .env.example .env  # fill in API keys
uvicorn main:app --reload
```

API at `http://localhost:8000` — docs at `http://localhost:8000/docs`

### Run the monitoring pipeline

```bash
python -m src.monitor --fetch --classify
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard at `http://localhost:3000`

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/bills` | GET | List bills (filter by jurisdiction, impact, urgency) |
| `/bills/{bill_id}` | GET | Single bill detail |
| `/bills/classify` | POST | Trigger classification of pending bills |
| `/bills/{bill_id}/draft-response` | POST | Generate coalition testimony draft |
| `/alerts` | GET | Recent high-urgency alerts |
| `/coalitions` | GET/POST | Manage coalition partners |

## Source Attributions

Built from patterns and code in:
- [LegiTrack-AI](https://github.com/Open-Paws/starred-repos/LegiTrack-AI) — Open States API client, two-tier NLP architecture, deterministic relevance scoring, 93.75% accuracy baseline
- [policy-alert-engine](https://github.com/Open-Paws/starred-repos/policy-alert-engine) — Impact scoring, AI drafting pipeline, dashboard patterns
- [democracy.io](https://github.com/EFForg/democracy.io) — Contact-your-representative flow (EFF, MIT License)
- [animalparliament](https://github.com/Open-Paws/starred-repos/animalparliament) — India policy scraping, Gemini analysis, animal welfare sentiment classification

## License

MIT
