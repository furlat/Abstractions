# Simplified Pydantic-AI Integration (No Dependencies)

## Key Insight

Since both `CallableRegistry` and `EntityRegistry` are implemented as class-based singletons:

```python
class CallableRegistry:
    _functions: Dict[str, FunctionMetadata] = {}  # Class attribute
    
    @classmethod
    def execute(cls, func_name: str, **kwargs):  # Class method
        # ...

class EntityRegistry:
    tree_registry: Dict[UUID, EntityTree] = {}  # Class attribute
    
    @classmethod  
    def get_stored_entity(cls, root_ecs_id: UUID, ecs_id: UUID):  # Class method
        # ...
```

They are **already global singletons** in the Python environment. No dependency injection needed!

## Simplified Tool Implementation

```python
from pydantic_ai import Agent
from pydantic_ai.toolsets.function import FunctionToolset
import json
from uuid import UUID

# Direct imports - no dependency wrapper needed
from abstractions.ecs.callable_registry import CallableRegistry
from abstractions.ecs.entity import EntityRegistry

# Create toolset
registry_toolset = FunctionToolset()

@registry_toolset.tool
async def execute_function(function_name: str, **kwargs) -> str:
    """Execute a registered function with string addressing support."""
    try:
        # Direct access to singleton
        result = CallableRegistry.execute(function_name, **kwargs)
        return json.dumps({
            "success": True,
            "function_name": function_name,
            "result": serialize_entity_result(result)
        }, default=str)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "function_name": function_name
        })

@registry_toolset.tool
def list_functions() -> str:
    """List all available functions in the callable registry."""
    try:
        # Direct access to singleton
        functions = CallableRegistry.list_functions()
        metadata = {}
        for func_name in functions:
            meta = CallableRegistry.get_metadata(func_name)
            metadata[func_name] = {
                "is_async": meta.is_async if meta else False,
                "docstring": getattr(meta.func, '__doc__', '') if meta else ''
            }
        
        return json.dumps({
            "success": True,
            "functions": functions,
            "metadata": metadata
        }, default=str)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@registry_toolset.tool
def get_all_lineages() -> str:
    """Show all entity lineages with their version history."""
    try:
        # Direct access to singleton
        lineages = {}
        for lineage_id, root_ids in EntityRegistry.lineage_registry.items():
            if root_ids:  # Only show lineages with entities
                latest_root_id = root_ids[-1]
                tree = EntityRegistry.get_stored_tree(latest_root_id)
                if tree and tree.root_ecs_id in tree.nodes:
                    root_entity = tree.nodes[tree.root_ecs_id]
                    lineages[str(lineage_id)] = {
                        "latest_ecs_id": str(latest_root_id),
                        "entity_type": type(root_entity).__name__,
                        "total_versions": len(root_ids),
                        "version_history": [str(rid) for rid in root_ids]
                    }
        
        return json.dumps({
            "success": True,
            "total_lineages": len(lineages),
            "lineages": lineages
        }, default=str)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@registry_toolset.tool
def get_entity(root_ecs_id: str, ecs_id: str) -> str:
    """Retrieve specific entity by root and entity IDs."""
    try:
        # Direct access to singleton
        root_uuid = UUID(root_ecs_id)
        entity_uuid = UUID(ecs_id)
        
        entity = EntityRegistry.get_stored_entity(root_uuid, entity_uuid)
        if not entity:
            return json.dumps({
                "success": False,
                "error": f"Entity {ecs_id} not found in root {root_ecs_id}"
            })
        
        entity_data = {
            "ecs_id": str(entity.ecs_id),
            "lineage_id": str(entity.lineage_id),
            "root_ecs_id": str(entity.root_ecs_id),
            "entity_type": type(entity).__name__,
            "is_root": entity.is_root_entity(),
            "attributes": {k: str(v) for k, v in entity.__dict__.items() 
                         if not k.startswith('_')}
        }
        
        return json.dumps({
            "success": True,
            "entity": entity_data
        }, default=str)
    except ValueError as e:
        return json.dumps({
            "success": False,
            "error": f"Invalid UUID format: {e}"
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })

# Simple agent setup - no dependencies needed!
agent = Agent(
    'anthropic:claude-sonnet-4-20250514',
    output_type=str,
    toolsets=[registry_toolset],
    system_prompt="""
    You are an assistant for the Abstractions Entity Framework.
    
    Available capabilities:
    - execute_function(function_name, **kwargs) - Execute registered functions
    - list_functions() - Show available functions with metadata
    - get_all_lineages() - Show all entity lineages and versions
    - get_entity(root_ecs_id, ecs_id) - Get specific entity details
    
    Use @uuid.field syntax for entity addressing in function parameters.
    Always provide clear, helpful responses about entity operations.
    """
)

# Usage - no dependencies to pass!
result = agent.run_sync(
    "List all available functions and show me the entity lineages"
)
print(result.output)
```

## Benefits of This Approach

1. **Much Simpler**: No dependency wrapper classes needed
2. **Direct Access**: Use CallableRegistry and EntityRegistry directly  
3. **Clean Separation**: Still completely external to abstractions package
4. **Natural**: Leverages the singleton design of the registries
5. **Less Coupling**: No complex dependency injection setup

## Helper Function

```python
def serialize_entity_result(result):
    """Helper to serialize CallableRegistry execution results."""
    if isinstance(result, Entity):
        return {
            "type": "single_entity",
            "ecs_id": str(result.ecs_id),
            "entity_type": type(result).__name__
        }
    elif isinstance(result, list):
        return {
            "type": "entity_list",
            "count": len(result),
            "entities": [
                {
                    "ecs_id": str(e.ecs_id) if hasattr(e, 'ecs_id') else str(e),
                    "entity_type": type(e).__name__
                } for e in result
            ]
        }
    else:
        return {"type": "other", "value": str(result)}
```

This is much cleaner and leverages the existing singleton architecture perfectly!