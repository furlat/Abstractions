# Pydantic-AI Registry Integration Plan

## Research Summary

Based on comprehensive research of pydantic-ai documentation, here's the integration plan for creating minimal tool wrappers around the abstractions entity registry system.

## Architecture Overview

### Core Components

1. **Registry Toolset**: `FunctionToolset` containing registry operation tools
2. **Agent Dependency**: `EntityRegistry` instance injected via `deps_type`
3. **String-based Addressing**: Use existing `@uuid.field` syntax for entity references
4. **Typed Responses**: JSON/string responses with structured output validation

## Minimal Tool Set Design

### 1. Execute Function Tool

```python
@registry_toolset.tool
async def execute_function(
    ctx: RunContext[EntityRegistry], 
    function_name: str, 
    **kwargs
) -> str:
    """
    Execute a function from the callable registry with string address parameters.
    
    Args:
        function_name: Name of the function to execute
        **kwargs: Function parameters (supports @uuid.field addresses)
    
    Returns:
        JSON string of execution result
    """
    # Use existing callable registry functionality
    registry = ctx.deps
    result = registry.call_function(function_name, **kwargs)
    return json.dumps(result, default=str)
```

### 2. List Functions Tool

```python
@registry_toolset.tool
def list_functions(ctx: RunContext[EntityRegistry]) -> str:
    """
    List all available functions in the callable registry.
    
    Returns:
        JSON array of function names
    """
    registry = ctx.deps
    functions = list(registry.callable_registry.functions.keys())
    return json.dumps(functions)
```

### 3. Get Function Signature Tool

```python
@registry_toolset.tool
def get_function_signature(ctx: RunContext[EntityRegistry], function_name: str) -> str:
    """
    Get type hints and signature for a specific function.
    
    Args:
        function_name: Name of the function
        
    Returns:
        JSON object with signature details
    """
    registry = ctx.deps
    func = registry.callable_registry.functions.get(function_name)
    if not func:
        raise ModelRetry(f"Function {function_name} not found")
    
    signature_info = {
        "name": function_name,
        "parameters": get_type_hints(func),
        "docstring": getdoc(func)
    }
    return json.dumps(signature_info, default=str)
```

### 4. List Lineages Tool

```python
@registry_toolset.tool
def list_lineages(ctx: RunContext[EntityRegistry]) -> str:
    """
    Show all entity lineages with their latest objects.
    
    Returns:
        JSON object mapping lineage_id to latest entity info
    """
    registry = ctx.deps
    lineages = {}
    
    for lineage_id, root_ids in registry.lineage_to_root_ids.items():
        latest_root_id = root_ids[-1]  # Most recent
        entity = registry.get_stored_entity(latest_root_id, latest_root_id)
        if entity:
            lineages[str(lineage_id)] = {
                "latest_ecs_id": str(latest_root_id),
                "entity_type": type(entity).__name__,
                "attributes": list(entity.__dict__.keys())
            }
    
    return json.dumps(lineages, default=str)
```

### 5. Get Lineage Tool

```python
@registry_toolset.tool
def get_lineage(ctx: RunContext[EntityRegistry], lineage_id: str) -> str:
    """
    Get version history for a specific lineage.
    
    Args:
        lineage_id: UUID of the lineage to examine
        
    Returns:
        JSON array of version history
    """
    registry = ctx.deps
    lineage_uuid = UUID(lineage_id)
    root_ids = registry.lineage_to_root_ids.get(lineage_uuid, [])
    
    history = []
    for root_id in root_ids:
        entity = registry.get_stored_entity(root_id, root_id)
        if entity:
            history.append({
                "ecs_id": str(root_id),
                "entity_type": type(entity).__name__,
                "timestamp": entity.created_at.isoformat() if hasattr(entity, 'created_at') else None
            })
    
    return json.dumps(history, default=str)
```

### 6. Get Entity Tool

```python
@registry_toolset.tool
def get_entity(ctx: RunContext[EntityRegistry], entity_id: str) -> str:
    """
    Retrieve specific entity by ID with full details.
    
    Args:
        entity_id: UUID of the entity to retrieve
        
    Returns:
        JSON representation of the entity
    """
    registry = ctx.deps
    entity_uuid = UUID(entity_id)
    
    # Find root containing this entity
    root_id = registry.ecs_id_to_root_id.get(entity_uuid)
    if not root_id:
        raise ModelRetry(f"Entity {entity_id} not found")
    
    entity = registry.get_stored_entity(root_id, entity_uuid)
    if not entity:
        raise ModelRetry(f"Could not retrieve entity {entity_id}")
    
    # Convert to JSON-serializable format
    entity_data = {
        "ecs_id": str(entity.ecs_id),
        "lineage_id": str(entity.lineage_id),
        "entity_type": type(entity).__name__,
        "attributes": {k: str(v) for k, v in entity.__dict__.items()}
    }
    
    return json.dumps(entity_data, default=str)
```

## Agent Setup

### Registry Agent Creation

```python
from pydantic_ai import Agent, FunctionToolset
from abstractions.ecs.entity import EntityRegistry

# Create registry toolset
registry_toolset = FunctionToolset()

# Add all tools to toolset (using decorators above)

# Create agent with registry dependency
registry_agent = Agent(
    'anthropic:claude-sonnet-4-20250514',
    deps_type=EntityRegistry,
    output_type=str,
    toolsets=[registry_toolset],
    system_prompt="""
    You are an assistant for the Entity Registry System. You can:
    
    1. Execute functions using execute_function(function_name, **kwargs)
    2. List available functions with list_functions()
    3. Get function signatures with get_function_signature(function_name)
    4. View entity lineages with list_lineages()
    5. Get lineage history with get_lineage(lineage_id)
    6. Retrieve entities with get_entity(entity_id)
    
    Use @uuid.field syntax for entity references in function parameters.
    Always provide helpful, structured responses about entity operations.
    """
)
```

### Usage Pattern

```python
# Initialize registry
registry = EntityRegistry()

# Run agent with registry as dependency
result = registry_agent.run_sync(
    "List all available functions and show me the entities in lineage abc-123",
    deps=registry
)

print(result.output)
```

## Key Benefits

1. **Minimal Interface**: Just 6 focused tools covering core registry operations
2. **String Addressing**: Leverages existing `@uuid.field` syntax
3. **JSON Responses**: Structured, parseable responses for complex data
4. **Type Safety**: Full type hints with error handling via `ModelRetry`
5. **Conversation Support**: Message history enables multi-step workflows
6. **Registry Integration**: Direct access to all existing registry functionality

## Implementation Steps

1. Create `registry_toolset.py` with the 6 tools
2. Create `registry_agent.py` with agent setup
3. Create example usage in `registry_agent_example.py`
4. Test integration with existing registry functions
5. Document conversation patterns for common workflows

This provides the minimal, clean interface you requested while leveraging all the powerful features of both pydantic-ai and the abstractions registry system.