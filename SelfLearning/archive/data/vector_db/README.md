# Vector Database Module

A production-grade vector database module for content embeddings and similarity search, designed to integrate seamlessly with the existing content processing pipeline.

## Features

### 🚀 Core Capabilities
- **Multi-Provider Embeddings**: Support for OpenAI, Anthropic, and local Sentence Transformers
- **Vector Storage**: In-memory, ChromaDB, FAISS, and Pinecone backends
- **Similarity Search**: Cosine similarity with metadata filtering
- **Batch Processing**: Efficient batch embedding generation and indexing
- **Content Integration**: Seamless integration with existing BlogContent pipeline

### 🛡️ Production Ready
- **Error Handling**: Comprehensive exception hierarchy with detailed error information
- **Fallback Support**: Automatic provider fallback for reliability
- **Health Monitoring**: Built-in health checks and statistics
- **Type Safety**: Full type hints and validation
- **Async/Await**: Fully asynchronous for high performance

### 🔧 Extensible Architecture
- **Plugin System**: Easy to add new embedding providers and vector stores
- **Configuration**: Flexible configuration with environment variables
- **Text Processing**: Built-in preprocessing and chunking capabilities
- **Metadata Support**: Rich metadata with custom fields and filtering

## Quick Start

### Installation

```bash
# Install core dependencies
pip install numpy scipy

# Optional: Install embedding providers
pip install openai anthropic sentence-transformers

# Optional: Install vector stores
pip install chromadb faiss-cpu
```

### Basic Usage

```python
import asyncio
from vector_db import VectorSearchService, VectorMetadata

async def main():
    # Create service with default configuration
    service = await VectorSearchService.create_default_service(
        openai_api_key="your-api-key",  # Optional
        use_sentence_transformers=True   # Local fallback
    )
    
    # Index some content
    doc_id = await service.index_content(
        content="Your content here...",
        metadata=VectorMetadata(
            title="Example Document",
            url="https://example.com",
            tags=["example", "demo"]
        )
    )
    
    # Search for similar content
    results = await service.search_similar_content(
        query="search query",
        limit=5,
        similarity_threshold=0.7
    )
    
    for result in results:
        print(f"{result.metadata.title}: {result.similarity_score:.3f}")

asyncio.run(main())
```

### Integration with Existing Pipeline

```python
from vector_content_processor import VectorContentProcessor
from llm_service.repositories.models import BlogContent

async def process_existing_content():
    # Initialize processor
    processor = VectorContentProcessor()
    
    # Index existing BlogContent
    blog_content = BlogContent.from_crawled_file("content.txt")
    doc_id = await processor.process_and_index_content(
        blog_content=blog_content,
        tags=["additional", "tags"],
        categories=["category1", "category2"]
    )
    
    # Find similar content
    similar = await processor.find_similar_content(
        query_text="your search query",
        limit=10,
        similarity_threshold=0.6
    )
    
    return similar
```

## Architecture

### Core Components

```
vector_db/
├── core/                   # Abstract interfaces
│   └── interfaces.py      # IEmbeddingProvider, IVectorStore, IVectorSearchService
├── models/                # Data models
│   └── vector_models.py   # VectorDocument, SearchResult, etc.
├── providers/             # Embedding providers
│   ├── openai_provider.py
│   ├── anthropic_provider.py
│   └── sentence_transformers_provider.py
├── storage/               # Vector storage backends
│   ├── in_memory_store.py
│   ├── chroma_store.py    # (Future)
│   └── faiss_store.py     # (Future)
├── services/              # High-level services
│   ├── embedding_service.py
│   └── vector_service.py
└── utils/                 # Utilities
    ├── exceptions.py
    ├── text_processing.py
    └── similarity_metrics.py
```

### Data Flow

```
Content → Text Processing → Embedding Generation → Vector Storage → Similarity Search
    ↓           ↓                    ↓                  ↓              ↓
BlogContent → Preprocessing → OpenAI/Local → InMemory/ChromaDB → SearchResults
```

## Configuration

### Environment Variables

```bash
# Embedding providers
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"

# Vector stores (if using external services)
export PINECONE_API_KEY="your-pinecone-key"
export PINECONE_ENVIRONMENT="your-environment"
```

### Provider Configuration

```python
from vector_db.providers import OpenAIEmbeddingProvider
from vector_db.models.vector_models import EmbeddingModel

# Configure OpenAI provider
provider = OpenAIEmbeddingProvider(
    api_key="your-key",
    model=EmbeddingModel.OPENAI_TEXT_EMBEDDING_3_SMALL,
    max_retries=3,
    timeout=30.0
)

# Configure local provider
from vector_db.providers import SentenceTransformersProvider

local_provider = SentenceTransformersProvider(
    model=EmbeddingModel.SENTENCE_TRANSFORMERS_ALL_MPNET,
    device="cpu"  # or "cuda" for GPU
)
```

## Advanced Usage

### Custom Embedding Service

