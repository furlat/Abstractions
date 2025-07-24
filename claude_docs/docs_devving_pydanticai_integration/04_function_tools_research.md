# Function Tools Research

## Tool Registration Methods

### 1. Agent Decorator Method (`@agent.tool`)

```python
@roulette_agent.tool
async def roulette_wheel(ctx: RunContext[int], square: int) -> str:
    """check if the square is a winner"""
    return 'winner' if square == ctx.deps else 'loser'
```

### 2. Tool Class Method

```python
from pydantic_ai import Tool

# With context
agent = Agent(
    'google-gla:gemini-1.5-flash',
    deps_type=str,
    tools=[
        Tool(roll_dice, takes_ctx=False),
        Tool(get_player_name, takes_ctx=True),
    ],
)

# Tool function definitions
def roll_dice() -> str:
    """Roll a dice and return the result."""
    return str(random.randint(1, 6))

def get_player_name(ctx: RunContext[str]) -> str:
    """Get the player's name."""
    return ctx.deps
```

### 3. Agent Tools List

```python
agent = Agent(
    'openai:o3-mini',
    tools=[duckduckgo_search_tool()],  # External tool functions
    system_prompt='Search DuckDuckGo for the given query and return the results.',
)
```

## Tool Configuration Options

### Retries

```python
@agent.tool_plain(retries=5)
def infinite_retry_tool() -> int:
    return 42

# Or with Tool class
@agent.tool(retries=2)
async def spam(ctx: RunContext[str], y: float) -> float:
    return ctx.deps + y
```

### Context Control

```python
# Tool class with takes_ctx parameter
Tool(roll_dice, takes_ctx=False)     # No RunContext needed
Tool(get_player_name, takes_ctx=True) # Requires RunContext
```

## Tool Definition Structure

Tools are converted to `ToolDefinition` objects:

```python
ToolDefinition(
    name='foobar',
    parameters_json_schema={
        'properties': {
            # JSON schema for parameters
        }
    }
)
```

## Tool Types

### @agent.tool
- Standard tool decorator
- Requires RunContext[DepsT] as first parameter
- Supports both sync and async functions

### @agent.tool_plain  
- Plain tool decorator
- No RunContext required
- Can configure retries independently

### Tool Class
- Explicit tool registration
- `takes_ctx` parameter controls context requirement
- Can be used in agent `tools=[]` parameter

## Tool Function Requirements

1. **Type Hints**: Functions must have complete type annotations
2. **Docstrings**: Used for tool description to the LLM
3. **Return Types**: Must specify return type for proper validation
4. **Parameters**: All parameters need type hints for schema generation

## Key Findings for Integration

1. Multiple registration methods available (`@agent.tool`, `Tool()`, `tools=[]`)
2. Context control via `takes_ctx` or function signature
3. Retry configuration per tool
4. JSON schema generation from type hints
5. Docstrings become tool descriptions for LLM
6. Both sync and async functions supported
7. Tools can be external functions or agent-specific methods