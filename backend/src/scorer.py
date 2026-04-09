"""
Urgency scoring for animal welfare bills.

Deterministic 100-point algorithm adapted from LegiTrack-AI's RelevanceScorer.
Three weighted dimensions:
  - Keyword Density   (max 40 points)
  - Committee Impact  (max 30 points)
  - Sponsor History   (max 30 points)

NEUTRAL/UNRELATED bills receive a 0.3x dampening multiplier to prevent
false-alarm alerts (per LegiTrack-AI stance-based penalty dampening design).

This is intentionally decoupled from the LLM classifier so that urgency
rankings are reproducible and auditable — orgs can explain to their boards
exactly why a bill was escalated.
"""
import logging
from typing import Optional

from .models import Bill, UrgencyLevel, WelfareImpact

logger = logging.getLogger(__name__)

# Committees that typically govern animal welfare policy — highest impact
HIGH_IMPACT_COMMITTEES = [
    "agriculture",
    "environment",
    "natural resources",
    "wildlife",
    "conservation",
    "judiciary",
    "game and fish",
    "animal welfare",
    "food and agriculture",
]

# Committees with moderate relevance — secondary impact
MEDIUM_IMPACT_COMMITTEES = [
    "health",
    "human services",
    "commerce",
    "appropriations",
    "finance",
    "ways and means",
    "public safety",
    "regulatory affairs",
]

# Status strings that indicate elevated urgency
IMMEDIATE_STATUS_SIGNALS = [
    "public comment closing",
    "comment period ends",
    "final rule",
    "hearing scheduled",
]

HIGH_STATUS_SIGNALS = [
    "committee vote",
    "floor vote",
    "second reading",
    "third reading",
    "engrossed",
    "passed committee",
]


def score_urgency(
    bill: Bill,
    keyword_density: float,
    known_sponsor_ids: Optional[list[str]] = None,
) -> Bill:
    """
    Compute a deterministic urgency score and level for a bill.

    Args:
        bill: The bill to score. Modified in place.
        keyword_density: Float 0-1, ratio of welfare keywords to total text.
                         Computed by classifier.BillClassifier.keyword_density().
        known_sponsor_ids: List of sponsor IDs already in the database with
                           prior animal welfare bill history. Pass [] if unknown.

    Returns:
        The bill with urgency, urgency_score, and urgency_breakdown populated.
    """
    score = 0
    breakdown: dict = {
        "keyword_points": 0,
        "committee_points": 0,
        "sponsor_points": 0,
        "total_score": 0,
        "details": [],
    }

    # ── 1. Keyword Density (max 40 points) ──────────────────────────────────
    # Density >= 3% of text = full 40 points (per LegiTrack-AI calibration)
    MAX_DENSITY = 0.03
    if keyword_density >= MAX_DENSITY:
        kw_points = 40
        breakdown["details"].append(
            f"Very high keyword density ({keyword_density * 100:.1f}%)"
        )
    else:
        kw_points = int((keyword_density / MAX_DENSITY) * 40)
        breakdown["details"].append(
            f"Standard keyword density ({keyword_density * 100:.1f}%)"
        )
    score += kw_points
    breakdown["keyword_points"] = kw_points

    # ── 2. Committee Assignment (max 30 points) ──────────────────────────────
    committee_lower = (bill.committee or "").lower()
    com_points = 0
    com_tier = "low/unknown impact"

    for kw in HIGH_IMPACT_COMMITTEES:
        if kw in committee_lower:
            com_points = 30
            com_tier = "high impact"
            break

    if com_points == 0:
        for kw in MEDIUM_IMPACT_COMMITTEES:
            if kw in committee_lower:
                com_points = 15
                com_tier = "medium impact"
                break

    score += com_points
    breakdown["committee_points"] = com_points
    if bill.committee and bill.committee.lower() != "unknown":
        breakdown["details"].append(
            f"Assigned to {bill.committee} ({com_tier})"
        )
    else:
        breakdown["details"].append("No specific committee assigned")

    # ── 3. Sponsor History (max 30 points) ───────────────────────────────────
    # known_sponsor_ids are IDs of sponsors already in the DB with prior
    # animal welfare bill history — indicates a committed advocate or opponent.
    sponsor_points = 0
    if known_sponsor_ids is None:
        sponsor_points = 15
        breakdown["details"].append("Sponsor history not checked")
    elif known_sponsor_ids:
        sponsor_points = 30
        breakdown["details"].append(
            f"Sponsor has prior animal welfare bill history in database"
        )
    else:
        sponsor_points = 15
        breakdown["details"].append("First tracked animal bill for this sponsor")

    score += sponsor_points
    breakdown["sponsor_points"] = sponsor_points

    # ── Stance-Based Penalty Dampening ────────────────────────────────────────
    # Bills classified UNRELATED or NEUTRAL (no welfare impact) should not
    # trigger coalition alerts even if they score high on keyword density.
    # Apply 0.3x multiplier to prevent false alarms.
    if bill.welfare_impact in (WelfareImpact.UNRELATED,):
        score = int(score * 0.3)
        breakdown["details"].append(
            "Stance penalty: bill classified UNRELATED (score reduced 70%)"
        )

    score = min(max(score, 0), 100)
    breakdown["total_score"] = score
    bill.urgency_score = score
    bill.urgency_breakdown = breakdown

    # ── Map score to urgency level ─────────────────────────────────────────
    # Also check status text for time-sensitive signals
    status_lower = (bill.status or "").lower()

    has_immediate_signal = any(s in status_lower for s in IMMEDIATE_STATUS_SIGNALS)
    has_high_signal = any(s in status_lower for s in HIGH_STATUS_SIGNALS)

    if has_immediate_signal or score >= 85:
        bill.urgency = UrgencyLevel.IMMEDIATE
    elif has_high_signal or score >= 65:
        bill.urgency = UrgencyLevel.HIGH
    elif score >= 45:
        bill.urgency = UrgencyLevel.MEDIUM
    else:
        bill.urgency = UrgencyLevel.MONITOR

    logger.info(
        "Scored bill %s: %d/100 → %s",
        bill.bill_id,
        score,
        bill.urgency.value,
    )
    return bill
