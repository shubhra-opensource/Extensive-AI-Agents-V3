from __future__ import annotations
import io
import math
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
import requests
from mcp.server.fastmcp import FastMCP, Image
from typing import List
from tavily import TavilyClient
from bs4 import BeautifulSoup

import xml.etree.ElementTree as ET
from datetime import datetime
# ---------------------------------------------------------------------------
# Load env variables
# ---------------------------------------------------------------------------
from dotenv import load_dotenv
load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
JOOBLE_API_KEY = os.getenv("JOOBLE_API_KEY")


mcp = FastMCP("LLM_Career_Copilot_Weekly_Brief")

# ---------------------------------------------------------------------------
# Sandbox — every file/shell tool is confined to this directory.
# Students see an explicit safety boundary instead of "the whole disk".
# ---------------------------------------------------------------------------
SANDBOX = Path(__file__).parent / "sandbox"
SANDBOX.mkdir(exist_ok=True)

# Create specific data directories within the sandbox
(SANDBOX / "data" / "briefs").mkdir(parents=True, exist_ok=True)
(SANDBOX / "data" / "cache").mkdir(parents=True, exist_ok=True)
(SANDBOX / "data" / "history").mkdir(parents=True, exist_ok=True)

BRIEFS_DIR = SANDBOX / "data" / "briefs"
CACHE_DIR = SANDBOX / "data" / "cache"
HISTORY_DIR = SANDBOX / "data" / "history"

def _safe_path(relative: str) -> Path:
    """Resolve `relative` inside SANDBOX and refuse anything that escapes."""
    p = (SANDBOX / relative).resolve()
    if SANDBOX.resolve() not in p.parents and p != SANDBOX.resolve():
        raise ValueError(f"Path '{relative}' escapes the sandbox")
    return p

# ===========================================================================
# TOOLS — simplest case: pure functions
# ===========================================================================

# ===========================================================================
# Web Search — News (Tavily)
# ===========================================================================

def _get_tavily_client() -> TavilyClient:
    if not TAVILY_API_KEY:
        raise ValueError("TAVILY_API_KEY not set in environment")
    return TavilyClient(api_key=TAVILY_API_KEY)


@mcp.tool()
def web_search_news(topic: str = "agentic ai", max_results: int = 5) -> list[dict]:
    """
    Fetch major news updates for the week using Tavily.
    Returns a list of:
    {
        title: str,
        url: str,
        content: str,
        source: str
    }
    """
    client = _get_tavily_client()

    query = f"{topic} news last 7 days major updates"

    response = client.search(
        query=query,
        max_results=max_results,
        search_depth="advanced",   # better quality
        include_answer=False
    )

    results = response.get("results", [])

    formatted = []
    for r in results:
        formatted.append({
            "title": r.get("title"),
            "url": r.get("url"),
            "content": r.get("content"),
            "source": r.get("source")
        })

    # Optional: cache latest results
    cache_path = CACHE_DIR / "news_latest.md"
    cache_text = "\n\n".join(
        f"### {item['title']}\n{item['url']}\n{item['content']}"
        for item in formatted
    )
    cache_path.write_text(cache_text, encoding="utf-8")

    return formatted

# ===========================================================================
# GitHub Trending (Weekly)
# ===========================================================================

@mcp.tool()
def github_trending(topic: str = "agentic ai", max_results: int = 5) -> list[dict]:
    """
    Fetch top trending GitHub repositories (weekly) and filter by topic.

    Returns:
    [
        {
            "name": "owner/repo",
            "url": "https://github.com/owner/repo",
            "description": "...",
            "language": "...",
            "stars": "1234",
        }
    ]
    """

    url = "https://github.com/trending?since=weekly"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception("Failed to fetch GitHub Trending")

    soup = BeautifulSoup(response.text, "html.parser")

    repos = []

    articles = soup.find_all("article", class_="Box-row")

    for article in articles:
        # Repo name
        h2 = article.find("h2")
        repo_name = h2.text.strip().replace("\n", "").replace(" ", "")
        repo_url = "https://github.com/" + repo_name

        # Description
        desc_tag = article.find("p")
        description = desc_tag.text.strip() if desc_tag else ""

        # Language
        lang_tag = article.find("span", itemprop="programmingLanguage")
        language = lang_tag.text.strip() if lang_tag else ""

        # Stars
        star_tag = article.find("a", href=lambda x: x and x.endswith("/stargazers"))
        stars = star_tag.text.strip() if star_tag else ""

        repos.append({
            "name": repo_name,
            "url": repo_url,
            "description": description,
            "language": language,
            "stars": stars
        })

    # --- Filter by topic ---
    topic_lower = topic.lower()

    filtered = [
        r for r in repos
        if topic_lower in r["name"].lower()
        or topic_lower in r["description"].lower()
    ]

    # fallback if nothing matches
    final = filtered if filtered else repos

    final = final[:max_results]

    # --- Cache ---
    cache_path = CACHE_DIR / "repos_latest.md"
    cache_text = "\n\n".join(
        f"### {r['name']}\n{r['url']}\n{r['description']}"
        for r in final
    )
    cache_path.write_text(cache_text, encoding="utf-8")

    return final


