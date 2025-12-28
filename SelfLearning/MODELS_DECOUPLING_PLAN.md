# Models Decoupling Plan

## Goal
Move all models from shared library to their respective services to eliminate tight coupling.

---

## Models to Migrate

### 1. Job Models (`job_queue.py`)

**Current**: `fyi_widget_shared_library/models/job_queue.py`

**Target Locations**:
- **API Service**: `fyi_widget_api/api/models/job_models.py`
  - `JobCreateRequest` (API-specific)
  - `JobStatusResponse` (API-specific)
  
- **Worker Service**: `fyi_widget_worker_service/models/job_models.py`
  - `ProcessingJob` (Worker's view of job)
  - `JobStatus` (enum - keep in both or move to shared enum if truly shared)
  - `JobResult` (Worker's view of result)

**Shared**: `JobStatus` enum could stay in shared if truly used by both, or duplicate in each service

---

### 2. Publisher Models (`publisher.py`)

**Current**: `fyi_widget_shared_library/models/publisher.py`

**Target Locations**:
- **API Service**: `fyi_widget_api/api/models/publisher_models.py`
  - `Publisher` (API's view - full entity for CRUD)
  - `PublisherStatus` (enum)
  - `PublisherConfig` (API's view - full config for CRUD)
  - All request/response models for API endpoints
  
- **Worker Service**: `fyi_widget_worker_service/models/publisher_models.py`
  - `PublisherConfig` (Worker's minimal view - only fields it needs for processing)
  - `PublisherStatus` (enum - if needed)

**Note**: Worker only needs config for processing, not full Publisher entity

---

### 3. Schema Models (`schemas.py`)

**Current**: `fyi_widget_shared_library/models/schemas.py`

**Analysis Needed**: Check which schemas are used where:
- `CrawledContent` - Used by Worker services (ContentRetrievalService, LLMGenerationService)
- `LLMGenerationResult`, `EmbeddingResult` - Used by shared services
- `QuestionAnswerPair`, `BlogSummary`, `SimilarBlog` - Used by StorageService (shared) and API
- `SearchSimilarRequest`, `SearchSimilarResponse` - Used by API only

**Target Strategy**:
- Move API-only schemas to API service
- Keep schemas used by shared services in shared library as internal implementation details
- OR: Move all to services, shared services accept/return dictionaries

---

## Migration Steps

### Step 1: Create Model Directories

```bash
mkdir -p fyi_widget_api/api/models
mkdir -p fyi_widget_worker_service/models
```

### Step 2: Move Job Models

1. Create `fyi_widget_api/api/models/job_models.py`
   - Copy `JobCreateRequest`, `JobStatusResponse`
   - Keep only API-relevant fields
   
2. Create `fyi_widget_worker_service/models/job_models.py`
   - Copy `ProcessingJob`, `JobResult`
   - Keep only Worker-relevant fields
   
3. Decide on `JobStatus` enum:
   - Option A: Duplicate in both services (better independence)
   - Option B: Keep in shared (if truly shared contract)

### Step 3: Update JobRepository

- Repository converts between database documents and service models
- API service's JobRepository returns API models
- Worker service's JobRepository returns Worker models
- Database schema remains stable

### Step 4: Move Publisher Models

1. Create `fyi_widget_api/api/models/publisher_models.py`
   - Full `Publisher` entity
   - Full `PublisherConfig`
   - All API request/response models
   
2. Create `fyi_widget_worker_service/models/publisher_models.py`
   - Minimal `PublisherConfig` (only fields needed for processing)
   
3. Update PostgresPublisherRepository
   - API service's repository returns API models
   - Worker service's repository returns Worker models

### Step 5: Handle Schema Models

1. Analyze usage of each schema
2. Move API-only schemas to API service
3. For shared service schemas:
   - Option A: Keep in shared library as internal implementation
   - Option B: Move to services, shared services use dictionaries

### Step 6: Update All Imports

- Update all API service imports
- Update all Worker service imports
- Update repository implementations

---

## Implementation Order

1. ✅ **Job Models** (simpler, clear separation)
2. ✅ **Publisher Models** (more complex, but clear separation)
3. ✅ **Schema Models** (requires analysis)

---

## Repository Pattern Change

**Before**:
```python
# Repository returns shared model
from fyi_widget_shared_library.models.job_queue import ProcessingJob

async def get_next_job() -> ProcessingJob:
    doc = await collection.find_one(...)
    return ProcessingJob(**doc)
```

**After**:
```python
# Repository converts to service-specific model
from fyi_widget_worker_service.models.job_models import ProcessingJob

async def get_next_job() -> ProcessingJob:
    doc = await collection.find_one(...)
    # Convert database document to Worker model
    return ProcessingJob(
        job_id=doc["job_id"],
        blog_url=doc["blog_url"],
        # ... only fields Worker needs
    )
```

---

## Database Schema Contract

- Database schema remains the source of truth
- Services map their models to/from database schema
- Schema changes require migration
- Services can evolve models independently as long as they map to/from same schema

---

## Benefits

✅ **Independent Evolution**: Services can change models without affecting others  
✅ **Loose Coupling**: Changes don't propagate across service boundaries  
✅ **Better Testing**: Services can be tested in isolation  
✅ **Clear Ownership**: Each service owns its data models  
✅ **Microservices Best Practice**: Services should be independently deployable and evolvable

