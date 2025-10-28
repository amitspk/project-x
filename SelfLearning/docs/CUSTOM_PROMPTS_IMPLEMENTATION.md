# Custom Prompts Implementation - Complete Guide

**Status**: ✅ Fully Implemented and Verified  
**Date**: October 27, 2025

## Overview

The publisher onboarding API now supports **custom prompts** for question generation and summarization. Publishers can customize the **content and style** of generated Q&A pairs and summaries without breaking the JSON format enforcement.

## Three-Layer Prompt Architecture

### Layer 1: System Prompt (Non-negotiable)
- **Purpose**: Defines AI role and enforces JSON format
- **Controlled by**: System (hardcoded in `LLMService`)
- **Customizable**: ❌ No - Format enforcement is critical

```python
SYSTEM_PROMPT_QUESTIONS = """You are an expert at creating educational Q&A content.
You MUST always respond with valid JSON in the exact format specified.
Never deviate from the JSON structure provided."""
```

### Layer 2: User Instructions (Customizable)
- **Purpose**: Guides content style, focus, and tone
- **Controlled by**: Publisher (via `custom_question_prompt` / `custom_summary_prompt`)
- **Customizable**: ✅ Yes - This is what publishers customize
- **Fallback**: Uses default instructions if not provided

```python
DEFAULT_QUESTIONS_INSTRUCTIONS = """Generate insightful question-answer pairs that:
1. Are diverse and cover key concepts from the content
2. Have comprehensive answers (50-100 words each)
3. Are engaging and start with varied interrogatives (What, How, Why, When, etc.)
4. Focus on practical understanding and key takeaways
5. Are educational and help readers deepen their understanding"""
```

### Layer 3: Format Template (Non-negotiable)
- **Purpose**: Explicit JSON schema enforcement
- **Controlled by**: System (appended to all prompts)
- **Customizable**: ❌ No - Schema must remain consistent

```python
QUESTIONS_JSON_FORMAT = """{
    "questions": [
        {
            "question": "Question text here?",
            "answer": "Detailed answer here.",
            "icon": "💡"
        }
    ]
}"""
```

## Publisher Onboarding API

### Endpoint: `POST /publishers/onboard`

**Request Example**:
```json
{
    "name": "Tech Blog Inc",
    "domain": "techblog.com",
    "email": "admin@techblog.com",
    "config": {
        "questions_per_blog": 7,
        "llm_model": "gpt-4o-mini",
        "temperature": 0.8,
        "daily_blog_limit": 50,
        "custom_question_prompt": "Generate technical question-answer pairs that focus on code examples and implementation details. Include how-to practical questions and emphasize best practices. Use technical terminology appropriate for developers.",
        "custom_summary_prompt": "Create a technical summary highlighting key technologies, frameworks, and implementation approaches. Focus on practical takeaways for developers."
    }
}
```

**Response**:
```json
{
    "status": "success",
    "status_code": 201,
    "message": "Publisher onboarded successfully",
    "result": {
        "success": true,
        "publisher": {
            "id": "pub_abc123",
            "name": "Tech Blog Inc",
            "domain": "techblog.com",
            "config": {
                "questions_per_blog": 7,
                "custom_question_prompt": "...",
                "custom_summary_prompt": "..."
            }
        },
        "api_key": "pk_live_abc123..."
    }
}
```

## Custom Prompt Examples

### Example 1: Technical Blog
```python
custom_question_prompt = """Generate highly technical question-answer pairs that:
1. Focus on implementation details and code examples
2. Include 'how-to' practical questions
3. Use technical terminology appropriate for senior developers
4. Emphasize best practices, common pitfalls, and performance considerations
5. Reference specific frameworks, APIs, and language features"""

custom_summary_prompt = """Create a technical summary that:
1. Highlights key technologies, frameworks, and APIs used
2. Focuses on practical takeaways and implementation approaches
3. Emphasizes architectural patterns and design decisions
4. Uses precise technical terminology"""
```

