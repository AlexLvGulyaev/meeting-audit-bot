"""Text utility helpers used across services and routes."""

from __future__ import annotations


def strip_markdown_fence(text: str | None) -> str:
    """Remove leading/trailing ```markdown / ``` fences from LLM output."""
    if not text:
        return ""
    lines = text.splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()
