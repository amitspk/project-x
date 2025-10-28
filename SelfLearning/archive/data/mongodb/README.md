# MongoDB Module

This module provides MongoDB integration for the SelfLearning project, offering persistent storage for content metadata, user interactions, search analytics, and processing job tracking.

## Features

- **Async MongoDB Connection Management**: Production-ready connection handling with proper error management
- **Content Metadata Storage**: Store processed content with summaries, questions, and metadata
- **User Interaction Tracking**: Track user engagement and behavior analytics
- **Search Analytics**: Monitor search patterns and performance metrics
- **Processing Job Management**: Track content processing pipeline jobs
- **Health Monitoring**: Built-in health checks and database statistics
- **Index Management**: Automatic index creation for optimal performance

## Quick Start

### 1. Install Dependencies

```bash
pip install motor pymongo
```

### 2. Start MongoDB with Docker

```bash
cd mongodb
./scripts/mongodb_setup.sh start
```

### 3. Basic Usage

```python
import asyncio
from mongodb import MongoDBConnection, ContentMetadata

async def main():
    # Connect to MongoDB
    connection = MongoDBConnection()
    await connection.connect()
    
    # Create indexes
    await connection.create_indexes()
    
    # Store content metadata
    content = ContentMetadata(
        content_id="example_article",
        url="https://example.com/article",
        title="Example Article",
        summary="This is an example article summary.",
        key_points=["Point 1", "Point 2"]
    )
    
    collection = connection.get_collection('content_metadata')
    await collection.insert_one(content.to_dict())
    
    # Health check
    health = await connection.health_check()
    print(f"MongoDB Status: {health['status']}")
    
    await connection.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

## Directory Structure

```
mongodb/
├── __init__.py                 # Module initialization
├── config/                     # Configuration management
│   ├── __init__.py
│   ├── settings.py            # MongoDB settings and connection strings
│   └── connection.py          # Connection management and health checks
├── models/                     # Data models
│   ├── __init__.py
│   └── content_models.py      # Content, interaction, and analytics models
├── scripts/                    # Management scripts
│   └── mongodb_setup.sh       # Docker container management
├── init/                       # Database initialization
│   └── init-db.js            # MongoDB initialization script
├── docker-compose.yml          # Docker services configuration
└── README.md                  # This file
```

## Configuration

### Environment Variables

Set these environment variables to configure MongoDB connection:

```bash
export MONGODB_HOST=localhost
export MONGODB_PORT=27017
export MONGODB_USERNAME=admin
export MONGODB_PASSWORD=password123
export MONGODB_DATABASE=selflearning
export MONGODB_AUTH_SOURCE=admin
```

### Docker Setup

The module includes a complete Docker setup:

```bash
# Start MongoDB
./scripts/mongodb_setup.sh start

# Check status
./scripts/mongodb_setup.sh status

# View logs
./scripts/mongodb_setup.sh logs

# Stop MongoDB
./scripts/mongodb_setup.sh stop
```

## Data Models

### ContentMetadata

Stores comprehensive information about processed content:

```python
content = ContentMetadata(
    content_id="unique_id",
    url="https://example.com",
    title="Article Title",
    summary="Article summary",
    key_points=["Point 1", "Point 2"],
    questions=[{"question": "What is...?", "type": "factual"}],
    word_count=1500,
    reading_time_minutes=6,
    tags=["technology", "programming"],
    llm_provider="openai",
    llm_model="gpt-4"
)
```

### UserInteraction

Tracks user engagement with content:

```python
interaction = UserInteraction(
    content_id="article_id",
    interaction_type=InteractionType.QUESTION_ANSWERED,
    question_id="q1",
    answer_provided="User's answer",
    time_spent_seconds=120
)
```

### SearchAnalytics

Monitors search performance and patterns:

```python
search = SearchAnalytics(
    query="machine learning",
    result_count=15,
    search_time_ms=45.2,
    search_type="similarity",
    embedding_model="text-embedding-ada-002"
)
```

### ProcessingJob

Tracks content processing pipeline jobs:

```python
job = ProcessingJob(
    job_type="generate_questions",
    content_id="article_id",
    status=ProcessingStatus.RUNNING,
    progress_percentage=75.0,
    current_step="Generating questions"
)
```

## Connection Management

### Basic Connection

```python
from mongodb.config import MongoDBConnection

connection = MongoDBConnection()
await connection.connect()
```

### Global Connection

```python
from mongodb.config.connection import get_connection

connection = await get_connection()  # Singleton instance
```

### Health Monitoring

```python
health = await connection.health_check()
print(f"Status: {health['status']}")
print(f"Response Time: {health['response_time_seconds']}s")
```

### Database Statistics

```python
stats = await connection.get_database_stats()
print(f"Collections: {stats['collections']}")
print(f"Data Size: {stats['data_size']} bytes")
```

## Collections and Indexes

The module automatically creates the following collections with optimized indexes:

### content_metadata
- `content_id` (unique)
- `url`
- `title`
- `created_at`
- Text index on `title` and `summary`

### user_interactions
- `content_id`
- `interaction_type`
- `timestamp`

### search_analytics
- `query`
- `timestamp`
- `result_count`

### processing_jobs
- `job_id` (unique)
- `status`
- `created_at`
- `content_id`

## Integration with Vector Database

The MongoDB module works seamlessly with the vector database module:

```python
from mongodb import ContentMetadata
from vector_db import VectorContentProcessor

# Store in both MongoDB and vector database
content_metadata = ContentMetadata(...)
vector_processor = VectorContentProcessor()

# Store metadata in MongoDB
collection = connection.get_collection('content_metadata')
await collection.insert_one(content_metadata.to_dict())

# Store vectors for similarity search
await vector_processor.process_content(content_metadata)
```

## Error Handling

The module provides comprehensive error handling:

```python
from mongodb.config.connection import MongoDBConnectionError

try:
    await connection.connect()
except MongoDBConnectionError as e:
    logger.error(f"Failed to connect: {e}")
```

## Production Considerations

### Connection Pooling
- Configurable pool sizes (min/max)
- Connection timeout settings
- Automatic reconnection handling

### Security
- Authentication support
- SSL/TLS configuration
- Connection string security

### Monitoring
- Health check endpoints
- Performance metrics
- Error tracking and logging

### Scalability
- Optimized indexes for query performance
- Efficient data models
- Batch operation support

## Docker Services

The `docker-compose.yml` includes:

- **MongoDB**: Main database service
- **Mongo Express**: Web-based admin interface (optional)
- **Persistent volumes**: Data persistence across restarts
- **Network isolation**: Secure container networking

Access Mongo Express at: http://localhost:8081

## Troubleshooting

### Connection Issues
```bash
# Check if MongoDB is running
./scripts/mongodb_setup.sh status

# View logs
./scripts/mongodb_setup.sh logs

# Restart service
./scripts/mongodb_setup.sh restart
```

### Performance Issues
```python
# Check database statistics
stats = await connection.get_database_stats()
print(stats)

# Monitor slow queries (enable profiling)
await connection.database.set_profiling_level(1, slow_ms=100)
```

### Data Issues
```python
# Verify indexes
collections = await connection.database.list_collection_names()
for collection_name in collections:
    collection = connection.get_collection(collection_name)
    indexes = await collection.list_indexes().to_list(None)
    print(f"{collection_name}: {len(indexes)} indexes")
```

## License

This module is part of the SelfLearning project and follows the same license terms.
