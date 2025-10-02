#!/usr/bin/env python3
"""
Content Processor CLI

This script processes blog content from the crawled_content folder,
generates Q&A files using the LLM service, and manages the complete workflow.

Usage:
    python content_processor.py --discover          # Discover new content
    python content_processor.py --process-all       # Process all unprocessed content
    python content_processor.py --process-id content_id  # Process specific content
    python content_processor.py --status            # Show processing status
    python content_processor.py --list-questions    # List generated questions
"""

import asyncio
import argparse
import sys
import json
from pathlib import Path
from typing import Optional

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from llm_service import LLMService
from llm_service.repositories import FileContentRepository
from llm_service.repositories.interfaces import ContentFilter
from llm_service.repositories.models import ProcessingStatus
from llm_service.services.content_service import ContentProcessingService, ContentDiscoveryService


async def discover_content(
    crawled_content_path: str = "crawled_content",
    index_file: Optional[str] = None
):
    """Discover new content in the repository."""
    print("🔍 Discovering content in repository...")
    
    # Initialize repository
    repository = FileContentRepository(
        crawled_content_path=crawled_content_path,
        index_file_path=index_file
    )
    await repository.initialize()
    
    # Initialize discovery service
    discovery_service = ContentDiscoveryService(repository)
    
    # Discover new content
    result = await discovery_service.discover_new_content()
    
    print(f"✅ Discovery completed!")
    print(f"   📁 New content found: {result['new_content_found']}")
    print(f"   ⏰ Discovery time: {result['discovery_time']}")
    
    # Get content summary
    summary = await discovery_service.get_content_summary()
    
    print(f"\n📊 Repository Summary:")
    print(f"   📄 Total content: {summary['statistics']['total_content']}")
    print(f"   📝 Total words: {summary['statistics']['total_word_count']:,}")
    print(f"   📈 Average words: {summary['statistics']['average_word_count']}")
    
    print(f"\n📋 Status Breakdown:")
    for status, count in summary['statistics']['status_breakdown'].items():
        print(f"   • {status}: {count}")
    
    print(f"\n📚 Content Types:")
    for content_type, count in summary['statistics']['content_type_breakdown'].items():
        print(f"   • {content_type}: {count}")
    
    if summary['sample_content']:
        print(f"\n📖 Sample Content:")
        for i, content in enumerate(summary['sample_content'][:3], 1):
            print(f"   {i}. {content['title']}")
            print(f"      ID: {content['content_id']}")
            print(f"      Words: {content['word_count']}, Status: {content['status']}")
            print()


async def process_all_content(
    crawled_content_path: str = "crawled_content",
    output_directory: str = "generated_questions",
    index_file: Optional[str] = None,
    num_questions: int = 10,
    batch_size: int = 5,
    max_concurrent: int = 2,
    force_reprocess: bool = False
):
    """Process all unprocessed content."""
    print("🚀 Starting batch content processing...")
    
    # Initialize LLM service
    print("🔄 Initializing LLM service...")
    llm_service = LLMService()
    await llm_service.initialize()
    
    if not llm_service.get_available_providers():
        print("❌ No LLM providers available. Please configure API keys.")
        return
    
    print(f"✅ Using LLM provider: {llm_service.get_available_providers()[0]}")
    
    # Initialize repository
    repository = FileContentRepository(
        crawled_content_path=crawled_content_path,
        index_file_path=index_file
    )
    await repository.initialize()
    
    # Initialize processing service
    processing_service = ContentProcessingService(
        content_repository=repository,
        llm_service=llm_service,
        output_directory=output_directory,
        max_concurrent_processing=max_concurrent
    )
    
    print(f"📁 Output directory: {output_directory}")
    print(f"❓ Questions per content: {num_questions}")
    print(f"📦 Batch size: {batch_size}")
    print(f"🔄 Max concurrent: {max_concurrent}")
    print(f"🔄 Force reprocess: {force_reprocess}")
    print("=" * 60)
    
    # Process all content
    try:
        stats = await processing_service.process_all_unprocessed(
            num_questions=num_questions,
            batch_size=batch_size,
            force_reprocess=force_reprocess
        )
        
        # Display results
        print("\n" + "=" * 60)
        print("📊 PROCESSING RESULTS")
        print("=" * 60)
        print(f"✅ Successfully processed: {stats['processed']}")
        print(f"❌ Failed: {stats['failed']}")
        print(f"⏭️  Skipped: {stats['skipped']}")
        print(f"❓ Total questions generated: {stats['total_questions_generated']}")
        
        if stats.get('duration_formatted'):
            print(f"⏱️  Duration: {stats['duration_formatted']}")
        
        if stats.get('success_rate'):
            print(f"📈 Success rate: {stats['success_rate']:.1%}")
        
        print(f"\n💾 Questions saved to: {output_directory}")
        
    except Exception as e:
        print(f"❌ Processing failed: {e}")
        import traceback
        traceback.print_exc()


