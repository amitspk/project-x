"""
Web Crawler Module

A production-grade web crawler for extracting and storing web content.

Classes:
    WebCrawler: Main crawler implementation
    ContentExtractor: Content extraction and processing
    FileStorage: File storage management
    
Functions:
    crawl_and_save: Simple function to crawl URL and save content
"""

from .core.crawler import WebCrawler
from .core.extractor import ContentExtractor
from .storage.file_handler import FileStorage
from .utils.validators import URLValidator
from .config.settings import CrawlerConfig

__version__ = "1.0.0"
__author__ = "Production Team"

__all__ = [
    "WebCrawler",
    "ContentExtractor", 
    "FileStorage",
    "URLValidator",
    "CrawlerConfig"
]
