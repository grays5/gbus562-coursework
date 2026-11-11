#!/usr/bin/env python3
"""hr_mcp_server.py - an HR MCP server (Model Context Protocol, stdio transport).

It exposes one organization's HR data to an agent as MCP tools:

    search_policy(query, k)          - semantic search over the org's policy documents (Chroma)
    list_policies()                  - names of the policy documents that are indexed
    get_leave_balance(employee_email) - leave balances for the SENDER of the current email only

Each organization lives in its own folder (default: week-04/hartwell-hr) containing:

    hr-docs/         policy documents (.md, .txt, .html, .htm, .pdf); a folder named policies/ also works
    employees.csv    employee roster with an email column and one or more balance columns
    sample-emails/   incoming employee emails (read by agent.py, not by this server)
    system_prompt.txt the agent's system prompt (read by agent.py)

Each organization gets its own Chroma database under week-04/chroma/<org>/, which is
excluded from Git by .gitignore.

Privacy guard: agent.py starts one server process per email and passes the verified
sender address in the HR_SENDER_EMAIL environment variable. get_leave_balance refuses
any address other than that sender, so another employee's balances can never be
returned, no matter what the email (or the model) asks for.

Normally agent.py starts this server for you. To run it by hand:

    HR_SENDER_EMAIL=someone@example.com python week-04/hr_mcp_server.py --org hartwell-hr
    python week-04/hr_mcp_server.py --org hartwell-hr --build-index   # just (re)build Chroma
"""

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

WEEK_DIR = Path(__file__).resolve().parent
DEFAULT_ORG = "hartwell-hr"
CHROMA_ROOT = WEEK_DIR / "chroma"  # excluded from Git by .gitignore
POLICY_EXTENSIONS = {".md", ".txt", ".html", ".htm", ".pdf"}
MAX_CHUNK_CHARS = 1200
DEFAULT_K = 4

# Header keywords used to detect columns in employees.csv.
EMAIL_HEADER_WORDS = ("email", "e-mail", "e_mail", "mail")
BALANCE_HEADER_WORDS = (
    "balance", "remaining", "available", "accrued", "accrual", "left",
    "pto", "vacation", "sick", "personal", "leave", "holiday", "floating",
    "bereavement", "hours", "days",
)
NAME_HEADER_PATTERNS = (
    r"^(full[ _-]?)?name$", r"^employee[ _-]?name$", r"^first[ _-]?name$",
    r"^preferred[ _-]?name$", r"^last[ _-]?name$",
)


# ------------------------------------------------------------ org folders


def resolve_org_dir(org):
    """--org may be a folder name under week-04/ or a path to an org folder."""
    candidate = Path(org)
    if not candidate.is_absolute():
        in_week = WEEK_DIR / org
        candidate = in_week if in_week.exists() else Path.cwd() / org
    return candidate.resolve()


POLICY_FOLDER_NAMES = ("hr-docs", "policies")


def policies_dir_for(org_dir):
    """The org's policy folder: hr-docs/ (as in the course data) or policies/."""
    for name in POLICY_FOLDER_NAMES:
        if (org_dir / name).is_dir():
            return org_dir / name
    return org_dir / POLICY_FOLDER_NAMES[0]


def org_paths(org_dir):
    return {
        "policies": policies_dir_for(org_dir),
        "employees": org_dir / "employees.csv",
        "emails": org_dir / "sample-emails",
        "system_prompt": org_dir / "system_prompt.txt",
    }


def missing_org_files(org_dir):
    """Return a list of human-readable problems with an organization folder."""
    p = org_paths(org_dir)
    problems = []
    if not org_dir.is_dir():
        return [f"organization folder {org_dir}"]
    if not p["policies"].is_dir() or not list_policy_files(p["policies"]):
        problems.append(f"policy documents in {p['policies']} ({', '.join(sorted(POLICY_EXTENSIONS))})")
    if not p["employees"].is_file():
        problems.append(f"{p['employees']}")
    if not p["emails"].is_dir() or not [f for f in p["emails"].iterdir() if f.is_file() and not f.name.startswith(".")]:
        problems.append(f"email files in {p['emails']}")
    if not p["system_prompt"].is_file() or not p["system_prompt"].read_text(encoding="utf-8").strip():
        problems.append(f"{p['system_prompt']}")
    return problems


# -------------------------------------------------------------- employees


def _norm(header):
    return header.strip().lower()


