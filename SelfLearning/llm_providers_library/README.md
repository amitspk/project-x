# LLM Providers Library

A standalone, reusable library for interacting with multiple LLM providers (OpenAI, Anthropic, Gemini).

## Design Philosophy

**This library provides generic LLM provider interactions - no business logic.**

The library focuses solely on:
- Provider abstraction (OpenAI, Anthropic, Gemini)
- Low-level API interactions
- Model routing and configuration
- Generic text generation and embeddings

**Business logic** (prompt engineering, JSON formatting, domain-specific methods) should be implemented by clients using this library.

## Features

- Multi-provider support (OpenAI, Anthropic, Gemini)
- Clean, generic API (`generate_text`, `generate_embedding`)
- Automatic provider routing based on model name
- Configurable via simple config objects
- Zero dependencies on application-specific code
- Provider-specific features supported via kwargs (e.g., `use_grounding` for Gemini)

## Installation

Install in development mode:

```bash
cd llm_providers_library
pip install -e .
```

Or install from a directory:

```bash
pip install -e /path/to/llm_providers_library
```

## Usage

### Basic Usage

```python
from llm_providers_library import LLMClient, LLMConfig

# Create config
config = LLMConfig(
    api_key="your-api-key",  # Optional, can use env vars
    model="gpt-4o-mini",
    temperature=0.7,
    max_tokens=2000
)

# Create client
client = LLMClient(config)

# Generate text (generic - you provide the prompts)
result = await client.generate_text(
    prompt="What is Python?",
    system_prompt="You are a helpful assistant."
)
print(result.text)
```

### Provider-Specific Features

Some providers support additional features via kwargs:

```python
# Gemini grounding (Google Search)
result = await client.generate_text(
    prompt="What is the latest news about AI?",
    use_grounding=True  # Gemini-specific feature
)
```

### Embeddings

```python
# Generate embeddings
embedding_result = await client.generate_embedding("Your text here")
print(embedding_result.embedding)
```

## Architecture

The library is structured as follows:

```
llm_providers_library/
├── client.py           # LLMClient - main entry point
├── client_config.py    # LLMConfig - configuration
├── models.py           # LLMGenerationResult, EmbeddingResult
├── model_config.py     # Model-to-provider mappings
└── providers/
    ├── base.py         # Abstract base provider
    ├── openai_provider.py
    ├── anthropic_provider.py
    ├── gemini_provider.py
    └── factory.py      # Provider factory
```

## Implementing Business Logic

This library is **generic** - it doesn't contain business-specific logic like "generate_summary" or "generate_questions". 

Clients should implement their own business logic using the generic `generate_text()` method:

```python
# Example: Business-specific summary generation
async def generate_summary(content: str, title: str):
    # Build your business-specific prompt
    prompt = f"""Summarize the following content:

Title: {title}
Content: {content}

Format: JSON with 'summary' and 'key_points' fields."""
    
    # Use the generic library method
    result = await client.generate_text(
        prompt=prompt,
        system_prompt="You are a summarization expert."
    )
    
    # Parse and return business-specific result
    return parse_summary_json(result.text)
```

## Design Principles

1. **Generic**: No business logic - only provider interactions
2. **Configurable**: Takes config objects, not hardcoded values
3. **Provider-agnostic**: Same interface for all providers
4. **Reusable**: Can be used by any client or package
5. **Extensible**: Provider-specific features via kwargs

## Models and Configuration

- `LLMConfig`: Configuration for the client (model, API key, temperature, etc.)
- `LLMGenerationResult`: Generic result from text generation
- `EmbeddingResult`: Result from embedding generation
- `LLMModelConfig`: Model-to-provider mappings and defaults

## Provider Support

- **OpenAI**: GPT-3.5, GPT-4, GPT-4o models + embeddings
- **Anthropic**: Claude models (no embeddings support)
- **Gemini**: Gemini 1.5/2.5 models + embeddings + grounding support

## License

[Your License Here]
