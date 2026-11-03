#!/usr/bin/env python3
"""ask.py - a small RAG (retrieval-augmented generation) tool.

It indexes a folder of documents into a local Chroma vector database,
retrieves the chunks most similar to a question, and asks Claude to answer
using only those chunks, citing its sources.

Usage (from the repository root, with the virtual environment active):

    python week-03/ask.py "What is the overdraft fee?"
    python week-03/ask.py --docs week-03/larkfield-docs "What is the overdraft fee?"
    python week-03/ask.py --docs week-03/larkfield-docs --save week-03/runs/q1.txt "..."

The Anthropic API key is read from the ANTHROPIC_API_KEY environment variable
(or a .env file, which is excluded from Git). It is never written to disk.
"""

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import anthropic
import chromadb
from dotenv import load_dotenv

MODEL = "claude-sonnet-5"  # required by the course; never silently replaced
WEEK_DIR = Path(__file__).resolve().parent
DEFAULT_DOCS = WEEK_DIR / "copperline-docs"
CHROMA_ROOT = WEEK_DIR / "chroma"  # excluded from Git by .gitignore
DOC_EXTENSIONS = {".html", ".htm", ".txt", ".md"}
TOP_K = 5
MAX_CHUNK_CHARS = 1200

SYSTEM_PROMPT = """You answer questions for staff using only the numbered document \
excerpts provided. Rules:
- Use only facts stated in the excerpts. Do not use outside knowledge.
- Cite every factual statement with the excerpt number(s) and source file, \
for example [1: consumer-fee-schedule.html].
- If the excerpts disagree (for example, two versions of the same document), \
say so, state which version each figure comes from, and explain which one \
appears to be current based on the excerpts.
- If the excerpts do not contain the answer, say that the documents provided \
do not answer the question instead of guessing.
- Keep the answer concise and in plain text."""


# ---------------------------------------------------------------- loading


class _HTMLBlocks(HTMLParser):
    """Collects (tag, text) blocks from an HTML page, skipping style/script."""

    BLOCK_TAGS = {"title", "h1", "h2", "h3", "h4", "p", "li", "td", "th"}
    SKIP_TAGS = {"style", "script", "footer", "nav"}

    def __init__(self):
        super().__init__()
        self.blocks = []
        self._tag = None
        self._buf = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self._skip += 1
        elif tag in self.BLOCK_TAGS and not self._skip:
            self._flush()
            self._tag = tag

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS:
            self._skip = max(0, self._skip - 1)
        elif tag in self.BLOCK_TAGS and tag == self._tag:
            self._flush()

    def handle_data(self, data):
        if self._tag and not self._skip:
            self._buf.append(data)

    def _flush(self):
        text = " ".join("".join(self._buf).split())
        if self._tag and text:
            self.blocks.append((self._tag, text))
        self._tag, self._buf = None, []


def _split_long(text, limit=MAX_CHUNK_CHARS):
    """Split text that is too long into pieces at paragraph/sentence breaks."""
    if len(text) <= limit:
        return [text]
    pieces, current = [], ""
    for part in text.replace(". ", ".\n").split("\n"):
        if current and len(current) + len(part) + 1 > limit:
            pieces.append(current.strip())
            current = ""
        current += part + " "
    if current.strip():
        pieces.append(current.strip())
    return pieces


def chunk_html(raw):
    """One chunk per <h2> section, each prefixed with the document title."""
    parser = _HTMLBlocks()
    parser.feed(raw)
    parser.close()
    title = next((t for tag, t in parser.blocks if tag == "title"), "")
    chunks, heading, body, preamble = [], None, [], []
    for tag, text in parser.blocks:
        if tag == "title":
            continue
        if tag == "h2":
            if heading is not None:
                chunks.append((heading, body))
            heading, body = text, []
        elif heading is None:
            preamble.append(text)  # h1 and version line before first section
        else:
            body.append(("- " if tag == "li" else "") + text)
    if heading is not None:
        chunks.append((heading, body))
    header = title or " ".join(preamble[:1])
    meta = " ".join(preamble[1:])  # e.g. "Version 8 (current). Replaces Version 7."
    out = []
    for sec_heading, sec_body in chunks:
        text = "\n".join(sec_body)
        for piece in _split_long(text):
            prefix = f"{header}\n{meta}\n" if meta else f"{header}\n"
            out.append(f"{prefix}Section: {sec_heading}\n{piece}")
    if not out and preamble:
        out.append("\n".join(preamble))
    return out


