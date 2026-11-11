# Week 4 Status (2026-11-11)

## Done

- `hr_mcp_server.py`: MCP server (stdio) with three tools: `search_policies`, `list_policies` and `get_leave_balance`.
  - Each organization gets its own Chroma database in `week-04/chroma/<org>/`. Git ignores it. It is rebuilt when the policy files change.
  - The email column and the balance columns are found from the `employees.csv` headers. Balance columns must contain numbers.
  - `get_leave_balance` only answers for the sender of the current email. Any other address gets `ACCESS DENIED`.
- `agent.py`: uses `claude-sonnet-5` and has `--org` (default `hartwell-hr`), `--email` and `--save` (with no file name it saves to `runs/<org>/<email>.txt`).
  - For each email it prints the sender and subject, the tool steps, the DRAFT, the reply and `Needs human review: true/false`.
  - The email body is treated as untrusted data. The code always sets review to true if the sender isn't in the roster, if a balance lookup is denied, or if the email looks like it contains instructions to the agent.
- Tested offline with throwaway mock data that wasn't committed. The column detection, the per-org database, the `ACCESS DENIED` guard, the output format and `--save` all worked. With no API key the agent stops with a clear error.

## Not done: files and a key are needed

Every file in each organization folder is missing. The agent stops and lists what is missing until they are added:

```
week-04/hartwell-hr/
  policies/          the lecture's Hartwell policy documents (.md, .txt, .html or .pdf)
  employees.csv      the lecture's Hartwell employee roster
  sample-emails/     the lecture's Hartwell sample emails (.txt, .eml, .md or .json)
  system_prompt.txt  the lecture's Hartwell system prompt
week-04/<ridgeline-folder>/   the same four items for Ridgeline
```

- No `ANTHROPIC_API_KEY` is set, so no email has been run against Claude and `runs/` is empty.
