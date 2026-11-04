**GBUS 562 Week 3: Python RAG Tool with Chroma and the Anthropic API**

> **Status at submission (2026-11-04):** The RAG tool, document fix and Chroma database rebuild are complete and verified. **No live Claude answers were generated**, because `ANTHROPIC_API_KEY` was not available in the environment where this work was done. Every result below comes from a run I actually made; nothing was invented. The API tests that could not run are listed in [API Tests Not Run](#api-tests-not-run).

## What I Built

`week-03/ask.py` is a command-line RAG (retrieval-augmented generation) tool:

1. It reads every `.html`, `.htm`, `.txt` or `.md` file in a documents folder (`--docs`, default `week-03/copperline-docs`).
2. It splits each HTML document into one chunk per `<h2>` section. Each chunk starts with the document title and its version line (for example "Version 8 (current). Replaces Version 7.").
3. It stores the chunks in a local Chroma vector database (`week-03/chroma/`, cosine similarity). Each documents folder gets its own database. The database is rebuilt automatically when any file in the folder is added, removed or edited, or on demand with `--rebuild`.
4. It retrieves the top 5 chunks for the question (`--k` to change) and prints each with its rank, similarity score and source file.
5. It sends those chunks to Claude (`claude-sonnet-5`) with a system prompt requiring answers to use only the excerpts, cite the source of every fact, point out conflicting versions, and say so when the documents don't answer the question.
6. `--save FILE` writes the complete run (question, files indexed, retrieved chunks, model requested, model that answered, answer) to a UTF-8 text file.

If the model is unavailable or the API call fails, the tool prints a clear error and stops. It never substitutes a different model.

Environment used (verified): Python virtual environment with chromadb 1.5.9, anthropic 2.4.0 and python-dotenv 1.2.4, installed from `week-03/requirements.txt`. Chroma used its default embedding model, all-MiniLM-L6-v2.

## The Document Issue and the Fix

**Problem.** The `larkfield-docs` folder had two versions of the Consumer Fee Schedule:

| File | Version line in the document | Overdraft / returned item fee | Max fees per day | $10 de minimis rule |
|---|---|---|---|---|
| `consumer-fee-schedule.html` | "Version 8 (current). Replaces Version 7." | $29 per item | 3 | Yes, no fee if overdrawn by $10 or less |
| `consumer-fee-schedule-v7.html` | "Version 7 (current). Replaces Version 6." | $35 per item | 4 | Not mentioned |

Both files call themselves "current", but Version 8 explicitly replaces Version 7. Because the two are almost identical, retrieval returned chunks from both, so Claude would be given conflicting fees ($29 and $35) for the same question.

**Before the fix (verified run, 6 files, 39 chunks):**

```
Q: What is the overdraft fee?
  1. 0.6701 consumer-fee-schedule.html    | Section: Overdraft and returned item fees
  2. 0.6393 consumer-fee-schedule-v7.html | Section: Overdraft and returned item fees
  3. 0.4339 consumer-fee-schedule-v7.html | Section: Checking account monthly fees
  4. 0.4332 consumer-fee-schedule.html    | Section: Checking account monthly fees
  5. 0.4331 consumer-fee-schedule-v7.html | Section: Stop payments

Q: How many overdraft fees can be charged in one day?
  1. 0.6473 consumer-fee-schedule.html    | Section: Overdraft and returned item fees
  2. 0.5886 consumer-fee-schedule-v7.html | Section: Overdraft and returned item fees
  3. 0.4597 consumer-fee-schedule.html    | Section: Checking account monthly fees
  4. 0.4595 consumer-fee-schedule-v7.html | Section: Checking account monthly fees
  5. 0.4421 consumer-fee-schedule-v7.html | Section: Dormant accounts
```

Three of the top five chunks for each question came from the outdated Version 7.

**Fix.** I moved the superseded Version 7 file out of the indexed folder into `week-03/archived-docs/consumer-fee-schedule-v7.html`. It's kept for the record but no longer searched. I didn't edit any document's content. Removing the file changed the folder fingerprint, so `ask.py` deleted and rebuilt the Chroma database.

**After the fix (verified run, 5 files, 30 chunks, database `week-03/chroma/larkfield-docs-d35d41e3`, built 2026-11-04T16:14:49Z):**

```
Q: What is the overdraft fee?
  1. 0.6701 consumer-fee-schedule.html | Section: Overdraft and returned item fees
  2. 0.4332 consumer-fee-schedule.html | Section: Checking account monthly fees
  3. 0.4309 consumer-fee-schedule.html | Section: Stop payments
  4. 0.4211 fee-refund-guide.html      | Section: Refunds that need a branch manager
  5. 0.4161 consumer-fee-schedule.html | Section: Dormant accounts

Q: How many overdraft fees can be charged in one day?
  1. 0.6473 consumer-fee-schedule.html | Section: Overdraft and returned item fees
  2. 0.4597 consumer-fee-schedule.html | Section: Checking account monthly fees
  3. 0.4418 consumer-fee-schedule.html | Section: Dormant accounts
  4. 0.4326 consumer-fee-schedule.html | Section: Stop payments
  5. 0.4322 consumer-fee-schedule.html | Section: Statements and account research
```

Now only the current Version 8 fee schedule is retrieved. Its top chunk states the $29 fee, the limit of three fees per day and the $10 de minimis rule. The top similarity score didn't change (0.6701 and 0.6473), which shows the right chunk was always found first. The fix removes the conflicting outdated chunks that were competing with it.

**Lesson.** A RAG system only knows what's in its document folder. Retrieval can't tell which of two near-identical documents is current, especially when both say "current". So the knowledge base has to be kept clean: superseded versions should be removed or archived, and the database rebuilt.

## API Tests Not Run

`ANTHROPIC_API_KEY` was not set in the environment where this work was done. I confirmed Python could not see it. As a result, **these steps could not run and have no results**:

| Test | Status |
|---|---|
| Claude answer to "What is the overdraft fee?" after the fix (should cite $29 from Version 8) | **Not run.** No answer generated. |
| Any Claude answer for the Larkfield questions, with `--save` output in `week-03/runs/` | **Not run.** `week-03/runs/` does not exist yet. |
| Claude answers for the Copperline Manufacturing documents | **Not run.** `week-03/copperline-docs/` is still empty (only `.gitkeep`), so there are no Copperline documents to index. |
| Confirming `claude-sonnet-5` is available to my API key ("Model that answered" line) | **Not run.** |

What I did verify without a key: running `python week-03/ask.py --docs week-03/larkfield-docs "What is the overdraft fee?"` builds or loads the database, retrieves chunks and then stops with a clear message instead of crashing or switching models:

```
Error: could not get an answer from Claude: "Could not resolve authentication method. Expected one of api_key, auth_token, or credentials to be set. ..."
```

To finish, run these from the repository root with the key set in the environment or in a `.env` file (`.env` is excluded from Git):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r week-03/requirements.txt
python week-03/ask.py --docs week-03/larkfield-docs --save week-03/runs/larkfield-overdraft.txt "What is the overdraft fee?"
```

Then add the saved runs and their answers to this writeup.

## Files

- `week-03/ask.py`: the RAG tool
- `week-03/requirements.txt`: Python dependencies
- `week-03/larkfield-docs/`: the five current Larkfield Credit Union documents that get indexed
- `week-03/archived-docs/consumer-fee-schedule-v7.html`: the superseded fee schedule, removed from the index
- `week-03/copperline-docs/`: placeholder for the Copperline Manufacturing documents (empty)
- `week-03/STATUS.md`: short status summary

Not committed (excluded by `.gitignore`): the Chroma database (`week-03/chroma/`), the virtual environment (`.venv/`) and any `.env` file or API key.
