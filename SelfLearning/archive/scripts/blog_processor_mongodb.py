#!/usr/bin/env python3
"""
Blog Processor with MongoDB Integration

Complete pipeline for processing blog articles with MongoDB storage:
1. Web crawling using existing web_crawler module
2. Content summarization (when LLM is available)
3. Question generation from summaries
4. Store results in MongoDB collections (blog_summary, blog_qna)
5. Also store raw content and metadata

Usage:
    python3 blog_processor_mongodb.py --url "https://example.com/article"
    python3 blog_processor_mongodb.py --url "https://medium.com/article" --database blog_ai_db
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
from typing import Optional, Dict, Any

# Import the existing web crawler
from web_crawler import WebCrawler
from web_crawler.config.settings import CrawlerConfig

# Import MongoDB module
try:
    from mongodb.config.connection import MongoDBConnection
    from mongodb.config.settings import MongoDBSettings
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    print("⚠️  MongoDB module not available. Install dependencies: pip install motor pymongo")


class BlogProcessorMongoDB:
    """Production blog processing pipeline with MongoDB integration"""
    
    def __init__(self, url: str, database_name: str = "blog_ai_db"):
        self.url = url
        self.database_name = database_name
        self.logger = logging.getLogger(__name__)
        self.mongodb_connection: Optional[MongoDBConnection] = None
        
    async def process_blog(self):
        """Process a blog article through the complete pipeline"""
        print("🚀 Blog Processing Pipeline with MongoDB")
        print("=" * 60)
        print(f"URL: {self.url}")
        print(f"Database: {self.database_name}")
        print()
        
        if not MONGODB_AVAILABLE:
            print("❌ MongoDB module not available!")
            print("Please install dependencies: pip install motor pymongo")
            return False
        
        try:
            # Initialize MongoDB connection
            await self._init_mongodb()
            
            # Step 1: Web Crawling
            crawl_result = await self._crawl_content()
            if not crawl_result:
                return False
            
            # Step 2: Store raw content
            raw_content_id = await self._store_raw_content(crawl_result)
            if not raw_content_id:
                return False
            
            # Step 3: Content Processing
            processing_result = await self._process_content(crawl_result)
            if not processing_result:
                return False
            
            # Step 4: Store processed content in MongoDB
            storage_result = await self._store_processed_content(
                crawl_result, processing_result, raw_content_id
            )
            
            # Step 5: Show Results
            self._show_results(crawl_result, processing_result, storage_result)
            
            return True
            
        except Exception as e:
            print(f"💥 Processing failed: {e}")
            self.logger.error(f"Processing failed: {e}", exc_info=True)
            return False
        finally:
            await self._cleanup_mongodb()
    
    async def _init_mongodb(self):
        """Initialize MongoDB connection"""
        print("🔗 Initializing MongoDB Connection")
        print("-" * 40)
        
        try:
            # Create connection with custom database name
            settings = MongoDBSettings()
            settings.database = self.database_name
            
            self.mongodb_connection = MongoDBConnection(settings)
            await self.mongodb_connection.connect()
            
            print(f"✅ Connected to MongoDB database: {self.database_name}")
            
            # Verify collections exist
            collections = await self.mongodb_connection.database.list_collection_names()
            required_collections = ['raw_blog_content', 'blog_meta_data', 'blog_summary', 'blog_qna']
            
            for collection in required_collections:
                if collection not in collections:
                    print(f"⚠️  Collection '{collection}' not found, creating...")
                    await self.mongodb_connection.database.create_collection(collection)
            
            print("✅ All required collections available")
            print()
            
        except Exception as e:
            print(f"❌ MongoDB connection failed: {e}")
            raise
    
    async def _cleanup_mongodb(self):
        """Clean up MongoDB connection"""
        if self.mongodb_connection:
            await self.mongodb_connection.disconnect()
            print("🔌 MongoDB connection closed")
    
    async def _crawl_content(self):
        """Step 1: Web crawling"""
        print("🌐 Step 1: Web Crawling")
        print("-" * 30)
        
        try:
            # Configure crawler
            config = CrawlerConfig()
            config.timeout = 30
            config.max_retries = 3
            config.user_agent = "BlogProcessorMongoDB/1.0"
            
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
    
    async def _store_raw_content(self, crawl_result):
        """Store raw blog content in MongoDB"""
        print("💾 Step 2: Storing Raw Content")
        print("-" * 30)
        
        try:
            content_id = self._generate_content_id(crawl_result['title'])
            
            # Prepare raw content document
            raw_content_doc = {
                "blog_id": content_id,
                "url": crawl_result['url'],
                "title": crawl_result['title'],
                "content": crawl_result['content'],
                "html_content": crawl_result['metadata'].get('html', ''),
                "author": crawl_result['metadata'].get('author', ''),
                "published_date": self._parse_date(crawl_result['metadata'].get('published_date')),
                "crawled_at": datetime.fromisoformat(crawl_result['crawled_at'].replace('Z', '+00:00')) if 'T' in crawl_result['crawled_at'] else datetime.now(),
                "source_domain": urlparse(crawl_result['url']).netloc,
                "word_count": len(crawl_result['content'].split()),
                "language": self._normalize_language_code(crawl_result['metadata'].get('language', 'en')),
                "content_type": "article",
                "raw_metadata": crawl_result['metadata'],
                "processing_status": "pending",
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            # Store in raw_blog_content collection
            collection = self.mongodb_connection.get_collection('raw_blog_content')
            
            # Check if already exists
            existing = await collection.find_one({"blog_id": content_id})
            if existing:
                print(f"⚠️  Content already exists, updating...")
                await collection.replace_one({"blog_id": content_id}, raw_content_doc)
            else:
                await collection.insert_one(raw_content_doc)
            
            print(f"✅ Raw content stored with ID: {content_id}")
            print(f"   Word count: {raw_content_doc['word_count']:,}")
            print(f"   Domain: {raw_content_doc['source_domain']}")
            print()
            
            return content_id
            
        except Exception as e:
            print(f"❌ Failed to store raw content: {e}")
            return None
    
    async def _process_content(self, crawl_result):
        """Step 3: Content processing (summarization + questions)"""
        print("📝 Step 3: Content Processing")
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
    
    async def _store_processed_content(self, crawl_result, processing_result, raw_content_id):
        """Step 4: Store processed content in MongoDB collections"""
        print("💾 Step 4: Storing Processed Content")
        print("-" * 40)
        
        try:
            content_id = self._generate_content_id(crawl_result['title'])
            
            # Store summary in blog_summary collection
            summary_id = await self._store_summary(processing_result['summary'], content_id)
            
            # Store questions in blog_qna collection
            question_ids = await self._store_questions(processing_result['questions'], content_id)
            
            # Update raw content processing status
            await self._update_processing_status(content_id, "completed")
            
            print("✅ All processed content stored successfully!")
            print()
            
            return {
                "content_id": content_id,
                "summary_id": summary_id,
                "question_ids": question_ids,
                "raw_content_id": raw_content_id
            }
            
        except Exception as e:
            print(f"❌ Failed to store processed content: {e}")
            # Update status to failed
            try:
                await self._update_processing_status(content_id, "failed")
            except:
                pass
            return None
    
    async def _store_summary(self, summary, content_id):
        """Store summary in blog_summary collection with embedding"""
        try:
            # Generate embedding for the summary
            embedding = await self._generate_embedding(summary.summary)
            
            summary_doc = {
                "blog_id": content_id,
                "summary_text": summary.summary,
                "key_points": summary.key_points,
                "main_topics": summary.topics,
                "summary_length": "medium",  # Could be determined dynamically
                "summary_type": "abstractive",  # Based on LLM generation
                "ai_model": "gpt-4",  # Could be extracted from summary object
                "ai_provider": "openai",  # Could be extracted from summary object
                "generation_parameters": {
                    "target_length": "medium",
                    "model_version": "gpt-4"
                },
                "confidence_score": summary.confidence_score,
                "coherence_score": 0.9,  # Could be calculated
                "relevance_score": 0.95,  # Could be calculated
                
                # Add embedding fields
                "embedding": embedding,
                "embedding_model": "text-embedding-ada-002",
                "embedding_provider": "openai",
                "embedding_dimensions": len(embedding) if embedding else 0,
                "embedding_generated_at": datetime.now(),
                
                "generated_at": datetime.now(),
                "processing_time_seconds": 15.0,  # Could be tracked
                "tokens_used": summary.word_count * 1.3,  # Rough estimate
                "cost_usd": 0.02,  # Could be calculated based on tokens
                "version": 1,
                "is_active": True,
                "user_ratings": {
                    "helpful_count": 0,
                    "not_helpful_count": 0,
                    "average_rating": 0.0
                },
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            collection = self.mongodb_connection.get_collection('blog_summary')
            
            # Check if summary already exists
            existing = await collection.find_one({"blog_id": content_id})
            if existing:
                print(f"   📝 Updating existing summary...")
                result = await collection.replace_one({"blog_id": content_id}, summary_doc)
                summary_id = existing['_id']
            else:
                print(f"   📝 Storing new summary...")
                result = await collection.insert_one(summary_doc)
                summary_id = result.inserted_id
            
            print(f"   ✅ Summary stored (ID: {summary_id})")
            return str(summary_id)
            
        except Exception as e:
            print(f"   ❌ Failed to store summary: {e}")
            raise
    
    async def _store_questions(self, question_set, content_id):
        """Store questions in blog_qna collection"""
        try:
            collection = self.mongodb_connection.get_collection('blog_qna')
            question_ids = []
            
            # Remove existing questions for this content
            await collection.delete_many({"blog_id": content_id})
            
            print(f"   ❓ Storing {question_set.total_questions} questions...")
            
            for i, question in enumerate(question_set.questions, 1):
                question_doc = {
                    "blog_id": content_id,
                    "question": question.question,
                    "answer": question.answer,
                    "question_type": question.question_type,
                    "difficulty_level": "intermediate",  # Could be determined from question
                    "topic_area": "general",  # Could be extracted from content
                    "ai_model": "gpt-4",
                    "ai_provider": "openai",
                    "generation_parameters": {
                        "question_style": "educational",
                        "context_window": 2000
                    },
                    "question_quality_score": question.confidence_score,
                    "answer_accuracy_score": question.confidence_score,
                    "relevance_score": question.confidence_score,
                    "learning_objective": f"Understanding concepts from question {i}",
                    "bloom_taxonomy_level": "comprehension",
                    "question_set_id": f"qset_{content_id}",
                    "question_order": i,
                    "total_questions_in_set": question_set.total_questions,
                    "times_asked": 0,
                    "correct_answers": 0,
                    "user_feedback": {
                        "clarity_rating": 0.0,
                        "difficulty_rating": 0.0,
                        "usefulness_rating": 0.0
                    },
                    "generated_at": datetime.now(),
                    "processing_time_seconds": question.estimated_answer_time,
                    "tokens_used": len(question.question.split()) * 1.5,  # Rough estimate
                    "is_active": True,
                    "review_status": "approved",
                    "reviewed_by": "auto_system",
                    "reviewed_at": datetime.now(),
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                }
                
                result = await collection.insert_one(question_doc)
                question_ids.append(str(result.inserted_id))
            
            print(f"   ✅ {len(question_ids)} questions stored")
            return question_ids
            
        except Exception as e:
            print(f"   ❌ Failed to store questions: {e}")
            raise
    
    async def _update_processing_status(self, content_id, status):
        """Update processing status in raw_blog_content"""
        try:
            collection = self.mongodb_connection.get_collection('raw_blog_content')
            await collection.update_one(
                {"blog_id": content_id},
                {
                    "$set": {
                        "processing_status": status,
                        "updated_at": datetime.now()
                    }
                }
            )
        except Exception as e:
            self.logger.error(f"Failed to update processing status: {e}")
    
    def _show_results(self, crawl_result, processing_result, storage_result):
        """Step 5: Show results and usage instructions"""
        print("🎯 Processing Complete!")
        print("-" * 30)
        print("✅ Blog processing finished successfully!")
        print()
        print("📊 Stored in MongoDB Collections:")
        print(f"   🗄️  Database: {self.database_name}")
        print(f"   📄 Raw Content: raw_blog_content (ID: {storage_result['content_id']})")
        print(f"   📝 Summary: blog_summary (ID: {storage_result['summary_id']})")
        print(f"   ❓ Questions: blog_qna ({len(storage_result['question_ids'])} questions)")
        print()
        print("🔍 Query Examples:")
        print("   # Get summary")
        print(f"   db.blog_summary.findOne({{blog_id: '{storage_result['content_id']}'}})")
        print()
        print("   # Get all questions")
        print(f"   db.blog_qna.find({{blog_id: '{storage_result['content_id']}'}})")
        print()
        print("🌐 MongoDB Access:")
        print(f"   Web UI: http://localhost:8081 (admin/password123)")
        print(f"   Connection: mongodb://admin:password123@localhost:27017/{self.database_name}")
        print()
        print("🎉 Ready for use in applications!")
    
    def _generate_content_id(self, title: str) -> str:
        """Generate content ID from title"""
        content_id = title.lower().replace(' ', '_').replace('-', '_')
        content_id = ''.join(c for c in content_id if c.isalnum() or c == '_')
        
        if len(content_id) > 50:
            hash_suffix = hashlib.md5(title.encode()).hexdigest()[:8]
            content_id = content_id[:40] + '_' + hash_suffix
        
        return content_id
    
    def _parse_date(self, date_str):
        """Parse date string to datetime object"""
        if not date_str:
            return None
        try:
            # Try common date formats
            for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S']:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            return None
        except:
            return None

    def _normalize_language_code(self, language_code: str) -> str:
        """Normalize language code for MongoDB text indexing compatibility."""
        if not language_code:
            return 'en'
        
        # MongoDB text indexes support these language codes:
        # da, nl, en, fi, fr, de, hu, it, nb, pt, ro, ru, es, sv, tr
        # Convert common locale codes to MongoDB-supported language codes
        language_map = {
            'en-US': 'en',
            'en-GB': 'en',
            'en-CA': 'en',
            'en-AU': 'en',
            'fr-FR': 'fr',
            'fr-CA': 'fr',
            'de-DE': 'de',
            'de-AT': 'de',
            'es-ES': 'es',
            'es-MX': 'es',
            'pt-BR': 'pt',
            'pt-PT': 'pt',
            'it-IT': 'it',
            'ru-RU': 'ru',
            'nl-NL': 'nl',
            'sv-SE': 'sv',
            'da-DK': 'da',
            'nb-NO': 'nb',
            'fi-FI': 'fi',
            'hu-HU': 'hu',
            'ro-RO': 'ro',
            'tr-TR': 'tr'
        }
        
        # Normalize the language code
        normalized = language_map.get(language_code.lower(), language_code.lower())
        
        # If it's still not a supported MongoDB language, default to 'en'
        supported_languages = {'da', 'nl', 'en', 'fi', 'fr', 'de', 'hu', 'it', 'nb', 'pt', 'ro', 'ru', 'es', 'sv', 'tr'}
        if normalized not in supported_languages:
            self.logger.warning(f"Unsupported language code '{language_code}', defaulting to 'en'")
            return 'en'
        
        return normalized
    
    async def _generate_embedding(self, text: str):
        """Generate embedding for text using OpenAI"""
        try:
            # Generate embedding using OpenAI's embedding model
            import openai
            from openai import AsyncOpenAI
            
            # Initialize OpenAI client
            client = AsyncOpenAI()
            
            response = await client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            
            embedding = response.data[0].embedding
            print(f"   🔢 Generated embedding: {len(embedding)} dimensions")
            return embedding
            
        except Exception as e:
            print(f"   ⚠️  Failed to generate embedding: {e}")
            print("   📝 Storing summary without embedding")
            return None


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Process blog articles and store in MongoDB collections",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a Medium article
  python3 blog_processor_mongodb.py --url "https://medium.com/article-url"
  
  # Process with custom database
  python3 blog_processor_mongodb.py --url "https://example.com/blog" --database my_blog_db
  
  # Process Wikipedia article
  python3 blog_processor_mongodb.py --url "https://en.wikipedia.org/wiki/Topic"
        """
    )
    
    parser.add_argument(
        '--url',
        type=str,
        required=True,
        help='Blog URL to process'
    )
    
    parser.add_argument(
        '--database',
        type=str,
        default='blog_ai_db',
        help='MongoDB database name (default: blog_ai_db)'
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
    processor = BlogProcessorMongoDB(args.url, args.database)
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
