"""docs/ledger/make_ledger.py -- builds the design lock's ledger from the repository:
  - the paper: docs/ledger/DCCREG-design-ledger.md -> docs/ledger/DCCREG-design-ledger.pdf (A4, via Chromium);
  - the drawings bundle: every technical drawing in the register below, one sheet each, behind a cover and a register
    -> docs/ledger/DCCREG-drawings-bundle.pdf (A3 landscape). The vector drawings (PDF) go in as they are; the
    schematics and figures are placed on titled sheets.
Needs python-markdown and pypdf (pip install markdown pypdf cffi) and playwright with chromium.
Usage: python3 docs/ledger/make_ledger.py [--paper] [--bundle]   (both by default)
"""
import argparse
import datetime
import html
import io
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

# the register (docs/ledger/register.py): sheet, title, file, what it shows, generator, part ("A" the design of record,
# "B" its supporting drawings, "C" earlier phases kept for the record)
sys.path.insert(0, HERE)
from register import REGISTER  # noqa: E402


def commit():
    try:
        return subprocess.run(["git", "-C", ROOT, "log", "-1", "--format=%h"], capture_output=True, text=True).stdout.strip()
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
p { margin: 0.35em 0 0.55em; text-align: justify; hyphens: auto; }
ul, ol { margin: 0.25em 0 0.6em; padding-left: 1.35em; }
li { margin: 0.12em 0; }
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
figcaption { font-family: 'DejaVu Sans', sans-serif; font-size: 7.8pt; color: #3c3b38; text-align: left;
             margin-top: 0.35em; line-height: 1.35; }
blockquote { margin: 0.6em 0; padding: 0.4em 0.9em; border-left: 3px solid #1d3f5e; background: #f4f6f9;
             font-size: 0.95em; }
