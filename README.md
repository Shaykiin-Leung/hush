# Hush 🤫

**Every agent you run wants your attention. Hush decides which ones get it.**

Hush is an attention firewall. It sits between you and everything that
wants to interrupt you — cron jobs, agents, reminders, feeds — and every
candidate has to pass a gate before it may buzz your phone:

1. **Freshness first.** Stale candidates (past their time-to-live) and
   duplicates are turned away by plain rules. They never reach the model.
2. **A local model judges.** An open-weight model running on your own
   machine (Ollama + qwen2.5:3b by default) scores what the rules cannot
   decide. The stream Hush reads is the most private one you have, so
   the judging never leaves your computer.
3. **Three answers only.** *Interrupt* — right now. *Digest* — worth
   knowing, not worth a buzz. *Silence* — turned away, with the reason
   written down.
4. **A hard budget.** At most N interruptions per day (default: 2).
   Overflow is not dropped; it is held for the digest. Quiet hours raise
   the bar further.

And one principle overrides everything:

> **Hush never silences a candidate it is unsure about.**
> Uncertainty is held for the digest, where a human will see it.

## The silence report

Most notification systems report what they delivered. Hush reports what
it *kept away*. From the bundled demo
(`examples/candidates.jsonl`, 10 candidates):

```
10 candidates knocked. 2 reached you, 4 were held for this digest,
4 were turned away at the gate.

🚨 Reached you:     home server disk at 94%, backups failing · proxy
                    node latency doubled, packet loss at 18%
📰 Held for digest: CI failed on main (important — but today's
                    interruption budget is spent), a delivered parcel,
                    weekend rain, a newsletter
🤫 Turned away:     a duplicate of the disk alert, a meeting reminder
                    that expired before the gate saw it, a flash sale,
                    a celebrity gossip roundup
```

Every line carries its score, who judged it, and why — silence with an
audit trail, not a black hole.

## Quickstart

Requires Python 3.11+. No third-party dependencies. For model judging,
run [Ollama](https://ollama.com) locally with `qwen2.5:3b` pulled;
without it, Hush falls back to a keyword heuristic and labels its
verdicts `heuristic-fallback` — honest about its own limits.

```bash
cp config.example.toml hush.toml        # optional; defaults work too
python -m hush run --inbox examples/candidates.jsonl
cat reports/hush-report-*.md
python -m unittest discover -s tests
```

Candidates are JSON Lines — anything that can append a line to a file
can knock on the gate:

```json
{"id": "disk-1", "source": "watchdog", "title": "Disk at 94%",
 "body": "Backups failing.", "ts": "2026-10-21T20:12:00+08:00",
 "ttl_minutes": 720}
```

## Where this comes from

Hush is distilled from a real, running personal agent system: one home
PC acting as the single "brain", two remote "hands", seven specialist
profiles and 24 scheduled jobs, all reporting to one person. A system
like that either learns when to shut up, or it gets unplugged. Its
rules — *queries run automatically, actions need confirmation; a daily
budget valve on proactivity; freshness is re-checked before anything is
delivered* — kept it alive. Hush is those rules, extracted into a small
tool anyone can put in front of their own noisy stack.

Slow is the feature: no streams, no real-time firehose — candidates are
judged in batches, interruptions are rationed, and everything else
arrives once, in the digest, when *you* choose to read it.

## Design notes

- **Rules before models.** Deterministic checks (stale, duplicate,
  budget, quiet hours) are code, not prompts — auditable and free.
- **The model is replaceable.** Any Ollama-served open-weight model
  works; the gate logic does not change.
- **Every decision is logged with a reason.** If the gate was wrong,
  the report shows exactly where.

---

Design distilled from the author's private personal-agent system; all
code in this repository was written fresh during the DEV Hacktoberfest
Week 3 challenge window (Oct 19–25, 2026).

MIT — see [LICENSE](LICENSE).
