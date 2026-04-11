# Job Gap Coach

## Overview

**Job Gap Coach** is a Chromium extension (Manifest V3) that scrapes the active tab’s job listing text, compares it to resume/skills text you provide, and surfaces matched vs. missing technical skills using a fixed skill dictionary. Results render in the side panel with category grouping, rough priority labels, and a simple four-week roadmap.

## Demo

- [Walkthrough on YouTube](https://www.youtube.com/watch?v=Q0E4yUTkTUw)

## Features

- **Side panel UI** — Open via the extension action; panel behavior is set to open on action click (`background.js`).
- **Job page extraction** — Content script (`content.js`) pulls title, company, description, and URL using CSS selectors (LinkedIn-oriented fallbacks, then `main` / `document.body`). Retries with short delays if the description is initially too short.
- **Skill matching** — `skills.js` scans resume and job text for phrases in `SKILL_DICTIONARY` (languages, data, ML/AI, infra, cloud).
- **Outputs** — Matched skills; missing skills with priority (`Must Learn` / `Nice to Have` / `Ignore for Now`) from mention counts; missing skills grouped by category; a 30-day-style roadmap from the top missing skills.
- **Persistence** — Resume/skills textarea is saved to `chrome.storage.local` and restored on panel load.

## Requirements

- Chromium-based browser with **Manifest V3** support (Chrome, Edge, Brave, etc.).
- No Node.js or bundler required; load the folder as an **unpacked** extension.

## Usage

### Install (developer / unpacked)

1. Clone or copy this folder locally.
2. Open `chrome://extensions` (or `edge://extensions`).
3. Enable **Developer mode**.
4. Click **Load unpacked** and select the `job-gap-coach-ver-1` directory (the folder containing `manifest.json`).

### Run an analysis

1. Navigate to a **normal HTML job posting** in the active tab (refresh once if extraction fails).
2. Click the extension icon to open the **side panel**.
3. Paste your resume or a bullet list of skills into the textarea.
4. Click **Analyze Current Job**.

The status line reports match/miss counts; scroll the panel for matched/missing lists, categories, priorities, roadmap, and an extracted job preview (description truncated for display).

### Extend or customize

| Goal | Where to edit |
|------|----------------|
| Add or rename skills / categories | `SKILL_DICTIONARY` in `skills.js` |
| Tune job-site DOM selectors | `content.js` (`extractJobDescriptionNow`, `extractJobPageData`) |
| UI copy or layout | `sidepanel.html`, inline styles, and `sidepanel.js` |
| Message flow between panel ↔ background ↔ tab | `sidepanel.js`, `background.js`, `content.js` (`GET_JOB_PAGE_DATA` / `EXTRACT_JOB_PAGE`) |

After changes, go to `chrome://extensions` and click **Reload** on the extension.

## Project layout

| File | Role |
|------|------|
| `manifest.json` | MV3 manifest: service worker, side panel, content script on `<all_urls>`, permissions |
| `background.js` | Side panel behavior; routes `GET_JOB_PAGE_DATA` to the active tab’s content script |
| `content.js` | In-page job text extraction; handles `EXTRACT_JOB_PAGE` |
| `sidepanel.html` / `sidepanel.js` | Panel UI and analysis trigger |
| `skills.js` | Dictionary, normalization, comparison, grouping, roadmap |

## Limitations

- Matching is **substring / phrase count** against a **static dictionary**, not NLP or embeddings; false positives/negatives depend on wording and dictionary coverage.
- Extraction quality depends on the site’s DOM; sites that load description text only after heavy client-side navigation may need selector or timing adjustments in `content.js`.
