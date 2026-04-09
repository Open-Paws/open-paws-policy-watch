"""
Multi-jurisdiction bill monitoring.

Supported jurisdictions:
  - US: all 50 states + federal via Open States API (REST v3)
  - India: PRS Legislative Research scraper (TODO: replace with API when available)
  - EU: Eur-Lex EUR-Lex SPARQL / RSS feed (TODO: structured API integration)

The monitor fetches bills, runs them through the classifier and scorer,
and persists results. Run as a cron job for continuous intelligence.

Usage:
    python -m src.monitor --fetch --classify
    python -m src.monitor --fetch --jurisdictions us/ca us/ny us_federal
"""
import argparse
import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

import httpx

from .classifier import BillClassifier
from .models import Bill, Jurisdiction, UrgencyLevel, WelfareImpact
from .scorer import score_urgency

logger = logging.getLogger(__name__)

OPENSTATES_BASE_URL = "https://v3.openstates.org/"
OPENSTATES_API_KEY = os.getenv("OPENSTATES_API_KEY", "")

# US states to monitor by default (Open States jurisdiction slugs)
DEFAULT_US_JURISDICTIONS = [
    "us",          # federal
    "us/ca", "us/ny", "us/tx", "us/fl",
    "us/il", "us/wa", "us/co", "us/or",
    "us/mn", "us/ma", "us/nj", "us/md",
]


class OpenStatesMonitor:
    """
    Fetches bills from the Open States v3 REST API.

    Adapted from LegiTrack-AI's OpenStatesClient, extended to support
    all 50 states and the federal jurisdiction.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or OPENSTATES_API_KEY
        self.base_url = OPENSTATES_BASE_URL
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={"x-api-key": self.api_key},
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def fetch_bills(
        self,
        jurisdiction: str,
        days_back: int = 30,
        per_page: int = 20,
    ) -> list[Bill]:
        """Fetch recent bills for a jurisdiction."""
        if not self.api_key:
            logger.warning(
                "OPENSTATES_API_KEY not set — skipping US jurisdiction %s",
                jurisdiction,
            )
            return []

        client = await self._get_client()
        updated_since = (datetime.utcnow() - timedelta(days=days_back)).strftime(
            "%Y-%m-%d"
        )
        params = {
            "jurisdiction": jurisdiction,
            "sort": "updated_desc",
            "per_page": per_page,
            "include": ["sponsorships", "actions", "abstracts"],
            "updated_since": updated_since,
        }

        try:
            resp = await client.get(f"{self.base_url}bills", params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Open States HTTP error %s for %s: %s",
                exc.response.status_code,
                jurisdiction,
                exc.response.text[:200],
            )
            return []
        except Exception as exc:
            logger.error("Open States request error for %s: %s", jurisdiction, exc)
            return []

        bills = []
        for raw in data.get("results", []):
            bill = self._map_raw_bill(raw, jurisdiction)
            bills.append(bill)

        logger.info("Fetched %d bills from Open States for %s", len(bills), jurisdiction)
        return bills

    def _map_raw_bill(self, raw: dict, jurisdiction: str) -> Bill:
        """Map Open States API response dict to our Bill model."""
        actions = raw.get("actions", [])
        last_action = actions[-1] if actions else {}

        abstracts = raw.get("abstracts", [])
        summary = abstracts[0].get("abstract") if abstracts else None

        sponsorships = raw.get("sponsorships", [])
        sponsors = [
            {"name": s.get("name", ""), "id": s.get("person_id", "")}
            for s in sponsorships
        ]

        return Bill(
            bill_id=raw.get("id", ""),
            title=raw.get("title", ""),
            jurisdiction=jurisdiction,
            status=last_action.get("description", "introduced"),
            introduced_date=_parse_date(raw.get("first_action_date")),
            last_action_date=_parse_date(raw.get("updated_at")),
            summary=summary,
            full_text_url=raw.get("openstates_url"),
            sponsor_name=sponsors[0]["name"] if sponsors else None,
            committee=last_action.get("organization", {}).get("name") if last_action else None,
            sponsors=sponsors,
        )


class IndiaMonitor:
    """
    Monitors Indian central government legislation.

    Primary source: PRS Legislative Research (prsindia.org) — scraping only
    until a structured API is available.

    India-specific context from animalparliament: bills affecting farmed
    animals, wildlife, and dairy/poultry industries route through Ministry
    of Environment, Forest and Climate Change (MoEF&CC) and Ministry of
    Fisheries, Animal Husbandry and Dairying (MFAHD).
    """

    async def fetch_bills(self) -> list[Bill]:
        """
        Fetch recent Indian legislation affecting animal welfare.
        TODO: Implement PRS Legislative Research API integration.
        See docs/jurisdictions.md for planned data sources.
        """
        logger.info(
            "India monitor: PRS Legislative Research integration not yet implemented. "
            "See docs/jurisdictions.md and open issue #2."
        )
        return []


class EUMonitor:
    """
    Monitors EU legislation via Eur-Lex.

    Primary targets:
      - Animal transport regulations
      - Slaughterhouse welfare directives
      - Farmed animal welfare framework (post-2023 revision)
      - Wildlife trade regulations

    TODO: Implement Eur-Lex SPARQL endpoint / RSS feed integration.
    See docs/jurisdictions.md and open issue #3.
    """

    async def fetch_bills(self) -> list[Bill]:
        logger.info(
            "EU monitor: Eur-Lex integration not yet implemented. "
            "See docs/jurisdictions.md and open issue #3."
        )
        return []


class BillMonitor:
    """
    Orchestrates multi-jurisdiction monitoring.
    Fetches bills, classifies them, scores urgency, and returns results.
    """

    def __init__(self):
        self.us_monitor = OpenStatesMonitor()
        self.india_monitor = IndiaMonitor()
        self.eu_monitor = EUMonitor()
        self.classifier = BillClassifier()

    async def fetch_and_classify(
        self,
        jurisdictions: Optional[list[str]] = None,
        days_back: int = 30,
    ) -> list[Bill]:
        """
        Fetch bills from all configured jurisdictions, classify them,
        and score urgency. Returns all classified bills.
        """
        all_bills: list[Bill] = []

        # US jurisdictions via Open States
        us_jurisdictions = [
            j for j in (jurisdictions or DEFAULT_US_JURISDICTIONS)
            if j.startswith("us")
        ]
        for jurisdiction in us_jurisdictions:
            bills = await self.us_monitor.fetch_bills(jurisdiction, days_back=days_back)
            all_bills.extend(bills)

        # India
        if jurisdictions is None or Jurisdiction.INDIA_CENTRAL.value in (jurisdictions or []):
            india_bills = await self.india_monitor.fetch_bills()
            all_bills.extend(india_bills)

        # EU
        if jurisdictions is None or Jurisdiction.EU.value in (jurisdictions or []):
            eu_bills = await self.eu_monitor.fetch_bills()
            all_bills.extend(eu_bills)

        # Classify and score all bills
        classified = []
        for bill in all_bills:
            try:
                bill = self.classifier.classify(bill)
                density = self.classifier.keyword_density(bill)
                bill = score_urgency(bill, keyword_density=density)
                classified.append(bill)
            except Exception as exc:
                logger.error("Failed to classify bill %s: %s", bill.bill_id, exc)

        logger.info(
            "Monitor complete: %d bills fetched, %d classified",
            len(all_bills),
            len(classified),
        )
        return classified

    async def close(self) -> None:
        await self.us_monitor.close()


def _parse_date(value: Optional[str]):
    """Parse ISO date string to date, returning None on failure."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value[:10]).date()
    except (ValueError, TypeError):
        return None


