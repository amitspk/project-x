#!/usr/bin/env python3
"""
Blog Manager Microservice Startup Script

Starts the FastAPI server with proper configuration and error handling.
"""

import sys
import os
import uvicorn
import argparse
import logging
from pathlib import Path

# Add the parent directory to Python path so we can import the blog_manager module
sys.path.insert(0, str(Path(__file__).parent.parent))

from blog_manager.core.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format=settings.log_format
)
logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Blog Manager Microservice",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_server.py                          # Start with default settings
  python run_server.py --host 0.0.0.0 --port 8080  # Custom host and port
  python run_server.py --debug                  # Enable debug mode
  python run_server.py --reload                 # Enable auto-reload for development
        """
    )
    
    parser.add_argument(
        "--host",
        default=settings.api_host,
        help=f"Host to bind to (default: {settings.api_host})"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=settings.api_port,
        help=f"Port to bind to (default: {settings.api_port})"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (default: 1)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=settings.log_level.upper(),
        help=f"Log level (default: {settings.log_level.upper()})"
    )
    
    return parser.parse_args()


def check_dependencies():
    """Check if all required dependencies are available."""
    try:
        import fastapi
        import motor
        import pymongo
        import pydantic
        logger.info("✅ All required dependencies are available")
        return True
    except ImportError as e:
        logger.error(f"❌ Missing dependency: {e}")
        logger.error("Please install dependencies with: pip install -r requirements.txt")
        return False


def check_mongodb_connection():
    """Check if MongoDB is accessible."""
    try:
        from pymongo import MongoClient
        
        # Create a test connection
        client = MongoClient(
            settings.mongodb_url,
            serverSelectionTimeoutMS=5000  # 5 second timeout
        )
        
        # Test the connection
        client.admin.command('ping')
        client.close()
        
        logger.info("✅ MongoDB connection test successful")
        return True
        
    except Exception as e:
        logger.warning(f"⚠️  MongoDB connection test failed: {e}")
        logger.warning("The service will start but may not function properly without MongoDB")
        return False


def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Update settings with command line arguments
    if args.debug:
        settings.debug = True
        settings.log_level = "DEBUG"
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    logger.info("🚀 Starting Blog Manager Microservice")
    logger.info(f"📊 Version: {settings.app_version}")
    logger.info(f"🔧 Debug Mode: {settings.debug}")
    logger.info(f"🌐 Host: {args.host}:{args.port}")
    logger.info(f"🗄️  Database: {settings.mongodb_database}")
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Check MongoDB connection
    check_mongodb_connection()
    
    # Configure uvicorn
    uvicorn_config = {
        "app": "blog_manager.api.main:app",
        "host": args.host,
        "port": args.port,
        "log_level": args.log_level.lower(),
        "access_log": True,
    }
    
    # Development settings
    if args.reload or settings.debug:
        uvicorn_config.update({
            "reload": True,
            "reload_dirs": [str(Path(__file__).parent)],
        })
        logger.info("🔄 Auto-reload enabled")
    
    # Production settings
    if not settings.debug and args.workers > 1:
        uvicorn_config["workers"] = args.workers
        logger.info(f"👥 Using {args.workers} worker processes")
    
    try:
        logger.info("🎯 Starting server...")
        uvicorn.run(**uvicorn_config)
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
