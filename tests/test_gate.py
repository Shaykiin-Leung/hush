"""Gate tests: the rules must hold even when the model is wrong."""

import sys
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, ".")

from hush.candidates import Candidate
from hush.gate import DIGEST, INTERRUPT, SILENCE, Gate, GateConfig, State
from hush.judge import Verdict

TZ = timezone(timedelta(hours=8))
NOW = datetime(2026, 10, 21, 21, 0, tzinfo=TZ)


def candidate(cid, title="Something happened", body="", minutes_ago=5,
              ttl=600):
    return Candidate(id=cid, source="test", title=title, body=body,
                     ts=NOW - timedelta(minutes=minutes_ago),
                     ttl_minutes=ttl)


def fixed_judge(score, confident=True):
    return lambda c: Verdict(score=score, reason="fixed",
                             source="test", confident=confident)


def make_gate(judge, **overrides):
    config = GateConfig(quiet_start=None, quiet_end=None, **overrides)
    return Gate(config, judge, State())


class GateTests(unittest.TestCase):
    def test_stale_is_silenced_without_judging(self):
        def exploding_judge(c):
            raise AssertionError("stale candidates must not be judged")
        gate = make_gate(exploding_judge)
        old = candidate("old", minutes_ago=300, ttl=60)
        self.assertEqual(gate.decide(old, NOW).decision, SILENCE)

    def test_duplicate_is_silenced(self):
        gate = make_gate(fixed_judge(9))
        first = candidate("a")
        second = candidate("b")  # same content, different id
        self.assertEqual(gate.decide(first, NOW).decision, INTERRUPT)
        self.assertEqual(gate.decide(second, NOW).decision, SILENCE)

    def test_budget_downgrades_overflow_to_digest(self):
        gate = make_gate(fixed_judge(9), daily_interrupt_budget=1)
        self.assertEqual(gate.decide(candidate("a", "One x"), NOW).decision,
                         INTERRUPT)
        self.assertEqual(gate.decide(candidate("b", "Two y"), NOW).decision,
                         DIGEST)

    def test_quiet_hours_hold_unless_critical(self):
        config = GateConfig(quiet_start=23, quiet_end=7)
        gate = Gate(config, fixed_judge(8), State())
        late = datetime(2026, 10, 21, 23, 30, tzinfo=TZ)
        self.assertEqual(gate.decide(candidate("a", "Late x"), late)
                         .decision, DIGEST)
        gate2 = Gate(config, fixed_judge(9.5), State())
        self.assertEqual(gate2.decide(candidate("b", "Critical y"), late)
                         .decision, INTERRUPT)

    def test_low_score_is_silenced(self):
        gate = make_gate(fixed_judge(1))
        self.assertEqual(gate.decide(candidate("a"), NOW).decision, SILENCE)

    def test_unsure_is_never_silenced(self):
        gate = make_gate(fixed_judge(1, confident=False))
        decision = gate.decide(candidate("a"), NOW)
        self.assertEqual(decision.decision, DIGEST)

    def test_mid_score_goes_to_digest(self):
        gate = make_gate(fixed_judge(5.5))
        self.assertEqual(gate.decide(candidate("a"), NOW).decision, DIGEST)


if __name__ == "__main__":
    unittest.main()
