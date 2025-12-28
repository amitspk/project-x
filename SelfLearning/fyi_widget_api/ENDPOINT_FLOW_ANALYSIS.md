# End-to-End Flow Analysis: Blog Processing Endpoint

## Endpoint: `POST /api/v1/jobs/process` (Blog Processing)

This document traces the complete flow from the router endpoint through service and repository layers, identifying which logic belongs in which layer.

---

## Flow Overview

```
Router (blogs_router.py)
  ↓
Service (BlogService)
  ↓
Repositories (JobRepository, PublisherRepository)
  ↓
Database (MongoDB, PostgreSQL)
```

---

## Layer-by-Layer Breakdown

### 1. **ROUTER LAYER** (`api/routers/blogs_router.py`)

**Endpoint:** `POST /api/v1/jobs/process`

**Responsibilities:**
- ✅ **HTTP Request/Response handling** - Receives HTTP request, returns HTTP response
- ✅ **Request validation** - FastAPI dependency injection (publisher auth, deps)
- ✅ **Response formatting** - Wraps service response in standardized API format
- ✅ **Error handling** - Catches exceptions, converts to HTTP responses
- ✅ **Request ID tracking** - Extracts/generates request_id from middleware
- ✅ **Logging** - Logs at API boundary level

**Code Location:** Lines 30-105

```python
async def enqueue_blog_processing(
    http_request: Request,
    request: JobCreateRequest,
    publisher: Publisher = Depends(get_current_publisher),  # Auth handled by dependency
    job_repo: JobRepository = Depends(get_job_repository),
    publisher_repo: PublisherRepository = Depends(get_publisher_repo),
) -> Dict[str, Any]:
    # Router logic:
    request_id = getattr(http_request.state, 'request_id', None) or generate_request_id()
    
    # Domain validation (could be in service, but fine here)
    await validate_blog_url_domain(request.blog_url, publisher)
    
    # Delegate to service
    job_service = BlogService(job_repo=job_repo, publisher_repo=publisher_repo)
    result_data, status_code, message = await job_service.enqueue_blog_processing(...)
    
    # Format HTTP response
    return success_response(result=result_data, message=message, ...)
```

**Key Logic:**
- Extract request_id
- **Domain validation** - `validate_blog_url_domain()` (business rule)
- Instantiate service with injected dependencies
- Call service method
- Format standardized HTTP response
- Handle HTTP exceptions and convert to responses

---

### 2. **SERVICE LAYER** (`api/services/blog_service.py`)

**Class:** `BlogService.enqueue_blog_processing()`

**Responsibilities:**
- ✅ **Business logic orchestration** - Coordinates multiple operations
- ✅ **Business rules enforcement** - Daily limits, existing blog checks
- ✅ **Transaction management** - Slot reservation/release (rollback on error)
- ✅ **Data transformation** - Converts between models and repository formats
- ✅ **Cross-repository coordination** - Uses both JobRepository and PublisherRepository

**Code Location:** Lines 29-128

```python
async def enqueue_blog_processing(
    self, *, blog_url: str, publisher: Publisher, request_id: str
) -> Tuple[Dict, int, str]:
    # SERVICE LAYER LOGIC:
    
    # 1. URL normalization (utility, but called from service)
    normalized_url = normalize_url(blog_url)
    
    # 2. Daily blog limit check (BUSINESS RULE - SERVICE LAYER)
    if publisher.config.daily_blog_limit:
        today_start = datetime.utcnow().replace(...)
        jobs_today = await self.job_repo.collection.count_documents({...})
        if jobs_today >= publisher.config.daily_blog_limit:
            raise HTTPException(status_code=429, ...)
    
    # 3. Existing blog check (BUSINESS LOGIC - SERVICE LAYER)
    blogs_collection = self.job_repo.database["raw_blog_content"]
    existing_blog = await blogs_collection.find_one({"url": normalized_url})
    if existing_blog:
        existing_job = await self.job_repo.collection.find_one({...})
        if existing_job:
            # Return existing job (BUSINESS LOGIC)
            return JobStatusResponse(...).model_dump(), 200, "..."
    
    # 4. Whitelist enforcement (BUSINESS RULE - SERVICE LAYER)
    PublisherService.ensure_url_whitelisted(normalized_url, publisher)
    
    # 5. Slot reservation with rollback (TRANSACTION MANAGEMENT - SERVICE LAYER)
    slot_reserved = False
    try:
        if self.publisher_repo:
            await self.publisher_repo.reserve_blog_slot(publisher.id)  # REPOSITORY
            slot_reserved = True
        
        job_id, is_new_job = await self.job_repo.create_job(...)  # REPOSITORY
    except UsageLimitExceededError:
        raise HTTPException(...)
    except Exception:
        # Rollback: release slot on error (SERVICE LAYER responsibility)
        if slot_reserved and self.publisher_repo:
            await self.publisher_repo.release_blog_slot(publisher.id, processed=False)
        raise
    
    # 6. Build response (DATA TRANSFORMATION - SERVICE LAYER)
    job_dict = await self.job_repo.get_job_by_id(job_id)
    job_response = JobStatusResponse(...)
    return job_response.model_dump(), 202, "..."
```

**Key Logic by Category:**

#### Business Rules (Service Layer):
- ✅ Daily blog limit enforcement
- ✅ Existing blog/job check (prevent duplicates)
- ✅ URL whitelist enforcement
- ✅ Slot reservation limits (via repository, but coordinated here)

#### Transaction Management (Service Layer):
- ✅ Reserve slot before creating job
- ✅ Rollback slot reservation on error
- ✅ Error handling with cleanup

