# Complete Sync Event Emission Fix Plan

## Problem Summary

The `emit_events` decorator sync wrapper creates unawaited coroutines using:
```python
try:
    asyncio.create_task(bus.emit(event))
except RuntimeError:
    pass
```

This causes RuntimeWarning and events are never actually processed.

## Solution Approach

Replace all problematic calls with:
```python
try:
    loop = asyncio.get_running_loop()
    # Already in async context - schedule as background task
    loop.create_task(bus.emit(event))
except RuntimeError:
    # No event loop running - create one and await properly
    asyncio.run(bus.emit(event))
```

## Complete File Analysis: `abstractions/events/events.py`

### 1. Remove the Complex emit_sync Method (Lines ~563-602)

**Location**: After `async def emit(self, event: Event) -> Event:` method

**Current Code to Remove**:
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

**Action**: Delete this entire method block

### 2. Fix emit_events Decorator Sync Wrapper - Location 1

**Approximate Line**: ~1130 (in sync_wrapper function)
**Context**: Start event emission

**Current Problematic Code**:
```python
# Emit the start event using sync method
bus.emit_sync(start_event)
```

**Replace With**:
```python
# Emit the start event
try:
    loop = asyncio.get_running_loop()
    # Already in async context - schedule as background task
    loop.create_task(bus.emit(start_event))
except RuntimeError:
    # No event loop running - create one and await properly
    asyncio.run(bus.emit(start_event))
```

### 3. Fix emit_events Decorator Sync Wrapper - Location 2

**Approximate Line**: ~1185 (in sync_wrapper function, another start event)
**Context**: Alternative start event emission path

**Current Problematic Code**:
```python
# Emit the start event using sync method
bus.emit_sync(start_event)
```

**Replace With**:
```python
# Emit the start event
try:
    loop = asyncio.get_running_loop()
    # Already in async context - schedule as background task
    loop.create_task(bus.emit(start_event))
except RuntimeError:
    # No event loop running - create one and await properly
    asyncio.run(bus.emit(start_event))
```

### 4. Fix emit_events Decorator Sync Wrapper - Location 3

**Approximate Line**: ~1207 (in sync_wrapper function)
**Context**: Completion event emission

**Current Problematic Code**:
```python
# Emit completion event using sync method
bus.emit_sync(end_event)
```

**Replace With**:
```python
# Emit completion event
try:
    loop = asyncio.get_running_loop()
    # Already in async context - schedule as background task
    loop.create_task(bus.emit(end_event))
except RuntimeError:
    # No event loop running - create one and await properly
    asyncio.run(bus.emit(end_event))
```

### 5. Fix emit_events Decorator Sync Wrapper - Location 4

**Approximate Line**: ~1239 (in sync_wrapper function)
**Context**: Error event emission

**Current Problematic Code**:
```python
# Emit error event using sync method
bus.emit_sync(error_event)
```

**Replace With**:
```python
# Emit error event
try:
    loop = asyncio.get_running_loop()
    # Already in async context - schedule as background task
    loop.create_task(bus.emit(error_event))
except RuntimeError:
    # No event loop running - create one and await properly
    asyncio.run(bus.emit(error_event))
```

### 6. Check track_state_transition Decorator

**Approximate Line**: ~1260-1270 (in track_state_transition decorator)
**Context**: State transition event emission

**Current Code**:
```python
def sync_wrapper(self, *args, **kwargs):
    try:
        loop = asyncio.get_running_loop()
        # Already in async context, create task
        return asyncio.create_task(async_wrapper(self, *args, **kwargs))
    except RuntimeError:
        # No event loop running
        return asyncio.run(async_wrapper(self, *args, **kwargs))
```

**Action**: This looks correct - uses asyncio.run() properly. No change needed.

## Summary of Changes Required

1. **Delete**: Complex `emit_sync()` and `_emit_sync_internal()` methods (Lines ~563-602)
2. **Replace**: 4 locations in `emit_events` sync wrapper with proper asyncio.run() pattern
3. **Verify**: `track_state_transition` decorator is already correct

## Expected Outcome

After these changes:
- ✅ No RuntimeWarning about unawaited coroutines
- ✅ Events are properly processed in sync contexts
- ✅ Async handlers execute correctly from sync code
- ✅ Pure async contexts work unchanged
- ✅ Simple, maintainable solution

## Test Plan

1. Run `debug_events_bus_error_async.py` - should still work (no regression)
2. Run `debug_events_bus_error.py` - should now show event handler output
3. Verify no RuntimeWarning messages appear

## Implementation Order

1. Remove complex emit_sync methods first
2. Fix all 4 emit_events locations
3. Test sync example
4. Test async example
5. Verify both work correctly