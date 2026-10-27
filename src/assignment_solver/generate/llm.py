"""Tiny client for a local Ollama server. Nothing leaves your machine."""
from __future__ import annotations

import requests


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, cfg: dict):
        m = cfg["model"]
        self.host = m["host"].rstrip("/")
        self.options = {
            "temperature": m["temperature"],
            "num_ctx": m["num_ctx"],
            "num_predict": m["num_predict"],
        }
        self.timeout = m["timeout_seconds"]
        self.model = self._pick_model(m["name"], m.get("fallback"))

    def _installed(self) -> list[str]:
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=10)
            r.raise_for_status()
        except requests.RequestException as exc:
            raise OllamaError(
                f"Cannot reach Ollama at {self.host}. Install it from https://ollama.com and make sure it is running."
            ) from exc
        return [m["name"] for m in r.json().get("models", [])]

    def _pick_model(self, name: str, fallback: str | None) -> str:
        installed = self._installed()

        def has(n: str) -> str | None:
            for m in installed:
                if m == n or m.split(":")[0] == n or m == f"{n}:latest":
                    return m
            return None

        for candidate in (name, fallback):
            if candidate and (found := has(candidate)):
                return found
        raise OllamaError(
            f"Neither '{name}' nor fallback '{fallback}' is installed. Run `ollama pull {fallback}` "
            f"or import your fine-tuned model (see README)."
        )

    def chat_json(self, messages: list[dict]) -> str:
        payload = {"model": self.model, "messages": messages, "stream": False, "format": "json", "options": self.options}
        try:
            r = requests.post(f"{self.host}/api/chat", json=payload, timeout=self.timeout)
            r.raise_for_status()
        except requests.RequestException as exc:
            raise OllamaError(f"Ollama request failed: {exc}") from exc
        return r.json()["message"]["content"]
