# Blog AI Database Schema

## Database: `blog_ai_db`

This database contains collections for managing blog content processing, AI-generated summaries, and Q&A generation.

## Collections Overview

### 1. 📄 **raw_blog_content**
**Purpose**: Store original blog content as crawled from sources

```javascript
{
  _id: ObjectId,
  blog_id: "unique_blog_identifier", // Unique index
  url: "https://example.com/blog-post", // Index
  title: "Original Blog Title",
  content: "Full blog content text...",
  html_content: "<html>Original HTML...</html>", // Optional
  author: "Author Name",
  published_date: ISODate("2024-01-15"),
  crawled_at: ISODate("2024-01-16"), // Index (desc)
  source_domain: "example.com",
  word_count: 1500,
  language: "en",
  content_type: "article", // article, tutorial, news, review
  raw_metadata: {
    // Any additional metadata from crawling
    meta_description: "...",
    keywords: ["keyword1", "keyword2"],
    og_image: "https://...",
    canonical_url: "https://..."
  },
  processing_status: "pending", // pending, processing, completed, failed
  created_at: ISODate,
  updated_at: ISODate
}
```

**Indexes:**
- `blog_id` (unique)
- `url`
- `created_at` (descending)

### 2. 📊 **blog_meta_data**
**Purpose**: Store processed metadata and categorization information

```javascript
{
  _id: ObjectId,
  blog_id: "unique_blog_identifier", // Unique index, references raw_blog_content
  title: "Processed/Cleaned Title", // Index
  author: "Author Name", // Index
  published_date: ISODate("2024-01-15"), // Index (desc)
  
  // Categorization
  tags: ["AI", "Machine Learning", "Python"], // Index
  categories: ["Technology", "Programming"],
  topics: ["artificial-intelligence", "data-science"],
  difficulty_level: "intermediate", // beginner, intermediate, advanced
  
  // Content metrics
  word_count: 1500,
  reading_time_minutes: 6,
  complexity_score: 0.7, // 0-1 scale
  
  // SEO and social
  meta_description: "Article description...",
  keywords: ["primary", "secondary", "keywords"],
  social_shares: {
    twitter: 25,
    linkedin: 12,
    facebook: 8
  },
  
  // Quality metrics
  content_quality_score: 0.85, // 0-1 scale
  readability_score: 0.75,
  
  // Processing info
  processed_by: "ai_processor_v1",
  processed_at: ISODate,
  last_updated: ISODate,
  
  // Relationships
  related_blogs: ["blog_id_1", "blog_id_2"], // Similar content
  source_url: "https://original-source.com",
  
  metadata: {} // Additional flexible metadata
}
```

**Indexes:**
- `blog_id` (unique)
- `title`
- `author`
- `published_date` (descending)
- `tags`

### 3. 📝 **blog_summary**
**Purpose**: Store AI-generated summaries and key insights

```javascript
{
  _id: ObjectId,
  blog_id: "unique_blog_identifier", // Unique index, references raw_blog_content
  
  // Summary content
  summary_text: "Comprehensive summary of the blog post...",
  key_points: [
    "Key insight 1",
    "Key insight 2",
    "Key insight 3"
  ],
  main_topics: ["topic1", "topic2"],
  
  // Summary metadata
  summary_length: "medium", // short, medium, long
  summary_type: "extractive", // extractive, abstractive, hybrid
  
  // AI generation info
  ai_model: "gpt-4",
  ai_provider: "openai",
  generation_parameters: {
    max_tokens: 500,
    temperature: 0.7,
    model_version: "gpt-4-0613"
  },
  
  // Quality metrics
  confidence_score: 0.92, // 0-1 scale
  coherence_score: 0.88,
  relevance_score: 0.95,
  
  // Processing info
  generated_at: ISODate, // Index (desc)
  processing_time_seconds: 15.2,
  tokens_used: 1250,
  cost_usd: 0.025,
  
  // Versions (for A/B testing different summaries)
  version: 1,
  is_active: true,
  
  // User feedback (optional)
  user_ratings: {
    helpful_count: 5,
    not_helpful_count: 1,
    average_rating: 4.2
  },
  
  created_at: ISODate,
  updated_at: ISODate
}
```

**Indexes:**
- `blog_id` (unique)
- `created_at` (descending)

### 4. ❓ **blog_qna**
**Purpose**: Store AI-generated questions and answers

