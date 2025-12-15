# Check-and-Load API Flow Diagram

```mermaid
flowchart TD
    Start([API Call: GET /api/v1/questions/check-and-load?blog_url=...]) --> Auth{Authentication Check}
    
    Auth -->|Invalid API Key| Error1[Return 401 Unauthorized]
    Auth -->|Valid API Key| Normalize[Normalize URL<br/>- Remove www<br/>- Normalize protocol<br/>- Remove trailing slash]
    
    Normalize --> ValidateDomain{Validate Blog URL Domain<br/>matches Publisher Domain}
    
    ValidateDomain -->|Domain Mismatch| Error2[Return 403 Forbidden]
    ValidateDomain -->|Domain Matches| Step1[STEP 1: Check if Questions Exist]
    
    Step1 --> QuestionsExist{Questions Found<br/>in MongoDB?}
    
    QuestionsExist -->|YES: Questions Found| FastPath[FAST PATH ⚡<br/>- Randomize questions<br/>- Get blog metadata<br/>- Format response]
    FastPath --> ReturnReady[Return 200 OK<br/>processing_status: 'ready'<br/>+ questions array<br/>+ blog_info]
    
    QuestionsExist -->|NO: No Questions| Step2[STEP 2: Check for Existing Job]
    
    Step2 --> CheckActiveJob{Find Job with Status:<br/>'pending' OR 'processing'<br/>for this URL}
    
    CheckActiveJob -->|Found: status='processing'| ReturnProcessing1[Return 200 OK<br/>processing_status: 'processing'<br/>job_id: existing_job_id<br/>message: 'Blog is currently being processed']
    
    CheckActiveJob -->|Found: status='pending'| ReturnProcessing2[Return 200 OK<br/>processing_status: 'processing'<br/>job_id: existing_job_id<br/>message: 'Blog processing is queued']
    
    CheckActiveJob -->|NOT Found<br/>No active job| Step3[STEP 3: Create New Job]
    
    Step3 --> CheckWhitelist{URL Whitelist Check<br/>ensure_url_whitelisted}
    
    CheckWhitelist -->|Not Whitelisted| Error3[Return 403 Forbidden]
    
    CheckWhitelist -->|Whitelisted| ReserveSlot[Reserve Blog Slot<br/>publisher_repo.reserve_blog_slot]
    
    ReserveSlot --> SlotLimit{Slot Limit Check<br/>blog_slots_reserved < max_blogs_per_day?}
    
    SlotLimit -->|Limit Exceeded| ReleaseSlot1[Release Reserved Slot<br/>processed=False]
    ReleaseSlot1 --> Error4[Return 403 Forbidden<br/>UsageLimitExceededError]
    
    SlotLimit -->|Slot Available| CreateJob[Create Job in MongoDB<br/>job_repo.create_job]
    
    CreateJob --> CheckDuplicate{Check for Duplicate<br/>Job with status:<br/>'queued' OR 'processing'?}
    
    CheckDuplicate -->|Duplicate Found| ReturnExisting[Return existing job_id<br/>No new job created]
    
    CheckDuplicate -->|No Duplicate| InsertJob[Insert New Job Document<br/>Status: 'queued'<br/>+ publisher_id<br/>+ config]
    
    InsertJob --> Success[Return 200 OK<br/>processing_status: 'not_started'<br/>job_id: new_job_id<br/>message: 'Processing started - check back in 30-60 seconds']
    
    CreateJob -->|Exception| HandleError{Exception Type?}
    
    HandleError -->|UsageLimitExceededError| ReleaseSlot2[Release Reserved Slot<br/>processed=False]
    ReleaseSlot2 --> Error5[Return 403 Forbidden]
    
    HandleError -->|Other Exception| ReleaseSlot3[Release Reserved Slot<br/>processed=False]
    ReleaseSlot3 --> Error6[Return 500 Internal Server Error]
    
    style Start fill:#e1f5ff
    style FastPath fill:#d4edda
    style ReturnReady fill:#d4edda
    style ReturnProcessing1 fill:#fff3cd
    style ReturnProcessing2 fill:#fff3cd
    style Success fill:#d4edda
    style Error1 fill:#f8d7da
    style Error2 fill:#f8d7da
    style Error3 fill:#f8d7da
    style Error4 fill:#f8d7da
    style Error5 fill:#f8d7da
    style Error6 fill:#f8d7da
```

## Key Conditions and Decision Points

### 1. Authentication & Authorization
- **Condition**: Valid X-API-Key header required
- **Failure**: Returns 401 Unauthorized

### 2. Domain Validation
- **Condition**: Blog URL domain must match publisher's registered domain
- **Failure**: Returns 403 Forbidden

### 3. Questions Existence Check
- **Condition**: `questions.length > 0` in MongoDB
- **Success Path**: Returns questions immediately (FAST PATH)
- **Failure Path**: Proceeds to job check

### 4. Active Job Check
- **Condition**: Job exists with status `'pending'` OR `'processing'`
- **Note**: `'skipped'` and `'failed'` jobs are NOT considered active
- **Success**: Returns existing job status
- **Failure**: Proceeds to create new job

### 5. URL Whitelist Check
- **Condition**: URL must be in publisher's `whitelisted_blog_urls` (if configured)
- **Failure**: Returns 403 Forbidden

### 6. Slot Reservation
- **Condition**: `blog_slots_reserved < max_blogs_per_day`
- **Failure**: Returns 403 Forbidden (UsageLimitExceededError)
- **Success**: Increments `blog_slots_reserved`

### 7. Duplicate Job Prevention
- **Condition**: Check for existing job with status `'queued'` OR `'processing'`
- **Note**: `'skipped'` jobs can be immediately requeued (not checked)
- **Success**: Returns existing job_id (no duplicate created)
- **Failure**: Creates new job

## Important Notes

1. **Skipped Jobs**: Can be immediately requeued (no delay/wait period)
2. **Failed Jobs**: Can be requeued (treated same as no job)
3. **Slot Management**: 
   - Reserved when job is created
   - Released when job is completed, failed, or skipped
4. **Error Handling**: If job creation fails after slot reservation, slot is automatically released

## Response States

- `ready`: Questions exist and are returned
- `processing`: Job is pending or currently processing
- `not_started`: New job was just created

