#!/usr/bin/env python3
"""
LLM Service - Standalone Server

Run this to start the LLM Service as an independent microservice.
"""

import sys
import os
import logging
import argparse

# Add parent directory to path so we can import llm_service
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="LLM Service - Standalone Microservice")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8002, help="Port to listen on")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    
    args = parser.parse_args()
    
    logger.info("=" * 70)
    logger.info("🚀 Starting LLM Service")
    logger.info("=" * 70)
    logger.info(f"📊 Version: 1.0.0")
    logger.info(f"🌐 Host: {args.host}:{args.port}")
    logger.info(f"🔧 Debug Mode: {args.debug}")
    logger.info(f"🔄 Auto-reload: {args.reload}")
    logger.info("=" * 70)
    
    # Run the service
    uvicorn.run(
        "llm_service.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="debug" if args.debug else "info"
    )


if __name__ == "__main__":
    main()

