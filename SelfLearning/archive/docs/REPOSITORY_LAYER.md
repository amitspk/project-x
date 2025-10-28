# Repository Layer for Content Management

A production-grade repository layer that reads blog content from the `crawled_content` folder, processes it through the LLM service to generate Q&A files, and provides a clean abstraction for future database implementations.

## 🎯 Overview

This repository layer provides:
- **File-based content management** from crawled content directory
- **Abstract repository interface** for easy database migration
- **Batch processing service** for efficient content processing
- **Status tracking** and metadata management
- **Extensible design** for multiple storage backends

## 🏗️ Architecture

### **Repository Pattern**
```
IContentRepository (Interface)
├── FileContentRepository (File-based implementation)
├── DatabaseContentRepository (Template for DB implementation)
├── PostgreSQLContentRepository (Future implementation)
├── MongoDBContentRepository (Future implementation)
└── SQLiteContentRepository (Future implementation)
```

### **Service Layer**
```
ContentProcessingService
├── Orchestrates content processing workflow
├── Manages LLM question generation
├── Handles batch processing with concurrency control
└── Provides comprehensive statistics and monitoring

ContentDiscoveryService
├── Discovers new content in repositories
├── Provides content summaries and statistics
└── Manages content indexing and metadata
```

## 📊 Data Models

### **BlogContent**
```python
@dataclass
class BlogContent:
    content_id: str              # Unique identifier
    title: str                   # Content title
    content: str                 # Raw content text
    metadata: ContentMetadata    # Rich metadata
    status: ProcessingStatus     # Processing state
```

### **ContentMetadata**
```python
@dataclass
class ContentMetadata:
    # Basic metadata
    url: Optional[str]
    author: Optional[str]
    published_date: Optional[datetime]
    
    # Content classification
    content_type: str            # article, tutorial, news, review
    difficulty_level: str        # beginner, intermediate, advanced
    language: str
    tags: List[str]
    
    # Content metrics
    word_count: int
    estimated_reading_time: int
    
    # Processing metadata
    questions_generated: bool
    questions_file_path: Optional[str]
    question_count: int
    average_confidence: float
```

### **ProcessingStatus**
```python
class ProcessingStatus(Enum):
    PENDING = "pending"          # Not yet processed
    PROCESSING = "processing"    # Currently being processed
    COMPLETED = "completed"      # Successfully processed
    FAILED = "failed"           # Processing failed
    SKIPPED = "skipped"         # Skipped due to filters/rules
```

## 🚀 Usage

### **CLI Interface**

```bash
# Discover content in crawled_content folder
python content_processor.py --discover

# Process all unprocessed content
python content_processor.py --process-all --num-questions 10

# Process specific content by ID
python content_processor.py --process-id "content_id_here"

# Show processing status
python content_processor.py --status

# List generated question files
python content_processor.py --list-questions

# Batch processing with custom settings
python content_processor.py --process-all \
    --crawled-path ./my_content \
    --output ./my_questions \
    --num-questions 8 \
    --batch-size 5 \
    --max-concurrent 2
```

### **Programmatic Usage**

```python
from llm_service import LLMService
from llm_service.repositories import FileContentRepository
from llm_service.services.content_service import ContentProcessingService

# Initialize repository
repository = FileContentRepository(
    crawled_content_path="crawled_content",
    index_file_path="content_index.json"
)
await repository.initialize()

# Initialize LLM service
llm_service = LLMService()
await llm_service.initialize()

# Initialize processing service
processor = ContentProcessingService(
    content_repository=repository,
    llm_service=llm_service,
    output_directory="generated_questions"
)

# Process all content
stats = await processor.process_all_unprocessed(
    num_questions=10,
    batch_size=5
)

print(f"Processed: {stats['processed']}")
print(f"Questions generated: {stats['total_questions_generated']}")
```

## 📁 File Structure

```
llm_service/repositories/
├── __init__.py                 # Package exports
├── interfaces.py               # Abstract interfaces
├── models.py                   # Data models and BlogContent
├── file_repository.py          # File-based implementation
└── database_repository.py      # Database templates

llm_service/services/
├── content_service.py          # Processing orchestration
└── question_generator.py       # Question generation logic

content_processor.py            # CLI interface
generated_questions/            # Output directory for Q&A files
crawled_content/               # Input directory for blog content
```

## 🔧 Repository Features

