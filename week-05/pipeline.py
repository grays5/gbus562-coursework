#!/usr/bin/env python3
"""pipeline.py - the supplier-response team as a fixed pipeline (code decides the steps).

For each supplier email, always in this order:
  1. supply analyst  -> brief (JSON), using the supply MCP server's tools
  2. supplier writer -> reply to the supplier (or NO REPLY NEEDED), then reviewer, revise loop
  3. customer writer -> one notice per order at risk whose numbers match a check_coverage
     result, then reviewer, revise loop. Skipped while the supplier is waiting for Copperline
     to choose an option (the ship dates depend on that decision).
  4. prints the full analyst brief, each FINAL DRAFT, and the human-review flags.

orchestrator.py runs the same specialists but lets the orchestrator prompt choose the steps.
This file also holds the output format and command-line handling both programs share.

Usage (from the repository root, with the virtual environment active):

    python week-05/pipeline.py --org copperline-coffee --email 01
    python week-05/pipeline.py --org copperline-coffee                 # every email
    python week-05/pipeline.py --org copperline-coffee --email 01 --save

--org defaults to brookfield-bikes. The Anthropic API key is read from the ANTHROPIC_API_KEY
environment variable (or a .env file, which Git ignores). It is never written to disk.
Nothing is ever sent: every draft is saved for a person to check.
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic
from dotenv import load_dotenv

import specialists as sp
import supply_mcp_server as supply

WEEK_DIR = Path(__file__).resolve().parent
RUNS_DIR = WEEK_DIR / "runs"
RULE = "=" * 76
LINE = "-" * 76


# ------------------------------------------------------------------ run record


class TeamRun:
    """Everything one email's run produced, whichever program drove it."""

    def __init__(self, mode, org_dir, msg):
        self.mode, self.org_dir, self.msg = mode, org_dir, msg
        self.usage = sp.Usage()
        self.analyst = None           # specialists.AnalystResult
        self.drafts = []              # specialists.DraftRecord
        self.steps = []               # orchestrator tool calls (orchestrator mode)
        self.summary = None           # orchestrator's finish summary
        self.decision_needed = None   # orchestrator's finish flag
        self.notes = []               # extra human-review reasons found by code


def human_review_reasons(run):
    """Code-level triggers. The model cannot talk its way out of these."""
    reasons = []
    a = run.analyst
    if a is not None:
        reasons += [f"analyst: {p}" for p in a.problems]
        brief = a.brief or {}
        for d in brief.get("decisions_for_a_person") or []:
            reasons.append(f"decision for a person: {d}")
        for q in brief.get("supplier_questions") or []:
            reasons.append(f"supplier asked: {q}")
        for o in brief.get("orders_at_risk") or []:
            if isinstance(o, dict) and str(o.get("late_penalty", "")).lower() in {"yes", "true"}:
                reasons.append(f"order {o.get('order_id')} at risk has a late penalty")
    if run.decision_needed:
        reasons.append("the orchestrator reported that a person needs to make a decision")
    for d in run.drafts:
        reasons += [f"{d.audience} draft ({d.about}): {r}" for r in d.reasons()]
    reasons += run.notes
    return reasons


# ------------------------------------------------------------------ output format


def _indent(text, pad="    "):
    return "\n".join(pad + line if line else line for line in str(text).splitlines())


