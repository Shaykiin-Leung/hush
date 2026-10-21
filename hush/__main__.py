"""Hush command line.

    python -m hush run --inbox candidates.jsonl [--config hush.toml]
                       [--state hush_state.json] [--out reports/]
                       [--at 2026-10-21T21:00:00+08:00]

Reads every candidate in the inbox, runs the gate, prints a summary
and writes the day's silence report.
"""

from __future__ import annotations

import argparse
import os
import sys
import tomllib
from datetime import datetime

from .candidates import load_candidates, parse_ts
from .gate import Gate, GateConfig, State
from .judge import OllamaJudge, heuristic_verdict
from .report import render_report


def load_config(path: str | None) -> tuple[GateConfig, dict]:
    gate = GateConfig()
    ollama = {"url": "http://localhost:11434", "model": "qwen2.5:3b",
              "timeout": 20.0}
    if path:
        with open(path, "rb") as fh:
            raw = tomllib.load(fh)
        for key, value in raw.get("gate", {}).items():
            setattr(gate, key, value)
        ollama.update(raw.get("ollama", {}))
    return gate, ollama


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hush")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="run the gate over an inbox file")
    run.add_argument("--inbox", required=True)
    run.add_argument("--config")
    run.add_argument("--state", default="hush_state.json")
    run.add_argument("--out", default="reports")
    run.add_argument("--at", help="ISO timestamp to decide 'now' "
                                  "(defaults to the current time)")
    run.add_argument("--no-model", action="store_true",
                     help="skip the local model, use heuristics only")
    args = parser.parse_args(argv)

    gate_config, ollama = load_config(args.config)
    if args.no_model:
        judge = heuristic_verdict
    else:
        judge = OllamaJudge(ollama["url"], ollama["model"],
                            float(ollama["timeout"]))

    now = parse_ts(args.at) if args.at else datetime.now().astimezone()
    candidates = load_candidates(args.inbox)
    state = State.load(args.state)
    gate = Gate(gate_config, judge, state)

    decisions = [gate.decide(c, now) for c in candidates]
    state.save(args.state)

    by_id = {c.id: c for c in candidates}
    day = now.date().isoformat()
    report = render_report(decisions, by_id, day)
    os.makedirs(args.out, exist_ok=True)
    report_path = os.path.join(args.out, f"hush-report-{day}.md")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(report)

    counts = {}
    for record in decisions:
        counts[record.decision] = counts.get(record.decision, 0) + 1
    print(f"hush: {len(decisions)} candidates -> "
          f"interrupt={counts.get('interrupt', 0)} "
          f"digest={counts.get('digest', 0)} "
          f"silence={counts.get('silence', 0)}")
    print(f"hush: report written to {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
