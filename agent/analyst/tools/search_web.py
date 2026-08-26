"""search_web tool — queries Jina Search and returns top results (AGE-96)."""
import os

import requests

JINA_SEARCH = "https://s.jina.ai/"


def search_web(query: str) -> list[dict] | dict:
    """Search via Jina. Returns [{title, url, snippet}, ...] or {"error": ...}."""
    try:
        resp = requests.get(
            JINA_SEARCH,
            params={"q": query},
            headers={
                "Authorization": f"Bearer {os.environ['JINA_API_KEY']}",
                "Accept": "application/json",
                "X-Respond-With": "no-content",
            },
            timeout=20,
        )
        if resp.status_code in (402, 429):
            return {"error": "search quota exceeded"}
        if not resp.ok:
            return {"error": f"{resp.status_code} {resp.reason}"}
        items = resp.json().get("data") or []
        return [
            {"title": r["title"], "url": r["url"], "snippet": r.get("description", "")}
            for r in items[:5]
        ]
    except Exception as e:
        return {"error": str(e)}
