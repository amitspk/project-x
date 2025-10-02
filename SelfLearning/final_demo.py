#!/usr/bin/env python3
"""
Final Demo - Complete Blog Processing Pipeline

This script demonstrates the complete flow:
1. Web crawling using existing web_crawler module
2. Content summarization (when LLM is available)
3. Question generation (when LLM is available)
4. Output ready for Chrome extension

Usage:
    python3 final_demo.py
"""

import asyncio
import json
import logging
from pathlib import Path
import sys
from datetime import datetime

# Import the existing web crawler
from web_crawler import WebCrawler
from web_crawler.config.settings import CrawlerConfig


# ============================================================================
# CONFIGURATION - Change this URL to crawl different articles
# ============================================================================

TARGET_URL = "https://medium.com/wehkamp-techblog/unit-testing-your-react-application-with-jest-and-enzyme-81c5545cee45"

# Alternative URLs you can try:
# TARGET_URL = "https://en.wikipedia.org/wiki/React_(JavaScript_library)"
# TARGET_URL = "https://reactjs.org/docs/getting-started.html"
# TARGET_URL = "https://jestjs.io/docs/getting-started"

# ============================================================================


class FinalDemo:
    """Final demo class that orchestrates the complete pipeline"""
    
    def __init__(self, url: str):
        self.url = url
        self.output_dir = Path("final_demo_results")
        self.logger = logging.getLogger(__name__)
        
    async def run_complete_demo(self):
        """Run the complete demo pipeline"""
        print("🚀 Final Demo - Complete Blog Processing Pipeline")
        print("=" * 60)
        print(f"Target URL: {self.url}")
        print(f"Output directory: {self.output_dir}")
        print()
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Step 1: Web Crawling
            crawl_result = await self.step1_web_crawling()
            if not crawl_result:
                return False
            
            # Step 2: Content Processing (summarization + questions)
            # For now, we'll create demo content since LLM might not be configured
            processing_result = await self.step2_content_processing(crawl_result)
            if not processing_result:
                return False
            
            # Step 3: Generate final output
            final_result = self.step3_generate_final_output(crawl_result, processing_result)
            
            # Step 4: Show usage instructions
            self.step4_show_usage_instructions(final_result)
            
            return True
            
        except Exception as e:
            print(f"💥 Demo failed with error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def step1_web_crawling(self):
        """Step 1: Web crawling using existing web_crawler module"""
        print("🌐 Step 1: Web Crawling")
        print("-" * 30)
        
        try:
            # Configure the crawler
            config = CrawlerConfig()
            config.timeout = 30
            config.max_retries = 3
            config.delay_between_requests = 1.0
            config.user_agent = "FinalDemo/1.0 (Educational Purpose)"
            
            print(f"🔧 Crawler configuration:")
            print(f"   Timeout: {config.timeout}s")
            print(f"   Max retries: {config.max_retries}")
            print(f"   User agent: {config.user_agent}")
            print()
            
            # Initialize and run crawler
            crawler = WebCrawler(config)
            print(f"🚀 Crawling: {self.url}")
            
            result = await crawler.crawl_and_save(self.url)
            
            # Check if we have content (success is implicit if no exception was raised)
            if result and 'content' in result and result['content']:
                print("✅ Web crawling successful!")
                print(f"   Content length: {len(result['content']):,} characters")
                print(f"   Title: {result['metadata'].get('title', 'N/A')}")
                print(f"   Saved to: {result.get('saved_to', 'N/A')}")
                print()
                
                # Save crawl result for next steps
                crawl_file = self.output_dir / "01_crawled_content.json"
                crawl_data = {
                    "url": self.url,
                    "title": result['metadata'].get('title', ''),
                    "content": result['content'],
                    "metadata": result['metadata'],
                    "crawled_at": result.get('crawled_at', datetime.now().isoformat()),
                    "success": True
                }
                
                with open(crawl_file, 'w', encoding='utf-8') as f:
                    json.dump(crawl_data, f, indent=2, ensure_ascii=False)
                
                print(f"💾 Crawl data saved to: {crawl_file}")
                print()
                
                return crawl_data
                
            else:
                print("❌ Web crawling failed!")
                print(f"   Error: No content retrieved or empty result")
                return None
                
        except Exception as e:
            print(f"💥 Web crawling error: {e}")
            return None
        
        finally:
            if 'crawler' in locals():
                await crawler.close()
    
    async def step2_content_processing(self, crawl_result):
        """Step 2: Content processing (summarization + question generation)"""
        print("📝 Step 2: Content Processing")
        print("-" * 30)
        
        try:
            # Try to use real LLM services if available
            try:
                from llm_service.services.content_summarizer import ContentSummarizerService
                from llm_service.services.simple_question_generator import SimpleQuestionGeneratorService
                
                print("🤖 Attempting to use LLM services...")
                
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
                print(f"⚠️  LLM services not available: {llm_error}")
                print("🔄 Falling back to demo content generation...")
                
                # Fallback to demo content
                demo_result = self._create_demo_content(crawl_result)
                print("✅ Demo content generated!")
                print(f"   Summary: {demo_result['summary']['word_count']} words")
                print(f"   Questions: {len(demo_result['questions']['questions'])}")
                print()
                
                return demo_result
                
        except Exception as e:
            print(f"💥 Content processing error: {e}")
            return None
    
    def step3_generate_final_output(self, crawl_result, processing_result):
        """Step 3: Generate final output files"""
        print("💾 Step 3: Generate Final Output")
        print("-" * 30)
        
        content_id = self._generate_content_id(crawl_result['title'])
        
        # Save summary
        summary_file = self.output_dir / f"{content_id}.summary.json"
        if processing_result['method'] == 'llm':
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
        else:
            summary_data = processing_result['summary']
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)
        
        # Save questions (Chrome extension format)
        questions_file = self.output_dir / f"{content_id}.questions.json"
        if processing_result['method'] == 'llm':
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
        else:
            questions_data = processing_result['questions']
        
        with open(questions_file, 'w', encoding='utf-8') as f:
            json.dump(questions_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Final output generated!")
        print(f"   Summary: {summary_file}")
        print(f"   Questions: {questions_file}")
        print()
        
        return {
            "summary_file": summary_file,
            "questions_file": questions_file,
            "content_id": content_id
        }
    
    def step4_show_usage_instructions(self, final_result):
        """Step 4: Show usage instructions"""
        print("🎯 Step 4: Usage Instructions")
        print("-" * 30)
        print("✅ Complete pipeline finished successfully!")
        print()
        print("📁 Generated Files:")
        print(f"   📄 Summary: {final_result['summary_file']}")
        print(f"   ❓ Questions: {final_result['questions_file']} ← Use this with Chrome extension!")
        print()
        print("🌐 How to test with Chrome Extension:")
        print("   1. Open Chrome → chrome://extensions/")
        print("   2. Load the 'Blog Question Injector' extension")
        print("   3. Go to any website with paragraphs")
        print("   4. Click the extension icon")
        print("   5. Upload the questions file:")
        print(f"      {final_result['questions_file']}")
        print("   6. Click 'Inject Custom Questions'")
        print("   7. Click questions to open answer drawers!")
        print()
        print("🔗 Good test websites:")
        print(f"   - Original: {self.url}")
        print("   - Wikipedia: https://en.wikipedia.org/wiki/React_(JavaScript_library)")
        print("   - Medium: https://medium.com/@any-article")
        print("   - Any blog with multiple paragraphs")
        print()
        print("🎉 Demo complete! Ready for testing.")
    
    def _generate_content_id(self, title: str) -> str:
        """Generate a content ID from title"""
        import hashlib
        content_id = title.lower().replace(' ', '_').replace('-', '_')
        content_id = ''.join(c for c in content_id if c.isalnum() or c == '_')
        
        if len(content_id) > 50:
            hash_suffix = hashlib.md5(title.encode()).hexdigest()[:8]
            content_id = content_id[:40] + '_' + hash_suffix
        
        return content_id
    
    def _create_demo_content(self, crawl_result):
        """Create demo content when LLM is not available"""
        content_id = self._generate_content_id(crawl_result['title'])
        
        # Create demo summary
        summary_data = {
            "content_id": content_id,
            "title": crawl_result['title'],
            "url": crawl_result['url'],
            "summary": "This article provides a comprehensive guide to unit testing React applications using Jest and Enzyme. It covers the fundamentals of testing stateless components through snapshot testing, simulating user events, and testing component state changes. The article emphasizes the importance of mocking in Jest, demonstrating how to mock functions and entire modules to achieve true unit testing.",
            "key_points": [
                "Jest and Enzyme provide a powerful combination for testing React applications",
                "Snapshot testing helps validate component rendering and catch unintended changes",
                "Event simulation allows testing of user interactions and component behavior",
                "State testing ensures component state changes work as expected",
                "Mocking is essential for isolating units under test and avoiding dependencies"
            ],
            "topics": ["react testing", "jest framework", "enzyme utility", "snapshot testing", "mocking"],
            "word_count": 89,
            "original_word_count": len(crawl_result['content'].split()),
            "compression_ratio": 89 / len(crawl_result['content'].split()),
            "confidence_score": 0.9
        }
        
        # Create demo questions
        questions_data = {
            "content_id": content_id,
            "content_title": crawl_result['title'],
            "content_url": crawl_result['url'],
            "summary": summary_data['summary'],
            "questions": [
                {
                    "id": "q1",
                    "question": "How do Jest snapshots help ensure component rendering consistency over time?",
                    "answer": "Jest snapshots create a saved representation of component output that can be compared against future renders. When tests run, Jest compares the current component output with the saved snapshot, immediately detecting any unintended changes in component structure, styling, or content.",
                    "question_type": "analytical",
                    "confidence_score": 0.9,
                    "estimated_answer_time": 45
                },
                {
                    "id": "q2",
                    "question": "What are the potential drawbacks of relying too heavily on snapshot testing?",
                    "answer": "Over-reliance on snapshot testing can lead to brittle tests that break with minor UI changes, creating maintenance overhead. Developers might become too focused on exact output matching rather than testing actual functionality.",
                    "question_type": "exploratory",
                    "confidence_score": 0.85,
                    "estimated_answer_time": 50
                },
                {
                    "id": "q3",
                    "question": "How does mocking in Jest contribute to true unit testing practices?",
                    "answer": "Mocking isolates the unit under test by replacing dependencies with controlled implementations. This ensures tests focus on a single component's behavior without being affected by external systems, network calls, or other components.",
                    "question_type": "analytical",
                    "confidence_score": 0.9,
                    "estimated_answer_time": 45
                },
                {
                    "id": "q4",
                    "question": "What role does Enzyme play in the React testing ecosystem?",
                    "answer": "Enzyme provides utilities for testing React components by offering methods to shallow render, mount, and interact with components. It simplifies component traversal, state inspection, and prop manipulation.",
                    "question_type": "analytical",
                    "confidence_score": 0.9,
                    "estimated_answer_time": 40
                },
                {
                    "id": "q5",
                    "question": "How can teams establish effective testing practices for React applications?",
                    "answer": "Teams should establish testing standards, choose consistent tools (Jest, Enzyme, React Testing Library), implement continuous integration with test requirements, and provide training on testing best practices.",
                    "question_type": "application",
                    "confidence_score": 0.8,
                    "estimated_answer_time": 50
                }
            ],
            "total_questions": 5,
            "average_confidence": 0.87,
            "generated_at": datetime.now().isoformat()
        }
        
        return {
            "method": "demo",
            "summary": summary_data,
            "questions": questions_data
        }


async def main():
    """Main function"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and run demo
    demo = FinalDemo(TARGET_URL)
    success = await demo.run_complete_demo()
    
    if success:
        print("\n🎉 Final demo completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Final demo failed!")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Demo interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)
