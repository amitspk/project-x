# End-to-End Flow Documentation - Visual Diagrams

This document shows the complete execution flow for each endpoint using visual flow diagrams.

---

## Router: `blogs_router.py` (`/api/v1/jobs`)

### Endpoint 1: `POST /api/v1/jobs/process` - Enqueue Blog Processing

```mermaid
graph TD
    A[HTTP POST Request<br/>JobCreateRequest] --> B[Router: enqueue_blog_processing &lpar;blogs_router.py&rpar;]
    B --> C{Extract request_id<br/>from middleware &lpar;blogs_router.py&rpar;}
    C --> D[Dependency Injection<br/>get_current_publisher &lpar;auth.py&rpar;]
    D --> E{Validate<br/>X-API-Key &lpar;auth.py&rpar;}
    E -->|Invalid| F[HTTPException 401 &lpar;blogs_router.py&rpar;]
    E -->|Valid| G[Get Publisher Object &lpar;auth.py&rpar;]
    G --> H[Dependency Injection<br/>Get Repositories &lpar;deps.py&rpar;]
    H --> I[Service: validate_blog_url_domain &lpar;auth_service.py&rpar;]
    I --> J{Domain Match? &lpar;auth_service.py&rpar;}
    J -->|No| K[HTTPException 403 &lpar;auth_service.py&rpar;]
    J -->|Yes| L[Instantiate BlogService &lpar;blogs_router.py&rpar;]
    L --> M[Service: enqueue_blog_processing &lpar;blog_service.py&rpar;]
    
    M --> N[Normalize URL &lpar;blog_service.py&rpar;]
    N --> O{Daily Limit<br/>Check &lpar;blog_service.py&rpar;}
    O -->|Exceeded| P[HTTPException 429 &lpar;blog_service.py&rpar;]
    O -->|OK| Q[Check Existing Blog &lpar;blog_service.py&rpar;]
    Q --> R{Blog Exists? &lpar;blog_service.py&rpar;}
    R -->|Yes, Completed| S[Return Existing Job<br/>Status 200 &lpar;blog_service.py&rpar;]
    R -->|No or Not Completed| T[Check Whitelist &lpar;publisher_service.py&rpar;]
    T --> U{Whitelisted? &lpar;publisher_service.py&rpar;}
    U -->|No| V[HTTPException 403 &lpar;publisher_service.py&rpar;]
    U -->|Yes| W[Repository: reserve_blog_slot &lpar;publisher_repository.py&rpar;]
    W --> X{Atomic Lock<br/>Check Limit &lpar;publisher_repository.py&rpar;}
    X -->|Exceeded| Y[UsageLimitExceededError &lpar;publisher_repository.py&rpar;]
    X -->|OK| Z[Increment<br/>blog_slots_reserved &lpar;publisher_repository.py&rpar;]
    Z --> AA[Repository: create_job &lpar;job_repository.py&rpar;]
    AA --> AB{Job Already<br/>Queued? &lpar;job_repository.py&rpar;}
    AB -->|Yes| AC[Return Existing Job ID &lpar;job_repository.py&rpar;]
    AB -->|No| AD[Generate UUID &lpar;job_repository.py&rpar;]
    AD --> AE[Insert Job to MongoDB<br/>status: QUEUED &lpar;job_repository.py&rpar;]
    AE --> AF[Repository: get_job_by_id &lpar;job_repository.py&rpar;]
    AF --> AG[Build JobStatusResponse &lpar;blog_service.py&rpar;]
    AG --> AH[Return Status 202 &lpar;blogs_router.py&rpar;]
    
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
    B --> C[Verify Admin Key<br/>X-Admin-Key &lpar;auth.py&rpar;]
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
    A[HTTP GET Request] --> B[Router: get_queue_stats &lpar;blogs_router.py&rpar;]
    B --> C[Verify Admin Key &lpar;auth.py&rpar;]
    C --> D[Instantiate BlogService]
    D --> E[Service: get_queue_stats &lpar;blog_service.py&rpar;]
    E --> F[Repository: get_job_stats &lpar;job_repository.py&rpar;]
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
    A[HTTP POST Request<br/>job_id path param] --> B[Router: cancel_job &lpar;blogs_router.py&rpar;]
    B --> C[Verify Admin Key &lpar;auth.py&rpar;]
    C --> D[Instantiate BlogService &lpar;blogs_router.py&rpar;]
    D --> E[Service: cancel_job &lpar;blog_service.py&rpar;]
    E --> F[Repository: cancel_job &lpar;job_repository.py&rpar;]
    F --> G{Find Job<br/>status=queued? &lpar;job_repository.py&rpar;}
    G -->|Not Found| H[Return False &lpar;job_repository.py&rpar;]
    G -->|Found| I[MongoDB Update<br/>status: cancelled &lpar;job_repository.py&rpar;]
    I --> J{Updated? &lpar;blog_service.py&rpar;}
    J -->|No| K[HTTPException 400 &lpar;blog_service.py&rpar;]
    J -->|Yes| L[Return Status 200<br/>Cancelled &lpar;blogs_router.py&rpar;]
    
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
    A[HTTP GET Request<br/>blog_url query] --> B[Router: check_and_load_questions &lpar;questions_router.py&rpar;]
    B --> C[Authenticate Publisher &lpar;auth.py&rpar;]
    C --> D[Normalize URL &lpar;questions_router.py&rpar;]
    D --> E[Validate Domain &lpar;auth_service.py&rpar;]
    E --> F[Instantiate QuestionService &lpar;questions_router.py&rpar;]
    F --> G[Service: check_and_load_questions &lpar;question_service.py&rpar;]
    
    G --> H[Repository: get_questions_by_url &lpar;question_repository.py&rpar;]
    H --> I{Questions<br/>Exist? &lpar;question_service.py&rpar;}
    I -->|Yes| J[Return Status: ready<br/>Questions Array &lpar;question_service.py&rpar;]
    I -->|No| K[Repository: get_job_by_url &lpar;job_repository.py&rpar;]
    K --> L{Job Exists? &lpar;question_service.py&rpar;}
    L -->|No| M[Reserve Slot &lpar;publisher_repository.py&rpar;]
    M --> N[Repository: create_job &lpar;job_repository.py&rpar;]
    N --> O[Return Status: not_started<br/>job_id &lpar;question_service.py&rpar;]
    L -->|Yes| P{Job Status? &lpar;question_service.py&rpar;}
    P -->|completed| Q[Get Questions &lpar;question_service.py&rpar;]
    Q --> J
    P -->|processing| R[Return Status: processing<br/>job_id &lpar;question_service.py&rpar;]
    P -->|failed| S[Return Status: failed<br/>job_id &lpar;question_service.py&rpar;]
    
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
    A[HTTP GET Request<br/>blog_url query] --> B[Router: get_questions_by_url &lpar;questions_router.py&rpar;]
    B --> C[Authenticate Publisher &lpar;auth.py&rpar;]
    C --> D[Validate Domain]
    D --> E[Instantiate QuestionService]
    E --> F[Service: get_questions_by_url &lpar;question_service.py&rpar;]
    F --> G[Repository: get_questions_by_url &lpar;question_repository.py&rpar;]
    G --> H[MongoDB Query<br/>Find by blog_url]
    H --> I{Questions<br/>Found?}
    I -->|No| J[HTTPException 404]
    I -->|Yes| K[Randomize Questions]
    K --> L[Repository: get_blog_by_url &lpar;question_repository.py&rpar;]
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
    A[HTTP GET Request<br/>question_id path] --> B[Router: get_question_by_id &lpar;questions_router.py&rpar;]
    B --> C[Verify Admin Key &lpar;auth.py&rpar;]
    C --> D[Repository: get_question_by_id &lpar;question_repository.py&rpar;]
    D --> E[MongoDB Query<br/>Find by _id &lpar;question_repository.py&rpar;]
    E --> F{Question<br/>Found? &lpar;questions_router.py&rpar;}
    F -->|No| G[HTTPException 404 &lpar;questions_router.py&rpar;]
    F -->|Yes| H[Return Status 200<br/>Question Object &lpar;questions_router.py&rpar;]
    
    style A fill:#cce5ff
    style D fill:#e6d5ff
    style E fill:#d5ffe6
    style H fill:#cce5ff
```

