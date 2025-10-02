# LLM Service

A production-grade LLM service that provides unified access to multiple LLM providers including OpenAI, Anthropic, Google, and local models.

## Features

- **Multi-Provider Support**: OpenAI, Anthropic Claude, Google Gemini, Ollama
- **Async/Await**: High-performance asynchronous operations
- **Rate Limiting**: Built-in rate limiting and quota management
- **Error Handling**: Comprehensive error handling with custom exceptions
- **Streaming**: Real-time streaming response support
- **Configuration**: Environment-based configuration management
- **Monitoring**: Production-ready logging and health checks
- **Type Safety**: Full type hints and comprehensive documentation

## Quick Start

### Installation

```bash
# Install dependencies
pip install openai anthropic

# Set API keys (optional - service works without them)
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"
```

### Basic Usage

```python
from llm_service import LLMService, LLMProvider

# Initialize service
service = LLMService()
await service.initialize()

# Generate response
response = await service.generate("What is machine learning?")
print(response.content)

# Use specific provider
response = await service.generate(
    "Explain quantum computing",
    provider=LLMProvider.ANTHROPIC,
    model="claude-3-sonnet-20240229"
)

# Streaming response
async for chunk in service.stream_generate("Tell me a story"):
    print(chunk, end="")
```

### CLI Usage

```bash
# Basic usage
python llm_chat.py "What is artificial intelligence?"

# Specify provider and model
python llm_chat.py "Explain quantum computing" --provider anthropic --model claude-3-sonnet-20240229

# Streaming response
python llm_chat.py "Tell me a story" --stream --temperature 0.9

# With system prompt
python llm_chat.py "Review this code" --system-prompt "You are a senior software engineer"
```

## Configuration

The service can be configured via environment variables:

```bash
# Provider API Keys
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"
export GOOGLE_API_KEY="your-google-key"

# Service Configuration
export LLM_DEFAULT_PROVIDER="openai"
export LLM_DEFAULT_TEMPERATURE="0.7"
export LLM_DEFAULT_MAX_TOKENS="2000"
export LLM_GLOBAL_TIMEOUT="120"
export LLM_ENABLE_LOGGING="true"
export LLM_LOG_LEVEL="INFO"
```

## Architecture

```
llm_service/
├── core/
│   ├── interfaces.py      # Abstract base classes
│   └── service.py         # Main service orchestrator
├── providers/
│   ├── openai_provider.py    # OpenAI integration
│   └── anthropic_provider.py # Anthropic integration
├── config/
│   └── settings.py        # Configuration management
├── utils/
│   └── exceptions.py      # Custom exceptions
└── example.py            # Usage examples
```

## Error Handling

The service provides comprehensive error handling:

```python
from llm_service import (
    LLMAuthenticationError, LLMRateLimitError, 
    LLMQuotaExceededError, LLMModelNotFoundError
)

try:
    response = await service.generate("Hello")
except LLMAuthenticationError:
    print("Check your API keys")
except LLMRateLimitError as e:
    print(f"Rate limited, retry after {e.retry_after} seconds")
except LLMQuotaExceededError:
    print("Usage quota exceeded")
```

## Health Monitoring

```python
# Check service health
health = await service.health_check()
print(f"Service status: {health['service']}")

# Check available providers
providers = service.get_available_providers()
print(f"Available providers: {providers}")

# Get models for a provider
models = service.get_provider_models(LLMProvider.OPENAI)
print(f"OpenAI models: {models}")
```

## Advanced Usage

### Chat Conversations

```python
from llm_service import LLMMessage

messages = [
    LLMMessage(role="user", content="Hi! I'm learning Python."),
    LLMMessage(role="assistant", content="Great! What would you like to know?"),
    LLMMessage(role="user", content="Explain decorators with an example.")
]

response = await service.chat(
    messages=messages,
    system_prompt="You are a helpful Python tutor."
)
```

### Custom Configuration

```python
from llm_service import LLMServiceConfig, ProviderConfig

config = LLMServiceConfig()
config.default_temperature = 0.9
config.default_max_tokens = 1000
config.global_timeout = 60

service = LLMService(config)
```

## Production Deployment

### Environment Setup

```bash
# Production environment variables
export LLM_ENABLE_LOGGING=true
export LLM_LOG_LEVEL=INFO
export LLM_GLOBAL_TIMEOUT=120
export LLM_GLOBAL_MAX_RETRIES=3
```

### Health Checks

```python
# Health check endpoint for monitoring
@app.get("/health")
async def health_check():
    health = await llm_service.health_check()
    return health
```

### Rate Limiting

The service includes built-in rate limiting per provider:
- OpenAI: 3000 RPM
- Anthropic: 1000 RPM  
- Google: 60 RPM
- Ollama: No limit (local)

## Examples

Run the comprehensive examples:

```bash
# All examples
python -m llm_service.example

# CLI interface
python llm_chat.py "Your prompt here"
```

## License

This is a production-grade module designed for enterprise use with proper error handling, logging, and monitoring capabilities.
