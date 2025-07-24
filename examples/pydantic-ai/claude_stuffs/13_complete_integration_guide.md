# Complete Pydantic-AI + Abstractions Integration Guide

## Executive Summary

This document presents the complete integration path between the Abstractions Entity Framework and Pydantic-AI, based on comprehensive research of both systems. The integration provides natural language access to the entity registry and function execution system while maintaining clean architectural separation.

## Architecture Overview

### Abstractions Framework (Source System)
The Abstractions framework is a functional data processing system with these core components:

#### 1. CallableRegistry - Function Execution Engine
```python
from abstractions.ecs.callable_registry import CallableRegistry

# Class-based singleton with @classmethod decorators
class CallableRegistry:
    _functions: Dict[str, FunctionMetadata] = {}  # Class attribute
    
    @classmethod
    def execute(cls, func_name: str, **kwargs) -> Union[Entity, List[Entity]]
    
    @classmethod
    def list_functions(cls) -> List[str]
    
    @classmethod
    def get_metadata(cls, name: str) -> Optional[FunctionMetadata]
```

#### 2. EntityRegistry - Versioned Entity Storage
```python
from abstractions.ecs.entity import EntityRegistry

# Class-based singleton with complete entity lifecycle management
class EntityRegistry:
    tree_registry: Dict[UUID, EntityTree] = {}              # root_ecs_id -> EntityTree
    lineage_registry: Dict[UUID, List[UUID]] = {}           # lineage_id -> [root_ecs_ids]
    live_id_registry: Dict[UUID, Entity] = {}               # live_id -> Entity
    ecs_id_to_root_id: Dict[UUID, UUID] = {}               # ecs_id -> root_ecs_id
    type_registry: Dict[Type[Entity], List[UUID]] = {}      # entity_type -> [lineage_ids]
    
    @classmethod
    def get_stored_entity(cls, root_ecs_id: UUID, ecs_id: UUID) -> Optional[Entity]
    
    @classmethod
    def get_stored_tree(cls, root_ecs_id: UUID) -> Optional[EntityTree]
    
    @classmethod
    def version_entity(cls, entity: Entity) -> bool
```

#### 3. String-Based Addressing System
```python
from abstractions.ecs.functional_api import get

# Universal entity addressing
student_name = get(f"@{entity.ecs_id}.name")
student_gpa = get(f"@{entity.ecs_id}.gpa")
```

#### 4. Event System (Optional Observability)
```python
from abstractions.events.events import get_event_bus, on, emit

# Event-driven coordination
@on(EntityCreatedEvent)
async def handle_entity_creation(event):
    pass
```

### Pydantic-AI Framework (Client System)
Pydantic-AI provides the agent interface with these components:

#### 1. Agent Creation
```python
from pydantic_ai import Agent

agent = Agent(
    'anthropic:claude-sonnet-4-20250514',  # Model specification
    output_type=str,                       # Expected output type
    toolsets=[toolset],                    # Tool collections
    system_prompt="Agent instructions"     # Behavior definition
)
```

#### 2. Tool Registration via FunctionToolset
```python
from pydantic_ai.toolsets.function import FunctionToolset

toolset = FunctionToolset()

@toolset.tool
async def my_tool(param: str) -> str:
    """Tool description for LLM."""
    return "result"
```

#### 3. Agent Execution
```python
result = agent.run_sync("Natural language query")
print(result.output)  # Typed output
```

#### 4. Message History Support
```python
result1 = agent.run_sync("First query")
result2 = agent.run_sync(
    "Follow up question",
    message_history=result1.new_messages()  # Conversation continuity
)
```

## Integration Architecture

### Core Insight: Global Singleton Access
Both CallableRegistry and EntityRegistry are implemented as **class-based singletons** accessible globally in the Python environment. This eliminates the need for dependency injection:

```python
# No dependency context needed!
@registry_toolset.tool
async def execute_function(function_name: str, **kwargs) -> str:
    # Direct access to global singleton
    result = CallableRegistry.execute(function_name, **kwargs)
    return json.dumps(result, default=str)
```

### Tool Design Pattern

Each tool follows this pattern:
1. **Accept natural language parameters** (strings, simple types)
2. **Convert to abstractions API calls** (UUIDs, entity operations)
3. **Wrap results in JSON** for agent consumption
4. **Handle errors gracefully** with structured error responses

## Complete Tool Implementation

