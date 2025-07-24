# Models Research

## Model Terminology

- **Model**: Pydantic AI class for making requests to specific LLM APIs (e.g., `OpenAIModel`, `AnthropicModel`, `GeminiModel`)
- **Provider**: Provider-specific classes for authentication and connections to LLM vendors
- **Profile**: Description of how to construct requests for specific model families

## Model Specification Syntax

### String-based Model Selection

```python
# OpenAI models
agent = Agent('openai:gpt-4o')

# Anthropic models  
agent = Agent('anthropic:claude-3-5-sonnet-latest')
agent = Agent('anthropic:claude-sonnet-4-20250514')  # From our test file
```

### Supported Model Providers

From the index, pydantic-ai supports:
- OpenAI
- Anthropic  
- Bedrock
- Cohere
- Gemini
- Google
- Groq
- Hugging Face
- Mistral

## Model Configuration Options

Basic agent with model:
```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-4o')
```

Agent with retries:
```python
agent = Agent(
    'anthropic:claude-3-5-sonnet-latest',
    retries=3,
)
```

## Usage Tracking

```python
from pydantic_ai.usage import UsageLimits

agent = Agent('anthropic:claude-3-5-sonnet-latest')

# Usage information is available in results
result.usage = Usage(
    requests=1, 
    request_tokens=56, 
    response_tokens=1, 
    total_tokens=57,
    model_name='gpt-4o',
    timestamp=datetime.datetime(...),
)
```

## Key Findings for Integration

1. Models are specified using string format: `'provider:model-name'`
2. For Anthropic: `'anthropic:claude-sonnet-4-20250514'` works
3. Models are swappable without code changes
4. Usage tracking is built-in with token counts
5. Retries and other options can be configured at agent level