# Automatic Event Nesting Implementation Plan

## Current State Analysis

### Current Event System (`events.py`)
- **`emit_events` decorator**: Lines 883-1021 - handles sync/async method wrapping
- **Parent-child support**: `parent_id`, `root_id`, `lineage_id` fields exist
- **EventBus tracking**: Lines 532-562 - tracks parent-child relationships in `_emit_internal`
- **No automatic nesting**: Each decorator creates independent events

### Current Entity System (`entity.py`)
- **Decorated methods**: 
  - `version_entity` (lines 1501-1506): calls other methods
  - `promote_to_root` (lines 1797-1800): calls `EntityRegistry.register_entity`
- **Method calling chains**: `promote_to_root` → `EntityRegistry.register_entity` → `version_entity`
- **Factory functions**: Already created (lines 29-101)

## Problem Statement

When `promote_to_root()` calls `EntityRegistry.register_entity()` which calls `version_entity()`, we get:
```
Independent Event A (promotion)
Independent Event B (registration) 
Independent Event C (versioning)
```

Instead of the desired hierarchy:
```
PromotionEvent (root)
  └── RegistrationEvent (child)
      └── VersioningEvent (child)
```

## Solution: Context Stack with `contextvars`

### Phase 1: Context Management Infrastructure

**File**: `abstractions/events/context.py` (new file)

```python
import contextvars
from typing import List, Optional
from uuid import UUID

# Context variable for event nesting
_event_context_stack: contextvars.ContextVar[List['Event']] = contextvars.ContextVar(
    'event_context_stack', 
    default=[]
)

def get_current_parent_event() -> Optional['Event']:
    """Get the current parent event from context stack."""
    stack = _event_context_stack.get()
    return stack[-1] if stack else None

def push_event_context(event: 'Event') -> None:
    """Push event onto context stack."""
    current_stack = _event_context_stack.get()
    _event_context_stack.set(current_stack + [event])

def pop_event_context() -> Optional['Event']:
    """Pop event from context stack."""
    current_stack = _event_context_stack.get()
    if current_stack:
        _event_context_stack.set(current_stack[:-1])
        return current_stack[-1]
    return None

def get_context_depth() -> int:
    """Get current nesting depth."""
    return len(_event_context_stack.get())

def clear_context() -> None:
    """Clear context stack (for testing)."""
    _event_context_stack.set([])
```

### Phase 2: Enhanced `emit_events` Decorator

**File**: `abstractions/events/events.py` (modifications)

**Current decorator** (lines 883-1021) needs these changes:

```python
# Add import at top
from abstractions.events.context import (
    get_current_parent_event, push_event_context, pop_event_context
)

def emit_events(
    creating_factory: Optional[Callable[..., Event]] = None,
    created_factory: Optional[Callable[..., Event]] = None,
    failed_factory: Optional[Callable[..., Event]] = None,
    include_timing: bool = True,
    include_args: bool = False,
    auto_parent: bool = True  # NEW: Enable/disable automatic parent linking
) -> Callable:
    """
    Enhanced decorator with automatic parent-child event linking.
    
    Args:
        auto_parent: Whether to automatically link to parent events in context
    """
    def decorator(func: Callable) -> Callable:
        is_async = inspect.iscoroutinefunction(func)
        
        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                bus = get_event_bus()
                start_time = time.time()
                
                # Get current parent from context
                parent_event = get_current_parent_event() if auto_parent else None
                
                # Create starting event
                start_event = None
                if creating_factory:
                    start_event = creating_factory(*args, **kwargs)
                    
                    # Auto-link to parent
                    if parent_event:
                        start_event.parent_id = parent_event.id
                        start_event.root_id = parent_event.root_id or parent_event.id
                        start_event.lineage_id = parent_event.lineage_id
                    else:
                        start_event.root_id = start_event.id
                    
                    # Push to context stack
                    push_event_context(start_event)
                    
                    if include_args:
                        start_event.metadata['args'] = str(args)
                        start_event.metadata['kwargs'] = str(kwargs)
                    
                    await bus.emit(start_event)
                    lineage_id = start_event.lineage_id
                else:
                    lineage_id = uuid4()
                
                try:
                    # Execute method (nested calls will see current event as parent)
                    result = await func(*args, **kwargs)
                    
                    # Create completion event
                    if created_factory:
                        end_event = created_factory(result, *args, **kwargs)
                        end_event.lineage_id = lineage_id
                        
                        # Auto-link completion event to parent
                        if parent_event:
                            end_event.parent_id = parent_event.id
                            end_event.root_id = parent_event.root_id or parent_event.id
                        
                        if include_timing:
                            end_event.duration_ms = (time.time() - start_time) * 1000
                        
                        await bus.emit(end_event)
                    
                    return result
                    
                except Exception as e:
                    # Create failure event (also auto-linked)
                    if failed_factory:
                        error_event = failed_factory(e, *args, **kwargs)
                        error_event.lineage_id = lineage_id
                        
                        if parent_event:
                            error_event.parent_id = parent_event.id
                            error_event.root_id = parent_event.root_id or parent_event.id
                        
                        if include_timing:
                            error_event.duration_ms = (time.time() - start_time) * 1000
                        
                        await bus.emit(error_event)
                    raise
                
                finally:
                    # Pop from context stack
                    if start_event:
                        pop_event_context()
            
            return async_wrapper
        
        else:
            # Similar changes for sync wrapper
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                # ... similar implementation for sync methods
                pass
            
            return sync_wrapper
    
    return decorator
```

