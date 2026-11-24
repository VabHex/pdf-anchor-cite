# PDF Anchor Cite

Version 1.1.0, updated 24/11/2026

PDF Anchor Cite links a written summary to the PDF it was written from. Open the summary and the PDF side by side, click an underlined phrase in the summary, and the PDF scrolls to the passage that phrase came from and highlights it.

The summary never needs to quote the PDF. Each citation is just a page number plus two to four short **anchor words** that appear close together in the PDF (for example `hepatitis B ... prophylaxis`). The tool finds those words on that page and highlights the passage between them.

It also checks every citation when the files are opened. A citation whose anchors can't be found is shown in red, so an incorrect or invented reference is easy to spot.

Everything runs on your own computer. Nothing is uploaded.

---

## Contents

1. [Try it in one minute](#1-try-it-in-one-minute)
2. [What's in this folder](#2-whats-in-this-folder)
3. [Two ways to open the viewer](#3-two-ways-to-open-the-viewer)
4. [Reading the colours](#4-reading-the-colours)
5. [The citation format](#5-the-citation-format)
6. [Prompt for an AI: write or update a summary with citations](#6-prompt-for-an-ai-write-or-update-a-summary-with-citations)
7. [Choosing good anchors](#7-choosing-good-anchors)
8. [The checker script (optional)](#8-the-checker-script-optional)
9. [Limits and troubleshooting](#9-limits-and-troubleshooting)
10. [Using it on a phone](#10-using-it-on-a-phone)
11. [Version history](#11-version-history)

---

## 1. Try it in one minute

1. Double-click **viewer.html**. It opens in your web browser.
2. Drag both files from the **example** folder onto the browser window: `Demo-summary.md` and `Demo-Guideline.pdf`. (Or use **Open summary** and **Open PDF**.)
3. Click any underlined phrase on the left. The PDF on the right jumps to the passage and highlights it.

The demo PDF is fictional and only for trying the tool. Its last section contains some deliberately broken citations, so you can see the amber, red and blue warnings.

---

## 2. What's in this folder

| Item | What it is |
|---|---|
| `viewer.html` | The viewer. Double-click to open it in your browser. |
| `vendor/` | PDF.js 6.2.108, Mozilla's PDF engine (Apache 2.0 licence), packed so the viewer works offline. Keep it next to `viewer.html`. |
| `Start viewer.bat` | Optional launcher. It opens the viewer and loads PDFs automatically from your library folder (see section 3). |
| `serve.py` | The small local web server that `Start viewer.bat` runs. Python, standard library only. |
| `config.json` | Settings for the launcher: your library folder and port number. |
| `check_citations.py` | Optional command-line checker for citations. An AI can use it to test citations before giving you a summary (section 8). |
| `library/` | Default library folder. Put PDFs and summaries here, or point `config.json` at another folder. |
| `example/` | A demo summary and a demo PDF. |

You can move or copy the whole folder anywhere, for example to `%userprofile%\Tools\pdf-anchor-cite`. Keep the files together.

---

## 3. Two ways to open the viewer

**A. Double-click `viewer.html`.** No setup is needed. You load the summary and the PDF yourself, by dragging them in or with the buttons. If the summary names a PDF you haven't loaded, its chip at the top is grey. Click the chip to choose the file.

**B. Double-click `Start viewer.bat`** (needs Python, which you already have). A small window opens and must stay open while you use the viewer. In this mode:

- When you open a summary, the viewer finds each PDF it names in your **library folder** (including subfolders) and loads it automatically.
- A **Library** button lists every `.md` and `.txt` summary in the library folder, newest first.
- You can drag a summary file onto `Start viewer.bat` to open it straight away.

To use a different library folder, edit `config.json`:

```json
{
  "library": "D:\\Cloud AI Knowledge Sync",
  "port": 8765
}
```

Use double backslashes in the path. A relative path such as `"library"` means "inside this tool's folder". The server only listens on your own computer (127.0.0.1) and only serves this tool and the library folder.

**Browser:** tested in Chrome. Edge uses the same engine, so it should behave the same.

---

## 4. Reading the colours

Each cited phrase is underlined in a colour, and the top bar shows how many citations are in each state.

| Colour | Meaning | What to do |
|---|---|---|
| Green | Found once on the stated page (anchors in any order). Also green if the same sentence is printed twice on that page, as in a key-points box. | Nothing. |
| Amber | Found, but needs a look. One of: on a different page; more than one possible place on that page; anchors spread over a long passage (80 to 240 words), so the highlight is long; or a page range wider than 3 pages. The bar above the PDF says which. Use ‹ › to step through possible matches. | Check that the highlight is the right passage. Then fix the page, or choose closer or rarer anchors. |
| Red (wavy) | Not verified. Either an anchor isn't in the PDF at all, or the anchors never appear together. This usually means the AI paraphrased or combined text from separate places. | Treat the claim as unverified until fixed. |
| Blue | Page-only citation (no anchors). Jumps to the page without highlighting. | Nothing. |
| Grey | The PDF for that source isn't loaded yet. | Click the source chip at the top to load it. |

The main highlight runs from the first anchor to the last. A paler highlight shows the rest of the sentence for context. Hover over a cited phrase to see its page, anchor words and status.

**Copy report** puts a plain-text list of every citation and its status on the clipboard. Paste it into an AI chat to ask it to fix the amber and red ones.

**Moving around the summary:**

- Click a **cited phrase**: the PDF jumps to it.
- Click the small **id** after a phrase (e.g. `c153`): jumps to that line in the citation list at the bottom.
- Click a **row in the citation list**: the PDF jumps to it. Click the **same row again** (or its ↑ button) to go back to the place in the text that cites it. If several phrases use that citation, each click goes to the next one.
- **‹ Summary** (on a phone) does the same from the PDF view.

Other controls: **−, Fit, +** zoom the PDF. Drag the bar between the panes to resize them. **Esc** clears the highlight. With more than one PDF, tabs appear above the PDF. To replace a loaded PDF, Shift-click (or right-click) its chip at the top.

---

## 5. The citation format

A summary is an ordinary Markdown (`.md`) or text file with three parts: a short header, the text with linked phrases, and a list of citations at the end.

```markdown
---
title: Rituximab and hepatitis B screening
sources:
  A: Demo-Guideline.pdf
---

Before rituximab, [screen for hepatitis B and give antiviral prophylaxis
if surface antigen positive](#c7). Review treatment at 48 to 72 hours, and
[a 5 day course is usually enough](#c8).

## Citations
- c7 | A | 4 | hepatitis B ... prophylaxis ... surface antigen
- c8 | A | 5 | 5 days
```

### The header

The block between the two `---` lines lists each PDF the summary uses and gives it a short id (`A`, `B`, `C`...). Write the PDF's exact filename. Optionally add the page count, e.g. `A: Demo-Guideline.pdf (5 pages)`, and the viewer warns you if a different version of the PDF is loaded.

### Links in the text

`[phrase](#c7)` makes the phrase clickable and ties it to citation `c7`. The phrase is written in the summary's own words. The same id can be linked from more than one place.

### Citation lines

One line per citation, starting with `- `:

```
- id | source | page | anchor ... anchor ... anchor | options
```

| Field | Rules | Examples |
|---|---|---|
| id | Letters, numbers, `-` or `.`; must match the link. | `c7`, `gold-3`, `12` |
| source | The id from the header. A filename ending in `.pdf` also works. | `A` |
| page | The page's position in the PDF file (first page of the file = 1), **not** the number printed on the page. A range covers a passage that crosses a page break. Use `?` to search the whole PDF. | `4`, `34-35`, `?` |
| anchors | 1 to 4 short pieces of PDF text, separated by `...`, in the order they appear in the PDF. Leave empty for a page-only citation. | `hepatitis B ... prophylaxis` |
| options | Optional. `#2` picks the 2nd match on the page. `span=120` allows a normal match over up to 120 words (default 80). | `#2`, `span=120` |

### How matching works

- Capitals, accents, punctuation, spacing and line breaks are ignored. `CURB-65` matches `CURB 65`, and `prophylaxis` matches `prophy-` at the end of one line followed by `laxis` on the next.
- Each anchor must match whole words. `300` won't match inside `1300`, and `B` won't match the start of `Bacteria`.
- Reference numbers stuck to a word (like `difficile¹²`) don't block a match.
- Running headers and footers (lines at the top or bottom of the page that repeat on other pages, such as "Printed: ..." lines, URLs and page numbers) are ignored. They don't count as words between anchors and are never highlighted, so a passage that crosses a page break works normally.
- Up to 80 words from the first anchor to the last is a normal match. 80 to 240 words on the stated page is amber ("spread out"). Further apart is red.
- The anchors' order is preferred but not required.
- The page number is checked first. If the passage isn't there, the tool looks on the pages either side, then in the whole PDF, and marks the citation amber.

### Several PDFs

List them all in the header (`A:`, `B:`...) and use the matching letter in each citation line. The viewer loads each one and shows tabs.

---

## 6. Prompt for an AI: write or update a summary with citations

Copy everything in the box below into a chat, then attach the PDF(s) and, if you already have one, your summary. It works for both jobs: writing a new summary with citations, or adding citations to an existing summary. It can also fix the warnings listed in the viewer's **Copy report** output.

```text
You are preparing a summary for a viewer tool called PDF Anchor Cite. The tool turns linked phrases in the summary into buttons that jump to, and highlight, the exact passage in the PDF. It finds the passage from a page number plus a few short "anchor" words.

WHAT I WANT
- If I give you a summary: keep my wording, structure and headings. Only add citation links and the citation list. Tell me about any claim you cannot find in the PDF instead of guessing.
- If I ask for a new summary: write it in your own words, citing every claim.
- If I paste a "PDF Anchor Cite report": fix only the citations marked CHECK, NOT FOUND or NO PDF and leave the rest unchanged.
- Return the complete summary as one Markdown code block, so I can save it as a .md file.

FORMAT (follow exactly)
1. The file starts with this header (one line per PDF, using the exact filename):
---
title: <short title>
sources:
  A: <exact filename of the first PDF, including .pdf>
  B: <exact filename of the second PDF, if there is one>
---
2. In the text, link the words that make each claim: [phrase in the summary's own words](#c1). Link the specific claim (a few words up to one sentence), not whole paragraphs. Every number, dose, threshold, recommendation and key finding must be linked. Number the ids c1, c2, c3... in order.
3. End the file with a "## Citations" heading and one line per id:
- c1 | A | 12 | anchor ... anchor ... anchor
The fields are: id | source letter | page | anchors. Do not use the | character anywhere else in these lines.

PAGE
- Use the page's position in the PDF file, counting the first page of the file as 1. Do NOT use the page number printed on the page (they often differ).
- Only use a range when the passage runs on to the NEXT page (e.g. 12-13). Never wider, and never join pages that are far apart.

ONE PLACE PER CITATION
- Each citation points to one sentence, bullet, table row or single drug regimen line.
- If a summary line combines things from different places (drug A OR drug B listed separately, an adult dose and a child dose in different sections, a regimen and its duration from another paragraph), give each part its own link and citation, e.g. [dicloxacillin 500 mg PO 6-hourly](#c13) or [flucloxacillin 500 mg PO 6-hourly](#c14).

ANCHORS (the most important part)
- Give 2 or 3 anchors (4 at most) separated by " ... ", in the order they appear in the PDF.
- All anchors must lie within about 40 words of each other, in the same sentence, bullet, table row or regimen line.
- Each anchor is 1 to 3 consecutive words copied exactly from the PDF, letter for letter. Use the PDF's spelling, not your abbreviation (write trimethoprim+sulfamethoxazole if that is what the PDF prints, not TMP-SMX). Never paraphrase an anchor. Never copy a sentence or a long phrase: all anchors in one citation together should be about 8 words at most.
- Keep a number with its drug or unit in the same anchor: "cefazolin 2 g", "aciclovir 800 mg", "12.5 mg/kg". Never use these on their own as an anchor: g, mg, mg/kg, up to, orally, intravenously, OR, PLUS, hourly, days, and, the.
- Choose distinctive words: drug or organism names, conditions, numbers with units, named scores, tests or trials, and table or figure labels. At least one anchor should be rare in the document.
- Avoid common words on their own (patients, treatment, recommended, should, population, may).
- Never take anchors from running headers or footers, web addresses, "Printed:" lines, page numbers or note markers.
- Make the first anchor the start of the claim (eg the drug or key noun) and the last anchor the deciding detail (dose, frequency, duration or condition).
- Tables: use the table label, the row label and the value (e.g. Table 2 ... FEV1 ... 50%).
- Figures: use the caption label and a caption word (e.g. Figure 3 ... survival). Words inside images cannot be found.
- If the same anchors would match more than one place on that page, add a rarer anchor. Only as a last resort, add a fifth field: "| #2" means the second match on that page.
- If a claim combines information from two places, link it twice or split the phrase, with one citation per place.
- If a claim summarises a whole page or a figure with no usable text, give a page-only citation: - c9 | A | 14

CHECK BEFORE YOU REPLY
- If you can run Python and have the file check_citations.py, run:
  python check_citations.py summary.md --pdf A="<path to PDF>"
  Fix every line marked CHECK or NOT FOUND, then run it again. Helpers:
  --find A "anchor ... anchor"   shows where anchors occur
  --rare A:12                    lists distinctive words on page 12
- Otherwise, for every citation, re-open the cited page and confirm that each anchor appears on it exactly as written, within about 40 words of the others, in one sentence, row or regimen.

EXAMPLE
---
title: Rituximab and hepatitis B screening
sources:
  A: Demo-Guideline.pdf
---
Before rituximab, [screen for hepatitis B and give antiviral prophylaxis if surface antigen positive](#c1). [A 5 day course is usually enough](#c2).

## Citations
- c1 | A | 4 | hepatitis B ... prophylaxis ... surface antigen
- c2 | A | 5 | 5 days
```

**Tips**

- If the AI can run code, also give it `check_citations.py` so it can test its own citations before replying.
- After loading the result in the viewer, use **Copy report**, paste the report back into the same chat and ask it to fix the amber and red citations.
- You can write citations by hand too. Open the PDF, find two or three rare words close to each other on the page, and write the line.

---

## 7. Choosing good anchors

| Good | Why |
|---|---|
| `hepatitis B ... prophylaxis` | A specific condition plus a specific action. |
| `CURB-65 ... urea ... 7 mmol` | A named score, a criterion and a number. |
| `Table 1 ... 3-5 ... ICU` | Table label, row label and value. |
| `benzylpenicillin ... doxycycline` | Drug names are rarely repeated close together. |

| Weak | Problem | Better |
|---|---|---|
| `recommended ... population` | Common words, likely to match many places. | `hepatitis B ... prophylaxis` |
| `empirical therapy` | A heading phrase that appears on many pages. | `empirical therapy ... narrowed` |
| `the patient should receive treatment` | Long copied wording. | `amoxicillin 1 g` |

Numbers make strong anchors. They are usually unique on a page, and they record facts rather than wording.

---

## 8. The checker script (optional)

`check_citations.py` checks citations without opening the viewer. It uses the same rules as the viewer and is mostly for an AI that can run code. It's also handy for checking many summaries at once.

It needs Python and one PDF library. **PyMuPDF** gives the closest match to the viewer:

```
pip install pymupdf
```

(`pypdf` or `pdfplumber` also work if already installed.)

Examples, run from this folder:

```
python check_citations.py "example\Demo-summary.md"
python check_citations.py "my summary.md" --pdf A="D:\Papers\guideline.pdf"
python check_citations.py "my summary.md" --find A "hepatitis B ... prophylaxis"
python check_citations.py "my summary.md" --rare A:12
python check_citations.py --pdf X="D:\Papers\guideline.pdf" --find X "CURB-65"
```

- The checker looks for PDFs in the summary's folder, then any `--pdf-dir` folders, then the library folder from `config.json`.
- `--find` lists every place a set of anchors occurs, with a few words of context.
- `--rare` lists the words that appear on a page but rarely elsewhere in the PDF, which make good anchors.
- `--json` gives machine-readable output.
- Exit codes: 0 = all found, 1 = some to check, 2 = some not found or a PDF is missing.

The viewer and the checker read PDF text with different engines. In rare cases (unusual layouts) one may grade a citation slightly differently from the other. The viewer is the final word.

---

## 9. Limits and troubleshooting

| Situation | What happens / what to do |
|---|---|
| **Scanned PDF** (pages are pictures, no selectable text) | Nothing can be found. Make the PDF searchable first with OCR, e.g. `ocrmypdf input.pdf output.pdf`, or "Recognise text" in Adobe Acrobat. |
| **Text inside images, charts or flowcharts** | Can't be found. Cite the caption, or use a page-only citation. |
| **Amber "found on p13, not p12"** | Usually the printed page number was used instead of the PDF page. Change the page, or ignore it: the highlight is still correct. |
| **Amber "several matches"** | Add a rarer anchor, or add `| #2` to pick the second match. |
| **Red "all anchors exist, but not together"** | The anchors are in the PDF but never near each other. Usually the AI paraphrased, or merged two separate places into one citation. Split it, or choose anchors from one sentence. |
| **Amber "spread over N words"** | Found, but the anchors cover a long passage, so the highlight is long. Choose anchors from one sentence. If the passage really is long, add `| span=200`. |
| **Two-column layouts and tables** | Usually fine. If not, choose anchors within one column or one table row. |
| **Grey chip / "waiting for PDF"** | The PDF isn't loaded or its filename differs from the header. Click the chip and choose the file. |
| **A new version of the PDF** | Citations keep working as long as the anchor words are still on those pages. Just re-open it. |
| **Old LaTeX PDFs with odd "fi"/"fl" characters** | Handled automatically. |
| **"vendor/pdfjs-bundle.js is missing"** | The `vendor` folder must sit next to `viewer.html`. |
| **Start viewer.bat shows a Python error** | Python isn't installed or isn't on PATH. Double-clicking `viewer.html` still works without it. |

**Privacy:** the viewer reads files only when you drop or choose them, or (with the launcher) from your library folder. Nothing goes over the internet.

---

## 10. Using it on a phone

The viewer adapts to small screens. It shows one pane at a time, with **Summary / PDF** buttons at the top. Tapping a cited phrase switches to the PDF, and **‹ Summary** brings you back. Hover tooltips don't exist on phones. Use the citation list at the bottom instead.

The catch is opening it. Phones won't run a web page straight from a file the way a computer does, so the page needs a web address. Your PDFs and summaries stay on the phone either way: you choose them with **Open summary** and **Open PDF** from the Files, OneDrive or Google Drive app, and they are read inside the browser.

Simple ways to give it an address:

1. **Publish the viewer page as a private web page** (for example as a Claude artifact, or on any free static host). It needs no computer running. This is the easiest option for use on the move.
2. **At home, run the launcher in "home network" mode** so the phone can open it from your PC over Wi-Fi, with library auto-loading. This needs a small change to `serve.py` and a Windows firewall prompt, and it only works while the PC is on.

---

## 11. Version history

| Version | Date | Changes |
|---|---|---|
| 1.1.0 | 24/11/2026 | Running headers and footers ignored (fixes most false reds when a passage crosses pages, and keeps highlights off them). Normal match widened to 80 words. Long but valid passages are amber ("spread out") rather than red. Anchor order no longer required. Overlapping and repeated identical passages count as one match. Wide page ranges flagged. Clicking an id jumps to its citation line; clicking a line twice returns to the text. Hover tooltip shows anchors. Phone layout. Prompt tightened (one place per citation, no unit-only anchors, PDF spelling, no headers). |
| 1.0.0 | 24/11/2026 | First release: viewer with anchor matching, highlights and status colours; launcher with library auto-load; checker script with `--find` and `--rare`; demo files; AI prompt. |
