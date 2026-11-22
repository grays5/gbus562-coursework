#!/usr/bin/env python3
"""specialists.py - the four specialists of the supplier-response team.

Each specialist is one Claude call (or tool-use loop) whose system prompt is read, unchanged,
from the organization's prompts/ folder. Nothing here writes a prompt of its own: the code only
passes each specialist its inputs, wrapped in labeled tags.

    run_supply_analyst      prompts/analyst.txt          tool loop over supply_mcp_server.py (MCP)
    write_supplier_reply    prompts/supplier-writer.txt  supplier email + analyst brief -> draft
    write_customer_notice   prompts/customer-writer.txt  one order's facts -> draft
    review_draft            prompts/reviewer.txt         draft + facts + audience -> APPROVE/REVISE

draft_with_review() runs a writer, has the reviewer check the draft, and (on REVISE) sends the
reviewer's notes back to the same writer, up to MAX_REVISIONS times. Every draft stays a draft:
nothing in this week's code can send email.

pipeline.py runs the specialists in a fixed order; orchestrator.py lets the orchestrator prompt
choose which ones to call.
"""

import email
import email.policy
import json
import os
import re
import sys
from dataclasses import dataclass, field
from email.utils import parseaddr
from pathlib import Path

import anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import supply_mcp_server as supply

MODEL = "claude-sonnet-5"  # required by the course; never silently replaced
MAX_TOKENS = 16000
WEEK_DIR = Path(__file__).resolve().parent
SERVER_SCRIPT = WEEK_DIR / "supply_mcp_server.py"
MAX_ANALYST_TURNS = 12
MAX_REVISIONS = 2  # reviewer rounds after the first draft
EMAIL_EXTENSIONS = {".eml", ".txt", ".md", ".json"}
NO_REPLY = "NO REPLY NEEDED"

BRIEF_FIELDS = ["part_id", "what_changed", "orders_at_risk", "options",
                "decisions_for_a_person", "supplier_questions"]
RISK_FIELDS = ["order_id", "customer", "units_short", "ship_day", "ready_day", "late_penalty"]


# ------------------------------------------------------------------ org + email


def load_prompts(org_dir):
    """The five role prompts, verbatim. A missing prompt is an error, never a default."""
    prompts = {}
    for name in supply.PROMPT_NAMES:
        path = Path(org_dir) / "prompts" / f"{name}.txt"
        if not path.is_file():
            raise FileNotFoundError(f"missing prompt {path}")
        prompts[name] = path.read_text(encoding="utf-8").strip()
    return prompts


def list_email_files(emails_dir):
    return sorted(p for p in Path(emails_dir).iterdir()
                  if p.is_file() and not p.name.startswith(".") and p.suffix.lower() in EMAIL_EXTENSIONS)


def find_email(emails_dir, wanted):
    """--email may be a file name (with or without extension), a number prefix like 01, or a path."""
    direct = Path(wanted)
    if direct.is_file():
        return direct.resolve()
    files = list_email_files(emails_dir)
    for p in files:
        if wanted in (p.name, p.stem):
            return p
    prefixed = [p for p in files if p.name.startswith(f"{wanted}-")]
    if len(prefixed) == 1:
        return prefixed[0]
    raise SystemExit(f"Error: email '{wanted}' not found in {emails_dir}. "
                     f"Available: {', '.join(p.name for p in files) or 'none'}")


def parse_email_file(path):
    """Return {'file', 'sender_name', 'sender', 'to', 'subject', 'body'}."""
    path = Path(path)
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(raw)
        from_field, to_field = str(data.get("from", "")), str(data.get("to", ""))
        subject, body = str(data.get("subject", "")), str(data.get("body", ""))
    else:
        msg = email.message_from_string(raw, policy=email.policy.default)
        from_field, to_field = str(msg.get("From") or ""), str(msg.get("To") or "")
        subject = str(msg.get("Subject") or "")
        part = msg.get_body(preferencelist=("plain", "html")) if msg.is_multipart() else msg
        body = part.get_content() if part is not None else msg.get_payload()
        if not (from_field or subject):
            body = raw
    name, addr = parseaddr(from_field)
    return {"file": path.name, "sender_name": name, "sender": addr.strip(), "to": to_field.strip(),
            "subject": subject.strip(), "body": str(body).strip()}


