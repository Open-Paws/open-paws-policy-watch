"""Data models for legislative intelligence."""
from dataclasses import dataclass, field
from datetime import date
from typing import Optional
from enum import Enum


class WelfareImpact(str, Enum):
    HELPS_ANIMALS = "HELPS_ANIMALS"
    HARMS_ANIMALS = "HARMS_ANIMALS"
    MIXED = "MIXED"
    UNRELATED = "UNRELATED"
    PENDING_CLASSIFICATION = "PENDING_CLASSIFICATION"


class UrgencyLevel(str, Enum):
    IMMEDIATE = "IMMEDIATE"   # <72 hours
    HIGH = "HIGH"             # <7 days
    MEDIUM = "MEDIUM"         # <30 days
    MONITOR = "MONITOR"       # early stage


class Jurisdiction(str, Enum):
    US_FEDERAL = "US_FEDERAL"
    # US states added dynamically via Open States jurisdiction slugs (e.g. "us/ca")
    INDIA_CENTRAL = "INDIA_CENTRAL"
    EU = "EU"


@dataclass
class Bill:
    """A piece of legislation being monitored."""
    bill_id: str
    title: str
    jurisdiction: str
    status: str
    introduced_date: Optional[date]
    last_action_date: Optional[date]
    summary: Optional[str]
    full_text_url: Optional[str]

    # Classification (populated after AI analysis)
    welfare_impact: WelfareImpact = WelfareImpact.PENDING_CLASSIFICATION
    urgency: UrgencyLevel = UrgencyLevel.MONITOR
    urgency_score: int = 0  # 0-100 deterministic score
    urgency_breakdown: dict = field(default_factory=dict)
    classification_reasoning: Optional[str] = None
    affected_species: list[str] = field(default_factory=list)
    key_provisions: list[str] = field(default_factory=list)

    # Contact info
    sponsor_name: Optional[str] = None
    sponsor_contact: Optional[str] = None
    committee: Optional[str] = None
    sponsors: list[dict] = field(default_factory=list)


@dataclass
class Coalition:
    """A coalition partner that receives alerts."""
    org_id: str
    name: str
    jurisdictions: list[str]  # Which jurisdictions they care about
    telegram_webhook: Optional[str]
    email: Optional[str]
    # Only alert on this urgency level and above
    min_urgency: UrgencyLevel = UrgencyLevel.MEDIUM
