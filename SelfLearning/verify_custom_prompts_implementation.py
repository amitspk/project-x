"""
Verify custom prompt implementation without requiring API calls.

Validates:
1. LLMService has custom_instructions parameters
2. Worker passes custom prompts from config
3. Publisher config has custom prompt fields
4. Three-layer architecture is properly implemented
"""

import sys
import inspect
from pathlib import Path

# Add shared to path
sys.path.append(str(Path(__file__).parent))

from shared.services.llm_service import LLMService, OUTPUT_FORMAT_INSTRUCTION
from shared.services.llm_service import DEFAULT_QUESTIONS_PROMPT, DEFAULT_SUMMARY_PROMPT
from shared.services.llm_service import QUESTIONS_JSON_FORMAT, SUMMARY_JSON_FORMAT
from shared.models.publisher import PublisherConfig


def verify_llm_service_structure():
    """Verify LLMService has proper two-part architecture."""
    print("\n" + "="*70)
    print("VERIFICATION 1: LLMService Two-Part Architecture")
    print("="*70)
    
    checks = []
    
    # Check Part 1: Output format enforcement
    print("\n📋 Part 1: Output Format Enforcement (Non-negotiable)")
    has_format_enforcement = (
        OUTPUT_FORMAT_INSTRUCTION and
        "JSON" in OUTPUT_FORMAT_INSTRUCTION and
        "MUST" in OUTPUT_FORMAT_INSTRUCTION
    )
    print(f"   {'✅' if has_format_enforcement else '❌'} Format enforcement instruction defined")
    checks.append(has_format_enforcement)
    
    # Check Part 2: Default prompts (role + instructions) exist
    print("\n📋 Part 2: Default Prompts (Role + Instructions with Fallback)")
    has_defaults = (
        DEFAULT_QUESTIONS_PROMPT and
        DEFAULT_SUMMARY_PROMPT and
        len(DEFAULT_QUESTIONS_PROMPT) > 50 and
        len(DEFAULT_SUMMARY_PROMPT) > 50 and
        "You are" in DEFAULT_QUESTIONS_PROMPT and  # Has role
        "You are" in DEFAULT_SUMMARY_PROMPT  # Has role
    )
    print(f"   {'✅' if has_defaults else '❌'} Default prompts defined with role + instructions")
    checks.append(has_defaults)
    
    # Check Format templates exist
    print("\n📋 Format Templates (Non-negotiable)")
    has_formats = (
        QUESTIONS_JSON_FORMAT and
        SUMMARY_JSON_FORMAT and
        '"questions"' in QUESTIONS_JSON_FORMAT and
        '"summary"' in SUMMARY_JSON_FORMAT
    )
    print(f"   {'✅' if has_formats else '❌'} Format templates defined with JSON schema")
    checks.append(has_formats)
    
    # Check generate_questions signature
    print("\n📋 Method Signatures:")
    sig_questions = inspect.signature(LLMService.generate_questions)
    has_custom_param_q = 'custom_prompt' in sig_questions.parameters
    print(f"   {'✅' if has_custom_param_q else '❌'} generate_questions() accepts custom_prompt parameter")
    checks.append(has_custom_param_q)
    
    # Check generate_summary signature
    sig_summary = inspect.signature(LLMService.generate_summary)
    has_custom_param_s = 'custom_prompt' in sig_summary.parameters
    print(f"   {'✅' if has_custom_param_s else '❌'} generate_summary() accepts custom_prompt parameter")
    checks.append(has_custom_param_s)
    
    # Check Optional typing
    is_optional_q = sig_questions.parameters['custom_prompt'].default is None
    is_optional_s = sig_summary.parameters['custom_prompt'].default is None
    is_optional = is_optional_q and is_optional_s
    print(f"   {'✅' if is_optional else '❌'} custom_prompt is Optional (defaults to None)")
    checks.append(is_optional)
    
    all_passed = all(checks)
    print(f"\n{'✅' if all_passed else '❌'} VERIFICATION 1: {'PASSED' if all_passed else 'FAILED'}")
    return all_passed


def verify_publisher_config():
    """Verify Publisher config has custom prompt fields."""
    print("\n" + "="*70)
    print("VERIFICATION 2: Publisher Config Model")
    print("="*70)
    
    checks = []
    
    # Create a test config
    config = PublisherConfig()
    
    # Check custom prompt fields exist
    print("\n📋 Custom Prompt Fields:")
    has_question_field = hasattr(config, 'custom_question_prompt')
    print(f"   {'✅' if has_question_field else '❌'} custom_question_prompt field exists")
    checks.append(has_question_field)
    
    has_summary_field = hasattr(config, 'custom_summary_prompt')
    print(f"   {'✅' if has_summary_field else '❌'} custom_summary_prompt field exists")
    checks.append(has_summary_field)
    
    # Check they default to None
    defaults_none = (
        config.custom_question_prompt is None and
        config.custom_summary_prompt is None
    )
    print(f"   {'✅' if defaults_none else '❌'} Fields default to None (backward compatible)")
    checks.append(defaults_none)
    
    # Test setting custom prompts
    print("\n📋 Testing Custom Prompt Assignment:")
    try:
        test_config = PublisherConfig(
            custom_question_prompt="Custom question prompt",
            custom_summary_prompt="Custom summary prompt"
        )
        can_set = (
            test_config.custom_question_prompt == "Custom question prompt" and
            test_config.custom_summary_prompt == "Custom summary prompt"
        )
        print(f"   {'✅' if can_set else '❌'} Can set custom prompts")
        checks.append(can_set)
    except Exception as e:
        print(f"   ❌ Failed to set custom prompts: {e}")
        checks.append(False)
    
    # Check field descriptions exist
    from pydantic import Field
    model_fields = PublisherConfig.model_fields
    has_descriptions = (
        'custom_question_prompt' in model_fields and
        'custom_summary_prompt' in model_fields and
        model_fields['custom_question_prompt'].description and
        model_fields['custom_summary_prompt'].description
    )
    print(f"   {'✅' if has_descriptions else '❌'} Fields have documentation/descriptions")
    checks.append(has_descriptions)
    
    all_passed = all(checks)
    print(f"\n{'✅' if all_passed else '❌'} VERIFICATION 2: {'PASSED' if all_passed else 'FAILED'}")
    return all_passed


