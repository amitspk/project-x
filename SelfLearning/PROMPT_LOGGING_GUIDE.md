# Prompt Logging Guide

**Status**: ✅ Implemented  
**Date**: October 27, 2025

## Overview

Enhanced logging has been added to track which prompts (CUSTOM or DEFAULT) are being used during blog processing. This helps debug and verify that custom publisher prompts are being applied correctly.

## Logging Levels

### Level 1: Worker Service - Configuration Check
**Location**: `worker_service/worker.py`  
**Triggers**: At the start of blog processing, after fetching publisher config

```log
📋 Config: 5 questions, model: gpt-4o-mini
🎯 Prompts: Questions=CUSTOM, Summary=DEFAULT
   Custom Question Prompt (preview): You are a senior software engineer creating technical Q&A...
```

**What it shows**:
- Whether custom or default prompts are configured
- First 100 characters of custom prompts (if any)
- Quick overview at the job level

### Level 2: Worker Service - Generation Step
**Location**: `worker_service/worker.py`  
**Triggers**: Before calling LLM service for summary/questions

```log
📝 Generating summary with DEFAULT prompt...
✅ Summary generated (342 tokens)

❓ Generating 5 questions with CUSTOM prompt...
✅ Questions generated (1245 tokens)
```

**What it shows**:
- Exactly which prompt type is being used for each generation step
- Token usage for each call

### Level 3: LLM Service - Detailed Prompt Info
**Location**: `shared/services/llm_service.py`  
**Triggers**: Inside LLM service when generating content

```log
📝 Generating summary with CUSTOM prompt (length: 456 chars)
   Custom prompt preview: You are a technical writer for developers. Create summaries that highlight implementation details, code patterns...

❓ Generating 5 questions with CUSTOM prompt (length: 523 chars)
   Custom prompt preview: You are a senior software engineer. Generate questions that focus on implementation details and best practices...
```

**What it shows**:
- Full character length of custom prompts
- First 150 characters preview of the actual custom prompt
- Allows verification that correct prompts are being passed

## Example Log Flow

### Scenario: Publisher with Custom Prompts

```log
# 1. Job Start
🔄 Processing job 12345: https://techblog.com/post

# 2. Configuration Loading
📋 Config: 5 questions, model: gpt-4o-mini
🎯 Prompts: Questions=CUSTOM, Summary=CUSTOM
   Custom Question Prompt (preview): You are an expert software engineer. Generate questions that...
   Custom Summary Prompt (preview): You are a technical content writer. Create summaries focusing on...

# 3. Crawling
🕷️  Crawling: https://techblog.com/post
✅ Crawled successfully: 3500 chars

# 4. Summary Generation
📝 Generating summary with CUSTOM prompt...
📝 Generating summary with CUSTOM prompt (length: 456 chars)
   Custom prompt preview: You are a technical content writer. Create summaries focusing on...
✅ Summary generated (342 tokens)

# 5. Questions Generation
❓ Generating 5 questions with CUSTOM prompt...
❓ Generating 5 questions with CUSTOM prompt (length: 523 chars)
   Custom prompt preview: You are an expert software engineer. Generate questions that...
✅ Questions generated (1245 tokens)

# 6. Storage
💾 Storing results...
✅ Job completed successfully
```

### Scenario: Publisher with Default Prompts

```log
# 1. Job Start
🔄 Processing job 67890: https://blog.example.com/article

# 2. Configuration Loading
📋 Config: 3 questions, model: gpt-4o-mini
🎯 Prompts: Questions=DEFAULT, Summary=DEFAULT

# 3. Summary Generation
📝 Generating summary with DEFAULT prompt...
📝 Generating summary with DEFAULT prompt (fallback)
✅ Summary generated (298 tokens)

# 4. Questions Generation
❓ Generating 3 questions with DEFAULT prompt...
❓ Generating 3 questions with DEFAULT prompt (fallback)
✅ Questions generated (876 tokens)
```

## How to View Logs

### Docker Logs
```bash
# Worker service logs (shows all levels)
docker logs -f blog-qa-worker

# Follow logs in real-time
docker logs -f blog-qa-worker --tail 100

# Search for prompt-related logs
docker logs blog-qa-worker 2>&1 | grep "🎯 Prompts"
docker logs blog-qa-worker 2>&1 | grep "CUSTOM prompt"
```

### Filter by Prompt Type
```bash
# Find jobs using custom prompts
docker logs blog-qa-worker 2>&1 | grep "CUSTOM"

# Find jobs using default prompts
docker logs blog-qa-worker 2>&1 | grep "DEFAULT"

# See custom prompt previews
docker logs blog-qa-worker 2>&1 | grep "Custom prompt preview"
```

## Debugging Tips

### 1. Verify Custom Prompts Are Being Used
```bash
# Check if your publisher's custom prompts are active
docker logs blog-qa-worker 2>&1 | grep "🎯 Prompts" | tail -5
```

### 2. See Actual Prompt Content
```bash
# View prompt previews
docker logs blog-qa-worker 2>&1 | grep "Custom prompt preview"
```

### 3. Track Specific Job
```bash
# Follow a specific job by URL
docker logs blog-qa-worker 2>&1 | grep "techblog.com/post"
```

## Code Locations

### Worker Service Logging
**File**: `worker_service/worker.py`  
**Lines**: ~175-186 (config check), ~197-198 (summary), ~216-217 (questions)

### LLM Service Logging
**File**: `shared/services/llm_service.py`  
**Lines**: ~135-139 (summary), ~214-218 (questions)

## Summary

The new logging provides three levels of visibility:
1. **Quick overview** at job start (CUSTOM/DEFAULT indicators)
2. **Step-by-step** tracking during processing
3. **Detailed preview** of actual prompt content

This makes it easy to verify that custom prompts are working correctly and debug any issues with prompt configuration.

---

**Last Updated**: October 27, 2025  
**Status**: Production Ready ✅

