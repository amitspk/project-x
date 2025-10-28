// MongoDB initialization script
// This script runs when the MongoDB container starts for the first time

// Switch to the blog_ai_db database
db = db.getSiblingDB('blog_ai_db');

// Create collections with initial structure
db.createCollection('content_metadata', {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["content_id", "title", "created_at"],
      properties: {
        content_id: {
          bsonType: "string",
          description: "Unique identifier for the content"
        },
        title: {
          bsonType: "string",
          description: "Title of the content"
        },
        url: {
          bsonType: "string",
          description: "URL of the original content"
        },
        author: {
          bsonType: "string",
          description: "Author of the content"
        },
        content_type: {
          bsonType: "string",
          enum: ["article", "tutorial", "news", "review", "summary"],
          description: "Type of content"
        },
        tags: {
          bsonType: "array",
          items: {
            bsonType: "string"
          },
          description: "Tags associated with the content"
        },
        categories: {
          bsonType: "array",
          items: {
            bsonType: "string"
          },
          description: "Categories for the content"
        },
        word_count: {
          bsonType: "int",
          minimum: 0,
          description: "Number of words in the content"
        },
        reading_time: {
          bsonType: "int",
          minimum: 0,
          description: "Estimated reading time in minutes"
        },
        created_at: {
          bsonType: "date",
          description: "When the content was created"
        },
        updated_at: {
          bsonType: "date",
          description: "When the content was last updated"
        },
        processed_at: {
          bsonType: "date",
          description: "When the content was processed"
        },
        vector_indexed: {
          bsonType: "bool",
          description: "Whether the content has been indexed in vector database"
        },
        vector_doc_id: {
          bsonType: "string",
          description: "Document ID in the vector database"
        },
        processing_status: {
          bsonType: "string",
          enum: ["pending", "processing", "completed", "failed", "skipped"],
          description: "Processing status of the content"
        },
        summary: {
          bsonType: "object",
          properties: {
            text: { bsonType: "string" },
            key_points: { 
              bsonType: "array",
              items: { bsonType: "string" }
            },
            topics: {
              bsonType: "array", 
              items: { bsonType: "string" }
            },
            confidence_score: { bsonType: "double" }
          },
          description: "Generated summary information"
        },
        questions: {
          bsonType: "object",
          properties: {
            count: { bsonType: "int" },
            average_confidence: { bsonType: "double" },
            file_path: { bsonType: "string" }
          },
          description: "Generated questions information"
        }
      }
    }
  }
});

// Create collection for user interactions and analytics
db.createCollection('user_interactions', {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["interaction_type", "timestamp"],
      properties: {
        interaction_type: {
          bsonType: "string",
          enum: ["search", "view", "bookmark", "share", "download"],
          description: "Type of user interaction"
        },
        content_id: {
          bsonType: "string",
          description: "ID of the content interacted with"
        },
        search_query: {
          bsonType: "string",
          description: "Search query if interaction is search"
        },
        similarity_score: {
          bsonType: "double",
          description: "Similarity score if from vector search"
        },
        user_id: {
          bsonType: "string",
          description: "User identifier (optional)"
        },
        session_id: {
          bsonType: "string",
          description: "Session identifier"
        },
        timestamp: {
          bsonType: "date",
          description: "When the interaction occurred"
        },
        metadata: {
          bsonType: "object",
          description: "Additional interaction metadata"
        }
      }
    }
  }
});

// Create collection for search analytics
db.createCollection('search_analytics', {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["query", "timestamp", "results_count"],
      properties: {
        query: {
          bsonType: "string",
          description: "The search query"
        },
        results_count: {
          bsonType: "int",
          minimum: 0,
          description: "Number of results returned"
        },
        avg_similarity_score: {
          bsonType: "double",
          description: "Average similarity score of results"
        },
        response_time_ms: {
          bsonType: "int",
          minimum: 0,
          description: "Response time in milliseconds"
        },
        timestamp: {
          bsonType: "date",
          description: "When the search was performed"
        },
        filters_used: {
          bsonType: "object",
          description: "Filters applied to the search"
        },
        top_results: {
          bsonType: "array",
          items: {
            bsonType: "object",
            properties: {
              content_id: { bsonType: "string" },
              similarity_score: { bsonType: "double" },
              title: { bsonType: "string" }
            }
          },
          description: "Top search results"
        }
      }
    }
  }
});

// Create collection for processing jobs and status
db.createCollection('processing_jobs', {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["job_type", "status", "created_at"],
      properties: {
        job_type: {
          bsonType: "string",
          enum: ["crawl", "summarize", "generate_questions", "vector_index", "batch_process"],
          description: "Type of processing job"
        },
        status: {
          bsonType: "string",
          enum: ["pending", "running", "completed", "failed", "cancelled"],
          description: "Current status of the job"
        },
        input_data: {
          bsonType: "object",
          description: "Input parameters for the job"
        },
        output_data: {
          bsonType: "object",
          description: "Results of the job"
        },
        progress: {
          bsonType: "object",
          properties: {
            current: { bsonType: "int" },
            total: { bsonType: "int" },
            percentage: { bsonType: "double" }
          },
          description: "Job progress information"
        },
        error_message: {
          bsonType: "string",
          description: "Error message if job failed"
        },
        created_at: {
          bsonType: "date",
          description: "When the job was created"
        },
        started_at: {
          bsonType: "date",
          description: "When the job started processing"
        },
        completed_at: {
          bsonType: "date",
          description: "When the job completed"
        },
        duration_ms: {
          bsonType: "int",
          description: "Job duration in milliseconds"
        }
      }
    }
  }
});

// Create indexes for better performance
db.content_metadata.createIndex({ "content_id": 1 }, { unique: true });
db.content_metadata.createIndex({ "url": 1 });
db.content_metadata.createIndex({ "content_type": 1 });
db.content_metadata.createIndex({ "tags": 1 });
db.content_metadata.createIndex({ "created_at": -1 });
db.content_metadata.createIndex({ "processing_status": 1 });
db.content_metadata.createIndex({ "vector_indexed": 1 });

db.user_interactions.createIndex({ "timestamp": -1 });
db.user_interactions.createIndex({ "interaction_type": 1 });
db.user_interactions.createIndex({ "content_id": 1 });
db.user_interactions.createIndex({ "search_query": "text" });

db.search_analytics.createIndex({ "timestamp": -1 });
db.search_analytics.createIndex({ "query": "text" });

db.processing_jobs.createIndex({ "created_at": -1 });
db.processing_jobs.createIndex({ "status": 1 });
db.processing_jobs.createIndex({ "job_type": 1 });

// Insert some sample data
db.content_metadata.insertOne({
  content_id: "sample_001",
  title: "Sample Content Document",
  url: "https://example.com/sample",
  author: "System",
  content_type: "article",
  tags: ["sample", "demo"],
  categories: ["examples"],
  word_count: 500,
  reading_time: 3,
  created_at: new Date(),
  updated_at: new Date(),
  vector_indexed: false,
  processing_status: "pending"
});

print("✅ blog_ai_db database initialized successfully!");
print("📊 Collections created:");
print("   - content_metadata (with validation schema)");
print("   - user_interactions (for analytics)");
print("   - search_analytics (for search tracking)");
print("   - processing_jobs (for job management)");
print("🔍 Indexes created for optimal performance");
print("📝 Sample document inserted");
