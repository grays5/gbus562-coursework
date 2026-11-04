# Week 3 Status: Live API Tests Not Yet Run

## Verified on 2026-11-04 (no API call needed)

- Installed `week-03/requirements.txt` in a virtual environment: chromadb 1.5.9, anthropic 2.4.0, python-dotenv 1.2.4.
- Chroma indexing works: the six Larkfield documents in `week-03/larkfield-docs` were indexed into 39 chunks.
- Retrieval works: the test question "What is the overdraft fee?" returned these top 3 chunks:
  1. consumer-fee-schedule.html (similarity 0.6701)
  2. consumer-fee-schedule-v7.html (similarity 0.6393)
  3. consumer-fee-schedule-v7.html (similarity 0.4339)
- `ask.py` fails cleanly when no key is set: it prints "could not get an answer from Claude" with the SDK's authentication error, instead of crashing or using another model.

## Blocked: Live Anthropic API Calls

`ANTHROPIC_API_KEY` was not available in the cloud environment where this work was done, so **no Claude answers have been generated and no answer output is included**. No results were invented.

To finish, run each assignment question from the repository root with the key set in the environment or in a `.env` file. Both `.env` and `.venv/` are excluded from Git.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r week-03/requirements.txt
python week-03/ask.py --docs week-03/larkfield-docs --save week-03/runs/q1.txt "<Question 1 text>"
```

Repeat the last command for each question, then commit the files in `week-03/runs/`.
