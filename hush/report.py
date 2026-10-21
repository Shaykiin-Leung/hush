"""The silence report: proof of what you did *not* have to see.

Most notification systems report what they delivered. Hush reports
what it kept away — every silenced candidate, with the reason — so
silence stays accountable instead of becoming a black hole.
"""

from __future__ import annotations

from .candidates import Candidate
from .gate import DIGEST, INTERRUPT, SILENCE, Decision


def render_report(decisions: list[Decision],
                  candidates: dict[str, Candidate],
                  day: str) -> str:
    groups = {INTERRUPT: [], DIGEST: [], SILENCE: []}
    for record in decisions:
        groups[record.decision].append(record)

    total = len(decisions)
    lines = [
        f"# 🤫 Hush report — {day}",
        "",
        f"{total} candidates knocked. "
        f"{len(groups[INTERRUPT])} reached you, "
        f"{len(groups[DIGEST])} were held for this digest, "
        f"{len(groups[SILENCE])} were turned away at the gate.",
        "",
    ]

    def section(title: str, key: str) -> None:
        lines.append(f"## {title} ({len(groups[key])})")
        lines.append("")
        if not groups[key]:
            lines.append("_None._")
            lines.append("")
            return
        for record in groups[key]:
            cand = candidates[record.candidate_id]
            score = (f" · score {record.score:g}"
                     if record.score is not None else "")
            source = (f" · judged by {record.judge_source}"
                      if record.judge_source else "")
            lines.append(f"- **{cand.title}** "
                         f"({cand.source}{score}{source})")
            lines.append(f"  _{record.reason}_")
        lines.append("")

    section("🚨 Reached you", INTERRUPT)
    section("📰 Held for the digest", DIGEST)
    section("🤫 Turned away", SILENCE)
    lines.append("---")
    lines.append("Every decision above carries its reason. "
                 "If the gate was wrong, the audit trail shows where.")
    return "\n".join(lines) + "\n"
