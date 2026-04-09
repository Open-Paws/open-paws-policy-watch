"""
Auto-draft coalition testimony and public comment letters.

Adapted from policy-alert-engine's AI Drafting Assistant.
Supports three tones: FORMAL (official submissions), INFORMAL (community
outreach), URGENT (rapidly closing comment windows).

Routes to cheapest capable model via OpenRouter to respect advocacy org
budget constraints. Static system prompts are placed first to maximize
cache hit rates.
"""
import logging
import os
from enum import Enum
from typing import Optional

import httpx

from .models import Bill, WelfareImpact

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Route drafting to a mid-tier model — sufficient quality, lower cost.
# Frontier model not needed here; reserve frontier budget for classification
# of genuinely ambiguous bills.
DEFAULT_DRAFTING_MODEL = "openai/gpt-4o-mini"


class DraftTone(str, Enum):
    FORMAL = "FORMAL"       # Official government submissions
    INFORMAL = "INFORMAL"   # Social media, community newsletters
    URGENT = "URGENT"       # Rapidly closing comment windows


# Static system prompt — placed first for prompt cache optimization.
# All static content before dynamic bill-specific content.
_SYSTEM_PROMPT = """You are a policy advocate drafting testimony for animal advocacy coalition partners.

Your drafts must:
- Clearly state the organization's position on the bill
- Cite specific provisions that help or harm animal welfare
- Use precise domain language: "farmed animal" (not "livestock"), "factory farm"
  (not "farm"), "slaughterhouse" (not "processing facility"), "ag-gag" for
  laws criminalizing undercover investigation
- Avoid speciesist idioms (no "kill two birds with one stone", etc.)
- Be factually grounded — do not invent statistics or citations
- End with a clear call to action

Format: Plain text, ready to submit. No markdown."""


class ResponseDrafter:
    """Generates coalition testimony and public comment letter drafts."""

    async def draft_response(
        self,
        bill: Bill,
        org_name: str,
        tone: DraftTone = DraftTone.FORMAL,
        custom_context: Optional[str] = None,
    ) -> str:
        """
        Generate a draft testimony or comment letter for a bill.

        Args:
            bill: The bill to respond to.
            org_name: Name of the coalition partner submitting the testimony.
            tone: FORMAL for official submissions, INFORMAL for community
                  outreach, URGENT for closing comment windows.
            custom_context: Optional additional context the drafter should
                            incorporate (e.g. local impact data).

        Returns:
            Draft text ready for human review before submission.
        """
        if not OPENROUTER_API_KEY:
            raise RuntimeError(
                "OPENROUTER_API_KEY not set. Cannot generate draft. "
                "Set the environment variable and retry."
            )

        stance = _describe_stance(bill)
        user_prompt = _build_user_prompt(bill, org_name, tone, stance, custom_context)

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "HTTP-Referer": "https://github.com/Open-Paws/open-paws-policy-watch",
                    "X-Title": "Open Paws Policy Watch",
                },
                json={
                    "model": DEFAULT_DRAFTING_MODEL,
                    "messages": [
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": 800,
                    "temperature": 0.3,  # Low temperature for consistent, factual output
                },
            )
            resp.raise_for_status()
            data = resp.json()

        draft = data["choices"][0]["message"]["content"].strip()
        logger.info(
            "Generated %s-tone draft for bill %s (%d chars)",
            tone.value,
            bill.bill_id,
            len(draft),
        )
        return draft


def _describe_stance(bill: Bill) -> str:
    """Translate WelfareImpact enum to a human-readable stance description."""
    descriptions = {
        WelfareImpact.HELPS_ANIMALS: (
            "This bill strengthens animal welfare protections. "
            "The organization SUPPORTS this bill."
        ),
        WelfareImpact.HARMS_ANIMALS: (
            "This bill weakens animal welfare protections or criminalizes "
            "undercover investigation. The organization OPPOSES this bill."
        ),
        WelfareImpact.MIXED: (
            "This bill contains both protective and harmful provisions. "
            "The organization has a nuanced position — support helpful "
            "provisions, oppose harmful provisions."
        ),
        WelfareImpact.UNRELATED: (
            "This bill has no direct animal welfare impact."
        ),
        WelfareImpact.PENDING_CLASSIFICATION: (
            "Classification pending. Draft based on bill text only."
        ),
    }
    return descriptions.get(bill.welfare_impact, "Classification unknown.")


def _build_user_prompt(
    bill: Bill,
    org_name: str,
    tone: DraftTone,
    stance: str,
    custom_context: Optional[str],
) -> str:
    tone_instructions = {
        DraftTone.FORMAL: (
            "Write a formal testimony for official government submission. "
            "Use respectful, professional language appropriate for a legislative hearing."
        ),
        DraftTone.INFORMAL: (
            "Write an accessible summary for community newsletters or social media. "
            "Clear, direct language — assume readers are engaged but not policy experts."
        ),
        DraftTone.URGENT: (
            "Write an urgent call-to-action. The comment window is closing soon. "
            "Be direct, clear, and motivating. Lead with the deadline and the stakes."
        ),
    }

    prompt_parts = [
        f"Organization: {org_name}",
        f"Bill: {bill.title}",
        f"Jurisdiction: {bill.jurisdiction}",
        f"Status: {bill.status}",
        f"Urgency: {bill.urgency.value}",
        f"Summary: {bill.summary or 'No summary available.'}",
        f"Classification reasoning: {bill.classification_reasoning or 'Not classified.'}",
        f"Position: {stance}",
        f"Tone: {tone_instructions[tone]}",
    ]

    if bill.key_provisions:
        prompt_parts.append(f"Key provisions: {'; '.join(bill.key_provisions)}")

    if custom_context:
        prompt_parts.append(f"Additional context: {custom_context}")

    return "\n".join(prompt_parts)
