#!/usr/bin/env python3
"""
PDF Anchor Cite - citation checker  v1.1.0 (2026-11-24)

Checks every citation in a summary against its PDF, using the same matching
rules as viewer.html, and helps choose anchor words.

  python check_citations.py SUMMARY.md                  check all citations
  python check_citations.py SUMMARY.md --pdf A=path.pdf  say where a source PDF is
  python check_citations.py SUMMARY.md --find A "hepatitis B ... prophylaxis"
                                                        where do these anchors occur?
  python check_citations.py SUMMARY.md --rare A:7       distinctive words on page 7
  python check_citations.py --pdf X=file.pdf --find X "CURB-65"   (no summary needed)

Exit code: 0 = all found, 1 = some need checking, 2 = some not found / PDF missing.

PDF text is read with PyMuPDF if installed (pip install pymupdf), otherwise
pdfplumber, otherwise pypdf. Only the Python standard library is needed
besides one of those.
"""
import argparse
import bisect
import json
import os
import re
import sys
import unicodedata
from collections import Counter

VERSION = "1.1.0"
DEFAULT_SPAN = 80          # words from first to last anchor for a normal match
FAR_FACTOR = 3             # up to 3x that on the stated page = "spread out" (amber), beyond = red
WIDE_RANGE = 3             # a page range longer than this many pages is flagged
SAME_TEXT_MIN = 6          # repeated identical passages of at least this many words count as one match
MAX_OCC = 5000
HERE = os.path.dirname(os.path.abspath(__file__))

# ----------------------------------------------------------------- core ---
_norm_cache = {}


def _is_alnum(c):
    return unicodedata.category(c)[0] in ("L", "N")


# Old LaTeX fonts without a Unicode map put ligatures in control codes (ff fi fl ffi ffl).
LIGATURE_CODES = {"\x1b": "ff", "\x1c": "fi", "\x1d": "fl", "\x1e": "ffi", "\x1f": "ffl"}


def norm_char(ch):
    v = _norm_cache.get(ch)
    if v is None and ch in LIGATURE_CODES:
        v = _norm_cache[ch] = LIGATURE_CODES[ch]
    if v is None:
        v = "".join(c for c in unicodedata.normalize("NFKD", ch).lower() if _is_alnum(c))
        _norm_cache[ch] = v
    return v


def norm_anchor(s):
    return "".join(norm_char(ch) for ch in s)


HEAD_LINES, FOOT_LINES = 4, 5


def blank_boilerplate(pages):
    """Blank out running headers/footers (lines near the top or bottom of a page that repeat
    on other pages, ignoring digits), so they don't count as words between anchors.
    Characters are replaced by spaces so positions stay the same."""
    def key(line):
        return re.sub(r"\d+", "#", " ".join(line.split()).lower())

    def zone(txt):
        lines = txt.split("\n")
        idx = [i for i, l in enumerate(lines) if l.strip()]
        return lines, set(idx[:HEAD_LINES] + idx[-FOOT_LINES:])

    counts = Counter()
    for txt in pages:
        lines, z = zone(txt)
        counts.update({key(lines[i]) for i in z})
    out = []
    for txt in pages:
        lines, z = zone(txt)
        for i in z:
            k, n = key(lines[i]), counts[key(lines[i])]
            if n >= 3 or (n >= 2 and len(k) >= 25):
                lines[i] = " " * len(lines[i])
        out.append("\n".join(lines))
    return out


