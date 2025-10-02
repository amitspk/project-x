#!/usr/bin/env python3
"""
Blog Question Generator CLI

This script generates exploratory questions from blog content with metadata
for JavaScript library injection and placement.

Usage:
    python blog_question_generator.py --content "blog content here"
    python blog_question_generator.py --file blog.txt --title "Blog Title"
    python blog_question_generator.py --url https://example.com/blog --num-questions 15
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
from llm_service.services.question_generator import QuestionGenerator
from llm_service.models.question_schema import question_set_to_json


async def generate_questions_from_content(
    content: str,
    title: str = "",
    content_id: str = "",
    content_url: Optional[str] = None,
    num_questions: int = 10,
    output_file: Optional[str] = None
):
    """Generate questions from content and output results."""
    
    print("🔄 Initializing LLM service...")
    
    # Initialize LLM service
    llm_service = LLMService()
    await llm_service.initialize()
    
    if not llm_service.get_available_providers():
        print("❌ No LLM providers available. Please configure API keys.")
        return
    
    print(f"✅ Using LLM provider: {llm_service.get_available_providers()[0]}")
    
    # Initialize question generator
    question_generator = QuestionGenerator(llm_service)
    
    print(f"🤖 Generating {num_questions} exploratory questions...")
    print(f"📝 Content length: {len(content)} characters")
    print(f"📋 Title: {title or 'Auto-detected'}")
    print("=" * 60)
    
    try:
        # Generate questions
        question_set = await question_generator.generate_questions(
            content=content,
            title=title,
            content_id=content_id,
            content_url=content_url,
            num_questions=num_questions
        )
        
        # Convert to JSON
        json_output = question_set_to_json(question_set)
        
        # Output results
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(json_output)
            print(f"💾 Questions saved to: {output_file}")
        else:
            print("📄 Generated Questions JSON:")
            print(json_output)
        
        # Show summary
        print("\n" + "=" * 60)
        print("📊 GENERATION SUMMARY")
        print("=" * 60)
        print(f"🎯 Content Topic: {question_set.content_context.topic}")
        print(f"📚 Difficulty Level: {question_set.content_context.difficulty_level}")
        print(f"📖 Content Type: {question_set.content_context.content_type}")
        print(f"⏱️  Reading Time: {question_set.content_context.estimated_reading_time} minutes")
        print(f"🔑 Keywords: {', '.join(question_set.content_context.keywords[:5])}")
        print(f"❓ Total Questions: {question_set.total_questions}")
        print(f"🎯 Average Confidence: {question_set.average_confidence:.2f}")
        
        print(f"\n📋 Question Types Distribution:")
        type_counts = {}
        for q in question_set.questions:
            q_type = q.question_type.value
            type_counts[q_type] = type_counts.get(q_type, 0) + 1
        
        for q_type, count in sorted(type_counts.items()):
            print(f"   • {q_type}: {count}")
        
        print(f"\n🎯 Question Placement:")
        placement_counts = {}
        for q in question_set.questions:
            placement = q.metadata.placement_strategy.value
            placement_counts[placement] = placement_counts.get(placement, 0) + 1
        
        for placement, count in sorted(placement_counts.items()):
            print(f"   • {placement}: {count}")
        
        print(f"\n✨ Sample Questions:")
        for i, question in enumerate(question_set.questions[:3], 1):
            print(f"   {i}. {question.question}")
            print(f"      → After paragraph {question.metadata.target_paragraph.paragraph_index}")
            print(f"      → Type: {question.question_type.value}")
            print(f"      → Confidence: {question.confidence_score:.2f}")
            print()
        
        return question_set
        
    except Exception as e:
        print(f"❌ Error generating questions: {e}")
        import traceback
        traceback.print_exc()
        return None


async def generate_from_file(file_path: str, **kwargs):
    """Generate questions from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if not kwargs.get('content_id'):
            kwargs['content_id'] = Path(file_path).stem
        
        return await generate_questions_from_content(content, **kwargs)
        
    except Exception as e:
        print(f"❌ Error reading file {file_path}: {e}")
        return None


async def generate_from_url(url: str, **kwargs):
    """Generate questions from a URL (requires web crawler)."""
    try:
        # Import web crawler
        from web_crawler import WebCrawler
        from web_crawler.config.settings import CrawlerConfig
        
        print(f"🌐 Crawling content from: {url}")
        
        # Initialize crawler
        config = CrawlerConfig()
        crawler = WebCrawler(config)
        
        # Crawl the URL
        result = await crawler.crawl(url)
        content = result['content']
        title = result['metadata'].get('title', '')
        
        if not kwargs.get('content_id'):
            kwargs['content_id'] = url.split('/')[-1] or 'web_content'
        
        kwargs['content_url'] = url
        
        return await generate_questions_from_content(content, title=title, **kwargs)
        
    except ImportError:
        print("❌ Web crawler not available. Please provide content directly or via file.")
        return None
    except Exception as e:
        print(f"❌ Error crawling URL {url}: {e}")
        return None


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate exploratory questions from blog content",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # From direct content
  python blog_question_generator.py --content "Your blog content here..." --title "Blog Title"
  
  # From file
  python blog_question_generator.py --file blog.txt --title "My Blog Post" --num-questions 15
  
  # From URL (requires web crawler)
  python blog_question_generator.py --url https://example.com/blog --output questions.json
  
  # With custom settings
  python blog_question_generator.py --file blog.txt --content-id "blog_001" --num-questions 12
        """
    )
    
    # Content source (mutually exclusive)
    content_group = parser.add_mutually_exclusive_group(required=True)
    content_group.add_argument(
        "--content", "-c",
        help="Blog content as string"
    )
    content_group.add_argument(
        "--file", "-f",
        help="Path to file containing blog content"
    )
    content_group.add_argument(
        "--url", "-u",
        help="URL to crawl for blog content"
    )
    
    # Optional parameters
    parser.add_argument(
        "--title", "-t",
        default="",
        help="Title of the blog post"
    )
    
    parser.add_argument(
        "--content-id",
        help="Unique identifier for the content"
    )
    
    parser.add_argument(
        "--num-questions", "-n",
        type=int,
        default=10,
        help="Number of questions to generate (default: 10)"
    )
    
    parser.add_argument(
        "--output", "-o",
        help="Output file path for JSON results"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="Blog Question Generator 1.0.0"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.num_questions < 1 or args.num_questions > 20:
        print("❌ Number of questions must be between 1 and 20")
        sys.exit(1)
    
    # Run the appropriate generator
    try:
        if args.content:
            result = asyncio.run(generate_questions_from_content(
                content=args.content,
                title=args.title,
                content_id=args.content_id or "direct_content",
                num_questions=args.num_questions,
                output_file=args.output
            ))
        elif args.file:
            result = asyncio.run(generate_from_file(
                file_path=args.file,
                title=args.title,
                content_id=args.content_id,
                num_questions=args.num_questions,
                output_file=args.output
            ))
        elif args.url:
            result = asyncio.run(generate_from_url(
                url=args.url,
                title=args.title,
                content_id=args.content_id,
                num_questions=args.num_questions,
                output_file=args.output
            ))
        
        if result:
            print("\n✅ Question generation completed successfully!")
        else:
            print("\n❌ Question generation failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n👋 Question generation interrupted by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
