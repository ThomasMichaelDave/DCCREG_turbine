"""docs/ledger/make_ledger.py -- builds the design lock's ledger from the repository:
  - the paper: docs/ledger/DCCREG-design-ledger.md -> docs/ledger/DCCREG-design-ledger.pdf (A4, via Chromium);
  - the drawings bundle: every technical drawing in the register below, one sheet each, behind a cover and a register
    -> docs/ledger/DCCREG-drawings-bundle.pdf (A3 landscape). The vector drawings (PDF) go in as they are; the
    schematics and figures are placed on titled sheets.
Needs markdown-it-py, mdit-py-plugins and pypdf (pip install markdown-it-py mdit-py-plugins pypdf cffi) and
playwright with chromium.
Usage: python3 docs/ledger/make_ledger.py [--paper] [--bundle]   (both by default)
"""
import argparse
import functools
import html
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
MD = os.path.join(HERE, "DCCREG-design-ledger.md")
PAPER = os.path.join(HERE, "DCCREG-design-ledger.pdf")
BUNDLE = os.path.join(HERE, "DCCREG-drawings-bundle.pdf")
CHROMIUM = os.environ.get("CHROMIUM", "/opt/pw-browsers/chromium")
LOCK_DATE = "2026-10-09"
LOCK_STATE = "09243c7"                 # the last commit that changed the design; the lock freezes it
REVISION = "revised at the settlement, 2026-10-09"   # the records settled against the lock's baseline

# the register (docs/ledger/register.py): sheet, title, file, what it shows, generator, part ("A" the design of record,
# "B" its supporting drawings, "C" earlier phases kept for the record)
sys.path.insert(0, HERE)
from register import CAD, REGISTER  # noqa: E402


@functools.lru_cache(maxsize=None)
def commit():
    """the commit the build reads from, marked when the tree differs from it (the two outputs aside)."""
    def git(*a):
        return subprocess.run(["git", "-C", ROOT, *a], capture_output=True, text=True).stdout.strip()
    try:
        dirty = git("status", "--porcelain", "--", ".", ":!" + os.path.relpath(PAPER, ROOT),
                    ":!" + os.path.relpath(BUNDLE, ROOT))
        return git("log", "-1", "--format=%h") + (" + uncommitted changes" if dirty else "")
    except OSError:
        return "?"


