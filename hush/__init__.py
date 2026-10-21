"""Hush — an attention firewall for agents and feeds.

Every candidate notification must pass a gate before it may interrupt
a human: a freshness check, a local-model judgment, and a daily
interruption budget. The gate has three answers — interrupt, hold for
the digest, or stay silent — and it writes down its reason every time.
"""

__version__ = "0.1.0"
