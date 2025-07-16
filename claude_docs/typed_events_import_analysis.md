# Typed Events Import Analysis: Avoiding Circular Dependencies

## Current Import Hierarchy Problem

```
abstractions/events/events.py (base events)
    ↑
abstractions/ecs/entity.py (imports events.py, defines Entity)
    ↑
abstractions/ecs/callable_registry.py (imports entity.py, imports events.py)
```

## The Challenge

Specialized event subclasses need to reference:
- `Entity` type (from entity.py)
- `ConfigEntity` type (from entity.py)
- `FunctionMetadata` type (from callable_registry.py)
- `UUID`, `Type`, `List`, etc. (from standard library)

If we put specialized events in `abstractions/events/typed_events.py`, we risk circular imports:
```
entity.py → typed_events.py → entity.py  # CIRCULAR!
```

## Solution: Forward References with TYPE_CHECKING

### New File Structure
```
abstractions/events/
├── events.py (base events)
├── typed_events.py (specialized events + factories)
└── ...

abstractions/ecs/
├── entity.py (imports typed_events.py)
├── callable_registry.py (imports typed_events.py)
└── ...
```

### Import Strategy in typed_events.py

```python
# abstractions/events/typed_events.py
from typing import TYPE_CHECKING, Type, List, Dict, Optional, Any
from uuid import UUID
from datetime import datetime

# Base events (no circular dependency)
from abstractions.events.events import (
    ProcessingEvent, ProcessedEvent, ModifyingEvent, ModifiedEvent, 
    StateTransitionEvent
)

# Forward references to avoid circular imports
if TYPE_CHECKING:
    from abstractions.ecs.entity import Entity, ConfigEntity
    from abstractions.ecs.callable_registry import FunctionMetadata
else:
    # Runtime placeholders
    Entity = Any
    ConfigEntity = Any
    FunctionMetadata = Any
```

### Event Class Definitions with String Types

```python
# Entity versioning events
class EntityVersioningEvent(ModifyingEvent):
    """Event for entity versioning operations."""
    subject_type: Type['Entity']  # String reference
    subject_id: UUID
    versioning_type: str  # "normal", "forced", "initial_registration"
    force_versioning: bool
    has_modifications: bool
    modified_entity_count: int
    tree_root_id: UUID
    lineage_id: UUID

class EntityVersionedEvent(ModifiedEvent):
    """Event for completed entity versioning."""
    subject_type: Type['Entity']  # String reference
    subject_id: UUID
    versioning_type: str
    force_versioning: bool
    version_created: bool
    new_root_id: UUID
    modified_entity_ids: List[UUID]
    id_mapping: Dict[UUID, UUID]
    versioning_duration: float
    tree_consistency_validated: bool

# Function execution events
class SingleEntityDirectProcessingEvent(ProcessingEvent):
    """Event for single entity direct execution pattern."""
    subject_type: Type['Entity']  # String reference
    subject_id: UUID
    execution_strategy: str = "single_entity_direct"
    primary_entity_type: Type['Entity']  # String reference
    primary_entity_id: UUID
    function_name: str
    expected_return_type: str

class SingleEntityWithConfigProcessingEvent(ProcessingEvent):
    """Event for single entity with config execution pattern."""
    subject_type: Type['Entity']  # String reference
    subject_id: UUID
    execution_strategy: str = "single_entity_with_config"
    primary_entity_type: Type['Entity']  # String reference
    primary_entity_id: UUID
    config_entity_type: Optional[Type['ConfigEntity']]  # String reference
    config_entity_id: Optional[UUID]
    primitive_params: Dict[str, Any]
    function_name: str
    uses_functools_partial: bool

# ... more event classes
```

### Factory Classes in typed_events.py

