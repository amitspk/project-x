# Blog Q&A Platform - Production Architecture

> **Enterprise-grade system for generating and injecting AI-powered Q&A content into blog posts**

[![Architecture](https://img.shields.io/badge/Architecture-Microservices-blue.svg)](SPLIT_SERVICES_ARCHITECTURE.md)
[![Python](https://img.shields.io/badge/Python-3.13-green.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-teal.svg)](https://fastapi.tiangolo.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Latest-green.svg)](https://mongodb.com)

## 🎯 Overview

A production-grade platform that:
1. **Crawls** blog content from any URL
2. **Generates** AI-powered summaries and Q&A pairs using OpenAI
3. **Stores** content with vector embeddings for semantic search
4. **Injects** interactive question cards into blog pages via JavaScript library

## 🏗️ Architecture

### Current: Split Services (CQRS Pattern)

```
┌─────────────────┐
│  Chrome Ext     │
│  (ui-js lib)    │
└────────┬────────┘
         │ HTTP
         ▼
┌─────────────────┐     ┌─────────────────┐
│  API Service    │────▶│  MongoDB        │
│  (Port 8005)    │     │  (Queue + Data) │
│  • REST API     │◀────┤                 │
│  • Read Ops     │     └─────────────────┘
│  • Job Enqueue  │              ▲
└─────────────────┘              │
                                 │
                    ┌────────────┴────────────┐
                    │  Worker Service         │
                    │  • Background Processor │
                    │  • Crawling             │
                    │  • LLM Generation       │
                    │  • Vector Storage       │
                    └─────────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │  Shared/                │
                    │  • Services (LLM,       │
                    │    Crawler, Storage)    │
                    │  • Data (MongoDB,       │
                    │    JobRepository)       │
                    │  • Models & Utils       │
                    └─────────────────────────┘
```

### Key Features

- **CQRS Pattern**: Separate read (API) and write (Worker) paths
- **Job Queue**: MongoDB-based queue for async processing
- **URL Normalization**: Handles `www`, case, and trailing slashes
- **Deduplication**: Prevents reprocessing of same URLs
- **Question Randomization**: Server-side shuffling for variety
- **Vector Search**: Semantic similarity for related articles
- **Resilient**: Retry logic, failure handling, status tracking

## 📁 Project Structure

```
.
├── api_service/              # REST API Service (port 8005)
│   ├── api/
│   │   ├── main.py          # FastAPI app
│   │   └── routers/         # API endpoints
│   │       ├── jobs_router.py      # Job management
│   │       ├── questions_router.py # Question retrieval
│   │       ├── search_router.py    # Similarity search
│   │       └── qa_router.py        # Custom Q&A
│   ├── core/
│   │   └── config.py        # Configuration
│   └── run_server.py        # Server entrypoint
│
├── worker_service/           # Background Job Processor
│   ├── core/
│   │   └── config.py        # Configuration
│   ├── worker.py            # Main worker logic
│   └── run_worker.py        # Worker entrypoint
│
├── shared/                   # Shared Code (DRY)
│   ├── data/                # Data access layer
│   │   ├── database.py      # MongoDB connection
│   │   └── job_repository.py # Job queue management
│   ├── models/              # Data models
│   │   ├── job_queue.py     # Job models
│   │   └── schemas.py       # Pydantic schemas
│   ├── services/            # Business logic
│   │   ├── crawler_service.py   # Web crawling
│   │   ├── llm_service.py       # OpenAI integration
│   │   └── storage_service.py   # MongoDB operations
│   └── utils/               # Utilities
│       └── url_utils.py     # URL normalization
│
├── chrome-extension/         # Chrome extension (test harness)
│   ├── manifest.json
│   ├── content.js
│   └── auto-blog-question-injector.js (from ui-js/)
│
├── ui-js/                    # Production JavaScript Library
│   ├── auto-blog-question-injector.js  # Main library
│   └── README.md
│
├── docker-compose.split-services.yml  # Docker orchestration
├── start_split_services.sh            # Quick start script
└── requirements.txt                   # Python dependencies
```

## 🚀 Quick Start

### Prerequisites

- Python 3.13+
- MongoDB 5.0+
- OpenAI API key

### Installation

```bash
# Clone repository
git clone <repo-url>
cd SelfLearning

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY="your-api-key"
export MONGODB_USERNAME="admin"
export MONGODB_PASSWORD="password123"
```

### Start Services

```bash
# Start MongoDB (Docker)
docker run -d -p 27017:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=password123 \
  --name mongodb mongo:latest

# Start API Service (Terminal 1)
cd api_service
python run_server.py

# Start Worker Service (Terminal 2)
cd worker_service
python run_worker.py
```

### Process a Blog

```bash
# Enqueue a blog for processing
curl -X POST http://localhost:8005/api/v1/jobs/process \
  -H "Content-Type: application/json" \
  -d '{"blog_url": "https://example.com/blog-post"}'

# Check job status
curl http://localhost:8005/api/v1/jobs/status/{job_id}

# Get generated questions
curl "http://localhost:8005/api/v1/questions/by-url?blog_url=https://example.com/blog-post&randomize=true"
```

## 📚 API Documentation

### Job Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/jobs/process` | POST | Enqueue blog for processing |
| `/api/v1/jobs/status/{id}` | GET | Get job status |
| `/api/v1/jobs/stats` | GET | Get queue statistics |
| `/api/v1/jobs/cancel/{id}` | POST | Cancel a job |

### Question Retrieval

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/questions/by-url` | GET | Get questions for a blog URL |

Query Parameters:
- `blog_url` (required): Blog URL
- `limit` (optional): Max questions (default: 10)
- `randomize` (optional): Randomize order (default: false)

### Similarity Search

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/search/similar` | POST | Find similar blogs |

### Custom Q&A

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/qa/ask` | POST | Answer any question |

## 🎨 Frontend Integration

### Using the JavaScript Library

```html
<!-- Include the library -->
<script src="https://your-cdn.com/auto-blog-question-injector.js"></script>

<!-- Initialize -->
<script>
  AutoBlogQuestionInjector.autoInit({
    apiBaseUrl: 'https://your-api.com/api/v1',
    randomizeOrder: true,
    debugMode: false
  });
</script>
```

### Chrome Extension Testing

1. Open Chrome: `chrome://extensions`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select the `chrome-extension/` directory
5. Visit any supported blog URL

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `MONGODB_URL` | MongoDB connection string | `mongodb://localhost:27017` |
| `MONGODB_USERNAME` | MongoDB username | `admin` |
| `MONGODB_PASSWORD` | MongoDB password | `password123` |
| `API_SERVICE_PORT` | API service port | `8005` |
| `POLL_INTERVAL` | Worker poll interval (seconds) | `5` |
| `MAX_RETRIES` | Max job retry attempts | `3` |

### URL Normalization

The system automatically normalizes URLs to prevent duplicates:

```python
# These are all treated as identical:
https://www.example.com/article
https://example.com/article
https://Example.COM/article/
www.example.com/article
```

See [URL_NORMALIZATION_COMPLETE.md](URL_NORMALIZATION_COMPLETE.md) for details.

## 🧪 Testing

### Run Unit Tests

```bash
python test_url_normalization.py
```

### Test API Endpoints

```bash
# Health check
curl http://localhost:8005/health

# Process test URL
curl -X POST http://localhost:8005/api/v1/jobs/process \
  -H "Content-Type: application/json" \
  -d '{"blog_url": "https://baeldung.com/java-threadlocal"}'
```

### Test Chrome Extension

1. Load extension in Chrome
2. Visit a supported blog (e.g., `baeldung.com`, `medium.com`)
3. Questions should appear automatically
4. Click question → Answer drawer opens
5. Use search box → AI answers custom questions

## 📊 Database Schema

### Collections

#### `raw_blog_content`
```json
{
  "_id": ObjectId,
  "url": "https://...",
  "title": "Blog Title",
  "content": "Full content...",
  "language": "en",
  "word_count": 1500,
  "metadata": {...}
}
```

#### `blog_summaries`
```json
{
  "_id": ObjectId,
  "blog_id": ObjectId,
  "blog_url": "https://...",
  "summary": "Summary text...",
  "key_points": ["Point 1", "Point 2"],
  "embedding": [0.123, 0.456, ...]  // 1536 dimensions
}
```

#### `processed_questions`
```json
{
  "_id": ObjectId,
  "blog_id": ObjectId,
  "blog_url": "https://...",
  "question": "What is X?",
  "answer": "X is...",
  "icon": "💡",
  "embedding": [0.123, 0.456, ...]
}
```

#### `processing_jobs`
```json
{
  "job_id": "uuid",
  "blog_url": "https://...",
  "status": "queued|processing|completed|failed",
  "failure_count": 0,
  "max_retries": 3,
  "error_message": null,
  "created_at": ISODate,
  "started_at": ISODate,
  "completed_at": ISODate
}
```

## 🛠️ Development

### Adding a New Endpoint

1. Create router in `api_service/api/routers/`
2. Register in `api_service/api/main.py`
3. Add business logic to `shared/services/`
4. Update documentation

### Modifying Worker Logic

1. Edit `worker_service/worker.py`
2. Update shared services if needed
3. Test with a sample blog URL

### Code Style

- Follow PEP 8
- Use type hints
- Write docstrings (Google style)
- Keep functions < 50 lines
- Use async/await for I/O operations

## 📈 Performance

### Benchmarks

- **Blog Processing**: ~20-40 seconds per blog
- **Question Generation**: 5 Q&A pairs per blog
- **API Response Time**: < 100ms (cached)
- **Vector Search**: < 200ms

### Scaling Considerations

- **Horizontal Scaling**: Add more worker instances
- **Database**: MongoDB sharding for large datasets
- **Caching**: Redis for frequently accessed questions
- **Rate Limiting**: Built-in for API protection

## 🐛 Troubleshooting

### Common Issues

**Problem**: Questions not saving
- **Solution**: Check worker logs for JSON parsing errors
- LLM might wrap JSON in markdown code blocks (fixed in latest version)

**Problem**: Duplicate URLs being processed
- **Solution**: URL normalization handles this automatically
- Ensure latest code is running

**Problem**: Chrome extension not loading questions
- **Solution**: Check supported domains in `auto-blog-question-injector.js`
- Verify API is running on `localhost:8005`
- Check browser console for errors

## 📝 Documentation

- **Architecture**: [SPLIT_SERVICES_ARCHITECTURE.md](SPLIT_SERVICES_ARCHITECTURE.md)
- **URL Normalization**: [URL_NORMALIZATION_COMPLETE.md](URL_NORMALIZATION_COMPLETE.md)
- **API Examples**: See API Documentation section above

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

[Your License Here]

## 👥 Authors

Senior Software Engineer Team

---

**Status**: ✅ Production Ready

**Last Updated**: October 2025

**Version**: 3.0.0 (Split Services Architecture)

