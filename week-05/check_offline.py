#!/usr/bin/env python3
"""check_offline.py - code checks for the Week 5 team that make NO Anthropic API calls.

What it checks:
  A. The Copperline data loads and every CSV column maps.
  B. supply_mcp_server.py works as a real MCP server over stdio: it lists the three tools named
     in prompts/analyst.txt, and get_part / get_orders_for_part / check_coverage answer.
  C. check_coverage gives the expected results for each supplier email's schedule change.
  D. pipeline.py and orchestrator.py run end to end with a SCRIPTED STAND-IN for the Claude API
     (canned replies, no network). This tests the code paths only - the stand-in's text is not
     model output and is never saved as a run. It also plants a wrong number in a brief to check
     that the code refuses to draft a customer notice from it and flags the run for review.
  E. The command-line programs stop cleanly with no API key and with the default --org.

Usage (from the repository root, with the virtual environment active):

    python week-05/check_offline.py
    python week-05/check_offline.py --save    # also writes week-05/checks/offline-checks.txt
"""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

WEEK_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(WEEK_DIR))

import supply_mcp_server as supply  # noqa: E402

ORG = WEEK_DIR / "copperline-coffee"
LINES, FAILURES = [], []


def log(text=""):
    print(text)
    LINES.append(text)


def check(name, ok, detail=""):
    log(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)


def at_risk(result):
    return [(o["order_id"], o["units_short"], o["ship_day"], o["ready_day"], o["late_penalty"])
            for o in result["orders_at_risk"]]


# ---------------------------------------------------------------- A + C: data and coverage


def check_data_and_coverage():
    log("A. Data loading and column mapping")
    check("copperline-coffee folder is complete", supply.missing_org_files(ORG) == [],
          str(supply.missing_org_files(ORG)))
    data = supply.SupplyData(ORG)
    check("all 5 CSVs mapped", len(data.mappings) == 5, ", ".join(sorted(data.mappings)))
    check("4 parts, 4 inbound POs, 10 orders, 6 BOM rows, 4 suppliers",
          (len(data.parts), len(data.inbound), len(data.orders), len(data.bom), len(data.suppliers))
          == (4, 4, 10, 6, 4))
    check("Cafe Duo uses 2 PU-20 per machine", data.per_unit("Cafe Duo", "PU-20") == 2)
    log()

    log("C. check_coverage for each supplier email (days counted from today = day 0)")
    for pid in data.parts:
        check(f"current schedule, {pid}: no orders at risk", at_risk(data.check_coverage(pid)) == [])

    r = data.check_coverage("PU-20", [{"qty": 40, "arrives_in_days": 4},
                                      {"qty": 160, "arrives_in_days": 19}], "PO-5512")
    expected = [("O-2203", 10, 12, 19, "yes"), ("O-2204", 20, 15, 19, "no"), ("O-2205", 25, 17, 19, "yes")]
    check("email 01 (PU-20: 40 on day 4, 160 on day 19)", at_risk(r) == expected, json.dumps(at_risk(r)))

    a = data.check_coverage("BL-12", [{"qty": 80, "arrives_in_days": 7},
                                      {"qty": 120, "arrives_in_days": 21}], "PO-5520")
    check("email 02 Option A (BL-12: 80 on day 7, 120 on day 21)",
          at_risk(a) == [("O-2205", 5, 17, 21, "yes")], json.dumps(at_risk(a)))
    b = data.check_coverage("BL-12", [{"qty": 200, "arrives_in_days": 13}], "PO-5520")
    check("email 02 Option B (BL-12: 200 on day 13)",
          at_risk(b) == [("O-2203", 40, 12, 13, "yes")], json.dumps(at_risk(b)))

    c = data.check_coverage("BR-64", [{"qty": 120, "arrives_in_days": 13}], "PO-5531")
    check("email 03 (BR-64: 120 on day 13): no orders at risk", at_risk(c) == [], json.dumps(at_risk(c)))

    check("email 04 (SW-3 arrives as scheduled): no orders at risk", at_risk(data.check_coverage("SW-3")) == [])

    bad = data.check_coverage("PU-20", [{"qty": 40, "arrives_in_days": 4}], "PO-9999")
    check("unknown PO is reported as an error", "error" in bad)
    check("unknown part is reported as an error", "error" in data.check_coverage("XX-1"))
    log()
    return data, {"01": r, "02A": a, "02B": b, "03": c}