### Example 2: Marketing Blog
```python
custom_question_prompt = """Generate engaging question-answer pairs that:
1. Focus on actionable insights and marketing strategies
2. Include real-world examples and case studies
3. Use conversational, accessible language
4. Emphasize ROI, business impact, and measurable outcomes
5. Appeal to marketing professionals and business owners"""

custom_summary_prompt = """Create a business-focused summary that:
1. Emphasizes strategic insights and actionable recommendations
2. Highlights ROI implications and business value
3. Uses executive-level language
4. Focuses on impact, outcomes, and bottom-line results"""
```

### Example 3: Educational Content
```python
custom_question_prompt = """Generate educational question-answer pairs that:
1. Are suitable for beginners and students
2. Break down complex concepts into simple explanations
3. Use analogies and relatable examples
4. Build progressively from basic to advanced concepts
5. Include 'why' questions to deepen understanding"""

custom_summary_prompt = """Create a learning-focused summary that:
1. Identifies key concepts and learning objectives
2. Uses clear, accessible language
3. Provides context and foundational knowledge
4. Highlights prerequisite concepts and further reading"""
```

## Implementation Details

### Files Modified

1. **`shared/services/llm_service.py`**
   - Added three-layer prompt constants
   - Updated `generate_questions()` to accept `custom_instructions` parameter
   - Updated `generate_summary()` to accept `custom_instructions` parameter
   - Implemented format enforcement at system and user levels

2. **`worker_service/worker.py`**
   - Updated to pass `config.custom_question_prompt` to LLMService
   - Updated to pass `config.custom_summary_prompt` to LLMService
   - Added comments explaining custom prompt flow

3. **`shared/models/publisher.py`**
   - Enhanced documentation for `custom_question_prompt` field
   - Enhanced documentation for `custom_summary_prompt` field
   - Added detailed examples and explanations

### Key Features

✅ **Format Safety**: JSON structure enforced at multiple levels  
✅ **Flexibility**: Publishers can customize content style without breaking format  
✅ **Backward Compatible**: Works with or without custom prompts  
✅ **Clear Separation**: System handles format, publishers handle content  
✅ **Well-Documented**: Extensive examples and field descriptions  

## Flow Diagram

```
Publisher Onboarding
        ↓
Publisher Config (with custom prompts)
        ↓
Stored in PostgreSQL
        ↓
Worker fetches config by domain
        ↓
Worker passes custom prompts to LLMService
        ↓
LLMService builds three-layer prompt:
    1. System: Role + Format enforcement
    2. User: Custom/Default instructions + Content
    3. Format: JSON schema template
        ↓
OpenAI generates response
        ↓
Response parsed as JSON
        ↓
Questions/Summary saved to MongoDB
```

## Testing

### Verification Script

Run the verification script to validate implementation:

```bash
cd /Users/aks000z/Documents/personal_repo/SelfLearning
source venv/bin/activate
python verify_custom_prompts_implementation.py
```

**Expected Output**: All verifications should pass ✅

### Manual Testing

1. **Onboard a Publisher with Custom Prompts**:
```bash
curl -X POST http://localhost:8000/publishers/onboard \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: your-admin-key" \
  -d '{
    "name": "Test Publisher",
    "domain": "test.com",
    "email": "test@test.com",
    "config": {
      "custom_question_prompt": "Generate simple, beginner-friendly questions"
    }
  }'
```

2. **Process a Blog**: Use the check-and-load endpoint to process a blog from that domain

3. **Verify Output**: Check that questions reflect the custom prompt style while maintaining JSON format

## Benefits

### For Publishers
- **Brand Consistency**: Questions match their content style
- **Audience Targeting**: Tailor Q&A for specific reader demographics
- **Content Quality**: More relevant questions for their niche
- **Flexibility**: Easy to update prompts via API

### For System
- **Format Safety**: JSON parsing never breaks
- **Maintainability**: Format enforcement centralized in one place
- **Scalability**: Each publisher has independent customization
- **Reliability**: Fallback to defaults ensures system always works

## API Integration Example

