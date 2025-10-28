# Blog Manager Microservice

A production-ready microservice built with FastAPI and MongoDB for managing blog content and Q&A. Follows n-tier architecture with clean separation of concerns.

## 🏗️ Architecture

The microservice follows a clean n-tier architecture:

```
blog_manager/
├── api/                    # Presentation Layer (FastAPI)
│   ├── main.py            # FastAPI app with middleware
│   └── routers/           # API route handlers
├── services/              # Business Logic Layer
│   └── blog_service.py    # Core business logic
├── data/                  # Data Access Layer
│   ├── database.py        # MongoDB connection manager
│   └── repositories.py   # Repository pattern implementation
├── models/                # Data Models
│   ├── request_models.py  # API request validation
│   ├── response_models.py # API response models
│   └── mongodb_models.py  # MongoDB document models
└── core/                  # Core Infrastructure
    ├── config.py          # Configuration management
    └── exceptions.py      # Custom exceptions
```

## 🚀 Features

- **RESTful API** for blog content and Q&A management
- **MongoDB Integration** with connection pooling and health checks
- **Smart URL Lookup** with fallback mechanisms
- **Comprehensive Error Handling** with custom exceptions
- **Request/Response Validation** using Pydantic models
- **Health Check Endpoints** for monitoring
- **CORS Support** for web applications
- **Structured Logging** with request tracking
- **Production Ready** with proper middleware and exception handling

## 📋 Prerequisites

- Python 3.8+
- MongoDB (running via Docker or locally)
- Required Python packages (see requirements.txt)

## 🛠️ Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start MongoDB** (if using Docker):
   ```bash
   cd mongodb
   ./scripts/mongodb_setup.sh start
   ```

3. **Configure Environment** (optional):
   ```bash
   # Create .env file in blog_manager/ directory
   echo "DEBUG=true" > blog_manager/.env
   echo "MONGODB_HOST=localhost" >> blog_manager/.env
   echo "MONGODB_PORT=27017" >> blog_manager/.env
   ```

## 🏃‍♂️ Running the Service

### Quick Start
```bash
cd blog_manager
python run_server.py
```

### Development Mode
```bash
python run_server.py --debug --reload
```

### Production Mode
```bash
python run_server.py --host 0.0.0.0 --port 8000 --workers 4
```

### Custom Configuration
```bash
python run_server.py --host 127.0.0.1 --port 8080 --log-level INFO
```

## 📡 API Endpoints

### Main Endpoint: Get Blog Questions by URL

**GET** `/api/v1/blogs/by-url`

Retrieve all questions and answers for a blog by its URL.

**Parameters:**
- `url` (required): The blog URL to lookup
- `include_summary` (optional): Include blog summary in response
- `include_metadata` (optional): Include question metadata
- `limit` (optional): Maximum number of questions to return
- `offset` (optional): Number of questions to skip

**Example:**
```bash
curl "http://localhost:8000/api/v1/blogs/by-url?url=https://medium.com/@alxkm/effective-use-of-threadlocal-in-java-applications-f4eb6a648d4a"
```

**Response:**
```json
{
  "success": true,
  "blog_info": {
    "blog_id": "effective_use_of_threadlocal_in_java_app_5bbb34ce",
    "title": "Effective Use of ThreadLocal in Java Applications",
    "url": "https://medium.com/@alxkm/effective-use-of-threadlocal-in-java-applications-f4eb6a648d4a",
    "author": "Alex Klimenko",
    "word_count": 3659,
    "source_domain": "medium.com"
  },
  "questions": [
    {
      "id": "q1",
      "question": "What are the potential risks of not using ThreadLocal?",
      "answer": "Not using ThreadLocal can lead to data inconsistency...",
      "question_type": "cause and effect",
      "question_order": 1,
      "confidence_score": 0.9
    }
  ],
  "total_questions": 10,
  "returned_questions": 10,
  "has_more": false,
  "processing_time_ms": 45.2
}
```

### Other Endpoints

- **GET** `/api/v1/blogs/{blog_id}/questions` - Get questions by blog ID
- **GET** `/api/v1/blogs/search?q={query}` - Search blogs by text
- **GET** `/api/v1/blogs/recent` - Get recently added blogs
- **GET** `/api/v1/blogs/stats` - Get blog statistics
- **GET** `/health` - Health check
- **GET** `/health/ready` - Readiness check
- **GET** `/health/live` - Liveness check

## 🔧 Configuration

The service can be configured via environment variables or `.env` file:

### Application Settings
- `DEBUG` - Enable debug mode (default: false)
- `API_HOST` - Host to bind to (default: 0.0.0.0)
- `API_PORT` - Port to bind to (default: 8000)
- `LOG_LEVEL` - Logging level (default: INFO)

### MongoDB Settings
- `MONGODB_HOST` - MongoDB host (default: localhost)
- `MONGODB_PORT` - MongoDB port (default: 27017)
- `MONGODB_USERNAME` - MongoDB username (default: admin)
- `MONGODB_PASSWORD` - MongoDB password (default: password123)
- `MONGODB_DATABASE` - MongoDB database (default: blog_ai_db)

### Performance Settings
- `MONGODB_MAX_POOL_SIZE` - Max connection pool size (default: 100)
- `CACHE_TTL_SECONDS` - Cache TTL in seconds (default: 3600)
- `RATE_LIMIT_REQUESTS` - Rate limit requests per window (default: 100)

## 🧪 Testing

### Manual Testing

