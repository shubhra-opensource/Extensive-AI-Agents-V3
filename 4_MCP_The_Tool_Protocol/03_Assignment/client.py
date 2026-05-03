"""
LLM Career Copilot — Weekly Brief client.

This client:
- Spins up the MCP server (server.py) over stdio.
- Calls tools to fetch:
  - News (Tavily)
  - GitHub trending repos
  - arXiv papers
  - Jobs (Jooble, India)
  - Recent history briefs
- Feeds the aggregated signals into Gemini to write the sections:
  - Introduction
  - Priority Signal
  - What Changed
  - Current Jobs
  - Action Items
  - Top Papers
  - Top GitHub Repos
- Saves the completed brief via history_write(brief_id, content).

Run (from this repo root):

  uv run client.py
  # or:
  python client.py

Env:
  GOOGLE_API_KEY  – for Gemini
  (server.py also expects TAVILY_API_KEY and JOOBLE_API_KEY in its own process)
"""

import asyncio
import json
import os
import sys

# Configure stdout for utf-8 to handle arrow characters on Windows
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
from concurrent.futures import TimeoutError
from datetime import datetime
from typing import Any, Dict, List, Optional
import webbrowser

from dotenv import load_dotenv
from google import genai
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from prefab_ui.app import PrefabApp
from prefab_ui.components import Markdown, Card, CardContent, Column

load_dotenv()

# ---------------------------------------------------------------------------
# LLM configuration (mirrors style from sample_client.py)
# ---------------------------------------------------------------------------

MODEL = "gemini-3.1-flash-lite-preview"  # swap if you use a different model
MAX_ITERATIONS = 3  # single-pass sections; no agentic loop needed here
LLM_SLEEP_SECONDS = 10
LLM_TIMEOUT = 90

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# ---------------------------------------------------------------------------
# Career brief configuration
# ---------------------------------------------------------------------------

DEFAULT_TOPIC = os.getenv("CAREER_TOPIC", "agentic AI and LLM careers")
DEFAULT_JOBS_QUERY = os.getenv("CAREER_JOBS_QUERY", "llm engineer")
BRIEF_ID_PREFIX = os.getenv("BRIEF_ID_PREFIX", "llm-career")

# Command used to launch the MCP server.
# Adjust if you prefer `python server.py` instead of `uv run server.py`.
SERVER_COMMAND = os.getenv("MCP_SERVER_COMMAND", "uv")
SERVER_ARGS = os.getenv("MCP_SERVER_ARGS", "run server.py").split()


# ---------------------------------------------------------------------------
# LLM helpers
# ---------------------------------------------------------------------------

async def generate_with_timeout(prompt: str, timeout: int = LLM_TIMEOUT) -> str:
    """Run the blocking Gemini call in a thread with a timeout and return text."""
    loop = asyncio.get_event_loop()
    try:
        response = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: client.models.generate_content(
                    model=MODEL,
                    contents=prompt,
                ),
            ),
            timeout=timeout,
        )
    except Exception as e:
        raise RuntimeError(f"LLM call failed: {e}") from e

    # For this use-case we expect a single text block.
    text = getattr(response, "text", "") or ""
    return text.strip()


# ---------------------------------------------------------------------------
# MCP helpers
# ---------------------------------------------------------------------------

def describe_tools(tools) -> str:
    """Human-readable description of tools (for debugging/logging)."""
    lines = []
    for i, t in enumerate(tools, 1):
        props = (t.inputSchema or {}).get("properties", {})
        params = ", ".join(f"{n}: {p.get('type', '?')}" for n, p in props.items()) or "no params"
        lines.append(f"{i}. {t.name}({params}) — {t.description or ''}")
    return "\n".join(lines)


def coerce(value: Any, schema_type: Optional[str]) -> Any:
    """Coerce JSON-ish values to the expected type if the schema is simple."""
    if schema_type == "integer":
        return int(value)
    if schema_type == "number":
        return float(value)
    if schema_type == "array":
        # Teaching code; fine inside the sandbox if we ever need string -> list.
        if isinstance(value, str):
            return json.loads(value)
        return list(value)
    if schema_type == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return bool(value)
    return value


