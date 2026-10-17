#!/usr/bin/env python3
"""
Compare the CPLR snapshot embedded in cplr-full-text.html against the live
NY Senate Open Legislation API (law CVP).

Each section in the page carries the "active date" it had when the snapshot
was taken. This script fetches the current law tree, compares section by
section, and writes a Markdown report of anything amended, added, or removed.

Exit codes: 0 = up to date, 1 = changes found (report written), 2 = error.
"""

import json
import os
import re
import sys
import urllib.request

PAGE = "cplr-full-text.html"
API_URL = "https://legislation.nysenate.gov/api/3/laws/CVP?full=true&key={key}"
REPORT = os.environ.get("CPLR_REPORT", "cplr-report.md")
SECTION_URL = "https://www.nysenate.gov/legislation/laws/CVP/{num}"


def load_snapshot():
    with open(PAGE, encoding="utf-8") as f:
        html = f.read()
    m = re.search(r'<script type="application/json" id="cplr-data">(.*?)</script>', html, re.S)
    if not m:
        raise RuntimeError("Could not find the cplr-data block in " + PAGE)
    snapshot = {}
    for art in json.loads(m.group(1)):
        for sec in art["s"]:
            snapshot[sec["n"].upper()] = {"title": sec["t"], "date": sec.get("d") or ""}
    return snapshot


def fetch_live(key):
    req = urllib.request.Request(API_URL.format(key=key), headers={"User-Agent": "cplr-snapshot-check"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.load(resp)
    if not data.get("success"):
        raise RuntimeError("API error: " + str(data.get("message")))
    live = {}

    def walk(node):
        if not isinstance(node, dict):
            return
        if node.get("docType") == "SECTION" and node.get("locationId"):
            live[str(node["locationId"]).upper()] = {
                "title": node.get("title") or "",
                "date": node.get("activeDate") or "",
            }
        children = node.get("documents")
        if isinstance(children, dict):
            children = children.get("items")
        for child in children or []:
            walk(child)

    walk(data.get("result", {}).get("documents"))
    if not live:
        raise RuntimeError("API response contained no sections; the response format may have changed.")
    return live


def sort_key(num):
    m = re.match(r"(\d+)(.*)", num)
    return (int(m.group(1)), m.group(2)) if m else (10**9, num)


def main():
    key = os.environ.get("NYSENATE_API_KEY")
    if not key:
        print("NYSENATE_API_KEY is not set.", file=sys.stderr)
        return 2
    try:
        snapshot = load_snapshot()
        live = fetch_live(key)
    except Exception as e:
        print("Check failed: " + str(e), file=sys.stderr)
        return 2

    amended = sorted((n for n in snapshot.keys() & live.keys()
                      if snapshot[n]["date"] != live[n]["date"]), key=sort_key)
    added = sorted(live.keys() - snapshot.keys(), key=sort_key)
    removed = sorted(snapshot.keys() - live.keys(), key=sort_key)

    print(f"Snapshot: {len(snapshot)} sections. Live: {len(live)} sections.")
    print(f"Amended: {len(amended)}, added: {len(added)}, removed: {len(removed)}.")
    if not (amended or added or removed):
        return 0

    def link(n):
        return f"[§ {n}]({SECTION_URL.format(num=n)})"

    lines = ["The CPLR snapshot in `cplr-full-text.html` no longer matches the NY Senate Open Legislation API.", ""]
    if amended:
        lines += [f"### Amended ({len(amended)})", "", "| Section | Title | Snapshot date | Current date |", "|---|---|---|---|"]
        lines += [f"| {link(n)} | {live[n]['title']} | {snapshot[n]['date']} | {live[n]['date']} |" for n in amended]
        lines.append("")
    if added:
        lines += [f"### New sections ({len(added)})", ""]
        lines += [f"- {link(n)} {live[n]['title']} (active {live[n]['date']})" for n in added]
        lines.append("")
    if removed:
        lines += [f"### No longer in the API ({len(removed)})", ""]
        lines += [f"- § {n} {snapshot[n]['title']}" for n in removed]
        lines.append("")
    lines.append("_This issue is updated automatically by the weekly CPLR check. Close it once the page has been refreshed._")

    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("Report written to " + REPORT)
    return 1


if __name__ == "__main__":
    sys.exit(main())
