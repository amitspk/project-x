# End-to-End Flow Documentation for All Endpoints

This document shows the complete execution flow for each endpoint, step-by-step from HTTP request to response.

---

## Router: `blogs_router.py` (`/api/v1/jobs`)

### Endpoint 1: `POST /api/v1/jobs/process`

**Purpose:** Enqueue a blog URL for asynchronous processing

#### Step-by-Step Flow:

1. **Router Layer** (`blogs_router.py::enqueue_blog_processing`)
   - Receive HTTP POST request with `JobCreateRequest` (contains `blog_url`)
   - Extract `request_id` from middleware state (or generate new one)
   - Dependency injection: Get authenticated `publisher` via `get_current_publisher` (validates X-API-Key header)
   - Dependency injection: Get `job_repo` (JobRepository) and `publisher_repo` (PublisherRepository)
   - Call `validate_blog_url_domain(request.blog_url, publisher)` - **Service Layer** (auth_service)
     - Extract domain from blog_url
     - Check if blog domain matches publisher's domain (exact or subdomain)
     - Raise HTTPException 403 if mismatch
   - Instantiate `BlogService(job_repo, publisher_repo)`
   - Call `blog_service.enqueue_blog_processing(blog_url, publisher, request_id)`

2. **Service Layer** (`blog_service.py::enqueue_blog_processing`)
   - Normalize URL using `normalize_url(blog_url)` utility
   - **Daily Limit Check** (Business Rule):
     - Get `daily_blog_limit` from `publisher.config`
     - If limit exists:
       - Calculate today's start timestamp (00:00:00 UTC)
       - Query MongoDB: `job_repo.collection.count_documents({blog_url regex, status: "completed", completed_at >= today_start})`
       - If count >= limit: Raise HTTPException 429 (Too Many Requests)
   - **Existing Blog Check** (Business Logic):
     - Query MongoDB: `job_repo.database["raw_blog_content"].find_one({url: normalized_url})`
     - If blog exists:
       - Query MongoDB: `job_repo.collection.find_one({blog_url: normalized_url, status: "completed"})`
       - If completed job exists:
         - Build `JobStatusResponse` from existing job dict
         - Return `(job_response.model_dump(), 200, "Blog already processed, returning existing job")`
       - Else: Log warning and continue to create new job
   - **Whitelist Enforcement** (Business Rule):
     - Call `PublisherService.ensure_url_whitelisted(normalized_url, publisher)` - **Service Layer** (publisher_service)
       - Get whitelist from `publisher.config.whitelisted_blog_urls`
       - Check if URL matches whitelist patterns
       - Raise HTTPException 403 if not whitelisted
   - **Slot Reservation** (Transaction Management):
     - Initialize `slot_reserved = False`
     - Try block:
       - If `publisher_repo` exists:
         - Call `publisher_repo.reserve_blog_slot(publisher.id)` - **Repository Layer**
           - Open PostgreSQL session with row-level lock (`with_for_update()`)
           - Fetch publisher record from PostgreSQL
           - Get `max_total_blogs` from config
           - Check: `total_blogs_processed + blog_slots_reserved >= limit`
           - If exceeded: Raise `UsageLimitExceededError`
           - Else: Increment `blog_slots_reserved` atomically
           - Commit transaction
         - Set `slot_reserved = True`
       - Call `job_repo.create_job(normalized_url, publisher.id, config)` - **Repository Layer**
         - Check MongoDB for existing job with same URL and status in [QUEUED, PROCESSING]
         - If exists: Return `(existing_job_id, False)`
         - Else: Generate UUID, create job dict, insert into MongoDB, return `(job_id, True)`
       - Get created job: `job_dict = job_repo.get_job_by_id(job_id)` - **Repository Layer**
         - Query MongoDB: `collection.find_one({job_id: job_id})`
         - Return job dict
       - Build `JobStatusResponse` from job dict
       - Return `(job_response.model_dump(), 202, "Blog processing job enqueued successfully")`
     - Catch `UsageLimitExceededError`:
       - Raise HTTPException 403 with error message
     - Catch Exception:
       - If `slot_reserved`: Call `publisher_repo.release_blog_slot(publisher.id, processed=False)` - **Repository Layer**
         - Atomic PostgreSQL update: Decrement `blog_slots_reserved`
         - Commit transaction
       - Re-raise exception

