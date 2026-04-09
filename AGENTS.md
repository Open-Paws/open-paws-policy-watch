# Open Paws Policy Watch — Agent Quick Reference

Monitors legislative bills across US, India, and EU jurisdictions, classifying each as HELPS_ANIMALS, HARMS_ANIMALS, or MIXED using a two-tier NLP pipeline (keyword filter + LLM classification).

## How to Run

```bash
# Install
pip install -e ".[dev]"

# Start API server
uvicorn src.api.server:app --reload
```

## Full Agent Routing

See `CLAUDE.md` for complete context: tech stack, key files, strategic role, quality gates, and task routing table.
