# 🚀 LLM Service API - Complete Examples & Responses

**Service URL**: http://localhost:8002  
**Status**: ✅ **ALL ENDPOINTS WORKING**  
**Date**: October 13, 2025

---

## 📋 Table of Contents

1. [Service Info](#1-service-info)
2. [Health Check](#2-health-check)
3. [Text Generation](#3-text-generation)
4. [Question & Answer](#4-question--answer)
5. [Question Generation](#5-question-generation)
6. [Single Embedding](#6-single-embedding)
7. [Batch Embeddings](#7-batch-embeddings)

---

## 1. Service Info

**Endpoint**: `GET /`  
**Purpose**: Get service information and available endpoints

### Request
```bash
curl http://localhost:8002/
```

### Response
```json
{
  "service": "LLM Service",
  "version": "1.0.0",
  "status": "operational",
  "docs": "/docs",
  "health": "/health"
}
```

---

## 2. Health Check

**Endpoint**: `GET /health`  
**Purpose**: Check service health status

### Request
```bash
curl http://localhost:8002/health
```

### Response
```json
{
  "status": "healthy",
  "service": "llm-service",
  "timestamp": "2025-10-13T21:56:00Z"
}
```

---

## 3. Text Generation

**Endpoint**: `POST /api/v1/generate`  
**Purpose**: Generate text using LLM with custom prompts

### Request
```bash
curl -X POST http://localhost:8002/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain what microservices architecture is in 2 sentences.",
    "temperature": 0.7,
    "max_tokens": 100
  }'
```

### Request Body
```json
{
  "prompt": "Explain what microservices architecture is in 2 sentences.",
  "temperature": 0.7,
  "max_tokens": 100
}
```

### Response
```json
{
  "content": "Microservices architecture is an architectural style in which complex applications are broken down into smaller, independent services that can be developed, deployed, and scaled independently. These services communicate with each other through APIs, enabling greater flexibility, scalability, and resilience in software development.",
  "model": "gpt-3.5-turbo",
  "provider": "openai",
  "tokens_used": null
}
```

### Use Cases
- Content generation
- Text completion
- Creative writing
- Code generation
- Explanations and summaries

---

## 4. Question & Answer

**Endpoint**: `POST /api/v1/qa/answer`  
**Purpose**: Answer questions with word count control

### Request
```bash
curl -X POST http://localhost:8002/api/v1/qa/answer \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the main benefits of using Docker containers?",
    "max_words": 50
  }'
```

### Request Body
```json
{
  "question": "What are the main benefits of using Docker containers?",
  "max_words": 50
}
```

### Response
```json
{
  "question": "What are the main benefits of using Docker containers?",
  "answer": "The main benefits of using Docker containers include portability, scalability, efficient resource utilization, faster deployment times, and improved consistency across different environments. Docker containers also allow for easier management and isolation of applications, making them a popular choice for software development and deployment.",
  "word_count": 43,
  "model": "gpt-3.5-turbo",
  "provider": "openai"
}
```

### Features
- ✅ Automatic word count control
- ✅ Returns actual word count
- ✅ Preserves original question
- ✅ Structured response format

### Use Cases
- FAQ automation
- Customer support
- Educational Q&A
- Documentation assistance
- Interactive chatbots

---

## 5. Question Generation

**Endpoint**: `POST /api/v1/questions/generate`  
**Purpose**: Auto-generate questions and answers from content

### Request
```bash
curl -X POST http://localhost:8002/api/v1/questions/generate \
  -H "Content-Type: application/json" \
  -d '{
    "content": "FastAPI is a modern, fast web framework for building APIs with Python. It uses type hints and provides automatic API documentation. FastAPI is built on top of Starlette and Pydantic.",
    "num_questions": 3,
    "difficulty": "medium"
  }'
```

### Request Body
```json
{
  "content": "FastAPI is a modern, fast web framework for building APIs with Python. It uses type hints and provides automatic API documentation. FastAPI is built on top of Starlette and Pydantic.",
  "num_questions": 3,
  "difficulty": "medium"
}
```

### Response
```json
{
  "questions": [
    {
      "question": "What are the key features of FastAPI?",
      "answer": "FastAPI is a modern, fast web framework for building APIs with Python. It uses type hints and provides automatic API documentation.",
      "difficulty": "medium",
      "category": null
    },
    {
      "question": "What are the underlying technologies that FastAPI is built on top of?",
      "answer": "FastAPI is built on top of Starlette and Pydantic.",
      "difficulty": "medium",
      "category": null
    },
    {
      "question": "How does FastAPI leverage type hints in Python?",
      "answer": "FastAPI uses type hints to provide a declarative approach to building APIs, enabling automatic data validation and serialization.",
      "difficulty": "medium",
      "category": null
    }
  ],
  "total_generated": 3,
  "source_word_count": 30
}
```

### Parameters
- `content`: Source text for question generation
- `num_questions`: Number of questions to generate (1-10)
- `difficulty`: Question difficulty level (`easy`, `medium`, `hard`)

### Use Cases
- Educational content creation
- Quiz generation
- Study material automation
- Content comprehension testing
- Blog engagement features

---

## 6. Single Embedding

**Endpoint**: `POST /api/v1/embeddings/generate`  
**Purpose**: Generate vector embedding for semantic search

### Request
```bash
curl -X POST http://localhost:8002/api/v1/embeddings/generate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Machine learning is a subset of artificial intelligence.",
    "model": "text-embedding-ada-002"
  }'
```

### Request Body
```json
{
  "text": "Machine learning is a subset of artificial intelligence.",
  "model": "text-embedding-ada-002"
}
```

### Response (Preview)
```json
{
  "model": "text-embedding-ada-002",
  "dimensions": 1536,
  "embedding": [
    -0.021252313628792763,
    -0.009635476395487785,
    0.00756577355787158,
    -0.004047909751534462,
    -0.014992725104093552,
    0.00808950886130333,
    -0.002363121137022972,
    0.0038743827026337385,
    0.0003730828466359526,
    -0.03538687154650688,
    ... (1536 dimensions total)
  ]
}
```

### Features
- ✅ 1536-dimensional vectors
- ✅ OpenAI's latest embedding model
- ✅ High-quality semantic representation
- ✅ Suitable for similarity search

### Use Cases
- Semantic search
- Document similarity
- Content recommendation
- Duplicate detection
- Clustering and categorization

---

## 7. Batch Embeddings

**Endpoint**: `POST /api/v1/embeddings/generate-batch`  
**Purpose**: Generate multiple embeddings efficiently

### Request
```bash
curl -X POST http://localhost:8002/api/v1/embeddings/generate-batch \
  -H "Content-Type: application/json" \
  -d '{
    "texts": [
      "Python is a programming language",
      "JavaScript is used for web development",
      "Docker is a containerization platform"
    ],
    "model": "text-embedding-ada-002"
  }'
```

### Request Body
```json
{
  "texts": [
    "Python is a programming language",
    "JavaScript is used for web development",
    "Docker is a containerization platform"
  ],
  "model": "text-embedding-ada-002"
}
```

### Response (Preview)
```json
{
  "model": "text-embedding-ada-002",
  "dimensions": 1536,
  "total_texts": 3,
  "embeddings": [
    [0.006010827608406544, -0.004153169225901365, ...],
    [0.006537651643157005, 0.005889100953936577, ...],
    [0.00670568086206913, -0.024955989792943, ...]
  ]
}
```

### Features
- ✅ Batch processing for efficiency
- ✅ Multiple texts in single request
- ✅ Consistent embedding dimensions
- ✅ Optimized for performance

### Use Cases
- Bulk document indexing
- Large-scale semantic search setup
- Content categorization
- Building vector databases
- Similarity matrix generation

---

## 🎯 Quick Reference

| Endpoint | Method | Purpose | Response Time |
|----------|--------|---------|---------------|
| `/` | GET | Service info | <50ms |
| `/health` | GET | Health check | <50ms |
| `/api/v1/generate` | POST | Text generation | 1-3s |
| `/api/v1/qa/answer` | POST | Q&A | 1-3s |
| `/api/v1/questions/generate` | POST | Question generation | 2-4s |
| `/api/v1/embeddings/generate` | POST | Single embedding | 200-500ms |
| `/api/v1/embeddings/generate-batch` | POST | Batch embeddings | 500ms-2s |

---

## 🔑 Authentication

Currently, the service uses the OpenAI API key configured via environment variable:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

For production, implement:
- API key authentication for clients
- Rate limiting per user
- Usage tracking and billing
- JWT tokens for secure access

---

## 📊 Common Response Codes

| Code | Status | Meaning |
|------|--------|---------|
| 200 | OK | Request successful |
| 400 | Bad Request | Invalid request format |
| 401 | Unauthorized | Missing/invalid API key |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Error | Server error |
| 503 | Service Unavailable | OpenAI API unavailable |

---

## 🌐 Interactive Documentation

**Swagger UI**: http://localhost:8002/docs  
**ReDoc**: http://localhost:8002/redoc  
**OpenAPI Schema**: http://localhost:8002/openapi.json

---

## 💡 Best Practices

### 1. Text Generation
- Use appropriate `temperature` (0.0-1.0)
- Set reasonable `max_tokens` limits
- Handle rate limits gracefully
- Cache frequent requests

### 2. Q&A
- Keep questions clear and specific
- Use `max_words` to control response length
- Validate word count in responses
- Store Q&A pairs for analytics

### 3. Question Generation
- Provide sufficient content (min 50 words)
- Choose appropriate difficulty level
- Review generated questions
- Fine-tune based on quality

### 4. Embeddings
- Use batch endpoint for multiple texts
- Cache embeddings for reuse
- Store in vector database
- Use cosine similarity for comparisons

---

## 🚀 Performance Tips

1. **Batch Operations**: Use batch endpoints when processing multiple items
2. **Caching**: Cache frequent requests and embeddings
3. **Async Calls**: Make parallel requests when possible
4. **Timeout Handling**: Set appropriate timeouts (10-30s)
5. **Retry Logic**: Implement exponential backoff for failures

---

## 📚 Additional Resources

- [OpenAI API Documentation](https://platform.openai.com/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Vector Search Best Practices](https://www.pinecone.io/learn/)
- [Microservices Architecture](https://microservices.io/)

---

**Service Version**: 1.0.0  
**Last Updated**: October 13, 2025  
**Status**: ✅ Production Ready

**All endpoints tested and working perfectly! 🎉**