hr { border: none; border-top: 0.8px solid #cfcdc4; margin: 1.2em 0; }
a { color: #1d3f5e; text-decoration: none; }
section.title { height: 252mm; display: flex; flex-direction: column; break-after: page; }
section.title h1 { font-size: 23pt; margin: 30mm 0 4mm; line-height: 1.15; border: none; }
section.title .sub { font-family: 'DejaVu Sans', sans-serif; font-size: 12pt; color: #1d3f5e; margin-bottom: 14mm; }
section.title table { font-size: 8.6pt; width: 100%; }
section.title .abstract { margin-top: 10mm; font-size: 9.6pt; }
section.title .foot { margin-top: auto; font-family: 'DejaVu Sans', sans-serif; font-size: 7.6pt; color: #555; }
nav.toc { break-after: page; font-family: 'DejaVu Sans', sans-serif; font-size: 9pt; }
nav.toc h2 { border-top: none; margin-top: 0; }
nav.toc ul { list-style: none; padding-left: 0; }
nav.toc li { margin: 0.25em 0; }
nav.toc li li { margin-left: 1.4em; font-size: 8.4pt; color: #333; }
.tag { font-family: 'DejaVu Sans Mono', monospace; font-size: 0.8em; color: #52514e; }
"""

HEADER = ('<div style="font-family: DejaVu Sans, sans-serif; font-size: 7pt; color: #666; width: 100%; '
          'padding: 0 17mm; display: flex; justify-content: space-between;">'
          '<span>DCCREG turbine &middot; design ledger and fact sheet</span><span>LOCKED {date} &middot; {commit}</span>'
          '</div>')
FOOTER = ('<div style="font-family: DejaVu Sans, sans-serif; font-size: 7pt; color: #666; width: 100%; '
          'padding: 0 17mm; text-align: right;"><span class="pageNumber"></span> / <span class="totalPages"></span></div>')


def md_to_html(text):
    import markdown
    md = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists", "attr_list", "toc", "md_in_html"],
                           extension_configs={"toc": {"toc_depth": "2-3"}})
    body = md.convert(text)
    # images alone in a paragraph become figures, their alt text the caption
    def fig(m):
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        cap = attrs.get("alt", "")
        return (f'<figure><img src="{attrs.get("src", "")}" alt=""/>'
                + (f"<figcaption>{cap}</figcaption>" if cap else "") + "</figure>")
    body = re.sub(r"<p>\s*<img ([^>]*?)/?>\s*</p>", fig, body)
    return body, md.toc_tokens


def toc_html(tokens):
    flat = []

    def walk(ts):
        for t in ts:
            flat.append(t)
            walk(t.get("children", []))
    walk(tokens)
    out = ['<nav class="toc"><h2>Contents</h2><ul>']
    open_sub = False
    for t in flat:
        if t["level"] == 2:
            if open_sub:
                out.append("</ul>")
                open_sub = False
            out.append(f'<li><a href="#{t["id"]}">{t["name"]}</a></li>')
        elif t["level"] == 3:
            if not open_sub:
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
    # the title block: everything before the first h2 goes on the title page
    i = body.find("<h2")
    title, rest = body[:i], body[i:]
    rest = rest.replace('<h2 id="', '<h2 class="newpage" id="', 1)
    for sec in ("the-machine-at-a-glance", "how-the-design-got-here", "the-components-and-how-they-work",
                "fact-sheet", "drawing-register"):                    # each part on a fresh page
        rest = re.sub(rf'<h2 id="([^"]*{sec}[^"]*)"', r'<h2 class="newpage" id="\1"', rest)
    doc = (f'<!doctype html><html><head><meta charset="utf-8"><title>DCCREG turbine design ledger</title>'
           f'<style>{PAPER_CSS}</style></head><body><section class="title">{title}'
           f'<div class="foot">Generated from docs/ledger/DCCREG-design-ledger.md by docs/ledger/make_ledger.py at commit '
           f'{commit()}. The markdown is the source; this PDF is its print form.</div></section>'
           f'{toc_html(tokens)}{rest}</body></html>')
    tmp = os.path.join(HERE, "_paper.html")
    open(tmp, "w", encoding="utf-8").write(doc)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROMIUM)
        pg = b.new_page()
        pg.goto("file://" + tmp)
        pg.wait_for_load_state("networkidle")
        pg.pdf(path=PAPER, format="A4", print_background=True, display_header_footer=True,
               header_template=HEADER.format(date=LOCK_DATE, commit=commit()), footer_template=FOOTER,
               margin=dict(top="19mm", bottom="19mm", left="17mm", right="17mm"))
        b.close()
    os.remove(tmp)
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
            f'</span><span>DCCREG turbine &middot; drawings bundle &middot; LOCKED {LOCK_DATE} &middot; {commit()}'
            f'</span></footer></div>')


def _cover_html(n_total):
    rows = []
    last = None
    for r in REGISTER:
        if r["part"] != last:
            rows.append(f'<tr><td class="part" colspan="5">{PART_NAME[r["part"]]}</td></tr>')
            last = r["part"]
        rows.append(f'<tr><td>{r["sheet"]}</td><td>{html.escape(r["title"])}</td><td>{html.escape(r["what"])}</td>'
                    f'<td>{html.escape(r["file"])}</td><td>{html.escape(r.get("gen") or "")}</td></tr>')
    return (f'<div class="sheet" style="padding-top: 14mm"><h1>DCCREG turbine — technical drawings</h1>'
            f'<div class="sub">The bundle of the design lock ({LOCK_DATE}, commit {commit()}): {n_total} sheets. '
            f'The ledger is docs/ledger/DCCREG-design-ledger.md (and .pdf).</div>'
            f'<table><thead><tr><th>sheet</th><th>title</th><th>what it shows</th><th>file</th><th>generator</th></tr>'
            f'</thead><tbody>{"".join(rows)}</tbody></table></div>')


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
            if r["part"] not in parent:
                parent[r["part"]] = writer.add_outline_item(PART_NAME[r["part"]], len(writer.pages))
            start = len(writer.pages)
            if r["file"].lower().endswith(".pdf"):
                for page in PdfReader(os.path.join(ROOT, r["file"])).pages:
                    writer.add_page(page)
            else:
                out = os.path.join(d, f"s{r['sheet']}.pdf")
                _print(pg, _sheet_html(r, n_total), out)
                for page in PdfReader(out).pages:
                    writer.add_page(page)
            writer.add_outline_item(f"{r['sheet']}. {r['title']}", start, parent=parent[r["part"]])
        b.close()
    writer.add_metadata({"/Title": "DCCREG turbine - technical drawings (design lock)", "/Subject":
                         f"locked {LOCK_DATE}, commit {commit()}"})
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