def chunk_text(raw, name):
    """Chunk plain text / Markdown by blank-line paragraphs, ~MAX_CHUNK_CHARS."""
    paragraphs = [p.strip() for p in raw.split("\n\n") if p.strip()]
    out, current = [], ""
    for p in paragraphs:
        if current and len(current) + len(p) + 2 > MAX_CHUNK_CHARS:
            out.append(current)
            current = ""
        current = f"{current}\n\n{p}" if current else p
    if current:
        out.append(current)
    return [f"{name}\n{c}" for piece in out for c in _split_long(piece)]


def list_documents(docs_dir):
    return sorted(
        p for p in docs_dir.iterdir()
        if p.is_file() and not p.name.startswith(".") and p.suffix.lower() in DOC_EXTENSIONS
    )


def load_chunks(docs_dir):
    ids, texts, metas = [], [], []
    for path in list_documents(docs_dir):
        raw = path.read_text(encoding="utf-8")
        if path.suffix.lower() in {".html", ".htm"}:
            chunks = chunk_html(raw)
        else:
            chunks = chunk_text(raw, path.name)
        for i, chunk in enumerate(chunks):
            ids.append(f"{path.name}::{i}")
            texts.append(chunk)
            metas.append({"source": path.name, "chunk": i})
    return ids, texts, metas


# --------------------------------------------------------------- database


def fingerprint(docs_dir):
    """Hash of file names and contents, so any added/removed/edited doc triggers a rebuild."""
    h = hashlib.sha256()
    for path in list_documents(docs_dir):
        h.update(path.name.encode("utf-8"))
        h.update(hashlib.sha256(path.read_bytes()).digest())
    return h.hexdigest()


def db_dir_for(docs_dir):
    """A separate Chroma database per document folder."""
    tag = hashlib.sha256(str(docs_dir).encode("utf-8")).hexdigest()[:8]
    return CHROMA_ROOT / f"{docs_dir.name}-{tag}"


def get_collection(docs_dir, force_rebuild=False):
    db_dir = db_dir_for(docs_dir)
    state_file = db_dir / "index-state.json"
    current = fingerprint(docs_dir)
    stale = True
    if db_dir.exists() and state_file.exists() and not force_rebuild:
        stale = json.loads(state_file.read_text(encoding="utf-8")).get("fingerprint") != current
    if stale and db_dir.exists():
        shutil.rmtree(db_dir)
    db_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(db_dir))
    collection = client.get_or_create_collection(
        name="docs", metadata={"hnsw:space": "cosine"}
    )
    rebuilt = False
    if stale:
        ids, texts, metas = load_chunks(docs_dir)
        if not ids:
            raise SystemExit(f"Error: no documents ({', '.join(sorted(DOC_EXTENSIONS))}) found in {docs_dir}")
        collection.add(ids=ids, documents=texts, metadatas=metas)
        state = {
            "fingerprint": current,
            "docs_dir": str(docs_dir),
            "files": [p.name for p in list_documents(docs_dir)],
            "chunks": len(ids),
            "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
        rebuilt = True
    return collection, db_dir, rebuilt


def retrieve(collection, question, k=TOP_K):
    res = collection.query(query_texts=[question], n_results=min(k, collection.count()))
    hits = []
    for rank, (doc, meta, dist) in enumerate(
        zip(res["documents"][0], res["metadatas"][0], res["distances"][0]), start=1
    ):
        hits.append({"rank": rank, "similarity": 1.0 - dist, "source": meta["source"], "text": doc})
    return hits


# ------------------------------------------------------------------ answer


def ask_claude(question, hits):
    excerpts = "\n\n".join(
        f"<excerpt number=\"{h['rank']}\" source=\"{h['source']}\">\n{h['text']}\n</excerpt>"
        for h in hits
    )
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Document excerpts:\n\n{excerpts}\n\nQuestion: {question}",
        }],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("the model declined to answer this request (stop_reason=refusal)")
    answer = "".join(b.text for b in response.content if b.type == "text").strip()
    return answer, response.model


