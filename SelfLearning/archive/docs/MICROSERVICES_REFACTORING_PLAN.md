# 🏗️ Microservices Architecture Refactoring Plan

**Date**: October 13, 2025  
**Goal**: Transform monolithic blog_manager into independent microservices

---

## 📊 Current Architecture (Monolithic)

```
┌─────────────────────────────────────────┐
│        Blog Manager (Single Process)    │
├─────────────────────────────────────────┤
│  • FastAPI API                          │
│  • Imports llm_service as module        │
│  • Imports web_crawler as module        │
│  • Imports vector_db as module          │
│  • All services in-process              │
│  • Single deployment                    │
│  • Shared database connection           │
└─────────────────────────────────────────┘
```

**Problems:**
- ❌ Single point of failure
- ❌ Cannot scale services independently
- ❌ Tight coupling
- ❌ Deployment requires full restart
- ❌ Resource contention
- ❌ Difficult to maintain

---

## 🎯 Target Architecture (Microservices)

```
┌──────────────────┐
│   API Gateway    │ ← Client Entry Point
│  (blog_manager)  │
└────────┬─────────┘
         │
    ┌────┴────────────────────────────────┐
    │                                     │
┌───▼──────────┐  ┌───────────┐  ┌──────▼──────┐
│  LLM Service │  │ Crawler   │  │   Vector    │
│  (FastAPI)   │  │ Service   │  │   Service   │
└──────────────┘  └───────────┘  └─────────────┘
    │                  │               │
┌───▼──────────┐  ┌───▼───────┐  ┌───▼────────┐
│  MongoDB     │  │  MongoDB  │  │  ChromaDB  │
│ (LLM data)   │  │ (crawled) │  │ (vectors)  │
└──────────────┘  └───────────┘  └────────────┘
```

---

## 🏢 Service Breakdown

### **1. API Gateway Service** (blog_manager)
**Port**: 8001  
**Responsibility**: Route requests, aggregate responses  
**Contains**:
- Main FastAPI app
- Request routing
- Response aggregation
- Authentication/Authorization
- Rate limiting
- Circuit breakers for downstream services

**Endpoints**:
- `GET /api/v1/blogs/by-url` → Routes to Question Service
- `POST /api/v1/qa/ask` → Routes to LLM Service
- `POST /api/v1/similar/blogs` → Routes to Vector Service
- `POST /api/v1/crawl` → Routes to Crawler Service

---

### **2. LLM Service** (Independent)
**Port**: 8002  
**Responsibility**: All LLM operations  
**Already Has**: Modular structure in `llm_service/`

**Endpoints**:
- `POST /api/v1/generate` - General text generation
- `POST /api/v1/qa/answer` - Q&A generation
- `POST /api/v1/questions/generate` - Question generation
- `POST /api/v1/summarize` - Content summarization
- `POST /api/v1/embeddings` - Generate embeddings
- `GET /health` - Health check

**Database**: Own MongoDB collection or shared with namespace

---

### **3. Web Crawler Service** (Independent)
**Port**: 8003  
**Responsibility**: Web scraping and content extraction  
**Already Has**: Modular structure in `web_crawler/`

**Endpoints**:
- `POST /api/v1/crawl` - Crawl a URL
- `POST /api/v1/extract` - Extract content
- `GET /api/v1/content/{url_hash}` - Get crawled content
- `GET /health` - Health check

**Database**: MongoDB - `crawled_content` collection

---

### **4. Vector Search Service** (Independent)
**Port**: 8004  
**Responsibility**: Vector storage and similarity search  
**Already Has**: Modular structure in `vector_db/`

**Endpoints**:
- `POST /api/v1/vectors/store` - Store embeddings
- `POST /api/v1/vectors/search` - Similarity search
- `GET /api/v1/vectors/{id}` - Get vector by ID
- `DELETE /api/v1/vectors/{id}` - Delete vector
- `GET /health` - Health check

**Database**: ChromaDB or MongoDB Vector Search

---

### **5. Question Service** (New - Extract from blog_manager)
**Port**: 8005  
**Responsibility**: Question/Answer storage and retrieval  

**Endpoints**:
- `GET /api/v1/questions/by-blog` - Get questions for a blog
- `POST /api/v1/questions` - Store generated questions
- `GET /api/v1/questions/{id}` - Get specific question
- `GET /health` - Health check

**Database**: MongoDB - `blog_questions` collection

---

## 📋 Refactoring Steps

### **Phase 1: Extract LLM Service** (2-3 hours)

**Step 1.1**: Create standalone FastAPI app in `llm_service/`
```bash
llm_service/
├── api/
│   ├── main.py          # FastAPI app
│   └── routers/
│       ├── generation.py
│       ├── qa.py
│       ├── questions.py
│       └── embeddings.py
├── run_server.py        # Standalone runner
└── requirements.txt     # Dependencies
```

**Step 1.2**: Update blog_manager to call LLM Service via HTTP
```python
# Before (in-process)
from llm_service.core.service import LLMService
response = await llm_service.generate(...)

# After (HTTP call)
import httpx
response = await httpx.post(
    "http://llm-service:8002/api/v1/generate",
    json={"prompt": ...}
)
```

**Step 1.3**: Add service discovery/health checks

**Step 1.4**: Test independently

---

### **Phase 2: Extract Web Crawler Service** (2-3 hours)

**Step 2.1**: Create standalone FastAPI app in `web_crawler/`
```bash
web_crawler/
├── api/
│   ├── main.py
│   └── routers/
│       └── crawler.py
├── run_server.py
└── requirements.txt
```

**Step 2.2**: Update blog_manager to call Crawler via HTTP

**Step 2.3**: Test independently

---

### **Phase 3: Extract Vector Service** (2-3 hours)

