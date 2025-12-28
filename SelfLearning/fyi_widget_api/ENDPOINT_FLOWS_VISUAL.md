# End-to-End Flow Documentation - Visual Diagrams

This document shows the complete execution flow for each endpoint using visual flow diagrams.

---

## Router: `blogs_router.py` (`/api/v1/jobs`)

### Endpoint 1: `POST /api/v1/jobs/process` - Enqueue Blog Processing

```mermaid
graph TD
    A[HTTP POST Request<br/>JobCreateRequest] --> B[Router: enqueue_blog_processing]
    B --> C{Extract request_id<br/>from middleware}
    C --> D[Dependency Injection<br/>get_current_publisher]
    D --> E{Validate<br/>X-API-Key}
    E -->|Invalid| F[HTTPException 401]
    E -->|Valid| G[Get Publisher Object]
    G --> H[Dependency Injection<br/>Get Repositories]
    H --> I[Service: validate_blog_url_domain]
    I --> J{Domain Match?}
    J -->|No| K[HTTPException 403]
    J -->|Yes| L[Instantiate BlogService]
    L --> M[Service: enqueue_blog_processing]
    
    M --> N[Normalize URL]
    N --> O{Daily Limit<br/>Check}
    O -->|Exceeded| P[HTTPException 429]
    O -->|OK| Q[Check Existing Blog]
    Q --> R{Blog Exists?}
    R -->|Yes, Completed| S[Return Existing Job<br/>Status 200]
    R -->|No or Not Completed| T[Check Whitelist]
    T --> U{Whitelisted?}
    U -->|No| V[HTTPException 403]
    U -->|Yes| W[Repository: reserve_blog_slot]
    W --> X{Atomic Lock<br/>Check Limit}
    X -->|Exceeded| Y[UsageLimitExceededError]
    X -->|OK| Z[Increment<br/>blog_slots_reserved]
    Z --> AA[Repository: create_job]
    AA --> AB{Job Already<br/>Queued?}
    AB -->|Yes| AC[Return Existing Job ID]
    AB -->|No| AD[Generate UUID]
    AD --> AE[Insert Job to MongoDB<br/>status: QUEUED]
    AE --> AF[Repository: get_job_by_id]
    AF --> AG[Build JobStatusResponse]
    AG --> AH[Return Status 202]
    
    style A fill:#e1f5ff
    style M fill:#fff4e1
    style W fill:#ffe1f5
    style AA fill:#ffe1f5
    style AE fill:#e1ffe1
    style AH fill:#e1f5ff
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
    B --> C[Verify Admin Key<br/>X-Admin-Key]
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
    
    style A fill:#e1f5ff
    style G fill:#fff4e1
    style H fill:#ffe1f5
    style I fill:#e1ffe1
    style N fill:#e1f5ff
```

---

### Endpoint 3: `GET /api/v1/jobs/stats` - Get Queue Statistics

```mermaid
graph TD
    A[HTTP GET Request] --> B[Router: get_queue_stats]
    B --> C[Verify Admin Key]
    C --> D[Instantiate BlogService]
    D --> E[Service: get_queue_stats]
    E --> F[Repository: get_job_stats]
    F --> G[MongoDB Aggregation<br/>$group by status]
    G --> H[Count per Status]
    H --> I[Calculate Total]
    I --> J[Return Status 200<br/>Stats Object]
    
    style A fill:#e1f5ff
    style E fill:#fff4e1
    style F fill:#ffe1f5
    style G fill:#e1ffe1
    style J fill:#e1f5ff
```

---

### Endpoint 4: `POST /api/v1/jobs/cancel/{job_id}` - Cancel Job

```mermaid
graph TD
    A[HTTP POST Request<br/>job_id path param] --> B[Router: cancel_job]
    B --> C[Verify Admin Key]
    C --> D[Instantiate BlogService]
    D --> E[Service: cancel_job]
    E --> F[Repository: cancel_job]
    F --> G{Find Job<br/>status=queued?}
    G -->|Not Found| H[Return False]
    G -->|Found| I[MongoDB Update<br/>status: cancelled]
    I --> J{Updated?}
    J -->|No| K[HTTPException 400]
    J -->|Yes| L[Return Status 200<br/>Cancelled]
    
    style A fill:#e1f5ff
    style E fill:#fff4e1
    style F fill:#ffe1f5
    style I fill:#e1ffe1
    style L fill:#e1f5ff
```

---

## Router: `questions_router.py` (`/api/v1/questions`)

