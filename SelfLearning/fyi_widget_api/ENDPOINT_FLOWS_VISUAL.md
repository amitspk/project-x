# End-to-End Flow Documentation - Visual Diagrams

This document shows the complete execution flow for each endpoint using visual flow diagrams.

---

## Router: `blogs_router.py` (`/api/v1/jobs`)

### Endpoint 1: `POST /api/v1/jobs/process` - Enqueue Blog Processing

```mermaid
graph TD
    A[HTTP POST Request<br/>JobCreateRequest] --> B[Router: enqueue_blog_processing<br/>(blogs_router.py)]
    B --> C{Extract request_id<br/>from middleware<br/>(blogs_router.py)}
    C --> D[Dependency Injection<br/>get_current_publisher<br/>(auth.py)]
    D --> E{Validate<br/>X-API-Key<br/>(auth.py)}
    E -->|Invalid| F[HTTPException 401<br/>(blogs_router.py)]
    E -->|Valid| G[Get Publisher Object<br/>(auth.py)]
    G --> H[Dependency Injection<br/>Get Repositories<br/>(deps.py)]
    H --> I[Service: validate_blog_url_domain<br/>(auth_service.py)]
    I --> J{Domain Match?<br/>(auth_service.py)}
    J -->|No| K[HTTPException 403<br/>(auth_service.py)]
    J -->|Yes| L[Instantiate BlogService<br/>(blogs_router.py)]
    L --> M[Service: enqueue_blog_processing<br/>(blog_service.py)]
    
    M --> N[Normalize URL<br/>(blog_service.py)]
    N --> O{Daily Limit<br/>Check<br/>(blog_service.py)}
    O -->|Exceeded| P[HTTPException 429<br/>(blog_service.py)]
    O -->|OK| Q[Check Existing Blog<br/>(blog_service.py)]
    Q --> R{Blog Exists?<br/>(blog_service.py)}
    R -->|Yes, Completed| S[Return Existing Job<br/>Status 200<br/>(blog_service.py)]
    R -->|No or Not Completed| T[Check Whitelist<br/>(publisher_service.py)]
    T --> U{Whitelisted?<br/>(publisher_service.py)}
    U -->|No| V[HTTPException 403<br/>(publisher_service.py)]
    U -->|Yes| W[Repository: reserve_blog_slot<br/>(publisher_repository.py)]
    W --> X{Atomic Lock<br/>Check Limit<br/>(publisher_repository.py)}
    X -->|Exceeded| Y[UsageLimitExceededError<br/>(publisher_repository.py)]
    X -->|OK| Z[Increment<br/>blog_slots_reserved<br/>(publisher_repository.py)]
    Z --> AA[Repository: create_job<br/>(job_repository.py)]
    AA --> AB{Job Already<br/>Queued?<br/>(job_repository.py)}
    AB -->|Yes| AC[Return Existing Job ID<br/>(job_repository.py)]
    AB -->|No| AD[Generate UUID<br/>(job_repository.py)]
    AD --> AE[Insert Job to MongoDB<br/>status: QUEUED<br/>(job_repository.py)]
    AE --> AF[Repository: get_job_by_id<br/>(job_repository.py)]
    AF --> AG[Build JobStatusResponse<br/>(blog_service.py)]
    AG --> AH[Return Status 202<br/>(blogs_router.py)]
    
    style A fill:#cce5ff
    style B fill:#cce5ff
    style C fill:#cce5ff
    style F fill:#cce5ff
    style H fill:#cce5ff
    style L fill:#cce5ff
    style AH fill:#cce5ff
    style I fill:#fff4e1
    style J fill:#fff4e1
    style M fill:#ffe6cc
    style N fill:#ffe6cc
    style O fill:#ffe6cc
    style Q fill:#ffe6cc
    style R fill:#ffe6cc
    style S fill:#ffe6cc
    style T fill:#fff4e1
    style U fill:#fff4e1
    style AG fill:#ffe6cc
    style W fill:#e6d5ff
    style X fill:#e6d5ff
    style Z fill:#e6d5ff
    style AA fill:#e6d5ff
    style AB fill:#e6d5ff
    style AC fill:#e6d5ff
    style AD fill:#e6d5ff
    style AF fill:#e6d5ff
    style AE fill:#d5ffe6
```

#### Detailed Flow Steps:

**Router Layer:**
1. Receive HTTP POST with `blog_url`
2. Extract `request_id` from middleware
3. Authenticate publisher via `get_current_publisher` (X-API-Key)
4. Inject repositories (JobRepository, PublisherRepository)
5. Validate domain: `validate_blog_url_domain()`
6. Call service: `BlogService.enqueue_blog_processing()`

