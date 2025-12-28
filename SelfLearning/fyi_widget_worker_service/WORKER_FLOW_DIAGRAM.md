# Worker Service Flow Diagrams

This document provides visual flow diagrams for the Worker Service, showing how jobs are polled and processed step-by-step.

## Color Legend

- **Light Blue (#E3F2FD)**: Worker/Orchestrator Layer (main coordination)
- **Orange (#FFF3E0)**: Service Layer (business logic services)
- **Purple (#F3E5F5)**: Repository Layer (data access)
- **Light Green (#E8F5E9)**: Database/External Layer (MongoDB, PostgreSQL, LLM APIs)
- **White (#FFFFFF)**: Decision points and utility functions

---

## 1. Worker Startup Flow

```mermaid
graph TD
    A[Worker Startup<br/>&lpar;run_worker.py&rpar;] --> B[Load Configuration<br/>&lpar;config.py&rpar;]
    B --> C[Initialize BlogProcessingWorker<br/>&lpar;worker.py&rpar;]
    C --> D[Connect to MongoDB<br/>&lpar;database.py&rpar;]
    D --> E[(MongoDB<br/>Connection)]
    E --> F[Connect to PostgreSQL<br/>&lpar;publisher_repository.py&rpar;]
    F --> G[(PostgreSQL<br/>Connection)]
    G --> H[Initialize BlogCrawler<br/>&lpar;blog_crawler.py&rpar;]
    H --> I[Initialize LLMContentGenerator<br/>&lpar;llm_content_generator.py&rpar;]
    I --> J[Initialize BlogContentRepository<br/>&lpar;blog_content_repository.py&rpar;]
    J --> K[Initialize JobRepository<br/>&lpar;job_repository.py&rpar;]
    K --> L[Initialize PublisherRepository<br/>&lpar;publisher_repository.py&rpar;]
    L --> M[Initialize ContentRetrievalService<br/>&lpar;content_retrieval_service.py&rpar;]
    M --> N[Initialize ThresholdService<br/>&lpar;threshold_service.py&rpar;]
    N --> O[Initialize LLMGenerationService<br/>&lpar;llm_generation_service.py&rpar;]
    O --> P[Initialize BlogProcessingService<br/>&lpar;blog_processing_service.py&rpar;]
    P --> Q[Initialize BlogProcessingOrchestrator<br/>&lpar;blog_processing_orchestrator.py&rpar;]
    Q --> R[Start Metrics Server<br/>&lpar;metrics_server.py&rpar;]
    R --> S[Start Polling Loop<br/>&lpar;worker.py&rpar;]

    style A fill:#E3F2FD
    style C fill:#E3F2FD
    style S fill:#E3F2FD
    style B fill:#FFF3E0
    style D fill:#FFF3E0
    style F fill:#FFF3E0
    style H fill:#FFF3E0
    style I fill:#FFF3E0
    style M fill:#FFF3E0
    style N fill:#FFF3E0
    style O fill:#FFF3E0
    style P fill:#FFF3E0
    style Q fill:#FFF3E0
    style R fill:#FFF3E0
    style J fill:#F3E5F5
    style K fill:#F3E5F5
    style L fill:#F3E5F5
    style E fill:#E8F5E9
    style G fill:#E8F5E9
```

---

## 2. Polling Loop Flow

```mermaid
graph TD
    A[Polling Loop Start<br/>&lpar;worker.py&rpar;] --> B[Start Background Tasks]
    B --> C[Update Uptime Metrics<br/>&lpar;worker.py&rpar;]
    B --> D[Update Queue Size Metrics<br/>&lpar;worker.py&rpar;]
    D --> E[Query Job Queue<br/>&lpar;job_repository.py&rpar;]
    E --> F[(MongoDB<br/>Job Queue)]
    F --> G{Job<br/>Found?}
    G -->|Yes| H[Extract Publisher Domain<br/>&lpar;url_utils.py&rpar;]
    H --> I[Record Job Polled Metric<br/>&lpar;metrics.py&rpar;]
    I --> J[Process Job<br/>&lpar;worker.py&rpar;]
    J --> K[Wait Poll Interval]
    G -->|No| K
    K --> L{Worker<br/>Running?}
    L -->|Yes| A
    L -->|No| M[Stop Worker<br/>&lpar;worker.py&rpar;]

    style A fill:#E3F2FD
    style J fill:#E3F2FD
    style M fill:#E3F2FD
    style E fill:#F3E5F5
    style H fill:#FFFFFF
    style G fill:#FFFFFF
    style L fill:#FFFFFF
    style F fill:#E8F5E9
```

---

## 3. Job Processing Flow (Complete Pipeline)

```mermaid
graph TD
    A[Process Job<br/>&lpar;blog_processing_service.py&rpar;] --> B[Delegates to Orchestrator<br/>&lpar;blog_processing_orchestrator.py&rpar;]
    B --> C[Start Processing Timer]
    C --> D[Extract Publisher Domain<br/>&lpar;url_utils.py&rpar;]
    D --> E[Increment Active Jobs Metric]
    E --> F[Normalize URL<br/>&lpar;url_utils.py&rpar;]
    F --> G[Get Publisher Config<br/>&lpar;blog_processing_orchestrator.py&rpar;]
    G --> H[Get Publisher by Domain<br/>&lpar;publisher_repository.py&rpar;]
    H --> I[(PostgreSQL<br/>Publishers)]
    I --> J{Publisher<br/>Found?}
    J -->|Yes| K[Use Publisher Config]
    J -->|No| L[Use Default Config]
    K --> M[Get Blog Content<br/>&lpar;content_retrieval_service.py&rpar;]
    L --> M
    M --> N[Check Threshold<br/>&lpar;threshold_service.py&rpar;]
    N --> O{Threshold<br/>Met?}
    O -->|No| P[Mark Job as Skipped<br/>&lpar;job_repository.py&rpar;]
    P --> Q[(MongoDB<br/>Job Queue)]
    Q --> R[Release Blog Slot<br/>&lpar;publisher_repository.py&rpar;]
    R --> S[Return]
    O -->|Yes| T[Generate Summary<br/>&lpar;llm_generation_service.py&rpar;]
    T --> U[Generate Questions<br/>&lpar;llm_generation_service.py&rpar;]
    U --> V[Generate Embeddings<br/>&lpar;llm_generation_service.py&rpar;]
    V --> W[Save Processing Results<br/>&lpar;blog_processing_orchestrator.py&rpar;]
    W --> X[Mark Job as Completed<br/>&lpar;job_repository.py&rpar;]
    X --> Y[(MongoDB<br/>Job Queue)]
    Y --> Z[Record Success Metrics]
    Z --> AA[Track Publisher Usage<br/>&lpar;blog_processing_orchestrator.py&rpar;]
    AA --> AB[Release Blog Slot<br/>&lpar;publisher_repository.py&rpar;]
    AB --> S

    style A fill:#E3F2FD
    style B fill:#E3F2FD
    style G fill:#E3F2FD
    style W fill:#E3F2FD
    style AA fill:#E3F2FD
    style M fill:#FFF3E0
    style N fill:#FFF3E0
    style T fill:#FFF3E0
    style U fill:#FFF3E0
    style V fill:#FFF3E0
    style H fill:#F3E5F5
    style P fill:#F3E5F5
    style X fill:#F3E5F5
    style R fill:#F3E5F5
    style AB fill:#F3E5F5
    style D fill:#FFFFFF
    style F fill:#FFFFFF
    style J fill:#FFFFFF
    style O fill:#FFFFFF
    style I fill:#E8F5E9
    style Q fill:#E8F5E9
    style Y fill:#E8F5E9
```

---

## 4. Get Blog Content Flow (Content Retrieval)

```mermaid
graph TD
    A[Get Blog Content<br/>&lpar;content_retrieval_service.py&rpar;] --> B[Normalize URL<br/>&lpar;url_utils.py&rpar;]
    B --> C[Check Cache: Get Blog by URL<br/>&lpar;blog_content_repository.py&rpar;]
    C --> D[(MongoDB<br/>raw_blog_content)]
    D --> E{Blog<br/>Cached?}
    E -->|Yes| F{Content<br/>Valid?}
    F -->|Yes| G[Return Cached Content]
    F -->|No| H[Log Warning: Invalid Content]
    E -->|No| I[Crawl URL<br/>&lpar;blog_crawler.py&rpar;]
    H --> I
    I --> J[Extract Content<br/>&lpar;blog_crawler.py&rpar;]
    J --> K{Content<br/>Valid?}
    K -->|No| L[Raise Crawl Error]
    K -->|Yes| M[Save Blog Content<br/>&lpar;blog_content_repository.py&rpar;]
    M --> N[(MongoDB<br/>raw_blog_content)]
    N --> O[Get Saved Blog Document<br/>&lpar;blog_content_repository.py&rpar;]
    O --> P[(MongoDB<br/>raw_blog_content)]
    P --> Q[Return Crawled Content]
    G --> R[Record Cache Hit Metric]
    Q --> S[Record Crawl Success Metric]

    style A fill:#FFF3E0
    style C fill:#F3E5F5
    style M fill:#F3E5F5
    style O fill:#F3E5F5
    style I fill:#FFF3E0
    style J fill:#FFF3E0
    style B fill:#FFFFFF
    style E fill:#FFFFFF
    style F fill:#FFFFFF
    style K fill:#FFFFFF
    style D fill:#E8F5E9
    style N fill:#E8F5E9
    style P fill:#E8F5E9
```

---

## 5. Check Threshold Flow

```mermaid
graph TD
    A[Check Threshold<br/>&lpar;threshold_service.py&rpar;] --> B[Get Triggered Count<br/>from Blog Document]
    B --> C{Triggered Count<br/>Field Exists?}
    C -->|No| D[Initialize to 0]
    C -->|Yes| E[Use Existing Count]
    D --> F[Get Threshold from Config]
    E --> F
    F --> G{triggered + 1<br/>&gt; threshold?}
    G -->|No| H[Increment Triggered Count<br/>&lpar;blog_content_repository.py&rpar;]
    H --> I[(MongoDB<br/>raw_blog_content)]
    I --> J[Mark Job as Skipped<br/>&lpar;job_repository.py&rpar;]
    J --> K[(MongoDB<br/>Job Queue)]
    K --> L[Return: Should Process = False]
    G -->|Yes| M[Increment Triggered Count<br/>&lpar;blog_content_repository.py&rpar;]
    M --> N[(MongoDB<br/>raw_blog_content)]
    N --> O[Return: Should Process = True]

    style A fill:#FFF3E0
    style H fill:#F3E5F5
    style M fill:#F3E5F5
    style J fill:#F3E5F5
    style C fill:#FFFFFF
    style G fill:#FFFFFF
    style I fill:#E8F5E9
    style K fill:#E8F5E9
    style N fill:#E8F5E9
```

---

## 6. Generate Summary Flow

```mermaid
graph TD
    A[Generate Summary<br/>&lpar;llm_generation_service.py&rpar;] --> B[Get Summary Model from Config]
    B --> C[Get Summary Prompt<br/>&lpar;Custom or Default&rpar;]
    C --> D[Call LLMContentGenerator<br/>&lpar;llm_content_generator.py&rpar;]
    D --> E[Build User Prompt<br/>&lpar;llm_content_generator.py&rpar;]
    E --> F[Build System Prompt<br/>&lpar;llm_prompts.py&rpar;]
    F --> G[Call LLMClient.generate_text<br/>&lpar;client.py&rpar;]
    G --> H[Route to Provider<br/>&lpar;factory.py&rpar;]
    H --> I{Provider<br/>Type?}
    I -->|OpenAI| J[OpenAI Provider<br/>&lpar;openai_provider.py&rpar;]
    I -->|Anthropic| K[Anthropic Provider<br/>&lpar;anthropic_provider.py&rpar;]
    I -->|Gemini| L[Gemini Provider<br/>&lpar;gemini_provider.py&rpar;]
    J --> M[(OpenAI<br/>API)]
    K --> N[(Anthropic<br/>API)]
    L --> O[(Gemini<br/>API)]
    M --> P[Return LLMGenerationResult]
    N --> P
    O --> P
    P --> Q[Parse JSON Response<br/>&lpar;llm_generation_service.py&rpar;]
    Q --> R{JSON<br/>Valid?}
    R -->|Yes| S[Extract Title, Summary, Key Points]
    R -->|No| T[Use Raw Text]
    S --> U[Record Success Metrics<br/>&lpar;metrics.py&rpar;]
    T --> U
    U --> V[Return Summary Data]

    style A fill:#FFF3E0
    style D fill:#FFF3E0
    style E fill:#FFF3E0
    style F fill:#FFF3E0
    style G fill:#FFF3E0
    style H fill:#FFF3E0
    style J fill:#FFF3E0
    style K fill:#FFF3E0
    style L fill:#FFF3E0
    style Q fill:#FFF3E0
    style I fill:#FFFFFF
    style R fill:#FFFFFF
    style M fill:#E8F5E9
    style N fill:#E8F5E9
    style O fill:#E8F5E9
```

---

## 7. Generate Questions Flow

```mermaid
graph TD
    A[Generate Questions<br/>&lpar;llm_generation_service.py&rpar;] --> B[Get Questions Model from Config]
    B --> C[Get Questions Prompt<br/>&lpar;Custom or Default&rpar;]
    C --> D[Call LLMContentGenerator<br/>&lpar;llm_content_generator.py&rpar;]
    D --> E[Build User Prompt<br/>&lpar;llm_content_generator.py&rpar;]
    E --> F[Build System Prompt<br/>&lpar;llm_prompts.py&rpar;]
    F --> G[Call LLMClient.generate_text<br/>&lpar;client.py&rpar;]
    G --> H[Route to Provider<br/>&lpar;factory.py&rpar;]
    H --> I{Provider<br/>Type?}
    I -->|OpenAI| J[OpenAI Provider<br/>&lpar;openai_provider.py&rpar;]
    I -->|Anthropic| K[Anthropic Provider<br/>&lpar;anthropic_provider.py&rpar;]
    I -->|Gemini| L[Gemini Provider<br/>&lpar;gemini_provider.py&rpar;]
    J --> M[(OpenAI<br/>API)]
    K --> N[(Anthropic<br/>API)]
    L --> O[(Gemini<br/>API)]
    M --> P[Return LLMGenerationResult]
    N --> P
    O --> P
    P --> Q[Parse JSON Response<br/>&lpar;llm_generation_service.py&rpar;]
    Q --> R{JSON<br/>Valid?}
    R -->|Yes| S[Extract Questions Array]
    R -->|No| T[Parse Fallback Format]
    S --> U[Validate Questions Count]
    T --> U
    U --> V[Record Success Metrics<br/>&lpar;metrics.py&rpar;]
    V --> W[Return Questions List]

    style A fill:#FFF3E0
    style D fill:#FFF3E0
    style E fill:#FFF3E0
    style F fill:#FFF3E0
    style G fill:#FFF3E0
    style H fill:#FFF3E0
    style J fill:#FFF3E0
    style K fill:#FFF3E0
    style L fill:#FFF3E0
    style Q fill:#FFF3E0
    style I fill:#FFFFFF
    style R fill:#FFFFFF
    style U fill:#FFFFFF
    style M fill:#E8F5E9
    style N fill:#E8F5E9
    style O fill:#E8F5E9
```

---

## 8. Save Processing Results Flow

```mermaid
graph TD
    A[Save Processing Results<br/>&lpar;blog_processing_orchestrator.py&rpar;] --> B[Save Summary<br/>&lpar;blog_content_repository.py&rpar;]
    B --> C[(MongoDB<br/>blog_summaries)]
    C --> D{Save<br/>Success?}
    D -->|No| E[Record DB Error Metric]
    E --> F[Raise Exception]
    D -->|Yes| G[Record DB Success Metric]
    G --> H[Prepare Questions for Batch Save]
    H --> I[Save Questions<br/>&lpar;blog_content_repository.py&rpar;]
    I --> J[(MongoDB<br/>questions)]
    J --> K{Save<br/>Success?}
    K -->|No| L[Record DB Error Metric]
    L --> F
    K -->|Yes| M[Record DB Success Metric]
    M --> N[Return Summary ID]

    style A fill:#E3F2FD
    style B fill:#F3E5F5
    style I fill:#F3E5F5
    style D fill:#FFFFFF
    style K fill:#FFFFFF
    style C fill:#E8F5E9
    style J fill:#E8F5E9
```

---

## 9. Job Failure Handling Flow

```mermaid
graph TD
    A[Job Processing Exception<br/>&lpar;blog_processing_orchestrator.py&rpar;] --> B[Extract Error Message]
    B --> C[Categorize Error Type<br/>&lpar;blog_processing_orchestrator.py&rpar;]
    C --> D{Error<br/>Type?}
    D -->|Crawl Error| E[crawl_error]
    D -->|LLM Error| F[llm_error]
    D -->|DB Error| G[db_error]
    D -->|Validation Error| H[validation_error]
    D -->|Other| I[unknown]
    E --> J[Record Failure Metrics<br/>&lpar;metrics.py&rpar;]
    F --> J
    G --> J
    H --> J
    I --> J
    J --> K[Mark Job as Failed<br/>&lpar;job_repository.py&rpar;]
    K --> L[(MongoDB<br/>Job Queue)]
    L --> M[Get Updated Job Status<br/>&lpar;job_repository.py&rpar;]
    M --> N[(MongoDB<br/>Job Queue)]
    N --> O{Job<br/>Status?}
    O -->|Permanently Failed| P[Release Blog Slot<br/>&lpar;publisher_repository.py&rpar;]
    O -->|Requeued| Q[Keep Slot Reserved]
    P --> R[Log Failure]
    Q --> R

    style A fill:#E3F2FD
    style C fill:#E3F2FD
    style K fill:#F3E5F5
    style M fill:#F3E5F5
    style P fill:#F3E5F5
    style D fill:#FFFFFF
    style O fill:#FFFFFF
    style L fill:#E8F5E9
    style N fill:#E8F5E9
```

---

## Layer Summary

### Worker/Orchestrator Layer (Light Blue)
- `worker.py` - Main worker class, polling loop
- `blog_processing_service.py` - Service wrapper
- `blog_processing_orchestrator.py` - Pipeline orchestration

### Service Layer (Orange)
- `content_retrieval_service.py` - Blog content retrieval
- `threshold_service.py` - Threshold checking
- `llm_generation_service.py` - LLM content generation
- `llm_content_generator.py` - LLM abstraction
- `blog_crawler.py` - Web crawling

### Repository Layer (Purple)
- `job_repository.py` - Job queue operations
- `publisher_repository.py` - Publisher config operations
- `blog_content_repository.py` - Blog content storage

### Database/External Layer (Light Green)
- MongoDB - Job queue, blog content, summaries, questions
- PostgreSQL - Publisher configurations
- LLM APIs - OpenAI, Anthropic, Gemini