```python
from vector_db.services import EmbeddingService

# Create service with multiple providers
embedding_service = EmbeddingService()

# Add providers with fallback
embedding_service.add_provider(openai_provider, is_primary=True)
embedding_service.add_provider(local_provider, is_primary=False)

# Generate embeddings with automatic fallback
embedding = await embedding_service.generate_embedding("text content")
```

### Metadata Filtering

```python
# Search with filters
results = await service.search_similar_content(
    query="machine learning",
    metadata_filter={
        "content_type": "tutorial",
        "tags": ["python", "ml"],
        "language": "en"
    },
    similarity_threshold=0.8
)
```

### Batch Processing

```python
# Index multiple documents efficiently
content_items = [
    (content1, metadata1, "id1"),
    (content2, metadata2, "id2"),
    (content3, metadata3, "id3")
]

doc_ids = await service.index_content_batch(content_items)
```

### Text Processing

```python
from vector_db.utils.text_processing import TextPreprocessor, TextChunker

# Preprocess text
preprocessor = TextPreprocessor()
clean_text = preprocessor.preprocess(
    raw_text,
    clean_html=True,
    remove_urls=True,
    normalize_whitespace=True
)

# Chunk long documents
chunker = TextChunker()
chunks = chunker.chunk_text(long_text)
```

## Performance Considerations

### Embedding Generation
- **Batch Processing**: Use batch methods for multiple documents
- **Local Models**: Consider Sentence Transformers for offline usage
- **Caching**: Implement embedding caching for repeated content

### Vector Storage
- **Memory Usage**: In-memory store suitable for < 100K documents
- **Persistence**: Use ChromaDB or FAISS for larger datasets
- **Indexing**: Consider approximate nearest neighbor for large scales

### Search Performance
- **Similarity Threshold**: Higher thresholds reduce result set size
- **Metadata Filtering**: Pre-filter before similarity computation
- **Result Limits**: Use appropriate limits for UI responsiveness

## Error Handling

The module provides comprehensive error handling with specific exception types:

```python
from vector_db.utils.exceptions import (
    EmbeddingError,
    VectorStoreError,
    VectorSearchError,
    ConfigurationError,
    RateLimitError
)

try:
    await service.index_content(content, metadata)
except RateLimitError as e:
    # Handle rate limiting
    print(f"Rate limited by {e.details.get('provider')}")
    await asyncio.sleep(e.details.get('retry_after', 60))
except EmbeddingError as e:
    # Handle embedding failures
    print(f"Embedding failed: {e.message}")
except VectorStoreError as e:
    # Handle storage failures
    print(f"Storage error: {e.message}")
```

## Monitoring and Health Checks

```python
# Service health check
health = await service.health_check()
if not health['service_healthy']:
    print("Issues detected:")
    for error in health['errors']:
        print(f"  - {error}")

# Get statistics
stats = await service.get_statistics()
print(f"Documents: {stats['document_count']}")
print(f"Providers: {stats['available_providers']}")

# Provider-specific stats
embedding_stats = embedding_service.get_provider_stats()
for provider, stats in embedding_stats.items():
    success_rate = stats['successful_requests'] / stats['total_requests']
    print(f"{provider}: {success_rate:.2%} success rate")
```

## Integration Examples

### With Web Crawler

```python
from vector_content_processor import VectorContentProcessor

processor = VectorContentProcessor()

# Index all crawled content
crawled_dir = Path("crawled_content")
doc_ids = await processor.index_crawled_content_directory(crawled_dir)

# Find similar articles
similar = await processor.find_similar_content(
    query_text="Java concurrency patterns",
    content_type_filter="article",
    tag_filter=["java", "threading"]
)
```

### With Question Generator

```python
# After generating questions, find related content
questions_file = "processed_content/questions/article.questions.json"
with open(questions_file) as f:
    questions_data = json.load(f)

# Use questions to find related content
for question in questions_data['questions']:
    related = await processor.find_similar_content(
        query_text=question['question'],
        limit=3,
        similarity_threshold=0.7
    )
    print(f"Related to '{question['question']}':")
    for result in related:
        print(f"  - {result.get_title()}")
```

## Testing

Run the comprehensive example:

```bash
python vector_db_example.py
```

This will demonstrate:
- Basic vector database operations
- Content processor integration
- Advanced search with filtering
- Performance benchmarking

## Future Enhancements

### Planned Features
- **ChromaDB Integration**: Persistent vector storage
- **FAISS Support**: High-performance similarity search
- **Pinecone Integration**: Cloud vector database
- **Hybrid Search**: Combine semantic and keyword search
- **Clustering**: Content clustering and topic modeling

### Performance Optimizations
- **Embedding Caching**: Redis-based embedding cache
- **Async Batching**: Automatic request batching
- **GPU Support**: CUDA acceleration for local models
- **Quantization**: Reduced precision for memory efficiency

## Contributing

1. Follow the existing architecture patterns
2. Add comprehensive type hints
3. Include error handling and logging
4. Write tests for new functionality
5. Update documentation

## License

This module is part of the SelfLearning project and follows the same license terms.