async def process_single_content(
    content_id: str,
    crawled_content_path: str = "crawled_content",
    output_directory: str = "generated_questions",
    index_file: Optional[str] = None,
    num_questions: int = 10,
    force_reprocess: bool = False
):
    """Process a single content item."""
    print(f"🎯 Processing single content: {content_id}")
    
    # Initialize LLM service
    print("🔄 Initializing LLM service...")
    llm_service = LLMService()
    await llm_service.initialize()
    
    if not llm_service.get_available_providers():
        print("❌ No LLM providers available. Please configure API keys.")
        return
    
    # Initialize repository
    repository = FileContentRepository(
        crawled_content_path=crawled_content_path,
        index_file_path=index_file
    )
    await repository.initialize()
    
    # Initialize processing service
    processing_service = ContentProcessingService(
        content_repository=repository,
        llm_service=llm_service,
        output_directory=output_directory
    )
    
    # Process the content
    try:
        question_set = await processing_service.process_single_content(
            content_id=content_id,
            num_questions=num_questions,
            force_reprocess=force_reprocess
        )
        
        if question_set:
            print(f"✅ Successfully processed: {content_id}")
            print(f"❓ Questions generated: {question_set.total_questions}")
            print(f"🎯 Average confidence: {question_set.average_confidence:.2f}")
            print(f"📝 Topic: {question_set.content_context.topic}")
            print(f"💾 Output saved to: {output_directory}")
        else:
            print(f"⚠️  No processing performed for: {content_id}")
            
    except Exception as e:
        print(f"❌ Processing failed: {e}")


async def show_processing_status(
    crawled_content_path: str = "crawled_content",
    output_directory: str = "generated_questions",
    index_file: Optional[str] = None
):
    """Show current processing status."""
    print("📊 Processing Status")
    print("=" * 60)
    
    # Initialize repository
    repository = FileContentRepository(
        crawled_content_path=crawled_content_path,
        index_file_path=index_file
    )
    await repository.initialize()
    
    # Initialize LLM service (without full initialization)
    llm_service = LLMService()
    
    # Initialize processing service
    processing_service = ContentProcessingService(
        content_repository=repository,
        llm_service=llm_service,
        output_directory=output_directory
    )
    
    # Get status
    status = await processing_service.get_processing_status()
    
    # Repository statistics
    repo_stats = status['repository_stats']
    print(f"📁 Repository: {crawled_content_path}")
    print(f"📄 Total content: {repo_stats['total_content']}")
    print(f"📝 Total words: {repo_stats['total_word_count']:,}")
    print(f"📈 Average words: {repo_stats['average_word_count']}")
    
    print(f"\n📋 Status Breakdown:")
    for status_name, count in repo_stats['status_breakdown'].items():
        print(f"   • {status_name}: {count}")
    
    print(f"\n📚 Content Types:")
    for content_type, count in repo_stats['content_type_breakdown'].items():
        print(f"   • {content_type}: {count}")
    
    print(f"\n⚙️  Processing Configuration:")
    print(f"   📁 Output directory: {status['output_directory']}")
    print(f"   🔄 Max concurrent: {status['max_concurrent_processing']}")
    
    # Show recent processing stats if available
    proc_stats = status['processing_stats']
    if proc_stats['processed'] > 0 or proc_stats['failed'] > 0:
        print(f"\n📊 Recent Processing:")
        print(f"   ✅ Processed: {proc_stats['processed']}")
        print(f"   ❌ Failed: {proc_stats['failed']}")
        print(f"   ⏭️  Skipped: {proc_stats['skipped']}")
        print(f"   ❓ Questions generated: {proc_stats['total_questions_generated']}")


