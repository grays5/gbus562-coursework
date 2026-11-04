# Week 3 Status (2026-11-04)

See `writeup.md` for full details and verified results.

## Done (verified)

- Requirements installed in a virtual environment: chromadb 1.5.9, anthropic 2.4.0, python-dotenv 1.2.4.
- Document issue fixed: the superseded `consumer-fee-schedule-v7.html` ($35 overdraft fee) was moved from `larkfield-docs/` to `archived-docs/`. Only Version 8 ($29) is indexed now.
- Chroma database rebuilt: 5 files, 30 chunks (was 6 files, 39 chunks). Overdraft questions now retrieve only Version 8 chunks.
- `ask.py` stops with a clear authentication error when no key is set. It does not crash or substitute another model.

## Not done: needs a working ANTHROPIC_API_KEY

- The seven required runs (Q1 before, Q1 after, Q2 to Q6) have no Claude answers. `week-03/runs/q1-before.txt`, `q1-after.txt` and `q2.txt` to `q6.txt` don't exist yet. The retrieval results for all seven are verified and recorded in `writeup.md`.
- The Example Run in `writeup.md` is empty until one saved run exists.
