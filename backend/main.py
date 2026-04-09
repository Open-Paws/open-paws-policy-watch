"""
FastAPI application for open-paws-policy-watch.

Endpoints:
  GET  /bills                      — list bills with filtering
  GET  /bills/{bill_id}            — single bill detail
  POST /bills/classify             — trigger classification of pending bills
  POST /bills/{bill_id}/draft-response — generate coalition testimony draft
  GET  /alerts                     — recent high-urgency alerts
  GET  /coalitions                 — list coalition partners
  POST /coalitions                 — register a new coalition partner
"""
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

import sqlite_utils
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.classifier import BillClassifier
from src.drafter import DraftTone, ResponseDrafter
from src.models import Bill, Coalition, UrgencyLevel, WelfareImpact
from src.monitor import BillMonitor
from src.notifier import CoalitionNotifier
from src.scorer import score_urgency

logger = logging.getLogger(__name__)

DATABASE_PATH = os.getenv("DATABASE_PATH", "./policy_watch.db")


# ── Pydantic schemas for API I/O ─────────────────────────────────────────────

class BillOut(BaseModel):
    bill_id: str
    title: str
    jurisdiction: str
    status: str
    welfare_impact: str
    urgency: str
    urgency_score: int
    summary: Optional[str]
    full_text_url: Optional[str]
    sponsor_name: Optional[str]
    committee: Optional[str]
    classification_reasoning: Optional[str]

    class Config:
        from_attributes = True


class DraftRequest(BaseModel):
    org_name: str
    tone: DraftTone = DraftTone.FORMAL
    custom_context: Optional[str] = None


class CoalitionIn(BaseModel):
    org_id: str
    name: str
    jurisdictions: list[str]
    telegram_webhook: Optional[str] = None
    email: Optional[str] = None
    min_urgency: str = UrgencyLevel.MEDIUM.value


# ── Database helpers ─────────────────────────────────────────────────────────

def _get_db() -> sqlite_utils.Database:
    db = sqlite_utils.Database(DATABASE_PATH)
    if "bills" not in db.table_names():
        db["bills"].create(
            {
                "bill_id": str,
                "title": str,
                "jurisdiction": str,
                "status": str,
                "welfare_impact": str,
                "urgency": str,
                "urgency_score": int,
                "summary": str,
                "full_text_url": str,
                "sponsor_name": str,
                "committee": str,
                "classification_reasoning": str,
                "introduced_date": str,
                "last_action_date": str,
            },
            pk="bill_id",
            if_not_exists=True,
        )
    if "coalitions" not in db.table_names():
        db["coalitions"].create(
            {
                "org_id": str,
                "name": str,
                "jurisdictions": str,  # JSON-encoded list
                "telegram_webhook": str,
                "email": str,
                "min_urgency": str,
            },
            pk="org_id",
            if_not_exists=True,
        )
    return db


def _bill_to_row(bill: Bill) -> dict:
    return {
        "bill_id": bill.bill_id,
        "title": bill.title,
        "jurisdiction": bill.jurisdiction,
        "status": bill.status,
        "welfare_impact": bill.welfare_impact.value,
        "urgency": bill.urgency.value,
        "urgency_score": bill.urgency_score,
        "summary": bill.summary,
        "full_text_url": bill.full_text_url,
        "sponsor_name": bill.sponsor_name,
        "committee": bill.committee,
        "classification_reasoning": bill.classification_reasoning,
        "introduced_date": str(bill.introduced_date) if bill.introduced_date else None,
        "last_action_date": str(bill.last_action_date) if bill.last_action_date else None,
    }


def _row_to_bill_out(row: dict) -> BillOut:
    return BillOut(**{k: row[k] for k in BillOut.model_fields})


# ── App setup ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    _get_db()  # Initialize DB on startup
    yield


