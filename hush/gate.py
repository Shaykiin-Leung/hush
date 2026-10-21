"""The gate: interrupt, hold for the digest, or stay silent.

Order matters. Deterministic rules run first — a stale or duplicate
candidate never reaches the model. The model only scores what rules
cannot decide. Then two hard limits shape the outcome: a daily
interruption budget, and quiet hours. One principle overrides
everything else:

    Hush never silences a candidate it is unsure about.
    Uncertainty is held for the digest, where a human will see it.

Every decision is recorded with its reason, so the gate can always
be audited — and overruled.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime

from .candidates import Candidate
from .judge import Verdict

INTERRUPT = "interrupt"
DIGEST = "digest"
SILENCE = "silence"


@dataclass
class GateConfig:
    interrupt_threshold: float = 7.5
    digest_threshold: float = 4.0
    daily_interrupt_budget: int = 2
    quiet_start: int | None = 23  # local hour, inclusive
    quiet_end: int | None = 7     # local hour, exclusive
    quiet_interrupt_threshold: float = 9.0


@dataclass
class Decision:
    candidate_id: str
    decision: str
    reason: str
    score: float | None = None
    judge_source: str | None = None


@dataclass
class State:
    seen: dict[str, str] = field(default_factory=dict)   # hash -> id
    interrupts: dict[str, int] = field(default_factory=dict)  # day -> n

    @classmethod
    def load(cls, path: str) -> "State":
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                raw = json.load(fh)
            return cls(seen=raw.get("seen", {}),
                       interrupts=raw.get("interrupts", {}))
        return cls()

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"seen": self.seen, "interrupts": self.interrupts},
                      fh, indent=2, ensure_ascii=False)


class Gate:
    def __init__(self, config: GateConfig, judge, state: State):
        self.config = config
        self.judge = judge
        self.state = state

    def _in_quiet_hours(self, now: datetime) -> bool:
        start, end = self.config.quiet_start, self.config.quiet_end
        if start is None or end is None:
            return False
        hour = now.hour
        if start <= end:
            return start <= hour < end
        return hour >= start or hour < end

    def decide(self, candidate: Candidate, now: datetime) -> Decision:
        cfg = self.config

        # Rule 1: freshness. Old news may not interrupt the present.
        if candidate.is_stale(now):
            self.state.seen[candidate.content_hash] = candidate.id
            return Decision(candidate.id, SILENCE,
                            "stale: past its time-to-live before the "
                            "gate saw it")

        # Rule 2: never say the same thing twice.
        original = self.state.seen.get(candidate.content_hash)
        if original is not None:
            return Decision(candidate.id, SILENCE,
                            f"duplicate of {original}, already decided")

        verdict: Verdict = self.judge(candidate)
        self.state.seen[candidate.content_hash] = candidate.id
        day = now.date().isoformat()
        used = self.state.interrupts.get(day, 0)

        if verdict.score >= cfg.interrupt_threshold:
            if self._in_quiet_hours(now) and \
                    verdict.score < cfg.quiet_interrupt_threshold:
                return Decision(candidate.id, DIGEST,
                                "important, but it is quiet hours — "
                                "held for the digest",
                                verdict.score, verdict.source)
            if used >= cfg.daily_interrupt_budget:
                return Decision(candidate.id, DIGEST,
                                "important, but today's interruption "
                                f"budget ({cfg.daily_interrupt_budget}) "
                                "is spent — held for the digest",
                                verdict.score, verdict.source)
            self.state.interrupts[day] = used + 1
            return Decision(candidate.id, INTERRUPT,
                            f"worth interrupting for: {verdict.reason}",
                            verdict.score, verdict.source)

        if verdict.score >= cfg.digest_threshold:
            return Decision(candidate.id, DIGEST,
                            f"worth knowing, not worth a buzz: "
                            f"{verdict.reason}",
                            verdict.score, verdict.source)

        if not verdict.confident:
            # No signal is not a verdict. Hold it for human eyes.
            return Decision(candidate.id, DIGEST,
                            "no signal either way — held for the "
                            "digest instead of being silenced",
                            verdict.score, verdict.source)

        return Decision(candidate.id, SILENCE,
                        f"not worth your attention: {verdict.reason}",
                        verdict.score, verdict.source)
