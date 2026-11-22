#!/usr/bin/env python3
"""supply_mcp_server.py - a supply-data MCP server (Model Context Protocol, stdio transport).

It exposes one organization's supply data to the supply analyst as three MCP tools:

    get_part(part_id)             - the part's stock on hand, supplier, scheduled inbound
                                    deliveries, and which products use it (and how many per unit)
    get_orders_for_part(part_id)  - the open customer orders that need the part
    check_coverage(part_id, new_deliveries, replaces_po)
                                  - which orders can be covered on time from stock on hand plus
                                    inbound deliveries, under the current schedule or a changed one

Each organization lives in its own folder under week-05/ (default: brookfield-bikes):

    parts.csv  inbound.csv  orders.csv  bill-of-materials.csv  suppliers.csv
    prompts/          orchestrator.txt analyst.txt supplier-writer.txt customer-writer.txt reviewer.txt
    supplier-emails/  incoming supplier emails (read by pipeline.py / orchestrator.py)
    columns.json      optional: explicit column (and file name) mapping, see COLUMN MAPPING below

All days are whole days counted from today (day 0), as in the CSVs' arrives_in_days and
ship_by_day columns.

COLUMN MAPPING
CSV headers are matched flexibly: each header is lower-cased and non-letters/digits become "_"
("Qty On Hand" -> "qty_on_hand"), then compared with the alias list for each field in
FILE_SPECS below. A folder can also include columns.json to name columns (or files) exactly:

    {"parts": {"file": "stock.csv", "on_hand": "Units In Stock"},
     "orders": {"ship_by_day": "Due (days)"}}

COVERAGE RULES (check_coverage) - assumptions to verify against the lecture
  1. Parts needed by an order = order units x per_unit for that product's row(s) in the bill of
     materials. Orders for products that do not use the part are ignored.
  2. Supply on day d = stock on hand (available from day 0) + every inbound delivery for the part
     arriving on or before day d.
  3. Orders are served in ship-by-day order (earliest first; ties by order_id). Each order claims
     stock only after every earlier order has been fully covered. Late-penalty orders get no
     priority.
  4. An order's ready_day is the first day cumulative supply covers it and every earlier order;
     ready_day is 0 if stock on hand already covers it. There is no assembly or shipping lead time:
     an order can ship on its ready_day.
  5. An order is at risk if ready_day > ship_by_day, or if no scheduled delivery ever covers it
     (ready_day is then null). units_short is the number of the part (not finished products)
     the order is still missing on its ship-by day.
  6. new_deliveries replaces the scheduled inbound deliveries of PO replaces_po (or, if
     replaces_po is omitted, every scheduled delivery of the part). Other parts are not checked:
     an order may also depend on other parts, which this tool does not look at.

Normally the analyst in specialists.py starts this server. To check an org's data by hand:

    python week-05/supply_mcp_server.py --org copperline-coffee --check
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

WEEK_DIR = Path(__file__).resolve().parent
DEFAULT_ORG = "brookfield-bikes"

# For each data file: accepted file names, and for each field (aliases, required, type).
FILE_SPECS = {
    "parts": {
        "files": ["parts.csv", "part.csv", "inventory.csv", "stock.csv", "components.csv"],
        "fields": {
            "part_id": (["part_id", "part", "part_number", "part_no", "partid", "sku",
                         "component_id", "item_id"], True, "str"),
            "description": (["description", "part_name", "part_description", "name", "desc"],
                            False, "str"),
            "on_hand": (["on_hand", "qty_on_hand", "quantity_on_hand", "units_on_hand", "stock",
                         "in_stock", "stock_on_hand", "inventory", "available"], True, "int"),
            "supplier": (["supplier", "supplier_name", "vendor", "vendor_name"], False, "str"),
        },
    },
    "inbound": {
        "files": ["inbound.csv", "inbound-shipments.csv", "purchase-orders.csv",
                  "purchase_orders.csv", "shipments.csv", "deliveries.csv"],
        "fields": {
            "po_number": (["po_number", "po", "po_id", "po_no", "purchase_order",
                           "purchase_order_number"], False, "str"),
            "part_id": (["part_id", "part", "part_number", "part_no", "partid", "sku",
                         "component_id", "item_id"], True, "str"),
            "supplier": (["supplier", "supplier_name", "vendor", "vendor_name"], False, "str"),
            "qty": (["qty", "quantity", "units", "qty_ordered", "quantity_ordered", "qty_due"],
                    True, "int"),
            "arrives_in_days": (["arrives_in_days", "arrival_day", "arrives_day", "eta_days",
                                 "eta_in_days", "days_until_arrival", "due_in_days", "arrives_in",
                                 "eta"], True, "int"),
        },
    },
    "orders": {
        "files": ["orders.csv", "customer-orders.csv", "customer_orders.csv", "open-orders.csv"],
        "fields": {
            "order_id": (["order_id", "order", "order_number", "order_no", "orderid"], True, "str"),
            "customer": (["customer", "customer_name", "client", "client_name", "account",
                          "account_name"], True, "str"),
            "contact_email": (["contact_email", "email", "customer_email", "contact"], False, "str"),
            "product": (["product", "product_name", "model", "product_id", "item"], True, "str"),
            "units": (["units", "qty", "quantity", "units_ordered", "qty_ordered"], True, "int"),
            "ship_by_day": (["ship_by_day", "ship_day", "ship_by", "ship_by_in_days",
                             "ship_in_days", "due_day", "due_in_days"], True, "int"),
            "late_penalty": (["late_penalty", "penalty", "has_late_penalty", "late_fee"],
                             False, "bool"),
        },
    },
    "bom": {
        "files": ["bill-of-materials.csv", "bill_of_materials.csv", "bom.csv"],
        "fields": {
            "product": (["product", "product_name", "model", "product_id", "item"], True, "str"),
            "part_id": (["part_id", "part", "part_number", "part_no", "partid", "sku",
                         "component_id"], True, "str"),
            "per_unit": (["per_unit", "qty_per_unit", "quantity_per_unit", "qty_per",
                          "quantity_per", "units_per", "units_per_product", "qty"], True, "int"),
        },
    },
    "suppliers": {
        "files": ["suppliers.csv", "supplier.csv", "vendors.csv", "supplier-contacts.csv"],
        "fields": {
            "supplier": (["supplier", "supplier_name", "vendor", "vendor_name", "name"], True, "str"),
            "contact_name": (["contact_name", "contact", "rep", "account_manager"], False, "str"),
            "contact_email": (["contact_email", "email", "supplier_email"], False, "str"),
            "part_id": (["part_id", "part", "part_number", "part_no", "partid", "sku"], False, "str"),
        },
    },
}

PROMPT_NAMES = ["orchestrator", "analyst", "supplier-writer", "customer-writer", "reviewer"]
EMAIL_DIR_NAMES = ["supplier-emails", "emails", "sample-emails"]


# ------------------------------------------------------------------ org folder


def resolve_org_dir(org):
    """--org may be a folder name under week-05/ or a path to a folder."""
    path = Path(org)
    if not path.is_absolute() and not path.exists():
        path = WEEK_DIR / org
    return path.resolve()


def find_data_file(org_dir, kind, overrides):
    wanted = (overrides.get(kind) or {}).get("file")
    names = [wanted] if wanted else FILE_SPECS[kind]["files"]
    for name in names:
        if (org_dir / name).is_file():
            return org_dir / name
    return None


def emails_dir_for(org_dir):
    for name in EMAIL_DIR_NAMES:
        if (org_dir / name).is_dir():
            return org_dir / name
    return org_dir / EMAIL_DIR_NAMES[0]


def load_overrides(org_dir):
    path = org_dir / "columns.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"{path.name} is not valid JSON: {e}") from None
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must be a JSON object keyed by file kind")
    return data


def missing_org_files(org_dir):
    """Everything the team needs from an org folder. An empty list means the folder is complete."""
    if not org_dir.is_dir():
        return [f"the folder itself ({org_dir})"]
    problems = []
    try:
        overrides = load_overrides(org_dir)
    except ValueError as e:
        return [str(e)]
    for kind, spec in FILE_SPECS.items():
        if find_data_file(org_dir, kind, overrides) is None:
            name = (overrides.get(kind) or {}).get("file") or spec["files"][0]
            problems.append(f"{name} ({kind} data)")
    for name in PROMPT_NAMES:
        if not (org_dir / "prompts" / f"{name}.txt").is_file():
            problems.append(f"prompts/{name}.txt")
    emails = emails_dir_for(org_dir)
    if not emails.is_dir() or not any(p.is_file() and not p.name.startswith(".")
                                      for p in emails.iterdir()):
        problems.append(f"{emails.name}/ with at least one supplier email")
    return problems


# --------------------------------------------------------------------- CSVs


def _norm(header):
    return re.sub(r"[^a-z0-9]+", "_", str(header).strip().lower()).strip("_")


def _convert(value, kind, field, file_name, row_no):
    value = (value or "").strip()
    if kind == "str":
        return value
    if kind == "bool":
        return value.lower() in {"yes", "y", "true", "t", "1"}
    if value == "":
        raise ValueError(f"{file_name} row {row_no}: '{field}' is empty")
    try:
        number = float(value.replace(",", ""))
    except ValueError:
        raise ValueError(f"{file_name} row {row_no}: '{field}' is not a number: {value!r}") from None
    if number != int(number):
        raise ValueError(f"{file_name} row {row_no}: '{field}' is not a whole number: {value!r}")
    return int(number)


def map_columns(kind, headers, overrides, file_name):
    """Return {field: original header} for one file, or raise ValueError naming what is missing."""
    normalized = {_norm(h): h for h in headers if h is not None}
    explicit = {k: v for k, v in (overrides.get(kind) or {}).items() if k != "file"}
    mapping, missing = {}, []
    for field, (aliases, required, _) in FILE_SPECS[kind]["fields"].items():
        header = None
        if field in explicit:
            header = explicit[field] if explicit[field] in headers else normalized.get(_norm(explicit[field]))
            if header is None:
                raise ValueError(f"columns.json maps {kind}.{field} to {explicit[field]!r}, "
                                 f"but {file_name} has no such column. Headers: {headers}")
        else:
            header = next((normalized[a] for a in aliases if a in normalized), None)
        if header is not None:
            mapping[field] = header
        elif required:
            missing.append(field)
    if missing:
        raise ValueError(f"{file_name}: could not find column(s) {missing} in headers {headers}. "
                         f"Rename them or map them in columns.json.")
    return mapping


def read_table(path, kind, overrides):
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = list(reader.fieldnames or [])
        mapping = map_columns(kind, headers, overrides, path.name)
        rows = []
        for row_no, raw in enumerate(reader, start=2):
            if not any((v or "").strip() for v in raw.values() if isinstance(v, str)):
                continue  # skip blank lines
            row = {}
            for field, (_, _, kind_) in FILE_SPECS[kind]["fields"].items():
                if field in mapping:
                    row[field] = _convert(raw.get(mapping[field]), kind_, field, path.name, row_no)
            rows.append(row)
    return rows, mapping


def yes_no(flag):
    """How every tool reports late_penalty, so the analyst sees one form whichever tool it copies."""
    return "yes" if flag else "no"


class SupplyData:
    """All five tables for one organization, keyed for the tools."""

    def __init__(self, org_dir):
        self.org_dir = Path(org_dir)
        overrides = load_overrides(self.org_dir)
        self.mappings, tables = {}, {}
        for kind in FILE_SPECS:
            path = find_data_file(self.org_dir, kind, overrides)
            if path is None:
                raise ValueError(f"missing {FILE_SPECS[kind]['files'][0]} ({kind} data) in {self.org_dir}")
            tables[kind], mapping = read_table(path, kind, overrides)
            self.mappings[path.name] = mapping
        self.parts = {r["part_id"]: r for r in tables["parts"]}
        self.inbound = tables["inbound"]
        self.orders = tables["orders"]
        self.bom = tables["bom"]
        self.suppliers = tables["suppliers"]
        self.orders_by_id = {o["order_id"]: o for o in self.orders}

    # ---- lookups

    def find_part_id(self, part_id):
        """Exact match first, then case-insensitive."""
        part_id = str(part_id).strip()
        if part_id in self.parts:
            return part_id
        for pid in self.parts:
            if pid.lower() == part_id.lower():
                return pid
        return None

    def per_unit(self, product, part_id):
        return sum(r["per_unit"] for r in self.bom
                   if r["part_id"] == part_id and r["product"].lower() == product.lower())

    def scheduled_deliveries(self, part_id):
        return [dict(r) for r in self.inbound if r["part_id"] == part_id]

    def supplier_contact(self, supplier=None, part_id=None):
        for s in self.suppliers:
            if supplier and s["supplier"].lower() == supplier.lower():
                return s
        for s in self.suppliers:
            if part_id and s.get("part_id") == part_id:
                return s
        return None

    def orders_for_part(self, part_id):
        out = []
        for o in self.orders:
            per = self.per_unit(o["product"], part_id)
            if per:
                out.append({**o, "per_unit": per, "parts_needed": o["units"] * per})
        return sorted(out, key=lambda o: (o["ship_by_day"], o["order_id"]))

    # ---- coverage

    def coverage(self, part_id, deliveries):
        """Apply COVERAGE RULES 1-5 (module docstring) for one part and one delivery schedule."""
        on_hand = self.parts[part_id]["on_hand"]
        arrivals = sorted((int(d["arrives_in_days"]), int(d["qty"])) for d in deliveries)

        def supply_by(day):
            return on_hand + sum(q for a, q in arrivals if a <= day)

        results, demand = [], 0
        for o in self.orders_for_part(part_id):
            demand += o["parts_needed"]  # this order plus every earlier one
            ready = 0 if on_hand >= demand else next(
                (a for a, _ in arrivals if supply_by(a) >= demand), None)
            short = min(o["parts_needed"], max(0, demand - supply_by(o["ship_by_day"])))
            at_risk = ready is None or ready > o["ship_by_day"]
            results.append({
                "order_id": o["order_id"], "customer": o["customer"], "product": o["product"],
                "units": o["units"], "parts_needed": o["parts_needed"],
                "ship_day": o["ship_by_day"], "ready_day": ready,
                "days_late": (None if ready is None else max(0, ready - o["ship_by_day"])),
                "units_short": short, "late_penalty": yes_no(o.get("late_penalty")),
                "at_risk": at_risk,
            })
        return {"on_hand": on_hand,
                "deliveries": [{"arrives_in_days": a, "qty": q} for a, q in arrivals],
                "total_supply": supply_by(float("inf")), "total_needed": demand,
                "orders": results}

    def check_coverage(self, part_id, new_deliveries=None, replaces_po=None):
        pid = self.find_part_id(part_id)
        if pid is None:
            return {"error": f"NOT FOUND: no part {part_id!r}. Known parts: {sorted(self.parts)}"}
        scheduled = self.scheduled_deliveries(pid)
        if new_deliveries is None:
            schedule, note = scheduled, "current schedule (no change applied)"
        else:
            clean = []
            for d in new_deliveries:
                try:
                    qty, day = int(d["qty"]), int(d["arrives_in_days"])
                except (KeyError, TypeError, ValueError):
                    return {"error": f"each new delivery needs whole-number qty and arrives_in_days; got {d!r}"}
                if qty < 0 or day < 0:
                    return {"error": f"qty and arrives_in_days must be 0 or more; got {d!r}"}
                clean.append({"qty": qty, "arrives_in_days": day})
            if replaces_po:
                if not any(r.get("po_number", "").lower() == replaces_po.lower() for r in scheduled):
                    return {"error": f"NOT FOUND: {replaces_po!r} is not a scheduled delivery of {pid}. "
                                     f"Scheduled: {[r.get('po_number') for r in scheduled]}"}
                kept = [r for r in scheduled if r.get("po_number", "").lower() != replaces_po.lower()]
                note = f"{replaces_po} replaced by the new deliveries; other scheduled deliveries kept"
            else:
                kept, note = [], f"every scheduled delivery of {pid} replaced by the new deliveries"
            schedule = kept + clean
        before = self.coverage(pid, scheduled)
        after = self.coverage(pid, schedule)
        risk_before = {o["order_id"] for o in before["orders"] if o["at_risk"]}
        for o in after["orders"]:
            o["at_risk_before_change"] = o["order_id"] in risk_before
        at_risk = [o for o in after["orders"] if o["at_risk"]]
        return {
            "part_id": pid, "schedule_checked": note,
            "on_hand": after["on_hand"], "deliveries": after["deliveries"],
            "total_supply": after["total_supply"], "total_needed": after["total_needed"],
            "orders_at_risk": at_risk,
            "orders_covered_on_time": [o["order_id"] for o in after["orders"] if not o["at_risk"]],
            "notes": ["units_short and parts_needed count parts, not finished products",
                      "ready_day null means no scheduled delivery covers the order",
                      "only this part is checked; days are counted from today (day 0)"],
        }


# ---------------------------------------------------------------- MCP server


def build_server(data):
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP(f"supply-{data.org_dir.name}", log_level="WARNING")

    @mcp.tool()
    def get_part(part_id: str) -> str:
        """Look up one part: stock on hand, supplier and contact, the scheduled inbound deliveries
        (PO number, quantity, arrives_in_days counted from today), and the products that use it
        with the number of parts per product unit."""
        pid = data.find_part_id(part_id)
        if pid is None:
            return f"NOT FOUND: no part {part_id!r}. Known parts: {sorted(data.parts)}"
        part = data.parts[pid]
        used_in = sorted({(r["product"], data.per_unit(r["product"], pid))
                          for r in data.bom if r["part_id"] == pid})
        return json.dumps({
            **part,
            "supplier_contact": data.supplier_contact(part.get("supplier"), pid),
            "scheduled_deliveries": data.scheduled_deliveries(pid),
            "used_in": [{"product": p, "per_unit": n} for p, n in used_in],
        }, indent=2)

    @mcp.tool()
    def get_orders_for_part(part_id: str) -> str:
        """List the open customer orders whose product uses this part, earliest ship-by day first,
        with units ordered, parts per unit, parts needed, ship_by_day (days from today) and
        late_penalty."""
        pid = data.find_part_id(part_id)
        if pid is None:
            return f"NOT FOUND: no part {part_id!r}. Known parts: {sorted(data.parts)}"
        orders = [{**o, "late_penalty": yes_no(o.get("late_penalty"))} for o in data.orders_for_part(pid)]
        return json.dumps({"part_id": pid, "orders": orders}, indent=2)

    @mcp.tool()
    def check_coverage(part_id: str, new_deliveries: list[dict] | None = None,
                       replaces_po: str | None = None) -> str:
        """Work out which orders for this part can ship on time from stock on hand plus inbound
        deliveries. With no new_deliveries, checks the current schedule. To test a change, pass
        new_deliveries as a list of {"qty": int, "arrives_in_days": int} (days from today) and
        replaces_po as the PO they replace (omit it to replace every scheduled delivery of the
        part). Call once per option. Orders are served earliest ship-by day first. Returns each
        order at risk with units_short (parts), ship_day, ready_day and late_penalty."""
        return json.dumps(data.check_coverage(part_id, new_deliveries, replaces_po), indent=2)

    return mcp


def main():
    parser = argparse.ArgumentParser(description="Supply-data MCP server (stdio).")
    parser.add_argument("--org", default=DEFAULT_ORG,
                        help=f"organization folder under week-05/ or a path (default: {DEFAULT_ORG})")
    parser.add_argument("--check", action="store_true",
                        help="load the data, print the column mapping and current coverage, and exit")
    args = parser.parse_args()

    org_dir = resolve_org_dir(args.org)
    problems = missing_org_files(org_dir)
    if problems:
        sys.exit(f"Error: organization folder {org_dir.name} is incomplete. Missing:\n  - "
                 + "\n  - ".join(problems))
    try:
        data = SupplyData(org_dir)
    except ValueError as e:
        sys.exit(f"Error: {e}")

    if args.check:
        for name, mapping in data.mappings.items():
            print(f"{name}: " + ", ".join(f"{k} <- '{v}'" for k, v in mapping.items()))
        for pid in data.parts:
            result = data.check_coverage(pid)
            print(f"{pid}: on hand {result['on_hand']}, deliveries {result['deliveries']}, "
                  f"at risk now: {[o['order_id'] for o in result['orders_at_risk']] or 'none'}")
        return
    build_server(data).run()  # stdio


if __name__ == "__main__":
    main()