#### Data Transformation (Service Layer):
- ✅ Convert job dict to JobStatusResponse model
- ✅ Format response for API layer

#### Cross-Repository Coordination (Service Layer):
- ✅ Uses both `job_repo` and `publisher_repo`
- ✅ Coordinates operations across repositories

---

### 3. **REPOSITORY LAYER**

#### 3a. **JobRepository** (`api/repositories/job_repository.py`)

**Responsibilities:**
- ✅ **Database operations** - MongoDB CRUD operations
- ✅ **Query logic** - Database queries and filters
- ✅ **Data persistence** - Insert, find, update operations
- ❌ **NO business logic** - Pure data access

**Code Location:** Lines 36-84 (`create_job` method)

```python
async def create_job(
    self, blog_url: str, publisher_id: Optional[str], config: Optional[dict]
) -> tuple[str, bool]:
    # REPOSITORY LAYER LOGIC:
    
    # 1. Check for existing job (DATA ACCESS - REPOSITORY)
    existing = await self.collection.find_one({
        "blog_url": blog_url,
        "status": {"$in": [JobStatus.QUEUED.value, JobStatus.PROCESSING.value]}
    })
    if existing:
        return existing.get("job_id"), False
    
    # 2. Create new job document (DATA PERSISTENCE - REPOSITORY)
    job_id = str(uuid.uuid4())
    job_dict = {
        "job_id": job_id,
        "blog_url": blog_url,
        "publisher_id": publisher_id,
        "config": config or {},
        "status": JobStatus.QUEUED.value,
        "failure_count": 0,
        "max_retries": 3,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    await self.collection.insert_one(job_dict)
    return job_id, True
```

**Key Logic:**
- ✅ Duplicate job prevention (simple data check - no business logic)
- ✅ Job document creation
- ✅ MongoDB insert operation
- ❌ **NO business rules** (daily limits, whitelisting, etc. are in service)

**Note:** The duplicate check here is **technical** (prevent duplicate QUEUED/PROCESSING jobs), not business logic (that's in service layer).

---

#### 3b. **PublisherRepository** (`api/repositories/publisher_repository.py`)

**Responsibilities:**
- ✅ **Database operations** - PostgreSQL CRUD operations
- ✅ **Atomic operations** - Slot reservation with row locking
- ✅ **Query logic** - SQL queries
- ❌ **NO business logic** - Pure data access (but ensures atomicity)

**Code Location:** Lines 444-481 (`reserve_blog_slot`)

```python
async def reserve_blog_slot(self, publisher_id: str) -> None:
    """Reserve a blog processing slot for a publisher (atomic)."""
    async with self.async_session_factory() as session:
        # REPOSITORY LAYER LOGIC:
        
        # 1. Atomic lock + fetch (DATA ACCESS - REPOSITORY)
        result = await session.execute(
            select(PublisherTable)
            .where(PublisherTable.id == publisher_id)
            .with_for_update()  # Row-level lock for atomicity
        )
        db_publisher = result.scalar_one_or_none()
        
        # 2. Check limit (TECHNICAL CHECK - ensures atomicity)
        # Note: The business rule "what is the limit" is in service/config
        # This just enforces it atomically
        config = db_publisher.config or {}
        limit = config.get("max_total_blogs")
        if not limit:
            return
        
        processed = db_publisher.total_blogs_processed or 0
        reserved = db_publisher.blog_slots_reserved or 0
        
        # 3. Atomic check + update (DATA ACCESS - REPOSITORY)
        if processed + reserved >= limit:
            raise UsageLimitExceededError(...)
        
        db_publisher.blog_slots_reserved = reserved + 1
        await session.commit()
```

**Key Logic:**
- ✅ Atomic slot reservation (row-level locking)
- ✅ Thread-safe counter increment
- ✅ Limit enforcement (technical - ensures atomicity, not business rule)
- ❌ **NO business rules** (what the limit should be is in config/service)

**Note:** The limit check here is **technical** (atomic enforcement), not business logic. The business rule "what is the limit" is defined in publisher config (service layer concern).

---

## Summary: Logic Distribution

| Logic Type | Layer | Example |
|------------|-------|---------|
| **HTTP Request/Response** | Router | Request parsing, response formatting |
| **Authentication** | Router | Dependency injection (`get_current_publisher`) |
| **Business Rules** | Service | Daily limits, whitelisting, existing blog checks |
| **Transaction Management** | Service | Slot reservation rollback, error cleanup |
| **Cross-Repository Coordination** | Service | Using both JobRepository and PublisherRepository |
| **Data Transformation** | Service | Converting dicts to models, building responses |
| **Database Operations** | Repository | MongoDB inserts, PostgreSQL updates |
| **Atomic Operations** | Repository | Row locking, atomic increments |
| **Query Logic** | Repository | MongoDB queries, SQL queries |

---

## Key Principles Observed

1. **Router Layer**: HTTP concerns only - request/response, auth, error formatting
2. **Service Layer**: Business logic, rules, orchestration, transactions
3. **Repository Layer**: Pure data access - no business logic, only technical operations

---

## Potential Issues / Improvements

1. **Service Layer accessing collection directly**: 
   - `self.job_repo.collection.count_documents(...)` - Should be a repository method
   - `blogs_collection = self.job_repo.database["raw_blog_content"]` - Should use QuestionRepository

2. **Domain validation in router vs service**:
   - Currently in router via `validate_blog_url_domain()`
   - Could move to service for consistency, but acceptable at router level

