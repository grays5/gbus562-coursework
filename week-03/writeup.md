**GBUS 562 Week 3: Python RAG Tool with Chroma and the Anthropic API**

> **Status at submission (2026-11-04):** The RAG tool, document fix and Chroma database rebuild are complete and verified. **No live Claude answers were generated**, because `ANTHROPIC_API_KEY` was not available in the environment where this work was done. Every result below comes from a run I actually made; nothing was invented. The status of each required question is in [Test Questions](#test-questions).

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

## Test Questions

These are the seven required runs. **None of them has a Claude answer**, because `ANTHROPIC_API_KEY` was not available. I checked again on 2026-11-04, and Python reported it as missing. The saved output files (`week-03/runs/q1-before.txt`, `q1-after.txt` and `q2.txt` to `q6.txt`) **have not been created**, because each should be a complete `ask.py` run including Claude's answer.

What I could verify without a key is the retrieval step: which chunks Chroma returns for each exact question. These are real results from the same index and search that `ask.py` uses (top 5, cosine similarity). They show what Claude *would* be given. They are not answers.

| Run | Question | Collection | Claude answer | Saved file |
|---|---|---|---|---|
| Q1 before | How much is the fee when a member overdraws their checking account? | Version 7 + Version 8 (6 files, 39 chunks) | **Not run** | Not created |
| Q1 after | How much is the fee when a member overdraws their checking account? | Corrected (5 files, 30 chunks) | **Not run** | Not created |
| Q2 | A member needs a replacement debit card quickly. What does rush delivery cost? | Corrected | **Not run** | Not created |
| Q3 | A member lost their wallet and called us the same day. How much of any fraudulent spending on their debit card could they be on the hook for? | Corrected | **Not run** | Not created |
| Q4 | Can I refund the outgoing international wire transfer fee for a member without approval from a manager? | Corrected | **Not run** | Not created |
| Q5 | A member deposited a $2,000 paycheck at a branch today. How much of it can they use on the next business day? | Corrected | **Not run** | Not created |
| Q6 | What is the current rate on a 30-year fixed mortgage? | Corrected | **Not run** | Not created |

For Q1 before, I reproduced the issue without touching the corrected collection. I copied the five current documents plus the archived Version 7 file into a temporary folder outside the repository, indexed that folder into its own Chroma database, and deleted the temporary database afterward. `week-03/larkfield-docs/` and its database were not changed.

### Retrieval results (verified, 2026-11-04)

```
Q1 BEFORE (Version 7 + Version 8, 39 chunks)
  1. 0.6886 consumer-fee-schedule.html     | Section: Overdraft and returned item fees
  2. 0.6554 consumer-fee-schedule-v7.html  | Section: Overdraft and returned item fees
  3. 0.5069 consumer-fee-schedule.html     | Section: Dormant accounts
  4. 0.5056 consumer-fee-schedule-v7.html  | Section: Dormant accounts
  5. 0.4899 consumer-fee-schedule.html     | Section: Checking account monthly fees

Q1 AFTER (corrected, 30 chunks)
  1. 0.6886 consumer-fee-schedule.html     | Section: Overdraft and returned item fees
  2. 0.5069 consumer-fee-schedule.html     | Section: Dormant accounts
  3. 0.4899 consumer-fee-schedule.html     | Section: Checking account monthly fees
  4. 0.4896 fee-refund-guide.html          | Section: Refunds that need a branch manager
  5. 0.4887 consumer-fee-schedule.html     | Section: Statements and account research

Q2
  1. 0.5631 consumer-fee-schedule.html     | Section: ATM and debit card fees
  2. 0.5415 card-dispute-procedure.html    | Section: How much the member may have to pay
  3. 0.4720 card-dispute-procedure.html    | Section: When a member reports a transaction they did not make
  4. 0.4655 consumer-fee-schedule.html     | Section: Overdraft and returned item fees
  5. 0.4478 consumer-fee-schedule.html     | Section: Statements and account research

Q3
  1. 0.6336 card-dispute-procedure.html    | Section: How much the member may have to pay
  2. 0.5019 card-dispute-procedure.html    | Section: When a member reports a transaction they did not make
  3. 0.4473 card-dispute-procedure.html    | Section: Provisional credit
  4. 0.3898 card-dispute-procedure.html    | Section: The dispute form
  5. 0.3859 consumer-fee-schedule.html     | Section: Overdraft and returned item fees

Q4
  1. 0.5341 fee-refund-guide.html          | Section: Refunds that need a branch manager
  2. 0.5096 fee-refund-guide.html          | Section: What a member service representative can approve
  3. 0.4920 fee-refund-guide.html          | Section: Refunds that need the Member Services Director
  4. 0.4881 consumer-fee-schedule.html     | Section: Wire transfers
  5. 0.4558 fee-refund-guide.html          | Section: Recording a refund

Q5
  1. 0.4863 funds-availability-policy.html | Section: Mobile check deposits
  2. 0.4703 funds-availability-policy.html | Section: Check deposits
  3. 0.4180 card-dispute-procedure.html    | Section: How much the member may have to pay
  4. 0.4164 consumer-fee-schedule.html     | Section: Overdraft and returned item fees
  5. 0.4155 funds-availability-policy.html | Section: Longer holds

Q6
  1. 0.2471 consumer-fee-schedule.html     | Section: Stop payments
  2. 0.2345 consumer-fee-schedule.html     | Section: Checking account monthly fees
  3. 0.2311 share-certificates.html        | Section: Dividend rates
  4. 0.2225 consumer-fee-schedule.html     | Section: Statements and account research
  5. 0.2106 consumer-fee-schedule.html     | Section: Wire transfers
```

### What the retrieval shows (observations, not Claude answers)

- **Q1:** Before the fix, the outdated Version 7 overdraft section ($35) ranked second, right behind Version 8 ($29). After the fix, only Version 8 is retrieved.
- **Q2, Q3, Q4:** The top chunks come from the documents that cover each topic: the ATM and debit card fees section, the card dispute procedure, and the fee refund guide plus the wire transfer fee section. Q4 needs facts from two documents (the fee amount and the refund approval rules), and both were retrieved.
- **Q5:** Both check sections were retrieved, but the "Cash, direct deposits, and wire transfers" section was **not** in the top 5. Whether a "paycheck deposited at a branch" counts as a check deposit or a direct deposit matters for the answer. That makes Q5 worth checking closely once Claude's answer is available.
- **Q6:** No document covers mortgages. All similarity scores are low (0.25 or below) and come from unrelated sections. The correct behavior is for Claude to say the documents don't answer the question, but that hasn't been tested.

### How to finish the seven runs

With the key set in the environment or a `.env` file (`.env` is excluded from Git), run from the repository root with the virtual environment active. For Q1 before, put the Version 7 file back temporarily, run it, then move it back so the corrected collection is restored:

```bash
cp week-03/archived-docs/consumer-fee-schedule-v7.html week-03/larkfield-docs/
python week-03/ask.py --docs week-03/larkfield-docs --save week-03/runs/q1-before.txt "How much is the fee when a member overdraws their checking account?"
rm week-03/larkfield-docs/consumer-fee-schedule-v7.html
python week-03/ask.py --docs week-03/larkfield-docs --save week-03/runs/q1-after.txt "How much is the fee when a member overdraws their checking account?"
python week-03/ask.py --docs week-03/larkfield-docs --save week-03/runs/q2.txt "A member needs a replacement debit card quickly. What does rush delivery cost?"
python week-03/ask.py --docs week-03/larkfield-docs --save week-03/runs/q3.txt "A member lost their wallet and called us the same day. How much of any fraudulent spending on their debit card could they be on the hook for?"
python week-03/ask.py --docs week-03/larkfield-docs --save week-03/runs/q4.txt "Can I refund the outgoing international wire transfer fee for a member without approval from a manager?"
python week-03/ask.py --docs week-03/larkfield-docs --save week-03/runs/q5.txt 'A member deposited a $2,000 paycheck at a branch today. How much of it can they use on the next business day?'
python week-03/ask.py --docs week-03/larkfield-docs --save week-03/runs/q6.txt "What is the current rate on a 30-year fixed mortgage?"
```

`ask.py` rebuilds the database automatically whenever the folder's files change, so each run uses the right collection. Q5 is in single quotes so the shell doesn't treat `$2` as a variable.

## Example Run

**No saved run exists yet.** The Example Run must be a complete, unedited `ask.py` output saved with `--save`, and every saved run needs Claude's answer, which requires a working API key. I am not including a made-up or partial run. Once the commands above have been run, paste the full contents of one file from `week-03/runs/` here in a code block, unedited.

The only real `ask.py` output from this environment is the authentication error. It shows the tool stops cleanly instead of crashing or switching models:

```
Error: could not get an answer from Claude: "Could not resolve authentication method. Expected one of api_key, auth_token, or credentials to be set. Or for the `Authorization` header to be explicitly omitted"
```

## Files

- `week-03/ask.py`: the RAG tool
- `week-03/requirements.txt`: Python dependencies
- `week-03/larkfield-docs/`: the five current Larkfield Credit Union documents that get indexed
- `week-03/archived-docs/consumer-fee-schedule-v7.html`: the superseded fee schedule, removed from the index
- `week-03/copperline-docs/`: empty placeholder folder (not used for this assignment; `ask.py`'s default `--docs` points here, so every command above passes `--docs week-03/larkfield-docs`)
- `week-03/runs/`: **not yet created**; it will hold `q1-before.txt`, `q1-after.txt` and `q2.txt` to `q6.txt`
- `week-03/STATUS.md`: short status summary

Not committed (excluded by `.gitignore`): the Chroma database (`week-03/chroma/`), the virtual environment (`.venv/`) and any `.env` file or API key.