### Endpoint 1: `GET /api/v1/questions/check-and-load` - Smart Question Loading

```mermaid
graph TD
    A[HTTP GET Request<br/>blog_url query] --> B[Router: check_and_load_questions]
    B --> C[Authenticate Publisher]
    C --> D[Normalize URL]
    D --> E[Validate Domain]
    E --> F[Instantiate QuestionService]
    F --> G[Service: check_and_load_questions]
    
    G --> H[Repository: get_questions_by_url]
    H --> I{Questions<br/>Exist?}
    I -->|Yes| J[Return Status: ready<br/>Questions Array]
    I -->|No| K[Repository: get_job_by_url]
    K --> L{Job Exists?}
    L -->|No| M[Reserve Slot]
    M --> N[Repository: create_job]
    N --> O[Return Status: not_started<br/>job_id]
    L -->|Yes| P{Job Status?}
    P -->|completed| Q[Get Questions]
    Q --> J
    P -->|processing| R[Return Status: processing<br/>job_id]
    P -->|failed| S[Return Status: failed<br/>job_id]
    
    style A fill:#e1f5ff
    style G fill:#fff4e1
    style H fill:#ffe1f5
    style K fill:#ffe1f5
    style N fill:#ffe1f5
    style J fill:#e1f5ff
```

---

### Endpoint 2: `GET /api/v1/questions/by-url` - Get Questions by URL

```mermaid
graph TD
    A[HTTP GET Request<br/>blog_url query] --> B[Router: get_questions_by_url]
    B --> C[Authenticate Publisher]
    C --> D[Validate Domain]
    D --> E[Instantiate QuestionService]
    E --> F[Service: get_questions_by_url]
    F --> G[Repository: get_questions_by_url]
    G --> H[MongoDB Query<br/>Find by blog_url]
    H --> I{Questions<br/>Found?}
    I -->|No| J[HTTPException 404]
    I -->|Yes| K[Randomize Questions]
    K --> L[Repository: get_blog_by_url]
    L --> M[Get Blog Info]
    M --> N[Build Response<br/>Questions + Blog]
    N --> O[Return Status 200]
    
    style A fill:#e1f5ff
    style F fill:#fff4e1
    style G fill:#ffe1f5
    style L fill:#ffe1f5
    style O fill:#e1f5ff
```

---

### Endpoint 3: `GET /api/v1/questions/{question_id}` - Get Question by ID

```mermaid
graph TD
    A[HTTP GET Request<br/>question_id path] --> B[Router: get_question_by_id]
    B --> C[Verify Admin Key]
    C --> D[Repository: get_question_by_id]
    D --> E[MongoDB Query<br/>Find by _id]
    E --> F{Question<br/>Found?}
    F -->|No| G[HTTPException 404]
    F -->|Yes| H[Return Status 200<br/>Question Object]
    
    style A fill:#e1f5ff
    style D fill:#ffe1f5
    style E fill:#e1ffe1
    style H fill:#e1f5ff
```

---

### Endpoint 4: `DELETE /api/v1/questions/{blog_id}` - Delete Blog

```mermaid
graph TD
    A[HTTP DELETE Request<br/>blog_id path] --> B[Router: delete_blog_by_id]
    B --> C[Verify Admin Key]
    C --> D[Validate ObjectId]
    D --> E[Repository: delete_blog]
    E --> F[Get Blog from MongoDB]
    F --> G[Extract blog_url]
    G --> H[Delete All Questions<br/>delete_many blog_url]
    H --> I[Delete Blog<br/>delete_one _id]
    I --> J[Return Status 200<br/>Deletion Counts]
    
    style A fill:#e1f5ff
    style E fill:#ffe1f5
    style F fill:#e1ffe1
    style H fill:#e1ffe1
    style I fill:#e1ffe1
    style J fill:#e1f5ff
```

---

## Router: `search_router.py` (`/api/v1/search`)

### Endpoint 1: `POST /api/v1/search/similar` - Find Similar Blogs

