"""aidbg toolbox — the read-only primitives an LLM agent calls (the "eyes").

This package is Layer 1: it gives an agent precise, queryable access to huge
waveforms / logs / the source repo so it never has to ingest them wholesale.
It holds NO debug judgement — the agent (driven by a profile + skill playbooks)
does the reasoning. Nothing here ever edits a file.
"""
