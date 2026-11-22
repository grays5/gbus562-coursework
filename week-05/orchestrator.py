#!/usr/bin/env python3
"""orchestrator.py - the supplier-response team led by an orchestrator agent.

The orchestrator (system prompt: <org>/prompts/orchestrator.txt, verbatim) reads one supplier
email and decides which specialists to call through four tools:

    run_supply_analyst      the analyst works out how the email affects customer orders
    draft_supplier_reply    supplier writer + reviewer (revise loop), using the latest brief
    draft_customer_notice   customer writer + reviewer for ONE order at risk (by order_id)
    finish                  short summary for the purchasing manager + whether a person must decide

The orchestrator never sees a writer's inputs beyond what the tools return, and it cannot pass
facts of its own to a writer: draft_customer_notice takes only an order_id, and the code builds
that customer's facts from the analyst's verified brief and orders.csv. Nothing can be sent.

Usage (from the repository root, with the virtual environment active):

    python week-05/orchestrator.py --org copperline-coffee --email 01
    python week-05/orchestrator.py --org copperline-coffee --save

--org defaults to brookfield-bikes. The API key comes from ANTHROPIC_API_KEY (never written to disk).
"""

import json

import pipeline
import specialists as sp

MAX_TURNS = 12

TOOLS = [
    {
        "name": "run_supply_analyst",
        "description": "Ask the supply analyst to work out how the current supplier email affects "
                       "customer orders. Returns the analyst's brief (JSON) and any problems found "
                       "when its numbers were checked against the coverage tool.",
        "strict": True,
        "input_schema": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
    },
    {
        "name": "draft_supplier_reply",
        "description": "Have the supplier writer draft a reply to the supplier who sent the current "
                       "email, using the latest analyst brief, then have the reviewer check it "
                       "(with revisions). Returns the final draft and the reviewer's verdict.",
        "strict": True,
        "input_schema": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
    },
    {
        "name": "draft_customer_notice",
        "description": "Have the customer writer draft a notice to the customer of ONE order that the "
                       "analyst's brief lists in orders_at_risk, then have the reviewer check it. "
                       "The customer's facts are taken from the brief and the order records.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string", "description": "An order_id from orders_at_risk."}},
            "required": ["order_id"], "additionalProperties": False,
        },
    },
    {
        "name": "finish",
        "description": "End the job. Give a short summary for Copperline's purchasing manager and say "
                       "whether a person needs to make a decision.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {"summary": {"type": "string"}, "decision_needed": {"type": "boolean"}},
            "required": ["summary", "decision_needed"], "additionalProperties": False,
        },
    },
]


def _draft_result(record):
    return json.dumps({"final_draft": record.final, "reviewer_verdict": record.verdict,
                       "review_rounds": len(record.rounds)}, indent=2)


async def run_orchestrator(client, org_dir, prompts, data, msg):
    run = pipeline.TeamRun("orchestrator", org_dir, msg)
    messages = [{"role": "user", "content": sp.tagged("supplier_email", sp.email_as_text(msg))}]
    drafted_orders = {}

    async def call(name, args):
        if name == "run_supply_analyst":
            run.analyst = await sp.run_supply_analyst(client, run.usage, org_dir, prompts, msg)
            return json.dumps({"brief": run.analyst.brief, "problems": run.analyst.problems}, indent=2), False
        if name == "draft_supplier_reply":
            brief = run.analyst.brief if run.analyst else None
            record = await sp.write_supplier_reply(client, run.usage, prompts, msg, brief)
            run.drafts = [d for d in run.drafts if d.audience != "supplier"] + [record]
            return _draft_result(record), False
        if name == "draft_customer_notice":
            order_id = str(args.get("order_id", "")).strip()
            if order_id in drafted_orders:
                return _draft_result(drafted_orders[order_id]), False
            if run.analyst is None or run.analyst.brief is None:
                return "ERROR: run the supply analyst first; there is no brief yet.", True
            listed = next((o for o in run.analyst.brief.get("orders_at_risk") or []
                           if isinstance(o, dict) and str(o.get("order_id")) == order_id), None)
            if listed is None:
                return f"ERROR: {order_id} is not in the brief's orders_at_risk.", True
            entry = sp.matching_tool_entry(listed, run.analyst.coverage_results)
            if entry is None or order_id not in data.orders_by_id:
                run.notes.append(f"customer notice for {order_id} refused: its numbers could not be "
                                 "matched to a check_coverage result")
                return f"ERROR: the brief's numbers for {order_id} do not match the coverage tool's output.", True
            record = await sp.write_customer_notice(client, run.usage, prompts, data, entry)
            drafted_orders[order_id] = record
            run.drafts.append(record)
            return _draft_result(record), False
        return f"ERROR: unknown tool {name}", True

    for _ in range(MAX_TURNS):
        response = await sp.ask(client, run.usage, prompts["orchestrator"], None, TOOLS, messages)
        messages.append({"role": "assistant", "content": response.content})
        tool_uses = [b for b in response.content if b.type == "tool_use"]
        if not tool_uses:
            run.notes.append("the orchestrator stopped without calling finish")
            run.summary = sp._text(response) or "(no summary)"
            return run
        results, finished = [], False
        for tu in tool_uses:
            args = tu.input if isinstance(tu.input, dict) else {}
            if tu.name == "finish":
                run.summary = str(args.get("summary", "")).strip()
                run.decision_needed = bool(args.get("decision_needed", True))
                run.steps.append(f"finish(decision_needed={run.decision_needed})")
                results.append({"type": "tool_result", "tool_use_id": tu.id, "content": "Job finished."})
                finished = True
                continue
            text, is_error = await call(tu.name, args)
            label = f"{tu.name}({json.dumps(args) if args else ''})"
            if tu.name.startswith("draft_") and not is_error:
                label += f" -> reviewer {json.loads(text)['reviewer_verdict']}"
            elif is_error:
                label += f" -> {text}"
            run.steps.append(label)
            results.append({"type": "tool_result", "tool_use_id": tu.id, "content": text, "is_error": is_error})
        messages.append({"role": "user", "content": results})
        if finished:
            return run
    run.notes.append(f"the orchestrator did not call finish within {MAX_TURNS} turns")
    return run


def main():
    pipeline.cli("orchestrator", "Supplier-response team led by an orchestrator agent.", run_orchestrator)


if __name__ == "__main__":
    main()
