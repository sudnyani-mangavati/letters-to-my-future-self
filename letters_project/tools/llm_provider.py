"""
LLM Provider for Letters to My Future Self.

Supports:
- MockLLM (default-safe, deterministic)
- Gemini via google-genai (Google AI Studio API key)

Design goals:
- No crashes in production (optional fail-open)
- Retries/backoff for 503/429 overload
- Fallback model list
- Agents can call: classify_emotion, summarise, generate_message, temporal_parse
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional, List

try:
    from google import genai  # google-genai
except Exception:
    genai = None  # type: ignore

try:
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential_jitter,
        retry_if_exception,
    )
except Exception:
    retry = None  # type: ignore
    stop_after_attempt = None  # type: ignore
    wait_exponential_jitter = None  # type: ignore
    retry_if_exception = None  # type: ignore


# -----------------------------
# Exceptions / Results
# -----------------------------

class LLMProviderError(RuntimeError):
    pass


@dataclass
class LLMResult:
    text: str
    model: str


# -----------------------------
# Mock implementation
# -----------------------------

class MockLLM:
    """Mock LLM providing basic heuristic behaviour."""

    def classify_emotion(self, text: str) -> str:
        lowered = (text or "").lower()
        positive_keywords = ["happy", "love", "joy", "excited", "pleased", "grateful", "proud", "amazing"]
        negative_keywords = ["sad", "angry", "upset", "anxious", "worried", "depressed", "scared", "hopeless"]
        if any(word in lowered for word in positive_keywords):
            return "positive"
        if any(word in lowered for word in negative_keywords):
            return "negative"
        return "neutral"

    def summarise(self, text: str, max_length: int = 60) -> str:
        t = (text or "").strip()
        if len(t) <= max_length:
            return t
        return t[: max_length - 3] + "..."

    def generate_message(self, content: str, metadata: Dict[str, str]) -> str:
        # IMPORTANT: This is a delivery wrapper; it does NOT rewrite the letter content.
        tone = (metadata or {}).get("tone", "neutral")
        preview = self.summarise(content, max_length=80)
        return (
            "Hi,\n\n"
            f"Tone detected when you wrote this: {tone}\n\n"
            "Your letter (unchanged):\n"
            f"{content}\n\n"
            f"Preview: {preview}\n"
        )

    def temporal_parse(self, expression: str) -> Optional[str]:
        expr = (expression or "").strip().lower()
        now = datetime.utcnow()
        if expr in ("now", "today"):
            return now.replace(microsecond=0).isoformat()
        if expr == "tomorrow":
            return (now + timedelta(days=1)).replace(microsecond=0).isoformat()
        if expr == "next year":
            return (now.replace(year=now.year + 1)).replace(microsecond=0).isoformat()
        match = re.match(r"in (\d+) days", expr)
        if match:
            days = int(match.group(1))
            return (now + timedelta(days=days)).replace(microsecond=0).isoformat()
        try:
            dt = datetime.fromisoformat(expression)
            return dt.replace(microsecond=0).isoformat()
        except Exception:
            return None


# -----------------------------
# Gemini implementation
# -----------------------------

class GeminiLLM:
    """
    Gemini LLM wrapper using google-genai SDK.

    Env:
      GEMINI_API_KEY=...
      GEMINI_MODEL=gemini-3-flash-preview   (example)
      GEMINI_FALLBACK_MODELS=model1,model2  (optional)
    """

    def __init__(self) -> None:
        if genai is None:
            raise LLMProviderError("google-genai is not installed. pip install google-genai")

        api_key = os.environ.get("GEMINI_API_KEY") or ""
        if not api_key.strip():
            raise LLMProviderError("GEMINI_API_KEY is missing or empty.")

        self.client = genai.Client(api_key=api_key)

        self.model = (os.environ.get("GEMINI_MODEL") or "gemini-3-flash-preview").strip()
        self.fallback_models = [
            m.strip()
            for m in (os.environ.get("GEMINI_FALLBACK_MODELS") or "").split(",")
            if m.strip()
        ]

        # tenacity is brought in by google-genai deps, but just in case:
        self._use_tenacity = retry is not None

    def _extract_text(self, r) -> Optional[str]:
        """
        Robust extraction because some SDK responses have r.text=None but candidates contain parts[text].
        """
        text = getattr(r, "text", None)
        if isinstance(text, str) and text.strip():
            return text.strip()

        for cand in (getattr(r, "candidates", None) or []):
            content = getattr(cand, "content", None)
            if not content:
                continue
            for part in (getattr(content, "parts", None) or []):
                t = getattr(part, "text", None)
                if isinstance(t, str) and t.strip():
                    return t.strip()

        return None

    def _is_retryable(self, ex: Exception) -> bool:
        msg = str(ex).lower()
        # Gemini overload/rate limit patterns
        return (
            "503" in msg
            or "unavailable" in msg
            or "429" in msg
            or "rate" in msg
            or "timeout" in msg
            or "temporarily" in msg
            or "overloaded" in msg
        )

    def _call_once_no_retry(self, model: str, prompt: str):
        return self.client.models.generate_content(model=model, contents=prompt)

    def _call_once(self, model: str, prompt: str):
        if not self._use_tenacity:
            # manual tiny retry if tenacity missing
            last = None
            for _ in range(4):
                try:
                    return self._call_once_no_retry(model, prompt)
                except Exception as ex:
                    last = ex
                    if not self._is_retryable(ex):
                        raise
                    time.sleep(1.2)
            raise last  # type: ignore[misc]

        # tenacity retry
        @retry(  # type: ignore[misc]
            stop=stop_after_attempt(4),
            wait=wait_exponential_jitter(initial=1, max=8),
            retry=retry_if_exception(lambda e: self._is_retryable(e)),
            reraise=True,
        )
        def _inner():
            return self._call_once_no_retry(model, prompt)

        return _inner()

    def generate_text(self, prompt: str) -> LLMResult:
        prompt = (prompt or "").strip()
        if not prompt:
            raise LLMProviderError("Empty prompt passed to Gemini.")

        models_to_try: List[str] = [self.model] + [m for m in self.fallback_models if m != self.model]
        last_error: Optional[Exception] = None

        for m in models_to_try:
            try:
                r = self._call_once(m, prompt)
                text = self._extract_text(r)
                if text:
                    return LLMResult(text=text, model=m)
                last_error = LLMProviderError(f"{m}: Gemini returned no text content.")
            except Exception as ex:
                last_error = ex
                continue

        raise LLMProviderError(f"All Gemini models failed. Last error: {last_error}")


# -----------------------------
# Provider facade (used by agents)
# -----------------------------

class LLMProvider:
    """
    Wrapper class to abstract between real and mock LLMs.

    Modes:
      - mock (default)
      - gemini (requires GEMINI_API_KEY)
    Env:
      LLM_PROVIDER=mock|gemini
      LLM_MOCK=1 forces mock
      LLM_FAIL_OPEN=1 -> if Gemini fails, fall back to MockLLM instead of crashing
    """

    def __init__(self, mode: str = "mock") -> None:
        # Keep backward compatibility:
        # - If orchestrator calls LLMProvider(mode="mock") it still works.
        # - If mode not provided, env decides.
        env_provider = (os.environ.get("LLM_PROVIDER") or "").strip().lower()
        force_mock = (os.environ.get("LLM_MOCK") or "0").strip() == "1"

        chosen = (mode or "").strip().lower() or env_provider or "mock"
        if force_mock:
            chosen = "mock"

        self.mode = chosen
        self._mock = MockLLM()

        if chosen == "gemini":
            self._impl = GeminiLLM()
        else:
            self._impl = self._mock

    def _fail_open(self) -> bool:
        return (os.environ.get("LLM_FAIL_OPEN") or "1").strip() == "1"

    # ---- Agent-facing methods ----

    def classify_emotion(self, text: str) -> str:
        if isinstance(self._impl, MockLLM):
            return self._impl.classify_emotion(text)

        prompt = (
            "Classify the overall emotional tone of the text as exactly one word: "
            "positive, negative, or neutral.\n\n"
            f"TEXT:\n{text}\n\n"
            "Answer with exactly one word."
        )
        try:
            out = self._impl.generate_text(prompt).text.lower().strip()
            if "positive" in out:
                return "positive"
            if "negative" in out:
                return "negative"
            return "neutral"
        except Exception:
            if self._fail_open():
                return self._mock.classify_emotion(text)
            raise

    def summarise(self, text: str, max_length: int = 60) -> str:
        if isinstance(self._impl, MockLLM):
            return self._impl.summarise(text, max_length=max_length)

        prompt = (
            f"Summarize the following text in one short sentence (max {max_length} characters). "
            "Do NOT rewrite the original letter content; only provide a summary.\n\n"
            f"TEXT:\n{text}\n\n"
            "Return ONLY the summary sentence."
        )
        try:
            out = self._impl.generate_text(prompt).text.strip()
            # Safety: hard-trim
            out = out.replace("\n", " ").strip()
            if len(out) > max_length:
                out = out[: max_length - 3] + "..."
            return out
        except Exception:
            if self._fail_open():
                return self._mock.summarise(text, max_length=max_length)
            raise

    def generate_message(self, content: str, metadata: Dict[str, str]) -> str:
        """
        Delivery wrapper (optional). MUST NOT rewrite the letter content.
        Your MessengerAgent already uses body=content. So this is mostly unused.
        """
        if isinstance(self._impl, MockLLM):
            return self._impl.generate_message(content, metadata)

        tone = (metadata or {}).get("tone", "neutral")
        prompt = (
            "Write a short friendly delivery note (2-4 lines). "
            "Do NOT rewrite or paraphrase the letter. "
            "The letter will be attached separately.\n\n"
            f"Tone: {tone}\n"
            "Return ONLY the delivery note."
        )
        try:
            note = self._impl.generate_text(prompt).text.strip()
            return note
        except Exception:
            if self._fail_open():
                return self._mock.generate_message(content, metadata)
            raise

    def temporal_parse(self, expression: str) -> Optional[str]:
        # Keep this mock/simple (production would use dateparser)
        return self._mock.temporal_parse(expression)


__all__ = ["LLMProvider", "MockLLM", "LLMProviderError", "LLMResult"]
