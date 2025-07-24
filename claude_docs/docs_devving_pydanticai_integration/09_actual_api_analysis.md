# Actual Abstractions API Analysis

## Research Method

This analysis is based on studying the actual codebase files:
- `/abstractions/ecs/entity.py` (EntityRegistry implementation)
- `/abstractions/ecs/callable_registry.py` (CallableRegistry implementation) 
- `/abstractions/events/events.py` (Event system)
- `/examples/readme_examples/01_basic_entity_transformation.py` (Usage patterns)

## Correct API Structure

### CallableRegistry API

The `CallableRegistry` is the main function execution engine:

```python
from abstractions.ecs.callable_registry import CallableRegistry

class CallableRegistry:
    _functions: Dict[str, FunctionMetadata] = {}
    
    @classmethod
    def execute(cls, func_name: str, **kwargs) -> Union[Entity, List[Entity]]:
        """Execute function using entity-native patterns (sync wrapper)."""
        
    @classmethod  
    async def aexecute(cls, func_name: str, **kwargs) -> Union[Entity, List[Entity]]:
        """Execute function asynchronously."""
        
    @classmethod
    def list_functions(cls) -> List[str]:
        """List all registered functions."""
        
    @classmethod
    def get_metadata(cls, name: str) -> Optional[FunctionMetadata]:
        """Get function metadata."""
        
    @classmethod
    def get_function_info(cls, name: str) -> Optional[Dict[str, Any]]:
        """Get detailed function information."""
```

### EntityRegistry API

The `EntityRegistry` manages entity storage and versioning:

```python
from abstractions.ecs.entity import EntityRegistry

class EntityRegistry:
    # Class attributes (not instance attributes!)
    tree_registry: Dict[UUID, EntityTree] = {}
    lineage_registry: Dict[UUID, List[UUID]] = {}  # lineage_id -> [root_ecs_ids]
    live_id_registry: Dict[UUID, Entity] = {}
    ecs_id_to_root_id: Dict[UUID, UUID] = {}
    type_registry: Dict[Type[Entity], List[UUID]] = {}
    
    @classmethod
    def register_entity_tree(cls, entity_tree: EntityTree) -> None:
        """Register an entity tree in the registry."""
        
    # Other methods to be discovered...
```

### Event System API

```python
from abstractions.events.events import get_event_bus, on, emit

# Global event bus
def get_event_bus() -> EventBus:
    """Get or create the global event bus instance."""

# Event handlers
@on(EventType)
async def handler(event: EventType):
    """Handle events with decorator pattern."""
```

### Correct Pydantic-AI Imports

Based on research in the pydantic-ai documentation:

```python
from pydantic_ai import Agent, RunContext
# NOT: from pydantic_ai import FunctionToolset  # This doesn't exist!
```

## Key Corrections Needed

### 1. Wrong Pydantic-AI Import
**Error**: `from pydantic_ai import FunctionToolset`
**Correct**: Need to research the actual toolset import pattern

### 2. Wrong Registry Access Pattern  
**Error**: `registry.callable_registry.functions`
**Correct**: `CallableRegistry.list_functions()` (separate class)

### 3. Wrong EntityRegistry Attributes
**Error**: `registry.lineage_to_root_ids` 
**Correct**: `EntityRegistry.lineage_registry` (class attribute)

### 4. Missing Entity Retrieval Methods
Need to find the actual methods for:
- Getting entities by ID
- Getting entities from trees
- Retrieving lineage history

## Next Research Steps

1. **Find correct pydantic-ai toolset pattern** - grep for toolset examples
2. **Discover EntityRegistry retrieval methods** - find get_entity, get_stored_entity patterns
3. **Understand dependency injection** - how to pass registry to tools
4. **Event system integration** - how to access event state

## Usage Pattern from Examples

From `01_basic_entity_transformation.py`:

```python
# Function registration
@CallableRegistry.register("update_gpa")
def update_gpa(student: Student, new_gpa: float) -> Student:
    student.gpa = new_gpa
    return student

# Function execution  
result = CallableRegistry.execute("update_gpa", student=student, new_gpa=3.8)

# Registry queries
functions = CallableRegistry.list_functions()
metadata = CallableRegistry.get_metadata("update_gpa")
```

This shows the CallableRegistry is the primary interface, not a sub-component of EntityRegistry.