# ----------------------------------------------------------------------------------------------------------- the paper
PAPER_CSS = """
@page { size: A4; margin: 19mm 17mm 19mm 17mm; }
html { font-size: 9.6pt; }
body { font-family: 'DejaVu Serif', 'Liberation Serif', serif; color: #161616; line-height: 1.42; margin: 0; }
h1, h2, h3, h4 { font-family: 'DejaVu Sans', 'Liberation Sans', sans-serif; color: #0b0b0b; line-height: 1.2;
                 break-after: avoid; }
h2 { font-size: 13.5pt; margin: 1.6em 0 0.5em; padding-top: 0.3em; border-top: 1.2px solid #1d3f5e; }
h2.newpage { break-before: page; }
h3 { font-size: 11pt; margin: 1.2em 0 0.35em; color: #1d3f5e; }
h4 { font-size: 9.8pt; margin: 0.9em 0 0.25em; }
p { margin: 0.35em 0 0.55em; }
ul, ol { margin: 0.25em 0 0.6em; padding-left: 1.35em; }
li { margin: 0.12em 0; break-inside: avoid; }
li > ul, li > ol { margin: 0.1em 0 0.15em; }
strong { color: #0b0b0b; }
code { font-family: 'DejaVu Sans Mono', monospace; font-size: 0.86em; background: #f3f2ee; padding: 0 0.18em;
       border-radius: 2px; }
pre { font-family: 'DejaVu Sans Mono', monospace; font-size: 7.8pt; background: #f6f5f1; padding: 0.6em 0.8em;
      border-left: 2px solid #c3c2b7; white-space: pre-wrap; break-inside: avoid; }
table { border-collapse: collapse; width: 100%; margin: 0.5em 0 0.9em; font-family: 'DejaVu Sans', sans-serif;
        font-size: 7.6pt; line-height: 1.3; }
thead { display: table-header-group; }
th { background: #eceae3; color: #0b0b0b; text-align: left; font-weight: bold; }
th, td { border: 0.6px solid #cfcdc4; padding: 0.28em 0.45em; vertical-align: top; }
tr { break-inside: avoid; }
tbody tr:nth-child(even) td { background: #fbfaf7; }
figure { margin: 0.8em 0 1.1em; text-align: center; break-inside: avoid; }
figure img { max-width: 100%; max-height: 205mm; }
@page land { size: A4 landscape; }
figure.landscape, div.landpage { page: land; margin: 0; }
figure.landscape img { max-height: 150mm; }
div.landpage h2, div.landpage h3 { margin-top: 0; }
div.landpage figure.landscape img { max-height: 136mm; }
nav.toc + .notes { font-size: 9pt; margin-top: 8mm; }
figcaption { font-family: 'DejaVu Sans', sans-serif; font-size: 7.8pt; color: #3c3b38; text-align: left;
             margin-top: 0.35em; line-height: 1.35; }
blockquote { margin: 0.6em 0; padding: 0.4em 0.9em; border-left: 3px solid #1d3f5e; background: #f4f6f9;
             font-size: 0.95em; }
hr { border: none; border-top: 0.8px solid #cfcdc4; margin: 1.2em 0; }
a { color: #1d3f5e; text-decoration: none; }
section.title { min-height: 252mm; display: flex; flex-direction: column; break-after: page; }
section.title h1 { font-size: 23pt; margin: 30mm 0 4mm; line-height: 1.15; border: none; }
section.title .sub { font-family: 'DejaVu Sans', sans-serif; font-size: 12pt; color: #1d3f5e; margin-bottom: 14mm; }
section.title table { font-size: 8.6pt; width: 100%; }
section.title .abstract { margin-top: 10mm; font-size: 9.6pt; }
section.title .foot { margin-top: auto; font-family: 'DejaVu Sans', sans-serif; font-size: 7.6pt; color: #555; }
nav.toc { font-family: 'DejaVu Sans', sans-serif; font-size: 9pt; }
.notes { break-after: page; }
nav.toc h2 { border-top: none; margin-top: 0; }
nav.toc ul { list-style: none; padding-left: 0; }
nav.toc li { margin: 0.25em 0; }
nav.toc li li { margin-left: 1.4em; font-size: 8.4pt; color: #333; }
.tag { font-family: 'DejaVu Sans Mono', monospace; font-size: 0.8em; color: #52514e; }
"""

HEADER = ('<div style="font-family: DejaVu Sans, sans-serif; font-size: 7pt; color: #666; width: 100%; '
          'padding: 0 17mm; display: flex; justify-content: space-between;">'
          '<span>DCCREG turbine &middot; design ledger and fact sheet</span><span>LOCKED {date} &middot; design state {state} '
          '&middot; {revision}</span>'
          '</div>')
FOOTER = ('<div style="font-family: DejaVu Sans, sans-serif; font-size: 7pt; color: #666; width: 100%; '
          'padding: 0 17mm; text-align: right;"><span class="pageNumber"></span> / <span class="totalPages"></span></div>')


# figures the paper sets on a page of their own, turned to landscape: the wide schematics and the A3 drawing
LANDSCAPE = ("figures/architecture.png", "../schematic-rings-supply.png", "../drawings/DCCREG-HUB-201.png",
             "../figures/hub-bench-predictions.png")


