"""OpenAI LLM provider for Anpurna Properties.

The rest of the application talks to this provider through LLMClient so the
provider can be replaced later without changing CRM/business logic.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger("anpurna_properties")


class LLMError(RuntimeError):
    """Raised when the configured LLM provider cannot return valid output."""


class LLMClient:
    def __init__(self) -> None:
        self.provider = settings.LLM_PROVIDER.lower()
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.LLM_MODEL
        self.mock = settings.AI_CALLING_MOCK_PROVIDERS
        self.timeout = settings.PROVIDER_HTTP_TIMEOUT_SECONDS
        self.base_url = settings.LLM_API_BASE_URL.rstrip("/")

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _structured(
        self,
        *,
        name: str,
        schema: dict[str, Any],
        instructions: str,
        transcript_turns: list[dict[str, str]],
    ) -> dict[str, Any]:
        if self.provider != "openai":
            raise LLMError(f"Unsupported LLM_PROVIDER={self.provider!r}")
        if not self.api_key:
            raise LLMError("OPENAI_API_KEY is not configured")

        transcript = "\n".join(
            f"{turn.get('speaker', 'Unknown')}: {turn.get('text', '')}"
            for turn in transcript_turns
        )
        payload = {
            "model": self.model,
            "instructions": instructions,
            "input": transcript,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": name,
                    "strict": True,
                    "schema": schema,
                }
            },
        }

        try:
            response = requests.post(
                f"{self.base_url}/responses",
                json=payload,
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            raise LLMError(f"OpenAI request failed: {exc}") from exc
        except ValueError as exc:
            raise LLMError("OpenAI returned invalid JSON") from exc

        text_parts: list[str] = []
        for output in data.get("output", []):
            for content in output.get("content", []):
                if content.get("type") in {"output_text", "text"} and content.get("text"):
                    text_parts.append(content["text"])

        if not text_parts:
            raise LLMError("OpenAI response contained no structured output")

        try:
            return json.loads("".join(text_parts))
        except json.JSONDecodeError as exc:
            raise LLMError("OpenAI structured output was not valid JSON") from exc

    def extract_qualification_fields(self, turns: list[dict[str, str]]) -> dict[str, Any]:
        """Extract the CRM qualification fields from a completed call."""
        if self.mock:
            return self._mock_qualification(turns)

        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "customer_name": {"type": "string"},
                "requirement_type": {"type": "string", "enum": ["Buy", "Sell", "Rent"]},
                "property_type": {"type": "string"},
                "budget_min": {"type": ["integer", "null"]},
                "budget_max": {"type": ["integer", "null"]},
                "location": {"type": "string"},
                "timeline": {"type": "string"},
                "interest_level": {"type": "string", "enum": ["High", "Medium", "Low"]},
                "needs_human_followup": {"type": "boolean"},
                "human_followup_reason": {"type": "string"},
            },
            "required": [
                "customer_name", "requirement_type", "property_type", "budget_min",
                "budget_max", "location", "timeline", "interest_level",
                "needs_human_followup", "human_followup_reason",
            ],
        }
        return self._structured(
            name="qualification",
            schema=schema,
            instructions=(
                "Extract only facts stated or strongly implied in the call. "
                "Do not invent property availability, pricing, or customer details. "
                "Use empty strings/null for missing values. Flag human follow-up for "
                "an explicit human request, unresolved ambiguity after clarification, "
                "or complex negotiation."
            ),
            transcript_turns=turns,
        )

    def generate_call_summary(
        self,
        turns: list[dict[str, str]],
        lead=None,
    ) -> dict[str, Any]:
        """Generate the structured CRM call summary."""
        if self.mock:
            return {
                "requirement": next(
                    (turn["text"] for turn in turns if turn.get("speaker") == "Customer"),
                    "Requirement not captured",
                ),
                "budget_text": "Not captured",
                "location": getattr(lead, "location", "") or "",
                "interest_level": getattr(lead, "interest_level", "") or "Medium",
                "key_points": ["Auto-generated from mock transcript extraction"],
                "suggested_action": "Review call and confirm next step with customer",
            }

        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "requirement": {"type": "string"},
                "budget_text": {"type": "string"},
                "location": {"type": "string"},
                "interest_level": {"type": "string", "enum": ["High", "Medium", "Low"]},
                "key_points": {"type": "array", "items": {"type": "string"}},
                "suggested_action": {"type": "string"},
            },
            "required": [
                "requirement", "budget_text", "location", "interest_level",
                "key_points", "suggested_action",
            ],
        }
        return self._structured(
            name="call_summary",
            schema=schema,
            instructions=(
                "Create a concise CRM call summary using only transcript facts. "
                "Include a practical next action. Never invent inventory, pricing, "
                "availability, or customer information."
            ),
            transcript_turns=turns,
        )

    @staticmethod
    def _mock_qualification(turns: list[dict[str, str]]) -> dict[str, Any]:
        """Deterministic fallback used only when mock providers are enabled."""
        import re

        text = " ".join(
            turn.get("text", "") for turn in turns if turn.get("speaker") == "Customer"
        ).lower()
        requirement = "Rent" if ("kiraye" in text or "rent" in text) else "Sell" if (
            "bechna" in text or "sell" in text
        ) else "Buy"
        match = re.search(r"(\d+)[\s-]*(?:se|to)?[\s-]*(\d+)?\s*lakh", text)
        minimum = int(match.group(1)) * 100_000 if match else None
        maximum = int(match.group(2)) * 100_000 if match and match.group(2) else minimum
        return {
            "customer_name": "",
            "requirement_type": requirement,
            "property_type": "Apartment",
            "budget_min": minimum,
            "budget_max": maximum,
            "location": "",
            "timeline": "",
            "interest_level": "Medium",
            "needs_human_followup": False,
            "human_followup_reason": "",
        }
