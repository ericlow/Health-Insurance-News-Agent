"""lookup_regulatory_rules tool — returns docs/regulatory-rules.md for the analyst engine."""
from pathlib import Path


def lookup_regulatory_rules() -> str:
    """Return the full content of docs/regulatory-rules.md."""
    path = Path(__file__).parents[3] / "docs" / "regulatory-rules.md"
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return "[regulatory-rules.md not found — proceeding without rules layer]"