async def list_generated_questions(
    output_directory: str = "generated_questions"
):
    """List all generated question files."""
    print("📋 Generated Question Files")
    print("=" * 60)
    
    output_path = Path(output_directory)
    if not output_path.exists():
        print(f"❌ Output directory does not exist: {output_directory}")
        return
    
    # Find all JSON files
    question_files = list(output_path.rglob("*.json"))
    
    if not question_files:
        print(f"📭 No question files found in: {output_directory}")
        return
    
    # Sort by modification time (newest first)
    question_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    print(f"📁 Found {len(question_files)} question files:")
    print()
    
    for i, file_path in enumerate(question_files[:10], 1):  # Show first 10
        try:
            stat = file_path.stat()
            size_kb = stat.st_size / 1024
            
            # Try to read basic info from the file
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                title = data.get('content_title', 'Unknown Title')
                question_count = data.get('total_questions', 0)
                avg_confidence = data.get('average_confidence', 0)
                
                print(f"{i:2d}. {file_path.name}")
                print(f"    📝 Title: {title[:60]}{'...' if len(title) > 60 else ''}")
                print(f"    ❓ Questions: {question_count}, Confidence: {avg_confidence:.2f}")
                print(f"    📊 Size: {size_kb:.1f} KB")
                print(f"    📅 Modified: {stat.st_mtime}")
                print()
                
            except json.JSONDecodeError:
                print(f"{i:2d}. {file_path.name} (Invalid JSON)")
                print(f"    📊 Size: {size_kb:.1f} KB")
                print()
                
        except Exception as e:
            print(f"{i:2d}. {file_path.name} (Error reading file: {e})")
            print()
    
    if len(question_files) > 10:
        print(f"... and {len(question_files) - 10} more files")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Process blog content and generate Q&A files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Discover new content
  python content_processor.py --discover
  
  # Process all unprocessed content
  python content_processor.py --process-all --num-questions 8
  
  # Process specific content
  python content_processor.py --process-id "example_com_blog_post"
  
  # Show status
  python content_processor.py --status
  
  # List generated questions
  python content_processor.py --list-questions
  
  # Custom paths and settings
  python content_processor.py --process-all --crawled-path ./my_content --output ./my_questions
        """
    )
    
    # Main actions (mutually exclusive)
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument(
        "--discover",
        action="store_true",
        help="Discover new content in the repository"
    )
    action_group.add_argument(
        "--process-all",
        action="store_true",
        help="Process all unprocessed content"
    )
    action_group.add_argument(
        "--process-id",
        help="Process specific content by ID"
    )
    action_group.add_argument(
        "--status",
        action="store_true",
        help="Show processing status"
    )
    action_group.add_argument(
        "--list-questions",
        action="store_true",
        help="List generated question files"
    )
    
    # Configuration options
    parser.add_argument(
        "--crawled-path",
        default="crawled_content",
        help="Path to crawled content directory (default: crawled_content)"
    )
    parser.add_argument(
        "--output",
        default="generated_questions",
        help="Output directory for generated questions (default: generated_questions)"
    )
    parser.add_argument(
        "--index-file",
        help="Path to index file for content persistence"
    )
    parser.add_argument(
        "--num-questions",
        type=int,
        default=10,
        help="Number of questions to generate per content (default: 10)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5,
        help="Batch size for processing (default: 5)"
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=2,
        help="Maximum concurrent processing tasks (default: 2)"
    )
    parser.add_argument(
        "--force-reprocess",
        action="store_true",
        help="Force reprocessing of already completed content"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="Content Processor 1.0.0"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.num_questions < 1 or args.num_questions > 20:
        print("❌ Number of questions must be between 1 and 20")
        sys.exit(1)
    
    if args.batch_size < 1 or args.batch_size > 50:
        print("❌ Batch size must be between 1 and 50")
        sys.exit(1)
    
    if args.max_concurrent < 1 or args.max_concurrent > 10:
        print("❌ Max concurrent must be between 1 and 10")
        sys.exit(1)
    
    # Run the appropriate action
    try:
        if args.discover:
            asyncio.run(discover_content(
                crawled_content_path=args.crawled_path,
                index_file=args.index_file
            ))
        elif args.process_all:
            asyncio.run(process_all_content(
                crawled_content_path=args.crawled_path,
                output_directory=args.output,
                index_file=args.index_file,
                num_questions=args.num_questions,
                batch_size=args.batch_size,
                max_concurrent=args.max_concurrent,
                force_reprocess=args.force_reprocess
            ))
        elif args.process_id:
            asyncio.run(process_single_content(
                content_id=args.process_id,
                crawled_content_path=args.crawled_path,
                output_directory=args.output,
                index_file=args.index_file,
                num_questions=args.num_questions,
                force_reprocess=args.force_reprocess
            ))
        elif args.status:
            asyncio.run(show_processing_status(
                crawled_content_path=args.crawled_path,
                output_directory=args.output,
                index_file=args.index_file
            ))
        elif args.list_questions:
            asyncio.run(list_generated_questions(
                output_directory=args.output
            ))
        
        print("\n✅ Operation completed successfully!")
        
    except KeyboardInterrupt:
        print("\n👋 Operation interrupted by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
