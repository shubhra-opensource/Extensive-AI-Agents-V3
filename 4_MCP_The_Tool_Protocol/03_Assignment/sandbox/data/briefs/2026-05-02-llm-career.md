Nice, then you now have your first domain-specific tool wired in.

Next, let’s add **`history_list(limit)`**, because it lets the model see “recent issues” and later powers `history_compare` and prompts like “since last week”. This will just read filenames from `data/briefs` and return a sorted list of brief IDs.

Here is a concrete version you can add after `history_write`:

```python
from typing import List

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
```

Key points for understanding:

- It assumes your `brief_id` is exactly the filename without `.md`, so it mirrors `history_write`.  
- Sorting by filename works well if your IDs start with ISO dates (`YYYY-MM-DD`), because string order == chronological order.

After this, the model can call `history_list` to get candidates, then `history_read` on a chosen one.

Next step would naturally be `history_read(brief_id)` to load a specific brief. In your own words, how would you implement `history_read` using the patterns you already used in `history_write` and `read_file`?