**Service Layer:**
1. Normalize URL
2. **Daily Limit Check** → Query MongoDB for completed jobs today
3. **Existing Blog Check** → Query MongoDB `raw_blog_content` collection
4. **Whitelist Check** → `PublisherService.ensure_url_whitelisted()`
5. **Reserve Slot** → `PublisherRepository.reserve_blog_slot()` (atomic)
6. **Create Job** → `JobRepository.create_job()` (check duplicates, insert)
7. Build response and return

**Repository Layer:**
- **reserve_blog_slot**: PostgreSQL row lock, check limit, increment counter
- **create_job**: MongoDB duplicate check, insert new job document

---

### Endpoint 2: `GET /api/v1/jobs/status/{job_id}` - Get Job Status

```mermaid
graph TD
    A[HTTP GET Request<br/>job_id path param] --> B[Router: get_job_status]
    B --> C[Verify Admin Key<br/>X-Admin-Key<br/>(auth.py)]
    C -->|Invalid| D[HTTPException 401]
    C -->|Valid| E[Dependency Injection<br/>Get JobRepository]
    E --> F[Instantiate BlogService]
    F --> G[Service: get_job_status]
    G --> H[Repository: get_job_by_id]
    H --> I[Query MongoDB<br/>find_one job_id]
    I --> J{Job Found?}
    J -->|No| K[HTTPException 404]
    J -->|Yes| L[Build JobStatusResponse]
    L --> M[Convert Dates to ISO]
    M --> N[Return Status 200<br/>with Job Details]
    
    style A fill:#cce5ff
    style G fill:#ffe6cc
    style H fill:#e6d5ff
    style I fill:#d5ffe6
    style N fill:#cce5ff
```

---

### Endpoint 3: `GET /api/v1/jobs/stats` - Get Queue Statistics

```mermaid
graph TD
    A[HTTP GET Request] --> B[Router: get_queue_stats<br/>(blogs_router.py)]
    B --> C[Verify Admin Key<br/>(auth.py)]
    C --> D[Instantiate BlogService]
    D --> E[Service: get_queue_stats<br/>(blog_service.py)]
    E --> F[Repository: get_job_stats<br/>(job_repository.py)]
    F --> G[MongoDB Aggregation<br/>$group by status]
    G --> H[Count per Status]
    H --> I[Calculate Total]
    I --> J[Return Status 200<br/>Stats Object]
    
    style A fill:#cce5ff
    style E fill:#ffe6cc
    style F fill:#e6d5ff
    style G fill:#d5ffe6
    style J fill:#cce5ff
```

---

### Endpoint 4: `POST /api/v1/jobs/cancel/{job_id}` - Cancel Job

```mermaid
graph TD
    A[HTTP POST Request<br/>job_id path param] --> B[Router: cancel_job<br/>(blogs_router.py)]
    B --> C[Verify Admin Key<br/>(auth.py)]
    C --> D[Instantiate BlogService<br/>(blogs_router.py)]
    D --> E[Service: cancel_job<br/>(blog_service.py)]
    E --> F[Repository: cancel_job<br/>(job_repository.py)]
    F --> G{Find Job<br/>status=queued?<br/>(job_repository.py)}
    G -->|Not Found| H[Return False<br/>(job_repository.py)]
    G -->|Found| I[MongoDB Update<br/>status: cancelled<br/>(job_repository.py)]
    I --> J{Updated?<br/>(blog_service.py)}
    J -->|No| K[HTTPException 400<br/>(blog_service.py)]
    J -->|Yes| L[Return Status 200<br/>Cancelled<br/>(blogs_router.py)]
    
    style A fill:#cce5ff
    style B fill:#cce5ff
    style C fill:#cce5ff
    style D fill:#cce5ff
    style L fill:#cce5ff
    style E fill:#ffe6cc
    style J fill:#ffe6cc
    style K fill:#ffe6cc
    style F fill:#e6d5ff
    style G fill:#e6d5ff
    style H fill:#e6d5ff
    style I fill:#d5ffe6
```

---

## Router: `questions_router.py` (`/api/v1/questions`)

### Endpoint 1: `GET /api/v1/questions/check-and-load` - Smart Question Loading