### 1. Function Execution Tool
```python
@registry_toolset.tool
async def execute_function(function_name: str, **kwargs) -> str:
    """
    Execute a registered function with string addressing support.
    
    Supports @uuid.field syntax for entity references in parameters.
    Returns JSON with execution results or error details.
    """
    try:
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
```

### 2. Function Discovery Tool
```python
@registry_toolset.tool
def list_functions() -> str:
    """List all available functions with metadata."""
    try:
        functions = CallableRegistry.list_functions()
        metadata = {}
        
        for func_name in functions:
            meta = CallableRegistry.get_metadata(func_name)
            metadata[func_name] = {
                "is_async": meta.is_async if meta else False,
                "docstring": getattr(meta.func, '__doc__', '') if meta else '',
                "signature": str(meta.signature) if meta else ''
            }
        
        return json.dumps({
            "success": True,
            "total_functions": len(functions),
            "functions": functions,
            "metadata": metadata
        }, default=str)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})
```

### 3. Entity Lineage Tool
```python
@registry_toolset.tool
def get_all_lineages() -> str:
    """Show all entity lineages with version history."""
    try:
        lineages = {}
        
        for lineage_id, root_ids in EntityRegistry.lineage_registry.items():
            if root_ids:
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
        return json.dumps({"success": False, "error": str(e)})
```

### 4. Entity Retrieval Tool
```python
@registry_toolset.tool
def get_entity(root_ecs_id: str, ecs_id: str) -> str:
    """Retrieve specific entity with complete details."""
    try:
        root_uuid = UUID(root_ecs_id)
        entity_uuid = UUID(ecs_id)
        
        entity = EntityRegistry.get_stored_entity(root_uuid, entity_uuid)
        if not entity:
            return json.dumps({
                "success": False,
                "error": f"Entity {ecs_id} not found in root {root_ecs_id}"
            })
        
        # Get entity tree for relationship context
        tree = EntityRegistry.get_stored_tree(root_uuid)
        ancestry_path = tree.get_ancestry_path(entity_uuid) if tree else []
        
        entity_data = {
            "ecs_id": str(entity.ecs_id),
            "lineage_id": str(entity.lineage_id),
            "root_ecs_id": str(entity.root_ecs_id),
            "entity_type": type(entity).__name__,
            "is_root": entity.is_root_entity(),
            "ancestry_path": [str(uid) for uid in ancestry_path],
            "attributes": {
                k: str(v) for k, v in entity.__dict__.items() 
                if not k.startswith('_') and k not in [
                    'ecs_id', 'live_id', 'root_ecs_id', 'root_live_id', 
                    'lineage_id', 'created_at', 'forked_at'
                ]
            }
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
        return json.dumps({"success": False, "error": str(e)})
```

### 5. Function Signature Tool
```python
@registry_toolset.tool
def get_function_signature(function_name: str) -> str:
    """Get detailed function signature and type information."""
    try:
        metadata = CallableRegistry.get_metadata(function_name)
        if not metadata:
            return json.dumps({
                "success": False,
                "error": f"Function '{function_name}' not found"
            })
        
        # Extract parameter information
        import inspect
        sig = inspect.signature(metadata.func)
        type_hints = get_type_hints(metadata.func)
        
        parameters = {}
        for param_name, param in sig.parameters.items():
            param_info = {
                "type": str(type_hints.get(param_name, param.annotation)),
                "default": str(param.default) if param.default != inspect.Parameter.empty else None,
                "required": param.default == inspect.Parameter.empty,
                "kind": str(param.kind)
            }
            parameters[param_name] = param_info
        
        return json.dumps({
            "success": True,
            "function_name": function_name,
            "parameters": parameters,
            "return_type": str(type_hints.get('return', sig.return_annotation)),
            "docstring": metadata.func.__doc__,
            "is_async": metadata.is_async,
            "signature": str(sig)
        }, default=str)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })
```

### 6. Lineage History Tool
```python
@registry_toolset.tool
def get_lineage_history(lineage_id: str) -> str:
    """Get complete version history for a specific lineage."""
    try:
        lineage_uuid = UUID(lineage_id)
        root_ids = EntityRegistry.lineage_registry.get(lineage_uuid, [])
        
        if not root_ids:
            return json.dumps({
                "success": False,
                "error": f"Lineage {lineage_id} not found"
            })
        
        history = []
        for i, root_id in enumerate(root_ids):
            tree = EntityRegistry.get_stored_tree(root_id)
            if tree and tree.root_ecs_id in tree.nodes:
                root_entity = tree.nodes[tree.root_ecs_id]
                version_info = {
                    "version_number": i + 1,
                    "root_ecs_id": str(root_id),
                    "entity_type": type(root_entity).__name__,
                    "created_at": str(root_entity.created_at),
                    "forked_at": str(root_entity.forked_at) if root_entity.forked_at else None,
                    "node_count": tree.node_count,
                    "edge_count": tree.edge_count,
                    "max_depth": tree.max_depth
                }
                history.append(version_info)
        
        return json.dumps({
            "success": True,
            "lineage_id": lineage_id,
            "total_versions": len(history),
            "history": history
        }, default=str)
    except ValueError as e:
        return json.dumps({
            "success": False,
            "error": f"Invalid UUID format: {e}"
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})
```