3. **Router Layer** (return)
   - Receive tuple `(result_data, status_code, message)` from service
   - Format response: `success_response(result=result_data, message=message, status_code=status_code, request_id=request_id)`
   - Return HTTP 202 Accepted with job details

---

### Endpoint 2: `GET /api/v1/jobs/status/{job_id}`

**Purpose:** Get the status of a processing job

#### Step-by-Step Flow:

1. **Router Layer** (`blogs_router.py::get_job_status`)
   - Receive HTTP GET request with `job_id` path parameter
   - Extract `request_id` from middleware state
   - Dependency injection: Verify admin key via `verify_admin_key` dependency
   - Dependency injection: Get `job_repo` (JobRepository)
   - Instantiate `BlogService(job_repo, publisher_repo=None)`
   - Call `blog_service.get_job_status(job_id, request_id)`

2. **Service Layer** (`blog_service.py::get_job_status`)
   - Call `job_repo.get_job_by_id(job_id)` - **Repository Layer**
     - Query MongoDB: `collection.find_one({job_id: job_id})`
     - Return job dict or None
   - If job not found: Raise HTTPException 404
   - Build `JobStatusResponse` from job dict
   - Convert datetime fields to ISO format strings
   - Return result_data dict

3. **Router Layer** (return)
   - Receive result_data from service
   - Format response: `success_response(result=result_data, message="Job status retrieved successfully", ...)`
   - Return HTTP 200 OK with job status

---

### Endpoint 3: `GET /api/v1/jobs/stats`

**Purpose:** Get aggregate statistics about the job queue

#### Step-by-Step Flow:

1. **Router Layer** (`blogs_router.py::get_queue_stats`)
   - Receive HTTP GET request
   - Extract `request_id` from middleware state
   - Dependency injection: Verify admin key via `verify_admin_key` dependency
   - Dependency injection: Get `job_repo` (JobRepository)
   - Instantiate `BlogService(job_repo, publisher_repo=None)`
   - Call `blog_service.get_queue_stats()`

2. **Service Layer** (`blog_service.py::get_queue_stats`)
   - Call `job_repo.get_job_stats()` - **Repository Layer**
     - MongoDB aggregation pipeline: `$group` by `status` field, count documents
     - Return dict: `{status: count}` for each status
   - Calculate total: `sum(stats.values())`
   - Return `{"queue_stats": stats, "total_jobs": total}`

3. **Router Layer** (return)
   - Receive result_data from service
   - Format response: `success_response(result=result_data, message="Queue statistics retrieved successfully", ...)`
   - Return HTTP 200 OK with stats

---

### Endpoint 4: `POST /api/v1/jobs/cancel/{job_id}`

**Purpose:** Cancel a queued job

#### Step-by-Step Flow:

1. **Router Layer** (`blogs_router.py::cancel_job`)
   - Receive HTTP POST request with `job_id` path parameter
   - Extract `request_id` from middleware state
   - Dependency injection: Verify admin key via `verify_admin_key` dependency
   - Dependency injection: Get `job_repo` (JobRepository)
   - Instantiate `BlogService(job_repo, publisher_repo=None)`
   - Call `blog_service.cancel_job(job_id, request_id)`