### Phase 3: Update Entity Decorators

**File**: `abstractions/ecs/entity.py` (modifications)

**Keep existing decorators simple** - they'll automatically get nesting:

```python
# Lines 1501-1506 (version_entity) - NO CHANGES NEEDED
@classmethod
@emit_events(
    creating_factory=lambda cls, entity, force_versioning=False:
        create_versioning_event(entity, force_versioning),
    created_factory=lambda result, cls, entity, force_versioning=False:
        create_versioned_event(result, entity, force_versioning)
)
def version_entity(cls, entity: "Entity", force_versioning: bool = False) -> bool:
    # Method unchanged - automatic nesting will work

# Lines 1797-1800 (promote_to_root) - NO CHANGES NEEDED  
@emit_events(
    creating_factory=lambda self: create_promotion_event(self),
    created_factory=lambda self: create_promoted_event(self)
)
def promote_to_root(self) -> None:
    # Method unchanged - when this calls EntityRegistry.register_entity,
    # the registration events will automatically be children
```

### Phase 4: Test the Automatic Nesting

**File**: `test_automatic_nesting.py` (new file)

```python
import asyncio
from abstractions.ecs.entity import Entity, EntityRegistry
from abstractions.events.events import get_event_bus, on
from abstractions.events.context import clear_context

async def test_nested_events():
    """Test that method calls create properly nested events."""
    
    # Clear context and start event bus
    clear_context()
    bus = get_event_bus()
    await bus.start()
    
    # Collect all events
    events = []
    
    @on(predicate=lambda e: True)
    async def collect_all_events(event):
        events.append(event)
        print(f"Event: {event.type} | Parent: {event.parent_id} | Root: {event.root_id}")
    
    # Create entity and promote to root
    entity = Entity()
    entity.promote_to_root()  # This calls EntityRegistry.register_entity -> version_entity
    
    # Wait for events
    await asyncio.sleep(0.1)
    
    # Analyze event hierarchy
    root_events = [e for e in events if e.parent_id is None]
    child_events = [e for e in events if e.parent_id is not None]
    
    print(f"\nRoot events: {len(root_events)}")
    print(f"Child events: {len(child_events)}")
    
    # Verify proper nesting
    assert len(root_events) == 2, f"Expected 2 root events, got {len(root_events)}"  # promotion start + end
    assert len(child_events) > 0, "Expected child events from registration/versioning"
    
    # Verify parent-child relationships
    for child in child_events:
        assert child.parent_id is not None, "Child event should have parent_id"
        assert child.root_id is not None, "Child event should have root_id"
        
        # Find parent
        parent = next((e for e in events if e.id == child.parent_id), None)
        assert parent is not None, f"Parent event {child.parent_id} not found"
        assert child.root_id == parent.root_id, "Child and parent should share root_id"
    
    await bus.stop()
    print("✅ Automatic nesting test passed!")

if __name__ == "__main__":
    asyncio.run(test_nested_events())
```

### Phase 5: Integration with Existing System

**Key Integration Points:**

1. **`contextvars` Benefits**:
   - **Async-safe**: Each async task gets isolated context
   - **Thread-safe**: Each thread gets isolated context  
   - **Automatic cleanup**: Context cleaned up when tasks complete

2. **Backward Compatibility**:
   - Existing decorators work unchanged
   - `auto_parent=False` disables nesting if needed
   - No changes to event structure

3. **Performance Impact**:
   - Minimal: O(1) context operations
   - Small memory footprint (typically 1-3 events in stack)
   - No additional network or I/O overhead

### Phase 6: Expected Results

**Before automatic nesting:**
```
PromotionEvent (independent)
RegistrationEvent (independent) 
VersioningEvent (independent)
```

**After automatic nesting:**
```
PromotionEvent (root_id: A, parent_id: None)
  └── RegistrationEvent (root_id: A, parent_id: A)
      └── VersioningEvent (root_id: A, parent_id: B)
  └── PromotionCompletedEvent (root_id: A, parent_id: None)
```

**Event Bus Statistics:**
- Total events: Same number
- Parent-child relationships: Properly established
- Event hierarchy: Complete and accurate
- Performance: No degradation

## Implementation Priority

1. **Phase 1** (High): Context management infrastructure
2. **Phase 2** (High): Enhanced `emit_events` decorator  
3. **Phase 3** (Medium): Update existing decorators (optional - they work as-is)
4. **Phase 4** (Medium): Comprehensive testing
5. **Phase 5** (Low): Performance optimization and monitoring

## Risk Mitigation

1. **Context leaks**: Use `finally` blocks to ensure context cleanup
2. **Performance**: Monitor context stack depth and size
3. **Testing**: Extensive async/sync testing with nested calls
4. **Rollback**: `auto_parent=False` provides immediate rollback

This implementation will solve the integration problems by providing automatic, transparent event nesting that maintains the existing decorator API while adding powerful parent-child relationship tracking.