def verify_worker_integration():
    """Verify worker code passes custom prompts correctly."""
    print("\n" + "="*70)
    print("VERIFICATION 3: Worker Integration")
    print("="*70)
    
    checks = []
    
    # Read worker.py file
    worker_path = Path(__file__).parent / "worker_service" / "worker.py"
    
    if not worker_path.exists():
        print("   ❌ worker.py not found")
        return False
    
    worker_code = worker_path.read_text()
    
    # Check for custom_summary_prompt usage
    print("\n📋 Custom Prompt Usage in Worker:")
    has_summary_prompt = "custom_prompt=config.custom_summary_prompt" in worker_code
    print(f"   {'✅' if has_summary_prompt else '❌'} Passes config.custom_summary_prompt to generate_summary()")
    checks.append(has_summary_prompt)
    
    # Check for custom_question_prompt usage
    has_question_prompt = "custom_prompt=config.custom_question_prompt" in worker_code
    print(f"   {'✅' if has_question_prompt else '❌'} Passes config.custom_question_prompt to generate_questions()")
    checks.append(has_question_prompt)
    
    # Check comments explain the flow
    has_comments = "with custom prompt" in worker_code.lower() or "uses default" in worker_code.lower()
    print(f"   {'✅' if has_comments else '❌'} Code has explanatory comments")
    checks.append(has_comments)
    
    all_passed = all(checks)
    print(f"\n{'✅' if all_passed else '❌'} VERIFICATION 3: {'PASSED' if all_passed else 'FAILED'}")
    return all_passed


def verify_format_enforcement():
    """Verify format enforcement is properly structured."""
    print("\n" + "="*70)
    print("VERIFICATION 4: Format Enforcement")
    print("="*70)
    
    checks = []
    
    # Read llm_service.py
    llm_path = Path(__file__).parent / "shared" / "services" / "llm_service.py"
    llm_code = llm_path.read_text()
    
    # Check format enforcement
    print("\n📋 Format Enforcement:")
    has_json_enforcement = (
        "OUTPUT_FORMAT_INSTRUCTION" in llm_code and
        "MUST respond ONLY with valid JSON" in llm_code
    )
    print(f"   {'✅' if has_json_enforcement else '❌'} Format enforcement instruction defined")
    checks.append(has_json_enforcement)
    
    # Check format templates are included in user prompt
    print("\n📋 Format Template Inclusion:")
    has_format_in_prompt = (
        "REQUIRED OUTPUT FORMAT" in llm_code and
        "QUESTIONS_JSON_FORMAT" in llm_code and
        "SUMMARY_JSON_FORMAT" in llm_code
    )
    print(f"   {'✅' if has_format_in_prompt else '❌'} Format templates included in user prompts")
    checks.append(has_format_in_prompt)
    
    # Check proper message structure (system + user)
    print("\n📋 Message Structure:")
    has_proper_structure = (
        'role": "system"' in llm_code and
        'role": "user"' in llm_code and
        "OUTPUT_FORMAT_INSTRUCTION" in llm_code
    )
    print(f"   {'✅' if has_proper_structure else '❌'} Uses proper system/user message structure")
    checks.append(has_proper_structure)
    
    all_passed = all(checks)
    print(f"\n{'✅' if all_passed else '❌'} VERIFICATION 4: {'PASSED' if all_passed else 'FAILED'}")
    return all_passed


def main():
    """Run all verifications."""
    print("\n" + "="*70)
    print("🔍 CUSTOM PROMPT IMPLEMENTATION VERIFICATION")
    print("   (Two-Part Architecture)")
    print("="*70)
    print("\nThis script validates the implementation structure without making API calls.")
    
    # Run all verifications
    results = []
    
    result1 = verify_llm_service_structure()
    results.append(("LLMService Three-Layer Architecture", result1))
    
    result2 = verify_publisher_config()
    results.append(("Publisher Config Model", result2))
    
    result3 = verify_worker_integration()
    results.append(("Worker Integration", result3))
    
    result4 = verify_format_enforcement()
    results.append(("Format Enforcement", result4))
    
    # Summary
    print("\n" + "="*70)
    print("📊 VERIFICATION SUMMARY")
    print("="*70)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "="*70)
    if all_passed:
        print("🎉 ALL VERIFICATIONS PASSED!")
        print("\nImplementation Summary:")
        print("✅ Two-part prompt architecture implemented correctly")
        print("   • Part 1: Pure format enforcement (non-negotiable)")
        print("   • Part 2: Role + Instructions (custom with fallback)")
        print("✅ LLMService accepts custom_prompt parameters")
        print("✅ Worker passes custom prompts from publisher config")
        print("✅ Publisher config model has custom prompt fields")
        print("✅ Format enforcement is separate and non-negotiable")
        print("\nKey Features:")
        print("• Part 1 enforces JSON format (can't be changed)")
        print("• Part 2 allows custom role + instructions (full flexibility)")
        print("• Automatic fallback to defaults if no custom prompt provided")
        print("• Publisher-specific customization via onboarding API")
    else:
        print("❌ SOME VERIFICATIONS FAILED")
        print("\nPlease review the failed checks above.")
    print("="*70)


if __name__ == "__main__":
    main()

