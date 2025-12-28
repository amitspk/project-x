# Eliminate Shared Library - Complete Refactoring Plan

## Principle
> "Shared libraries are for multiple external clients. Here we have internal services (API and Worker) that should own their dependencies independently."

**Goal**: Completely eliminate `fyi_widget_shared_library` and move everything to respective services.

---

## Current Usage Analysis

### API Service Uses

**Repositories**:
- `JobRepository` - Create/read job status
- `PostgresPublisherRepository` - CRUD operations
- `DatabaseManager` - MongoDB connection

**Services**:
- `StorageService` - Read questions (`get_questions_by_url`), read summaries, search (`search_similar_blogs`)
- `LLMService` - Q&A endpoint (`answer_question`)

**Models**:
- Job models (create/status)
- Publisher models (full entity)

**Utils**:
- `url_utils` (normalize_url, extract_domain)
- `response_utils` (API-only)

---

### Worker Service Uses

**Repositories**:
- `JobRepository` - Read/update jobs
- `PostgresPublisherRepository` - Read config
- `DatabaseManager` - MongoDB connection

**Services**:
- `StorageService` - Save/read blog content, summaries, questions (full CRUD)
- `CrawlerService` - Crawl blogs
- `LLMService` - Generate summaries, questions, embeddings
- `llm_providers/` - All provider implementations
- `llm_prompts.py` - Prompt templates

**Models**:
- Job models (processing)
- Publisher models (config only)
- Schema models (CrawledContent, LLMGenerationResult, EmbeddingResult)

**Utils**:
- `url_utils` (extract_domain, normalize_url)

---

## Migration Strategy

### Approach: Each Service Gets Own Copy

Since we're eliminating shared library to avoid coupling, each service should have its own implementations. This enables:
- Independent evolution
- No deployment coordination
- Better testing isolation

---

## Detailed Migration Plan

### Phase 1: Move Repositories to Both Services (WITH Business Logic Names)

#### 1.1 DatabaseManager → Both Services
- `fyi_widget_api/api/core/database.py`
- `fyi_widget_worker_service/core/database.py`
- Simple MongoDB connection manager (small, acceptable duplication)
- **Keep name as-is** (infrastructure component)

