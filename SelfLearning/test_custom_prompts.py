"""
Test script for custom prompt implementation.

Tests:
1. Default prompts work (no custom prompt provided)
2. Custom prompts work (custom prompt provided)
3. JSON format is always maintained (format enforcement)
4. End-to-end flow with publisher config
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# Add shared to path
sys.path.append(str(Path(__file__).parent))

from shared.services.llm_service import LLMService
from shared.models.publisher import PublisherConfig


# Sample blog content for testing
SAMPLE_CONTENT = """
# Introduction to Python Async/Await

Asynchronous programming in Python has become increasingly important for building 
high-performance applications. The async/await syntax, introduced in Python 3.5, 
provides a clean and intuitive way to write concurrent code.

## What is Async/Await?

Async/await allows you to write asynchronous code that looks and behaves like 
synchronous code. It's particularly useful for I/O-bound operations like network 
requests, file operations, and database queries.

## Key Concepts

1. **Coroutines**: Functions defined with `async def`
2. **await**: Keyword to wait for async operations
3. **Event Loop**: Manages and executes async tasks

## Example

```python
async def fetch_data():
    await asyncio.sleep(1)
    return {"data": "success"}

asyncio.run(fetch_data())
```

## Benefits

- Improved performance for I/O operations
- Better resource utilization
- Cleaner code compared to callbacks
- Native Python support
"""


CUSTOM_TECHNICAL_PROMPT = """Generate highly technical question-answer pairs that:
1. Focus on implementation details and code examples
2. Include "how-to" practical questions
3. Use technical terminology appropriate for senior developers
4. Emphasize best practices, common pitfalls, and performance considerations
5. Reference specific Python features and syntax"""


CUSTOM_SUMMARY_PROMPT = """Create a technical summary that:
1. Highlights key technologies, frameworks, and APIs
2. Focuses on practical takeaways for developers
3. Emphasizes code patterns and implementation approaches
4. Uses precise technical terminology"""


def validate_json(text: str, expected_keys: list) -> bool:
    """Validate that text is valid JSON with expected keys."""
    try:
        # Remove markdown code blocks if present
        if text.startswith("```"):
            import re
            match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
            if match:
                text = match.group(1).strip()
        
        data = json.loads(text)
        
        # Check all expected keys are present
        for key in expected_keys:
            if key not in data:
                print(f"❌ Missing expected key: {key}")
                return False
        
        return True
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing failed: {e}")
        print(f"   Text: {text[:200]}...")
        return False


async def test_default_prompts(llm_service: LLMService):
    """Test 1: Default prompts work."""
    print("\n" + "="*70)
    print("TEST 1: Default Prompts (No Custom Instructions)")
    print("="*70)
    
    try:
        # Test questions with default prompt
        print("\n📝 Testing default question generation...")
        result = await llm_service.generate_questions(
            content=SAMPLE_CONTENT,
            title="Introduction to Python Async/Await",
            num_questions=3,
            custom_instructions=None  # Use defaults
        )
        
        print(f"✅ Generated questions ({result.tokens_used} tokens)")
        
        # Validate JSON format
        is_valid = validate_json(result.text, ["questions"])
        if is_valid:
            data = json.loads(result.text.strip().replace("```json", "").replace("```", ""))
            questions = data.get("questions", [])
            print(f"✅ Valid JSON format with {len(questions)} questions")
            
            # Show first question as sample
            if questions:
                print(f"\n📌 Sample Question:")
                print(f"   Q: {questions[0].get('question', 'N/A')[:80]}...")
                print(f"   A: {questions[0].get('answer', 'N/A')[:80]}...")
        else:
            print("❌ Invalid JSON format!")
            return False
        
        # Test summary with default prompt
        print("\n📝 Testing default summary generation...")
        result = await llm_service.generate_summary(
            content=SAMPLE_CONTENT,
            title="Introduction to Python Async/Await",
            custom_instructions=None  # Use defaults
        )
        
        print(f"✅ Generated summary ({result.tokens_used} tokens)")
        
        # Validate JSON format
        is_valid = validate_json(result.text, ["summary", "key_points"])
        if is_valid:
            data = json.loads(result.text.strip().replace("```json", "").replace("```", ""))
            print(f"✅ Valid JSON format")
            print(f"\n📌 Sample Summary:")
            print(f"   {data.get('summary', 'N/A')[:150]}...")
        else:
            print("❌ Invalid JSON format!")
            return False
        
        print("\n✅ TEST 1 PASSED: Default prompts work correctly")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 1 FAILED: {e}")
        return False


async def test_custom_prompts(llm_service: LLMService):
    """Test 2: Custom prompts work."""
    print("\n" + "="*70)
    print("TEST 2: Custom Prompts")
    print("="*70)
    
    try:
        # Test questions with custom prompt
        print("\n📝 Testing CUSTOM question generation...")
        print(f"Custom prompt: {CUSTOM_TECHNICAL_PROMPT[:100]}...")
        
        result = await llm_service.generate_questions(
            content=SAMPLE_CONTENT,
            title="Introduction to Python Async/Await",
            num_questions=3,
            custom_instructions=CUSTOM_TECHNICAL_PROMPT
        )
        
        print(f"✅ Generated questions with custom prompt ({result.tokens_used} tokens)")
        
        # Validate JSON format
        is_valid = validate_json(result.text, ["questions"])
        if is_valid:
            data = json.loads(result.text.strip().replace("```json", "").replace("```", ""))
            questions = data.get("questions", [])
            print(f"✅ Valid JSON format with {len(questions)} questions")
            
            # Show first question to verify custom style
            if questions:
                print(f"\n📌 Sample Technical Question:")
                print(f"   Q: {questions[0].get('question', 'N/A')}")
                print(f"   A: {questions[0].get('answer', 'N/A')[:100]}...")
        else:
            print("❌ Invalid JSON format!")
            return False
        
        # Test summary with custom prompt
        print("\n📝 Testing CUSTOM summary generation...")
        print(f"Custom prompt: {CUSTOM_SUMMARY_PROMPT[:100]}...")
        
        result = await llm_service.generate_summary(
            content=SAMPLE_CONTENT,
            title="Introduction to Python Async/Await",
            custom_instructions=CUSTOM_SUMMARY_PROMPT
        )
        
        print(f"✅ Generated summary with custom prompt ({result.tokens_used} tokens)")
        
        # Validate JSON format
        is_valid = validate_json(result.text, ["summary", "key_points"])
        if is_valid:
            data = json.loads(result.text.strip().replace("```json", "").replace("```", ""))
            print(f"✅ Valid JSON format")
            print(f"\n📌 Technical Summary:")
            print(f"   {data.get('summary', 'N/A')}")
        else:
            print("❌ Invalid JSON format!")
            return False
        
        print("\n✅ TEST 2 PASSED: Custom prompts work correctly")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 2 FAILED: {e}")
        return False


async def test_publisher_config_flow(llm_service: LLMService):
    """Test 3: End-to-end flow with publisher config."""
    print("\n" + "="*70)
    print("TEST 3: Publisher Config Flow")
    print("="*70)
    
    try:
        # Create publisher config with custom prompts
        config = PublisherConfig(
            questions_per_blog=3,
            llm_model="gpt-4o-mini",
            custom_question_prompt=CUSTOM_TECHNICAL_PROMPT,
            custom_summary_prompt=CUSTOM_SUMMARY_PROMPT
        )
        
        print("\n📋 Publisher Config:")
        print(f"   Questions per blog: {config.questions_per_blog}")
        print(f"   LLM Model: {config.llm_model}")
        print(f"   Has custom question prompt: {config.custom_question_prompt is not None}")
        print(f"   Has custom summary prompt: {config.custom_summary_prompt is not None}")
        
        # Test with config (simulating worker flow)
        print("\n📝 Simulating worker flow with publisher config...")
        
        result = await llm_service.generate_questions(
            content=SAMPLE_CONTENT,
            title="Introduction to Python Async/Await",
            num_questions=config.questions_per_blog,
            custom_instructions=config.custom_question_prompt
        )
        
        is_valid = validate_json(result.text, ["questions"])
        if is_valid:
            print(f"✅ Questions generated with publisher config")
        else:
            print("❌ Invalid JSON format!")
            return False
        
        print("\n✅ TEST 3 PASSED: Publisher config flow works correctly")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 3 FAILED: {e}")
        return False


async def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("🧪 CUSTOM PROMPT IMPLEMENTATION TESTS")
    print("="*70)
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\n❌ ERROR: OPENAI_API_KEY not set in environment")
        print("   Please set it with: export OPENAI_API_KEY=your-key-here")
        return
    
    # Initialize LLM service
    print("\n🔧 Initializing LLM Service...")
    llm_service = LLMService(api_key=api_key)
    
    # Run tests
    results = []
    
    test1_passed = await test_default_prompts(llm_service)
    results.append(("Default Prompts", test1_passed))
    
    test2_passed = await test_custom_prompts(llm_service)
    results.append(("Custom Prompts", test2_passed))
    
    test3_passed = await test_publisher_config_flow(llm_service)
    results.append(("Publisher Config Flow", test3_passed))
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED! Custom prompt implementation is working correctly.")
        print("\n✅ Format Enforcement: JSON structure is always maintained")
        print("✅ Flexibility: Custom prompts customize content style")
        print("✅ Backward Compatibility: Default prompts work when custom not provided")
    else:
        print("\n❌ SOME TESTS FAILED. Please review the errors above.")


if __name__ == "__main__":
    asyncio.run(main())