def format_run(question, docs_dir, db_dir, hits, answer, served_model):
    lines = [
        "RAG RUN",
        f"Question: {question}",
        f"Documents folder: {docs_dir}",
        f"Documents indexed: {', '.join(p.name for p in list_documents(docs_dir))}",
        f"Chroma database: {db_dir}",
        f"Model requested: {MODEL}",
        f"Model that answered: {served_model}",
        f"Run time (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        f"RETRIEVED CHUNKS (top {len(hits)}, cosine similarity)",
        "",
    ]
    for h in hits:
        lines.append(f"[{h['rank']}] Rank: {h['rank']} | Similarity: {h['similarity']:.4f} | Source: {h['source']}")
        lines.append(h["text"])
        lines.append("")
    lines.append("ANSWER")
    lines.append(answer)
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Ask a question about a folder of documents (RAG with Chroma + Claude).")
    parser.add_argument("question", help="the question to ask, in quotes")
    parser.add_argument("--docs", default=str(DEFAULT_DOCS),
                        help=f"folder of documents to search (default: {DEFAULT_DOCS.relative_to(WEEK_DIR.parent)})")
    parser.add_argument("--save", metavar="FILE", help="also save the complete run output to FILE (UTF-8)")
    parser.add_argument("--k", type=int, default=TOP_K, help=f"number of chunks to retrieve (default {TOP_K})")
    parser.add_argument("--rebuild", action="store_true", help="force the Chroma database to be rebuilt")
    args = parser.parse_args()

    load_dotenv(WEEK_DIR.parent / ".env")
    load_dotenv(WEEK_DIR / ".env")

    docs_dir = Path(args.docs).resolve()
    if not docs_dir.is_dir():
        sys.exit(f"Error: documents folder not found: {docs_dir}")
    if not list_documents(docs_dir):
        sys.exit(f"Error: no documents ({', '.join(sorted(DOC_EXTENSIONS))}) found in {docs_dir}")

    collection, db_dir, rebuilt = get_collection(docs_dir, force_rebuild=args.rebuild)
    if rebuilt:
        print(f"(Built Chroma database for {docs_dir.name}: {collection.count()} chunks)", file=sys.stderr)
    hits = retrieve(collection, args.question, args.k)

    try:
        answer, served_model = ask_claude(args.question, hits)
    except anthropic.NotFoundError as e:
        sys.exit(f"Error: model '{MODEL}' was not found or is not available to this API key. "
                 f"No other model was substituted. Details: {e}")
    except anthropic.AuthenticationError as e:
        sys.exit(f"Error: the Anthropic API rejected the API key. Check ANTHROPIC_API_KEY. Details: {e}")
    except anthropic.PermissionDeniedError as e:
        sys.exit(f"Error: this API key does not have access to '{MODEL}'. Details: {e}")
    except anthropic.RateLimitError as e:
        sys.exit(f"Error: rate limited by the Anthropic API; try again shortly. Details: {e}")
    except anthropic.APIStatusError as e:
        sys.exit(f"Error: Anthropic API error {e.status_code}: {e}")
    except anthropic.APIConnectionError as e:
        sys.exit(f"Error: could not connect to the Anthropic API: {e}")
    except (anthropic.AnthropicError, TypeError, RuntimeError) as e:
        # e.g. no API key configured at all
        sys.exit(f"Error: could not get an answer from Claude: {e}")

    output = format_run(args.question, docs_dir, db_dir, hits, answer, served_model)
    sys.stdout.write(output)
    if args.save:
        save_path = Path(args.save)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text(output, encoding="utf-8")
        print(f"(Saved run to {save_path})", file=sys.stderr)


if __name__ == "__main__":
    main()
