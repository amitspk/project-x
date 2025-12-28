# Models Decoupling Analysis

## User's Concern
> "Any models should not be kept in shared library, as any change here impacts everyone using it"

**This is a valid architectural concern about tight coupling and dependency management.**

---

## Current State

### Models in Shared Library

1. **`job_queue.py`**
   - `ProcessingJob`, `JobStatus`, `JobResult`, `JobCreateRequest`, `JobStatusResponse`
   - Used by: API service (creates jobs) + Worker service (processes jobs)
   - Represents: MongoDB job queue documents

2. **`publisher.py`**
   - `Publisher`, `PublisherConfig`, `PublisherStatus`, etc.
   - Used by: API service (CRUD) + Worker service (reads config)
   - Represents: PostgreSQL publisher records

3. **`schemas.py`**
   - `CrawledContent`, `QuestionAnswerPair`, `BlogSummary`, `SimilarBlog`, etc.
   - Used by: Shared services (StorageService, LLMService, CrawlerService)
   - Represents: Internal data structures and MongoDB document structures

---

## The Problem with Shared Models

### Tight Coupling Issues

1. **Breaking Changes**: Any change to a shared model breaks all consumers
   - API service changes → Worker service must update
   - Worker service changes → API service must update
   - Can't evolve services independently

2. **Dependency Hell**: Services can't be versioned independently
   - All services must use the same model version
   - Can't have different model versions for different services

3. **Deployment Coordination**: Changes require coordinated deployments
   - Can't deploy API service changes without updating Worker service
   - Increased risk of production issues

4. **Testing Complexity**: Testing one service requires all model dependencies
   - Can't test services in isolation
   - Mocking becomes more complex

---

## Recommended Architecture: Service-Specific Models

### Principle: Each Service Owns Its Models

**Services should have their own models, even if they work with the same underlying data.**

### Strategy: Separate Models + Shared Schema Definition

1. **Database Schema Definition** (if needed)
   - Define database schemas separately (e.g., in migrations, or minimal shared schema definitions)
   - Services read/write to database using their own models
   - Use ORMs/ODMs that handle the mapping

2. **API Service Models**
   - `fyi_widget_api/api/models/job_models.py` - API's view of jobs
   - `fyi_widget_api/api/models/publisher_models.py` - API's view of publishers
   - `fyi_widget_api/api/models/` - All API-specific models

3. **Worker Service Models**
   - `fyi_widget_worker_service/models/job_models.py` - Worker's view of jobs
   - `fyi_widget_worker_service/models/publisher_models.py` - Worker's view of publishers
   - `fyi_widget_worker_service/models/` - All worker-specific models

4. **Shared Services** (StorageService, LLMService, etc.)
   - Keep their own internal models/schemas
   - Accept raw dictionaries or service-specific DTOs
   - Return raw dictionaries or service-specific DTOs
   - Don't expose shared models

---

## Migration Strategy

### Phase 1: Keep Database Compatibility

- Services can have different models, but they must be compatible with the database schema
- Use serialization/deserialization at the repository layer
- Repositories handle conversion between service models and database documents

### Phase 2: Move Models to Services

1. **Move job models**:
   - `job_queue.py` → Split into:
     - `fyi_widget_api/api/models/job_models.py` (API's view)
     - `fyi_widget_worker_service/models/job_models.py` (Worker's view)

2. **Move publisher models**:
   - `publisher.py` → Split into:
     - `fyi_widget_api/api/models/publisher_models.py` (API's view)
     - `fyi_widget_worker_service/models/publisher_models.py` (Worker's view)

3. **Move schema models**:
   - `schemas.py` → Move to services that use them
   - Or keep minimal schemas in shared services (as internal implementation details)

### Phase 3: Repository Layer Handles Conversion

- Repositories convert between service models and database documents
- Each service uses its own model structure
- Database schema remains stable (or evolves via migrations)

---

## Example: Job Model Separation

### API Service Model
```python
# fyi_widget_api/api/models/job_models.py
class JobCreateRequest(BaseModel):
    """API's view of job creation request."""
    blog_url: str
    # API-specific fields

class JobStatusResponse(BaseModel):
    """API's view of job status."""
    job_id: str
    status: str
    # API-specific fields only
```

### Worker Service Model
```python
# fyi_widget_worker_service/models/job_models.py
class ProcessingJob(BaseModel):
    """Worker's view of a job to process."""
    job_id: str
    blog_url: str
    # Worker-specific fields only
```

### Repository Handles Conversion
```python
# Repository converts between model and database document
async def create_job(job_request: JobCreateRequest) -> str:
    # Convert API model to database document
    doc = {
        "job_id": str(uuid.uuid4()),
        "blog_url": job_request.blog_url,
        "status": "queued",
        # ... database schema fields
    }
    await collection.insert_one(doc)
    return doc["job_id"]

async def get_next_job() -> ProcessingJob:
    # Fetch from database
    doc = await collection.find_one(...)
    # Convert database document to Worker model
    return ProcessingJob(
        job_id=doc["job_id"],
        blog_url=doc["blog_url"],
        # ... map only fields Worker needs
    )
```

---

## Benefits of This Approach

✅ **Independent Evolution**: Services can evolve models independently  
✅ **Loose Coupling**: Changes in one service don't break others  
✅ **Better Testing**: Services can be tested in isolation  
✅ **Clear Ownership**: Each service owns its data models  
✅ **Flexibility**: Services can have different views of the same data  

---

## Considerations

### Database Schema Stability
- Database schema should remain stable
- Use migrations for schema changes
- Services map their models to/from database schema

### Shared Services
- Shared services (StorageService, LLMService) should use minimal, stable interfaces
- Accept/return dictionaries or simple DTOs
- Don't expose complex models

### Communication Between Services
- If services communicate via APIs: API defines the contract
- If services communicate via database: Use stable database schema, services map to their models
- If services communicate via message queue: Define message schemas separately

---

## Recommendation

**Yes, we should move all models out of the shared library** and into their respective services. This is better architecture that:
- Reduces coupling
- Enables independent service evolution
- Improves testability
- Follows microservices best practices

The shared library should contain:
- **Services** (business logic, not models)
- **Utilities** (helper functions)
- **Repository implementations** (database access, which can handle model conversion)
- **Minimal shared interfaces/DTOs** (only if absolutely necessary for service communication)

**Not models that represent domain entities or API contracts.**