2. **Service Layer** (`blog_service.py::cancel_job`)
   - Call `job_repo.cancel_job(job_id)` - **Repository Layer**
     - Query MongoDB: `collection.find_one({job_id: job_id, status: "queued"})`
     - If not found or status != "queued": Return False
     - Update MongoDB: `collection.update_one({job_id: job_id}, {$set: {status: "cancelled"}})`
     - Return True if updated, False otherwise
   - If not cancelled: Raise HTTPException 400 ("Job cannot be cancelled...")
   - Return `{"job_id": job_id, "cancelled": True}`

3. **Router Layer** (return)
   - Receive result_data from service
   - Format response: `success_response(result=result_data, message=f"Job {job_id} cancelled successfully", ...)`
   - Return HTTP 200 OK

---

## Router: `questions_router.py` (`/api/v1/questions`)

### Endpoint 1: `GET /api/v1/questions/check-and-load`

**Purpose:** Smart endpoint - check if questions exist, return if ready, or auto-create processing job

#### Step-by-Step Flow:

1. **Router Layer** (`questions_router.py::check_and_load_questions`)
   - Receive HTTP GET request with `blog_url` query parameter
   - Extract `request_id` from middleware state
   - Dependency injection: Get authenticated `publisher` via `get_current_publisher`
   - Dependency injection: Get `question_repo`, `job_repo`, `publisher_repo`
   - Normalize URL: `normalize_url(blog_url)`
   - Call `validate_blog_url_domain(normalized_url, publisher)` - **Service Layer** (auth_service)
   - Instantiate `QuestionService(question_repo, job_repo, publisher_repo)`
   - Call `question_service.check_and_load_questions(normalized_url, publisher, request_id)`

2. **Service Layer** (`question_service.py::check_and_load_questions`)
   - **Step 1: Check if questions exist**
     - Call `question_repo.get_questions_by_url(normalized_url, limit=None)` - **Repository Layer**
       - Query MongoDB: `questions` collection, find questions with matching `blog_url`
       - Return list of question dicts
     - If questions exist:
       - Return `{"processing_status": "ready", "questions": [...], "blog_info": {...}, "job_id": None, "message": "Questions ready"}`
   
   - **Step 2: Check if job exists**
     - Call `job_repo.get_job_by_url(normalized_url)` - **Repository Layer**
       - Query MongoDB: `collection.find_one({blog_url: normalized_url})`
       - Return job dict or None
     - If job exists:
       - Return status based on job.status:
         - "completed": Return questions (Step 1)
         - "processing": Return `{"processing_status": "processing", "job_id": ..., "message": "Processing in progress"}`
         - "failed": Return `{"processing_status": "failed", "job_id": ..., "message": "Previous processing failed"}`
   
   - **Step 3: Create new job** (if no questions and no job)
     - **Slot Reservation**:
       - Try block:
         - Call `publisher_repo.reserve_blog_slot(publisher.id)` - **Repository Layer** (same as blog processing)
         - Set `slot_reserved = True`
         - Call `job_repo.create_job(normalized_url, publisher.id, config)` - **Repository Layer**
         - If job already exists (not new): Release slot
       - Catch exceptions: Release slot on error
     - Return `{"processing_status": "not_started", "job_id": ..., "message": "Processing started..."}`

3. **Router Layer** (return)
   - Receive result_data from service
   - Format response: `success_response(result=result_data, message=result_data.get("message"), ...)`
   - Return HTTP 200 OK with status and questions (if ready)

---

### Endpoint 2: `GET /api/v1/questions/by-url`

**Purpose:** Get all questions for a specific blog URL

#### Step-by-Step Flow:

1. **Router Layer** (`questions_router.py::get_questions_by_url`)
   - Receive HTTP GET request with `blog_url` query parameter
   - Extract `request_id` from middleware state
   - Dependency injection: Get authenticated `publisher` via `get_current_publisher`
   - Dependency injection: Get `question_repo`, `job_repo`, `publisher_repo`
   - Extract domain: `extract_domain(normalized_url)`
   - Call `validate_blog_url_domain(normalized_url, publisher)` - **Service Layer** (auth_service)
   - Instantiate `QuestionService(question_repo, job_repo, publisher_repo)`
   - Call `question_service.get_questions_by_url(normalized_url, publisher, request_id, blog_url)`

