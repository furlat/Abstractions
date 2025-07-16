# Event Decorator Integration Plan (ACTUALLY CORRECTED)

## Overview
After reviewing the shame file, the correct approach is:
1. **CallableRegistry operations**: DON'T use decorators - use bridge functions for operations that need events
2. **Entity lifecycle methods**: Use decorators on actual entity state transitions
3. **Function execution**: Only emit events about actual entities being processed, not synthetic tracking entities

## Current State
- ✅ Event decorators available in `abstractions/events/events.py`
- ✅ Bridge functions working in `abstractions/events/bridge.py`
- ✅ CallableRegistry entity-native pattern working perfectly
- ✅ Entity lifecycle methods (promote_to_root, detach, attach) working

## CORRECTED Phase 1: CallableRegistry Event Integration

### 1.1 Function Registration Events
**CORRECT APPROACH**: Function registration is a **registry operation**, NOT an entity operation.

**DON'T ADD DECORATORS** - Instead, use bridge functions when applications need to track function registrations:

```python
# Application code that needs to track registrations:
@CallableRegistry.register("my_function")
def my_function(...):
    pass

# Then if needed, emit events about the registration:
await emit_processing_events(
    operation_name="function_registered",
    metadata={"function_name": "my_function"}
)
```

### 1.2 Function Execution Events  
**CORRECT APPROACH**: Only emit events about the **actual input/output entities**, not synthetic tracking entities.

**DON'T ADD DECORATORS** - Instead, applications can use bridge functions with actual entities:

```python
# In application code:
result = await CallableRegistry.aexecute("my_function", input_entity=my_entity)

# Then emit events about the actual entities processed:
await emit_processing_events(
    my_entity,  # Real input entity
    operation_name="function_executed",
    metadata={"function_name": "my_function"}
)
```

## Phase 2: Entity Lifecycle Event Integration

### 2.1 Entity Promotion Events
**File**: `abstractions/ecs/entity.py`
**Method**: `promote_to_root()` (lines 1702-1709)

**Changes**:
```python
@emit_events(
    creating_factory=lambda self: StateTransitionEvent(
        subject_type=type(self),
        subject_id=self.ecs_id,
        from_state="child_entity",
        to_state="root_entity",
        transition_reason="promotion"
    )
)
def promote_to_root(self) -> None:
    """Promote entity to root with automatic event emission."""
    self.root_ecs_id = self.ecs_id
    self.root_live_id = self.live_id
    self.update_ecs_ids()
    EntityRegistry.register_entity(self)
```

### 2.2 Entity Detachment Events
**File**: `abstractions/ecs/entity.py`
**Method**: `detach()` (lines 1711-1742)

**Changes**:
```python
@emit_events(
    creating_factory=lambda self: StateTransitionEvent(
        subject_type=type(self),
        subject_id=self.ecs_id,
        from_state="attached_entity",
        to_state="detached_entity",
        transition_reason="detachment"
    )
)
def detach(self) -> None:
    """Detach entity with automatic event emission."""
    # Existing detachment logic...
```

### 2.3 Entity Attachment Events
**File**: `abstractions/ecs/entity.py`
**Method**: `attach()` (lines 1816-1847)

**Changes**:
```python
@emit_events(
    creating_factory=lambda self, new_root_entity: StateTransitionEvent(
        subject_type=type(self),
        subject_id=self.ecs_id,
        from_state="root_entity",
        to_state="attached_entity",
        transition_reason="attachment",
        metadata={"new_root_id": str(new_root_entity.ecs_id)}
    )
)
def attach(self, new_root_entity: "Entity") -> None:
    """Attach entity with automatic event emission."""
    # Existing attachment logic...
```

### 2.4 Entity Versioning Events
**File**: `abstractions/ecs/entity.py`
**Method**: `EntityRegistry.version_entity()` (lines 1412-1485)

**Changes**:
```python
@classmethod
@emit_events(
    creating_factory=lambda cls, entity: ModifyingEvent(
        subject_type=type(entity),
        subject_id=entity.ecs_id,
        fields=["ecs_id", "version"],
        operation_name="versioning"
    ),
    created_factory=lambda result, cls, entity: ModifiedEvent(
        subject_type=type(entity),
        subject_id=entity.ecs_id,
        fields=["ecs_id", "version"],
        operation_name="versioning"
    )
)
def version_entity(cls, entity: "Entity", force_versioning: bool = False) -> bool:
    """Version entity with automatic event emission."""
    # Existing versioning logic...
```

## Phase 3: Import Integration

### 3.1 Add Event Imports
**File**: `abstractions/ecs/callable_registry.py` (top of file)
```python
# ADD these imports:
from abstractions.events.events import emit_events, ProcessingEvent, ProcessedEvent
# NOTE: No bridge imports needed - we're using decorators directly
```

**File**: `abstractions/ecs/entity.py` (top of file)
```python
# ADD these imports:
from abstractions.events.events import emit_events, StateTransitionEvent, ModifyingEvent, ModifiedEvent
```

## Phase 4: Testing Strategy

### 4.1 Compatibility Testing
- Run existing shame file to ensure no conflicts
- Verify bridge functions still work alongside decorators
- Test event emission count (should not double-emit)

### 4.2 Performance Testing
- Measure event emission overhead
- Test async event emission doesn't block operations
- Verify decorator overhead is minimal

## Phase 5: Documentation Update

### 5.1 Update Integration Example
- Modify shame file to show decorator usage
- Add examples of automatic vs manual event emission
- Document best practices

## Expected Benefits
1. **Automatic Event Emission**: All ECS operations emit events without manual calls
2. **Reduced Boilerplate**: No need for bridge function calls in application code
3. **Consistency**: All operations automatically tracked
4. **Observability**: Complete audit trail without developer intervention
5. **Backward Compatibility**: Bridge functions still work for custom events

## Risk Mitigation
- Decorators are additive - existing code continues to work
- Event emission is async and non-blocking
- Bridge functions remain available for custom events
- All changes are in method signatures, not core logic
- **NO SYNTHETIC ENTITIES**: Events observe existing operations, don't create fake entities

## Implementation Order
1. ~~CallableRegistry.register() - DON'T ADD DECORATORS~~ (Use bridge functions in applications)
2. ~~CallableRegistry.aexecute() - DON'T ADD DECORATORS~~ (Use bridge functions in applications)
3. Entity.promote_to_root() - entity promotion events (CORRECT - add decorators)
4. Entity.detach() - entity detachment events (CORRECT - add decorators)
5. Entity.attach() - entity attachment events (CORRECT - add decorators)
6. EntityRegistry.version_entity() - entity versioning events (CORRECT - add decorators)
7. Testing and validation

## Key Corrections Made
- **Function Registration**: DON'T use decorators - registry operations aren't entity operations
- **Function Execution**: DON'T use decorators - let applications emit events about actual entities
- **Entity Operations**: ADD decorators for actual entity lifecycle events
- **No Synthetic Entities**: Never create entities just to satisfy event system requirements

## The Shame File Lesson
The shame file shows that **only actual entity operations** should have automatic event emission via decorators. Registry operations should use bridge functions when applications need events, not automatic decoration.