```mermaid
graph TD
    A[HTTP GET Request<br/>blog_url query] --> B[Router: check_and_load_questions<br/>(questions_router.py)]
    B --> C[Authenticate Publisher<br/>(auth.py)]
    C --> D[Normalize URL<br/>(questions_router.py)]
    D --> E[Validate Domain<br/>(auth_service.py)]
    E --> F[Instantiate QuestionService<br/>(questions_router.py)]
    F --> G[Service: check_and_load_questions<br/>(question_service.py)]
    
    G --> H[Repository: get_questions_by_url<br/>(question_repository.py)]
    H --> I{Questions<br/>Exist?<br/>(question_service.py)}
    I -->|Yes| J[Return Status: ready<br/>Questions Array<br/>(question_service.py)]
    I -->|No| K[Repository: get_job_by_url<br/>(job_repository.py)]
    K --> L{Job Exists?<br/>(question_service.py)}
    L -->|No| M[Reserve Slot<br/>(publisher_repository.py)]
    M --> N[Repository: create_job<br/>(job_repository.py)]
    N --> O[Return Status: not_started<br/>job_id<br/>(question_service.py)]
    L -->|Yes| P{Job Status?<br/>(question_service.py)}
    P -->|completed| Q[Get Questions<br/>(question_service.py)]
    Q --> J
    P -->|processing| R[Return Status: processing<br/>job_id<br/>(question_service.py)]
    P -->|failed| S[Return Status: failed<br/>job_id<br/>(question_service.py)]
    
    style A fill:#cce5ff
    style B fill:#cce5ff
    style D fill:#cce5ff
    style F fill:#cce5ff
    style G fill:#ffe6cc
    style I fill:#ffe6cc
    style J fill:#ffe6cc
    style L fill:#ffe6cc
    style O fill:#ffe6cc
    style P fill:#ffe6cc
    style Q fill:#ffe6cc
    style R fill:#ffe6cc
    style S fill:#ffe6cc
    style H fill:#e6d5ff
    style K fill:#e6d5ff
    style M fill:#e6d5ff
    style N fill:#e6d5ff
```

---

### Endpoint 2: `GET /api/v1/questions/by-url` - Get Questions by URL

```mermaid
graph TD
    A[HTTP GET Request<br/>blog_url query] --> B[Router: get_questions_by_url<br/>(questions_router.py)]
    B --> C[Authenticate Publisher<br/>(auth.py)]
    C --> D[Validate Domain]
    D --> E[Instantiate QuestionService]
    E --> F[Service: get_questions_by_url<br/>(question_service.py)]
    F --> G[Repository: get_questions_by_url<br/>(question_repository.py)]
    G --> H[MongoDB Query<br/>Find by blog_url]
    H --> I{Questions<br/>Found?}
    I -->|No| J[HTTPException 404]
    I -->|Yes| K[Randomize Questions]
    K --> L[Repository: get_blog_by_url<br/>(question_repository.py)]
    L --> M[Get Blog Info]
    M --> N[Build Response<br/>Questions + Blog]
    N --> O[Return Status 200]
    
    style A fill:#cce5ff
    style F fill:#ffe6cc
    style G fill:#e6d5ff
    style L fill:#e6d5ff
    style O fill:#cce5ff
```

---

### Endpoint 3: `GET /api/v1/questions/{question_id}` - Get Question by ID

```mermaid
graph TD
    A[HTTP GET Request<br/>question_id path] --> B[Router: get_question_by_id<br/>(questions_router.py)]
    B --> C[Verify Admin Key<br/>(auth.py)]
    C --> D[Repository: get_question_by_id<br/>(question_repository.py)]
    D --> E[MongoDB Query<br/>Find by _id<br/>(question_repository.py)]
    E --> F{Question<br/>Found?<br/>(questions_router.py)}
    F -->|No| G[HTTPException 404<br/>(questions_router.py)]
    F -->|Yes| H[Return Status 200<br/>Question Object<br/>(questions_router.py)]
    
    style A fill:#cce5ff
    style D fill:#e6d5ff
    style E fill:#d5ffe6
    style H fill:#cce5ff
```

---

### Endpoint 4: `DELETE /api/v1/questions/{blog_id}` - Delete Blog

```mermaid
graph TD
    A[HTTP DELETE Request<br/>blog_id path] --> B[Router: delete_blog_by_id<br/>(questions_router.py)]
    B --> C[Verify Admin Key<br/>(auth.py)]
    C --> D[Validate ObjectId<br/>(questions_router.py)]
    D --> E[Repository: delete_blog<br/>(question_repository.py)]
    E --> F[Get Blog from MongoDB<br/>(question_repository.py)]
    F --> G[Extract blog_url<br/>(question_repository.py)]
    G --> H[Delete All Questions<br/>delete_many blog_url<br/>(question_repository.py)]
    H --> I[Delete Blog<br/>delete_one _id<br/>(question_repository.py)]
    I --> J[Return Status 200<br/>Deletion Counts<br/>(questions_router.py)]
    
    style A fill:#cce5ff
    style E fill:#e6d5ff
    style F fill:#d5ffe6
    style H fill:#d5ffe6
    style I fill:#d5ffe6
    style J fill:#cce5ff
```

