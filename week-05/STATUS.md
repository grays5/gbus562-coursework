# Week 5 Part B Status (2026-11-22)

## Submission summary

| Item | State |
|---|---|
| Code (`supply_mcp_server.py`, `specialists.py`, `pipeline.py`, `orchestrator.py`) | Done |
| Offline code checks (`check_offline.py`, output in `checks/offline-checks.txt`) | Done: 37 of 37 pass, no API calls |
| Writeup (`writeup.md`) | Done except the Example Run and the model-dependent Reflection answers |
| README Week 5 entry | Updated |
| Live API runs for the four Copperline emails (`runs/copperline-coffee/`) | **NOT DONE**: no Anthropic API key was available |
| Brookfield Bikes data and lecture files | **NOT AVAILABLE** in the repository |

## Still missing

1. Live runs. Nothing in `runs/` exists yet, and no results were made up. To produce them:

   ```
   python week-05/pipeline.py --org copperline-coffee --save
   python week-05/orchestrator.py --org copperline-coffee --save
   ```

   That writes 8 files: `runs/copperline-coffee/<email>-pipeline.txt` and `<email>-orchestrator.txt`.
2. `writeup.md` Example Run: paste one complete saved run there.
3. `writeup.md` Reflection: answer the open questions there from the saved runs.
4. Brookfield Bikes: add the lecture data to `brookfield-bikes/` (the default `--org`), then check the assumptions below.

The Brookfield lecture files were not available, so the code follows the Copperline assignment files: the five prompts, the five CSVs and the four supplier emails. Everything below marked **Assumption** is my reading of those files. Check each one against the lecture when you have it.

## Done

- `copperline-coffee/`: extracted from `copperline-coffee.zip` with no changes (5 CSVs, `prompts/`, `supplier-emails/`).
- `brookfield-bikes/`: empty placeholder folders only. No Brookfield data was made up. `--org` defaults to `brookfield-bikes`, so a run without `--org` stops and lists the files it still needs.
- `supply_mcp_server.py`: MCP server (stdio) with the three tools named in `prompts/analyst.txt`: `get_part`, `get_orders_for_part` and `check_coverage`.
- `specialists.py`: the analyst (a tool loop over the MCP server), the supplier writer, the customer writer and the reviewer. Each uses its prompt file unchanged as the system prompt.
- `pipeline.py`: fixed order. Analyst, then supplier reply, then customer notices, each followed by the reviewer.
- `orchestrator.py`: the orchestrator prompt chooses which specialists to call, using the tools `run_supply_analyst`, `draft_supplier_reply`, `draft_customer_notice` and `finish`.
- Both programs use `claude-sonnet-5` and have `--org`, `--email` and `--save`. They print the analyst's tool calls, the full analyst brief, each review round, each `FINAL DRAFT`, and `Needs human review: true/false` with its reasons.

## Offline checks (verified, no API calls)

| Check | Result |
|---|---|
| Column mapping for Copperline | All 5 CSVs mapped |
| Renamed headers (`Qty On Hand`, `ETA Days`, `Order #`...), `bom.csv`, and `columns.json` | Mapped correctly. A bad `columns.json` entry gives a clear error |
| `check_coverage`, email 01 (40 pumps on day 4, 160 on day 19) | At risk: O-2203 (10 short, ready day 19, ship day 12, penalty), O-2204 (20 short, ready 19, ship 15), O-2205 (25 short, ready 19, ship 17, penalty) |
| Email 02 Option A (80 boilers on day 7, 120 on day 21) | At risk: O-2205 (5 short, ready 21, ship 17, penalty) |
| Email 02 Option B (200 boilers on day 13) | At risk: O-2203 (40 short, ready 13, ship 12, penalty) |
| Email 03 (120 burr sets on day 13) | No orders at risk |
| Current schedule, all four parts | No orders at risk |
| Both programs with a scripted stand-in for the API | Ran end to end. A wrong number planted in the brief was caught: no notice was drafted for that order, and the run was flagged for review |
| `--org brookfield-bikes` (the default) | Stops and lists the missing files |
| No API key | Stops with a clear message |

All of these are repeated by `python week-05/check_offline.py --save` (37 checks). No email has been run against the real API yet.

## Assumptions to verify against the lecture

### `check_coverage`
1. Parts an order needs = units × `per_unit` from `bill-of-materials.csv`. For example, Cafe Duo needs 2 pumps per machine.
2. Supply on day d = stock on hand + every inbound delivery arriving on or before day d. All days count from today, which is day 0.
3. Orders are served earliest ship-by day first (ties broken by order_id). Late-penalty orders get no priority.
4. `ready_day` is the first day supply covers that order and every earlier one. There is no assembly or shipping lead time.
5. An order is at risk if `ready_day` > ship-by day, or if no delivery ever covers it (`ready_day` is then `null`). `units_short` counts **parts** short on the ship-by day, not machines.
6. Only the part in the email is checked. An order that also uses another part (Cafe Duo uses PU-20, BL-12 and SW-3) is not checked for those.
7. `new_deliveries` replaces only the PO named in `replaces_po`. If no PO is named, it replaces every scheduled delivery for the part.

### Team behaviour
8. The reviewer allows up to 2 revisions (3 reviews in total). If the last verdict isn't APPROVE, the draft is flagged for review.
9. A supplier reply of `NO REPLY NEEDED` is not sent to the reviewer.
10. Customer notices are drafted only for orders whose brief numbers exactly match a `check_coverage` result. In pipeline mode, no notices are drafted while the supplier is waiting for Copperline to choose an option (email 02).
11. A customer writer sees only: order number, customer, product, quantity, planned and expected ship day, and days late. It never sees the supplier name or the late penalty.
12. When asking for a rewrite, the code adds one instruction: "Rewrite the draft so it fixes every point in the reviewer notes. Reply with the email text only." This is the only instruction text not taken from the prompt files.

### Output and human review
13. The exact lecture wording for the FINAL DRAFT and human-review lines is unknown. The format is the one in `pipeline.py` `format_run()`.
14. `Needs human review: true` whenever any of these hold:
    - the brief has a problem, or its numbers don't match the tool output;
    - the brief lists `decisions_for_a_person` or `supplier_questions`;
    - an at-risk order has a late penalty;
    - a draft wasn't approved;
    - the orchestrator reports a decision is needed, or stops without calling `finish`.

    Nothing is ever sent, either way.
15. `--save` writes `week-05/runs/<org>/<email>-<mode>.txt`. Without it, nothing is written to disk.