def format_run(run):
    m = run.msg
    out = [RULE,
           f"Organization: {run.org_dir.name}",
           f"Mode: {run.mode}",
           f"Email file: {m['file']}",
           f"From: {(m['sender_name'] + ' ') if m['sender_name'] else ''}<{m['sender']}>",
           f"Subject: {m['subject']}",
           LINE]

    if run.steps:
        out.append("ORCHESTRATOR STEPS")
        out += [f"  {i}. {s}" for i, s in enumerate(run.steps, 1)]
        out.append(LINE)

    out.append("SUPPLY ANALYST")
    a = run.analyst
    if a is None:
        out.append("  (not run)")
    else:
        out.append("Analyst tool calls:")
        for i, (name, args, result) in enumerate(a.steps, 1):
            out.append(f"  {i}. {name}({json.dumps(args)})")
            out.append(_indent(result, "       "))
        if not a.steps:
            out.append("  (none)")
        out.append("")
        out.append("ANALYST BRIEF (full)")
        out.append(json.dumps(a.brief, indent=2) if a.brief is not None
                   else "(no JSON brief found; analyst's final text follows)\n" + (a.raw_text or "(empty)"))
        if a.problems:
            out.append("Brief checks: PROBLEMS")
            out += [f"  - {p}" for p in a.problems]
        else:
            out.append("Brief checks: OK (fields complete; every at-risk number matches a check_coverage result)")
    out.append(LINE)

    if not run.drafts:
        out += ["DRAFTS", "  (no drafts were written)", LINE]
    for n, d in enumerate(run.drafts, 1):
        out.append(f"DRAFT {n} of {len(run.drafts)}: {d.audience} {'reply' if d.audience == 'supplier' else 'notice'}")
        out.append(f"To: {d.to}")
        out.append(f"About: {d.about}")
        for r, (draft, verdict, review_text) in enumerate(d.rounds, 1):
            out.append(f"Review round {r}: {verdict}")
            if verdict != "APPROVE" or r < len(d.rounds):
                out.append("  Draft reviewed in this round:")
                out.append(_indent(draft))
            out.append("  Reviewer:")
            out.append(_indent(review_text))
        out += ["", "FINAL DRAFT (not sent - saved for a person to check)", "", d.final, "",
                f"Reviewer verdict: {d.verdict}",
                f"Needs human review: {'true' if d.needs_human_review else 'false'}"]
        if d.reasons():
            out.append("Reason: " + " | ".join(d.reasons()))
        out.append(LINE)

    if run.summary is not None:
        out += ["SUMMARY FOR THE PURCHASING MANAGER (from the orchestrator)", run.summary,
                f"Decision needed by a person: {'yes' if run.decision_needed else 'no'}", LINE]

    reasons = human_review_reasons(run)
    out.append("HUMAN REVIEW")
    out.append(f"Needs human review: {'true' if reasons else 'false'}")
    if reasons:
        out.append("Reasons:")
        out += [f"  - {r}" for r in reasons]
    out.append("Nothing was sent. Every draft above is saved for a person to check.")
    served = ", ".join(sorted(run.usage.served_models)) or "none"
    out.append(f"Model requested: {sp.MODEL} | served: {served} | API calls: {run.usage.calls} | "
               f"tokens in/out: {run.usage.input_tokens}/{run.usage.output_tokens}")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ the fixed pipeline


async def run_pipeline(client, org_dir, prompts, data, msg):
    run = TeamRun("pipeline", org_dir, msg)
    run.analyst = await sp.run_supply_analyst(client, run.usage, org_dir, prompts, msg)
    brief = run.analyst.brief

    run.drafts.append(await sp.write_supplier_reply(client, run.usage, prompts, msg, brief))

    risky = (brief or {}).get("orders_at_risk") or []
    if brief and brief.get("options") and risky:
        run.notes.append("customer notices not drafted: the supplier offered options, so ship dates "
                         "depend on which option a person chooses")
        return run
    for order in risky:
        if not isinstance(order, dict):
            continue
        entry = sp.matching_tool_entry(order, run.analyst.coverage_results)
        if entry is None or entry["order_id"] not in data.orders_by_id:
            run.notes.append(f"customer notice for {order.get('order_id')} not drafted: "
                             "its numbers could not be matched to a check_coverage result")
            continue
        run.drafts.append(await sp.write_customer_notice(client, run.usage, prompts, data, entry))
    return run


# ------------------------------------------------------------------ shared CLI


def _first_leaf(exc):
    while isinstance(exc, BaseExceptionGroup) and exc.exceptions:
        exc = exc.exceptions[0]
    return exc


def _run_header(org_dir, mode):
    return (f"SUPPLIER-RESPONSE TEAM RUN\nOrganization: {org_dir.name}\nMode: {mode}\n"
            f"Model requested: {sp.MODEL}\n"
            f"Run time (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}\n")


