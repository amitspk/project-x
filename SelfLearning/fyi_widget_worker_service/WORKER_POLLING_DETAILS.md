# Worker Service Polling Loop - Detailed Analysis

## Overview

The worker service uses a **continuous polling loop** (not a traditional cron job) that runs indefinitely while the service is active. It polls for jobs from MongoDB, processes them, and maintains background tasks for metrics collection.

---

## Architecture

The worker service is **always running** and continuously polling. It's not a scheduled cron job - it's a long-running service that:

1. Polls MongoDB for pending jobs
2. Processes jobs immediately when found
3. Runs background tasks for metrics collection
4. Handles graceful shutdown via signals

---

## Main Polling Loop (`poll_loop()`)

**Location:** `worker.py:174`

### Purpose
Continuously polls MongoDB for queued jobs and processes them one at a time.

### Flow Diagram

```
┌─────────────────────────────────────────────┐
│         poll_loop() Starts                  │
│   (Called once when worker.start() runs)    │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│  Start Background Tasks (asyncio.create_)   │
│  1. update_uptime() - every 10 seconds      │
│  2. update_queue_size() - every 30 seconds  │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
        ┌─────────────────┐
        │  Main Loop      │
        │  while running  │
        └────────┬────────┘
                 │
                 ▼
    ┌────────────────────────┐
    │ Increment poll counter │
    │ poll_iterations_total  │
    └────────┬───────────────┘
             │
             ▼
    ┌─────────────────────────────┐
    │ get_next_queued_job()       │
    │ (Queries MongoDB for        │
    │  status="pending" job)      │
    └────────┬────────────────────┘
             │
        ┌────┴────┐
        │         │
        │ Job     │ No Job
        │ Found?  │
        │         │
        ▼         ▼
┌───────────┐   ┌──────────────────────┐
│ Process   │   │ Sleep                │
│ Job:      │   │ poll_interval_seconds│
│           │   │ (default: 5 seconds) │
│ 1. Extract│   └──────────┬───────────┘
│    domain │              │
│ 2. Record │              │
│    metric │              │
│ 3. Call   │              │
│    process_job()         │
│           │              │
└─────┬─────┘              │
      │                    │
      └──────────┬─────────┘
                 │
                 │ (Loop continues)
                 ▼
          ┌──────────────┐
          │ Back to top  │
          │ of loop      │
          └──────┬───────┘
                 │
          [Exception?]
                 │
                 ▼
      ┌──────────────────────┐
      │ Log error            │
      │ Increment            │
      │ poll_errors_total    │
      │ Sleep                │
      │ poll_interval_seconds│
      └──────────┬───────────┘
                 │
                 │ (Loop continues)
                 ▼
```

---

## Detailed Step-by-Step Breakdown

### 1. **Initialization Phase** (Once, at startup)

```python
async def poll_loop(self):
    """Main polling loop."""
    logger.info("🔄 Starting polling loop...")
```

**What happens:**
- Logs that polling loop is starting
- Sets up background tasks (before main loop)

---

### 2. **Background Task: Uptime Updater** (Runs every 10 seconds)

```python
async def update_uptime():
    """Periodically update uptime metric."""
    while self.running:
        worker_uptime_seconds.set(time.time() - self.start_time)
        await asyncio.sleep(10)
```

**Purpose:**
- Updates Prometheus gauge metric `worker_uptime_seconds`
- Tracks how long the worker has been running
- Updates every **10 seconds**

**Metrics:**
- `worker_uptime_seconds` (Gauge) - Current uptime in seconds

**Why it's separate:**
- Runs independently in background
- Doesn't block the main job polling loop
- Continuous monitoring of service health

---

### 3. **Background Task: Queue Size Updater** (Runs every 30 seconds)