def email_as_text(msg):
    sender = f"{msg['sender_name']} <{msg['sender']}>" if msg["sender_name"] else msg["sender"]
    return f"From: {sender}\nTo: {msg['to']}\nSubject: {msg['subject']}\n\n{msg['body']}"


# ------------------------------------------------------------------ Claude calls


class ModelRefusal(RuntimeError):
    pass


@dataclass
class Usage:
    served_models: set = field(default_factory=set)
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    def add(self, response):
        self.calls += 1
        self.served_models.add(response.model)
        self.input_tokens += response.usage.input_tokens
        self.output_tokens += response.usage.output_tokens


def _text(response):
    return "".join(b.text for b in response.content if b.type == "text").strip()


async def ask(client, usage, system, user_text, tools=None, messages=None):
    """One Messages API call with MODEL. Raises ModelRefusal on stop_reason=refusal."""
    kwargs = {"tools": tools} if tools else {}
    response = await client.messages.create(
        model=MODEL, max_tokens=MAX_TOKENS, system=system,
        messages=messages if messages is not None else [{"role": "user", "content": user_text}],
        **kwargs)
    usage.add(response)
    if response.stop_reason == "refusal":
        raise ModelRefusal("the model declined this request (stop_reason=refusal)")
    return response


def tagged(tag, text):
    return f"<{tag}>\n{text}\n</{tag}>"


# ------------------------------------------------------------------ analyst


@dataclass
class AnalystResult:
    brief: dict | None
    raw_text: str
    steps: list            # (tool name, args dict, result text)
    coverage_results: list  # parsed check_coverage results (dicts without "error")
    problems: list          # validation / verification problems -> human review


def extract_json(text):
    """The last JSON object in the text (fenced or bare) that has a part_id field."""
    candidates = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    decoder, found = json.JSONDecoder(), []
    for chunk in candidates:
        try:
            found.append(json.loads(chunk))
        except json.JSONDecodeError:
            pass
    if not found:
        for i, ch in enumerate(text):
            if ch == "{":
                try:
                    obj, _ = decoder.raw_decode(text[i:])
                    found.append(obj)
                except json.JSONDecodeError:
                    continue
    found = [f for f in found if isinstance(f, dict) and "part_id" in f]
    return found[-1] if found else None


def validate_brief(brief):
    if brief is None:
        return ["the analyst did not finish with a JSON brief"]
    problems = []
    missing = [f for f in BRIEF_FIELDS if f not in brief]
    extra = [f for f in brief if f not in BRIEF_FIELDS]
    if missing:
        problems.append(f"brief is missing field(s): {missing}")
    if extra:
        problems.append(f"brief has unexpected field(s): {extra}")
    for f in ["orders_at_risk", "options", "decisions_for_a_person", "supplier_questions"]:
        if f in brief and not isinstance(brief[f], list):
            problems.append(f"brief field {f} is not a list")
    for o in brief.get("orders_at_risk") or []:
        if not isinstance(o, dict) or [f for f in RISK_FIELDS if f not in o]:
            problems.append(f"order at risk is missing field(s): {o}")
    return problems


def _same_number(a, b):
    """Exact whole-number match. null only matches null; true/false are not numbers."""
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, bool) or isinstance(b, bool):
        return False
    try:
        return int(a) == int(b) and float(a) == float(b)
    except (TypeError, ValueError):
        return False


_YES, _NO = {"yes", "true"}, {"no", "false"}


def _flag(value):
    """A yes/no flag as the tools and the analyst write it: yes/no, true/false (JSON or text)."""
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return True if text in _YES else False if text in _NO else None


def _same_flag(a, b):
    fa, fb = _flag(a), _flag(b)
    return fa is not None and fa == fb


NUMBER_FIELDS = ["units_short", "ship_day", "ready_day"]