2. **Service Layer** (`question_service.py::get_questions_by_url`)
   - Call `question_repo.get_questions_by_url(normalized_url, limit=None)` - **Repository Layer**
     - Query MongoDB: `questions` collection, find questions with matching `blog_url`
     - Sort by `created_at` descending
     - Return list of question dicts
   - If no questions: Raise HTTPException 404
   - Randomize questions list
   - Get blog info: `question_repo.get_blog_by_url(normalized_url)` - **Repository Layer**
     - Query MongoDB: `raw_blog_content` collection, find blog with matching `url`
     - Return blog dict
   - Build response with questions and blog info
   - Return result_data dict

3. **Router Layer** (return)
   - Receive result_data from service
   - Format response: `success_response(result=result_data, message="Questions retrieved successfully", ...)`
   - Return HTTP 200 OK with questions

---

### Endpoint 3: `GET /api/v1/questions/{question_id}`

**Purpose:** Get a specific question by ID

#### Step-by-Step Flow:

1. **Router Layer** (`questions_router.py::get_question_by_id`)
   - Receive HTTP GET request with `question_id` path parameter
   - Extract `request_id` from middleware state
   - Dependency injection: Verify admin key via `verify_admin_key` dependency
   - Dependency injection: Get `question_repo` (QuestionRepository)
   - Call `question_repo.get_question_by_id(question_id)` - **Repository Layer**
     - Query MongoDB: `questions` collection, find question by `_id` (ObjectId)
     - Return question dict or None
   - If not found: Raise HTTPException 404
   - Format response: `success_response(result=question_dict, ...)`
   - Return HTTP 200 OK

---

### Endpoint 4: `DELETE /api/v1/questions/{blog_id}`

**Purpose:** Delete a blog and all its associated questions

#### Step-by-Step Flow:

1. **Router Layer** (`questions_router.py::delete_blog_by_id`)
   - Receive HTTP DELETE request with `blog_id` path parameter
   - Extract `request_id` from middleware state
   - Dependency injection: Verify admin key via `verify_admin_key` dependency
   - Dependency injection: Get `question_repo` (QuestionRepository)
   - Validate blog_id format (ObjectId)
   - Call `question_repo.delete_blog(blog_id)` - **Repository Layer**
     - Query MongoDB to get blog: `raw_blog_content` collection, find by `_id`
     - Get blog URL from blog document
     - Delete all questions: `questions` collection, `delete_many({blog_url: blog_url})`
     - Delete blog: `raw_blog_content` collection, `delete_one({_id: blog_id})`
     - Return deletion counts
   - Format response: `success_response(result={"deleted": True, ...}, ...)`
   - Return HTTP 200 OK

---

## Router: `search_router.py` (`/api/v1/search`)

### Endpoint 1: `POST /api/v1/search/similar`

**Purpose:** Find similar blogs based on a question's embedding

#### Step-by-Step Flow:

1. **Router Layer** (`search_router.py::search_similar_blogs`)
   - Receive HTTP POST request with `SearchSimilarRequest` (contains `question_id` and `limit`)
   - Extract `request_id` from middleware state
   - Dependency injection: Get authenticated `publisher` via `get_current_publisher`
   - Dependency injection: Get `question_repo` (QuestionRepository)
   - Call `question_repo.get_question_by_id(request.question_id)` - **Repository Layer**
     - Query MongoDB: `questions` collection, find question by `_id`
     - Return question dict or None
   - If question not found: Raise HTTPException 404
   - Get question's blog_url from question dict
   - Call `validate_blog_url_domain(question_blog_url, publisher)` - **Service Layer** (auth_service)
   - Extract domain from question's blog_url
   - Call `question_repo.increment_question_click_count(question_id)` - **Repository Layer**
     - MongoDB atomic update: `find_one_and_update({_id: question_id}, {$inc: {click_count: 1}})`
     - Return new click_count
   - Get embedding from question dict
   - If no embedding: Raise HTTPException 400
   - Call `question_repo.search_similar_blogs(embedding, limit, publisher_domain)` - **Repository Layer**
     - MongoDB vector search: Query `blogs` collection using embedding
     - Filter by domain
     - Sort by similarity score (cosine distance)
     - Limit results
     - Return list of similar blog dicts with similarity scores
   - Batch fetch blogs: `question_repo._get_blogs_by_urls(blog_urls)` - **Repository Layer**
     - Query MongoDB: `raw_blog_content` collection, find blogs with URLs in list
     - Return map of {url: blog_dict}
   - Enrich similar blogs with blog_id and metadata
   - Format response: `success_response(result={"similar_blogs": [...], "total": count}, ...)`
   - Return HTTP 200 OK with similar blogs

---

## Router: `qa_router.py` (`/api/v1/qa`)

### Endpoint 1: `POST /api/v1/qa/ask`

**Purpose:** Answer a custom question using LLM

#### Step-by-Step Flow:

1. **Router Layer** (`qa_router.py::ask_question`)
   - Receive HTTP POST request with `QARequest` (contains `question` string)
   - Extract `request_id` from middleware state
   - Dependency injection: Get authenticated `publisher` via `get_current_publisher`
   - Validate question is not empty (raise HTTPException 400 if empty)
   - Call `get_llm_service(publisher)` - **Router Layer** (helper function)
     - Extract chat_model from `publisher.config.chat_model`
     - Instantiate `LLMContentGenerator(api_key=None, model=chat_model)` - **Worker Service** (llm_content_generator)
       - Initialize with publisher's chat model configuration
   - Get chat model config: `publisher.config.chat_temperature`, `chat_max_tokens`
   - Call `llm_service.answer_question(question, context="", model=chat_model, temperature=..., max_tokens=..., use_grounding=False)` - **Worker Service**
     - Build user prompt: `f"Question: {question}\n\nContext: {context}"`
     - Call `LLMClient.generate_text(prompt=user_prompt, system_prompt=QA_ANSWER_SYSTEM_PROMPT, ...)` - **LLM Library**
       - Route to appropriate provider (OpenAI/Anthropic/Gemini) based on model
       - Generate text using provider API
       - Return `LLMGenerationResult` with text, tokens, model
     - Return `LLMGenerationResult`
   - Extract answer text from result
   - Calculate processing time and word count
   - Build `QAResponse` with question, answer, word_count, processing_time_ms
   - Format response: `success_response(result=qa_response.model_dump(), ...)`
   - Return HTTP 200 OK with answer

**Note:** This endpoint has a direct dependency on the Worker service's `LLMContentGenerator` class, which uses the standalone `llm_providers_library`.

---

## Router: `publishers_router.py` (`/api/v1/publishers`)

### Endpoint 1: `POST /api/v1/publishers/onboard`

**Purpose:** Create a new publisher account

#### Step-by-Step Flow:

1. **Router Layer** (`publishers_router.py::onboard_publisher`)
   - Receive HTTP POST request with `PublisherCreateRequest`
   - Extract `request_id` from middleware state
   - Dependency injection: Verify admin key via `verify_admin_key` dependency
   - Dependency injection: Get `publisher_repo` (PublisherRepository)
   - Instantiate `PublisherService(publisher_repo)`
   - Call `publisher_service.onboard_publisher(request, request_id)`