```python
async def update_queue_size():
    """Periodically update queue size metrics."""
    while self.running:
        try:
            if self.job_repo:
                # Use single aggregation query instead of 4 separate count queries
                pipeline = [
                    {
                        "$group": {
                            "_id": "$status",
                            "count": {"$sum": 1}
                        }
                    }
                ]
                results = await self.job_repo.collection.aggregate(pipeline).to_list(length=None)
                
                # Initialize all statuses to 0
                status_counts = {
                    "pending": 0,
                    "processing": 0,
                    "completed": 0,
                    "failed": 0,
                    "skipped": 0
                }
                
                # Update with actual counts from aggregation
                for result in results:
                    status = result["_id"]
                    if status in status_counts:
                        status_counts[status] = result["count"]
                
                # Update metrics
                job_queue_size.labels(status="pending").set(status_counts["pending"])
                job_queue_size.labels(status="processing").set(status_counts["processing"])
                job_queue_size.labels(status="completed").set(status_counts["completed"])
                job_queue_size.labels(status="failed").set(status_counts["failed"])
                job_queue_size.labels(status="skipped").set(status_counts["skipped"])
        except Exception as e:
            logger.debug(f"Error updating queue size: {e}")
        await asyncio.sleep(30)
```

**Purpose:**
- Updates Prometheus gauge metrics for queue sizes by status
- Provides visibility into job queue state
- Updates every **30 seconds**

**Optimization:**
- Uses MongoDB aggregation pipeline (single query)
- Groups jobs by status and counts them
- More efficient than 5 separate count queries

**Metrics Updated:**
- `job_queue_size{status="pending"}` (Gauge)
- `job_queue_size{status="processing"}` (Gauge)
- `job_queue_size{status="completed"}` (Gauge)
- `job_queue_size{status="failed"}` (Gauge)
- `job_queue_size{status="skipped"}` (Gauge)

**Why it's separate:**
- Runs independently in background
- Doesn't slow down job polling
- Provides monitoring dashboard data
- Updates less frequently (30s) to reduce DB load

---

### 4. **Main Polling Loop** (Runs continuously)

```python
while self.running:
    try:
        poll_iterations_total.inc()
        
        # Get next job
        job = await self.job_repo.get_next_queued_job()
        
        if job:
            logger.info(f"📥 Found job: {job.job_id} ({job.blog_url})")
            # Extract domain for metrics using shared utility
            publisher_domain = extract_domain(job.blog_url)
            
            # Record job polled
            jobs_polled_total.labels(publisher_domain=publisher_domain).inc()
            
            await self.process_job(job)
        else:
            # No jobs, wait before next poll
            await asyncio.sleep(self.config.poll_interval_seconds)
        
    except Exception as e:
        poll_errors_total.inc()
        logger.error(f"❌ Error in poll loop: {e}", exc_info=True)
        await asyncio.sleep(self.config.poll_interval_seconds)
```

#### Step-by-Step Breakdown:

##### A. **Increment Poll Counter**
```python
poll_iterations_total.inc()
```
- Increments Prometheus counter metric
- Tracks total number of polling iterations
- Useful for monitoring poll frequency and detecting issues

**Metric:**
- `poll_iterations_total` (Counter) - Total poll loop iterations

---

##### B. **Query for Next Job**
```python
job = await self.job_repo.get_next_queued_job()
```

**What this does:**
- Queries MongoDB for a job with `status="pending"`
- Uses `JobRepository.get_next_queued_job()` method
- Returns `ProcessingJob` object or `None`

**Database Query:**
- Filters: `status == "pending"`
- Likely uses `find_one_and_update()` to atomically:
  1. Find a pending job
  2. Update status to "processing" (prevents race conditions)
  3. Return the job

**Why atomic:**
- Prevents multiple workers from picking the same job
- Ensures job locking before processing
- Handles concurrent worker scenarios

---

##### C. **If Job Found**

```python
if job:
    logger.info(f"📥 Found job: {job.job_id} ({job.blog_url})")
    publisher_domain = extract_domain(job.blog_url)
    jobs_polled_total.labels(publisher_domain=publisher_domain).inc()
    await self.process_job(job)
```

**Actions:**
1. **Log job found** - Records job ID and blog URL
2. **Extract domain** - Uses shared utility to extract publisher domain from blog URL
3. **Record metric** - Increments `jobs_polled_total` with publisher domain label
4. **Process job** - Calls `process_job()` which delegates to `BlogProcessingService`

**Metrics:**
- `jobs_polled_total{publisher_domain="..."}` (Counter) - Jobs polled per publisher

**Job Processing:**
- Delegates to `self.blog_processing_service.process_job(job)`
- This triggers the entire blog processing pipeline:
  - Content retrieval (crawl or cache)
  - Threshold checking
  - LLM generation (summary, questions, embeddings)
  - Database persistence
  - Publisher usage tracking

