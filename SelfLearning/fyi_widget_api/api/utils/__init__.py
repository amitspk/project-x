"""API service utilities."""

from .url_utils import normalize_url, are_urls_equivalent, extract_domain
from .response_utils import (
    generate_request_id,
    success_response,
    error_response,
    create_json_response,
    success_json_response,
    error_json_response,
    handle_http_exception,
    handle_generic_exception,
    not_found_response,
    validation_error_response,
    unauthorized_response,
    forbidden_response
)

__all__ = [
    "normalize_url",
    "are_urls_equivalent",
    "extract_domain",
    "generate_request_id",
    "success_response",
    "error_response",
    "create_json_response",
    "success_json_response",
    "error_json_response",
    "handle_http_exception",
    "handle_generic_exception",
    "not_found_response",
    "validation_error_response",
    "unauthorized_response",
    "forbidden_response",
]

