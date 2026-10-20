#!/usr/bin/env python3
"""
Pull the NJ Rules of Court (Parts I-VI, the parts that govern the Superior
Court) from the Judiciary's rules-of-court data endpoints on njcourts.gov and
embed them in nj-court-rules.html.

Usage:
  python3 .github/scripts/build-nj-rules.py                # rebuild the page (about an hour: requests are rate-limited)
  python3 .github/scripts/build-nj-rules.py --check        # full compare, no write; exit 1 if any rule changed
  python3 .github/scripts/build-nj-rules.py --check-date   # one request: has the "amendments through" date moved?

The njcourts.gov site rejects requests that don't look like a browser, so
requests carry browser-style headers.
"""

import datetime
import html
import json
import os
import re
import sys
import time
import urllib.request
from html.parser import HTMLParser

PAGE = "nj-court-rules.html"
BASE = "https://www.njcourts.gov"
API = BASE + "/njcourts_rules_of_court/"
PARTS = ["Part 1", "Part 2", "Part 3", "Part 4", "Part 5", "Part 6"]
REPORT = os.environ.get("NJ_RULES_REPORT", "nj-rules-report.md")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": BASE + "/attorneys/rules-of-court",
}
MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"


DELAY = float(os.environ.get("NJ_RULES_DELAY", "1.5"))   # seconds between requests; the site rate-limits
CACHE = os.environ.get("NJ_RULES_CACHE")                   # optional dir: saves responses so an interrupted run can resume


class Blocked(Exception):
    pass


def get(url, as_json=True):
    cache_file = None
    if CACHE:
        os.makedirs(CACHE, exist_ok=True)
        cache_file = os.path.join(CACHE, re.sub(r"[^A-Za-z0-9]+", "_", url[len(BASE):]) + ".txt")
        if os.path.exists(cache_file):
            with open(cache_file, encoding="utf-8") as f:
                body = f.read()
            return json.loads(body) if as_json else body
    for attempt in range(3):
        time.sleep(DELAY)
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read().decode("utf-8")
        except Exception:
            if attempt == 2:
                raise
            time.sleep(10 * (attempt + 1))
            continue
        if "Pardon Our Interruption" in body:
            raise Blocked("njcourts.gov bot protection blocked the request; try again later or raise NJ_RULES_DELAY.")
        result = json.loads(body) if as_json else body
        if cache_file:
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(body)
        return result