---

### Endpoint 4: `DELETE /api/v1/questions/{blog_id}` - Delete Blog

```mermaid
graph TD
    A[HTTP DELETE Request<br/>blog_id path] --> B[Router: delete_blog_by_id &lpar;questions_router.py&rpar;]
    B --> C[Verify Admin Key &lpar;auth.py&rpar;]
    C --> D[Validate ObjectId &lpar;questions_router.py&rpar;]
    D --> E[Repository: delete_blog &lpar;question_repository.py&rpar;]
    E --> F[Get Blog from MongoDB &lpar;question_repository.py&rpar;]
    F --> G[Extract blog_url &lpar;question_repository.py&rpar;]
    G --> H[Delete All Questions<br/>delete_many blog_url &lpar;question_repository.py&rpar;]
    H --> I[Delete Blog<br/>delete_one _id &lpar;question_repository.py&rpar;]
    I --> J[Return Status 200<br/>Deletion Counts &lpar;questions_router.py&rpar;]
    
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
    A[HTTP POST Request<br/>SearchSimilarRequest<br/>question_id + limit] --> B[Router: search_similar_blogs &lpar;search_router.py&rpar;]
    B --> C[Authenticate Publisher &lpar;auth.py&rpar;]
    C --> D[Repository: get_question_by_id &lpar;question_repository.py&rpar;]
    D --> E[MongoDB Query<br/>Find Question &lpar;question_repository.py&rpar;]
    E --> F{Question<br/>Found? &lpar;questions_router.py&rpar;}
    F -->|No| G[HTTPException 404 &lpar;questions_router.py&rpar;]
    F -->|Yes| H[Get blog_url from Question &lpar;search_router.py&rpar;]
    H --> I[Validate Domain &lpar;auth_service.py&rpar;]
    I --> J[Repository: increment_question_click_count &lpar;question_repository.py&rpar;]
    J --> K[MongoDB Atomic Update<br/>$inc click_count]
    K --> L[Get Embedding from Question &lpar;search_router.py&rpar;]
    L --> M{Embedding<br/>Exists?}
    M -->|No| N[HTTPException 400]
    M -->|Yes| O[Repository: search_similar_blogs &lpar;question_repository.py&rpar;]
    O --> P[MongoDB Vector Search<br/>Cosine Similarity]
    P --> Q[Filter by Domain &lpar;question_repository.py&rpar;]
    Q --> R[Sort by Similarity Score &lpar;question_repository.py&rpar;]
    R --> S[Limit Results &lpar;question_repository.py&rpar;]
    S --> T[Repository: _get_blogs_by_urls &lpar;question_repository.py&rpar;]
    T --> U[Batch Fetch Blog Docs &lpar;question_repository.py&rpar;]
    U --> V[Enrich with Blog IDs &lpar;search_router.py&rpar;]
    V --> W[Return Status 200<br/>Similar Blogs Array &lpar;search_router.py&rpar;]
    
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
    A[HTTP POST Request<br/>QARequest question] --> B[Router: ask_question &lpar;qa_router.py&rpar;]
    B --> C[Authenticate Publisher &lpar;auth.py&rpar;]
    C --> D{Question<br/>Empty?}
    D -->|Yes| E[HTTPException 400]
    D -->|No| F[Get LLM Service]
    F --> G[Extract chat_model<br/>from publisher.config]
    G --> H[Instantiate LLMContentGenerator<br/>Worker Service]
    H --> I[Service: answer_question &lpar;llm_content_generator.py&rpar;]
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
    A[HTTP POST Request<br/>PublisherCreateRequest] --> B[Router: onboard_publisher &lpar;publishers_router.py&rpar;]
    B --> C[Verify Admin Key &lpar;auth.py&rpar;]
    C --> D[Instantiate PublisherService]
    D --> E[Service: onboard_publisher &lpar;publisher_service.py&rpar;]
    E --> F[Repository: get_publisher_by_domain &lpar;publisher_repository.py&rpar;]
    F --> G[PostgreSQL Query<br/>SELECT by domain]
    G --> H{Publisher<br/>Exists?}
    H -->|Yes| I[HTTPException 409]
    H -->|No| J[Build Publisher Model]
    J --> K[Extract Config Dict]
    K --> L[Add Widget Config]
    L --> M[Repository: create_publisher &lpar;publisher_repository.py&rpar;]
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
    A[HTTP GET Request<br/>blog_url query<br/>NO AUTH] --> B[Router: get_publisher_metadata &lpar;publishers_router.py&rpar;]
    B --> C[Extract Domain &lpar;publishers_router.py&rpar;]
    C --> D[Instantiate PublisherService]
    D --> E[Service: get_publisher_metadata &lpar;publisher_service.py&rpar;]
    E --> F[Repository: get_publisher_by_domain &lpar;publisher_repository.py&rpar;<br/>allow_subdomain=true]
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