def detect_columns(headers):
    """Detect the email column, the balance columns and a name column from CSV headers."""
    email_candidates = [h for h in headers if any(w in _norm(h) for w in EMAIL_HEADER_WORDS)]
    # Prefer the employee's own address over e.g. manager_email / supervisor_email.
    email_candidates.sort(key=lambda h: (
        _norm(h) not in {"email", "e-mail", "email address", "email_address", "work email", "work_email"},
        any(w in _norm(h) for w in ("manager", "supervisor", "personal", "backup")),
    ))
    email_col = email_candidates[0] if email_candidates else None
    name_cols = [h for h in headers if any(re.match(p, _norm(h)) for p in NAME_HEADER_PATTERNS)]
    balance_cols = [
        h for h in headers
        if h != email_col and h not in name_cols
        and any(w in _norm(h) for w in BALANCE_HEADER_WORDS)
    ]
    return email_col, balance_cols, name_cols


def _mostly_numeric(values):
    filled = [str(v).strip().replace(",", "") for v in values if v is not None and str(v).strip()]
    if not filled:
        return False
    numeric = sum(bool(re.fullmatch(r"-?\d+(\.\d+)?( ?(h|hrs?|hours?|d|days?))?", v.lower())) for v in filled)
    return numeric >= 0.8 * len(filled)


def load_employees(csv_path):
    """Return (rows_by_email, email_col, balance_cols, name_cols)."""
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        email_col, balance_cols, name_cols = detect_columns(headers)
        if email_col is None:
            raise ValueError(f"no email column found in {csv_path.name} headers: {headers}")
        rows = {}
        for row in reader:
            email = (row.get(email_col) or "").strip().lower()
            if email:
                rows[email] = row
        # Keep only balance columns whose filled-in values are numbers (drops e.g. "leave_type").
        balance_cols = [c for c in balance_cols if _mostly_numeric(r.get(c) for r in rows.values())]
        if not balance_cols:
            raise ValueError(f"no numeric balance columns found in {csv_path.name} headers: {headers}")
    return rows, email_col, balance_cols, name_cols


# --------------------------------------------------------------- policies


class _HTMLText(HTMLParser):
    BLOCK_TAGS = {"p", "li", "h1", "h2", "h3", "h4", "tr", "br", "div", "title"}
    SKIP_TAGS = {"style", "script"}

    def __init__(self):
        super().__init__()
        self.parts, self._skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self._skip += 1
        elif tag in self.BLOCK_TAGS:
            self.parts.append("\n\n" if tag.startswith("h") or tag == "p" else "\n")
            if tag in {"h1", "h2", "h3", "h4"}:
                self.parts.append("# ")

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS:
            self._skip = max(0, self._skip - 1)

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def read_policy_text(path):
    suffix = path.suffix.lower()
    if suffix in {".html", ".htm"}:
        parser = _HTMLText()
        parser.feed(path.read_text(encoding="utf-8"))
        return re.sub(r"[ \t]+", " ", "".join(parser.parts))
    if suffix == ".pdf":
        from pypdf import PdfReader
        return "\n\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    return path.read_text(encoding="utf-8")