### **FileContentRepository**
- **Auto-discovery**: Scans crawled_content directory for .txt files
- **Metadata extraction**: Reads associated .meta.json files
- **Content classification**: Automatically classifies content type and difficulty
- **Status tracking**: Maintains processing status for each content item
- **Index persistence**: Optional JSON index file for faster startup
- **Memory-efficient**: Streams content in batches for large datasets

### **Content Processing**
- **Batch processing**: Processes multiple items with configurable batch sizes
- **Concurrency control**: Limits concurrent LLM requests to prevent rate limiting
- **Error handling**: Robust error handling with retry mechanisms
- **Progress tracking**: Real-time statistics and progress monitoring
- **Smart filtering**: Skips content that's too short or already processed

### **Question Generation Integration**
- **Seamless LLM integration**: Uses existing question generator service
- **Rich metadata**: Generates comprehensive question metadata for JS injection
- **File management**: Automatically saves questions to organized file structure
- **Status updates**: Updates content status and metadata after processing

## 📊 Example Output

### **Discovery Results**
```
🔍 Discovering content in repository...
✅ Discovery completed!
   📁 New content found: 0
   ⏰ Discovery time: 2025-09-28T19:56:55.945382

📊 Repository Summary:
   📄 Total content: 5
   📝 Total words: 4,372
   📈 Average words: 874

📋 Status Breakdown:
   • pending: 5

📚 Content Types:
   • article: 3
   • tutorial: 1
   • news: 1
```

### **Batch Processing Results**
```
============================================================
📊 PROCESSING RESULTS
============================================================
✅ Successfully processed: 4
❌ Failed: 0
⏭️  Skipped: 1
❓ Total questions generated: 32
⏱️  Duration: 0:00:30.741
📈 Success rate: 100.0%

💾 Questions saved to: generated_questions
```

### **Generated Files**
```
📋 Generated Question Files
============================================================
📁 Found 4 question files:

 1. medium_com_unit_testing_react_questions.json
    📝 Title: Unit testing your React application with Jest and Enzyme
    ❓ Questions: 8, Confidence: 0.79
    📊 Size: 10.1 KB

 2. hindustantimes_com_sezs_universities_questions.json
    📝 Title: Building SEZs with labs and universities
    ❓ Questions: 8, Confidence: 0.81
    📊 Size: 10.8 KB
```

## 🔮 Future Database Implementation

### **Easy Migration Path**
The repository layer is designed for easy migration to database backends:

```python
# Current file-based usage
repository = FileContentRepository("crawled_content")

# Future database usage (same interface!)
repository = PostgreSQLContentRepository("postgresql://...")
repository = MongoDBContentRepository("mongodb://...")
repository = SQLiteContentRepository("./content.db")
```

### **Database Schema (PostgreSQL Example)**
```sql
CREATE TABLE blog_content (
    content_id VARCHAR(255) PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'pending',
    word_count INTEGER DEFAULT 0,
    created_date TIMESTAMP DEFAULT NOW(),
    updated_date TIMESTAMP DEFAULT NOW(),
    search_vector tsvector
);

CREATE INDEX idx_blog_content_status ON blog_content(status);
CREATE INDEX idx_blog_content_search ON blog_content USING gin(search_vector);
```

### **Migration Utility**
```python
# Migrate from file to database
migrator = RepositoryMigrator(
    source_repo=file_repository,
    target_repo=database_repository
)

stats = await migrator.migrate_all()
print(f"Migrated: {stats['migrated']} items")
```

## 🎯 Key Benefits

### **Production Ready**
- **Robust error handling** with comprehensive logging
- **Concurrency control** to prevent API rate limiting
- **Memory efficient** streaming for large datasets
- **Status tracking** for reliable processing workflows
- **Comprehensive statistics** for monitoring and optimization

### **Flexible Architecture**
- **Repository pattern** allows easy backend switching
- **Service layer** separates business logic from data access
- **Abstract interfaces** enable testing with mock implementations
- **Extensible design** supports custom content sources

### **Developer Experience**
- **Rich CLI interface** for easy operation and debugging
- **Comprehensive logging** for troubleshooting
- **Clear data models** with type hints and documentation
- **Async/await support** for modern Python development

### **Scalability**
- **Batch processing** for efficient large-scale operations
- **Streaming support** for memory-efficient processing
- **Database-ready design** for high-volume production use
- **Horizontal scaling** support through stateless design

The repository layer provides a solid foundation for content management that can grow from file-based prototypes to production database systems while maintaining the same clean, intuitive interface.
