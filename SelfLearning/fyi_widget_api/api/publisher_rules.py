"""Utility functions for enforcing publisher configuration rules."""

from typing import Optional, Sequence
from urllib.parse import urlparse

from fastapi import HTTPException

from fyi_widget_shared_library.models.publisher import Publisher
from fyi_widget_shared_library.utils import normalize_url


def is_url_whitelisted(url: str, whitelist: Optional[Sequence[str]]) -> bool:
    """Return True if the URL is allowed by the whitelist definition."""
    if not whitelist:
        return True

    normalized_url = normalize_url(url)
    parsed = urlparse(normalized_url)

    for raw in whitelist:
        if raw is None:
            continue

        entry = raw.strip()
        if not entry:
            continue

        if entry == "*":
            return True

        if "://" in entry:
            # Compare normalized URL prefixes when full URL is provided
            allowed = normalize_url(entry)
            if normalized_url.startswith(allowed):
                return True
            continue

        # Handle domain or path fragments
        # If the entry looks like a path (/news/featured)
        if entry.startswith("/"):
            if parsed.path.startswith(entry):
                return True
            continue

        # Attempt to treat the entry as a host/path without scheme
        candidate = normalize_url(f"https://{entry.lstrip('/')}")
        if normalized_url.startswith(candidate):
            return True

        # Fallback: substring match on path
        if entry.lower() in parsed.path.lower():
            return True

    return False


def ensure_url_whitelisted(url: str, publisher: Publisher) -> None:
    """Raise HTTPException if the blog URL is not allowed for this publisher."""
    whitelist = getattr(publisher.config, "whitelisted_blog_urls", None)
    if is_url_whitelisted(url, whitelist):
        return

    raise HTTPException(
        status_code=403,
        detail="Blog URL is not whitelisted for this publisher.",
    )