# ---------------------------------------------------------------- B: the real MCP server


async def check_mcp_server():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    log("B. supply_mcp_server.py over MCP stdio")
    params = StdioServerParameters(command=sys.executable,
                                   args=[str(WEEK_DIR / "supply_mcp_server.py"), "--org", str(ORG)],
                                   env=dict(os.environ))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            names = sorted(t.name for t in (await session.list_tools()).tools)
            check("server lists exactly the tools named in analyst.txt",
                  names == ["check_coverage", "get_orders_for_part", "get_part"], str(names))
            part = json.loads((await session.call_tool("get_part", {"part_id": "PU-20"})).content[0].text)
            check("get_part(PU-20): 50 on hand, PO-5512 for 200 on day 4",
                  part["on_hand"] == 50 and part["scheduled_deliveries"][0]["qty"] == 200
                  and part["scheduled_deliveries"][0]["arrives_in_days"] == 4)
            orders = json.loads((await session.call_tool("get_orders_for_part", {"part_id": "PU-20"})).content[0].text)
            check("get_orders_for_part(PU-20): 7 orders (Cafe One + Cafe Duo)", len(orders["orders"]) == 7)
            cov = json.loads((await session.call_tool("check_coverage", {
                "part_id": "PU-20", "replaces_po": "PO-5512",
                "new_deliveries": [{"qty": 40, "arrives_in_days": 4}, {"qty": 160, "arrives_in_days": 19}],
            })).content[0].text)
            check("check_coverage through MCP matches the direct call",
                  [o["order_id"] for o in cov["orders_at_risk"]] == ["O-2203", "O-2204", "O-2205"])
    log()


# ---------------------------------------------------------------- D: scripted stand-in for the API


def _resp(blocks, stop="end_turn"):
    return SimpleNamespace(model="scripted-stand-in (not a model)", stop_reason=stop, content=blocks,
                           usage=SimpleNamespace(input_tokens=0, output_tokens=0))


def _text(t):
    return SimpleNamespace(type="text", text=t)


def _tool(name, args, n):
    return SimpleNamespace(type="tool_use", id=f"tu_{n}", name=name, input=args)


class StandIn:
    """Pretends to be anthropic.AsyncAnthropic. Picks a canned reply by which prompt is the system."""

    def __init__(self, prompts, brief, orchestrated=False):
        self.prompts, self.brief, self.orchestrated = prompts, brief, orchestrated
        self.analyst_turn = self.orch_turn = 0
        self.messages = SimpleNamespace(create=self.create)

    async def create(self, model, system, messages, max_tokens, tools=None):
        assert model == "claude-sonnet-5", model
        p = self.prompts
        if system == p["analyst"]:
            self.analyst_turn += 1
            if self.analyst_turn == 1:
                return _resp([_tool("check_coverage", {
                    "part_id": "PU-20", "replaces_po": "PO-5512",
                    "new_deliveries": [{"qty": 40, "arrives_in_days": 4}, {"qty": 160, "arrives_in_days": 19}]}, 1)],
                    "tool_use")
            return _resp([_text("```json\n" + json.dumps(self.brief) + "\n```")])
        if system == p["reviewer"]:
            return _resp([_text("APPROVE")])
        if system in (p["supplier-writer"], p["customer-writer"]):
            return _resp([_text("[stand-in draft text]")])
        if system == p["orchestrator"]:
            self.orch_turn += 1
            script = {1: [_tool("run_supply_analyst", {}, 10)],
                      2: [_tool("draft_supplier_reply", {}, 11)],
                      3: [_tool("draft_customer_notice", {"order_id": "O-2203"}, 12),
                          _tool("draft_customer_notice", {"order_id": "O-2204"}, 13)],
                      4: [_tool("finish", {"summary": "stand-in summary", "decision_needed": False}, 14)]}
            return _resp(script[self.orch_turn], "tool_use")
        raise AssertionError("unexpected system prompt")


def stand_in_brief(wrong_number=False):
    risky = [{"order_id": "O-2203", "customer": "Elm State University Dining", "units_short": 10,
              "ship_day": 12, "ready_day": 19, "late_penalty": "yes"},
             {"order_id": "O-2204", "customer": "Kettle & Crumb Bakery", "units_short": 20,
              "ship_day": 15, "ready_day": 19, "late_penalty": "no"}]
    if wrong_number:
        risky[1]["units_short"] = 99  # planted error
    return {"part_id": "PU-20", "what_changed": "stand-in", "orders_at_risk": risky, "options": [],
            "decisions_for_a_person": [], "supplier_questions": ["customer list"]}


