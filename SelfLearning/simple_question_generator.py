#!/usr/bin/env python3
"""
Simple Question Generator CLI

This script generates 10 exploratory questions from content summaries.
The questions are designed to be placed after paragraphs without specific positioning.

Usage:
    python simple_question_generator.py --input-dir summaries --output-dir simple_questions
    python simple_question_generator.py --file summaries/example.summary.json
"""

import asyncio
import argparse
import logging
from pathlib import Path
import sys

from llm_service.services.simple_question_generator import SimpleQuestionGeneratorService


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


async def generate_from_single_file(file_path: Path, output_dir: Path) -> None:
    """Generate questions from a single summary file"""
    generator = SimpleQuestionGeneratorService()
    
    try:
        question_set = await generator.generate_from_summary_file(file_path, output_dir)
        print(f"✅ Successfully generated questions for: {file_path.name}")
        print(f"   Questions: {question_set.total_questions}")
        print(f"   Average confidence: {question_set.average_confidence:.2f}")
        print(f"   Content: {question_set.content_title}")
        print()
        
        # Show sample questions
        if question_set.questions:
            print("📝 Sample questions:")
            for i, q in enumerate(question_set.questions[:3]):
                print(f"   {i+1}. {q.question}")
            if len(question_set.questions) > 3:
                print(f"   ... and {len(question_set.questions) - 3} more")
            print()
        
    except Exception as e:
        print(f"❌ Failed to generate questions for {file_path.name}: {e}")


async def generate_from_directory(input_dir: Path, output_dir: Path) -> None:
    """Generate questions from all summary files in a directory"""
    generator = SimpleQuestionGeneratorService()
    
    try:
        question_sets = await generator.batch_generate(input_dir, output_dir)
        
        print(f"\n📊 Question Generation Complete!")
        print(f"   Processed: {len(question_sets)} files")
        
        if question_sets:
            total_questions = sum(qs.total_questions for qs in question_sets)
            avg_confidence = sum(qs.average_confidence for qs in question_sets) / len(question_sets)
            
            print(f"   Total questions generated: {total_questions}")
            print(f"   Average confidence: {avg_confidence:.2f}")
            
            # Show question type distribution
            question_types = {}
            for qs in question_sets:
                for q in qs.questions:
                    question_types[q.question_type] = question_types.get(q.question_type, 0) + 1
            
            if question_types:
                print(f"   Question types:")
                for qtype, count in sorted(question_types.items()):
                    print(f"     - {qtype}: {count}")
        
    except Exception as e:
        print(f"❌ Batch question generation failed: {e}")


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Generate exploratory questions from content summaries",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate questions from all summary files in a directory
  python simple_question_generator.py --input-dir summaries --output-dir simple_questions
  
  # Generate questions from a single summary file
  python simple_question_generator.py --file summaries/example.summary.json --output-dir simple_questions
  
  # Enable debug logging
  python simple_question_generator.py --input-dir summaries --output-dir simple_questions --debug
        """
    )
    
    # Input options (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '--input-dir',
        type=Path,
        help='Directory containing summary files to process'
    )
    input_group.add_argument(
        '--file',
        type=Path,
        help='Single summary file to process'
    )
    
    # Output options
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('simple_questions'),
        help='Directory to save questions (default: simple_questions)'
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
    
    print("🔄 Starting question generation...")
    print(f"   Output directory: {args.output_dir}")
    print()
    
    # Process based on input type
    if args.input_dir:
        await generate_from_directory(args.input_dir, args.output_dir)
    else:
        await generate_from_single_file(args.file, args.output_dir)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Question generation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)
