# BlogProcessingService Refactoring Plan

## Current State
- `BlogProcessingService` is 865 lines with 11+ responsibilities (SRP violation)
- `process_job()` method is 676 lines (God Method anti-pattern)

## Target Structure

### Services to Extract:

1. ✅ **ContentRetrievalService** (created)
   - Responsibility: Fetch/cache blog content
   - Methods: `get_blog_content()`

2. ✅ **ThresholdService** (created)
   - Responsibility: Check processing thresholds
   - Methods: `should_process_blog()`

3. 🔄 **LLMGenerationService** (to create)
   - Responsibility: All LLM operations
   - Methods:
     - `generate_summary()` - Generate and parse summary
     - `generate_questions()` - Generate and parse questions
     - `generate_embeddings()` - Generate embeddings for summary + questions

4. 🔄 **BlogProcessingOrchestrator** (to create)
   - Responsibility: Orchestrate the processing pipeline
   - Uses all above services
   - Handles job status, error handling, metrics tracking

5. 🔄 **PublisherUsageService** (optional - can stay in orchestrator)
   - Responsibility: Track publisher usage
   - Methods: `track_usage()`, `release_slot()`

### Final Structure:

```
services/
├── blog_processing_service.py (refactored - uses orchestrator)
├── blog_processing_orchestrator.py (NEW - main coordinator)
├── content_retrieval_service.py (NEW - content fetching)
├── threshold_service.py (NEW - threshold checking)
├── llm_generation_service.py (NEW - LLM operations)
└── publisher_usage_service.py (NEW - optional, usage tracking)
```

## Benefits

1. **Single Responsibility**: Each service has one clear purpose
2. **Testability**: Each service can be tested independently
3. **Maintainability**: Changes to one concern don't affect others
4. **Reusability**: Services can be reused in other contexts
5. **Readability**: Smaller, focused files are easier to understand