2. **Service Layer** (`publisher_service.py::onboard_publisher`)
   - **Check for existing publisher**:
     - Call `publisher_repo.get_publisher_by_domain(request.domain)` - **Repository Layer**
       - Query PostgreSQL: `SELECT * FROM publishers WHERE domain = $1`
       - Return Publisher model or None
     - If exists: Raise HTTPException 409 (Conflict)
   - **Create Publisher model**:
     - Build `Publisher` Pydantic model from request
     - Extract config dict: `publisher.config.model_dump()`
     - Add widget_config to config_dict: `config_dict["widget"] = request.widget_config`
   - **Create in database**:
     - Call `publisher_repo.create_publisher(publisher, config_dict)` - **Repository Layer**
       - Generate API key: `f"pub_{secrets.token_urlsafe(32)}"`
       - Create SQLAlchemy PublisherTable object
       - Insert into PostgreSQL: `session.add(publisher_table)`, `session.commit()`
       - Convert back to Publisher model
       - Return created Publisher
   - **Enrich with widget config**:
     - Call `_enrich_publisher_with_widget_config(created_publisher)` - **Service Layer**
       - Query PostgreSQL: `SELECT config FROM publishers WHERE domain = $1`
       - Extract widget config from raw config
       - Strip sensitive fields (temperatures, etc.)
       - Merge widget config into publisher dict
       - Return enriched dict
   - Build `PublisherResponse` model
   - Return `(response_dict, 201, "Publisher onboarded successfully")`

3. **Router Layer** (return)
   - Receive tuple from service
   - Format response: `success_response(result=result_data, message=message, status_code=201, ...)`
   - Return HTTP 201 Created with publisher details and API key

---

### Endpoint 2: `GET /api/v1/publishers/metadata?blog_url=...`

**Purpose:** Get publisher metadata for a blog URL (public endpoint, used by widget)

#### Step-by-Step Flow:

1. **Router Layer** (`publishers_router.py::get_publisher_metadata`)
   - Receive HTTP GET request with `blog_url` query parameter
   - Extract `request_id` from middleware state
   - **No authentication required** (public endpoint)
   - Extract domain from blog_url: `extract_domain(blog_url)`
   - Dependency injection: Get `publisher_repo` (PublisherRepository)
   - Instantiate `PublisherService(publisher_repo)`
   - Call `publisher_service.get_publisher_metadata(blog_url, request_id)`

2. **Service Layer** (`publisher_service.py::get_publisher_metadata`)
   - Extract domain from blog_url
   - Call `publisher_repo.get_publisher_by_domain(domain, allow_subdomain=True)` - **Repository Layer**
     - Query PostgreSQL: `SELECT * FROM publishers WHERE domain = $1 OR $1 LIKE '%.' || domain`
     - Return Publisher model or None
   - If not found: Raise HTTPException 404
   - Check publisher status is ACTIVE
   - Get raw config: `publisher_repo.get_publisher_raw_config_by_domain(domain)` - **Repository Layer**
   - Extract widget config from raw config
   - Build metadata response with publisher info and widget config
   - Return result_data dict

3. **Router Layer** (return)
   - Receive result_data from service
   - Format response: `success_response(result=result_data, ...)`
   - Return HTTP 200 OK with metadata (public, no auth)

---

## Summary: Flow Patterns

### Common Patterns Across Endpoints:

1. **Router Layer Always:**
   - Extract request_id from middleware
   - Handle authentication (via dependencies)
   - Inject repositories/services via dependencies
   - Format standardized HTTP responses
   - Convert exceptions to HTTP responses

2. **Service Layer Typically:**
   - Enforce business rules
   - Coordinate multiple repository calls
   - Manage transactions (reserve/release slots)
   - Transform data (dict ↔ models)
   - Validate business constraints

3. **Repository Layer Always:**
   - Perform database operations (CRUD)
   - Execute queries (MongoDB/PostgreSQL)
   - Handle atomic operations (transactions, locks)
   - Return raw data (dicts/models)
   - **No business logic**

4. **Database Operations:**
   - MongoDB: Used for jobs, questions, blog content (collections: `processing_jobs`, `questions`, `raw_blog_content`, `blogs`)
   - PostgreSQL: Used for publishers (table: `publishers`)