def md_to_html(text):
    """CommonMark with tables (as GitHub reads the markdown), ids on the h2 / h3; returns the body and the contents."""
    from markdown_it import MarkdownIt
    from mdit_py_plugins.anchors import anchors_plugin
    md = MarkdownIt("commonmark", {"html": True}).enable("table").use(anchors_plugin, min_level=2, max_level=3)
    tokens = md.parse(text)
    toc = [dict(level=int(t.tag[1]), id=t.attrGet("id"),
                name=md.renderer.renderInline(tokens[i + 1].children, md.options, {}))
           for i, t in enumerate(tokens) if t.type == "heading_open" and t.tag in ("h2", "h3")]
    body = md.renderer.render(tokens, md.options, {})

    # an image alone in a paragraph becomes a figure, its alt text the caption
    def fig(m):
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        src, cap = attrs.get("src", ""), attrs.get("alt", "")
        cls = ' class="landscape"' if src in LANDSCAPE else ""
        return (f'<figure{cls}><img src="{src}" alt=""/>' + (f"<figcaption>{cap}</figcaption>" if cap else "")
                + "</figure>")
    body = re.sub(r"<p>\s*<img ([^>]*?)/?>\s*</p>", fig, body)
    # a heading straight before a landscape figure goes onto its page
    body = re.sub(r'(<h([23])[^>]*>(?:(?!</?h[1-6]).)*</h\2>)\s*(<figure class="landscape">.*?</figure>)',
                  r'<div class="landpage">\1\3</div>', body, flags=re.S)
    # a table whose header row is empty (the front matter's) prints without it
    body = re.sub(r"<thead>\s*<tr>\s*(?:<th[^>]*>\s*</th>\s*)+</tr>\s*</thead>\s*", "", body)
    return body, toc


def toc_html(toc):
    out = ['<nav class="toc"><h2>Contents</h2><ul>']
    open_sub = False
    for t in toc:
        if t["level"] == 2 and open_sub:
            out.append("</ul>")
            open_sub = False
        elif t["level"] == 3 and not open_sub:
            out.append("<ul>")
            open_sub = True
        out.append(f'<li><a href="#{t["id"]}">{t["name"]}</a></li>')
    if open_sub:
        out.append("</ul>")
    out.append("</ul></nav>")
    return "".join(out)


def build_paper():
    text = open(MD, encoding="utf-8").read()
    body, tokens = md_to_html(text)
    # the title page: everything before the first h2, the reading notes aside (they go under the contents)
    m = re.search(r'<div class="landpage"><h2|<h2', body)
    i = m.start() if m else len(body)
    title, rest = body[:i], body[i:]
    # the title's two parts on two lines (the bookmark then reads the name, not a wrapped line)
    title = re.sub(r"<h1>(.*?) — (.*?)</h1>", lambda m: f'<h1>{m.group(1)}</h1><div class="sub">'
                   f'{m.group(2)[:1].upper()}{m.group(2)[1:]}</div>', title, count=1)
    j = title.find("<p><strong>Reading notes.</strong></p>")
    title, notes = (title[:j], title[j:]) if j >= 0 else (title, "")
    for sec in ("the-components-and-how-they-work", "fact-sheet", "known-inconsistencies"):  # each on a fresh page
        rest = re.sub(rf'<h2 id="([^"]*{sec}[^"]*)"', r'<h2 class="newpage" id="\1"', rest)
    doc = (f'<!doctype html><html><head><meta charset="utf-8"><title>DCCREG turbine design ledger</title>'
           f'<style>{PAPER_CSS}</style></head><body><section class="title">{title}'
           f'<div class="foot">Generated from docs/ledger/DCCREG-design-ledger.md by docs/ledger/make_ledger.py, built at '
           f'commit {commit()}. The markdown is the source; this PDF is its print form.</div></section>'
           f'{toc_html(tokens)}<div class="notes">{notes}</div>{rest}</body></html>')
    tmp = os.path.join(HERE, "_paper.html")
    open(tmp, "w", encoding="utf-8").write(doc)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROMIUM)
        pg = b.new_page()
        pg.goto("file://" + tmp)
        pg.wait_for_load_state("networkidle")
        pg.pdf(path=PAPER, format="A4", prefer_css_page_size=True, print_background=True, display_header_footer=True,
               header_template=HEADER.format(date=LOCK_DATE, state=LOCK_STATE, revision=REVISION), footer_template=FOOTER,
               margin=dict(top="19mm", bottom="19mm", left="17mm", right="17mm"), outline=True, tagged=True)
        b.close()
    os.remove(tmp)
    from pypdf import PdfWriter
    w = PdfWriter(clone_from=PAPER)                                   # the bookmarks and tags stay; the metadata added
    w.add_metadata({"/Title": "DCCREG turbine - design ledger and fact sheet (design lock)",
                    "/Subject": f"locked {LOCK_DATE}, design state {LOCK_STATE}, {REVISION}, built at {commit()}"})
    with open(PAPER, "wb") as f:
        w.write(f)
    return PAPER