```python
class EntityEventFactory:
    """Factory for creating specialized entity events."""
    
    @staticmethod
    def create_versioning_event(entity: 'Entity', force_versioning: bool) -> EntityVersioningEvent:
        """Create appropriate versioning event based on entity state."""
        # Use runtime type() function to get actual type
        return EntityVersioningEvent(
            subject_type=type(entity),  # Runtime type resolution
            subject_id=entity.ecs_id,
            versioning_type="forced" if force_versioning else "normal",
            force_versioning=force_versioning,
            has_modifications=True,
            modified_entity_count=1,
            tree_root_id=entity.root_ecs_id or entity.ecs_id,
            lineage_id=entity.lineage_id
        )
    
    @staticmethod
    def create_versioned_event(result: bool, entity: 'Entity', force_versioning: bool) -> EntityVersionedEvent:
        """Create versioned event after operation completion."""
        return EntityVersionedEvent(
            subject_type=type(entity),  # Runtime type resolution
            subject_id=entity.ecs_id,
            versioning_type="forced" if force_versioning else "normal",
            force_versioning=force_versioning,
            version_created=result,
            new_root_id=entity.ecs_id,
            modified_entity_ids=[entity.ecs_id],
            id_mapping={},
            versioning_duration=0.0,
            tree_consistency_validated=True
        )

class FunctionExecutionEventFactory:
    """Factory for creating specialized function execution events."""
    
    @staticmethod
    def create_processing_event(
        strategy: str,
        func_name: str,
        kwargs: Dict[str, Any],
        metadata: Optional['FunctionMetadata'] = None
    ) -> ProcessingEvent:
        """Create strategy-specific processing event."""
        
        if strategy == "single_entity_direct":
            entity = next(v for v in kwargs.values() if hasattr(v, 'ecs_id'))
            return SingleEntityDirectProcessingEvent(
                subject_type=type(entity),  # Runtime type resolution
                subject_id=entity.ecs_id,
                primary_entity_type=type(entity),
                primary_entity_id=entity.ecs_id,
                function_name=func_name,
                expected_return_type="Entity"
            )
        
        elif strategy == "single_entity_with_config":
            entity = next((v for v in kwargs.values() if hasattr(v, 'ecs_id') and not hasattr(v, '__bases__')), None)
            config_entity = next((v for v in kwargs.values() if hasattr(v, '__bases__') and 'ConfigEntity' in str(v.__class__.__bases__)), None)
            
            primitives = {k: v for k, v in kwargs.items() 
                         if not hasattr(v, 'ecs_id')}
            
            return SingleEntityWithConfigProcessingEvent(
                subject_type=type(entity) if entity else None,
                subject_id=entity.ecs_id if entity else None,
                primary_entity_type=type(entity) if entity else None,
                primary_entity_id=entity.ecs_id if entity else None,
                config_entity_type=type(config_entity) if config_entity else None,
                config_entity_id=config_entity.ecs_id if config_entity else None,
                primitive_params=primitives,
                function_name=func_name,
                uses_functools_partial=True
            )
        
        # Fallback to generic event
        return ProcessingEvent(
            subject_type=None,
            subject_id=None,
            process_name="function_execution",
            metadata={"function_name": func_name}
        )
```

### Updated Imports in entity.py

```python
# abstractions/ecs/entity.py
from abstractions.events.typed_events import (
    EntityEventFactory, EntityVersioningEvent, EntityVersionedEvent,
    EntityPromotionEvent, EntityAttachmentEvent, EntityDetachmentEvent
)

# Updated decorator
@emit_events(
    creating_factory=lambda cls, entity, force_versioning=False: 
        EntityEventFactory.create_versioning_event(entity, force_versioning),
    created_factory=lambda result, cls, entity, force_versioning=False:
        EntityEventFactory.create_versioned_event(result, entity, force_versioning)
)
def version_entity(cls, entity: "Entity", force_versioning: bool = False) -> bool:
    # ... existing implementation
```

### Updated Imports in callable_registry.py

```python
# abstractions/ecs/callable_registry.py
from abstractions.events.typed_events import (
    FunctionExecutionEventFactory, SingleEntityDirectProcessingEvent,
    SingleEntityWithConfigProcessingEvent, # ... other specialized events
)

# Updated decorator
@emit_events(
    creating_factory=lambda cls, func_name, **kwargs: 
        FunctionExecutionEventFactory.create_processing_event(
            cls._detect_execution_strategy(kwargs, cls.get_metadata(func_name)),
            func_name,
            kwargs,
            cls.get_metadata(func_name)
        ),
    created_factory=lambda result, cls, func_name, **kwargs:
        FunctionExecutionEventFactory.create_processed_event(
            result, func_name, kwargs
        )
)
async def aexecute(cls, func_name: str, **kwargs):
    # ... existing implementation
```

## Benefits of This Approach

1. **No Circular Imports**: typed_events.py doesn't import entity.py at runtime
2. **Type Safety**: Full type checking support with TYPE_CHECKING imports
3. **Centralized Events**: All specialized events in one place
4. **Clean Architecture**: Clear separation of concerns
5. **Maintainable**: Easy to add new specialized events

## Runtime Type Resolution

The factories use `type(entity)` at runtime to get actual types, avoiding the need for compile-time type imports. This ensures events contain the correct type information while maintaining import safety.

This architecture allows both entity.py and callable_registry.py to import rich, specialized events without circular dependencies.