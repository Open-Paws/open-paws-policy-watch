"""
Alert coalition partners when bills need rapid response.

Sends alerts to Telegram webhooks. Each coalition partner configures:
  - Which jurisdictions they care about
  - Their minimum urgency threshold (only alert on HIGH+ by default)
  - Their Telegram webhook URL

Design note: alert messages use plain text formatting because Telegram's
MarkdownV2 mode requires escaping many characters. The format is readable
without special parsing.
"""
import logging
from typing import Optional

import httpx

from .models import Bill, Coalition, UrgencyLevel, WelfareImpact

logger = logging.getLogger(__name__)

_URGENCY_ORDER = [
    UrgencyLevel.MONITOR,
    UrgencyLevel.MEDIUM,
    UrgencyLevel.HIGH,
    UrgencyLevel.IMMEDIATE,
]

_IMPACT_LABEL = {
    WelfareImpact.HELPS_ANIMALS: "HELPS ANIMALS",
    WelfareImpact.HARMS_ANIMALS: "HARMS ANIMALS",
    WelfareImpact.MIXED: "MIXED IMPACT",
    WelfareImpact.UNRELATED: "UNRELATED",
    WelfareImpact.PENDING_CLASSIFICATION: "PENDING",
}


class CoalitionNotifier:
    """Sends bill alerts to coalition partners via configured channels."""

    async def notify(self, bill: Bill, coalitions: list[Coalition]) -> int:
        """
        Notify all relevant coalitions about a bill.

        Returns count of notifications sent.
        """
        sent = 0
        for coalition in coalitions:
            if not self._jurisdiction_matches(bill.jurisdiction, coalition.jurisdictions):
                continue
            if not self._meets_urgency_threshold(bill.urgency, coalition.min_urgency):
                continue

            message = self._format_alert(bill, coalition)

            if coalition.telegram_webhook:
                success = await self._send_telegram(coalition.telegram_webhook, message)
                if success:
                    sent += 1
                    logger.info(
                        "Notified coalition %s about bill %s",
                        coalition.org_id,
                        bill.bill_id,
                    )

        return sent

    def _format_alert(self, bill: Bill, coalition: Coalition) -> str:
        """Format a plain-text alert message for Telegram."""
        impact_label = _IMPACT_LABEL.get(bill.welfare_impact, "UNKNOWN")
        urgency_label = bill.urgency.value

        lines = [
            f"POLICY ALERT [{urgency_label}]",
            "",
            bill.title,
            f"Jurisdiction: {bill.jurisdiction}",
            f"Impact: {impact_label}",
            f"Urgency score: {bill.urgency_score}/100",
            "",
        ]

        if bill.summary:
            # Truncate long summaries for Telegram readability
            summary = bill.summary if len(bill.summary) <= 300 else bill.summary[:297] + "..."
            lines.append(summary)
            lines.append("")

        if bill.classification_reasoning:
            lines.append(f"Analysis: {bill.classification_reasoning}")
            lines.append("")

        if bill.full_text_url:
            lines.append(f"Full text: {bill.full_text_url}")

        return "\n".join(lines)

    async def _send_telegram(self, webhook_url: str, message: str) -> bool:
        """Send a message to a Telegram webhook. Returns True on success."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    webhook_url,
                    json={"text": message},
                )
                resp.raise_for_status()
                return True
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Telegram webhook HTTP error %s: %s",
                exc.response.status_code,
                exc.response.text[:200],
            )
            return False
        except Exception as exc:
            logger.error("Telegram webhook error: %s", exc)
            return False

    def _jurisdiction_matches(
        self, bill_jurisdiction: str, coalition_jurisdictions: list[str]
    ) -> bool:
        """Check if a coalition cares about a bill's jurisdiction."""
        if not coalition_jurisdictions:
            return True  # Empty list means all jurisdictions

        bill_j = bill_jurisdiction.lower()
        for j in coalition_jurisdictions:
            j_lower = j.lower()
            # Exact match or prefix match (e.g. "us" matches "us/ca")
            if bill_j == j_lower or bill_j.startswith(j_lower + "/"):
                return True
        return False

    def _meets_urgency_threshold(
        self, urgency: UrgencyLevel, threshold: UrgencyLevel
    ) -> bool:
        """Return True if urgency is at or above the threshold level."""
        urgency_idx = _URGENCY_ORDER.index(urgency)
        threshold_idx = _URGENCY_ORDER.index(threshold)
        return urgency_idx >= threshold_idx