#### 1.2 JobRepository → Both Services  
- `fyi_widget_api/api/repositories/job_repository.py` (API's view)
- `fyi_widget_worker_service/repositories/job_repository.py` (Worker's view)
- Each uses its own models
- Same database schema, different model interfaces
- **Keep name as-is** (already domain-focused)

#### 1.3 PostgresPublisherRepository → PublisherRepository (Both Services)
- `fyi_widget_api/api/repositories/publisher_repository.py` (API's view)
- `fyi_widget_worker_service/repositories/publisher_repository.py` (Worker's view)
- **RENAME**: `PostgresPublisherRepository` → `PublisherRepository`
- Each uses its own models
- Same database schema, different model interfaces
- Postgres implementation detail hidden in class

---

### Phase 2: Move Services (WITH Business Logic Names)

#### 2.1 StorageService → BlogContentRepository (Worker Service)
- `fyi_widget_worker_service/services/blog_content_repository.py`
- **RENAME**: `StorageService` → `BlogContentRepository`
- Worker is primary consumer (saves/reads everything)
- **API Service Decision**: 
  - Option A: Create minimal read-only wrapper in API (recommended)
  - Option B: API imports from Worker (acceptable internal dependency)
  - **Recommendation**: Option A (API creates minimal `QuestionRepository` for reads only)

#### 2.2 CrawlerService → BlogCrawler (Worker Service)
- `fyi_widget_worker_service/services/blog_crawler.py`
- **RENAME**: `CrawlerService` → `BlogCrawler`
- Only used by Worker

#### 2.3 LLMService → LLMContentGenerator (Worker Service)
- `fyi_widget_worker_service/services/llm_content_generator.py`
- `fyi_widget_worker_service/services/llm_providers/` (keep as-is - implementation detail)
- `fyi_widget_worker_service/services/llm_prompts.py` (keep as-is)
- **RENAME**: `LLMService` → `LLMContentGenerator`
- **API Service Decision**:
  - Option A: API imports from Worker (recommended - Worker owns LLM logic)
  - Option B: API creates minimal wrapper
  - **Recommendation**: Option A (internal dependency is acceptable, Worker owns LLM)

---

### Phase 3: Move Models (Already Planned)

#### 3.1 Job Models → Both Services
- `fyi_widget_api/api/models/job_models.py`
- `fyi_widget_worker_service/models/job_models.py`

#### 3.2 Publisher Models → Both Services
- `fyi_widget_api/api/models/publisher_models.py` (full entity)
- `fyi_widget_worker_service/models/publisher_models.py` (config only)

#### 3.3 Schema Models → Worker Service
- `fyi_widget_worker_service/models/schema_models.py`
- Used primarily by Worker services

---

### Phase 4: Move Utils

#### 4.1 url_utils.py → Both Services
- `fyi_widget_api/api/utils/url_utils.py`
- `fyi_widget_worker_service/utils/url_utils.py`
- Simple utility functions (acceptable duplication)

#### 4.2 response_utils.py → API Service Only
- `fyi_widget_api/api/utils/response_utils.py`
- Already identified as API-only

---

## Final Directory Structure

### API Service
```
fyi_widget_api/
├── api/
│   ├── core/
│   │   ├── database.py              # DatabaseManager
│   │   ├── metrics.py
│   │   └── middleware.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── job_repository.py       # API's view
│   │   └── publisher_repository.py # API's view (renamed from PostgresPublisherRepository)
│   ├── services/
│   │   ├── question_repository.py  # Minimal read-only wrapper (NEW, domain-focused)
│   │   ├── question_service.py
│   │   ├── job_service.py
│   │   └── publisher_service.py
│   ├── models/
│   │   ├── job_models.py
│   │   ├── publisher_models.py
│   │   ├── response_models.py
│   │   └── swagger_models.py
│   ├── routers/
│   │   └── ...
│   └── utils/
│       ├── url_utils.py
│       └── response_utils.py
└── config/
    └── config.py
```

### Worker Service
```
fyi_widget_worker_service/
├── core/
│   ├── database.py                  # DatabaseManager
│   ├── config.py
│   ├── metrics.py
│   └── metrics_server.py
├── repositories/
│   ├── __init__.py
│   ├── job_repository.py           # Worker's view
│   └── publisher_repository.py     # Worker's view (renamed from PostgresPublisherRepository)
├── services/
│   ├── blog_content_repository.py  # Full repository (renamed from StorageService)
│   ├── blog_crawler.py             # Renamed from CrawlerService
│   ├── llm_content_generator.py    # Renamed from LLMService
│   ├── llm_providers/
│   │   ├── base.py
│   │   ├── openai_provider.py
│   │   ├── gemini_provider.py
│   │   ├── anthropic_provider.py
│   │   ├── factory.py
│   │   └── model_config.py
│   ├── llm_prompts.py
│   ├── blog_processing_service.py
│   ├── blog_processing_orchestrator.py
│   ├── content_retrieval_service.py
│   ├── threshold_service.py
│   └── llm_generation_service.py
├── models/
│   ├── job_models.py
│   ├── publisher_models.py
│   └── schema_models.py
└── utils/
    └── url_utils.py
```

---

## Phase 5: Rename to Business Logic Names (Domain-Driven Design)

### Principle
> "Repositories and services should be named after business concepts, not technical implementation details."

### Current Technical Names → Business Logic Names

#### Repositories

1. **`PostgresPublisherRepository`** → **`PublisherRepository`**
   - Technical detail (Postgres) removed
   - Business concept (Publisher) kept
   - Implementation detail hidden in the class itself

2. **`JobRepository`** → **`ProcessingJobRepository`** or keep as `JobRepository`
   - Current name is acceptable (domain-focused)
   - Could be more specific: `ProcessingJobRepository`
   - Decision: Keep `JobRepository` (Job is clear business concept)

3. **`DatabaseManager`** → **`DatabaseConnection`** or keep as-is
   - This is infrastructure, current name is acceptable
   - Decision: Keep `DatabaseManager` (it's infrastructure, not domain logic)

#### Services

1. **`StorageService`** → **`ContentRepository`** or **`BlogContentRepository`**
   - Current name is technical (Storage = implementation detail)
   - Business concept: It manages blog content, questions, summaries
   - Options:
     - `BlogContentRepository` - Clear domain focus
     - `ContentRepository` - Simpler, but less specific
     - Split into multiple repositories:
       - `BlogRepository` (blogs)
       - `QuestionRepository` (questions)  
       - `SummaryRepository` (summaries)
   - **Recommendation**: `BlogContentRepository` (single service handling all content types is acceptable)

2. **`CrawlerService`** → **`BlogCrawler`** or **`ContentFetcher`**
   - Current name is technical (Crawler = implementation detail)
   - Business concept: Fetches blog content from URLs
   - Options:
     - `BlogCrawler` - Domain-focused
     - `ContentFetcher` - More generic
     - `BlogContentFetcher` - Most specific
   - **Recommendation**: `BlogCrawler` (clear, domain-focused)

3. **`LLMService`** → **`ContentGenerator`** or **`LLMContentGenerator`**
   - Current name is technical (LLM = implementation detail)
   - Business concept: Generates content (summaries, questions, answers)
   - Options:
     - `ContentGenerator` - Generic, domain-focused
     - `LLMContentGenerator` - More specific (but still mentions LLM)
     - `AIContentGenerator` - Alternative
   - **Recommendation**: `LLMContentGenerator` (acceptable - LLM is the business capability we provide, not just implementation)

### Renaming Strategy

#### Step 5.1: Rename Repositories
- `PostgresPublisherRepository` → `PublisherRepository`
- Update all imports and usages
- Update class names

#### Step 5.2: Rename Services
- `StorageService` → `BlogContentRepository`
- `CrawlerService` → `BlogCrawler`
- `LLMService` → `LLMContentGenerator`
- Update all imports and usages
- Update class names

#### Step 5.3: Update All References
- Update imports in both services
- Update dependency injections
- Update variable names
- Update documentation

---

## Implementation Steps

### Step 1: Create Directory Structures
```bash
# API Service
mkdir -p fyi_widget_api/api/repositories
mkdir -p fyi_widget_api/api/utils

# Worker Service  
mkdir -p fyi_widget_worker_service/repositories
mkdir -p fyi_widget_worker_service/models
mkdir -p fyi_widget_worker_service/utils
```

### Step 2: Move Repositories (Phase 1) + Rename
1. Copy `DatabaseManager` to both services (keep name)
2. Copy `JobRepository` to both services (keep name, adapt to service models)
3. Copy `PostgresPublisherRepository` to both services
   - **RENAME**: `PostgresPublisherRepository` → `PublisherRepository`
   - Adapt to service models
4. Update imports and class references in both services

### Step 3: Move Services (Phase 2) + Rename
1. Move services to Worker and rename:
   - `StorageService` → `BlogContentRepository`
   - `CrawlerService` → `BlogCrawler`
   - `LLMService` → `LLMContentGenerator`
2. Create minimal `QuestionRepository` in API (read-only wrapper, domain-focused name)
3. API imports `LLMContentGenerator` from Worker (acceptable internal dependency)
4. Update all imports and class references

### Step 4: Move Models (Phase 3)
1. Move job models to both services
2. Move publisher models to both services  
3. Move schema models to Worker
4. Update repository implementations

### Step 5: Move Utils (Phase 4)
1. Copy `url_utils.py` to both services
2. Move `response_utils.py` to API service
3. Update imports

### Step 6: Create API's Minimal Content Repository (WITH Business Logic Name)

API only needs read operations:
```python
# fyi_widget_api/api/services/question_repository.py
class QuestionRepository:
    """Minimal read-only content repository for API service."""
    
    def __init__(self, database: AsyncIOMotorDatabase):
        self.database = database
        self.questions_collection = database["processed_questions"]
        self.summaries_collection = database["blog_summaries"]
        self.blogs_collection = database["raw_blog_content"]
    
    async def get_questions_by_url(self, url: str, limit: Optional[int] = None):
        # Minimal implementation for API needs
        ...
    
    async def get_summary_by_url(self, url: str):
        # Minimal implementation
        ...
    
    async def search_similar_blogs(self, embedding, limit, publisher_domain):
        # Minimal implementation
        ...
```

**RENAME**: `QuestionStorageService` → `QuestionRepository` (domain-focused name)

### Step 7: Update All Imports
- Update all imports across both services
- Remove `sys.path.append` hacks
- Test each service independently

### Step 8: Delete Shared Library
- Remove `fyi_widget_shared_library/` directory
- Update documentation
- Update deployment configs if needed

---

## Key Decisions

### 1. Content Repository in API
**Decision**: Create minimal `QuestionRepository` wrapper in API  
**Reason**: API only needs read operations, Worker owns full `BlogContentRepository`

### 2. LLM Content Generator in API
**Decision**: API imports `LLMContentGenerator` from Worker service  
**Reason**: Internal dependency is acceptable, Worker owns LLM logic

### 3. Repository Duplication
**Decision**: Acceptable - each service has its own view  
**Reason**: Repositories are thin wrappers, enables independent evolution

### 4. Utility Duplication
**Decision**: Acceptable for simple utilities  
**Reason**: Small code, independence is worth the duplication

### 5. Naming Convention
**Decision**: Use business logic names, not technical implementation names  
**Renames**:
- `PostgresPublisherRepository` → `PublisherRepository`
- `StorageService` → `BlogContentRepository`
- `CrawlerService` → `BlogCrawler`
- `LLMService` → `LLMContentGenerator`
- `QuestionStorageService` → `QuestionRepository`

---

## Benefits

✅ **No Shared Library**: Eliminates tight coupling  
✅ **Independent Evolution**: Services can change independently  
✅ **Clear Ownership**: Each service owns its dependencies  
✅ **Better Testing**: Services testable in isolation  
✅ **Microservices Best Practice**: Services are independently deployable  

---

## Migration Timeline

- **Phase 1** (Repositories + Rename): 4-5 hours
- **Phase 2** (Services + Rename): 5-6 hours
- **Phase 3** (Models): 2-3 hours
- **Phase 4** (Utils): 1 hour
- **Phase 5** (Naming - integrated into phases 1-2): Included above
- **Step 6** (API Content Repository): 2 hours
- **Testing & Cleanup**: 3-4 hours

**Total**: ~17-21 hours of focused work

---

## Execution Order

1. ✅ Create directory structures
2. ✅ Move utils (simplest)
3. ✅ Move models (already partially planned)
4. ✅ Move repositories + rename (foundation)
   - Rename `PostgresPublisherRepository` → `PublisherRepository`
5. ✅ Move services + rename (depends on repositories)
   - Rename `StorageService` → `BlogContentRepository`
   - Rename `CrawlerService` → `BlogCrawler`
   - Rename `LLMService` → `LLMContentGenerator`
6. ✅ Create API's `QuestionRepository` (domain-focused name)
7. ✅ Update all imports and references
8. ✅ Delete shared library

## Summary of Renames

| Current Name | New Name | Reason |
|-------------|----------|--------|
| `PostgresPublisherRepository` | `PublisherRepository` | Remove technical detail (Postgres) |
| `StorageService` | `BlogContentRepository` | Domain-focused (blog content), repository pattern |
| `CrawlerService` | `BlogCrawler` | Domain-focused (blog crawling) |
| `LLMService` | `LLMContentGenerator` | Business capability (content generation) |
| `QuestionStorageService` (planned) | `QuestionRepository` | Domain-focused, repository pattern |