---

## Router: `search_router.py` (`/api/v1/search`)

### Endpoint 1: `POST /api/v1/search/similar` - Find Similar Blogs

```mermaid
graph TD
    A[HTTP POST Request<br/>SearchSimilarRequest<br/>question_id + limit] --> B[Router: search_similar_blogs<br/>(search_router.py)]
    B --> C[Authenticate Publisher<br/>(auth.py)]
    C --> D[Repository: get_question_by_id<br/>(question_repository.py)]
    D --> E[MongoDB Query<br/>Find Question<br/>(question_repository.py)]
    E --> F{Question<br/>Found?<br/>(questions_router.py)}
    F -->|No| G[HTTPException 404<br/>(questions_router.py)]
    F -->|Yes| H[Get blog_url from Question<br/>(search_router.py)]
    H --> I[Validate Domain<br/>(auth_service.py)]
    I --> J[Repository: increment_question_click_count<br/>(question_repository.py)]
    J --> K[MongoDB Atomic Update<br/>$inc click_count]
    K --> L[Get Embedding from Question<br/>(search_router.py)]
    L --> M{Embedding<br/>Exists?}
    M -->|No| N[HTTPException 400]
    M -->|Yes| O[Repository: search_similar_blogs<br/>(question_repository.py)]
    O --> P[MongoDB Vector Search<br/>Cosine Similarity]
    P --> Q[Filter by Domain<br/>(question_repository.py)]
    Q --> R[Sort by Similarity Score<br/>(question_repository.py)]
    R --> S[Limit Results<br/>(question_repository.py)]
    S --> T[Repository: _get_blogs_by_urls<br/>(question_repository.py)]
    T --> U[Batch Fetch Blog Docs<br/>(question_repository.py)]
    U --> V[Enrich with Blog IDs<br/>(search_router.py)]
    V --> W[Return Status 200<br/>Similar Blogs Array<br/>(search_router.py)]
    
    style A fill:#cce5ff
    style D fill:#e6d5ff
    style J fill:#e6d5ff
    style O fill:#e6d5ff
    style T fill:#e6d5ff
    style P fill:#d5ffe6
    style W fill:#cce5ff
```

---

## Router: `qa_router.py` (`/api/v1/qa`)

### Endpoint 1: `POST /api/v1/qa/ask` - Answer Question with LLM

```mermaid
graph TD
    A[HTTP POST Request<br/>QARequest question] --> B[Router: ask_question<br/>(qa_router.py)]
    B --> C[Authenticate Publisher<br/>(auth.py)]
    C --> D{Question<br/>Empty?}
    D -->|Yes| E[HTTPException 400]
    D -->|No| F[Get LLM Service]
    F --> G[Extract chat_model<br/>from publisher.config]
    G --> H[Instantiate LLMContentGenerator<br/>Worker Service]
    H --> I[Service: answer_question<br/>(llm_content_generator.py)]
    I --> J[Build User Prompt<br/>Question + Context]
    J --> K[LLM Library: generate_text]
    K --> L{Model<br/>Provider?}
    L -->|OpenAI| M[OpenAI API Call]
    L -->|Anthropic| N[Anthropic API Call]
    L -->|Gemini| O[Gemini API Call]
    M --> P[LLMGenerationResult]
    N --> P
    O --> P
    P --> Q[Extract Answer Text]
    Q --> R[Calculate Word Count]
    R --> S[Calculate Processing Time]
    S --> T[Build QAResponse]
    T --> U[Return Status 200<br/>Question + Answer]
    
    style A fill:#cce5ff
    style I fill:#ffe6cc
    style K fill:#e6d5ff
    style M fill:#d5ffe6
    style N fill:#d5ffe6
    style O fill:#d5ffe6
    style U fill:#cce5ff
```

**Note:** This endpoint has a dependency on Worker Service's `LLMContentGenerator`, which uses the standalone `llm_providers_library`.

---

## Router: `publishers_router.py` (`/api/v1/publishers`)

### Endpoint 1: `POST /api/v1/publishers/onboard` - Create Publisher