**Step 3.1**: Create standalone FastAPI app in `vector_db/`

**Step 3.2**: Update blog_manager to call Vector Service via HTTP

**Step 3.3**: Test independently

---

### **Phase 4: Extract Question Service** (3-4 hours)

**Step 4.1**: Create new `question_service/` directory

**Step 4.2**: Move question logic from blog_manager

**Step 4.3**: Create FastAPI app

**Step 4.4**: Update blog_manager to orchestrate

---

### **Phase 5: Add Service Communication** (2-3 hours)

**Step 5.1**: Add HTTP clients with retry logic

**Step 5.2**: Add circuit breakers for each service

**Step 5.3**: Add request/response logging

**Step 5.4**: Add distributed tracing

---

### **Phase 6: Containerization** (2-3 hours)

**Step 6.1**: Create Dockerfile for each service

**Step 6.2**: Create docker-compose.yml

**Step 6.3**: Add service orchestration

---

## 🐳 Docker Compose Setup

```yaml
version: '3.8'

services:
  # API Gateway
  api-gateway:
    build: ./blog_manager
    ports:
      - "8001:8001"
    environment:
      - LLM_SERVICE_URL=http://llm-service:8002
      - CRAWLER_SERVICE_URL=http://crawler-service:8003
      - VECTOR_SERVICE_URL=http://vector-service:8004
      - QUESTION_SERVICE_URL=http://question-service:8005
    depends_on:
      - mongodb
      - llm-service
      - crawler-service
      - vector-service
      - question-service

  # LLM Service
  llm-service:
    build: ./llm_service
    ports:
      - "8002:8002"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - MONGODB_URL=mongodb://mongodb:27017
    depends_on:
      - mongodb

  # Crawler Service
  crawler-service:
    build: ./web_crawler
    ports:
      - "8003:8003"
    environment:
      - MONGODB_URL=mongodb://mongodb:27017
    depends_on:
      - mongodb

  # Vector Service
  vector-service:
    build: ./vector_db
    ports:
      - "8004:8004"
    environment:
      - CHROMADB_HOST=chromadb
      - CHROMADB_PORT=8000
    depends_on:
      - chromadb

  # Question Service
  question-service:
    build: ./question_service
    ports:
      - "8005:8005"
    environment:
      - MONGODB_URL=mongodb://mongodb:27017
    depends_on:
      - mongodb

  # Databases
  mongodb:
    image: mongo:7.0
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data:/data/db

  chromadb:
    image: ghcr.io/chroma-core/chroma:latest
    ports:
      - "8000:8000"
    volumes:
      - chromadb_data:/chroma/chroma

volumes:
  mongodb_data:
  chromadb_data:
```

---

## 🔗 Service Communication

### **HTTP Client with Circuit Breaker**

```python
# blog_manager/core/service_clients.py

from blog_manager.core.resilience import with_circuit_breaker
import httpx

class LLMServiceClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    @with_circuit_breaker('llm_service')
    async def generate_answer(self, question: str) -> dict:
        response = await self.client.post(
            f"{self.base_url}/api/v1/qa/answer",
            json={"question": question}
        )
        response.raise_for_status()
        return response.json()
    
    async def health_check(self) -> dict:
        response = await self.client.get(f"{self.base_url}/health")
        return response.json()
```

---

## 📊 Benefits of Microservices

### **Scalability**
```
High Load on LLM Service?
→ Scale only llm-service: docker-compose up --scale llm-service=5
```

### **Independent Deployment**
```
Update Crawler Logic?
→ Deploy only crawler-service
→ No downtime for other services
```

### **Fault Isolation**
```
LLM Service Down?
→ Circuit breaker prevents cascade
→ Other services continue working
→ Graceful degradation
```

### **Technology Freedom**
```
Want to rewrite Crawler in Go?
→ Replace service, same API contract
→ No changes to other services
```

---

## ⚠️ Challenges & Solutions

### **Challenge 1: Network Latency**
**Problem**: HTTP calls slower than in-process  
**Solution**: 
- Use HTTP/2 or gRPC
- Implement caching
- Batch requests where possible

### **Challenge 2: Distributed Transactions**
**Problem**: Can't use database transactions across services  
**Solution**:
- Use Saga pattern
- Implement compensating transactions
- Event sourcing

### **Challenge 3: Service Discovery**
**Problem**: Services need to find each other  
**Solution**:
- Use Docker DNS (service names)
- Add Consul/Eureka in production
- Environment variables for URLs

### **Challenge 4: Debugging**
**Problem**: Tracing requests across services  
**Solution**:
- Distributed tracing (OpenTelemetry)
- Correlation IDs
- Centralized logging

---

## 🚀 Quick Start (For You)

### **Option 1: Gradual Migration** (Recommended)
Start with one service at a time, keep others in-process.

```bash
# Week 1: Extract LLM Service
# Week 2: Extract Crawler Service
# Week 3: Extract Vector Service
# Week 4: Polish & Production
```

### **Option 2: Big Bang**
Extract all services at once (risky but faster).

### **Option 3: Strangler Pattern**
Run old and new side-by-side, gradually shift traffic.

---

## 📋 My Recommendation

**Start with LLM Service extraction:**

1. **Why LLM First?**
   - Already well-structured
   - Clear boundaries
   - High benefit (independent scaling)
   - Low risk (well-tested)

2. **Estimated Time**: 2-3 hours
3. **Impact**: Can scale LLM independently
4. **Risk**: Low (easy to rollback)

---

## 🎯 Next Steps

**Would you like me to:**

A) Start with LLM Service extraction (recommended)
B) Create a full docker-compose setup first
C) Extract a different service first
D) Show detailed step-by-step for one service

**What would you prefer?**

