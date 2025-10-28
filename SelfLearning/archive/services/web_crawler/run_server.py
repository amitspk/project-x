"""
Web Crawler Service - Server Runner.

Standalone script to run the Web Crawler Service.
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import uvicorn
except ImportError:
    print("Error: uvicorn is not installed. Please install it with: pip install uvicorn")
    sys.exit(1)


def main():
    """Run the Web Crawler Service."""
    parser = argparse.ArgumentParser(description="Web Crawler Service")
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8003,
        help="Port to bind to (default: 8003)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload (development only)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (default: 1)"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 70)
    logger.info("🕷️  WEB CRAWLER SERVICE")
    logger.info("=" * 70)
    logger.info(f"Host: {args.host}")
    logger.info(f"Port: {args.port}")
    logger.info(f"Debug: {args.debug}")
    logger.info(f"Reload: {args.reload}")
    logger.info(f"Workers: {args.workers}")
    logger.info("=" * 70)
    logger.info("")
    logger.info("📖 Swagger UI: http://{}:{}/docs".format(
        args.host if args.host != "0.0.0.0" else "localhost", 
        args.port
    ))
    logger.info("📚 ReDoc: http://{}:{}/redoc".format(
        args.host if args.host != "0.0.0.0" else "localhost",
        args.port
    ))
    logger.info("")
    logger.info("Starting server...")
    logger.info("=" * 70)
    
    # Run server
    uvicorn.run(
        "web_crawler.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,
        log_level="debug" if args.debug else "info"
    )


if __name__ == "__main__":
    main()

