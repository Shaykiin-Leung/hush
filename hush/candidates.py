"""Candidate notifications: anything that wants your attention.

A candidate is one would-be interruption — a cron result, an agent
message, a reminder, a feed item — normalised into a small record.
Sources write candidates as JSON Lines into an inbox file; Hush never
talks to the sources directly, which keeps the gate source-agnostic.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone


def parse_ts(value: str) -> datetime:
    """Parse an ISO-8601 timestamp; a trailing 'Z' means UTC."""
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@dataclass
class Candidate:
    id: str
    source: str
    title: str
    body: str
    ts: datetime
    ttl_minutes: int | None = None  # after ts + ttl the candidate is stale

    @property
    def text(self) -> str:
        return f"{self.title}\n{self.body}"

    @property
    def content_hash(self) -> str:
        """Stable hash of the normalised content, used for dedup."""
        normalised = " ".join(self.text.lower().split())
        return hashlib.sha256(normalised.encode("utf-8")).hexdigest()

    def is_stale(self, now: datetime) -> bool:
        if self.ttl_minutes is None:
            return False
        age_minutes = (now - self.ts).total_seconds() / 60.0
        return age_minutes > self.ttl_minutes


def load_candidates(path: str) -> list[Candidate]:
    """Load candidates from a JSON Lines file, oldest first."""
    candidates: list[Candidate] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            candidates.append(
                Candidate(
                    id=str(raw["id"]),
                    source=str(raw.get("source", "unknown")),
                    title=str(raw.get("title", "")),
                    body=str(raw.get("body", "")),
                    ts=parse_ts(str(raw["ts"])),
                    ttl_minutes=raw.get("ttl_minutes"),
                )
            )
    candidates.sort(key=lambda c: c.ts)
    return candidates