class Stream:
    """All pages as one run of lower-case letters/digits with word boundaries."""

    def __init__(self, pages, original=None):
        self.pages = original or pages
        chars, is_start, page, raw = [], [], [], []
        last_kind = ""
        for p, txt in enumerate(pages):
            sep = True
            for r, ch in enumerate(txt):
                n = norm_char(ch)
                if not n:
                    sep = True
                    continue
                for c in n:
                    kind = "N" if unicodedata.category(c)[0] == "N" else "L"
                    is_start.append(1 if (sep or kind != last_kind) else 0)
                    chars.append(c)
                    page.append(p)
                    raw.append(r)
                    sep = False
                    last_kind = kind
        n = len(chars)
        self.text = "".join(chars)
        self.is_start = is_start
        self.is_end = [0] * n
        self.word_idx = [0] * n
        w = 0
        for i in range(n):
            if is_start[i]:
                w += 1
            self.word_idx[i] = w
            if i + 1 >= n or is_start[i + 1]:
                self.is_end[i] = 1
        self.page = page
        self.raw = raw
        self.num_pages = len(pages)

    def occurrences(self, a):
        out = []
        if not a:
            return out
        i = self.text.find(a)
        while i != -1 and len(out) < MAX_OCC:
            e = i + len(a) - 1
            if self.is_start[i] and self.is_end[e]:
                out.append((i, e))
            i = self.text.find(a, i + 1)
        return out

    def span(self, s, e):
        return self.word_idx[e] - self.word_idx[s] + 1

    def context(self, s, e, words=8):
        """A short snippet around a match, for the console only."""
        p = self.page[s]
        txt = self.pages[p]
        a, b = self.raw[s], self.raw[e] if self.page[e] == p else len(txt) - 1
        left = " ".join(txt[:a].split()[-words:])
        mid = " ".join(txt[a:b + 1].split())
        right = " ".join(txt[b + 1:].split()[:words])
        return f"...{left} [{mid}] {right}..."


def ordered_windows(occ):
    out = []
    starts = [[o[0] for o in L] for L in occ]
    for o1 in occ[0]:
        cur, ok = o1[1], True
        for j in range(1, len(occ)):
            k = bisect.bisect_right(starts[j], cur)
            if k >= len(occ[j]):
                ok = False
                break
            cur = occ[j][k][1]
        if not ok:
            break
        out.append((o1[0], cur, True))
    by_e = {}
    for w in out:
        if w[1] not in by_e or w[0] > by_e[w[1]][0]:
            by_e[w[1]] = w
    return sorted(by_e.values())


def unordered_windows(occ):
    k = len(occ)
    allo = sorted((s, e, j) for j, L in enumerate(occ) for (s, e) in L)
    cnt = [0] * k
    have, l, out, seen = 0, 0, [], set()
    for r in range(len(allo)):
        if cnt[allo[r][2]] == 0:
            have += 1
        cnt[allo[r][2]] += 1
        while l < r and cnt[allo[l][2]] > 1:
            cnt[allo[l][2]] -= 1
            l += 1
        if have == k and l not in seen:
            seen.add(l)
            e = max(x[1] for x in allo[l:r + 1])
            out.append((allo[l][0], e, False))
    return out


def parse_pages(field):
    f = (field or "").strip()
    if not f or f == "?":
        return None
    m = re.match(r"^(?:pp?\.?\s*)?(\d+)(?:\s*[-–]\s*(\d+))?$", f, re.I)
    if not m:
        return "bad"
    a = int(m.group(1))
    b = int(m.group(2)) if m.group(2) else a
    return (min(a, b), max(a, b))


def parse_anchors(field):
    return [s.strip() for s in re.split(r"\s*(?:\.\.\.|…)\s*", field or "") if s.strip()]


def parse_options(field):
    o = {"nth": None, "span": DEFAULT_SPAN}
    for t in re.split(r"[\s,;]+", field or ""):
        if re.match(r"^#\d+$", t):
            o["nth"] = int(t[1:])
        elif re.match(r"^span=\d+$", t, re.I):
            o["span"] = max(1, int(t.split("=")[1]))
    return o


def merge_overlaps(cands):
    """Overlapping windows are the same passage: keep the tighter one."""
    out = []
    for c in sorted(cands, key=lambda c: (c["s"], c["e"])):
        if out and c["s"] <= out[-1]["e"]:
            if c["span"] < out[-1]["span"]:
                out[-1] = c
        else:
            out.append(c)
    return out