1. **Health Check**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **Get Blog Questions**:
   ```bash
   curl "http://localhost:8000/api/v1/blogs/by-url?url=https://medium.com/@alxkm/effective-use-of-threadlocal-in-java-applications-f4eb6a648d4a"
   ```

3. **Search Blogs**:
   ```bash
   curl "http://localhost:8000/api/v1/blogs/search?q=ThreadLocal"
   ```

### Using the API Documentation

The microservice provides comprehensive API documentation through multiple interfaces:

#### **Swagger UI (Interactive Documentation)**
- **URL**: `http://localhost:8001/docs`
- **Features**: Interactive API testing, request/response examples, schema validation
- **Best for**: Testing endpoints, understanding request/response formats

#### **ReDoc (Alternative Documentation)**
- **URL**: `http://localhost:8001/redoc`
- **Features**: Clean, readable documentation with detailed schemas
- **Best for**: Reading comprehensive API documentation

#### **OpenAPI Schema**
- **URL**: `http://localhost:8001/openapi.json`
- **Features**: Machine-readable API specification
- **Best for**: Code generation, API client development

#### **Service Information**
- **URL**: `http://localhost:8001/`
- **Features**: Basic service info with documentation links
- **Best for**: Quick service overview and navigation

## 📊 Monitoring

### Health Checks

The service provides multiple health check endpoints:

- `/health` - Comprehensive health status
- `/health/ready` - Readiness for accepting requests
- `/health/live` - Basic liveness check

### Logging

The service uses structured logging with:
- Request/response logging
- Performance metrics
- Error tracking
- Database operation logging

### Metrics

Response headers include:
- `X-Process-Time` - Request processing time in milliseconds

## 🔒 Security

- Input validation using Pydantic models
- SQL injection prevention through MongoDB ODM
- CORS configuration for web security
- Rate limiting (configurable)
- Proper error handling without information leakage

## 🚀 Production Deployment

### Docker Deployment

1. **Create Dockerfile**:
   ```dockerfile
   FROM python:3.9-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY blog_manager/ ./blog_manager/
   EXPOSE 8000
   CMD ["python", "blog_manager/run_server.py", "--host", "0.0.0.0"]
   ```

2. **Build and Run**:
   ```bash
   docker build -t blog-manager .
   docker run -p 8000:8000 blog-manager
   ```

### Environment Variables for Production

```bash
export DEBUG=false
export LOG_LEVEL=INFO
export MONGODB_HOST=your-mongodb-host
export MONGODB_USERNAME=your-username
export MONGODB_PASSWORD=your-password
export API_HOST=0.0.0.0
export API_PORT=8000
```

## 🤝 Integration Examples

### JavaScript/Frontend Integration

```javascript
// Fetch blog questions
async function getBlogQuestions(url) {
    const response = await fetch(
        `http://localhost:8000/api/v1/blogs/by-url?url=${encodeURIComponent(url)}`
    );
    const data = await response.json();
    return data;
}

// Usage
const questions = await getBlogQuestions('https://medium.com/@author/article');
console.log(`Found ${questions.total_questions} questions`);
```

### Python Client Integration

```python
import requests

def get_blog_questions(url):
    response = requests.get(
        "http://localhost:8000/api/v1/blogs/by-url",
        params={"url": url}
    )
    return response.json()

# Usage
questions = get_blog_questions("https://medium.com/@author/article")
print(f"Found {questions['total_questions']} questions")
```

## 📝 Error Handling

The API returns structured error responses:

```json
{
  "success": false,
  "error_code": "BLOG_NOT_FOUND",
  "message": "Blog not found for URL: https://example.com/nonexistent",
  "details": {
    "identifier": "https://example.com/nonexistent",
    "identifier_type": "URL"
  },
  "timestamp": "2025-10-02T20:52:42.869Z"
}
```

Common error codes:
- `BLOG_NOT_FOUND` - Blog not found
- `NO_QUESTIONS_FOUND` - No questions available
- `INVALID_URL` - Invalid URL format
- `VALIDATION_ERROR` - Request validation failed
- `DATABASE_CONNECTION_ERROR` - Database connection issues

## 🔄 Development

### Project Structure

The microservice follows clean architecture principles:

1. **API Layer** - FastAPI routers and middleware
2. **Service Layer** - Business logic and orchestration
3. **Repository Layer** - Data access abstraction
4. **Model Layer** - Data validation and serialization
5. **Core Layer** - Configuration and shared utilities

### Adding New Features

1. **Add Models** - Define request/response models
2. **Update Repository** - Add data access methods
3. **Implement Service** - Add business logic
4. **Create Router** - Add API endpoints
5. **Update Tests** - Add test coverage

## 📚 Dependencies

- **FastAPI** - Modern web framework
- **Motor** - Async MongoDB driver
- **PyMongo** - MongoDB driver
- **Pydantic** - Data validation
- **Uvicorn** - ASGI server

## 🆘 Troubleshooting

### Common Issues

1. **MongoDB Connection Failed**:
   - Check if MongoDB is running
   - Verify connection settings
   - Check network connectivity

2. **Import Errors**:
   - Install dependencies: `pip install -r requirements.txt`
   - Check Python path configuration

3. **Port Already in Use**:
   - Use different port: `--port 8001`
   - Kill existing process

### Debug Mode

Run with debug mode for detailed logging:
```bash
python run_server.py --debug --log-level DEBUG
```

## 📄 License

This project is part of the SelfLearning repository and follows the same license terms.

## 🤝 Contributing

1. Follow the existing code structure
2. Add proper error handling
3. Include comprehensive logging
4. Update documentation
5. Add tests for new features