# ===========================================================================
# Papers Search (arXiv )
# ===========================================================================


def _clean_text(text: str) -> str:
    return " ".join(text.strip().split())


def _score_paper(paper: dict, topic: str) -> int:
    score = 0
    text = (paper["title"] + " " + paper["summary"]).lower()

    keywords = [
        topic.lower(),
        "llm",
        "transformer",
        "agent",
        "rag",
        "alignment",
        "multimodal",
        "evaluation"
    ]

    for k in keywords:
        if k in text:
            score += 1

    return score


@mcp.tool()
def papers_search(topic: str="agentic ai", max_results: int = 5) -> list[dict]:
    """
    Fetch relevant papers from arXiv (primary) and rank them.

    Returns:
    [
        {
            "title": str,
            "url": str,
            "summary": str,
            "authors": [str],
            "published": str (YYYY-MM-DD)
        }
    ]
    """

    query = f"all:{topic}"

    url = (
        "http://export.arxiv.org/api/query?"
        f"search_query={query}"
        f"&sortBy=submittedDate"
        f"&sortOrder=descending"
        f"&max_results=15"
    )

    response = requests.get(url)
    if response.status_code != 200:
        raise Exception("Failed to fetch arXiv papers")

    root = ET.fromstring(response.text)

    ns = {"atom": "http://www.w3.org/2005/Atom"}

    papers = []

    for entry in root.findall("atom:entry", ns):
        title = _clean_text(entry.find("atom:title", ns).text)
        summary = _clean_text(entry.find("atom:summary", ns).text)

        link = entry.find("atom:id", ns).text

        authors = [
            a.find("atom:name", ns).text
            for a in entry.findall("atom:author", ns)
        ]

        published_raw = entry.find("atom:published", ns).text
        published = published_raw.split("T")[0]

        papers.append({
            "title": title,
            "url": link,
            "summary": summary,
            "authors": authors,
            "published": published
        })

    # --- Rank papers ---
    papers = sorted(
        papers,
        key=lambda p: _score_paper(p, topic),
        reverse=True
    )

    final = papers[:max_results]

    # --- Cache ---
    cache_path = CACHE_DIR / "papers_latest.md"
    cache_text = "\n\n".join(
        f"### {p['title']}\n{p['url']}\n{p['summary']}"
        for p in final
    )
    cache_path.write_text(cache_text, encoding="utf-8")

    return final

# ===========================================================================
# Jooble
# ===========================================================================
def _get_jooble_key() -> str:
    if not JOOBLE_API_KEY:
        raise ValueError("JOOBLE_API_KEY not set in environment")
    return JOOBLE_API_KEY

@mcp.tool()
def jobs_search(topic: str = "llm engineer", max_results: int = 5) -> list[dict]:
    """
    Fetch relevant current jobs in India using the Jooble REST API.

    Returns a list of:
    {
        "title": str,
        "company": str,
        "location": str,
        "snippet": str,
        "url": str,
        "source": str,
        "salary": str | None,
        "updated": str | None,
    }
    """
    api_key = _get_jooble_key()
    url = f"https://jooble.org/api/{api_key}"

    # For now: always search within India; topic is your "what"
    payload = {
        "keywords": topic,
        "location": "India",          # you can make this smarter later
        "radius": "0",                # 0 = exact location, but "India" is broad
        "page": "1",
        "ResultOnPage": str(max_results),
        "companysearch": "false",     # search in title/description, not only company
    }

    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    jobs_raw = data.get("jobs", [])
    jobs: list[dict] = []

    for job in jobs_raw[:max_results]:
        jobs.append(
            {
                "title": job.get("title"),
                "company": job.get("company"),
                "location": job.get("location"),
                "snippet": job.get("snippet"),
                "url": job.get("link"),
                "source": job.get("source"),
                "salary": job.get("salary"),
                "updated": job.get("updated"),
            }
        )

    # Cache to data/cache/jobs_latest.md (same pattern as news/repos/papers)
    cache_path = CACHE_DIR / "jobs_latest.md"
    cache_text = "\n\n".join(
        f"### {j['title']}\n"
        f"{j.get('company') or ''} — {j.get('location') or ''}\n"
        f"{j.get('url') or ''}\n"
        f"{j.get('snippet') or ''}"
        for j in jobs
    )
    cache_path.write_text(cache_text, encoding="utf-8")

    return jobs







# ===========================================================================
# FILE CRUD — the same primitives Claude itself uses to edit code
# ===========================================================================

