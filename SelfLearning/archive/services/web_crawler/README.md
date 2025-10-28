# Web Crawler

A production-grade web crawler module for extracting and storing web content with enterprise-level features.

## Features

🚀 **Production Ready**
- Async/await support for high performance
- Comprehensive error handling and retry mechanisms
- Rate limiting and respectful crawling
- Atomic file operations to prevent corruption

🔒 **Security First**
- URL validation with security checks
- Protection against SSRF attacks
- Content type and size validation
- SSL certificate verification

⚡ **Performance Optimized**
- Concurrent request handling
- Connection pooling and keep-alive
- Configurable timeouts and limits
- Memory-efficient content streaming

📊 **Monitoring & Observability**
- Structured logging with JSON support
- Comprehensive metrics and metadata
- Health checks and error tracking
- Performance monitoring capabilities

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

```python
import asyncio
from web_crawler import WebCrawler

async def main():
    async with WebCrawler() as crawler:
        result = await crawler.crawl_and_save("https://example.com")
        print(f"Content saved to: {result['saved_to']}")

asyncio.run(main())
```

### Advanced Configuration

```python
from web_crawler import WebCrawler
from web_crawler.config.settings import CrawlerConfig
from pathlib import Path

# Custom configuration
config = CrawlerConfig(
    timeout=30,
    max_retries=3,
    delay_between_requests=1.0,
    output_directory=Path("./my_crawls"),
    user_agent="MyBot/1.0",
    requests_per_minute=30
)

async with WebCrawler(config=config) as crawler:
    result = await crawler.crawl_and_save("https://example.com")
```

## Configuration

### Environment Variables

Set environment variables with `CRAWLER_` prefix:

```bash
export CRAWLER_TIMEOUT=60
export CRAWLER_MAX_RETRIES=5
export CRAWLER_OUTPUT_DIR="./crawled_data"
export CRAWLER_USER_AGENT="MyBot/2.0"
export CRAWLER_REQUESTS_PER_MINUTE=30
```

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `timeout` | 30 | Request timeout in seconds |
| `max_retries` | 3 | Maximum retry attempts |
| `delay_between_requests` | 1.0 | Delay between requests (seconds) |
| `max_concurrent_requests` | 5 | Maximum concurrent requests |
| `output_directory` | `./crawled_content` | Directory for saved files |
| `requests_per_minute` | 60 | Rate limit for requests |
| `verify_ssl` | True | Verify SSL certificates |
| `allow_local_urls` | False | Allow local/private URLs |

## Architecture

```
web_crawler/
├── core/
│   ├── interfaces.py      # Abstract interfaces
│   ├── crawler.py         # Main crawler implementation
│   └── extractor.py       # Content extraction
├── storage/
│   └── file_handler.py    # File storage management
├── utils/
│   ├── validators.py      # URL validation
│   ├── text_processor.py  # Text processing utilities
│   └── exceptions.py      # Custom exceptions
└── config/
    └── settings.py        # Configuration management
```

## Security Features

- **SSRF Protection**: Blocks access to local/private networks
- **Content Validation**: Validates content types and sizes
- **Input Sanitization**: Sanitizes URLs and filenames
- **Rate Limiting**: Prevents abuse and respects server resources
- **SSL Verification**: Ensures secure connections

## Error Handling

The crawler provides comprehensive error handling with specific exception types:

```python
from web_crawler.utils.exceptions import (
    CrawlerError, NetworkError, ValidationError, StorageError
)

try:
    result = await crawler.crawl_and_save(url)
except ValidationError as e:
    print(f"Invalid URL: {e}")
except NetworkError as e:
    print(f"Network error: {e}")
except StorageError as e:
    print(f"Storage error: {e}")
except CrawlerError as e:
    print(f"General crawler error: {e}")
```

## Output Format

Crawled content is saved as text files with optional metadata:

```
crawled_content/
├── example.com/
│   ├── example.com_index.txt      # Main content
│   └── example.com_index.meta.json # Metadata
└── httpbin.org/
    ├── httpbin.org_html.txt
    └── httpbin.org_html.meta.json
```

### Metadata Structure

```json
{
  "title": "Page Title",
  "description": "Page description",
  "source_url": "https://example.com",
  "crawled_at": "2024-01-01T12:00:00Z",
  "content_length": 1234,
  "status_code": 200,
  "content_type": "text/html"
}
```

## Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=web_crawler

# Run specific test file
pytest tests/test_crawler.py
```

## Examples

See `example.py` for comprehensive usage examples:

```bash
python web_crawler/example.py
```

## Production Deployment

### Docker Support

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY web_crawler/ ./web_crawler/
CMD ["python", "-m", "web_crawler.example"]
```

### Monitoring

The crawler supports structured logging and metrics collection:

```python
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.WriteLoggerFactory(),
    wrapper_class=structlog.BoundLogger,
    cache_logger_on_first_use=True,
)
```

## License

This project is licensed under the MIT License.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Support

For issues and questions, please create an issue in the repository.