def grade(st, cit):
    """Same rules as CORE.grade in viewer.html."""
    P, opts = cit["pages"], cit["opts"]
    page_str = "whole PDF" if not P else (f"p{P[0]}" if P[0] == P[1] else f"p{P[0]}-{P[1]}")
    res = lambda status, msg, cands=(), pick=0: {"status": status, "msg": msg, "cands": list(cands), "pick": pick}
    if P == "bad":
        return res("bad", "Page field not understood (use e.g. 7 or 34-35)")
    if P and (P[0] < 1 or P[1] > st.num_pages):
        return res("bad", f"Page {page_str} is outside the PDF (it has {st.num_pages} pages)")
    anchors = [a for a in (norm_anchor(x) for x in cit["anchors"]) if a]
    if not anchors:
        if cit["anchors"]:
            return res("bad", "Anchors contain no letters or numbers")
        if not P:
            return res("bad", "No page and no anchors")
        return res("page", f"Page only ({page_str}), no anchors to highlight")
    occ = [st.occurrences(a) for a in anchors]
    missing = [x for x in cit["anchors"] if norm_anchor(x) and not occ[anchors.index(norm_anchor(x))]]
    if missing:
        return res("bad", 'Not found anywhere in the PDF: "' + '", "'.join(missing) + '"')

    span_lim = opts["span"]
    far_lim = span_lim * FAR_FACTOR
    wide = P and P[1] - P[0] + 1 > WIDE_RANGE
    on = (lambda c: c["p1"] >= P[0] and c["p2"] <= P[1]) if P else (lambda c: True)
    near = (lambda c: c["p1"] >= P[0] - 1 and c["p2"] <= P[1] + 1) if P else (lambda c: True)

    def mk(w):
        s, e, ordered = w
        return {"s": s, "e": e, "p1": st.page[s] + 1, "p2": st.page[e] + 1, "span": st.span(s, e), "ordered": ordered}

    ordered = [mk(w) for w in ordered_windows(occ)]
    unordered = [mk(w) for w in unordered_windows(occ)] if len(anchors) > 1 else []
    note = " Page range is very wide: cite one place per citation." if wide else ""

    # 1. tight match on the stated page(s): ordered first, then any order
    for pool, extra in ((ordered, ""), (unordered, " (anchors in a different order)")):
        hits = merge_overlaps([c for c in pool if c["span"] <= span_lim and on(c)])
        if len(hits) == 1:
            return res("warn" if wide else "ok", f"Found on p{hits[0]['p1']}{extra}.{note}", hits)
        if len(hits) > 1 and min(c["span"] for c in hits) >= SAME_TEXT_MIN and len({st.text[c["s"]:c["e"] + 1] for c in hits}) == 1:
            # the same sentence printed more than once on the page (eg a key-points box): any copy verifies it
            return res("warn" if wide else "ok", f"Found on p{hits[0]['p1']}{extra} (same wording appears {len(hits)} times on this page).{note}", hits)
        if len(hits) > 1:
            nth = opts["nth"]
            if nth and nth <= len(hits):
                return res("warn" if wide else "ok", f"Match #{nth} of {len(hits)} on {page_str}{extra}.{note}", hits, nth - 1)
            more = f" (#{nth} requested, only {len(hits)})" if nth else ""
            return res("warn", f"{len(hits)} possible matches on {page_str}{extra}, showing the first{more}. Add a rarer anchor or #2, #3.{note}", hits)
    # 2. on the stated page(s) but spread out
    spread = merge_overlaps([c for c in ordered + unordered if span_lim < c["span"] <= far_lim and on(c)])
    if spread:
        best = min(spread, key=lambda c: c["span"])
        return res("warn", f"Found on p{best['p1']}, but the anchors are spread over {best['span']} words, so the highlight is long. Use anchors from one sentence or regimen.{note}", [best])
    # 3. tight match on another page
    for pool in (ordered, unordered):
        tight = merge_overlaps([c for c in pool if c["span"] <= span_lim])
        if tight:
            close = [c for c in tight if near(c)] or tight
            pages = list(dict.fromkeys(c["p1"] for c in close))
            pl = ", ".join(map(str, pages[:6])) + ("..." if len(pages) > 6 else "")
            many = f" ({len(close)} matches)" if len(close) > 1 else ""
            return res("warn", f"Not on {page_str}; found on p{pl}{many}.{note}", close)
    best = min(ordered + unordered, key=lambda c: c["span"], default=None)
    where = f" (closest: {best['span']} words apart, p{best['p1']})" if best else ""
    return res("bad", f"All anchors exist, but not together{where}. Probably a paraphrase or wrong anchors.")