async def call_tool_json(
    session: ClientSession,
    name: str,
    arguments: Optional[Dict[str, Any]] = None,
) -> Any:
    """
    Call a tool and try to extract a JSON-serializable Python object.

    This is resilient to different MCP content encodings:
    - content[0].json
    - JSON in content[0].text
    - fall back to raw text / repr
    """
    arguments = arguments or {}
    result = await session.call_tool(name, arguments=arguments)

    if not getattr(result, "content", None):
        return None

    parsed_items = []
    for c in result.content:
        if hasattr(c, "json") and c.json is not None and not callable(c.json):
            parsed_items.append(c.json)
            continue

        text = getattr(c, "text", None)
        if text is not None:
            text = text.strip()
            if not text:
                continue
            try:
                parsed = json.loads(text)
                if isinstance(parsed, str):
                    try:
                        parsed = json.loads(parsed)
                    except Exception:
                        pass
                parsed_items.append(parsed)
            except Exception:
                parsed_items.append(text)
        else:
            parsed_items.append(c)

    if len(result.content) == 1:
        return parsed_items[0]
    return parsed_items


async def call_tool_text(
    session: ClientSession,
    name: str,
    arguments: Optional[Dict[str, Any]] = None,
) -> str:
    """Call a tool and return the best-effort text representation."""
    arguments = arguments or {}
    result = await session.call_tool(name, arguments=arguments)

    if not getattr(result, "content", None):
        return ""

    c = result.content[0]
    if hasattr(c, "text") and c.text is not None:
        return c.text

    if hasattr(c, "json") and c.json is not None and not callable(c.json):
        return json.dumps(c.json, indent=2)

    return repr(c)


# ---------------------------------------------------------------------------
# Formatting helpers for prompts
# ---------------------------------------------------------------------------

def format_news_block(news: List[Dict[str, Any]]) -> str:
    lines = ["# News"]
    for item in news or []:
        title = item.get("title") or ""
        url = item.get("url") or ""
        source = item.get("source") or ""
        lines.append(f"- {title} ({source}) — {url}")
    return "\n".join(lines)


def format_repos_block(repos: List[Dict[str, Any]]) -> str:
    lines = ["# GitHub Repos"]
    for r in repos or []:
        name = r.get("name") or ""
        url = r.get("url") or ""
        desc = r.get("description") or ""
        stars = r.get("stars") or ""
        language = r.get("language") or ""
        lines.append(f"- {name} [{language}] ⭐ {stars} — {url} — {desc}")
    return "\n".join(lines)


def format_papers_block(papers: List[Dict[str, Any]]) -> str:
    lines = ["# Papers"]
    for p in papers or []:
        title = p.get("title") or ""
        url = p.get("url") or ""
        authors = ", ".join(p.get("authors") or [])
        published = p.get("published") or ""
        lines.append(f"- {title} ({published}) — {authors} — {url}")
    return "\n".join(lines)


def format_jobs_block(jobs: List[Dict[str, Any]]) -> str:
    lines = ["# Jobs"]
    for j in jobs or []:
        title = j.get("title") or ""
        company = j.get("company") or ""
        location = j.get("location") or ""
        url = j.get("url") or ""
        snippet = (j.get("snippet") or "").replace("\n", " ").strip()
        lines.append(f"- {title} — {company} — {location} — {url}\n  {snippet}")
    return "\n".join(lines)


