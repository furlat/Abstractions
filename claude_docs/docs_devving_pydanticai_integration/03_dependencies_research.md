# Dependencies Research

## Dependency System Overview

Dependencies in pydantic-ai provide a way to inject state and services into agent tools and functions. They are accessed through the `RunContext` parameter.

## Key Components

### 1. Dependency Type Declaration

```python
# Agent with integer dependency
roulette_agent = Agent(
    'openai:gpt-4o',
    deps_type=int,  # Declare dependency type
    output_type=bool,
)

# Agent with custom dependency class
weather_agent = Agent[WeatherService, str](
    'openai:gpt-4o',
)
```

### 2. RunContext Access Pattern

Tools and functions receive dependencies through `RunContext[T]`:

```python
@roulette_agent.tool
async def roulette_wheel(ctx: RunContext[int], square: int) -> str:
    """check if the square is a winner"""
    return 'winner' if square == ctx.deps else 'loser'  # Access via ctx.deps
```

### 3. Dependency Injection at Runtime

Dependencies are passed when running the agent:

```python
success_number = 18
result = roulette_agent.run_sync(
    'Put my money on square eighteen', 
    deps=success_number  # Inject dependency here
)
```

## Advanced Dependency Patterns

### Complex Dependency Objects

```python
@dataclass
class MyDeps:
    http_client: httpx.AsyncClient
    api_key: str

@agent.tool
async def get_joke_material(ctx: RunContext[MyDeps], subject: str) -> str:
    response = await ctx.deps.http_client.get(
        'https://example.com#jokes',
        params={'subject': subject},
        headers={'Authorization': f'Bearer {ctx.deps.api_key}'},
    )
    response.raise_for_status()
    return response.text
```

### Dependencies in System Prompts

```python
@agent.system_prompt
def add_user_name(ctx: RunContext[str]) -> str:
    return f"The user's name is {ctx.deps}."

@agent.system_prompt
async def get_system_prompt(ctx: RunContext[MyDeps]) -> str:
    response = await ctx.deps.http_client.get('https://example.com')
    response.raise_for_status()
    return f'Prompt: {response.text}'
```

### Dependencies in Output Validators

```python
@agent.output_validator
async def validate_output(ctx: RunContext[MyDeps], output: str) -> str:
    response = await ctx.deps.http_client.post(
        'https://example.com#validate',
        headers={'Authorization': f'Bearer {ctx.deps.api_key}'},
        params={'query': output},
    )
    response.raise_for_status()
    return output
```

## Key Findings for Integration

1. Dependencies are strongly typed through `RunContext[T]`
2. Access pattern is always `ctx.deps` in tools and functions  
3. Dependencies can be primitives (int, str) or complex objects
4. Dependencies are injected at agent run time via `deps=` parameter
5. Same dependency system works for tools, system prompts, and validators
6. Async and sync functions both support dependencies
7. Dependencies enable stateful operations and external service access