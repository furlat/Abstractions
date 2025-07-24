# Corrected Abstractions API Analysis

## Core Framework Understanding

Based on studying the README and actual codebase, here's the correct understanding:

### Primary APIs

#### 1. CallableRegistry - The Function Execution Engine
```python
from abstractions.ecs.callable_registry import CallableRegistry

# Function registration
@CallableRegistry.register("function_name")
def my_function(student: Student, param: float) -> Student:
    return student

# Function execution
result = CallableRegistry.execute("function_name", student=student, param=3.8)
# Returns: Union[Entity, List[Entity]]

# Async execution  
result = await CallableRegistry.aexecute("function_name", student=student, param=3.8)

# Registry queries
functions = CallableRegistry.list_functions()  # List[str]
metadata = CallableRegistry.get_metadata("function_name")  # Optional[FunctionMetadata]
```

#### 2. EntityRegistry - Entity Storage and Versioning
```python
from abstractions.ecs.entity import EntityRegistry

# Class attributes (not instance methods!)
EntityRegistry.tree_registry: Dict[UUID, EntityTree] = {}
EntityRegistry.lineage_registry: Dict[UUID, List[UUID]] = {}  # lineage_id -> [root_ecs_ids]
EntityRegistry.live_id_registry: Dict[UUID, Entity] = {}
EntityRegistry.ecs_id_to_root_id: Dict[UUID, UUID] = {}
EntityRegistry.type_registry: Dict[Type[Entity], List[UUID]] = {}

# Key methods (need to discover actual API)
EntityRegistry.register_entity(entity)
EntityRegistry.get_stored_tree(root_ecs_id: UUID) -> Optional[EntityTree]
EntityRegistry.get_stored_entity(root_ecs_id: UUID, ecs_id: UUID) -> Optional[Entity]
```

#### 3. Functional API - Distributed Addressing
```python
from abstractions.ecs.functional_api import get

# String-based entity addressing
student_name = get(f"@{student.ecs_id}.name")
student_gpa = get(f"@{student.ecs_id}.gpa")
```

#### 4. Event System - Optional Observability
```python
from abstractions.events.events import get_event_bus, on, emit, Event, CreatedEvent

# Event handlers
@on(EventType)
async def handler(event: EventType):
    pass

# Global event bus
bus = get_event_bus()
```

### Correct Pydantic-AI Integration Pattern

Based on research, the correct pydantic-ai pattern is:

```python
from pydantic_ai import Agent, RunContext
from pydantic_ai.toolsets.function import FunctionToolset

# Create toolset
toolset = FunctionToolset()

# Add tools with decorator
@toolset.tool
async def my_tool(ctx: RunContext[Dependencies], param: str) -> str:
    """Tool description for LLM."""
    # Access dependencies via ctx.deps
    return "result"

# Create agent with toolset
agent = Agent(
    'anthropic:claude-sonnet-4-20250514',
    deps_type=Dependencies,
    output_type=str,
    toolsets=[toolset],
    system_prompt="Agent instructions"
)

# Run agent
result = agent.run_sync("Query", deps=dependencies_instance)
```

## Key Corrections for Integration

### 1. Dependencies Structure
We need a dependency object that provides access to both registries:

```python
@dataclass
class RegistryDependencies:
    """Dependencies for pydantic-ai tools to access abstractions framework."""
    
    def list_functions(self) -> List[str]:
        """List available functions from CallableRegistry."""
        return CallableRegistry.list_functions()
    
    def execute_function(self, func_name: str, **kwargs) -> Union[Entity, List[Entity]]:
        """Execute function from CallableRegistry."""
        return CallableRegistry.execute(func_name, **kwargs)
    
    def get_function_metadata(self, func_name: str) -> Optional[FunctionMetadata]:
        """Get function metadata."""
        return CallableRegistry.get_metadata(func_name)
    
    def get_lineages(self) -> Dict[UUID, List[UUID]]:
        """Get all lineages from EntityRegistry."""
        return EntityRegistry.lineage_registry
    
    def get_entity_tree(self, root_ecs_id: UUID) -> Optional[EntityTree]:
        """Get entity tree from EntityRegistry."""
        return EntityRegistry.get_stored_tree(root_ecs_id)
    
    def get_entity(self, root_ecs_id: UUID, ecs_id: UUID) -> Optional[Entity]:
        """Get specific entity from EntityRegistry."""
        return EntityRegistry.get_stored_entity(root_ecs_id, ecs_id)
```

### 2. Tool Implementation Pattern
```python
from pydantic_ai.toolsets.function import FunctionToolset

registry_toolset = FunctionToolset()

@registry_toolset.tool
async def execute_function(
    ctx: RunContext[RegistryDependencies], 
    function_name: str, 
    **kwargs
) -> str:
    """Execute a registered function with string addressing support."""
    try:
        result = ctx.deps.execute_function(function_name, **kwargs)
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

### 3. Agent Setup
```python
agent = Agent(
    'anthropic:claude-sonnet-4-20250514',
    deps_type=RegistryDependencies,
    output_type=str,
    toolsets=[registry_toolset],
    system_prompt="""
    You are an assistant for the Abstractions Entity Framework.
    You can execute registered functions, query entity lineages, and access distributed data.
    
    Available capabilities:
    - execute_function(function_name, **kwargs) - Run registered functions
    - list_functions() - Show available functions  
    - get_entity(root_ecs_id, ecs_id) - Retrieve entities
    - get_lineages() - Show entity version history
    
    Use @uuid.field syntax for entity addressing in function parameters.
    """
)

# Usage
dependencies = RegistryDependencies()
result = agent.run_sync(
    "Execute the update_gpa function with student @abc-123 and new_gpa 3.8",
    deps=dependencies
)
```

## Next Implementation Steps

1. **Create RegistryDependencies class** - Wrapper around CallableRegistry and EntityRegistry
2. **Build FunctionToolset with 6 core tools** - Using correct `@toolset.tool` pattern
3. **Research EntityRegistry retrieval methods** - Find actual API for get_stored_entity etc.
4. **Test with simple examples** - Validate integration works with actual framework
5. **Add event system access** - Provide access to event bus state if needed

This approach keeps the integration external to abstractions while providing natural language access to the full framework capabilities.