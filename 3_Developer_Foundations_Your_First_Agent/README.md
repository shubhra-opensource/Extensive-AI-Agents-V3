# Job Gap Coach v3

## Overview

**Job Gap Coach** is a Chromium extension (Manifest V3) in **`job-gap-coach-ver-3`** that reads the active tab's job listing text, compares it with your resume/skills text, and surfaces:
- matched technical skills
- missing skills with priority labels
- missing skills grouped by category
- a 4-week learning roadmap

You can run analysis in two ways:

- **Local (default)** - Substring/phrase matching against the fixed `SKILL_DICTIONARY` in `skills.js`.
- **Gemini** - Optional LLM analysis via the Google Generative Language API (`gemini-3-flash-preview` in `gemini.js`), returning structured JSON (matched, missing, grouped missing, roadmap).

v3 also adds a second Gemini-powered action:
- **Find Similar Jobs (LLM)** - Generates 5-8 close-match roles with quick-search links for LinkedIn and Indeed.

## Demo

- [Walkthrough on YouTube](https://youtu.be/W8WCPVOFya4)

## Features

- **Side panel UI** - Open via the extension action; panel opens on action click (`background.js`).
- **Job page extraction** - `content.js` pulls title, company, description, and URL (LinkedIn-oriented fallbacks, then `main` / `document.body`), with retries if description text is initially short.
- **Analysis modes** - Checkbox **Use Gemini for analysis**; if off, `compareSkills` in `skills.js` runs. If on, `analyzeJobGapWithGemini` in `gemini.js` calls Gemini.
- **Similar jobs generation** - Button **Find Similar Jobs (LLM)** calls `suggestSimilarJobsWithGemini` and renders LinkedIn/Indeed links from generated search queries.
- **Outputs** - Matched skills, missing skills with priority (`Must Learn` / `Nice to Have` / `Ignore for Now`), missing skills by category, priority learning order, 30-day roadmap, similar jobs, and extracted job preview.
- **API key options** - Paste a key in the side panel, or set `GEMINI_API_KEY` / `GOOGLE_API_KEY` in `job-gap-coach-ver-3/.env` and run `node scripts/write-env-config.cjs` (or `powershell -File scripts/write-env-config.ps1`) to write `env-config.js`.
- **Persistence** - Resume text, optional panel API key, and Gemini toggle are stored in `chrome.storage.local`.

## Requirements

- Chromium-based browser with **Manifest V3** support (Chrome, Edge, Brave, etc.).
- **Unpacked load** — No bundler required for the extension itself.
- **Gemini features** - A valid API key and network access to `https://generativelanguage.googleapis.com` (declared in `manifest.json` under `host_permissions`).
- **Optional tooling** - **Node.js** for `scripts/write-env-config.cjs`, or PowerShell for `scripts/write-env-config.ps1`.

## Usage

### Install (developer / unpacked)

1. Clone or copy this repo locally.
2. Open `chrome://extensions` (or `edge://extensions`).
3. Enable **Developer mode**.
4. Click **Load unpacked** and select the **`job-gap-coach-ver-3`** directory (the folder containing `manifest.json`).

### Gemini API key (optional)

1. Create `job-gap-coach-ver-3/.env` with either:
   - `GEMINI_API_KEY=your_key_here`, or  
   - `GOOGLE_API_KEY=your_key_here`
2. From `job-gap-coach-ver-3`, run:
   - `node scripts/write-env-config.cjs` (works even without `.env`; writes an empty key if missing), or  
   - `powershell -File scripts/write-env-config.ps1` (requires `.env` to exist)
3. Reload the extension in `chrome://extensions`.

`env-config.js` is generated and should **not** be committed if it contains a real key (`.env` is gitignored).

Alternatively, paste the key in the side panel field **Gemini API key**.

### Run an analysis

1. Open a **normal HTML job posting** in the active tab (refresh once if extraction fails).
2. Click the extension icon to open the **side panel**.
3. Paste your resume or a bullet list of skills.
4. Choose **Use Gemini for analysis** or leave it off for local dictionary matching.
5. Click **Analyze Current Job**.

The status line shows match/miss counts and whether the run used Gemini or the local dictionary.

### Find similar jobs (Gemini)

1. Keep **Use Gemini for analysis** enabled.
2. Ensure an API key is available (from `.env` -> `env-config.js` or the panel input).
3. Click **Find Similar Jobs (LLM)**.
4. Review suggested roles and open quick links to LinkedIn/Indeed searches.

### Extend or customize

| Goal | Where to edit |
|------|----------------|
| Add or rename skills / categories (local mode) | `SKILL_DICTIONARY` in `skills.js` |
| LLM model, prompts, JSON shapes | `gemini.js` (`GEMINI_MODEL`, `ANALYSIS_JSON_INSTRUCTION`, `SIMILAR_JOBS_JSON_INSTRUCTION`) |
| Job-site DOM selectors | `content.js` (`extractJobDescriptionNow`, `extractJobPageData`) |
| UI copy or layout | `sidepanel.html`, styles, `sidepanel.js` |
| Message flow panel ↔ background ↔ tab | `sidepanel.js`, `background.js`, `content.js` (`GET_JOB_PAGE_DATA` / `EXTRACT_JOB_PAGE`) |
| Env → `env-config.js` | `scripts/write-env-config.cjs` or `scripts/write-env-config.ps1` |

After changes, reload the extension on `chrome://extensions`.

## Project layout (`job-gap-coach-ver-3`)

| File / folder | Role |
|---------------|------|
| `manifest.json` | MV3: service worker, side panel, content script on `<all_urls>`, `storage` / `sidePanel` / `tabs`, host permissions for job pages and Generative Language API |
| `background.js` | Side panel behavior; routes `GET_JOB_PAGE_DATA` to the active tab’s content script |
| `content.js` | In-page job text extraction; handles `EXTRACT_JOB_PAGE` |
| `sidepanel.html` / `sidepanel.js` | Panel UI, mode toggle, API key field, analysis trigger, rendering |
| `skills.js` | Dictionary, normalization, local `compareSkills`, grouping, roadmap |
| `gemini.js` | Gemini analysis + similar-jobs calls, JSON parsing, normalization |
| `env-config.js` | Injected `GEMINI_API_KEY_FROM_ENV` (generated; optional) |
| `scripts/write-env-config.cjs` | Reads `.env` → writes `env-config.js` (Node) |
| `scripts/write-env-config.ps1` | Same for Windows PowerShell |

## Limitations

- **Local mode** - Matching is substring/phrase count against a **static dictionary**, not embeddings; wording impacts precision/recall.
- **Gemini features** - Send resume and job text to Google's API; outputs depend on model and prompts. Very long inputs are truncated in `gemini.js`. Costs, quotas, and privacy policies apply.
- **Extraction** - Quality depends on site DOM; heavy client-side rendering may require selector/timing tweaks in `content.js`.