**Blocking Behavior:**
- `process_job()` is `await`ed, so the loop waits for job completion
- Only processes **one job at a time** (sequential processing)
- If job takes 5 minutes, next poll happens after 5 minutes

---

##### D. **If No Job Found**

```python
else:
    # No jobs, wait before next poll
    await asyncio.sleep(self.config.poll_interval_seconds)
```

**Actions:**
- Sleeps for `poll_interval_seconds` (default: 5 seconds)
- Then loops back to poll again

**Configuration:**
- `POLL_INTERVAL_SECONDS` environment variable (default: 5)
- Controlled by `WorkerServiceConfig.poll_interval_seconds`

**Why sleep:**
- Prevents busy-waiting when no jobs available
- Reduces MongoDB query load
- Balances responsiveness vs resource usage

---

##### E. **Error Handling**

```python
except Exception as e:
    poll_errors_total.inc()
    logger.error(f"❌ Error in poll loop: {e}", exc_info=True)
    await asyncio.sleep(self.config.poll_interval_seconds)
```

**Actions:**
1. **Increment error counter** - Tracks poll loop errors
2. **Log error** - Full exception traceback
3. **Sleep and retry** - Waits `poll_interval_seconds` before next poll

**Resilience:**
- Loop continues even if errors occur
- Doesn't crash the worker service
- Errors are logged for debugging
- Automatic retry on next iteration

**Metrics:**
- `poll_errors_total` (Counter) - Total poll loop errors

**Common Error Scenarios:**
- Database connection issues
- MongoDB query failures
- Network timeouts
- Unexpected exceptions

---

## Configuration

### Poll Interval
- **Environment Variable:** `POLL_INTERVAL_SECONDS`
- **Default:** 5 seconds
- **Config Class:** `WorkerServiceConfig.poll_interval_seconds`
- **Usage:** Sleep duration when no jobs found or on error

**Trade-offs:**
- **Lower interval (1-2s):** More responsive, higher DB load
- **Higher interval (10-30s):** Lower DB load, less responsive
- **Current (5s):** Good balance

---

## Metrics Collected

### Counter Metrics
1. **`poll_iterations_total`**
   - Total number of poll loop iterations
   - Incremented every iteration (regardless of job found)

2. **`jobs_polled_total{publisher_domain}`**
   - Total jobs polled from queue
   - Labeled by publisher domain
   - Incremented when job is found

3. **`poll_errors_total`**
   - Total errors in poll loop
   - Incremented on exceptions

### Gauge Metrics
1. **`worker_uptime_seconds`**
   - Current worker uptime in seconds
   - Updated every 10 seconds

2. **`job_queue_size{status}`**
   - Current queue size by status
   - Statuses: pending, processing, completed, failed, skipped
   - Updated every 30 seconds

---

## Job Processing Flow

When a job is found, the processing flow is:

```
poll_loop() finds job
    │
    ▼
process_job(job)
    │
    ▼
BlogProcessingService.process_job(job)
    │
    ▼
BlogProcessingOrchestrator.process_job(job)
    │
    ├─→ ContentRetrievalService.get_blog_content()
    │   ├─ Check MongoDB cache
    │   └─ If not found, crawl URL
    │
    ├─→ ThresholdService.should_process_blog()
    │   ├─ Check triggered_no_of_times
    │   ├─ Increment triggered count
    │   └─ Skip if threshold not met
    │
    ├─→ LLMGenerationService.generate_summary()
    │   └─ Generate summary with LLM
    │
    ├─→ LLMGenerationService.generate_questions()
    │   └─ Generate questions with LLM
    │
    ├─→ LLMGenerationService.generate_embeddings()
    │   ├─ Generate summary embedding
    │   └─ Generate question embeddings
    │
    ├─→ Save to MongoDB
    │   ├─ Save summary
    │   └─ Save questions
    │
    └─→ Track publisher usage
        └─ Update publisher stats
```

**Processing is sequential:**
- One job at a time (no parallel processing)
- Loop waits for job to complete before polling again
- If job fails, error is logged and loop continues

---

## Concurrency Model

### Current Implementation: **Sequential Processing**

- **Only one job processed at a time**
- Loop waits for `process_job()` to complete
- No parallel job processing

**Why Sequential:**
- Simpler error handling
- Prevents resource exhaustion
- Easier to debug
- Reduces race conditions

