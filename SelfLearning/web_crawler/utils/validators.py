"""
URL validation utilities with comprehensive security checks.

Provides robust URL validation to prevent security vulnerabilities
and ensure only valid URLs are processed.
"""

import re
from urllib.parse import urlparse, ParseResult
from typing import Set, Optional
from .exceptions import ValidationError


class URLValidator:
    """Validates URLs with security and format checks."""
    
    # Allowed schemes for security
    ALLOWED_SCHEMES: Set[str] = {'http', 'https'}
    
    # Blocked domains/IPs for security
    BLOCKED_DOMAINS: Set[str] = {
        'localhost', '127.0.0.1', '0.0.0.0', '::1',
        '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'
    }
    
    # URL pattern for basic validation
    URL_PATTERN = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    @classmethod
    def validate_url(cls, url: str, allow_local: bool = False) -> ParseResult:
        """
        Validate a URL with comprehensive security checks.
        
        Args:
            url: URL to validate
            allow_local: Whether to allow local/private URLs
            
        Returns:
            Parsed URL object
            
        Raises:
            ValidationError: If URL is invalid or blocked
        """
        if not url or not isinstance(url, str):
            raise ValidationError("URL must be a non-empty string")
        
        url = url.strip()
        if len(url) > 2048:  # Reasonable URL length limit
            raise ValidationError("URL too long (max 2048 characters)")
        
        # Basic pattern validation
        if not cls.URL_PATTERN.match(url):
            raise ValidationError(f"Invalid URL format: {url}")
        
        # Parse URL
        try:
            parsed = urlparse(url)
        except Exception as e:
            raise ValidationError(f"Failed to parse URL: {e}")
        
        # Validate scheme
        if parsed.scheme.lower() not in cls.ALLOWED_SCHEMES:
            raise ValidationError(f"Unsupported scheme: {parsed.scheme}")
        
        # Validate hostname
        if not parsed.netloc:
            raise ValidationError("URL must have a valid hostname")
        
        # Security checks for local/private networks
        if not allow_local:
            hostname = parsed.hostname or parsed.netloc.split(':')[0]
            if cls._is_blocked_domain(hostname):
                raise ValidationError(f"Access to local/private networks blocked: {hostname}")
        
        return parsed
    
    @classmethod
    def _is_blocked_domain(cls, hostname: str) -> bool:
        """Check if hostname is in blocked domains list."""
        hostname_lower = hostname.lower()
        
        # Check exact matches
        if hostname_lower in cls.BLOCKED_DOMAINS:
            return True
        
        # Check for private IP ranges (basic check)
        if cls._is_private_ip(hostname_lower):
            return True
        
        return False
    
    @classmethod
    def _is_private_ip(cls, hostname: str) -> bool:
        """Basic check for private IP addresses."""
        try:
            parts = hostname.split('.')
            if len(parts) != 4:
                return False
            
            octets = [int(part) for part in parts]
            
            # Private IP ranges
            if octets[0] == 10:  # 10.0.0.0/8
                return True
            if octets[0] == 172 and 16 <= octets[1] <= 31:  # 172.16.0.0/12
                return True
            if octets[0] == 192 and octets[1] == 168:  # 192.168.0.0/16
                return True
            if octets[0] == 127:  # 127.0.0.0/8 (loopback)
                return True
                
        except (ValueError, IndexError):
            pass
        
        return False
    
    @classmethod
    def sanitize_filename(cls, url: str) -> str:
        """
        Generate a safe filename from a URL.
        
        Args:
            url: URL to convert to filename
            
        Returns:
            Safe filename string
        """
        parsed = urlparse(url)
        
        # Create base filename from domain and path
        domain = parsed.netloc.replace('www.', '')
        path = parsed.path.strip('/').replace('/', '_')
        
        filename = f"{domain}_{path}" if path else domain
        
        # Remove unsafe characters
        filename = re.sub(r'[^\w\-_.]', '_', filename)
        filename = re.sub(r'_+', '_', filename)  # Collapse multiple underscores
        filename = filename.strip('_')
        
        # Ensure reasonable length
        if len(filename) > 100:
            filename = filename[:97] + '...'
        
        return filename or 'webpage'
