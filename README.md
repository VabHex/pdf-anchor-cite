# PDF Anchor Cite

Version 1.1.1, updated 26/11/2026

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
  "library": "D:\\Documents\\Summaries",
  "port": 8765
}