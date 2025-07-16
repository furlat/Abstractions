# Automatic Event Nesting Implementation

## Core Concept: Context Stack

Use `contextvars` to maintain a stack of currently active events. When a decorated method calls another decorated method, the child event automatically inherits the parent context.

## Implementation

### 1. Context Management

```python
import contextvars
from typing import List, Optional

# Context variable to track event stack
_event_context: contextvars.ContextVar[List[Event]] = contextvars.ContextVar('event_context', default=[])

def get_current_parent_event() -> Optional[Event]:
    """Get the current parent event from the context stack."""
    stack = _event_context.get()
    return stack[-1] if stack else None

def push_event_context(event: Event) -> None:
    """Push an event onto the context stack."""
    current_stack = _event_context.get()
    _event_context.set(current_stack + [event])

def pop_event_context() -> Optional[Event]:
    """Pop an event from the context stack."""
    current_stack = _event_context.get()
    if current_stack:
        _event_context.set(current_stack[:-1])
        return current_stack[-1]
    return None
```

### 2. Enhanced emit_events Decorator

```python
def emit_events(
    creating_factory: Optional[Callable[..., Event]] = None,
    created_factory: Optional[Callable[..., Event]] = None,
    failed_factory: Optional[Callable[..., Event]] = None,
    include_timing: bool = True,
    include_args: bool = False,
    auto_parent: bool = True  # New parameter for automatic parent linking
) -> Callable:
    """
    Decorator that emits events around method execution with automatic nesting.
    
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
                
                # Get current parent context
                parent_event = get_current_parent_event() if auto_parent else None
                
                # Create starting event
                if creating_factory:
                    start_event = creating_factory(*args, **kwargs)
                    
                    # Automatic parent linking
                    if parent_event:
                        start_event.parent_id = parent_event.id
                        start_event.root_id = parent_event.root_id or parent_event.id
                        start_event.lineage_id = parent_event.lineage_id  # Same lineage
                    else:
                        start_event.root_id = start_event.id
                    
                    # Add to context stack
                    push_event_context(start_event)
                    
                    if include_args:
                        start_event.metadata['args'] = str(args)
                        start_event.metadata['kwargs'] = str(kwargs)
                    
                    await bus.emit(start_event)
                    lineage_id = start_event.lineage_id
                else:
                    lineage_id = uuid4()
                    start_event = None
                
                try:
                    # Execute method (any nested decorated calls will see this as parent)
                    result = await func(*args, **kwargs)
                    
                    # Create completion event
                    if created_factory:
                        end_event = created_factory(result, *args, **kwargs)
                        end_event.lineage_id = lineage_id
                        
                        # Automatic parent linking for completion event
                        if parent_event:
                            end_event.parent_id = parent_event.id
                            end_event.root_id = parent_event.root_id or parent_event.id
                        
                        if include_timing:
                            end_event.duration_ms = (time.time() - start_time) * 1000
                        
                        await bus.emit(end_event)
                    
                    return result
                    
                except Exception as e:
                    # Create failure event
                    if failed_factory:
                        error_event = failed_factory(e, *args, **kwargs)
                        error_event.lineage_id = lineage_id
                        
                        # Automatic parent linking for error event
                        if parent_event:
                            error_event.parent_id = parent_event.id
                            error_event.root_id = parent_event.root_id or parent_event.id
                        
                        if include_timing:
                            error_event.duration_ms = (time.time() - start_time) * 1000
                        
                        await bus.emit(error_event)
                    raise
                
                finally:
                    # Remove from context stack
                    if start_event:
                        pop_event_context()
            
            return async_wrapper
        
        else:
            # Similar implementation for sync functions
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Same logic but without await
                # ... implementation ...
                pass
            
            return sync_wrapper
    
    return decorator
```

### 3. Automatic Nesting in Action

```python
class Entity:
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
        """This will be the root event."""
        # This calls version_entity, which will automatically be a child event
        EntityRegistry.version_entity(self)
    
    @classmethod
    @emit_events(
        creating_factory=lambda cls, entity, force_versioning=False: ModifyingEvent(
            subject_type=type(entity),
            subject_id=entity.ecs_id,
            fields=["ecs_id", "version"]
        )
    )
    def version_entity(cls, entity: "Entity", force_versioning: bool = False) -> bool:
        """This will automatically be a child of promote_to_root."""
        # Do versioning work
        return True
```

### 4. Event Hierarchy Result

When `promote_to_root()` is called, the event hierarchy will be:

```
PromotionEvent (root_id: A, parent_id: None)
  └── VersioningEvent (root_id: A, parent_id: A)
      └── VersionedEvent (root_id: A, parent_id: A)
  └── PromotedEvent (root_id: A, parent_id: None)
```

## Benefits

1. **Automatic**: No manual parent-child specification
2. **Transparent**: Existing decorated methods work without changes
3. **Correct Hierarchy**: Events form proper parent-child trees
4. **Async-Safe**: Uses `contextvars` which work correctly with async/await
5. **Opt-Out**: Can disable with `auto_parent=False` if needed

## Context Variable Behavior

`contextvars` automatically handles:
- **Async Task Isolation**: Each async task gets its own context
- **Thread Safety**: Each thread gets its own context
- **Proper Scoping**: Context is automatically cleaned up when tasks complete

## Error Handling

If an exception occurs:
1. Error event is created with proper parent linkage
2. Context stack is cleaned up in `finally` block
3. Parent context continues normally

## Performance

- **Minimal Overhead**: Context operations are O(1)
- **Memory Efficient**: Context stack is small (typically 1-3 events deep)
- **No Leaks**: Context automatically cleaned up by garbage collector

This implementation provides automatic event nesting while maintaining the existing decorator API and ensuring proper parent-child relationships.