class TextExtractor(HTMLParser):
    """Turn the rule HTML into plain text, one paragraph per block element."""
    BLOCKS = {"p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "table", "ul", "ol"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in self.BLOCKS:
            self.parts.append("\n\n")
        elif tag == "br":
            self.parts.append("\n")
        elif tag in ("td", "th"):
            self.parts.append("\t")

    def handle_endtag(self, tag):
        if tag in self.BLOCKS:
            self.parts.append("\n\n")

    def handle_data(self, data):
        self.parts.append(data)

    def text(self):
        s = "".join(self.parts).replace("\xa0", " ")
        s = re.sub(r"[ \t]+", " ", s)
        s = re.sub(r" *\n *", "\n", s)
        s = re.sub(r"\n{3,}", "\n\n", s)
        return s.strip()


def html_to_text(fragment):
    p = TextExtractor()
    p.feed(fragment or "")
    return p.text()


def split_note(text):
    """Separate the trailing 'Note: Source-...' history paragraph from the rule text."""
    m = re.search(r"\n\nNote:\s*(.*)$", "\n\n" + text, re.S)
    if not m:
        return text, ""
    body = ("\n\n" + text)[: m.start()].strip()
    return body, m.group(1).strip()


def last_effective(note):
    dates = re.findall(r"effective\s+((?:%s)\s+\d{1,2},\s*\d{4})" % MONTHS, note)
    for d in reversed(dates):
        try:
            return datetime.datetime.strptime(re.sub(r"\s+", " ", d), "%B %d, %Y").strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


def split_title(full):
    """'4:46-2-Motion and Proceedings Thereon' -> ('4:46-2', 'Motion and Proceedings Thereon')."""
    m = re.match(r"\s*(\d+:\d+[A-Z]?(?:-\d+[A-Z]?)*(?:\([a-z0-9]+\))?)\s*-\s*(.*)", full)
    if m:
        return m.group(1), re.sub(r"\s+", " ", m.group(2)).strip()
    return full.strip(), ""


def fetch_term(key):
    data = get(API + "get-term?tid=" + str(key))
    return html_to_text(data.get("description", ""))


def fetch_children(key):
    return get(API + "subtree?tid=" + str(key)) or []


def collect(node, out):
    """Depth-first: add this node's own text (if any), then its descendants."""
    num, title = split_title(node["title"])
    text = fetch_term(node["key"])
    if text:
        body, note = split_note(text)
        out.append({"n": num, "t": title, "x": body, "m": note, "d": last_effective(note)})
    if node.get("lazy", True):
        for child in fetch_children(node["key"]):
            collect(child, out)


def build_chapter(ch):
    num, title = split_title(ch["title"])
    rules = []
    collect(ch, rules)
    return {
        "p": int(ch["section"].split()[-1]),
        "a": num,
        "t": title,
        "f": rules[0]["n"] if rules else num,
        "z": rules[-1]["n"] if rules else num,
        "s": rules,
    }


def fetch_all():
    tree = [c for c in get(API + "tree") if c.get("section") in PARTS]
    chapters = []
    for i, ch in enumerate(tree, 1):
        chapters.append(build_chapter(ch))
        print(f"  [{i}/{len(tree)}] {ch['title'][:70]}", flush=True)
    chapters = [c for c in chapters if c["s"]]
    return chapters, fetch_through()


def load_page_data():
    with open(PAGE, encoding="utf-8") as f:
        src = f.read()
    m = re.search(r'(<script type="application/json" id="nj-rules-data">)(.*?)(</script>)', src, re.S)
    if not m:
        raise RuntimeError("Could not find the nj-rules-data block in " + PAGE)
    return src, m, json.loads(m.group(2) or "[]")


def flatten(chapters):
    return {r["n"]: r for c in chapters for r in c["s"]}


def write_report(old, new):
    o, n = flatten(old), flatten(new)
    changed = sorted((k for k in o.keys() & n.keys() if (o[k]["x"], o[k]["m"]) != (n[k]["x"], n[k]["m"])))
    added = sorted(n.keys() - o.keys())
    removed = sorted(o.keys() - n.keys())
    print(f"Page: {len(o)} rules. Live: {len(n)} rules.")
    print(f"Changed: {len(changed)}, added: {len(added)}, removed: {len(removed)}.")
    if not (changed or added or removed):
        return False

    def link(k):
        return f"[R. {k}]({BASE}/attorneys/rules-of-court?id={k})"

    lines = ["The NJ Rules of Court snapshot in `nj-court-rules.html` no longer matches njcourts.gov.", ""]
    if changed:
        lines += [f"### Changed ({len(changed)})", "", "| Rule | Title | Latest effective date |", "|---|---|---|"]
        lines += [f"| {link(k)} | {n[k]['t']} | {n[k]['d'] or '—'} |" for k in changed]
        lines.append("")
    if added:
        lines += [f"### New ({len(added)})", ""] + [f"- {link(k)} {n[k]['t']}" for k in added] + [""]
    if removed:
        lines += [f"### No longer on njcourts.gov ({len(removed)})", ""] + [f"- R. {k} {o[k]['t']}" for k in removed] + [""]
    lines.append("To refresh the page, run `python3 .github/scripts/build-nj-rules.py` locally and commit the result.")
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("Report written to " + REPORT)
    return True


def fetch_through():
    page = get(BASE + "/attorneys/rules-of-court", as_json=False)
    m = re.search(r"amendments effective on or before\s*([^<.]+\d{4})", page)
    return html.unescape(m.group(1)).strip() if m else ""


def check_date():
    """One request: compare the 'amendments effective on or before' date with the page's."""
    with open(PAGE, encoding="utf-8") as f:
        m = re.search(r'<span class="statute-tag" id="tag-through">Amendments effective through ([^<]*)</span>', f.read())
    ours = m.group(1).strip() if m else ""
    try:
        live = fetch_through()
    except Exception as e:
        print("Check failed: " + str(e), file=sys.stderr)
        return 2
    if not live:
        print("Could not find the amendments date on njcourts.gov; the page layout may have changed.", file=sys.stderr)
        return 2
    print(f"Page: amendments through {ours}. njcourts.gov: amendments through {live}.")
    if live == ours:
        return 0
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write(
            f"njcourts.gov now says the Rules of Court include amendments effective on or before **{live}**, "
            f"but `nj-court-rules.html` was built from the version through **{ours}**.\n\n"
            "To refresh the page, run `python3 .github/scripts/build-nj-rules.py` locally (it takes about an hour "
            "because njcourts.gov rate-limits requests), then commit the updated page. Close this issue once that's done.\n\n"
            "_Opened automatically by the weekly NJ Court Rules check._\n")
    print("Report written to " + REPORT)
    return 1


def main():
    if "--check-date" in sys.argv:
        return check_date()
    check_only = "--check" in sys.argv
    try:
        src, m, old = load_page_data()
        chapters, through = fetch_all()
    except Exception as e:
        print("Failed: " + str(e), file=sys.stderr)
        return 2
    if not chapters or sum(len(c["s"]) for c in chapters) < 500:
        print("Suspiciously little data came back; not touching the page.", file=sys.stderr)
        return 2

    stale = write_report(old, chapters)
    if check_only:
        return 1 if stale else 0
    if not stale and old:
        print("Page already up to date.")
        return 0

    data = json.dumps(chapters, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    out = src[: m.start(2)] + data + src[m.end(2):]
    today = datetime.date.today()
    pulled = today.strftime("%b ") + str(today.day) + today.strftime(", %Y")
    out = re.sub(r'(<span class="statute-tag" id="tag-through">)[^<]*(</span>)',
                 lambda x: x.group(1) + "Amendments effective through " + (through or "—") + x.group(2), out)
    out = re.sub(r'(<span class="statute-tag" id="tag-pulled">)[^<]*(</span>)',
                 lambda x: x.group(1) + "Pulled " + pulled + x.group(2), out)
    out = re.sub(r'(<span id="foot-through">)[^<]*(</span>)', lambda x: x.group(1) + (through or "—") + x.group(2), out)
    out = re.sub(r'(<span id="foot-pulled">)[^<]*(</span>)', lambda x: x.group(1) + pulled + x.group(2), out)
    with open(PAGE, "w", encoding="utf-8", newline="\n") as f:
        f.write(out)
    print(f"Wrote {sum(len(c['s']) for c in chapters)} rules in {len(chapters)} chapters to {PAGE}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
