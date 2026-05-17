"""Hugging Face Inference API client with a compatible interface.

Provides `HFClient`, `HFClientError`, and `extract_json_block` used by the
prompt pipeline. The client converts OpenAI-style messages to a single
prompt string for HF models.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.core.logging import logger


class HFClientError(RuntimeError):
    """Raised for any Hugging Face-related error."""


def extract_json_block(text: str) -> str:
    fenced = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.IGNORECASE | re.DOTALL)
    if fenced:
        return fenced.group(1).strip()

    obj_start = text.find("{")
    obj_end = text.rfind("}")
    if obj_start != -1 and obj_end != -1 and obj_end > obj_start:
        return text[obj_start: obj_end + 1].strip()

    arr_start = text.find("[")
    arr_end = text.rfind("]")
    if arr_start != -1 and arr_end != -1 and arr_end > arr_start:
        return text[arr_start: arr_end + 1].strip()

    raise HFClientError("HF response did not contain a JSON object or array")


DEFAULT_TIMEOUT = 60.0


class HFClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.api_key = api_key or settings.HUGGINGFACE_API_KEY
        self.model = model or settings.HF_MODEL
        self.temperature = temperature if temperature is not None else settings.HF_TEMPERATURE
        self.timeout = timeout

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _get_payload(self, messages: List[Dict[str, str]], temperature: Optional[float]) -> Dict[str, Any]:
        payload = {
            "model": str(self.model),
            "messages": messages,
            "max_tokens": 1024,
        }
        temp = temperature if temperature is not None else self.temperature
        if temp is not None:
            payload["temperature"] = temp
        
        return payload

    def _parse_response(self, raw: str) -> str:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.debug("Failed to decode HF raw response as JSON")
            raise HFClientError("HuggingFace returned invalid JSON") from exc

        # Handle different HF response shapes
        if isinstance(data, dict) and "error" in data:
            raise HFClientError(f"HuggingFace error: {data.get('error')}")

        # OpenAI format: {'choices': [{'message': {'content': '...'}}]}
        if isinstance(data, dict) and "choices" in data:
            try:
                return data["choices"][0]["message"]["content"]
            except (KeyError, IndexError):
                pass

        # Common: [{'generated_text': '...'}] or {'generated_text': '...'}
        if isinstance(data, list) and data and isinstance(data[0], dict) and "generated_text" in data[0]:
            return data[0]["generated_text"]
        if isinstance(data, dict) and "generated_text" in data:
            return data["generated_text"]

        # Some models return a string directly
        if isinstance(data, str):
            return data

        # Last resort: try to find text fields
        def find_text(obj: Any) -> Optional[str]:
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if isinstance(v, str) and len(v) > 0:
                        return v
                    if isinstance(v, (dict, list)):
                        res = find_text(v)
                        if res:
                            return res
            if isinstance(obj, list):
                for item in obj:
                    res = find_text(item)
                    if res:
                        return res
            return None

        res = find_text(data)
        if res is not None:
            return res

        raise HFClientError("Unexpected HuggingFace response payload structure")

    def chat(self, messages: List[Dict[str, str]], temperature: Optional[float] = None) -> str:
        if not self.api_key:
            raise HFClientError("HUGGINGFACE_API_KEY is not configured")
        
        url = "https://router.huggingface.co/v1/chat/completions"
        headers = self._get_headers()
        payload = self._get_payload(messages, temperature)
        
        logger.debug(f"HF Request Payload: {json.dumps(payload)}")
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                return self._parse_response(response.text)
        except httpx.HTTPStatusError as exc:
            try:
                body = exc.response.text
            except Exception:
                body = "(unable to read response body)"
            raise HFClientError(f"HuggingFace HTTP {exc.response.status_code}: {body}") from exc
        except httpx.RequestError as exc:
            raise HFClientError(f"HuggingFace request failed: {exc}") from exc

    async def achat(self, messages: List[Dict[str, str]], temperature: Optional[float] = None) -> str:
        if not self.api_key:
            raise HFClientError("HUGGINGFACE_API_KEY is not configured")

        url = "https://router.huggingface.co/v1/chat/completions"
        headers = self._get_headers()
        payload = self._get_payload(messages, temperature)
        
        logger.debug(f"HF Async Request Payload: {json.dumps(payload)}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                return self._parse_response(response.text)
        except httpx.HTTPStatusError as exc:
            try:
                body = exc.response.text
            except Exception:
                body = "(unable to read response body)"
            raise HFClientError(f"HuggingFace HTTP {exc.response.status_code}: {body}") from exc
        except httpx.RequestError as exc:
            raise HFClientError(f"HuggingFace request failed: {exc}") from exc