def cli(mode, description, runner):
    """Shared main() for pipeline.py and orchestrator.py. runner(client, org_dir, prompts, data, msg)."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--org", default=supply.DEFAULT_ORG,
                        help=f"organization folder under week-05/ or a path (default: {supply.DEFAULT_ORG})")
    parser.add_argument("--email", help="one supplier email: file name, stem, or number prefix like 01 "
                                        "(default: every email)")
    parser.add_argument("--save", nargs="?", const="", metavar="FILE",
                        help=f"save the output; with no FILE, saves to week-05/runs/<org>/<email>-{mode}.txt")
    args = parser.parse_args()

    load_dotenv(WEEK_DIR.parent / ".env")
    load_dotenv(WEEK_DIR / ".env")

    org_dir = supply.resolve_org_dir(args.org)
    problems = supply.missing_org_files(org_dir)
    if problems:
        sys.exit(f"Error: organization folder '{org_dir.name}' is incomplete. Missing:\n  - "
                 + "\n  - ".join(problems)
                 + ("\nThe Brookfield Bikes data is not in this repository yet. "
                    "Run a provided organization instead, e.g. --org copperline-coffee"
                    if org_dir.name == supply.DEFAULT_ORG else ""))
    try:
        data = supply.SupplyData(org_dir)
        prompts = sp.load_prompts(org_dir)
    except (ValueError, FileNotFoundError) as e:
        sys.exit(f"Error: {e}")
    for name, mapping in data.mappings.items():
        print(f"({name}: " + ", ".join(f"{k}<-'{v}'" for k, v in mapping.items()) + ")", file=sys.stderr)

    emails_dir = supply.emails_dir_for(org_dir)
    emails = [sp.find_email(emails_dir, args.email)] if args.email else sp.list_email_files(emails_dir)
    client = anthropic.AsyncAnthropic()
    combined = []
    for path in emails:
        msg = sp.parse_email_file(path)
        try:
            run = asyncio.run(runner(client, org_dir, prompts, data, msg))
        except BaseExceptionGroup as group:  # the MCP client wraps errors in task groups
            err = _first_leaf(group)
            if isinstance(err, (anthropic.AnthropicError, TypeError)):
                _api_exit(err)
            raise err from None
        except sp.ModelRefusal as e:
            sys.exit(f"Error on {path.name}: {e}. Nothing was drafted.")
        except (anthropic.AnthropicError, TypeError) as e:  # TypeError: no API key configured
            _api_exit(e)
        output = format_run(run)
        sys.stdout.write(output)
        combined.append(output)
        if args.save == "":
            save_path = RUNS_DIR / org_dir.name / f"{path.stem}-{mode}.txt"
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_text(_run_header(org_dir, mode) + output, encoding="utf-8")
            print(f"(Saved run to {save_path})", file=sys.stderr)
    if args.save:
        save_path = Path(args.save)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text(_run_header(org_dir, mode) + "".join(combined), encoding="utf-8")
        print(f"(Saved run to {save_path})", file=sys.stderr)


def _api_exit(e):
    if isinstance(e, anthropic.NotFoundError):
        sys.exit(f"Error: model '{sp.MODEL}' was not found or is not available to this API key. "
                 f"No other model was substituted. Details: {e}")
    if isinstance(e, anthropic.AuthenticationError):
        sys.exit(f"Error: the Anthropic API rejected the API key. Check ANTHROPIC_API_KEY. Details: {e}")
    if isinstance(e, anthropic.PermissionDeniedError):
        sys.exit(f"Error: this API key does not have access to '{sp.MODEL}'. Details: {e}")
    if isinstance(e, anthropic.RateLimitError):
        sys.exit(f"Error: rate limited by the Anthropic API; try again shortly. Details: {e}")
    if isinstance(e, anthropic.APIStatusError):
        sys.exit(f"Error: Anthropic API error {e.status_code}: {e}")
    if isinstance(e, anthropic.APIConnectionError):
        sys.exit(f"Error: could not connect to the Anthropic API: {e}")
    if isinstance(e, TypeError) and "authentication" in str(e).lower():
        sys.exit("Error: no Anthropic API key found. Set ANTHROPIC_API_KEY in your shell "
                 "(or in a .env file, which Git ignores) and run again.")
    if isinstance(e, TypeError):
        raise e
    sys.exit(f"Error: could not get a reply from Claude: {e}")


def main():
    cli("pipeline", "Supplier-response team, fixed pipeline: analyst -> writers -> reviewer.", run_pipeline)


if __name__ == "__main__":
    main()
