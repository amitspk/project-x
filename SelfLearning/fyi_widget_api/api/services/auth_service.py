"""Service layer for authentication-related domain rules."""

import logging
from urllib.parse import urlparse

from fastapi import HTTPException

from fyi_widget_api.api.models.publisher_models import Publisher

logger = logging.getLogger(__name__)


def extract_domain(url: str) -> str:
    """
    Extract domain from URL, removing www. prefix.

    Args:
        url: Full URL or host value

    Returns:
        Domain without www. prefix, lowercased.
    """
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path.split("/")[0]

    # Remove www. prefix
    if domain.startswith("www."):
        domain = domain[4:]

    return domain.lower()


async def validate_blog_url_domain(blog_url: str, publisher: Publisher) -> None:
    """
    Validate that the blog URL domain matches the publisher's domain.

    Business rule:
    - Allow exact match or subdomains of publisher domain.

    Raises:
        HTTPException: 403 if domains don't match.
    """
    blog_domain = extract_domain(blog_url)
    publisher_domain = publisher.domain.lower()

    is_valid_domain = blog_domain == publisher_domain or blog_domain.endswith(
        f".{publisher_domain}"
    )

    if not is_valid_domain:
        logger.warning(
            "Blog URL domain mismatch: '%s' doesn't match publisher domain '%s'",
            blog_domain,
            publisher_domain,
        )
        raise HTTPException(
            status_code=403,
            detail={
                "status": "error",
                "status_code": 403,
                "message": "Blog URL domain mismatch",
                "error": {
                    "code": "FORBIDDEN",
                    "detail": (
                        f"Blog URL domain '{blog_domain}' does not match your "
                        f"publisher domain '{publisher_domain}'"
                    ),
                },
            },
        )


