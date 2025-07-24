# Event Bus Race Condition Fix Plan

## Problem Analysis

The `RuntimeWarning: coroutine 'EventBus.emit' was never awaited` errors occur because the `emit_events` decorator's sync wrapper creates asyncio tasks but never awaits them.

### Error Location
**File**: `abstractions/events/events.py`
**Lines**: 1132, 1169, 1201 (approximately)

### Root Cause
```python
# Current problematic code in sync wrapper:
try:
    asyncio.create_task(bus.emit(start_event))  # ❌ Never awaited
except RuntimeError:
    pass
```

The `asyncio.create_task()` creates a coroutine task but it's never awaited, causing the runtime warning.

## Fix Strategy

Replace the problematic `asyncio.create_task()` calls with proper background emission using threads.

### Fix Implementation

**Location 1** - Start event emission (around line 1130):
```python
# Replace:
try:
    asyncio.create_task(bus.emit(start_event))
except RuntimeError:
    # No event loop running, skip event
    pass

# With:
try:
    # Try to get running loop and create task
    loop = asyncio.get_running_loop()
    loop.create_task(bus.emit(start_event))
except RuntimeError:
    # No event loop running - emit synchronously in background
    import threading
    def emit_in_background():
        try:
            asyncio.run(bus.emit(start_event))
        except Exception:
            pass  # Ignore errors in background emission
    threading.Thread(target=emit_in_background, daemon=True).start()
```

**Location 2** - Completion event emission (around line 1167):
```python
# Replace:
try:
    asyncio.create_task(bus.emit(end_event))
except RuntimeError:
    # No event loop running, skip event
    pass

# With:
try:
    # Try to get running loop and create task
    loop = asyncio.get_running_loop()
    loop.create_task(bus.emit(end_event))
except RuntimeError:
    # No event loop running - emit synchronously in background
    import threading
    def emit_in_background():
        try:
            asyncio.run(bus.emit(end_event))
        except Exception:
            pass  # Ignore errors in background emission
    threading.Thread(target=emit_in_background, daemon=True).start()
```

**Location 3** - Error event emission (around line 1199):
```python
# Replace:
try:
    asyncio.create_task(bus.emit(error_event))
except RuntimeError:
    pass

# With:
try:
    # Try to get running loop and create task  
    loop = asyncio.get_running_loop()
    loop.create_task(bus.emit(error_event))
except RuntimeError:
    # No event loop running - emit synchronously in background
    import threading
    def emit_in_background():
        try:
            asyncio.run(bus.emit(error_event))
        except Exception:
            pass  # Ignore errors in background emission
    threading.Thread(target=emit_in_background, daemon=True).start()
```

## Expected Outcome

After the fix:
1. ✅ No more `RuntimeWarning: coroutine 'EventBus.emit' was never awaited`
2. ✅ Events properly emitted in both sync and async contexts
3. ✅ Background threads handle sync context emission safely
4. ✅ No regression in existing async functionality

## Test Plan

1. Run `examples/debug_events_bus_error.py` - should show no warnings
2. Verify entity promotion events are still emitted
3. Test async code paths still work correctly
4. Check event handlers still receive events

## Alternative Solutions Considered

1. **Queue-based**: Store events and process later (more complex)
2. **Sync-only**: Remove async emission entirely (breaks async support)  
3. **Thread pool**: Use ThreadPoolExecutor (heavier weight)

The threading solution is optimal because:
- Simple and reliable
- Maintains backward compatibility
- Handles both sync and async contexts
- Low overhead with daemon threads