# MongoDB Collections Design for SelfLearning Project

## Database Structure

**Database Name**: `selflearning`

## Collections Overview

### 1. 📄 **content_metadata**
**Purpose**: Store processed content with summaries and questions
```javascript
{
  _id: ObjectId,
  content_id: "unique_article_id",
  url: "https://example.com/article",
  title: "Article Title",
  summary: "Generated summary text",
  key_points: ["Point 1", "Point 2"],
  questions: [
    {
      question: "What is ThreadLocal?",
      type: "factual",
      difficulty: "beginner"
    }
  ],
  word_count: 1200,
  reading_time_minutes: 5,
  language: "en",
  content_type: "article",
  processed_at: ISODate,
  llm_provider: "openai",
  llm_model: "gpt-4",
  tags: ["java", "concurrency"],
  categories: ["programming"],
  vector_db_id: "chroma_doc_id",
  embedding_model: "text-embedding-ada-002"
}
```

### 2. 👤 **user_interactions**
**Purpose**: Track user engagement and behavior analytics
```javascript
{
  _id: ObjectId,
  interaction_id: "uuid",
  content_id: "article_id",
  user_id: "user_123", // Optional for future user system
  session_id: "session_abc",
  interaction_type: "question_answered", // view, bookmark_added, etc.
  timestamp: ISODate,
  question_id: "q1",
  answer_provided: "User's answer",
  time_spent_seconds: 180,
  scroll_percentage: 85.5,
  user_agent: "Chrome/...",
  referrer: "https://google.com"
}
```

### 3. 🔍 **search_analytics**
**Purpose**: Monitor search patterns and performance
```javascript
{
  _id: ObjectId,
  search_id: "uuid",
  query: "ThreadLocal Java",
  result_count: 5,
  search_time_ms: 45.2,
  timestamp: ISODate,
  search_type: "similarity", // similarity, keyword, hybrid
  embedding_model: "text-embedding-ada-002",
  similarity_threshold: 0.7,
  clicked_results: ["article_123"],
  result_click_positions: [1],
  user_id: "user_123",
  session_id: "session_abc"
}
```

### 4. ⚙️ **processing_jobs**
**Purpose**: Track content processing pipeline jobs
```javascript
{
  _id: ObjectId,
  job_id: "uuid",
  content_id: "article_123",
  url: "https://example.com/article",
  job_type: "generate_questions", // crawl, summarize, index_vectors
  status: "completed", // pending, running, completed, failed
  created_at: ISODate,
  started_at: ISODate,
  completed_at: ISODate,
  progress_percentage: 100.0,
  current_step: "Generating questions",
  result: {
    questions_generated: 5,
    processing_time: 2.3,
    tokens_used: 1250
  },
  error_message: null,
  llm_provider: "openai",
  llm_model: "gpt-4"
}
```

### 5. 🎯 **vector_mappings** (New Recommendation)
**Purpose**: Map between MongoDB documents and vector database entries
```javascript
{
  _id: ObjectId,
  content_id: "article_123",
  vector_db_type: "chromadb", // chromadb, faiss, pinecone
  vector_db_id: "chroma_doc_id",
  embedding_model: "text-embedding-ada-002",
  embedding_dimensions: 1536,
  indexed_at: ISODate,
  chunk_count: 3, // If content is split into chunks
  chunks: [
    {
      chunk_id: "chunk_1",
      vector_db_id: "chroma_chunk_1",
      start_position: 0,
      end_position: 500,
      text_preview: "First 100 chars..."
    }
  ]
}
```

### 6. 📊 **system_metrics** (New Recommendation)
**Purpose**: Store system performance and usage metrics
```javascript
{
  _id: ObjectId,
  metric_type: "daily_usage", // daily_usage, performance, errors
  date: ISODate,
  metrics: {
    total_articles_processed: 25,
    total_questions_generated: 125,
    total_searches: 89,
    avg_processing_time_seconds: 15.2,
    unique_users: 12,
    popular_topics: ["java", "python", "javascript"]
  },
  created_at: ISODate
}
```

### 7. 🔧 **configuration** (New Recommendation)
**Purpose**: Store application configuration and settings
```javascript
{
  _id: ObjectId,
  config_type: "llm_settings", // llm_settings, vector_db_settings, ui_settings
  environment: "production", // development, staging, production
  settings: {
    default_llm_provider: "openai",
    default_model: "gpt-4",
    max_questions_per_article: 5,
    similarity_threshold: 0.7,
    max_search_results: 10
  },
  updated_at: ISODate,
  updated_by: "admin"
}
```

