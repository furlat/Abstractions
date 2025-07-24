# Event Bus Sync/Async Fix Implementation Plan

## Problem Analysis

### Root Cause
The `emit_events` decorator sync wrapper creates unawaited coroutines:
- Lines 1132, 1169, 1201: `asyncio.create_task(bus.emit(start_event))`
- `bus.emit()` returns a coroutine that gets wrapped in a task but never awaited
- This creates RuntimeWarning about unawaited coroutines
- The tasks are orphaned and events never actually get processed

### Debug Example Issue
- Event handlers are async: `@on(EntityRegistrationEvent) async def handle_entity_registration`
- But events are never processed because tasks are never awaited
- Result: No event reactions happen at all

## Comprehensive Solution

### 1. Add `emit_sync()` Method to EventBus

```python
def emit_sync(self, event: Event) -> Event:
    """
    Emit an event from sync context with proper async handler execution.
    
    This method handles three scenarios:
    1. Already in async context - use normal async emission
    2. Sync context with running loop - schedule as background task  
    3. Pure sync context - create new event loop to run async emission
    """
    try:
        # Try to get running event loop
        loop = asyncio.get_running_loop()
        
        # We're in an async context, but called from sync code
        # Schedule the emission as a background task
        task = loop.create_task(self.emit(event))
        
        # Store the task to prevent it from being garbage collected
        # and to allow proper cleanup
        if not hasattr(self, '_background_tasks'):
            self._background_tasks = set()
        
        self._background_tasks.add(task)
        
        # Add callback to remove from set when done
        task.add_done_callback(self._background_tasks.discard)
        
        return event
        
    except RuntimeError:
        # No event loop running - we're in pure sync context
        # Create a new event loop to run the async emission
        try:
            # Use asyncio.run to properly handle async emission
            asyncio.run(self._emit_sync_internal(event))
            return event
        except Exception as e:
            # If async emission fails, log and continue
            logger.warning(f"Failed to emit event in sync context: {e}")
            return event

async def _emit_sync_internal(self, event: Event) -> None:
    """Internal helper for sync emission in new event loop."""
    await self.emit(event)
```

### 2. Fix emit_events Decorator Sync Wrapper

Replace all instances of:
```python
try:
    asyncio.create_task(bus.emit(start_event))
except RuntimeError:
    # No event loop running, skip event
    pass
```

With:
```python
bus.emit_sync(start_event)
```

This ensures:
- Events are actually processed
- Async handlers get executed properly
- No unawaited coroutine warnings
- Proper error handling

### 3. Implementation Steps

1. **Add emit_sync method and background task management to EventBus**
2. **Replace sync wrapper calls in emit_events decorator (3 locations)**
3. **Test with debug example to verify async handlers execute**
4. **Verify no regression in pure async usage**

### 4. Benefits

- ✅ Eliminates RuntimeWarning about unawaited coroutines
- ✅ Ensures async event handlers execute from sync contexts
- ✅ Maintains backward compatibility
- ✅ Proper resource cleanup with background task management
- ✅ Graceful degradation if async processing fails

### 5. Test Cases

1. **Pure async context**: Normal async emission (no changes)
2. **Sync context with loop**: Background task emission  
3. **Pure sync context**: New loop creation for emission
4. **Mixed sync/async handlers**: All handlers execute properly
5. **Error scenarios**: Graceful handling without breaking sync code

## Files to Modify

- `abstractions/events/events.py`: Add emit_sync method and fix emit_events decorator
- `examples/debug_events_bus_error.py`: Test the fix (should see event handler output)