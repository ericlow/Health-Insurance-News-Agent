"""fetch_url tool — retrieves readable text from a URL with Jina Reader fallback (AGE-96)."""
import json
import os

import requests
from bs4 import BeautifulSoup

from agent import http_utils

JINA_READER = "https://r.jina.ai/"


def fetch_url(url: str) -> str:
    """Fetch readable text from a URL. Falls back to Jina Reader on 403/PDF/network error."""
    text = _standard_fetch(url)
    if text is None:
        text = _jina_fetch(url)
    return text if text is not None else json.dumps({"error": f"could not fetch {url}"})


def _standard_fetch(url: str) -> str | None:
    try:
        resp = http_utils.get(url, timeout=30)
        if "pdf" in resp.headers.get("content-type", "").lower():
            return None
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        # ponytail: cap at 50k chars to stay in context window
        return soup.get_text(separator="\n", strip=True)[:50000]
    except Exception:
        return None


def _jina_fetch(url: str) -> str | None:
    try:
        resp = requests.get(
            JINA_READER + url,
            headers={"Authorization": f"Bearer {os.environ['JINA_API_KEY']}"},
            timeout=30,
        )
        return resp.text[:50000] if resp.ok else None
    except Exception:
        return None
