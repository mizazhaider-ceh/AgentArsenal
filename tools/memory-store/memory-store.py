#!/usr/bin/env python3
"""memory-store: a small SQLite memory store for agents.

Three memory kinds: episodic (what happened), semantic (facts that stay
true), procedural (how-to knowledge). Stdlib only.

Usage:
    memory-store.py store --kind episodic --agent NAME --text "..." \
        [--confidence 0-1] [--ttl-days N] [--tags a,b]
    memory-store.py recall --query "..." [--kind K] [--limit N] \
        [--agent NAME] [--tags a,b]
    memory-store.py consolidate [--dry-run]
    memory-store.py forget --id ID [--id ID ...] | --expired
    memory-store.py stats

The database path comes from the MEMORY_STORE_DB environment variable,
defaulting to ~/.memory-store/memory.db.
"""

import argparse
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone

KINDS = ("episodic", "semantic", "procedural")
DEFAULT_TTL = {"episodic": 30, "semantic": 365, "procedural": 730}
SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    text TEXT NOT NULL,
    source_agent TEXT NOT NULL,
    confidence REAL NOT NULL,
    ttl_days INTEGER,
    tags TEXT,
    created_at TEXT NOT NULL,
    expires_at TEXT,
    merged_from TEXT
);
"""

TOKEN_RE = re.compile(r"[a-z0-9]+")


class UsageError(Exception):
    """A usage problem: reported to stderr, exit code 2."""


def db_path():
    return os.path.expanduser(
        os.environ.get("MEMORY_STORE_DB", "~/.memory-store/memory.db"))


def connect():
    path = db_path()
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(SCHEMA)
    return conn


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def norm_tags(tags):
    if not tags:
        return ""
    return ",".join(t.strip().lower() for t in tags.split(",") if t.strip())


def cmd_store(args):
    if args.kind not in KINDS:
        raise UsageError("--kind must be one of: %s" % ", ".join(KINDS))
    if not (0.0 <= args.confidence <= 1.0):
        raise UsageError("--confidence must be between 0 and 1")
    if not args.text.strip():
        raise UsageError("--text must not be empty")
    ttl = args.ttl_days if args.ttl_days is not None else DEFAULT_TTL[args.kind]
    created = now_iso()
    expires = None
    if ttl and ttl > 0:
        expires = (datetime.now(timezone.utc) + timedelta(days=ttl)
                   ).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn = connect()
    cur = conn.execute(
        "INSERT INTO memories (kind, text, source_agent, confidence,"
        " ttl_days, tags, created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (args.kind, args.text.strip(), args.agent, args.confidence,
         ttl, norm_tags(args.tags), created, expires))
    conn.commit()
    print("stored id %d (%s)" % (cur.lastrowid, args.kind))
    conn.close()
    return 0


def tokens(text):
    return set(TOKEN_RE.findall(text.lower()))


def cmd_recall(args):
    if args.kind and args.kind not in KINDS:
        raise UsageError("--kind must be one of: %s" % ", ".join(KINDS))
    conn = connect()
    query = ("SELECT id, kind, text, source_agent, confidence, tags, created_at"
             " FROM memories WHERE (expires_at IS NULL OR expires_at > ?)")
    params = [now_iso()]
    if args.kind:
        query += " AND kind = ?"
        params.append(args.kind)
    if args.agent:
        query += " AND source_agent = ?"
        params.append(args.agent)
    rows = conn.execute(query, params).fetchall()
    conn.close()

    qtokens = tokens(args.query)
    if args.tags:
        wanted = {t.strip().lower() for t in args.tags.split(",") if t.strip()}
        rows = [r for r in rows
                if wanted & {t.strip() for t in (r[5] or "").split(",")}]

    scored = []
    for row in rows:
        hit = len(qtokens & tokens(row[2]))
        if qtokens and hit == 0:
            continue
        scored.append((hit, row[4], row[6], row))
    scored.sort(key=lambda s: (s[0], s[1], s[2]), reverse=True)
    results = [s[3] for s in scored[:args.limit]]
    if not results:
        print("no matching memories")
        return 0
    for rid, kind, text, agent, conf, tags, created in results:
        print("id: %d  kind: %s  agent: %s  confidence: %.2f"
              % (rid, kind, agent, conf))
        print("  created: %s  tags: %s" % (created, tags or "-"))
        print("  %s" % text)
        print("")
    return 0


def jaccard(a, b):
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def cmd_consolidate(args):
    conn = connect()
    rows = conn.execute(
        "SELECT id, kind, source_agent, text, confidence, created_at"
        " FROM memories ORDER BY created_at").fetchall()
    merged = 0
    skipped = 0
    removed = set()
    for i, (rid, kind, agent, text, conf, _) in enumerate(rows):
        if rid in removed:
            continue
        for j in range(i + 1, len(rows)):
            r2id, r2kind, r2agent, r2text, r2conf, _ = rows[j]
            if r2id in removed or r2kind != kind:
                continue
            if jaccard(text, r2text) >= 0.75:
                if args.dry_run:
                    print("would merge id %d into id %d" % (r2id, rid))
                else:
                    conn.execute(
                        "UPDATE memories SET confidence = MAX(confidence, ?),"
                        " merged_from = COALESCE(merged_from || ',', '') || ?"
                        " WHERE id = ?",
                        (r2conf, str(r2id), rid))
                    conn.execute("DELETE FROM memories WHERE id = ?", (r2id,))
                    removed.add(r2id)
                    print("merged id %d into id %d" % (r2id, rid))
                merged += 1
    if not args.dry_run:
        conn.commit()
    print("%s %d duplicate entr%s (%d merge candidate group%s checked)"
          % ("would merge" if args.dry_run else "merged", merged,
             "y" if merged == 1 else "ies", len(rows),
             "" if len(rows) == 1 else "s"))
    conn.close()
    return 0


def cmd_forget(args):
    if not args.id and not args.expired:
        raise UsageError("forget needs --id ID ... or --expired")
    conn = connect()
    total = 0
    if args.id:
        for rid in args.id:
            cur = conn.execute("DELETE FROM memories WHERE id = ?", (rid,))
            total += cur.rowcount
            note = (" reason: %s" % args.reason) if args.reason else ""
            print("deleted id %d (%d row%s)%s" % (rid, cur.rowcount,
                                                "" if cur.rowcount == 1 else "s",
                                                note))
    if args.expired:
        cur = conn.execute(
            "DELETE FROM memories WHERE expires_at IS NOT NULL"
            " AND expires_at <= ?", (now_iso(),))
        total += cur.rowcount
        print("deleted %d expired entr%s" % (cur.rowcount,
                                             "y" if cur.rowcount == 1 else "ies"))
    conn.commit()
    conn.close()
    return 0


def cmd_stats(args):
    conn = connect()
    total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    per_kind = conn.execute(
        "SELECT kind, COUNT(*) FROM memories GROUP BY kind").fetchall()
    expired = conn.execute(
        "SELECT COUNT(*) FROM memories WHERE expires_at IS NOT NULL"
        " AND expires_at <= ?", (now_iso(),)).fetchone()[0]
    avg_conf = conn.execute(
        "SELECT AVG(confidence) FROM memories").fetchone()[0]
    agents = conn.execute(
        "SELECT source_agent, COUNT(*) FROM memories GROUP BY source_agent"
        " ORDER BY COUNT(*) DESC LIMIT 5").fetchall()
    conn.close()
    print("total entries: %d" % total)
    for kind, count in per_kind:
        print("  %s: %d" % (kind, count))
    print("expired (pending cleanup): %d" % expired)
    print("average confidence: %.2f" % (avg_conf or 0.0))
    print("top agents:")
    for agent, count in agents:
        print("  %s: %d" % (agent, count))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="memory-store.py",
        description="SQLite memory store for agents: capture, recall,"
                    " consolidate, forget, stats.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("store", aliases=["capture"],
                       help="record a new memory entry")
    p.add_argument("--kind", required=True, choices=KINDS,
                   help="memory kind")
    p.add_argument("--agent", required=True,
                   help="name of the agent recording the entry")
    p.add_argument("--text", required=True, help="the memory content")
    p.add_argument("--confidence", type=float, default=0.7,
                   help="0.0 to 1.0 (default: 0.7)")
    p.add_argument("--ttl-days", type=int, default=None,
                   help="days until expiry (default: 30/365/730 by kind)")
    p.add_argument("--tags", default="", help="comma separated tags")
    p.set_defaults(func=cmd_store)

    p = sub.add_parser("recall", help="search stored memories")
    p.add_argument("--query", required=True, help="2-4 keywords work best")
    p.add_argument("--kind", choices=KINDS, help="restrict to one kind")
    p.add_argument("--limit", type=int, default=10,
                   help="max results (default: 10)")
    p.add_argument("--agent", help="restrict to one agent")
    p.add_argument("--tags", help="comma separated tags to filter by")
    p.set_defaults(func=cmd_recall)

    p = sub.add_parser("consolidate",
                       help="merge near-duplicate entries")
    p.add_argument("--dry-run", action="store_true",
                   help="show what would merge without changing anything")
    p.set_defaults(func=cmd_consolidate)

    p = sub.add_parser("forget", help="delete entries by id or expiry")
    p.add_argument("--id", type=int, action="append", default=[],
                   help="entry id to delete (repeatable)")
    p.add_argument("--expired", action="store_true",
                   help="delete all expired entries")
    p.add_argument("--reason", default="",
                   help="why the entry is being deleted (audit note)")
    p.set_defaults(func=cmd_forget)

    p = sub.add_parser("stats", help="show store statistics")
    p.set_defaults(func=cmd_stats)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except UsageError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    sys.exit(main())