def matching_tool_entry(order, coverage_results):
    """The check_coverage entry (from a real tool call) that this brief order's numbers came from."""
    for result in coverage_results:
        for entry in result.get("orders_at_risk", []):
            if (entry["order_id"] == str(order.get("order_id"))
                    and all(_same_number(order.get(k), entry.get(k)) for k in NUMBER_FIELDS)
                    and _same_flag(order.get("late_penalty"), entry.get("late_penalty"))):
                return entry
    return None


def verify_brief(brief, coverage_results):
    """Check every number in orders_at_risk and options against the analyst's check_coverage calls."""
    if brief is None:
        return []
    problems = []
    risky = brief.get("orders_at_risk") or []
    if risky and not coverage_results:
        problems.append("orders_at_risk is not empty but check_coverage was never called successfully")
    for o in risky:
        if isinstance(o, dict) and matching_tool_entry(o, coverage_results) is None:
            problems.append(f"numbers for {o.get('order_id')} do not match any check_coverage result")
    tool_sets = [sorted(e["order_id"] for e in r.get("orders_at_risk", [])) for r in coverage_results]
    for opt in brief.get("options") or []:
        ids = opt.get("order_ids") if isinstance(opt, dict) else None
        if ids is None:
            ids = next((v for v in opt.values() if isinstance(v, list)), None) if isinstance(opt, dict) else None
        if ids is None:
            problems.append(f"option has no list of order_ids: {opt}")
        elif sorted(map(str, ids)) not in tool_sets:
            problems.append(f"order_ids for option {opt.get('name', opt)} do not match any check_coverage result")
    return problems


async def run_supply_analyst(client, usage, org_dir, prompts, msg):
    """The analyst's tool loop. It starts its own supply_mcp_server.py process for the org."""
    params = StdioServerParameters(command=sys.executable,
                                   args=[str(SERVER_SCRIPT), "--org", str(org_dir)],
                                   env=dict(os.environ))
    steps, coverage_results, text = [], [], ""
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = [{"name": t.name, "description": t.description or "", "input_schema": t.inputSchema}
                     for t in (await session.list_tools()).tools]
            messages = [{"role": "user", "content": tagged("supplier_email", email_as_text(msg))}]
            for _ in range(MAX_ANALYST_TURNS):
                response = await ask(client, usage, prompts["analyst"], None, tools, messages)
                messages.append({"role": "assistant", "content": response.content})
                tool_uses = [b for b in response.content if b.type == "tool_use"]
                if not tool_uses:
                    text = _text(response)
                    break
                results = []
                for tu in tool_uses:
                    args = tu.input if isinstance(tu.input, dict) else {}
                    try:
                        res = await session.call_tool(tu.name, args)
                        out = "\n".join(c.text for c in res.content if getattr(c, "type", "") == "text")
                        is_error = bool(res.isError)
                    except Exception as e:  # report tool failures back to the model
                        out, is_error = f"Tool error: {e}", True
                    steps.append((tu.name, args, out))
                    if tu.name == "check_coverage" and not is_error:
                        try:
                            parsed = json.loads(out)
                            if "error" not in parsed:
                                coverage_results.append(parsed)
                        except json.JSONDecodeError:
                            pass
                    results.append({"type": "tool_result", "tool_use_id": tu.id, "content": out,
                                    "is_error": is_error})
                messages.append({"role": "user", "content": results})
            else:
                text = ""
    brief = extract_json(text)
    problems = validate_brief(brief) + verify_brief(brief, coverage_results)
    if not text:
        problems.insert(0, f"the analyst did not finish within {MAX_ANALYST_TURNS} turns")
    return AnalystResult(brief, text, steps, coverage_results, problems)


# ------------------------------------------------------------------ writers + reviewer


def customer_facts(data, entry):
    """The only facts a customer writer sees: no supplier, no penalty, no other customer."""
    order = data.orders_by_id[entry["order_id"]]
    ready = entry["ready_day"]
    return {
        "order_id": order["order_id"],
        "customer": order["customer"],
        "product": order["product"],
        "quantity": order["units"],
        "planned_ship_day": order["ship_by_day"],
        "expected_ship_day": ready if ready is not None else "not yet known",
        "days_later_than_planned": (ready - order["ship_by_day"]) if ready is not None else "not yet known",
        "days_are_counted_from": "today (day 0)",
    }