async def check_team_code():
    import orchestrator
    import pipeline
    import specialists as sp

    log("D. Team code paths with a scripted stand-in for the API (no network, not model output)")
    prompts = sp.load_prompts(ORG)
    data = supply.SupplyData(ORG)
    msg = sp.parse_email_file(ORG / "supplier-emails" / "01-danforth-pump-delay.eml")
    check("email 01 parsed", msg["sender"] == "d.kessler@danforthpump.example" and "PO-5512" in msg["subject"])

    for mode, runner in [("pipeline", pipeline.run_pipeline), ("orchestrator", orchestrator.run_orchestrator)]:
        run = await runner(StandIn(prompts, stand_in_brief()), ORG, prompts, data, msg)
        out = pipeline.format_run(run)
        notices = [d for d in run.drafts if d.audience == "customer"]
        check(f"{mode}: brief checks pass when numbers match check_coverage", run.analyst.problems == [],
              str(run.analyst.problems))
        check(f"{mode}: 1 supplier reply + 2 customer notices drafted",
              len(run.drafts) == 3 and len(notices) == 2)
        check(f"{mode}: output has full brief, FINAL DRAFT and human-review line",
              "ANALYST BRIEF (full)" in out and out.count("FINAL DRAFT") == 3
              and "Needs human review: true" in out)
        check(f"{mode}: penalty order and supplier question force human review",
              "O-2203 at risk has a late penalty" in out and "supplier asked" in out)
        facts = json.loads(notices[0].facts.split("\n", 1)[1].rsplit("\n", 1)[0])
        check(f"{mode}: customer writer sees no supplier name or penalty",
              "Danforth" not in notices[0].facts and "penalty" not in notices[0].facts
              and facts["days_later_than_planned"] == 7, json.dumps(facts))

        run = await runner(StandIn(prompts, stand_in_brief(wrong_number=True)), ORG, prompts, data, msg)
        out = pipeline.format_run(run)
        drafted = [d.about for d in run.drafts if d.audience == "customer"]
        check(f"{mode}: planted wrong number is caught (no notice for O-2204, run flagged)",
              "Order O-2204" not in drafted and "numbers for O-2204 do not match" in out
              and "Needs human review: true" in out, f"customer notices drafted: {drafted}")
    log()


# ---------------------------------------------------------------- E: command-line failure modes


def check_cli():
    log("E. Command-line behaviour without an API key")
    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}
    for script in ["pipeline.py", "orchestrator.py"]:
        p = subprocess.run([sys.executable, str(WEEK_DIR / script)], capture_output=True, text=True,
                           env=env, cwd=WEEK_DIR.parent)
        check(f"{script} with default --org (brookfield-bikes) stops and lists missing files",
              p.returncode != 0 and "incomplete" in p.stderr and "parts.csv" in p.stderr)
        p = subprocess.run([sys.executable, str(WEEK_DIR / script), "--org", "copperline-coffee",
                            "--email", "01"], capture_output=True, text=True, env=env, cwd=WEEK_DIR.parent)
        check(f"{script} --org copperline-coffee with no API key stops with a clear message",
              p.returncode != 0 and "no Anthropic API key" in p.stderr, p.stderr.strip().splitlines()[-1])
    p = subprocess.run([sys.executable, str(WEEK_DIR / "pipeline.py"), "--org", "copperline-coffee",
                        "--email", "99"], capture_output=True, text=True, env=env, cwd=WEEK_DIR.parent)
    check("unknown --email lists the available emails", p.returncode != 0 and "Available:" in p.stderr)
    log()


def main():
    log("WEEK 5 OFFLINE CHECKS (no Anthropic API calls were made)")
    log("=" * 76)
    check_data_and_coverage()
    asyncio.run(check_mcp_server())
    asyncio.run(check_team_code())
    check_cli()
    total = sum(1 for line in LINES if line.startswith("[PASS]") or line.startswith("[FAIL]"))
    log(f"Result: {total - len(FAILURES)} of {total} checks passed.")
    if "--save" in sys.argv:
        path = WEEK_DIR / "checks" / "offline-checks.txt"
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(LINES) + "\n", encoding="utf-8")
        print(f"(Saved to {path})", file=sys.stderr)
    sys.exit(1 if FAILURES else 0)


if __name__ == "__main__":
    main()