# -------------------------------------------------------------- summary ---
CITE_LINE = re.compile(r"^\s*[-*+]\s+([\w.:-]+)\s*\|(.*)$")


def parse_citation_line(line):
    m = CITE_LINE.match(line)
    if not m:
        return None
    parts = [p.strip() for p in m.group(2).split("|")]
    if len(parts) < 2 or not parts[0]:
        return None
    parts += [""] * (4 - len(parts))
    source, page_field, anchor_field, opt_field = parts[:4]
    pages = parse_pages(page_field)
    if pages == "bad" and not re.search(r"\d", page_field):
        return None
    return {"id": m.group(1), "source": source, "page_field": page_field, "pages": pages,
            "anchors": parse_anchors(anchor_field), "anchor_text": anchor_field,
            "opts": parse_options(opt_field), "opt_text": opt_field}


def unq(s):
    m = re.match(r"^([\"'])(.*)\1$", s)
    return m.group(2) if m else s


def parse_summary(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("﻿")
    lines = text.split("\n")
    sources, body_start = {}, 0
    if lines and lines[0].strip() == "---":
        end = next((i for i in range(1, len(lines)) if re.match(r"^(---|\.\.\.)\s*$", lines[i])), -1)
        if end > 0:
            in_sources = False
            for L in lines[1:end]:
                if not L.strip() or L.strip().startswith("#"):
                    continue
                top = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", L)
                if top:
                    in_sources = top.group(1).lower() == "sources"
                    continue
                src = re.match(r"^\s+-?\s*([\w.-]+)\s*:\s*(.+)$", L)
                if in_sources and src:
                    val, pages = unq(src.group(2).strip()), None
                    pm = re.search(r"\s*\((\d+)\s*pages?\)\s*$", val, re.I)
                    if pm:
                        pages, val = int(pm.group(1)), val[:pm.start()].strip()
                    sources[src.group(1)] = {"id": src.group(1), "filename": unq(val), "pages": pages}
            body_start = end + 1
    cits, dupes = {}, []
    for L in lines[body_start:]:
        c = parse_citation_line(L)
        if c:
            if c["id"] in cits:
                dupes.append(c["id"])
            cits[c["id"]] = c
    for c in cits.values():
        if c["source"] not in sources:
            fn = c["source"] if c["source"].lower().endswith(".pdf") else None
            sources[c["source"]] = {"id": c["source"], "filename": fn, "pages": None}
    body = "\n".join(lines[body_start:])
    links = re.findall(r"\]\(#([\w.:-]+)\)", body)
    return sources, cits, dupes, links


# ------------------------------------------------------------ PDF text ---
def extract_pages(path):
    """Text per page, in the PDF's own reading order (same order the viewer uses)."""
    try:
        import fitz  # PyMuPDF: best match for the viewer
        with fitz.open(path) as d:
            return [pg.get_text("text") for pg in d], "PyMuPDF"
    except ImportError:
        pass
    try:
        from pypdf import PdfReader
        return [(pg.extract_text() or "") for pg in PdfReader(path).pages], "pypdf"
    except ImportError:
        pass
    try:
        import pdfplumber
        cid = {"(cid:27)": "\x1b", "(cid:28)": "\x1c", "(cid:29)": "\x1d", "(cid:30)": "\x1e", "(cid:31)": "\x1f"}
        with pdfplumber.open(path) as d:
            pages = [(pg.extract_text(use_text_flow=True) or "") for pg in d.pages]
        return [re.sub(r"\(cid:(?:27|28|29|30|31)\)", lambda m: cid[m.group(0)], t) for t in pages], "pdfplumber"
    except ImportError:
        sys.exit("No PDF library found. Install one:  pip install pymupdf")


def config_library():
    cfg = os.path.join(HERE, "config.json")
    try:
        with open(cfg, encoding="utf-8") as f:
            lib = json.load(f).get("library")
        if lib:
            return lib if os.path.isabs(lib) else os.path.join(HERE, lib)
    except (OSError, ValueError):
        pass
    return None


def find_file(name, dirs):
    low = name.lower()
    for d in dirs:
        if not d or not os.path.isdir(d):
            continue
        direct = os.path.join(d, name)
        if os.path.isfile(direct):
            return direct
        for root, _dirs, files in os.walk(d):
            for f in files:
                if f.lower() == low:
                    return os.path.join(root, f)
    return None


# ----------------------------------------------------------------- main ---
LABEL = {"ok": "FOUND", "warn": "CHECK", "bad": "NOT FOUND", "page": "PAGE ONLY", "wait": "NO PDF"}


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Check anchor citations in a summary against its PDF(s).")
    ap.add_argument("summary", nargs="?", help="summary .md/.txt file")
    ap.add_argument("--pdf", action="append", default=[], metavar="ID=PATH", help="path to the PDF for a source id")
    ap.add_argument("--pdf-dir", action="append", default=[], metavar="DIR", help="extra folder to search for PDFs")
    ap.add_argument("--find", nargs=2, metavar=("ID", "ANCHORS"), help='show every place these anchors occur, e.g. --find A "CURB-65 ... urea"')
    ap.add_argument("--rare", metavar="ID:PAGE", help="list distinctive words on a page (good anchor candidates)")
    ap.add_argument("--span", type=int, default=DEFAULT_SPAN, help=f"max words between first and last anchor (default {DEFAULT_SPAN})")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--version", action="version", version=VERSION)
    a = ap.parse_args()

    sources, cits, dupes, links = {}, {}, [], []
    if a.summary:
        with open(a.summary, encoding="utf-8-sig") as f:
            sources, cits, dupes, links = parse_summary(f.read())
    explicit = {}
    for item in a.pdf:
        if "=" not in item:
            sys.exit(f"--pdf needs ID=PATH, got {item}")
        sid, path = item.split("=", 1)
        explicit[sid] = path
        sources.setdefault(sid, {"id": sid, "filename": os.path.basename(path), "pages": None})
    if not sources:
        ap.error("give a summary file, or --pdf ID=PATH")

    dirs = list(a.pdf_dir)
    if a.summary:
        dirs.insert(0, os.path.dirname(os.path.abspath(a.summary)))
    dirs.append(config_library())

    streams, info = {}, {}

    def load(sid):
        if sid in streams:
            return streams[sid]
        s = sources.get(sid)
        if not s:
            sys.exit(f"Unknown source id {sid}. Known: {', '.join(sources)}")
        path = explicit.get(sid) or (find_file(s["filename"], dirs) if s.get("filename") else None)
        if not path or not os.path.isfile(path):
            streams[sid] = None
            info[sid] = f"{s.get('filename') or '(no filename)'} -> NOT FOUND (use --pdf {sid}=path)"
            return None
        pages, engine = extract_pages(path)
        st = Stream(blank_boilerplate(pages), pages)
        streams[sid] = st
        note = ""
        if s.get("pages") and s["pages"] != len(pages):
            note = f"  WARNING: summary says {s['pages']} pages"
        if sum(len(t.strip()) for t in pages) < 20 * max(1, len(pages)):
            note += "  WARNING: very little text; is this a scanned PDF? Run OCR first."
        info[sid] = f"{path} ({len(pages)} pages, text via {engine}){note}"
        return st

    # --find
    if a.find:
        sid, anch = a.find
        st = load(sid)
        if not st:
            sys.exit(info[sid])
        cit = {"pages": None, "anchors": parse_anchors(anch), "opts": {"nth": None, "span": a.span}}
        r = grade(st, cit)
        print(f"Source {sid}: {info[sid]}")
        print(f'Anchors: {" ... ".join(cit["anchors"])}')
        for anchor in cit["anchors"]:
            print(f'  "{anchor}" occurs {len(st.occurrences(norm_anchor(anchor)))} time(s)')
        if not r["cands"]:
            print("No usable match: " + r["msg"])
            return 2
        print(f"{len(r['cands'])} match(es) within {a.span} words:")
        for c in r["cands"][:40]:
            print(f"  p{c['p1']}{'-' + str(c['p2']) if c['p2'] != c['p1'] else ''}  ({c['span']} words)  {st.context(c['s'], c['e'])}")
        if len(r["cands"]) > 40:
            print(f"  ... and {len(r['cands']) - 40} more")
        return 0 if len(r["cands"]) == 1 else 1

    # --rare
    if a.rare:
        m = re.match(r"^([\w.-]+):(\d+)$", a.rare)
        if not m:
            sys.exit("--rare needs ID:PAGE, e.g. A:7")
        sid, pno = m.group(1), int(m.group(2))
        st = load(sid)
        if not st:
            sys.exit(info[sid])
        if not 1 <= pno <= st.num_pages:
            sys.exit(f"Page {pno} outside 1-{st.num_pages}")
        doc_c, page_c, i, n = Counter(), Counter(), 0, len(st.text)
        while i < n:
            j = i
            while not st.is_end[j]:
                j += 1
            w = st.text[i:j + 1]
            doc_c[w] += 1
            if st.page[i] == pno - 1:
                page_c[w] += 1
            i = j + 1
        rows = [(w, page_c[w], doc_c[w]) for w in page_c if (len(w) >= 4 or any(ch.isdigit() for ch in w))]
        rows.sort(key=lambda r: (r[2] - r[1], -len(r[0])))
        print(f"Distinctive words on {sid} p{pno} (times on this page / in whole PDF). Fewer elsewhere = safer anchor:")
        for w, pc, dc in rows[:40]:
            print(f"  {w:<28} {pc:>3} / {dc:<4}{'  <- only on this page' if pc == dc else ''}")
        return 0

    # check all
    if not cits:
        print("No citation lines found. Format:  - c1 | A | 7 | anchor ... anchor")
        return 2
    results = {}
    for cid, c in cits.items():
        st = load(c["source"])
        results[cid] = {"status": "wait", "msg": f"PDF for source {c['source']} not found", "cands": []} if st is None else grade(st, c)

    if a.json:
        out = {"version": VERSION, "sources": info, "citations": [
            {"id": cid, "source": c["source"], "page": c["page_field"], "anchors": c["anchor_text"],
             "status": results[cid]["status"], "message": results[cid]["msg"],
             "matches": [{"page": x["p1"], "words": x["span"]} for x in results[cid]["cands"]]}
            for cid, c in cits.items()]}
        print(json.dumps(out, indent=2))
    else:
        print(f"PDF Anchor Cite checker {VERSION}")
        for sid in sources:
            if sid in info:
                print(f"Source {sid}: {info[sid]}")
        print()
        w = max(len(k) for k in cits)
        for cid, c in cits.items():
            r = results[cid]
            print(f"{cid:<{w}}  {LABEL[r['status']]:<9}  {c['source']} p{c['page_field']:<5}  {c['anchor_text']}")
            print(f"{'':<{w}}  -> {r['msg']}")
            st = streams.get(c["source"])
            if st and r["status"] == "warn":
                for x in r["cands"][:5]:
                    print(f"{'':<{w}}     p{x['p1']}: {st.context(x['s'], x['e'], 6)}")
        orphans = sorted(set(links) - set(cits))
        unused = [k for k in cits if k not in set(links)]
        if dupes:
            print(f"\nDuplicate citation ids (last one wins): {', '.join(dupes)}")
        if orphans:
            print(f"Links with no citation line: {', '.join(orphans)}")
        if unused:
            print(f"Citation lines not linked from the text: {', '.join(unused)}")
        n = Counter(r["status"] for r in results.values())
        print("\nSummary: " + ", ".join(f"{n[k]} {LABEL[k].lower()}" for k in LABEL if n[k]))
    sts = {r["status"] for r in results.values()}
    return 2 if sts & {"bad", "wait"} else (1 if "warn" in sts else 0)


if __name__ == "__main__":
    sys.exit(main())
