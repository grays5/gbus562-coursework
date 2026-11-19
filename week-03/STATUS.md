# Week 3 Status (2026-11-19)

See `writeup.md` for full details.

## Done

- Document issue fixed: the superseded `consumer-fee-schedule-v7.html` ($35 overdraft fee) was moved from `larkfield-docs/` to `archived-docs/`. Only Version 8 ($29) is indexed now.
- All seven required runs are complete and saved in `week-03/runs/`. Each was run with `claude-sonnet-5-5` (recorded as both the model requested and the model that answered) on 2026-11-19:
  - `q1-before.txt`: Version 7 and Version 8 both indexed (6 files). Version 7 ranked second in retrieval. Claude flagged the conflict ($35 vs $29) and identified Version 8 as current.
  - `q1-after.txt`: corrected folder (5 files). Version 7 no longer retrieved. Answer: $29 per item.
  - `q2.txt` to `q6.txt`: corrected folder (5 files). Q6 (mortgage rate) was correctly declined because no document covers mortgages.
- The Example Run in `writeup.md` contains the complete, unedited `q2.txt` run.
- The Q6 reflection in `writeup.md` describes the actual `q6.txt` answer.