async def _run_cli(args: argparse.Namespace) -> None:
    monitor = BillMonitor()
    try:
        jurisdictions = args.jurisdictions or None
        bills = await monitor.fetch_and_classify(
            jurisdictions=jurisdictions,
            days_back=args.days_back,
        )

        impact_counts: dict[str, int] = {}
        for bill in bills:
            key = bill.welfare_impact.value
            impact_counts[key] = impact_counts.get(key, 0) + 1

        print(f"\nFetched and classified {len(bills)} bills:")
        for impact, count in sorted(impact_counts.items()):
            print(f"  {impact}: {count}")

        high_urgency = [
            b for b in bills
            if b.urgency in (UrgencyLevel.IMMEDIATE, UrgencyLevel.HIGH)
            and b.welfare_impact != WelfareImpact.UNRELATED
        ]
        if high_urgency:
            print(f"\n{len(high_urgency)} bills require prompt attention:")
            for bill in high_urgency:
                print(f"  [{bill.urgency.value}] {bill.title} ({bill.jurisdiction})")
    finally:
        await monitor.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch and classify legislative bills")
    parser.add_argument("--fetch", action="store_true", help="Fetch new bills")
    parser.add_argument("--classify", action="store_true", help="Classify fetched bills")
    parser.add_argument(
        "--jurisdictions",
        nargs="*",
        help="Specific jurisdictions to monitor (e.g. us/ca us/ny)",
    )
    parser.add_argument(
        "--days-back",
        type=int,
        default=30,
        help="How many days back to fetch bills (default: 30)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    asyncio.run(_run_cli(args))
