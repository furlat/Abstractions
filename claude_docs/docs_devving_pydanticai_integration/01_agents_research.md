# Agents Research

## Agent Class Definition

```python
@final
@dataclasses.dataclass(init=False)
class Agent(Generic[AgentDepsT, OutputDataT]):
    """Class for defining "agents" - a way to have a specific type of "conversation" with an LLM.

    Agents are generic in the dependency type they take [`AgentDepsT`][pydantic_ai.tools.AgentDepsT]
```

## Agent Creation Syntax

Basic agent creation:
```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-4o')
```

Agent with configuration:
```python
from pydantic_ai import Agent, RunContext

roulette_agent = Agent(  
    'openai:gpt-4o',
    deps_type=int,
    output_type=bool,
    system_prompt=(
        'Use the `roulette_wheel` function to see if the '
        'customer has won based on the number they provide.'
    ),
)
```

## Tool Registration

Tools are registered using the `@agent.tool` decorator:

```python
@roulette_agent.tool
async def roulette_wheel(ctx: RunContext[int], square: int) -> str:
    """check if the square is a winner"""
    return 'winner' if square == ctx.deps else 'loser'
```

## Key Agent Parameters

- **Model**: String identifier like `'openai:gpt-4o'` or `'anthropic:claude-sonnet-4-20250514'`
- **deps_type**: Type for dependency injection (e.g., `int`, custom classes)
- **output_type**: Expected output type (e.g., `bool`, `str`, custom types)
- **system_prompt**: String or tuple of strings for system instructions

## Agent Run Results

```python
@dataclasses.dataclass
class AgentRunResult(Generic[OutputDataT]):
    """The final result of an agent run."""
    output: OutputDataT
```

## Key Findings for Integration

1. Agents are generic over dependency and output types
2. Tools are registered with decorators and receive RunContext
3. System prompts can be strings or tuples
4. Model specification is string-based
5. Agent runs return structured results with typed output