```mermaid
graph TD
    A[HTTP POST Request<br/>PublisherCreateRequest] --> B[Router: onboard_publisher<br/>(publishers_router.py)]
    B --> C[Verify Admin Key<br/>(auth.py)]
    C --> D[Instantiate PublisherService]
    D --> E[Service: onboard_publisher<br/>(publisher_service.py)]
    E --> F[Repository: get_publisher_by_domain<br/>(publisher_repository.py)]
    F --> G[PostgreSQL Query<br/>SELECT by domain]
    G --> H{Publisher<br/>Exists?}
    H -->|Yes| I[HTTPException 409]
    H -->|No| J[Build Publisher Model]
    J --> K[Extract Config Dict]
    K --> L[Add Widget Config]
    L --> M[Repository: create_publisher<br/>(publisher_repository.py)]
    M --> N[Generate API Key<br/>pub_token]
    N --> O[Create PublisherTable Object]
    O --> P[PostgreSQL INSERT]
    P --> Q[Convert to Publisher Model]
    Q --> R[Service: _enrich_publisher_with_widget_config]
    R --> S[Get Raw Config from DB]
    S --> T[Extract Widget Config]
    T --> U[Strip Sensitive Fields]
    U --> V[Build PublisherResponse]
    V --> W[Return Status 201<br/>Publisher + API Key]
    
    style A fill:#cce5ff
    style E fill:#ffe6cc
    style F fill:#e6d5ff
    style M fill:#e6d5ff
    style P fill:#d5ffe6
    style W fill:#cce5ff
```

---

### Endpoint 2: `GET /api/v1/publishers/metadata` - Get Publisher Metadata (Public)

```mermaid
graph TD
    A[HTTP GET Request<br/>blog_url query<br/>NO AUTH] --> B[Router: get_publisher_metadata<br/>(publishers_router.py)]
    B --> C[Extract Domain<br/>(publishers_router.py)]
    C --> D[Instantiate PublisherService]
    D --> E[Service: get_publisher_metadata<br/>(publisher_service.py)]
    E --> F[Repository: get_publisher_by_domain<br/>(publisher_repository.py)<br/>allow_subdomain=true]
    F --> G[PostgreSQL Query<br/>Exact or Subdomain Match]
    G --> H{Publisher<br/>Found?}
    H -->|No| I[HTTPException 404]
    H -->|Yes| J{Status<br/>ACTIVE?}
    J -->|No| K[HTTPException 404]
    J -->|Yes| L[Repository: get_publisher_raw_config_by_domain]
    L --> M[Get Widget Config]
    M --> N[Build Metadata Response]
    N --> O[Return Status 200<br/>Publisher Metadata]
    
    style A fill:#cce5ff
    style E fill:#ffe6cc
    style F fill:#e6d5ff
    style L fill:#e6d5ff
    style G fill:#d5ffe6
    style O fill:#cce5ff
```

---

## Layer Responsibilities Summary

### Router Layer (HTTP Boundary)
- ✅ Request parsing and validation
- ✅ Authentication (via dependencies)
- ✅ Dependency injection (repositories/services)
- ✅ Response formatting (standardized JSON)
- ✅ Error handling → HTTP exceptions

### Service Layer (Business Logic)
- ✅ Business rules enforcement
- ✅ Cross-repository coordination
- ✅ Transaction management
- ✅ Data transformation (dict ↔ models)
- ✅ Validation and constraint checking

### Repository Layer (Data Access)
- ✅ Database operations (CRUD)
- ✅ Query execution (MongoDB/PostgreSQL)
- ✅ Atomic operations (locks, transactions)
- ✅ Data persistence
- ❌ **NO business logic**

### Database Layer
- **MongoDB Collections:**
  - `processing_jobs` - Job queue
  - `questions` - Generated questions
  - `raw_blog_content` - Blog content cache
  - `blogs` - Blog summaries with embeddings
  
- **PostgreSQL Tables:**
  - `publishers` - Publisher accounts and configs

---

## Color Coding Legend

All boxes are colored based on the layer they belong to:

- 🔵 **Light Blue (#cce5ff)** - **Router/HTTP Layer**
  - HTTP request/response handling
  - Authentication checks
  - Response formatting
  - Error handling

- 🟠 **Orange (#ffe6cc)** - **Service Layer**
  - Business logic
  - Business rules enforcement
  - Cross-repository coordination
  - Transaction management
  - Data transformation

- 🟣 **Purple (#e6d5ff)** - **Repository Layer**
  - Database operations (CRUD)
  - Query execution
  - Atomic operations
  - Data persistence

- 🟢 **Light Green (#d5ffe6)** - **Database Operations**
  - MongoDB queries
  - PostgreSQL queries
  - Database inserts/updates

- ⬜ **White/Gray** - **Decision Points**
  - Conditional logic
  - If/else checks
  - Flow control

