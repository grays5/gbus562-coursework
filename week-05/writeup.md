# Week 5 Writeup: Copperline Supplier-Response Team

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

`check_offline.py` provides offline regression checks. All 74 checks passed after the final fixes.

## Why This Approach

Task A: Script is appropriate for fixed calculations and deterministic
coverage checks because arithmetic and order matching should not be
left to a language model. The MCP server supplies verified results.

Task B: Agent is appropriate for analyzing supplier emails because
the analyst must interpret different situations, request supply data,
and decide which coverage checks are needed.

Task C: Pipeline provides a predictable specialist sequence, making
every stage easier to inspect and compare across supplier emails.
The reviewer checks drafts before they are saved.

Task D: Orchestrator allows the model to select specialists based on
the email's needs. This can avoid unnecessary drafting when a
supplier message is informational and no order is at risk.

The pipeline offers consistency, while the orchestrator offers
flexibility. Both use the same supply tools, validation rules,
and safeguards to prevent unsupported customer communications.

## Example Run

The following is the complete, unedited saved Email 1 pipeline run.

```text
SUPPLIER-RESPONSE TEAM RUN
Organization: copperline-coffee
Mode: pipeline
Model requested: claude-sonnet-5
Run time (UTC): 2026-11-22T21:12:32+00:00
============================================================================
Organization: copperline-coffee
Mode: pipeline
Email file: 01-danforth-pump-delay.eml
From: Diane Kessler <d.kessler@danforthpump.example>
Subject: PO-5512 - PU-20 pumps - partial shipment
----------------------------------------------------------------------------
SUPPLY ANALYST
Analyst tool calls:
  1. get_part({"part_id": "PU-20"})
       {
         "part_id": "PU-20",
         "description": "Vibration pump",
         "on_hand": 50,
         "supplier": "Danforth Pump Works",
         "supplier_contact": {
           "supplier": "Danforth Pump Works",
           "contact_name": "Diane Kessler",
           "contact_email": "d.kessler@danforthpump.example",
           "part_id": "PU-20"
         },
         "scheduled_deliveries": [
           {
             "po_number": "PO-5512",
             "part_id": "PU-20",
             "supplier": "Danforth Pump Works",
             "qty": 200,
             "arrives_in_days": 4
           }
         ],
         "used_in": [
           {
             "product": "Cafe Duo",
             "per_unit": 2
           },
           {
             "product": "Cafe One",
             "per_unit": 1
           }
         ]
       }
  2. get_orders_for_part({"part_id": "PU-20"})
       {
         "part_id": "PU-20",
         "orders": [
           {
             "order_id": "O-2201",
             "customer": "Morning Ritual Cafe",
             "contact_email": "orders@morningritualcafe.example",
             "product": "Cafe One",
             "units": 20,
             "ship_by_day": 6,
             "late_penalty": "no",
             "per_unit": 1,
             "parts_needed": 20
           },
           {
             "order_id": "O-2202",
             "customer": "Harbor Hotel Group",
             "contact_email": "purchasing@harborhotelgroup.example",
             "product": "Cafe Duo",
             "units": 15,
             "ship_by_day": 9,
             "late_penalty": "no",
             "per_unit": 2,
             "parts_needed": 30
           },
           {
             "order_id": "O-2203",
             "customer": "Elm State University Dining",
             "contact_email": "dining@elmstate.example",
             "product": "Cafe One",
             "units": 50,
             "ship_by_day": 12,
             "late_penalty": "yes",
             "per_unit": 1,
             "parts_needed": 50
           },
           {
             "order_id": "O-2204",
             "customer": "Kettle & Crumb Bakery",
             "contact_email": "owner@kettleandcrumb.example",
             "product": "Cafe Duo",
             "units": 10,
             "ship_by_day": 15,
             "late_penalty": "no",
             "per_unit": 2,
             "parts_needed": 20
           },
           {
             "order_id": "O-2205",
             "customer": "Tall Pines Coffee House",
             "contact_email": "hello@tallpinescoffee.example",
             "product": "Cafe One",
             "units": 25,
             "ship_by_day": 17,
             "late_penalty": "yes",
             "per_unit": 1,
             "parts_needed": 25
           },
           {
             "order_id": "O-2208",
             "customer": "Northside Roasters",
             "contact_email": "orders@northsideroasters.example",
             "product": "Cafe Duo",
             "units": 12,
             "ship_by_day": 30,
             "late_penalty": "no",
             "per_unit": 2,
             "parts_needed": 24
           },
           {
             "order_id": "O-2210",
             "customer": "Bright Day Coworking",
             "contact_email": "office@brightdaycowork.example",
             "product": "Cafe One",
             "units": 15,
             "ship_by_day": 33,
             "late_penalty": "no",
             "per_unit": 1,
             "parts_needed": 15
           }
         ]
       }
  3. check_coverage({"part_id": "PU-20", "new_deliveries": [{"qty": 40, "arrives_in_days": 4}, {"qty": 160, "arrives_in_days": 19}], "replaces_po": "PO-5512"})
       {
         "part_id": "PU-20",
         "schedule_checked": "PO-5512 replaced by the new deliveries; other scheduled deliveries kept",
         "on_hand": 50,
         "deliveries": [
           {
             "arrives_in_days": 4,
             "qty": 40
           },
           {
             "arrives_in_days": 19,
             "qty": 160
           }
         ],
         "total_supply": 250,
         "total_needed": 184,
         "orders_at_risk": [
           {
             "order_id": "O-2203",
             "customer": "Elm State University Dining",
             "product": "Cafe One",
             "units": 50,
             "parts_needed": 50,
             "ship_day": 12,
             "ready_day": 19,
             "days_late": 7,
             "units_short": 10,
             "late_penalty": "yes",
             "at_risk": true,
             "at_risk_before_change": false
           },
           {
             "order_id": "O-2204",
             "customer": "Kettle & Crumb Bakery",
             "product": "Cafe Duo",
             "units": 10,
             "parts_needed": 20,
             "ship_day": 15,
             "ready_day": 19,
             "days_late": 4,
             "units_short": 20,
             "late_penalty": "no",
             "at_risk": true,
             "at_risk_before_change": false
           },
           {
             "order_id": "O-2205",
             "customer": "Tall Pines Coffee House",
             "product": "Cafe One",
             "units": 25,
             "parts_needed": 25,
             "ship_day": 17,
             "ready_day": 19,
             "days_late": 2,
             "units_short": 25,
             "late_penalty": "yes",
             "at_risk": true,
             "at_risk_before_change": false
           }
         ],
         "orders_covered_on_time": [
           "O-2201",
           "O-2202",
           "O-2208",
           "O-2210"
         ],
         "notes": [
           "units_short and parts_needed count parts, not finished products",
           "ready_day null means no scheduled delivery covers the order",
           "only this part is checked; days are counted from today (day 0)"
         ]
       }

ANALYST BRIEF (full)
{
  "part_id": "PU-20",
  "what_changed": "Of the 200 PU-20 pumps on PO-5512 due in 4 days, only 40 will arrive on day 4 as scheduled, with the remaining 160 arriving 15 days later on day 19.",
  "orders_at_risk": [
    {
      "order_id": "O-2203",
      "customer": "Elm State University Dining",
      "units_short": 10,
      "ship_day": 12,
      "ready_day": 19,
      "late_penalty": "yes"
    },
    {
      "order_id": "O-2204",
      "customer": "Kettle & Crumb Bakery",
      "units_short": 20,
      "ship_day": 15,
      "ready_day": 19,
      "late_penalty": "no"
    },
    {
      "order_id": "O-2205",
      "customer": "Tall Pines Coffee House",
      "units_short": 25,
      "ship_day": 17,
      "ready_day": 19,
      "late_penalty": "yes"
    }
  ],
  "options": [],
  "decisions_for_a_person": [
    "Decide whether to expedite/split stock to protect the two late-penalty orders (O-2203, Elm State University Dining; O-2205, Tall Pines Coffee House) ahead of the non-penalty order (O-2204, Kettle & Crumb Bakery), since all three are now short of parts until day 19.",
    "Decide whether to notify affected customers (Elm State University Dining, Kettle & Crumb Bakery, Tall Pines Coffee House) of potential ship delays."
  ],
  "supplier_questions": [
    "Diane Kessler asked for a list of the customer orders these pumps are for, with each customer's name and quantity."
  ]
}
Brief checks: OK (fields complete; every at-risk number matches a check_coverage result)
----------------------------------------------------------------------------
DRAFT 1 of 4: supplier reply
To: Diane Kessler <d.kessler@danforthpump.example>
About: Re: PO-5512 - PU-20 pumps - partial shipment
Review round 1: APPROVE
  Reviewer:
    APPROVE

FINAL DRAFT (not sent - saved for a person to check)

Subject: RE: PO-5512 - PU-20 pumps - partial shipment

Hello Diane,

Thank you for the update. To confirm our understanding: of the 200 PU-20 pumps on PO-5512 due in 4 days, 40 will arrive on schedule, with the remaining 160 arriving 15 days later on day 19.

This shortfall affects 55 units across our downstream orders and will push delivery on those orders out to day 19, which is a delay of several days against their original ship dates.

We're not able to share customer names or order details.

If there is any way to expedite a portion of the 160 units sooner than day 19 — even a partial early shipment — that would help us reduce the impact. Please let us know what's possible.

Purchasing, Copperline Coffee Machines

Reviewer verdict: APPROVE
Needs human review: false
----------------------------------------------------------------------------
DRAFT 2 of 4: customer notice
To: Elm State University Dining <dining@elmstate.example>
About: Order O-2203
Review round 1: APPROVE
  Reviewer:
    APPROVE

FINAL DRAFT (not sent - saved for a person to check)

Subject: Update on Order O-2203

Dear Elm State University Dining,

We're writing about Order O-2203 for 50 Cafe One units. We're sorry for the inconvenience, but this order is now expected to ship 7 days later than planned, due to a delay in a part from one of our suppliers.

We understand timing matters for your operations and appreciate your patience while we work to get your order out as soon as possible.

If you have any questions in the meantime, please don't hesitate to reach out.

Thank you for your understanding.

Customer Service, Copperline Coffee Machines

Reviewer verdict: APPROVE
Needs human review: true
Reason: Order O-2203 has a late penalty
----------------------------------------------------------------------------
DRAFT 3 of 4: customer notice
To: Kettle & Crumb Bakery <owner@kettleandcrumb.example>
About: Order O-2204
Review round 1: APPROVE
  Reviewer:
    APPROVE

FINAL DRAFT (not sent - saved for a person to check)

Subject: Update on Your Order O-2204

Dear Kettle & Crumb Bakery,

We're writing with an update on order O-2204 for 10 Cafe Duo units. The order is now expected to ship 4 days later than originally planned.

We apologize for this delay. It is due to a delay in a part from one of our suppliers.

We understand timing matters for your business and appreciate your patience. If you have any questions about your order, please don't hesitate to reach out.

Customer Service, Copperline Coffee Machines

Reviewer verdict: APPROVE
Needs human review: false
----------------------------------------------------------------------------
DRAFT 4 of 4: customer notice
To: Tall Pines Coffee House <hello@tallpinescoffee.example>
About: Order O-2205
Review round 1: APPROVE
  Reviewer:
    APPROVE

FINAL DRAFT (not sent - saved for a person to check)

Subject: Update on Your Order O-2205

Dear Tall Pines Coffee House,

We're writing to update you on order O-2205 for 25 units of the Cafe One. The order is now expected to ship 2 days later than originally planned.

We apologize for this delay. It was caused by a delay in a part from one of our suppliers.

We appreciate your patience and understanding, and we'll keep you informed if anything further changes with your order.

Customer Service, Copperline Coffee Machines

Reviewer verdict: APPROVE
Needs human review: true
Reason: Order O-2205 has a late penalty
----------------------------------------------------------------------------
HUMAN REVIEW
Needs human review: true
Reasons:
  - decision for a person: Decide whether to expedite/split stock to protect the two late-penalty orders (O-2203, Elm State University Dining; O-2205, Tall Pines Coffee House) ahead of the non-penalty order (O-2204, Kettle & Crumb Bakery), since all three are now short of parts until day 19.
  - decision for a person: Decide whether to notify affected customers (Elm State University Dining, Kettle & Crumb Bakery, Tall Pines Coffee House) of potential ship delays.
  - supplier asked: Diane Kessler asked for a list of the customer orders these pumps are for, with each customer's name and quantity.
  - order O-2203 at risk has a late penalty
  - order O-2205 at risk has a late penalty
  - customer draft (Order O-2203): Order O-2203 has a late penalty
  - customer draft (Order O-2205): Order O-2205 has a late penalty
Nothing was sent. Every draft above is saved for a person to check.
Model requested: claude-sonnet-5 | served: claude-sonnet-5 | API calls: 11 | tokens in/out: 14875/3894
```

## Reflection

Email 1 reading: Matches the supplier's statement that the
remaining 160 pumps arrive 15 days later. The saved run describes
40 pumps on day 4 and 160 on day 19. The analyst used the changed
schedule to identify affected orders and their expected shipping days.

Email 1 customer names: No customer
names were shared in the supplier reply. The supplier requested
customer order details, but these should remain internal. The
customer notices are separate drafts intended for their recipients.

Email 4 orchestrator: run_supply_analyst then finish.
The saved run shows these specialist actions in this order.
Because the maintenance closure did not affect the scheduled
delivery or place orders at risk, no customer notice was needed.

I learned that tool-based calculations and code-level checks are
important safeguards when using AI for business communications.
The team produced drafts for human review rather than sending
messages automatically. I used AI assistance to build, debug,
test, and document the implementation, and I reviewed the
saved outputs against the assignment requirements.