```javascript
{
  _id: ObjectId,
  blog_id: "unique_blog_identifier", // Index, references raw_blog_content
  
  // Question details
  question: "What is the main benefit of using ThreadLocal in Java?",
  answer: "ThreadLocal provides thread-specific storage...",
  
  // Question metadata
  question_type: "factual", // Index: factual, conceptual, analytical, practical
  difficulty_level: "intermediate", // beginner, intermediate, advanced
  topic_area: "java-concurrency",
  
  // AI generation info
  ai_model: "gpt-4",
  ai_provider: "openai",
  generation_parameters: {
    question_style: "educational",
    context_window: 2000
  },
  
  // Quality metrics
  question_quality_score: 0.89, // 0-1 scale
  answer_accuracy_score: 0.94,
  relevance_score: 0.91,
  
  // Educational value
  learning_objective: "Understanding thread-local storage concepts",
  bloom_taxonomy_level: "comprehension", // knowledge, comprehension, application, analysis, synthesis, evaluation
  
  // Question set info
  question_set_id: "qset_123", // Groups related questions
  question_order: 1, // Order within the set
  total_questions_in_set: 5,
  
  // User interaction
  times_asked: 12,
  correct_answers: 8,
  user_feedback: {
    clarity_rating: 4.5,
    difficulty_rating: 3.2,
    usefulness_rating: 4.1
  },
  
  // Processing info
  generated_at: ISODate, // Index (desc)
  processing_time_seconds: 8.5,
  tokens_used: 800,
  
  // Status
  is_active: true,
  review_status: "approved", // pending, approved, rejected
  reviewed_by: "human_reviewer_id",
  reviewed_at: ISODate,
  
  created_at: ISODate,
  updated_at: ISODate
}
```

**Indexes:**
- `blog_id`
- `question_type`
- `created_at` (descending)

## Collection Relationships

```
raw_blog_content (1) ←→ (1) blog_meta_data
raw_blog_content (1) ←→ (1) blog_summary  
raw_blog_content (1) ←→ (N) blog_qna
```

## Sample Queries

### Get complete blog information
```javascript
// Get all data for a specific blog
const blogId = "blog_123";

const rawContent = db.raw_blog_content.findOne({blog_id: blogId});
const metadata = db.blog_meta_data.findOne({blog_id: blogId});
const summary = db.blog_summary.findOne({blog_id: blogId});
const questions = db.blog_qna.find({blog_id: blogId}).toArray();
```

### Find blogs by topic
```javascript
// Find all blogs about AI/ML
db.blog_meta_data.find({
  tags: {$in: ["AI", "Machine Learning", "Deep Learning"]}
}).sort({published_date: -1});
```

### Get recent summaries
```javascript
// Get summaries generated in the last 7 days
db.blog_summary.find({
  generated_at: {
    $gte: new Date(Date.now() - 7*24*60*60*1000)
  }
}).sort({generated_at: -1});
```

### Analytics queries
```javascript
// Count questions by type
db.blog_qna.aggregate([
  {$group: {
    _id: "$question_type",
    count: {$sum: 1},
    avg_quality: {$avg: "$question_quality_score"}
  }}
]);

// Top performing blogs by engagement
db.blog_meta_data.find().sort({
  "social_shares.twitter": -1,
  "content_quality_score": -1
}).limit(10);
```

## Data Flow

1. **Crawling**: Content stored in `raw_blog_content`
2. **Metadata Extraction**: Processed info stored in `blog_meta_data`
3. **AI Processing**: 
   - Summary generated → `blog_summary`
   - Questions generated → `blog_qna`
4. **User Interaction**: Feedback updates quality scores

## Backup Strategy

### Priority Levels
1. **High**: `raw_blog_content`, `blog_meta_data`
2. **Medium**: `blog_summary`, `blog_qna`

### Backup Commands
```bash
# Backup specific collections
mongodump --db blog_ai_db --collection raw_blog_content --out /backup/$(date +%Y%m%d)
mongodump --db blog_ai_db --collection blog_meta_data --out /backup/$(date +%Y%m%d)

# Full database backup
mongodump --db blog_ai_db --out /backup/full_$(date +%Y%m%d)
```

## Performance Considerations

### Indexing Strategy
- All `blog_id` fields are indexed for fast lookups
- Time-based fields (`created_at`, `published_date`) use descending indexes
- Text fields (`tags`, `title`, `author`) are indexed for search
- Consider text indexes for full-text search on content

### Scaling Recommendations
- **Sharding**: Shard by `blog_id` hash for horizontal scaling
- **Read Replicas**: Use for analytics and reporting queries
- **Archiving**: Move old content to archive collections after 1 year

## Connection String

```
mongodb://admin:password123@localhost:27017/blog_ai_db
```

## Web Interface Access

- **URL**: http://localhost:8081
- **Login**: admin / password123
- **Database**: blog_ai_db
