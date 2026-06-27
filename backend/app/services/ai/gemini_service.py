"""Gemini AI service with local fallback when no API key."""

import json
import logging
import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import ProcessingError

logger = logging.getLogger(__name__)


class GeminiService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()
        self._model = None
        self._vision_model = None
        if self.settings.gemini_api_key:
            self._init_client()

    @property
    def is_available(self) -> bool:
        return bool(self.settings.gemini_api_key and self._model)

    def _init_client(self) -> None:
        try:
            import google.generativeai as genai

            genai.configure(api_key=self.settings.gemini_api_key)
            self._model = genai.GenerativeModel(self.settings.gemini_model)
            self._vision_model = genai.GenerativeModel(self.settings.gemini_vision_model)
        except Exception as exc:
            logger.warning("Failed to initialize Gemini client: %s", exc)
            self._model = None
            self._vision_model = None

    async def generate_text(
        self,
        prompt: str,
        *,
        system_instruction: str | None = None,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        if self.is_available:
            try:
                full_prompt = prompt
                if system_instruction:
                    full_prompt = f"{system_instruction}\n\n{prompt}"
                response = await self._model.generate_content_async(
                    full_prompt,
                    generation_config={"temperature": temperature},
                )
                text = response.text or ""
                return {"text": text.strip(), "confidence": 0.92, "source": "gemini"}
            except Exception as exc:
                logger.warning("Gemini generate_text failed, using fallback: %s", exc)

        return self._fallback_text(prompt, system_instruction)

    async def generate_json(
        self,
        prompt: str,
        *,
        schema_hint: str | None = None,
        system_instruction: str | None = None,
    ) -> dict[str, Any]:
        json_prompt = prompt
        if schema_hint:
            json_prompt += f"\n\nRespond with valid JSON only. Schema: {schema_hint}"
        json_prompt += "\n\nRespond with valid JSON only, no markdown fences."

        if self.is_available:
            try:
                result = await self.generate_text(
                    json_prompt,
                    system_instruction=system_instruction or "You are a JSON extraction assistant.",
                    temperature=0.1,
                )
                parsed = self._parse_json(result["text"])
                parsed["_confidence"] = result["confidence"]
                parsed["_source"] = "gemini"
                return parsed
            except Exception as exc:
                logger.warning("Gemini generate_json failed, using fallback: %s", exc)

        return self._fallback_json(prompt, schema_hint)

    async def analyze_image(
        self,
        image_bytes: bytes,
        prompt: str,
        mime_type: str = "image/png",
    ) -> dict[str, Any]:
        if self.is_available and self._vision_model:
            try:
                import google.generativeai as genai

                image_part = {"mime_type": mime_type, "data": image_bytes}
                response = await self._vision_model.generate_content_async([prompt, image_part])
                text = response.text or ""
                return {"text": text.strip(), "confidence": 0.88, "source": "gemini_vision"}
            except Exception as exc:
                logger.warning("Gemini analyze_image failed: %s", exc)

        return {
            "text": "Image analysis unavailable without Gemini API key or vision model.",
            "confidence": 0.35,
            "source": "local_fallback",
            "reason": "GEMINI_API_KEY not configured or vision request failed",
        }

    def _parse_json(self, text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ProcessingError(
                "Failed to parse AI JSON response",
                reason=str(exc),
            ) from exc

    def _fallback_text(
        self, prompt: str, system_instruction: str | None = None
    ) -> dict[str, Any]:
        prompt_lower = prompt.lower()
        if "summarize" in prompt_lower or "summary" in prompt_lower:
            lines = [ln.strip() for ln in prompt.split("\n") if ln.strip()]
            body = " ".join(lines[-3:])[:500]
            return {
                "text": f"Summary (local): {body[:300]}..." if len(body) > 300 else f"Summary (local): {body}",
                "confidence": 0.55,
                "source": "local_heuristic",
            }
        if "intent" in prompt_lower:
            intent = "invoice_submission"
            if any(w in prompt_lower for w in ("timesheet", "hours", "payroll")):
                intent = "timesheet"
            elif any(w in prompt_lower for w in ("receipt", "expense")):
                intent = "receipt"
            elif any(w in prompt_lower for w in ("spam", "unsubscribe", "lottery")):
                intent = "spam"
            return {"text": intent, "confidence": 0.6, "source": "local_heuristic"}
        return {
            "text": "Local analysis: content processed using rule-based heuristics.",
            "confidence": 0.5,
            "source": "local_heuristic",
        }

    def _fallback_json(self, prompt: str, schema_hint: str | None) -> dict[str, Any]:
        prompt_lower = prompt.lower()
        data: dict[str, Any] = {"_confidence": 0.45, "_source": "local_heuristic"}

        employee_match = re.search(r"(?:employee|consultant|name)[:\s]+([A-Za-z\s\.]+)", prompt, re.I)
        hours_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:hours|hrs)", prompt_lower)
        rate_match = re.search(r"(?:rate|hourly)[:\s]*\$?(\d+(?:\.\d+)?)", prompt_lower)
        date_match = re.search(r"(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})", prompt)
        company_match = re.search(r"(?:company|client|vendor)[:\s]+([A-Za-z0-9\s&\.]+)", prompt, re.I)

        if employee_match:
            data["employee"] = employee_match.group(1).strip()
        if hours_match:
            data["hours"] = float(hours_match.group(1))
        if rate_match:
            data["rate"] = float(rate_match.group(1))
        if date_match:
            data["date"] = date_match.group(1)
        if company_match:
            data["company"] = company_match.group(1).strip()

        if "invoice" in prompt_lower or "classify" in prompt_lower:
            data["document_type"] = "invoice" if "invoice" in prompt_lower else "timesheet"
            data["classification_confidence"] = 0.55

        if schema_hint and not data.get("reason"):
            data["reason"] = "Extracted via regex heuristics; configure GEMINI_API_KEY for higher accuracy"

        return data