# -------------------------------------------------------------------------------------------------- the drawings bundle
SHEET_CSS = """
@page { size: A3 landscape; margin: 0; }
html, body { margin: 0; padding: 0; }
body { font-family: 'DejaVu Sans', 'Liberation Sans', sans-serif; color: #111; }
.sheet { width: 420mm; height: 297mm; box-sizing: border-box; padding: 9mm 11mm 8mm; display: flex;
         flex-direction: column; break-after: page; }
.sheet header { display: flex; justify-content: space-between; align-items: baseline; border-bottom: 1.4px solid #1d3f5e;
                padding-bottom: 2.5mm; margin-bottom: 4mm; }
.sheet header .t { font-size: 15pt; font-weight: bold; }
.sheet header .n { font-size: 10pt; color: #1d3f5e; }
.sheet .what { font-size: 9pt; color: #333; margin: 0 0 3mm; }
.sheet .img { flex: 1; display: flex; align-items: center; justify-content: center; min-height: 0; }
.sheet .img img { max-width: 100%; max-height: 100%; object-fit: contain; }
.sheet footer { font-size: 7.6pt; color: #666; display: flex; justify-content: space-between; border-top: 0.6px solid #ccc;
                padding-top: 2mm; margin-top: 3mm; }
table { border-collapse: collapse; width: 100%; font-size: 7.4pt; }
th, td { border: 0.6px solid #cfcdc4; padding: 1.1mm 1.6mm; text-align: left; vertical-align: top; }
th { background: #eceae3; }
h1 { font-size: 24pt; margin: 0 0 2mm; } .sub { font-size: 12pt; color: #1d3f5e; margin-bottom: 6mm; }
.part { font-weight: bold; background: #f4f6f9; }
.tight td, .tight th { padding: 0.75mm 1.6mm; }
"""
PART_NAME = {"A": "Part A — the design of record (locked)", "B": "Part B — supporting drawings of the record",
             "C": "Part C — earlier phases, kept for the record (superseded)"}


def _sheet_html(r, n_total):
    src = os.path.join(ROOT, r["file"])
    return (f'<div class="sheet"><header><span class="t">{html.escape(r["title"])}</span>'
            f'<span class="n">sheet {r["sheet"]} of {n_total} &middot; {PART_NAME[r["part"]].split(" — ")[0]}</span>'
            f'</header><div class="what">{html.escape(r["what"])}</div><div class="img"><img src="file://{src}"/></div>'
            f'<footer><span>{html.escape(r["file"])}' + (f' &middot; generator {html.escape(r["gen"])}' if r.get("gen")
                                                         else "") +
            f'</span><span>DCCREG turbine &middot; drawings bundle &middot; LOCKED {LOCK_DATE} &middot; design state {LOCK_STATE}'
            f' &middot; {REVISION}'
            f'</span></footer></div>')


