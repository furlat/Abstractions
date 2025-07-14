# Event Decorator Integration Plan

## Overview
Integrate event decorators directly into CallableRegistry and Entity classes to automatically emit events for all operations, eliminating the need for manual event emission via bridge functions.

## Current State
- ✅ Event decorators available in `abstractions/events/events.py`:
  - `@on` - Event subscription
  - `@emit_events` - Method event emission
  - `@track_state_transition` - State change tracking
  - `@create_event_chain` - Event chain creation
- ✅ Bridge functions working in `abstractions/events/bridge.py`
- ✅ CallableRegistry entity-native pattern working perfectly
- ✅ Entity lifecycle methods (promote_to_root, detach, attach) working

## Phase 1: CallableRegistry Event Integration

### 1.1 Function Registration Events
**File**: `abstractions/ecs/callable_registry.py`
**Method**: `register()` decorator (lines 303-350)

**Changes**:
```python
@classmethod
def register(cls, name: str) -> Callable:
    """Register functions with automatic event emission."""
    
    def decorator(func: Callable) -> Callable:
        # Existing registration logic...
        
        # ADD: Emit function registration event
        from abstractions.events.bridge import emit_creation_events
        
        # Create function metadata entity for event
        func_entity = Entity()
        func_entity.function_name = name
        func_entity.function_signature = str(signature(func))
        func_entity.promote_to_root()
        
        # Emit registration event asynchronously
        async def emit_registration():
            await emit_creation_events(func_entity, f"function_registered_{name}")
        
        # Schedule emission (don't block registration)
        asyncio.create_task(emit_registration())
        
        return func
```

### 1.2 Function Execution Events
**File**: `abstractions/ecs/callable_registry.py`
**Method**: `aexecute()` (lines 358-361)

**Changes**:
```python
@classmethod
@emit_events(
    creating_factory=lambda cls, func_name, **kwargs: ProcessingEvent(
        subject_type=Entity,
        subject_id=uuid4(),
        process_name=f"execute_{func_name}",
        metadata={"function_name": func_name, "input_count": len(kwargs)}
    ),
    created_factory=lambda result, cls, func_name, **kwargs: ProcessedEvent(
        subject_type=type(result[0]) if isinstance(result, list) else type(result),
        subject_id=result[0].ecs_id if isinstance(result, list) else result.ecs_id,
        process_name=f"execute_{func_name}",
        result_summary={"output_count": len(result) if isinstance(result, list) else 1}
    )
)
async def aexecute(cls, func_name: str, **kwargs) -> Union[Entity, List[Entity]]:
    """Execute function with automatic event emission."""
    return await cls._execute_async(func_name, **kwargs)
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
from abstractions.events.bridge import emit_creation_events
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

## Implementation Order
1. CallableRegistry.register() - function registration events
2. CallableRegistry.aexecute() - function execution events  
3. Entity.promote_to_root() - entity promotion events
4. Entity.detach() - entity detachment events
5. Entity.attach() - entity attachment events
6. EntityRegistry.version_entity() - entity versioning events
7. Testing and validation