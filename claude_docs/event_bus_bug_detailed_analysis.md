# Event Bus RuntimeWarning Bug - Detailed Technical Analysis

## 🐛 The Error Messages

Your debug script produces these specific warnings:

```
C:\Users\Tommaso\Documents\Dev\Abstractions\abstractions\events\events.py:1135: RuntimeWarning: coroutine 'EventBus.emit' was never awaited
  pass
RuntimeWarning: Enable tracemalloc to get the object allocation traceback
C:\Users\Tommaso\Documents\Dev\Abstractions\abstractions\events\events.py:1172: RuntimeWarning: coroutine 'EventBus.emit' was never awaited
  pass
RuntimeWarning: Enable tracemalloc to get the object allocation traceback
```

## 🔍 Step-by-Step Bug Analysis

### 1. The Trigger Sequence

**Your Code:**
```python
# examples/debug_events_bus_error.py
for customer in customers:
    customer.promote_to_root()  # ← This triggers the bug
```

**What Happens:**
1. `customer.promote_to_root()` is called in **synchronous context** (no async/await)
2. `promote_to_root()` is decorated with `@emit_events` 
3. The `@emit_events` decorator detects it's a sync function and uses the **sync wrapper**
4. The sync wrapper tries to emit events but creates **unawaited coroutines**

### 2. The Problematic Code Path

**File:** `abstractions/events/events.py`  
**Method:** `emit_events` decorator's sync wrapper  
**Lines:** ~1092-1210

Here's the execution flow:

```python
@emit_events(creating_factory=..., created_factory=...)
def promote_to_root(self):  # ← Sync method
    # decorated with emit_events
```

**Decorator Logic:**
```python
def decorator(func: Callable) -> Callable:
    is_async = inspect.iscoroutinefunction(func)  # ← False for promote_to_root
    
    if is_async:
        # async wrapper (not used)
    else:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):  # ← This path is taken
            # ... sync wrapper code ...
```

### 3. The Exact Bug Location

**Problem Code 1** (Line ~1132):
```python
def sync_wrapper(*args, **kwargs):
    # ...
    if creating_factory:
        start_event = creating_factory(*args, **kwargs)
        # ...
        # Emit the start event
        try:
            asyncio.create_task(bus.emit(start_event))  # ❌ BUG HERE
        except RuntimeError:
            # No event loop running, skip event
            pass  # ← Line 1135 from error message
```

**Problem Code 2** (Line ~1169):
```python
# Create completion event
if created_factory:
    end_event = created_factory(result, *args, **kwargs)
    # ...
    # Emit completion event
    try:
        asyncio.create_task(bus.emit(end_event))  # ❌ BUG HERE  
    except RuntimeError:
        # No event loop running, skip event
        pass  # ← Line 1172 from error message
```

### 4. Why The RuntimeWarning Occurs

#### The Core Issue: Fire-and-Forget Coroutines

**What `asyncio.create_task()` Does:**
```python
task = asyncio.create_task(bus.emit(start_event))
# Creates a Task object that runs bus.emit() concurrently
# But the task is never stored or awaited!
```

**The Problem:**
- `bus.emit()` returns a **coroutine** (async function)
- `asyncio.create_task()` wraps it in a **Task** for concurrent execution
- The task starts running immediately in the background
- **But nothing ever waits for it to complete**
- Python's asyncio runtime detects this and issues the `RuntimeWarning`

#### Why This Is Dangerous

1. **Resource Leaks**: Unawaited tasks consume memory
2. **Unpredictable Timing**: Events may or may not be processed
3. **Silent Failures**: If the task fails, you'll never know
4. **Race Conditions**: The main function might finish before events are emitted

### 5. The Execution Context Problem

**Your Script Context:**
```python
if __name__ == "__main__":
    # This runs in synchronous context
    for customer in customers:
        customer.promote_to_root()  # ← Sync call
```

**The Mismatch:**
- Your code runs **synchronously** (no event loop initially)
- `promote_to_root()` needs to emit **async events**
- The sync wrapper tries to bridge this gap but does it wrong

**What Should Happen:**
- Either run the events in the existing event loop (if any)
- Or create a separate event loop to handle the emission properly

### 6. Event Loop State Analysis

**When `promote_to_root()` is called:**

```python
# In sync_wrapper:
try:
    asyncio.create_task(bus.emit(start_event))  # Tries to use current loop
except RuntimeError:
    pass  # Falls back to doing nothing
```

**The RuntimeError Path:**
- `asyncio.create_task()` requires a **running event loop**
- If no loop exists, it raises `RuntimeError`
- The code catches this and does `pass` (ignores the event)

**But There's a Bug in the Bug:**
Sometimes there **is** a running loop (from the event bus auto-start), but the task is still created without being awaited, causing the warning.

### 7. Event Bus Initialization Race

**File:** `abstractions/events/events.py` (Lines 50-66)

```python
def get_event_bus() -> 'EventBus':
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    
    # Auto-start if not running and we're in an async context
    try:
        loop = asyncio.get_running_loop()  # ← May or may not exist
        if not _event_bus._processor_task:
            loop.create_task(_event_bus.start())  # ← Creates another unawaited task!
    except RuntimeError:
        pass
    
    return _event_bus
```

**The Race Condition:**
1. `get_event_bus()` is called
2. It detects a running loop (maybe from a background thread)
3. It creates a task to start the event bus
4. Meanwhile, your sync code calls `promote_to_root()`
5. The decorator tries to emit events while the bus is starting
6. Multiple unawaited tasks are created

### 8. Why The Warnings Appear Twice

Looking at your error output:
```
abstractions\events\events.py:1135: RuntimeWarning: coroutine 'EventBus.emit' was never awaited
abstractions\events\events.py:1172: RuntimeWarning: coroutine 'EventBus.emit' was never awaited
```

**Two different line numbers = Two different events:**
- **Line 1135**: Start event emission (from `creating_factory`)
- **Line 1172**: Completion event emission (from `created_factory`)

Each `promote_to_root()` call emits **both** a start and completion event, so you get warnings for both.

### 9. The Fundamental Design Conflict

**The Real Issue:**
The `emit_events` decorator tries to support both sync and async functions by:
- Using `await` for async functions (correct)
- Using `asyncio.create_task()` for sync functions (incorrect)

**Why This Doesn't Work:**
- Sync functions **cannot await** anything
- But they still need to emit async events
- `create_task()` creates concurrent tasks but doesn't wait for them
- This creates fire-and-forget behavior with warnings

## 🔧 Summary

The bug is a **concurrency design flaw** where:

1. **Sync decorated methods** need to emit async events
2. The decorator uses **fire-and-forget tasks** (`create_task` without await)
3. Python's runtime **warns about unawaited coroutines**
4. Events may or may not be processed due to **race conditions**

**The fix requires:**
- Proper background execution for sync contexts
- Either threading or proper event loop management  
- Ensuring events are actually processed, not just created