app = FastAPI(
    title="Open Paws Policy Watch",
    description=(
        "Legislative intelligence platform for animal advocacy coalitions. "
        "Monitors bills, classifies by welfare impact, and enables rapid response."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/bills", response_model=list[BillOut], summary="List bills with filtering")
def list_bills(
    jurisdiction: Optional[str] = Query(None, description="Filter by jurisdiction slug"),
    welfare_impact: Optional[str] = Query(None, description="Filter by WelfareImpact value"),
    urgency: Optional[str] = Query(None, description="Filter by UrgencyLevel value"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    db = _get_db()
    query = "SELECT * FROM bills WHERE 1=1"
    params: list = []

    if jurisdiction:
        query += " AND jurisdiction LIKE ?"
        params.append(f"{jurisdiction}%")
    if welfare_impact:
        query += " AND welfare_impact = ?"
        params.append(welfare_impact.upper())
    if urgency:
        query += " AND urgency = ?"
        params.append(urgency.upper())

    query += " ORDER BY urgency_score DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = list(db.execute(query, params).fetchall())
    columns = [col[0] for col in db.execute("PRAGMA table_info(bills)").fetchall()]
    return [_row_to_bill_out(dict(zip(columns, row))) for row in rows]


@app.get("/bills/{bill_id}", response_model=BillOut, summary="Get a single bill")
def get_bill(bill_id: str):
    db = _get_db()
    rows = list(db["bills"].rows_where("bill_id = ?", [bill_id]))
    if not rows:
        raise HTTPException(status_code=404, detail=f"Bill {bill_id!r} not found")
    return _row_to_bill_out(rows[0])


@app.post("/bills/classify", summary="Fetch and classify pending bills")
async def trigger_classification(
    jurisdictions: Optional[list[str]] = Query(None),
    days_back: int = Query(7, ge=1, le=90),
):
    """
    Trigger the monitoring pipeline: fetch new bills, classify them,
    score urgency, and persist to the database.
    """
    monitor = BillMonitor()
    try:
        bills = await monitor.fetch_and_classify(
            jurisdictions=jurisdictions,
            days_back=days_back,
        )
    finally:
        await monitor.close()

    db = _get_db()
    saved = 0
    for bill in bills:
        try:
            db["bills"].upsert(_bill_to_row(bill), pk="bill_id")
            saved += 1
        except Exception as exc:
            logger.error("Failed to save bill %s: %s", bill.bill_id, exc)

    return {
        "fetched": len(bills),
        "saved": saved,
        "breakdown": {
            impact.value: sum(1 for b in bills if b.welfare_impact == impact)
            for impact in WelfareImpact
        },
    }


@app.post(
    "/bills/{bill_id}/draft-response",
    summary="Generate coalition testimony draft for a bill",
)
async def draft_response(bill_id: str, request: DraftRequest):
    db = _get_db()
    rows = list(db["bills"].rows_where("bill_id = ?", [bill_id]))
    if not rows:
        raise HTTPException(status_code=404, detail=f"Bill {bill_id!r} not found")

    row = rows[0]
    bill = Bill(
        bill_id=row["bill_id"],
        title=row["title"],
        jurisdiction=row["jurisdiction"],
        status=row["status"],
        introduced_date=None,
        last_action_date=None,
        summary=row.get("summary"),
        full_text_url=row.get("full_text_url"),
        welfare_impact=WelfareImpact(row["welfare_impact"]),
        urgency=UrgencyLevel(row["urgency"]),
        urgency_score=row.get("urgency_score", 0),
        classification_reasoning=row.get("classification_reasoning"),
        committee=row.get("committee"),
        sponsor_name=row.get("sponsor_name"),
    )

    drafter = ResponseDrafter()
    try:
        draft = await drafter.draft_response(
            bill=bill,
            org_name=request.org_name,
            tone=request.tone,
            custom_context=request.custom_context,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return {"bill_id": bill_id, "tone": request.tone.value, "draft": draft}


@app.get("/alerts", response_model=list[BillOut], summary="Recent high-urgency alerts")
def get_alerts(
    min_urgency: str = Query("HIGH", description="Minimum urgency level"),
    limit: int = Query(20, le=100),
):
    """
    Returns bills with urgency at or above the threshold that have welfare
    impact (not UNRELATED). Ordered by urgency_score descending.
    """
    urgency_order = ["MONITOR", "MEDIUM", "HIGH", "IMMEDIATE"]
    if min_urgency.upper() not in urgency_order:
        raise HTTPException(status_code=400, detail=f"Invalid urgency level: {min_urgency}")

    min_idx = urgency_order.index(min_urgency.upper())
    qualifying_levels = urgency_order[min_idx:]

    db = _get_db()
    placeholders = ",".join("?" * len(qualifying_levels))
    query = (
        f"SELECT * FROM bills "
        f"WHERE urgency IN ({placeholders}) "
        f"AND welfare_impact != 'UNRELATED' "
        f"ORDER BY urgency_score DESC "
        f"LIMIT ?"
    )
    params = qualifying_levels + [limit]
    rows = list(db.execute(query, params).fetchall())
    columns = [col[0] for col in db.execute("PRAGMA table_info(bills)").fetchall()]
    return [_row_to_bill_out(dict(zip(columns, row))) for row in rows]


@app.get("/coalitions", summary="List coalition partners")
def list_coalitions():
    import json
    db = _get_db()
    rows = list(db["coalitions"].rows)
    for row in rows:
        if isinstance(row.get("jurisdictions"), str):
            try:
                row["jurisdictions"] = json.loads(row["jurisdictions"])
            except (ValueError, TypeError):
                row["jurisdictions"] = []
    return rows


@app.post("/coalitions", summary="Register a new coalition partner")
def create_coalition(coalition: CoalitionIn):
    import json
    db = _get_db()
    row = {
        "org_id": coalition.org_id,
        "name": coalition.name,
        "jurisdictions": json.dumps(coalition.jurisdictions),
        "telegram_webhook": coalition.telegram_webhook,
        "email": coalition.email,
        "min_urgency": coalition.min_urgency,
    }
    db["coalitions"].upsert(row, pk="org_id")
    return {"status": "ok", "org_id": coalition.org_id}