@mcp.tool()
def cache_clear() -> str:
    """
    Clear cached .md files under data/cache before building a new brief.
    """
    deleted = []
    for path in CACHE_DIR.glob("*.md"):
        try:
            path.unlink()
            deleted.append(path.name)
        except Exception:
            pass
    return f"Cleared cache files: {', '.join(deleted) if deleted else 'none'}"

@mcp.tool()
def list_files(subdir: str = "") -> list[str]:
    """List files and folders inside the sandbox (optionally under subdir)."""
    target = _safe_path(subdir) if subdir else SANDBOX
    return sorted(str(p.relative_to(SANDBOX)) for p in target.iterdir())


@mcp.tool()
def read_file(path: str) -> str:
    """Read a text file from the sandbox."""
    return _safe_path(path).read_text(encoding="utf-8")


@mcp.tool()
def write_file(path: str, content: str) -> str:
    """Create or overwrite a text file. Parent dirs are created as needed."""
    p = _safe_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} chars to {path}"


@mcp.tool()
def edit_file(path: str, old: str, new: str) -> str:
    """Replace the first occurrence of `old` with `new` in a file.
    Fails if `old` is missing or appears more than once (forces disambiguation).
    """
    p = _safe_path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count == 0:
        raise ValueError("old string not found")
    if count > 1:
        raise ValueError(f"old string matches {count} locations — make it unique")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    return f"Edited {path}"


@mcp.tool()
def delete_file(path: str) -> str:
    """Delete a file or an empty directory inside the sandbox."""
    p = _safe_path(path)
    if p.is_dir():
        shutil.rmtree(p)
    else:
        p.unlink()
    return f"Deleted {path}"


# ===========================================================================
# History
# ===========================================================================
@mcp.tool()
def history_write(brief_id: str, content: str) -> str:
    """
    Save a weekly brief as a markdown file under data/briefs.
    brief_id: usually in format 'YYYY-MM-DD-llm-career'.
    """
    # Normalize to a relative path under SANDBOX
    rel_path = f"data/briefs/{brief_id}.md"
    p = _safe_path(rel_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")

    return f"Saved brief to {rel_path}"



@mcp.tool()
def history_list(limit: int = 5) -> List[str]:
    """
    List up to `limit` most recent brief IDs from data/briefs.
    Returns brief_ids without the `.md` extension, sorted newest first.
    """
    briefs_dir = SANDBOX / "data" / "briefs"
    if not briefs_dir.exists():
        return []

    # Collect only .md files
    files = [p for p in briefs_dir.iterdir() if p.is_file() and p.suffix == ".md"]

    # Sort by filename descending (assuming brief_id encodes date like 2026-05-03)
    files_sorted = sorted(files, key=lambda p: p.name, reverse=True)

    # Trim to limit and strip extension
    brief_ids = [p.stem for p in files_sorted[: max(limit, 0)]]

    return brief_ids

@mcp.tool()
def history_read(brief_id: str) -> str:
    """
    Read a single brief from data/briefs by its brief_id.

    brief_id: e.g. '2026-05-03' (without .md).
    Returns the markdown content as a string.
    """
    rel_path = f"data/briefs/{brief_id}.md"
    p = _safe_path(rel_path)

    if not p.exists():
        raise FileNotFoundError(f"Brief '{brief_id}' not found at {rel_path}")

    return p.read_text(encoding="utf-8")

@mcp.tool()
def history_compare(limit: int = 5) -> dict:
    """
    Return the last `limit` briefs (ID + full markdown content) so the LLM
    can compare current signals/topics against them in its own prompt.

    Returns:
    {
        "briefs": [
            {
                "brief_id": str,
                "content": str,
            },
            ...
        ]
    }
    """
    briefs_dir = BRIEFS_DIR
    if not briefs_dir.exists():
        return {"briefs": []}

    # Collect .md files and sort newest first by filename
    files = [p for p in briefs_dir.iterdir() if p.is_file() and p.suffix == ".md"]
    files_sorted = sorted(files, key=lambda p: p.name, reverse=True)
    files_sorted = files_sorted[: max(limit, 0)]

    briefs: list[dict] = []
    for p in files_sorted:
        content = p.read_text(encoding="utf-8")
        briefs.append(
            {
                "brief_id": p.stem,
                "content": content,
            }
        )

    return {"briefs": briefs}

# ===========================================================================
# RESOURCES — read-only, addressed by URI (vs tools which are actions)
# ===========================================================================


@mcp.resource("sandbox://{path}")
def sandbox_file(path: str) -> str:
    """Expose sandbox files as a resource the client can attach as context."""
    return _safe_path(path).read_text(encoding="utf-8")

# ===========================================================================
# Running the mcp server
# ===========================================================================

if __name__ == "__main__":
    print(f"STARTING — sandbox at {SANDBOX}", file=sys.stderr)
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        mcp.run()
    else:
        mcp.run(transport="stdio")
