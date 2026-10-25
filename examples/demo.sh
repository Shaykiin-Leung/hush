#!/usr/bin/env bash
# Hush 2-minute demo: run the gate over 10 sample candidates and
# open the silence report it produces.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== 10 candidates are waiting in the inbox =="
cat examples/candidates.jsonl | python3 -c "
import json, sys
for line in sys.stdin:
    c = json.loads(line)
    print(f\"  [{c['source']}] {c['title']}\")
"

echo
echo "== Running the gate (fresh state, fixed clock: 21:00) =="
rm -f hush_state.json
python3 -m hush run --inbox examples/candidates.jsonl \
  --at 2026-10-21T21:00:00+08:00

echo
echo "== The silence report =="
cat reports/hush-report-2026-10-21.md

echo
echo "== Run it again: everything is a duplicate now =="
python3 -m hush run --inbox examples/candidates.jsonl \
  --at 2026-10-22T21:05:00+08:00
# NOTE: second run uses a different day on purpose, so its report
# (hush-report-2026-10-22.md, all duplicates) does not overwrite
# the first run's meaningful report (hush-report-2026-10-21.md).
