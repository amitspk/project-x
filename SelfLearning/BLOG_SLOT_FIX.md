# Blog Slot Reservation Fix

## Problem Identified

The `blog_slots_reserved` count was getting stuck because slots were being released incorrectly when jobs failed and were requeued for retry.

## Root Cause

When a job failed:
1. The worker would call `mark_job_failed()` which could either:
   - Requeue the job (status = `QUEUED`) if under max retries
   - Permanently fail the job (status = `FAILED`) if max retries exceeded
2. **The worker ALWAYS released the slot**, regardless of whether the job was requeued or permanently failed
3. When a requeued job was picked up again, it didn't reserve a new slot
4. This caused the slot count to become incorrect (slots released but jobs still in queue)

## Fix Applied

**File**: `SelfLearning/fyi_widget_worker_service/worker.py`

**Change**: Modified the error handling to only release the blog slot when a job is **permanently failed**, not when it's requeued for retry.

- If job is requeued → Keep slot reserved (job will retry)
- If job is permanently failed → Release slot (job won't retry)

## Remaining Edge Cases

The following scenarios can still cause stuck slots (but are less common):

1. **Jobs stuck in "processing" state**: If a worker crashes while processing a job, the job stays in "processing" and the slot is never released.
   - **Mitigation**: Add a cleanup job that detects jobs in "processing" state for > X hours and releases their slots

2. **Jobs created but never picked up**: If jobs are created while the worker is down, slots stay reserved.
   - **Mitigation**: Add a cleanup job that detects jobs in "queued" state for > X hours and releases their slots

3. **Missing publisher_id**: If `publisher_id` is None, slots can't be released.
   - **Current mitigation**: Worker tries to find publisher by domain as fallback
   - **Note**: This should be rare since API endpoints now set `publisher_id` when creating jobs

## Testing Recommendations

1. Test job failure and requeue → Slot should stay reserved
2. Test job permanent failure → Slot should be released
3. Test job success → Slot should be released and `total_blogs_processed` incremented
4. Monitor `blog_slots_reserved` count over time to ensure it doesn't get stuck

## Future Improvements

Consider adding a periodic cleanup job that:
- Finds jobs in "processing" state for > 2 hours → Release slot and mark as failed
- Finds jobs in "queued" state for > 24 hours → Release slot (optional, may indicate worker issues)