## Indexes Strategy

### Performance Indexes
```javascript
// content_metadata
db.content_metadata.createIndex({ "content_id": 1 }, { unique: true })
db.content_metadata.createIndex({ "url": 1 })
db.content_metadata.createIndex({ "tags": 1 })
db.content_metadata.createIndex({ "processed_at": -1 })
db.content_metadata.createIndex({ "title": "text", "summary": "text" })

// user_interactions
db.user_interactions.createIndex({ "content_id": 1 })
db.user_interactions.createIndex({ "session_id": 1 })
db.user_interactions.createIndex({ "timestamp": -1 })
db.user_interactions.createIndex({ "interaction_type": 1 })

// search_analytics
db.search_analytics.createIndex({ "query": 1 })
db.search_analytics.createIndex({ "timestamp": -1 })
db.search_analytics.createIndex({ "search_type": 1 })

// processing_jobs
db.processing_jobs.createIndex({ "job_id": 1 }, { unique: true })
db.processing_jobs.createIndex({ "status": 1 })
db.processing_jobs.createIndex({ "created_at": -1 })
db.processing_jobs.createIndex({ "content_id": 1 })

// vector_mappings
db.vector_mappings.createIndex({ "content_id": 1 }, { unique: true })
db.vector_mappings.createIndex({ "vector_db_type": 1, "vector_db_id": 1 })

// system_metrics
db.system_metrics.createIndex({ "metric_type": 1, "date": -1 })

// configuration
db.configuration.createIndex({ "config_type": 1, "environment": 1 }, { unique: true })
```

## Collection Relationships

```
content_metadata (1) ←→ (N) user_interactions
content_metadata (1) ←→ (N) processing_jobs
content_metadata (1) ←→ (1) vector_mappings
search_analytics (N) ←→ (N) content_metadata (via clicked_results)
```

## Data Consistency Rules

1. **content_id** must be consistent across all collections
2. **processing_jobs** should be created before processing starts
3. **vector_mappings** should be created after successful vector indexing
4. **user_interactions** should reference valid content_id
5. **search_analytics** clicked_results should reference valid content_ids

## Backup Strategy

### Daily Backups
```bash
# Backup entire database
mongodump --db selflearning --out /backup/$(date +%Y%m%d)

# Backup specific collections
mongodump --db selflearning --collection content_metadata --out /backup/content_$(date +%Y%m%d)
```

### Collection Priority for Backups
1. **High Priority**: content_metadata, vector_mappings
2. **Medium Priority**: processing_jobs, configuration
3. **Low Priority**: user_interactions, search_analytics, system_metrics

## Scaling Considerations

### Horizontal Scaling (Sharding)
If you reach high volume, consider sharding by:
- **content_metadata**: Shard by `content_id` hash
- **user_interactions**: Shard by `session_id` or `user_id`
- **search_analytics**: Shard by `timestamp` (time-based)

### Vertical Scaling
- Increase MongoDB server resources
- Use MongoDB Atlas for managed scaling
- Implement read replicas for analytics queries

## Alternative Approaches (Not Recommended for Your Project)

### ❌ Multiple Databases
```
databases:
├── content_db          // Only content data
├── analytics_db        // Only analytics data
├── jobs_db            // Only processing jobs
└── config_db          // Only configuration
```

**Why Not Recommended:**
- Complex connection management
- No cross-database transactions
- Harder to maintain data consistency
- More complex backup/restore procedures
- Increased operational overhead

### ❌ Single Collection with Type Field
```javascript
{
  _id: ObjectId,
  type: "content", // content, interaction, search, job
  data: { /* all data in one field */ }
}
```

**Why Not Recommended:**
- Poor query performance
- No schema validation per type
- Difficult indexing strategy
- Complex application logic
- Poor data modeling practices

## Best Practices Summary

1. ✅ **Use one database with multiple collections**
2. ✅ **Design collections based on access patterns**
3. ✅ **Create appropriate indexes for performance**
4. ✅ **Maintain referential integrity via application logic**
5. ✅ **Use consistent naming conventions**
6. ✅ **Plan for future scaling needs**
7. ✅ **Implement proper backup strategies**
8. ✅ **Monitor collection sizes and performance**