def _cover_html(n_total):
    """two register pages: the title with parts A and B; then part C and the CAD files."""
    def rows_for(parts):
        out, last = [], None
        for r in REGISTER:
            if r["part"] not in parts:
                continue
            if r["part"] != last:
                out.append(f'<tr><td class="part" colspan="5">{PART_NAME[r["part"]]}</td></tr>')
                last = r["part"]
            out.append(f'<tr><td>{r["sheet"]}</td><td>{html.escape(r["title"])}</td><td>{html.escape(r["what"])}</td>'
                       f'<td>{html.escape(r["file"])}</td><td>{html.escape(r.get("gen") or "")}</td></tr>')
        return "".join(out)
    head = ('<table><thead><tr><th style="width:4%">sheet</th><th style="width:20%">title</th><th>what it shows</th>'
            '<th style="width:24%">file</th><th style="width:15%">generator</th></tr></thead><tbody>')
    cad = "".join(f'<tr><td>{p_}</td><td>{html.escape(f)}</td><td>{html.escape(w)}</td></tr>' for p_, f, w in CAD)
    page1 = (f'<div class="sheet" style="padding-top: 14mm"><h1>DCCREG turbine — technical drawings</h1>'
             f'<div class="sub">The bundle of the design lock ({LOCK_DATE}, design state {LOCK_STATE}, {REVISION}; built '
             f'at {commit()}): '
             f'{n_total} sheets after '
             f'this register. The ledger is docs/ledger/DCCREG-design-ledger.md (and .pdf); the drawings themselves stay '
             f'in the repository at the paths below, with the scripts that redraw them.</div>'
             f'{head}{rows_for("AB")}</tbody></table></div>')
    page2 = (f'<div class="sheet tight" style="padding-top: 12mm"><header><span class="t">Register, continued</span>'
             f'<span class="n">part C and the CAD files</span></header>{head}{rows_for("C")}</tbody></table>'
             f'<h3 style="margin: 5mm 0 2mm; font-size: 11pt">CAD and DXF files (not placed on sheets)</h3>'
             f'<table><thead><tr><th style="width:4%">part</th><th style="width:40%">file</th><th>what</th></tr></thead>'
             f'<tbody>{cad}</tbody></table>'
             f'<p style="font-size: 8pt; color: #444; margin-top: 4mm">Analysis plots of the earlier phases (the '
             f'repository root\'s *.png and sim/*.png) are data, not drawings; they stay with their findings.</p></div>')
    return page1 + page2


def _print(pg, html_text, out):
    tmp = os.path.join(HERE, "_sheet.html")
    open(tmp, "w", encoding="utf-8").write(f'<!doctype html><html><head><meta charset="utf-8"><style>{SHEET_CSS}</style>'
                                           f'</head><body>{html_text}</body></html>')
    pg.goto("file://" + tmp)
    pg.wait_for_load_state("networkidle")
    pg.pdf(path=out, width="420mm", height="297mm", print_background=True, margin=dict(top="0", bottom="0", left="0",
                                                                                        right="0"))
    os.remove(tmp)


def build_bundle():
    from pypdf import PdfReader, PdfWriter
    from playwright.sync_api import sync_playwright
    n_total = len(REGISTER)
    writer = PdfWriter()
    with tempfile.TemporaryDirectory() as d, sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROMIUM)
        pg = b.new_page()
        cover = os.path.join(d, "cover.pdf")
        _print(pg, _cover_html(n_total), cover)
        for page in PdfReader(cover).pages:
            writer.add_page(page)
        writer.add_outline_item("Cover and register", 0)
        parent = {}
        for r in REGISTER:
            start = len(writer.pages)
            if r["file"].lower().endswith(".pdf"):
                for page in PdfReader(os.path.join(ROOT, r["file"])).pages:
                    writer.add_page(page)
            else:
                out = os.path.join(d, f"s{r['sheet']}.pdf")
                _print(pg, _sheet_html(r, n_total), out)
                for page in PdfReader(out).pages:
                    writer.add_page(page)
            if r["part"] not in parent:                                 # once its first page is in, so it points there
                parent[r["part"]] = writer.add_outline_item(PART_NAME[r["part"]], start)
            writer.add_outline_item(f"{r['sheet']}. {r['title']}", start, parent=parent[r["part"]])
        b.close()
    writer.add_metadata({"/Title": "DCCREG turbine - technical drawings (design lock)", "/Subject":
                         f"locked {LOCK_DATE}, design state {LOCK_STATE}, {REVISION}, built at {commit()}"})
    with open(BUNDLE, "wb") as f:
        writer.write(f)
    return BUNDLE


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", action="store_true")
    ap.add_argument("--bundle", action="store_true")
    a = ap.parse_args()
    both = not (a.paper or a.bundle)
    if a.paper or both:
        print(build_paper())
    if a.bundle or both:
        print(build_bundle())


if __name__ == "__main__":
    main()