## Agent Configuration

```python
from pydantic_ai import Agent
from pydantic_ai.toolsets.function import FunctionToolset

# Create toolset with all tools
registry_toolset = FunctionToolset()
# ... add all tools with @registry_toolset.tool decorators

# Create agent
registry_agent = Agent(
    'anthropic:claude-sonnet-4-20250514',
    output_type=str,
    toolsets=[registry_toolset],
    system_prompt="""
    You are an assistant for the Abstractions Entity Framework.
    
    The framework is a functional data processing system where:
    - Entities are immutable data units with global identity
    - Functions transform entities and are tracked in a registry
    - All operations maintain complete provenance and lineage
    - String addressing allows distributed data access (@uuid.field syntax)
    
    Available capabilities:
    - execute_function(function_name, **kwargs) - Execute registered functions
    - list_functions() - Show available functions with metadata  
    - get_function_signature(function_name) - Get function type information
    - get_all_lineages() - Show all entity lineages and versions
    - get_lineage_history(lineage_id) - Get version history for specific lineage
    - get_entity(root_ecs_id, ecs_id) - Get specific entity details
    
    When users ask about functions, help them understand parameters and usage.
    When users ask about entities, help them explore lineages and relationships.
    Always provide clear, structured responses with relevant IDs for further exploration.
    
    For function execution, you can use @uuid.field syntax in parameters to reference
    entity attributes. Example: execute_function("update_gpa", student="@abc-123", new_gpa=3.8)
    """
)
```

## Usage Patterns

### 1. Function Discovery and Execution
```python
# Discover available functions
result = registry_agent.run_sync("What functions are available?")

# Get function details
result = registry_agent.run_sync("Show me the signature for update_gpa function")

# Execute function
result = registry_agent.run_sync(
    "Execute update_gpa with student @abc-123-def-456 and new_gpa 3.8"
)
```

### 2. Entity Exploration
```python
# Browse entity lineages
result = registry_agent.run_sync("Show me all entity lineages")

# Get specific entity
result = registry_agent.run_sync(
    "Get entity details for ecs_id def-456-ghi-789 in root abc-123-def-456"
)

# Explore version history
result = registry_agent.run_sync("Show version history for lineage xyz-789-abc-123")
```

### 3. Conversational Workflows
```python
# Multi-step conversation
result1 = registry_agent.run_sync("List available functions")
result2 = registry_agent.run_sync(
    "Execute the first function you showed me with appropriate test parameters",
    message_history=result1.new_messages()
)
```

## Key Benefits

### 1. Natural Language Interface
- Users can explore and execute functions using natural language
- No need to learn complex APIs or UUID management
- Conversational exploration of entity relationships

### 2. Complete Separation
- Pydantic-AI integration is entirely external to abstractions
- No modification of existing abstractions code
- Clean architectural boundaries

### 3. Leverages Both Systems
- Abstractions: Provides powerful entity management and function execution
- Pydantic-AI: Provides natural language understanding and conversation

### 4. Future-Ready Architecture
- Ready for multi-tenant contexts when needed
- Event system integration available for observability
- Extensible tool pattern for additional capabilities

## Implementation Status

✅ **Research Complete**: Both systems fully understood  
✅ **Architecture Defined**: Clean separation with singleton access  
✅ **Tools Designed**: 6 core tools covering all major operations  
✅ **Integration Pattern**: Direct access to global singletons  
🔄 **Implementation**: Ready for coding and testing  

## Next Steps

1. **Create `registry_agent.py`** - Complete implementation with all 6 tools
2. **Create `example_usage.py`** - Demonstration of various usage patterns  
3. **Create `test_integration.py`** - Basic validation tests
4. **Documentation** - Usage guide and API reference

This integration provides a complete natural language interface to the sophisticated Abstractions Entity Framework while maintaining clean architectural separation and leveraging the strengths of both systems.