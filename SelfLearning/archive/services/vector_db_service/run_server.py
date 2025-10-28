"""
Vector DB Service - Server Runner.
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import uvicorn
except ImportError:
    print("Error: uvicorn not installed. Install: pip install uvicorn")
    sys.exit(1)


def main():
    """Run the Vector DB Service."""
    parser = argparse.ArgumentParser(description="Vector DB Service")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host")
    parser.add_argument("--port", type=int, default=8004, help="Port")
    parser.add_argument("--reload", action="store_true", help="Auto-reload")
    parser.add_argument("--debug", action="store_true", help="Debug logging")
    parser.add_argument("--workers", type=int, default=1, help="Workers")
    
    args = parser.parse_args()
    
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 70)
    logger.info("🗄️  VECTOR DB SERVICE")
    logger.info("=" * 70)
    logger.info(f"Host: {args.host}")
    logger.info(f"Port: {args.port}")
    logger.info(f"Debug: {args.debug}")
    logger.info("=" * 70)
    logger.info(f"📖 Swagger: http://{'localhost' if args.host == '0.0.0.0' else args.host}:{args.port}/docs")
    logger.info("=" * 70)
    
    uvicorn.run(
        "vector_db_service.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,
        log_level="debug" if args.debug else "info"
    )


if __name__ == "__main__":
    main()

