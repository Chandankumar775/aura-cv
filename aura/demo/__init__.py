"""Demo world: a hard-coded, clearly labelled illustrative scenario that makes the full
AURA-CV workflow runnable end to end before the real detectors (M1-M6) exist.

Every value produced by this package is ILLUSTRATIVE, not measured. The API marks all
responses with ``demo: true`` and the UI shows a permanent DEMO DATA marker (CLAUDE.md
A3 rule 2: placeholder content must be visibly labelled as placeholder).

What is *real* even in demo mode: the check scheduler and its UNAVAILABLE fallbacks,
the disposition policy, finding schema validation, Ed25519 signing of inference
records and reports, record verification, and the hash-chained signed audit log.
"""

DEMO_NOTICE = "Demo scenario - illustrative values, not measured results."
