"""LLM access: Google Gemini (google-genai SDK), plus an offline mock for dry runs."""
import os
import random
import time

from .prompts import SYSTEM_PROMPT

DEFAULT_MODEL = "gemini-3.5-flash-lite"
DEFAULT_FALLBACK = "gemini-3.5-flash"        # used automatically when the main model is overloaded
RETRY_CODES = {429, 500, 502, 503, 504}


class GeminiClient:
    def __init__(self, model: str | None = None, max_tokens: int = 8000, fallback_model: str | None = None):
        try:
            from google import genai
            from google.genai import errors, types
        except ImportError as e:                         # pragma: no cover
            raise SystemExit("Install the SDK first: pip install google-genai") from e
        key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise SystemExit(
                "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key "
                "(create one at https://aistudio.google.com/apikey), or run with --dry-run."
            )
        self._types, self._errors = types, errors
        self.client = genai.Client(api_key=key)
        self.model = model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
        self.fallback_model = fallback_model or os.getenv("GEMINI_FALLBACK_MODEL", DEFAULT_FALLBACK)
        if self.fallback_model in ("", "none", self.model):
            self.fallback_model = None
        self.config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            max_output_tokens=max_tokens,
            temperature=0.4,
        )

    def _contents(self, messages: list[dict]):
        t = self._types
        return [
            t.Content(role="model" if m["role"] == "assistant" else "user",
                      parts=[t.Part(text=m["content"])])
            for m in messages
        ]

    def _generate(self, model, messages):
        resp = self.client.models.generate_content(
            model=model, contents=self._contents(messages), config=self.config)
        text = (resp.text or "").strip()
        if not text:
            raise RuntimeError("Gemini returned an empty response (possibly blocked by a safety filter).")
        return text

    def complete(self, messages: list[dict], retries: int = 6, switch_after: int = 3) -> str:
        """messages: [{'role': 'user'|'assistant', 'content': str}, ...]
        Overloaded/rate-limited calls are retried with backoff. After `switch_after` failures on the
        main model, the less busy fallback model takes over for the remaining attempts."""
        delay, model = 2.0, self.model
        for attempt in range(1, retries + 1):
            try:
                return self._generate(model, messages)
            except self._errors.APIError as e:
                if getattr(e, "code", None) not in RETRY_CODES or attempt == retries:
                    raise
                if attempt == switch_after and self.fallback_model and model != self.fallback_model:
                    model = self.fallback_model
                    print(f"   {self.model} is overloaded; switching to {model}")
                    continue
                wait = delay + random.uniform(0, 1.5)
                print(f"   transient API error ({e.code}); retry in {wait:.0f}s")
                time.sleep(wait)
                delay = min(delay * 2, 60)


class MockClient:
    """Offline stand-in so the whole pipeline can be tested without an API key."""
    model = "mock"

    def complete(self, messages: list[dict], retries: int = 0) -> str:
        q = messages[0]["content"]
        if "practical question" in q:
            return (
                "```python\nimport statistics\nvalues = [3, 5, 7, 9]\n"
                "print('Mean:', statistics.mean(values))\n```\n\n"
                "The mean of the sample values is 6, showing the program runs correctly."
            )
        return (
            "This is a placeholder answer produced in dry-run mode.\n\n"
            "### Key points\n- First point with **bold** text\n- Second point with `inline code`\n\n"
            "| Aspect | Option A | Option B |\n|---|---|---|\n| Speed | Fast | Slow |\n| Cost | Low | High |\n\n"
            "Example: a small worked example appears here."
        )