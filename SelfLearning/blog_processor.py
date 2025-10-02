#!/usr/bin/env python3
"""
Blog Processor - Production Pipeline

Complete pipeline for processing blog articles:
1. Web crawling using existing web_crawler module
2. Content summarization (when LLM is available)
3. Question generation from summaries
4. Output ready for Chrome extension

Usage:
    python3 blog_processor.py --url "https://example.com/article"
    python3 blog_processor.py --url "https://medium.com/article" --output-dir results
"""

import asyncio
import argparse
import json
import logging
from pathlib import Path
import sys
from datetime import datetime
from urllib.parse import urlparse
import hashlib

# Import the existing web crawler
from web_crawler import WebCrawler
from web_crawler.config.settings import CrawlerConfig


class BlogProcessor:
    """Production blog processing pipeline"""
    
    def __init__(self, url: str, output_dir: Path = None):
        self.url = url
        self.output_dir = output_dir or Path("processed_content")
        self.logger = logging.getLogger(__name__)
        
    async def process_blog(self):
        """Process a blog article through the complete pipeline"""
        print("🚀 Blog Processing Pipeline")
        print("=" * 50)
        print(f"URL: {self.url}")
        print(f"Output: {self.output_dir}")
        print()
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Step 1: Web Crawling
            crawl_result = await self._crawl_content()
            if not crawl_result:
                return False
            
            # Step 2: Content Processing
            processing_result = await self._process_content(crawl_result)
            if not processing_result:
                return False
            
            # Step 3: Generate Output
            final_result = self._generate_output(crawl_result, processing_result)
            
            # Step 4: Show Results
            self._show_results(final_result)
            
            return True
            
        except Exception as e:
            print(f"💥 Processing failed: {e}")
            self.logger.error(f"Processing failed: {e}", exc_info=True)
            return False
    
    async def _crawl_content(self):
        """Step 1: Web crawling"""
        print("🌐 Step 1: Web Crawling")
        print("-" * 30)
        
        try:
            # Configure crawler
            config = CrawlerConfig()
            config.timeout = 30
            config.max_retries = 3
            config.user_agent = "BlogProcessor/1.0"
            
            # Initialize and crawl
            crawler = WebCrawler(config)
            print(f"🚀 Crawling: {self.url}")
            
            result = await crawler.crawl_and_save(self.url)
            
            if result and 'content' in result and result['content']:
                print("✅ Web crawling successful!")
                print(f"   Content: {len(result['content']):,} characters")
                print(f"   Title: {result['metadata'].get('title', 'N/A')}")
                print()
                
                return {
                    "url": self.url,
                    "title": result['metadata'].get('title', ''),
                    "content": result['content'],
                    "metadata": result['metadata'],
                    "crawled_at": result.get('crawled_at', datetime.now().isoformat())
                }
            else:
                print("❌ Web crawling failed - no content retrieved")
                return None
                
        except Exception as e:
            print(f"💥 Web crawling error: {e}")
            return None
        finally:
            if 'crawler' in locals():
                await crawler.close()
    
    async def _process_content(self, crawl_result):
        """Step 2: Content processing (summarization + questions)"""
        print("📝 Step 2: Content Processing")
        print("-" * 30)
        
        try:
            # Try to use LLM services
            try:
                from llm_service.services.content_summarizer import ContentSummarizerService
                from llm_service.services.simple_question_generator import SimpleQuestionGeneratorService
                
                print("🤖 Using LLM services...")
                
                # Generate summary
                summarizer = ContentSummarizerService()
                summary = await summarizer.summarize_content(
                    content=crawl_result['content'],
                    title=crawl_result['title'],
                    url=crawl_result['url'],
                    content_id=self._generate_content_id(crawl_result['title']),
                    target_length="medium"
                )
                
                # Generate questions
                generator = SimpleQuestionGeneratorService()
                question_set = await generator.generate_questions_from_summary(
                    summary=summary.summary,
                    title=summary.title,
                    content_id=summary.content_id,
                    url=summary.url,
                    num_questions=10
                )
                
                print("✅ LLM processing successful!")
                print(f"   Summary: {summary.word_count} words")
                print(f"   Questions: {question_set.total_questions}")
                print()
                
                return {
                    "method": "llm",
                    "summary": summary,
                    "questions": question_set
                }
                
            except Exception as llm_error:
                print(f"⚠️  LLM services unavailable: {llm_error}")
                print("❌ Cannot process without LLM services")
                print("💡 Please configure LLM API keys or use demo mode")
                return None
                
        except Exception as e:
            print(f"💥 Content processing error: {e}")
            return None
    
    def _generate_output(self, crawl_result, processing_result):
        """Step 3: Generate output files"""
        print("💾 Step 3: Generate Output")
        print("-" * 30)
        
        content_id = self._generate_content_id(crawl_result['title'])
        
        # Save summary
        summary_file = self.output_dir / f"{content_id}.summary.json"
        summary_data = {
            "content_id": processing_result['summary'].content_id,
            "title": processing_result['summary'].title,
            "url": processing_result['summary'].url,
            "summary": processing_result['summary'].summary,
            "key_points": processing_result['summary'].key_points,
            "topics": processing_result['summary'].topics,
            "word_count": processing_result['summary'].word_count,
            "original_word_count": processing_result['summary'].original_word_count,
            "compression_ratio": processing_result['summary'].compression_ratio,
            "confidence_score": processing_result['summary'].confidence_score
        }
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)
        
        # Save questions (Chrome extension format)
        questions_file = self.output_dir / f"{content_id}.questions.json"
        questions_data = {
            "content_id": processing_result['questions'].content_id,
            "content_title": processing_result['questions'].content_title,
            "content_url": processing_result['questions'].content_url,
            "summary": processing_result['questions'].summary,
            "questions": [
                {
                    "id": q.id,
                    "question": q.question,
                    "answer": q.answer,
                    "question_type": q.question_type,
                    "confidence_score": q.confidence_score,
                    "estimated_answer_time": q.estimated_answer_time
                }
                for q in processing_result['questions'].questions
            ],
            "total_questions": processing_result['questions'].total_questions,
            "average_confidence": processing_result['questions'].average_confidence,
            "generated_at": processing_result['questions'].generated_at
        }
        
        with open(questions_file, 'w', encoding='utf-8') as f:
            json.dump(questions_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Output generated!")
        print(f"   Summary: {summary_file}")
        print(f"   Questions: {questions_file}")
        print()
        
        return {
            "summary_file": summary_file,
            "questions_file": questions_file,
            "content_id": content_id
        }
    
    def _show_results(self, final_result):
        """Step 4: Show results and usage instructions"""
        print("🎯 Processing Complete!")
        print("-" * 30)
        print("✅ Blog processing finished successfully!")
        print()
        print("📁 Generated Files:")
        print(f"   📄 Summary: {final_result['summary_file']}")
        print(f"   ❓ Questions: {final_result['questions_file']}")
        print()
        print("🌐 Chrome Extension Usage:")
        print("   1. Load 'Blog Question Injector' extension")
        print("   2. Go to any website with paragraphs")
        print("   3. Upload the questions file:")
        print(f"      {final_result['questions_file']}")
        print("   4. Click 'Inject Custom Questions'")
        print("   5. Click questions to open answer drawers!")
        print()
        print("🎉 Ready for testing!")
    
    def _generate_content_id(self, title: str) -> str:
        """Generate content ID from title"""
        content_id = title.lower().replace(' ', '_').replace('-', '_')
        content_id = ''.join(c for c in content_id if c.isalnum() or c == '_')
        
        if len(content_id) > 50:
            hash_suffix = hashlib.md5(title.encode()).hexdigest()[:8]
            content_id = content_id[:40] + '_' + hash_suffix
        
        return content_id


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Process blog articles into questions for Chrome extension",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a Medium article
  python3 blog_processor.py --url "https://medium.com/article-url"
  
  # Process with custom output directory
  python3 blog_processor.py --url "https://example.com/blog" --output-dir my_results
  
  # Process Wikipedia article
  python3 blog_processor.py --url "https://en.wikipedia.org/wiki/Topic"
        """
    )
    
    parser.add_argument(
        '--url',
        type=str,
        required=True,
        help='Blog URL to process'
    )
    
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('processed_content'),
        help='Output directory (default: processed_content)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Validate URL
    try:
        parsed = urlparse(args.url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Invalid URL format")
    except Exception as e:
        print(f"❌ Invalid URL: {e}")
        sys.exit(1)
    
    # Process blog
    processor = BlogProcessor(args.url, args.output_dir)
    success = await processor.process_blog()
    
    if success:
        print("\n🎉 Blog processing completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Blog processing failed!")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)
