# Week 4 Status (2026-11-11)

## Done

- `hr_mcp_server.py`: MCP server (stdio) with three tools: `search_policy`, `list_policies` and `get_leave_balance`. These names match `system_prompt.txt`.
  - Each organization gets its own Chroma database in `week-04/chroma/<org>/`. Git ignores it. It is rebuilt when the policy files change.
  - Policies are read from `hr-docs/`. A folder named `policies/` also works.
  - The email column and the balance columns are found from the `employees.csv` headers.
  - `get_leave_balance` only answers for the sender of the current email. Any other address gets `ACCESS DENIED`.
- `agent.py`: uses `claude-sonnet-5` and has `--org` (default `hartwell-hr`), `--email` and `--save`. The model finishes by calling `save_reply` with the reply and `needs_human_review`.
  - For each email it prints the sender and subject, the tool steps, the DRAFT, the reply and `Needs human review: true/false`.
  - The code always sets review to true if the sender isn't in `employees.csv`, if a balance lookup is denied, or if the email looks like it contains instructions to the agent.
- `ridgeline-hotels/`: extracted from `ridgeline-hotels.zip` with no changes. The files were checked byte for byte against the archive.

## Ridgeline Hotels: offline checks (verified, no API calls)

| Check | Result |
|---|---|
| Folder structure | `hr-docs/` (5 HTML policies), `employees.csv` (12 people), `sample-emails/` (7 `.eml`), `system_prompt.txt` |
| CSV columns detected | email: `Email Address`. Balances: `PTO Days Remaining`, `Sick Days Remaining` |
| Chroma database | `chroma/ridgeline-hotels/`, 6 chunks from 5 files |
| All 7 emails parsed | sender and subject read correctly for each one |
| `07-logan-seasonal.eml` | Logan Brooks is not in `employees.csv`, so review is forced to true |
| `05-nicole-room-rate.eml` | the "ADMIN OVERRIDE" text is detected, so review is forced to true |
| Another employee's balance (for example Tyler asking about Jenna) | `ACCESS DENIED` from the server |
| Retrieval | PTO, bereavement, room rate, harassment and seasonal questions each returned the matching policy file first |

## Not done: an API key is needed

- `ANTHROPIC_API_KEY` is not available in this environment, so none of the seven emails has been run against Claude and `runs/` is empty.
- `hartwell-hr/` still has no files (the lecture's Hartwell data), so the default `--org` stops and lists what is missing.

To run all seven Ridgeline emails and save one file per email to `runs/ridgeline-hotels/`:

```
python week-04/agent.py --org ridgeline-hotels --save
```
