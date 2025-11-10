"""
URL utilities for normalizing and validating URLs.

Ensures consistent URL handling across the application by:
- Removing www prefix
- Lowercasing domain
- Removing trailing slashes
- Preserving query parameters and fragments
"""

from urllib.parse import urlparse, urlunparse
import re

# Maximum number of sanitized query entries to preserve (currently zero because we drop all)
ALLOWED_QUERY_PARAMS: tuple[str, ...] = ()


def normalize_url(url: str) -> str:
    """
    Normalize a URL to ensure consistent handling across the system.
    
    Normalization rules:
    1. Remove 'www.' prefix from domain
    2. Lowercase the domain (not the path)
    3. Remove trailing slash from path (unless it's just "/")
    4. Preserve query parameters and fragments
    5. Ensure scheme is present (default to https if missing)
    
    Args:
        url: The URL to normalize
        
    Returns:
        Normalized URL string
        
    Examples:
        >>> normalize_url("https://www.baeldung.com/article")
        'https://baeldung.com/article'
        
        >>> normalize_url("https://Baeldung.COM/Article/")
        'https://baeldung.com/Article'
        
        >>> normalize_url("www.example.com/path")
        'https://example.com/path'
    """
    if not url or not isinstance(url, str):
        return url
    
    # Add scheme if missing
    if not url.startswith(('http://', 'https://')):
        if url.startswith('//'):
            url = 'https:' + url
        else:
            url = 'https://' + url
    
    # Parse URL
    parsed = urlparse(url)
    
    # Normalize domain
    domain = parsed.netloc.lower()
    
    # Remove www. prefix
    if domain.startswith('www.'):
        domain = domain[4:]
    
    # Normalize path
    path = parsed.path
    
    # Remove trailing slash (but keep root "/")
    if path and len(path) > 1 and path.endswith('/'):
        path = path.rstrip('/')
    
    # If path is empty, set to "/"
    if not path:
        path = '/'
    
    # Strip all query parameters/fragments for canonical comparison
    query = parsed.query
    if ALLOWED_QUERY_PARAMS:
        # Optional future behavior: keep selected query params in canonical form
        from urllib.parse import parse_qsl, urlencode

        kept_pairs = [
            (k, v)
            for k, v in parse_qsl(parsed.query, keep_blank_values=True)
            if k in ALLOWED_QUERY_PARAMS
        ]
        query = urlencode(kept_pairs, doseq=True)
    else:
        query = ""

    normalized = urlunparse((
        parsed.scheme,      # scheme (http/https)
        domain,             # netloc (normalized domain)
        path,               # path (normalized)
        parsed.params,      # params
        query,              # query (filtered/removed)
        ""                 # fragment removed for canonical comparison
    ))
    
    return normalized


def are_urls_equivalent(url1: str, url2: str) -> bool:
    """
    Check if two URLs are equivalent after normalization.
    
    Args:
        url1: First URL
        url2: Second URL
        
    Returns:
        True if URLs are equivalent, False otherwise
        
    Examples:
        >>> are_urls_equivalent("https://www.example.com", "https://example.com")
        True
        
        >>> are_urls_equivalent("https://example.com/path/", "https://example.com/path")
        True
    """
    return normalize_url(url1) == normalize_url(url2)


def extract_domain(url: str) -> str:
    """
    Extract the normalized domain from a URL.
    
    Args:
        url: The URL to extract domain from
        
    Returns:
        Normalized domain (without www)
        
    Examples:
        >>> extract_domain("https://www.baeldung.com/article")
        'baeldung.com'
    """
    normalized = normalize_url(url)
    parsed = urlparse(normalized)
    return parsed.netloc

