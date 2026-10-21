"""Judgment: how much does this candidate deserve your attention?

The judge is a local open-weight model (Ollama, qwen2.5:3b by
default). The candidates Hush reads are the most private stream a
person has — messages, agent output, reminders — so the judging
happens on the owner's machine and nothing leaves it.

If the model is unreachable, a keyword heuristic takes over and says
so: every verdict records where it came from, and a verdict with no
signal at all is marked unconfident so the gate can refuse to silence
on it.
"""

from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass

from .candidates import Candidate


@dataclass
class Verdict:
    score: float  # 0 (worthless) .. 10 (drop everything)
    reason: str
    source: str  # "ollama" | "heuristic" | "heuristic-fallback"
    confident: bool = True


POSITIVE = {
    "urgent": 3, "failed": 2, "failing": 2, "failure": 2, "down": 2,
    "offline": 2, "deadline": 2, "expires": 2, "expiring": 2,
    "security": 2, "error": 2, "disk": 1, "backup": 1, "backups": 1,
    "latency": 1, "loss": 1, "rain": 1, "delivered": 1, "meeting": 1,
    "ci": 1, "payment": 2, "cancelled": 2,
}
NEGATIVE = {
    "sale": -3, "discount": -3, "giveaway": -3, "celebrity": -3,
    "gossip": -3, "flash": -2, "sponsored": -2, "promo": -2,
    "off": -1, "deal": -1,
}
BASE_SCORE = 4.0


def heuristic_verdict(candidate: Candidate, source: str = "heuristic") -> Verdict:
    words = set(re.findall(r"[a-z0-9]+", candidate.text.lower()))
    score = BASE_SCORE
    hits: list[str] = []
    for word, weight in {**POSITIVE, **NEGATIVE}.items():
        if word in words:
            score += weight
            hits.append(word)
    score = max(0.0, min(10.0, score))
    if hits:
        reason = f"keyword signal: {', '.join(sorted(hits))}"
    else:
        reason = "no keyword signal either way"
    return Verdict(score=score, reason=reason, source=source,
                   confident=bool(hits))


class OllamaJudge:
    """Score candidates with a local model; fall back honestly."""

    def __init__(self, url: str, model: str, timeout: float = 20.0):
        self.url = url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def __call__(self, candidate: Candidate) -> Verdict:
        prompt = (
            "You are the attention gatekeeper for a busy person. "
            "Score how much this candidate notification deserves to "
            "interrupt them right now, from 0 (worthless) to 10 "
            "(drop everything). Reply with ONLY a JSON object like "
            '{"score": 7, "reason": "short reason"}.\n\n'
            f"Source: {candidate.source}\n"
            f"Title: {candidate.title}\nBody: {candidate.body}"
        )
        payload = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }).encode("utf-8")
        request = urllib.request.Request(
            f"{self.url}/api/generate", data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({}))
            with opener.open(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
            text = data.get("response", "")
            match = re.search(r"\{.*\}", text, re.DOTALL)
            parsed = json.loads(match.group(0)) if match else {}
            score = float(parsed["score"])
            return Verdict(
                score=max(0.0, min(10.0, score)),
                reason=str(parsed.get("reason", "model verdict")),
                source="ollama",
            )
        except Exception:
            fallback = heuristic_verdict(candidate,
                                         source="heuristic-fallback")
            fallback.reason += " (local model unreachable)"
            return fallback