def chunk_text(text, source):
    """Split by headings / blank-line paragraphs into chunks of about MAX_CHUNK_CHARS."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, current, heading = [], "", ""
    for p in paragraphs:
        if p.startswith("#"):
            heading = p.lstrip("# ").splitlines()[0]
        if current and len(current) + len(p) + 2 > MAX_CHUNK_CHARS:
            chunks.append(current)
            current = f"(continued: {heading})\n{p}" if heading else p
        else:
            current = f"{current}\n\n{p}" if current else p
    if current:
        chunks.append(current)
    out = []
    for c in chunks:  # hard-split anything still too long
        out.extend(c[i:i + MAX_CHUNK_CHARS * 2] for i in range(0, len(c), MAX_CHUNK_CHARS * 2))
    return [f"Source: {source}\n{c}" for c in out]


def list_policy_files(policies_dir):
    if not policies_dir.is_dir():
        return []
    return sorted(
        p for p in policies_dir.rglob("*")
        if p.is_file() and not p.name.startswith(".") and p.suffix.lower() in POLICY_EXTENSIONS
    )


def _fingerprint(files, root):
    h = hashlib.sha256()
    for path in files:
        h.update(str(path.relative_to(root)).encode("utf-8"))
        h.update(hashlib.sha256(path.read_bytes()).digest())
    return h.hexdigest()


def chroma_dir_for(org_dir):
    """A separate Chroma database for each organization."""
    return CHROMA_ROOT / org_dir.name


def get_policy_collection(org_dir, force_rebuild=False):
    """Open the org's Chroma collection, rebuilding it if the policy files changed."""
    import chromadb

    policies_dir = org_paths(org_dir)["policies"]
    files = list_policy_files(policies_dir)
    if not files:
        raise FileNotFoundError(f"no policy documents found in {policies_dir}")
    db_dir = chroma_dir_for(org_dir)
    state_file = db_dir / "index-state.json"
    current = _fingerprint(files, policies_dir)
    stale = True
    if state_file.exists() and not force_rebuild:
        state = json.loads(state_file.read_text(encoding="utf-8"))
        stale = state.get("fingerprint") != current or state.get("org_dir") != str(org_dir)
    if stale and db_dir.exists():
        shutil.rmtree(db_dir)
    db_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(db_dir))
    collection = client.get_or_create_collection(name="policies", metadata={"hnsw:space": "cosine"})
    if stale:
        ids, docs, metas = [], [], []
        for path in files:
            rel = str(path.relative_to(policies_dir))
            for i, chunk in enumerate(chunk_text(read_policy_text(path), rel)):
                ids.append(f"{rel}::{i}")
                docs.append(chunk)
                metas.append({"source": rel, "chunk": i})
        if not ids:
            raise ValueError(f"policy documents in {policies_dir} contained no text")
        collection.add(ids=ids, documents=docs, metadatas=metas)
        state_file.write_text(json.dumps({
            "fingerprint": current,
            "org_dir": str(org_dir),
            "files": [str(p.relative_to(policies_dir)) for p in files],
            "chunks": len(ids),
            "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }, indent=2), encoding="utf-8")
        print(f"(Built Chroma database for {org_dir.name}: {len(ids)} chunks from {len(files)} files)",
              file=sys.stderr)
    return collection, db_dir


# ------------------------------------------------------------- MCP server


def build_server(org_dir, sender_email):
    from mcp.server.fastmcp import FastMCP

    paths = org_paths(org_dir)
    collection, _ = get_policy_collection(org_dir)
    employees, email_col, balance_cols, name_cols = load_employees(paths["employees"])
    sender = (sender_email or "").strip().lower()

    mcp = FastMCP(f"hr-{org_dir.name}", log_level="WARNING")

    @mcp.tool()
    def search_policy(query: str, k: int = DEFAULT_K) -> str:
        """Search this organization's HR policy documents. Returns the most relevant
        excerpts, each labelled with its source file. Use it before stating any policy."""
        k = max(1, min(int(k), 8, collection.count()))
        res = collection.query(query_texts=[query], n_results=k)
        lines = []
        for rank, (doc, meta, dist) in enumerate(
            zip(res["documents"][0], res["metadatas"][0], res["distances"][0]), start=1
        ):
            lines.append(f'<excerpt rank="{rank}" source="{meta["source"]}" similarity="{1 - dist:.3f}">\n'
                         f"{doc}\n</excerpt>")
        return "\n\n".join(lines) if lines else "No matching policy excerpts."

    @mcp.tool()
    def list_policies() -> str:
        """List the policy documents available for this organization."""
        return "\n".join(str(p.relative_to(paths["policies"])) for p in list_policy_files(paths["policies"]))

    @mcp.tool()
    def get_leave_balance(employee_email: str) -> str:
        """Get leave/PTO balances for the employee who SENT the current email.
        Only the sender's own address is allowed; any other address is refused."""
        requested = (employee_email or "").strip().lower()
        if not sender:
            return "ACCESS DENIED: the sender of this email could not be verified."
        if requested != sender:
            return ("ACCESS DENIED: balances can only be shared with the employee who sent the email "
                    f"({sender}). Requests about other employees must go to a human HR reviewer.")
        row = employees.get(sender)
        if row is None:
            return f"NOT FOUND: {sender} is not in the employee roster. A human HR reviewer must handle this."
        result = {col: (row.get(col) or "").strip() for col in balance_cols}
        name = " ".join((row.get(c) or "").strip() for c in name_cols if (row.get(c) or "").strip())
        return json.dumps({"employee_email": sender, "name": name or None, "balances": result}, indent=2)

    return mcp


def main():
    parser = argparse.ArgumentParser(description="HR MCP server for one organization (stdio).")
    parser.add_argument("--org", default=DEFAULT_ORG, help=f"organization folder (default: {DEFAULT_ORG})")
    parser.add_argument("--build-index", action="store_true", help="build/refresh the Chroma database and exit")
    parser.add_argument("--rebuild", action="store_true", help="force the Chroma database to be rebuilt")
    args = parser.parse_args()

    org_dir = resolve_org_dir(args.org)
    if args.build_index or args.rebuild:
        collection, db_dir = get_policy_collection(org_dir, force_rebuild=args.rebuild)
        print(f"Chroma database for {org_dir.name}: {db_dir} ({collection.count()} chunks)", file=sys.stderr)
        return
    server = build_server(org_dir, os.environ.get("HR_SENDER_EMAIL", ""))
    server.run(transport="stdio")  # stdout carries MCP messages; logs go to stderr


if __name__ == "__main__":
    main()