```mermaid
graph TD
    A[HTTP POST Request<br/>SearchSimilarRequest<br/>question_id + limit] --> B[Router: search_similar_blogs]
    B --> C[Authenticate Publisher]
    C --> D[Repository: get_question_by_id]
    D --> E[MongoDB Query<br/>Find Question]
    E --> F{Question<br/>Found?}
    F -->|No| G[HTTPException 404]
    F -->|Yes| H[Get blog_url from Question]
    H --> I[Validate Domain]
    I --> J[Repository: increment_question_click_count]
    J --> K[MongoDB Atomic Update<br/>$inc click_count]
    K --> L[Get Embedding from Question]
    L --> M{Embedding<br/>Exists?}
    M -->|No| N[HTTPException 400]
    M -->|Yes| O[Repository: search_similar_blogs]
    O --> P[MongoDB Vector Search<br/>Cosine Similarity]
    P --> Q[Filter by Domain]
    Q --> R[Sort by Similarity Score]
    R --> S[Limit Results]
    S --> T[Repository: _get_blogs_by_urls]
    T --> U[Batch Fetch Blog Docs]
    U --> V[Enrich with Blog IDs]
    V --> W[Return Status 200<br/>Similar Blogs Array]
    
    style A fill:#e1f5ff
    style D fill:#ffe1f5
    style J fill:#ffe1f5
    style O fill:#ffe1f5
    style T fill:#ffe1f5
    style P fill:#e1ffe1
    style W fill:#e1f5ff
```

---

## Router: `qa_router.py` (`/api/v1/qa`)

### Endpoint 1: `POST /api/v1/qa/ask` - Answer Question with LLM

```mermaid
graph TD
    A[HTTP POST Request<br/>QARequest question] --> B[Router: ask_question]
    B --> C[Authenticate Publisher]
    C --> D{Question<br/>Empty?}
    D -->|Yes| E[HTTPException 400]
    D -->|No| F[Get LLM Service]
    F --> G[Extract chat_model<br/>from publisher.config]
    G --> H[Instantiate LLMContentGenerator<br/>Worker Service]
    H --> I[Service: answer_question]
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
    
    style A fill:#e1f5ff
    style I fill:#fff4e1
    style K fill:#ffe1f5
    style M fill:#e1ffe1
    style N fill:#e1ffe1
    style O fill:#e1ffe1
    style U fill:#e1f5ff
```

**Note:** This endpoint has a dependency on Worker Service's `LLMContentGenerator`, which uses the standalone `llm_providers_library`.

---

## Router: `publishers_router.py` (`/api/v1/publishers`)

### Endpoint 1: `POST /api/v1/publishers/onboard` - Create Publisher

```mermaid
graph TD
    A[HTTP POST Request<br/>PublisherCreateRequest] --> B[Router: onboard_publisher]
    B --> C[Verify Admin Key]
    C --> D[Instantiate PublisherService]
    D --> E[Service: onboard_publisher]
    E --> F[Repository: get_publisher_by_domain]
    F --> G[PostgreSQL Query<br/>SELECT by domain]
    G --> H{Publisher<br/>Exists?}
    H -->|Yes| I[HTTPException 409]
    H -->|No| J[Build Publisher Model]
    J --> K[Extract Config Dict]
    K --> L[Add Widget Config]
    L --> M[Repository: create_publisher]
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
    
    style A fill:#e1f5ff
    style E fill:#fff4e1
    style F fill:#ffe1f5
    style M fill:#ffe1f5
    style P fill:#e1ffe1
    style W fill:#e1f5ff
```

---

### Endpoint 2: `GET /api/v1/publishers/metadata` - Get Publisher Metadata (Public)

```mermaid
graph TD
    A[HTTP GET Request<br/>blog_url query<br/>NO AUTH] --> B[Router: get_publisher_metadata]
    B --> C[Extract Domain]
    C --> D[Instantiate PublisherService]
    D --> E[Service: get_publisher_metadata]
    E --> F[Repository: get_publisher_by_domain<br/>allow_subdomain=true]
    F --> G[PostgreSQL Query<br/>Exact or Subdomain Match]
    G --> H{Publisher<br/>Found?}
    H -->|No| I[HTTPException 404]
    H -->|Yes| J{Status<br/>ACTIVE?}
    J -->|No| K[HTTPException 404]
    J -->|Yes| L[Repository: get_publisher_raw_config_by_domain]
    L --> M[Get Widget Config]
    M --> N[Build Metadata Response]
    N --> O[Return Status 200<br/>Publisher Metadata]
    
    style A fill:#e1f5ff
    style E fill:#fff4e1
    style F fill:#ffe1f5
    style L fill:#ffe1f5
    style G fill:#e1ffe1
    style O fill:#e1f5ff
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

## Legend

- 🔵 **Blue boxes** - HTTP/Router layer
- 🟡 **Yellow boxes** - Service layer (business logic)
- 🟣 **Pink boxes** - Repository layer (data access)
- 🟢 **Green boxes** - Database operations
- ⬜ **White boxes** - Decision points or data transformations