**Configuration Available:**
- `CONCURRENT_JOBS` config exists (default: 1)
- **BUT:** Not currently implemented in code!
- Could be enhanced to process multiple jobs in parallel

---

## Graceful Shutdown

The worker can be stopped gracefully:

```python
async def stop(self):
    """Stop the worker gracefully."""
    logger.info("🛑 Stopping worker...")
    self.running = False
    # Close DB connections
    if self.publisher_repo:
        await self.publisher_repo.disconnect()
    if self.db_manager:
        await self.db_manager.close()
```

**Signal Handling:**
```python
signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
```

**Shutdown Flow:**
1. Signal received (SIGINT/SIGTERM)
2. `signal_handler()` called
3. `worker.stop()` called
4. `self.running = False` (stops all loops)
5. Background tasks exit (check `self.running`)
6. Main loop exits
7. DB connections closed

**Current Job Handling:**
- If job is processing when shutdown occurs, it will complete
- No job cancellation mechanism
- Could be enhanced with timeout/cancellation

---

## Performance Characteristics

### Database Load
- **Poll Query:** 1 query every `poll_interval_seconds` (default: 5s)
- **Queue Size Query:** 1 aggregation query every 30 seconds
- **Uptime Update:** No DB query (in-memory calculation)

**Typical Load:**
- 12 poll queries per minute (when idle)
- 2 queue size queries per minute
- **Total: ~14 queries/minute when idle**

**When Processing:**
- Poll queries only when no job found
- Additional queries from job processing
- Queue size updates continue independently

### CPU/Memory Usage
- **Low when idle:** Just polling loop (sleeps most of the time)
- **High during processing:** LLM calls, crawling, DB operations
- **Background tasks:** Minimal overhead (update metrics)

---

## Comparison with Traditional Cron

| Aspect | Worker Service | Traditional Cron |
|--------|---------------|------------------|
| **Execution Model** | Continuous loop | Scheduled intervals |
| **Job Discovery** | Active polling | Time-based trigger |
| **Latency** | 0-5 seconds (when job added) | Fixed interval (e.g., every minute) |
| **Resource Usage** | Always running | Runs only when triggered |
| **Concurrency** | Sequential (1 job at a time) | Depends on cron implementation |
| **Job Queue** | Uses MongoDB job queue | Typically file-based or direct execution |
| **Error Handling** | Automatic retry on next poll | Depends on cron retry configuration |

**Key Differences:**
- Worker service is **always running** (daemon/service)
- Polls **continuously** instead of running on schedule
- More **responsive** to job additions (processes within seconds)
- Uses **database-backed job queue** instead of time-based triggers

---

## Potential Improvements

### 1. **Concurrent Job Processing**
**Current:** Sequential (1 job at a time)  
**Potential:** Process up to `CONCURRENT_JOBS` jobs in parallel

**Implementation:**
```python
# Use asyncio semaphore or task pool
semaphore = asyncio.Semaphore(config.concurrent_jobs)
tasks = []
while jobs_available:
    job = await get_next_queued_job()
    task = asyncio.create_task(process_job_with_semaphore(semaphore, job))
    tasks.append(task)
```

### 2. **Exponential Backoff on Errors**
**Current:** Fixed sleep interval on error  
**Potential:** Exponential backoff to reduce DB load during outages

### 3. **Job Priority/Ordering**
**Current:** FIFO (first-in-first-out)  
**Potential:** Priority queue or time-based ordering

### 4. **Health Checks**
**Current:** Uptime metric only  
**Potential:** Health check endpoint that verifies DB connectivity

### 5. **Job Timeout/Cancellation**
**Current:** Jobs run until completion  
**Potential:** Timeout mechanism for stuck jobs

---

## Summary

The worker service polling loop is a **continuous, event-driven system** that:

1. **Polls MongoDB** every 5 seconds (configurable) for pending jobs
2. **Processes jobs sequentially** (one at a time)
3. **Updates metrics** in background (uptime every 10s, queue size every 30s)
4. **Handles errors gracefully** (logs and retries)
5. **Supports graceful shutdown** (via signals)

**Key Characteristics:**
- ✅ Always running (daemon service)
- ✅ Low latency (processes jobs within seconds of addition)
- ✅ Resilient (continues on errors)
- ✅ Observable (comprehensive metrics)
- ⚠️ Sequential processing (only 1 job at a time)
- ⚠️ Fixed poll interval (no exponential backoff)

