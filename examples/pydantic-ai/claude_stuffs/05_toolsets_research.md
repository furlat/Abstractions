# Toolsets Research

## Toolset Overview

Toolsets are collections of related tools that can be shared across multiple agents. They provide a way to organize and reuse tool functionality.

## Toolset Types

### 1. FunctionToolset
Built-in toolset for organizing custom functions:

```python
from pydantic_ai import FunctionToolset

toolset = FunctionToolset()

@toolset.tool
def foobar(ctx: RunContext[int], x: int) -> int:
    return ctx.deps + x

@toolset.tool(retries=2)
async def spam(ctx: RunContext[str], y: float) -> float:
    return ctx.deps + y

agent = Agent('test', toolsets=[toolset], deps_type=int)
```

### 2. LangChainToolset  
Integration with LangChain tools:

```python
from langchain_community.agent_toolkits import SlackToolkit
from pydantic_ai import Agent
from pydantic_ai.ext.langchain import LangChainToolset

toolkit = SlackToolkit()
toolset = LangChainToolset(toolkit.get_tools())

agent = Agent('openai:gpt-4o', toolsets=[toolset])
```

### 3. ACIToolset
Azure Container Instances integration:

```python
from pydantic_ai.ext.aci import ACIToolset

toolset = ACIToolset(
    # ACI configuration
)
```

## Toolset Registration

### Agent Integration

```python
agent = Agent(
    'openai:gpt-4o', 
    toolsets=[toolset1, toolset2],  # Multiple toolsets
    deps_type=MyDependency
)
```

### Tool Definition in Toolsets

```python
toolset = FunctionToolset()

@toolset.tool
def example_tool(ctx: RunContext[int], param: str) -> str:
    """Tool description for the LLM."""
    return f"Result: {ctx.deps} - {param}"
```

## Toolset Architecture

### Internal Structure
```python
# Agent has internal toolset management
_function_toolset: FunctionToolset[AgentDepsT]
_output_toolset: OutputToolset[AgentDepsT] | None  
_user_toolsets: Sequence[AbstractToolset[AgentDepsT]]
```

### Tool Name Conflict Detection
Toolsets check for naming conflicts:
```python
# Error if tools have same name across toolsets
f'{toolset.name} defines a tool whose name conflicts with existing tool from {existing_tools.toolset.name}: {name!r}'
```

## Key Benefits

1. **Reusability**: Share tools across multiple agents
2. **Organization**: Group related tools together
3. **Modularity**: Separate concerns and functionality
4. **Integration**: Built-in support for external libraries (LangChain, ACI)
5. **Conflict Detection**: Automatic checking for tool name conflicts

## Integration Patterns

### Custom Toolset Creation
```python
# Create a registry-specific toolset
registry_toolset = FunctionToolset()

@registry_toolset.tool
def execute_function(ctx: RunContext[EntityRegistry], function_name: str, **kwargs) -> str:
    """Execute a function from the entity registry."""
    # Implementation here
    pass

@registry_toolset.tool  
def list_functions(ctx: RunContext[EntityRegistry]) -> List[str]:
    """List all available functions in the registry."""
    return list(ctx.deps.callable_registry.functions.keys())
```

## Key Findings for Integration

1. `FunctionToolset` is ideal for custom registry tools
2. Toolsets use `@toolset.tool` decorator pattern
3. Multiple toolsets can be combined per agent
4. Conflict detection prevents tool name clashes
5. Same dependency system as individual tools
6. Toolsets can be shared across multiple agents
7. External integrations available (LangChain, ACI)