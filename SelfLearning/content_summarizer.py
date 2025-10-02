#!/usr/bin/env python3
"""
Content Summarizer CLI

This script generates summaries from crawled content files.
The summaries can then be used for question generation.

Usage:
    python content_summarizer.py --input-dir crawled_content --output-dir summaries
    python content_summarizer.py --file crawled_content/example.content.json
"""

import asyncio
import argparse
import logging
from pathlib import Path
import sys

from llm_service.services.content_summarizer import ContentSummarizerService


def setup_logging(debug: bool = False) -> None:
    """Setup logging configuration"""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


async def summarize_single_file(file_path: Path, output_dir: Path) -> None:
    """Summarize a single content file"""
    summarizer = ContentSummarizerService()
    
    try:
        summary = await summarizer.summarize_from_file(file_path, output_dir)
        print(f"✅ Successfully summarized: {file_path.name}")
        print(f"   Summary: {summary.word_count} words (compression: {summary.compression_ratio:.2%})")
        print(f"   Confidence: {summary.confidence_score:.2f}")
        print(f"   Topics: {', '.join(summary.topics)}")
        print()
        
    except Exception as e:
        print(f"❌ Failed to summarize {file_path.name}: {e}")


async def summarize_directory(input_dir: Path, output_dir: Path) -> None:
    """Summarize all content files in a directory"""
    summarizer = ContentSummarizerService()
    
    try:
        summaries = await summarizer.batch_summarize(input_dir, output_dir)
        
        print(f"\n📊 Summarization Complete!")
        print(f"   Processed: {len(summaries)} files")
        
        if summaries:
            avg_compression = sum(s.compression_ratio for s in summaries) / len(summaries)
            avg_confidence = sum(s.confidence_score for s in summaries) / len(summaries)
            total_original_words = sum(s.original_word_count for s in summaries)
            total_summary_words = sum(s.word_count for s in summaries)
            
            print(f"   Average compression: {avg_compression:.2%}")
            print(f"   Average confidence: {avg_confidence:.2f}")
            print(f"   Total words: {total_original_words:,} → {total_summary_words:,}")
        
    except Exception as e:
        print(f"❌ Batch summarization failed: {e}")


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Generate summaries from crawled content",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Summarize all content files in a directory
  python content_summarizer.py --input-dir crawled_content --output-dir summaries
  
  # Summarize a single file
  python content_summarizer.py --file crawled_content/example.content.json --output-dir summaries
  
  # Enable debug logging
  python content_summarizer.py --input-dir crawled_content --output-dir summaries --debug
        """
    )
    
    # Input options (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '--input-dir',
        type=Path,
        help='Directory containing content files to summarize'
    )
    input_group.add_argument(
        '--file',
        type=Path,
        help='Single content file to summarize'
    )
    
    # Output options
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('summaries'),
        help='Directory to save summaries (default: summaries)'
    )
    
    # Other options
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.debug)
    
    # Validate inputs
    if args.input_dir and not args.input_dir.exists():
        print(f"❌ Input directory does not exist: {args.input_dir}")
        sys.exit(1)
    
    if args.file and not args.file.exists():
        print(f"❌ Input file does not exist: {args.file}")
        sys.exit(1)
    
    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    print("🔄 Starting content summarization...")
    print(f"   Output directory: {args.output_dir}")
    print()
    
    # Process based on input type
    if args.input_dir:
        await summarize_directory(args.input_dir, args.output_dir)
    else:
        await summarize_single_file(args.file, args.output_dir)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Summarization interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)
