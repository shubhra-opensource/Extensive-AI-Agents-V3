# LLM Career Copilot 🚀

The **LLM Career Copilot** is an agentic, weekly career brief generator tailored for experienced ML/LLM engineers. Utilizing the **Model Context Protocol (MCP)**, this project demonstrates a modern architecture for separating AI reasoning (the client) from capabilities/tools (the server).

Each week, the copilot aggregates top industry signals—news, trending repositories, research papers, and jobs—and synthesizes a personalized, actionable career brief.

---

## 🎯 What it Generates
The final artifact is the **"LLM Career Copilot Weekly Brief"**, a beautifully formatted HTML document containing:
- **Introduction**: A short opening framing the week's theme and why it matters.
- **Priority Signal**: The single most important insight to pay attention to this week.
- **What Changed**: Key shifts in AI, hiring, tools, or skills since the last issue.
- **Current Jobs**: Relevant roles worth tracking based on the profile.
- **Action Items**: Specific things to do this week to stay ahead.
- **Top Papers**: Practical, high-value research papers.
- **Top GitHub Repos**: The most useful new repos to study or clone.

---

## 🏗️ Architecture

The application follows a standard **2-file MCP architecture** (Server + Client).

### 1. `server.py` (The MCP Server)
The server provides the tools (capabilities) to fetch and persist data safely. It runs in an isolated context and exposes tools via standard I/O (stdio).
- **Data Gathering Tools**: 
  - `web_search_news` (Tavily API for AI news)
  - `github_trending` (Web scraped weekly trending repos)
  - `papers_search` (arXiv API for latest ML research)
  - `jobs_search` (Jooble API for ML/LLM jobs)
- **State & File Tools**: 
  - Manages a secure `sandbox/` directory.
  - Exposes `cache_clear` and general file CRUD operations.
  - History tools (`history_write`, `history_list`, `history_read`, `history_compare`) for persisting prior briefs to inform future insights.

### 2. `client.py` (The MCP Client)
The client acts as the orchestrator and the "brain".
- **LLM Integration**: Connects to **Google Gemini** (`gemini-3.1-flash-lite-preview`).
- **Workflow**:
  1. Spawns the MCP Server as a subprocess (`uv run server.py`).
  2. Queries the server for available tools.
  3. Executes data-gathering tools to pull down fresh context.
  4. Reads historical briefs to provide context on "What Changed".
  5. Prompts Gemini to sequentially generate each section of the weekly brief based on the aggregated signals.
  6. Compiles the markdown, saves it to the sandbox history, and generates a stunning **HTML** view using `prefab_ui`.

---

## ⚙️ How the Process Works

When you run the client, the following sequential process executes:
1. **Initialize Connection**: The Python client opens a `stdio` connection to the FastMCP server.
2. **Clear Cache**: Old cached data is wiped using the `cache_clear` tool.
3. **Data Aggregation**: The client asynchronously requests the server to fetch the latest news, research papers, jobs, and GitHub repos using external APIs.
4. **Context Building**: The server responds with structured JSON data. The client merges this data into a coherent textual context.
5. **Generative Pipeline**: The client makes isolated, single-pass LLM requests to Gemini for each sub-section (Introduction, Jobs, Action Items, etc.) providing the newly gathered context.
6. **Formatting & Output**: The sections are compiled into a final Markdown document. The client leverages the `prefab_ui` library to wrap the Markdown inside a beautiful UI Card, exports it to a self-contained `.html` file, and automatically opens it in your default web browser.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- `uv` (Fast Python package installer)

### Environment Setup
Create a `.env` file at the root of the project with the following API keys:
```env
GOOGLE_API_KEY="your-gemini-api-key"
TAVILY_API_KEY="your-tavily-api-key"
JOOBLE_API_KEY="your-jooble-api-key"
```

### Running the App
To run the full end-to-end pipeline and generate your weekly brief:
```bash
uv run client.py
```
This will fetch the data, stream LLM responses, build the brief, and pop open an HTML page in your browser.

### Running the Server in Dev Mode (MCP Inspector)
If you wish to test the server's tools manually without the client, you can launch the FastMCP Inspector:
```bash
uv run fastmcp dev inspector server.py
```

---

## 📁 Directory Structure
- `client.py` - AI orchestrator and UI generator.
- `server.py` - FastMCP server providing search and persistence tools.
- `sandbox/` - Secure storage for the server.
  - `data/briefs/` - Contains historical markdown briefs.
  - `data/cache/` - Intermediate data from API calls.