def format_history_context(history: Dict[str, Any]) -> str:
    briefs = (history or {}).get("briefs", [])
    if not briefs:
        return "(no prior briefs available)"

    lines = ["# Recent Briefs Summary"]
    for b in briefs:
        brief_id = b.get("brief_id") or "unknown-id"
        content = (b.get("content") or "").strip()
        first_lines = "\n".join(content.splitlines()[:5])
        lines.append(f"## {brief_id}\n{first_lines}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Section generation with LLM
# ---------------------------------------------------------------------------

async def write_introduction(topic: str, merged_signals: str) -> str:
    prompt = f"""
You are an expert AI career copilot for experienced ML/LLM engineers in India.

Write the "Introduction" section (3–5 sentences) for this week's brief.

Audience: seasoned ML/LLM engineer planning their career.
Topic: {topic}

Signals:
{merged_signals}

Guidelines:
- Set the tone for the week and why this topic matters now.
- Do NOT include a heading; only body text.
- Be concrete and practical, not fluffy.
"""
    return await generate_with_timeout(prompt)


async def write_priority_signal(topic: str, merged_signals: str, history_context: str) -> str:
    prompt = f"""
You are an AI career strategist.

Write the "Priority Signal" section (3–6 sentences) for this week's brief.

Goal:
- Identify ONE main insight the reader should act on this week.

Topic: {topic}

Current signals:
{merged_signals}

Recent history (previous briefs):
{history_context}

Guidelines:
- Clearly highlight what changed versus prior weeks.
- Make the recommendation specific and actionable.
- Do NOT include a heading; only body text.
"""
    return await generate_with_timeout(prompt)


async def write_what_changed(topic: str, merged_signals: str, history_context: str) -> str:
    prompt = f"""
Write the "What Changed" section (4–7 sentences) for this week's brief.

Topic: {topic}

Current signals:
{merged_signals}

Recent history:
{history_context}

Guidelines:
- Focus on shifts in AI, hiring, tools, or skills since prior briefs.
- Contrast this week vs earlier patterns.
- Avoid generic commentary; tie directly to the signals.
- No heading; body text only.
"""
    return await generate_with_timeout(prompt)


async def write_current_jobs(topic: str, jobs_block: str) -> str:
    prompt = f"""
Write the "Current Jobs" section for a weekly LLM career brief.

Reader focus: {topic}

Jobs data:
{jobs_block}

Guidelines:
- Summarize 3–6 specific patterns across roles, locations, and skills.
- Highlight what is surprising or important for a senior ML/LLM engineer.
- 4–7 sentences, no bullet list.
- No heading; body text only.
"""
    return await generate_with_timeout(prompt)


async def write_action_items(
    topic: str,
    merged_signals: str,
    jobs_block: str,
    papers_block: str,
    repos_block: str,
) -> str:
    prompt = f"""
Write the "Action Items" section as a short, numbered list.

Topic: {topic}

Signals:
{merged_signals}

Jobs:
{jobs_block}

Papers:
{papers_block}

Repos:
{repos_block}

Guidelines:
- 3–7 concrete actions the reader can do this week (e.g., update portfolio, learn X, apply to Y).
- Each item should be 1–2 sentences.
- Prefix items with "1.", "2.", etc.
- No heading; just the list.
"""
    return await generate_with_timeout(prompt)


async def write_top_papers(topic: str, papers_block: str) -> str:
    prompt = f"""
Write the "Top Papers" section for this week's brief.

Topic: {topic}

Candidate papers:
{papers_block}

Guidelines:
- Select 3–5 key papers and explain why each matters in 2–3 sentences.
- Present them as a numbered list "1.", "2.", ...
- Focus on practical career impact, not only theory.
- No heading; only the list.
"""
    return await generate_with_timeout(prompt)


async def write_top_github_repos(topic: str, repos_block: str) -> str:
    prompt = f"""
Write the "Top GitHub Repos" section for this week's brief.

Topic: {topic}

Candidate repos:
{repos_block}

Guidelines:
- Select 3–5 repos and explain why each is useful.
- Use a numbered list.
- Emphasize what to clone, read, or adapt for an LLM/agentic engineer.
- No heading; only the list.
"""
    return await generate_with_timeout(prompt)


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

async def main() -> None:
    """End-to-end pipeline to build and save a weekly brief."""
    brief_date = datetime.now().strftime("%Y-%m-%d")
    brief_id = os.getenv("BRIEF_ID", f"{brief_date}-{BRIEF_ID_PREFIX}")
    topic = DEFAULT_TOPIC
    jobs_query = DEFAULT_JOBS_QUERY

    print(f"Starting LLM Career Copilot client")
    print(f"- Brief ID : {brief_id}")
    print(f"- Topic    : {topic}")
    print(f"- Jobs     : {jobs_query}")
    print()

    server_params = StdioServerParameters(
        command=SERVER_COMMAND,
        args=SERVER_ARGS,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Connected to LLM_Career_Copilot_Weekly_Brief MCP server")

            tools = (await session.list_tools()).tools
            print(f"Loaded {len(tools)} tools")
            print(describe_tools(tools))
            print()

            # ----------------------------------------------------------------
            # 1) Clear cache
            # ----------------------------------------------------------------
            print("→ Clearing cache...")
            cache_msg = await call_tool_text(session, "cache_clear")
            print(f"← {cache_msg}")
            print()

            # ----------------------------------------------------------------
            # 2) Fetch data: news, repos, papers, jobs, history
            # ----------------------------------------------------------------
            print("→ Fetching news...")
            news = await call_tool_json(
                session,
                "web_search_news",
                {"topic": topic, "max_results": 7},
            )
            if news is not None and not isinstance(news, list): news = [news]
            print(f"← Got {len(news or [])} news items")
            print()

            print("→ Fetching GitHub trending repos...")
            repos = await call_tool_json(
                session,
                "github_trending",
                {"topic": topic, "max_results": 7},
            )
            if repos is not None and not isinstance(repos, list): repos = [repos]
            print(f"← Got {len(repos or [])} repos")
            print()

            print("→ Fetching papers...")
            papers = await call_tool_json(
                session,
                "papers_search",
                {"topic": topic, "max_results": 7},
            )
            if papers is not None and not isinstance(papers, list): papers = [papers]
            print(f"← Got {len(papers or [])} papers")
            print()

            print("→ Fetching jobs (India)...")
            jobs = await call_tool_json(
                session,
                "jobs_search",
                {"topic": jobs_query, "max_results": 7},
            )
            if jobs is not None and not isinstance(jobs, list): jobs = [jobs]
            print(f"← Got {len(jobs or [])} jobs")
            print()

            print("→ Fetching recent brief history...")
            history = await call_tool_json(
                session,
                "history_compare",
                {"limit": 3},
            )
            brief_count = len((history or {}).get("briefs", []))
            print(f"← Got {brief_count} prior briefs")
            print()

            # ----------------------------------------------------------------
            # 3) Build merged signals + history context strings
            # ----------------------------------------------------------------
            news_block = format_news_block(news or [])
            repos_block = format_repos_block(repos or [])
            papers_block = format_papers_block(papers or [])
            jobs_block = format_jobs_block(jobs or [])
            history_context = format_history_context(history or {})

            merged_signals = "\n\n".join(
                [
                    news_block,
                    repos_block,
                    papers_block,
                    jobs_block,
                ]
            )

            # ----------------------------------------------------------------
            # 4) Use LLM to write each section
            # ----------------------------------------------------------------
            print("→ Writing Introduction...")
            introduction = await write_introduction(topic, merged_signals)
            print("← Done")
            print()

            print("→ Writing Priority Signal...")
            priority_signal = await write_priority_signal(
                topic, merged_signals, history_context
            )
            print("← Done")
            print()

            print("→ Writing What Changed...")
            what_changed = await write_what_changed(
                topic, merged_signals, history_context
            )
            print("← Done")
            print()

            print("→ Writing Current Jobs...")
            current_jobs_text = await write_current_jobs(topic, jobs_block)
            print("← Done")
            print()

            print("→ Writing Action Items...")
            action_items = await write_action_items(
                topic,
                merged_signals,
                jobs_block,
                papers_block,
                repos_block,
            )
            print("← Done")
            print()

            print("→ Writing Top Papers...")
            top_papers_text = await write_top_papers(topic, papers_block)
            print("← Done")
            print()

            print("→ Writing Top GitHub Repos...")
            top_repos_text = await write_top_github_repos(topic, repos_block)
            print("← Done")
            print()

            # ----------------------------------------------------------------
            # 5) Assemble markdown brief
            # ----------------------------------------------------------------
            brief_md = f"""# LLM Career Copilot Weekly Brief — {brief_date}

Topic: {topic}

---

## Introduction

{introduction}

## Priority Signal

{priority_signal}

## What Changed

{what_changed}

## Current Jobs

{current_jobs_text}

## Action Items

{action_items}

## Top Papers

{top_papers_text}

## Top GitHub Repos

{top_repos_text}
"""

            # ----------------------------------------------------------------
            # 6) Save brief via history_write and show recent IDs
            # ----------------------------------------------------------------
            print("→ Saving brief to history...")
            save_msg = await call_tool_text(
                session,
                "history_write",
                {"brief_id": brief_id, "content": brief_md},
            )
            print(f"← {save_msg}")
            print()

            print("→ Listing most recent briefs...")
            recent_ids = await call_tool_json(session, "history_list", {"limit": 5})
            if recent_ids is not None and not isinstance(recent_ids, list): recent_ids = [recent_ids]
            print("← Recent brief IDs:")
            for b_id in recent_ids or []:
                print(f"   - {b_id}")

            print()
            print("→ Generating HTML view with prefab_ui...")
            with PrefabApp(title="LLM Career Copilot Brief", css_class="max-w-4xl mx-auto p-4") as app:
                with Card():
                    with CardContent():
                        Markdown(brief_md)
            
            html_content = app.html()
            html_file = os.path.abspath(f"{brief_id}.html")
            with open(html_file, "w", encoding="utf-8") as f:
                f.write(html_content)
                
            print(f"→ Saved HTML brief to {html_file}")
            print("→ Opening in browser...")
            webbrowser.open(f"file://{html_file}")
            print("=== Done ===")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (TimeoutError, asyncio.TimeoutError):
        print("Top-level timeout while running client.")
    except KeyboardInterrupt:
        print("Interrupted by user.")