def supplier_input(msg, brief):
    brief_text = json.dumps(brief, indent=2) if brief is not None else "(no analyst brief was produced)"
    return tagged("supplier_email", email_as_text(msg)) + "\n\n" + tagged("analyst_brief", brief_text)


def customer_input(facts):
    return tagged("order_facts", json.dumps(facts, indent=2))


def revision_input(base_input, previous_draft, review_text):
    return (base_input + "\n\n" + tagged("your_previous_draft", previous_draft) + "\n\n"
            + tagged("reviewer_notes", review_text)
            + "\n\nRewrite the draft so it fixes every point in the reviewer notes. "
              "Reply with the email text only.")


def parse_verdict(review_text):
    for line in review_text.splitlines():
        word = re.sub(r"[^A-Z]", "", line.strip().upper())
        if word:
            return word if word in {"APPROVE", "REVISE"} else "UNCLEAR"
    return "UNCLEAR"


async def review_draft(client, usage, prompts, draft, facts_text, audience):
    user = (f"Audience: {audience}\n\n" + tagged("facts", facts_text) + "\n\n" + tagged("draft", draft))
    text = _text(await ask(client, usage, prompts["reviewer"], user))
    return parse_verdict(text), text


@dataclass
class DraftRecord:
    audience: str          # "supplier" or "customer"
    to: str
    about: str             # e.g. PO / order id
    final: str
    verdict: str           # APPROVE / REVISE / UNCLEAR / NOT REVIEWED
    rounds: list           # (draft, verdict, review_text)
    facts: str
    late_penalty: bool = False   # set from orders data in code; never shown to the writer

    @property
    def no_reply(self):
        return self.final.strip().upper().rstrip(".") == NO_REPLY

    @property
    def needs_human_review(self):
        return self.reasons() != []

    def reasons(self):
        if self.no_reply:
            return []
        reasons = []
        if self.late_penalty:
            reasons.append(f"{self.about} has a late penalty")
        if self.verdict == "UNCLEAR":
            reasons.append("the reviewer's answer did not start with APPROVE or REVISE")
        elif self.verdict != "APPROVE":
            reasons.append(f"the reviewer still asked for revisions after {len(self.rounds)} round(s)")
        return reasons


async def draft_with_review(client, usage, prompts, writer, base_input, facts_text, audience, to, about):
    """Writer -> reviewer -> (on REVISE) writer again, up to MAX_REVISIONS revisions."""
    rounds, user = [], base_input
    for _ in range(MAX_REVISIONS + 1):
        draft = _text(await ask(client, usage, prompts[writer], user))
        if audience == "supplier" and draft.strip().upper().rstrip(".") == NO_REPLY:
            return DraftRecord(audience, to, about, draft, "NOT REVIEWED", rounds, facts_text)
        verdict, review_text = await review_draft(client, usage, prompts, draft, facts_text, audience)
        rounds.append((draft, verdict, review_text))
        if verdict == "APPROVE":
            break
        user = revision_input(base_input, draft, review_text)
    return DraftRecord(audience, to, about, rounds[-1][0], rounds[-1][1], rounds, facts_text)


async def write_supplier_reply(client, usage, prompts, msg, brief):
    base = supplier_input(msg, brief)
    to = f"{msg['sender_name']} <{msg['sender']}>" if msg["sender_name"] else msg["sender"]
    return await draft_with_review(client, usage, prompts, "supplier-writer", base, base,
                                   "supplier", to, f"Re: {msg['subject']}")


async def write_customer_notice(client, usage, prompts, data, entry):
    facts = customer_facts(data, entry)
    order = data.orders_by_id[entry["order_id"]]
    to = f"{order['customer']} <{order['contact_email']}>" if order.get("contact_email") else order["customer"]
    base = customer_input(facts)
    record = await draft_with_review(client, usage, prompts, "customer-writer", base, base,
                                     "customer", to, f"Order {order['order_id']}")
    record.late_penalty = bool(order.get("late_penalty"))
    return record
