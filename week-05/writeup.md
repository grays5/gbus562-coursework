# Week 5 Writeup: Copperline Supplier-Response Team

> **Status (2026-11-22):** the code and every offline check are complete. **No email has been run against the Anthropic API yet**, because no API key was available in the environment where this was finished. Every section below that depends on model output says so. No model output in this writeup is invented. The numbers quoted come from the `check_coverage` tool, run directly in Python (see `week-05/checks/offline-checks.txt`).

## What I Built

A team of Claude Sonnet 5 (`claude-sonnet-5`) specialists that responds to supplier emails for Copperline Coffee Machines. It has four parts:

- **`supply_mcp_server.py`** is an MCP server (stdio) that exposes Copperline's supply data as the three tools named in `prompts/analyst.txt`:
  - `get_part` returns stock on hand, the supplier and the scheduled deliveries.
  - `get_orders_for_part` returns the open orders that use the part, with parts needed per order from the bill of materials.
  - `check_coverage` works out which orders ship late under the current delivery schedule or a changed one. The numbers in the brief come from this tool, so the model never does the arithmetic itself.
- **`specialists.py`** holds the four specialists. Each one uses its prompt file from `copperline-coffee/prompts/`, unchanged, as its system prompt:
  - The **supply analyst** runs a tool loop over the MCP server and finishes with the JSON brief.
  - The **supplier writer** drafts the reply to the supplier, or `NO REPLY NEEDED`.
  - The **customer writer** drafts one notice per order at risk. It sees only that order's facts.
  - The **reviewer** answers APPROVE or REVISE. On REVISE, its notes go back to the writer, for up to 2 revisions.
- **`pipeline.py`** runs the specialists in a fixed order: analyst, supplier reply, customer notices, each draft followed by the reviewer.
- **`orchestrator.py`** uses the orchestrator prompt to choose which specialists to call, through the tools `run_supply_analyst`, `draft_supplier_reply`, `draft_customer_notice` and `finish`.

Both programs print the analyst's tool calls, the full analyst brief, each review round, each `FINAL DRAFT` and `Needs human review: true/false` with reasons. Both support `--org`, `--email` and `--save`. Nothing can be sent.

Safeguards in code, not left to the model:
- **Brief check.** Every order and number in the brief must match a real `check_coverage` result. If one doesn't, no customer notice is drafted for that order and the run is flagged for review.
- **Customer writer's view.** The customer writer is given only order number, customer, product, quantity, and planned and expected ship day. It never sees the supplier's name, the late penalty or other customers.
- **Human review triggers.** Review is forced when:
  - there is a late-penalty order at risk;
  - there is a decision for a person or a question from the supplier;
  - the reviewer didn't approve;
  - the orchestrator didn't call `finish`.

`check_offline.py` tests all of this without the API (37 of 37 checks pass; output in `checks/offline-checks.txt`).

## Why This Approach

**Pipeline vs orchestrator.** Every supplier email needs the same first step, the analysis. The pipeline is predictable, so it's easy to audit and costs a known number of calls. But it always calls the supplier writer, even for email 04, which needs no action. The orchestrator can skip specialists an email doesn't need, as `orchestrator.txt` asks ("An email that needs no action may need none"). That saves calls, but adds a model decision that can go wrong, such as skipping a customer notice that was needed. That is why both versions share the same code-level checks and human-review triggers.

**Why the analyst uses a tool for coverage.** The coverage rules involve ordering by ship-by day, multiplying by bill-of-materials quantities and summing deliveries over time. That's fixed arithmetic, so it belongs in code (`check_coverage`), not in the model. The analyst's job is to read the email, turn it into a delivery schedule in days from today, and call the tool once per option.

**Why a separate reviewer.** The writers see the facts. The reviewer, which "did not write it", checks the draft against the six rules: numbers in the facts, no unsupported promises, no customer names to suppliers, no supplier names or costs to customers, no accepting options, and tone.

## Expected Results From the Coverage Tool (verified offline)

These come from `check_coverage` itself, called with each email's new schedule. They are what the analyst's brief should contain on a live run. They are **not** model output.

| Email | Schedule checked | Orders at risk (units_short parts, ship day, ready day, penalty) |
|---|---|---|
| 01 Danforth PU-20 pumps | 40 on day 4, 160 on day 19 | O-2203 (10, 12, 19, yes); O-2204 (20, 15, 19, no); O-2205 (25, 17, 19, yes) |
| 02 Marlow BL-12, Option A | 80 on day 7, 120 on day 21 | O-2205 (5, 17, 21, yes) |
| 02 Marlow BL-12, Option B | 200 on day 13 | O-2203 (40, 12, 13, yes) |
| 03 Ashgrove BR-64 burrs | 120 on day 13 | none |
| 04 Pelham SW-3 wands | unchanged (day 11) | none |

What a correct live run should show:
- **Email 01:** the supplier asked for customer names and quantities. The supplier reply must refuse to give them (supplier-writer rule, reviewer rule 3).
- **Email 02:** a person must choose between the options before Marlow's three-business-day deadline, or Marlow will default to Option B. The reply must not accept either option. The pipeline drafts no customer notices until the choice is made.
- **Emails 03 and 04:** no orders are at risk, so no customer notices should be drafted.

## Example Run

**Not completed.** This section should contain one complete, unchanged saved run, such as `week-05/runs/copperline-coffee/01-danforth-pump-delay-pipeline.txt`. That file doesn't exist yet because no API run has been made. I've left this section empty on purpose rather than write a made-up run.

## Reflection

**Not completed: these answers need the live runs.** What can be said now:

- The code checks show the safeguards work with canned replies. A wrong number planted in a brief was caught: no notice was drafted for that order, and the run was flagged for review. Whether the real model's briefs pass these checks is still unknown.
- Still to answer from the live runs:
  - Did the analyst convert "15 days later" and "two weeks after that" into days 19 and 21 correctly?
  - Did the supplier reply for email 01 refuse the request for customer names?
  - Did the orchestrator skip the writers for email 04?
  - How many review rounds did each draft take?
- Assumptions still to check against the lecture are listed in `week-05/STATUS.md`, such as orders being served earliest ship-by day first, and `units_short` counting parts rather than machines.