### JavaScript/TypeScript
```typescript
interface PublisherConfig {
  questions_per_blog?: number;
  llm_model?: string;
  temperature?: number;
  custom_question_prompt?: string;
  custom_summary_prompt?: string;
}

async function onboardPublisher(
  name: string,
  domain: string,
  email: string,
  config: PublisherConfig
) {
  const response = await fetch('http://api.example.com/publishers/onboard', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Admin-Key': process.env.ADMIN_API_KEY,
    },
    body: JSON.stringify({ name, domain, email, config }),
  });
  
  return response.json();
}

// Usage
const result = await onboardPublisher(
  'Tech Blog',
  'techblog.com',
  'admin@techblog.com',
  {
    questions_per_blog: 7,
    custom_question_prompt: 'Generate technical Q&A with code examples...',
    custom_summary_prompt: 'Create technical summaries focused on implementation...',
  }
);

console.log('API Key:', result.result.api_key);
```

### Python
```python
import requests

def onboard_publisher(name: str, domain: str, email: str, config: dict):
    response = requests.post(
        'http://api.example.com/publishers/onboard',
        headers={
            'Content-Type': 'application/json',
            'X-Admin-Key': os.getenv('ADMIN_API_KEY'),
        },
        json={
            'name': name,
            'domain': domain,
            'email': email,
            'config': config,
        }
    )
    return response.json()

# Usage
result = onboard_publisher(
    name='Tech Blog',
    domain='techblog.com',
    email='admin@techblog.com',
    config={
        'questions_per_blog': 7,
        'custom_question_prompt': 'Generate technical Q&A with code examples...',
        'custom_summary_prompt': 'Create technical summaries focused on implementation...',
    }
)

print(f"API Key: {result['result']['api_key']}")
```

## Troubleshooting

### Issue: Custom prompts not being used

**Check**:
1. Publisher config has custom prompts set (query PostgreSQL)
2. Worker is fetching publisher config by domain
3. Worker is passing custom prompts to LLMService
4. Check worker logs for "CUSTOM instructions" messages

**Solution**: Review publisher onboarding request and verify config was saved correctly

### Issue: JSON parsing fails

**Possible Causes**:
- LLM doesn't follow format (rare with proper system prompts)
- Custom prompt includes conflicting instructions about format

**Solution**: 
- Review custom prompt for format-related instructions
- Ensure custom prompt focuses on content/style, not structure
- Check LLMService logs for the actual LLM response

### Issue: Questions don't reflect custom style

**Check**:
1. Custom prompt is actually being passed (check logs)
2. Custom prompt is clear and specific enough
3. LLM model supports the requested style

**Solution**: Refine custom prompt with more specific instructions

## Best Practices

### Writing Effective Custom Prompts

✅ **DO**:
- Focus on content style, tone, and focus areas
- Be specific about target audience
- Include examples of desired question types
- Mention specific terminology to use/avoid
- Keep prompts concise but descriptive (100-300 words)

❌ **DON'T**:
- Try to change the JSON format
- Include format-related instructions
- Use overly vague prompts like "make it good"
- Make prompts too long (>500 words)
- Include contradictory instructions

### Monitoring and Optimization

1. **Monitor generated content** for quality and style adherence
2. **Iterate on prompts** based on output quality
3. **A/B test** different prompt variations
4. **Track metrics** like user engagement with different prompt styles
5. **Update prompts** as content strategy evolves

## Future Enhancements

Potential improvements for future versions:

- [ ] Prompt templates library (pre-built prompts for common use cases)
- [ ] Prompt versioning (track prompt changes over time)
- [ ] A/B testing framework (compare different prompts)
- [ ] Analytics dashboard (measure prompt effectiveness)
- [ ] Prompt validation (check for problematic instructions)
- [ ] Multi-language support (custom prompts per language)

## Support

For questions or issues with custom prompts:

1. Review this documentation
2. Run the verification script
3. Check worker logs for prompt usage
4. Verify publisher config in PostgreSQL
5. Test with default prompts first, then add customization

---

**Implementation Status**: ✅ Complete and Verified  
**Last Updated**: October 27, 2025  
**Maintainer**: Engineering Team

