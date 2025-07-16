# Event Nesting Detection Options

## Current Problem
The `@emit_events` decorator doesn't automatically detect when one decorated method calls another, so events don't form proper parent-child relationships.

## Option 1: Thread-Local Context Stack (Recommended)

Use thread-local storage to track the current event context:

```python
import threading

# Thread-local storage for event context
_event_context = threading.local()

def get_current_event_context():
    """Get the current event context from thread-local storage."""
    return getattr(_event_context, 'stack', [])

def push_event_context(event: Event):
    """Push an event onto the context stack."""
    if not hasattr(_event_context, 'stack'):
        _event_context.stack = []
    _event_context.stack.append(event)

def pop_event_context():
    """Pop an event from the context stack."""
    if hasattr(_event_context, 'stack') and _event_context.stack:
        return _event_context.stack.pop()
    return None

# Updated emit_events decorator
def emit_events(creating_factory=None, created_factory=None):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get current parent context
            current_context = get_current_event_context()
            parent_event = current_context[-1] if current_context else None
            
            # Create starting event
            if creating_factory:
                start_event = creating_factory(*args, **kwargs)
                
                # Auto-link to parent
                if parent_event:
                    start_event.parent_id = parent_event.id
                    start_event.root_id = parent_event.root_id or parent_event.id
                else:
                    start_event.root_id = start_event.id
                
                # Push to context stack
                push_event_context(start_event)
                bus.emit(start_event)
            
            try:
                result = func(*args, **kwargs)
                
                # Create completion event
                if created_factory:
                    end_event = created_factory(result, *args, **kwargs)
                    if parent_event:
                        end_event.parent_id = parent_event.id
                        end_event.root_id = parent_event.root_id or parent_event.id
                    bus.emit(end_event)
                
                return result
            finally:
                # Pop from context stack
                if creating_factory:
                    pop_event_context()
        
        return wrapper
    return decorator
```

**Pros:**
- Automatic parent-child detection
- Works with any call depth
- Thread-safe
- Minimal performance overhead

**Cons:**
- Requires thread-local storage
- Not async-friendly (needs asyncio context vars)

## Option 2: Call Stack Inspection

Use `inspect.stack()` to detect calling decorated methods:

```python
import inspect

def emit_events(creating_factory=None, created_factory=None):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Inspect call stack for parent events
            parent_event = None
            stack = inspect.stack()
            
            for frame_info in stack[1:]:  # Skip current frame
                frame = frame_info.frame
                # Check if frame has event context
                if hasattr(frame, 'f_locals') and '_current_event' in frame.f_locals:
                    parent_event = frame.f_locals['_current_event']
                    break
            
            # Create starting event
            if creating_factory:
                start_event = creating_factory(*args, **kwargs)
                
                # Auto-link to parent
                if parent_event:
                    start_event.parent_id = parent_event.id
                    start_event.root_id = parent_event.root_id or parent_event.id
                
                # Store in frame locals for child detection
                frame = inspect.currentframe()
                frame.f_locals['_current_event'] = start_event
                
                bus.emit(start_event)
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator
```

**Pros:**
- No thread-local storage needed
- Can detect any calling context

**Cons:**
- Performance overhead (stack inspection)
- Complex and fragile
- Frame manipulation is hacky

## Option 3: Explicit Context Manager

Require explicit context for nested operations:

```python
@asynccontextmanager
async def event_context(event: Event):
    """Context manager for nested event operations."""
    push_event_context(event)
    try:
        yield event
    finally:
        pop_event_context()

# Usage
@emit_events(...)
async def method_A(self):
    start_event = create_start_event()
    
    async with event_context(start_event):
        # Any decorated methods called here will be children
        await self.method_B()
```

**Pros:**
- Explicit and clear
- Full control over nesting
- Async-friendly

**Cons:**
- Manual context management
- More verbose
- Easy to forget

## Option 4: Event ID Propagation

Pass event IDs through method parameters:

```python
def emit_events(creating_factory=None, created_factory=None):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Check for _parent_event_id in kwargs
            parent_event_id = kwargs.pop('_parent_event_id', None)
            
            # Create starting event
            if creating_factory:
                start_event = creating_factory(*args, **kwargs)
                
                if parent_event_id:
                    start_event.parent_id = parent_event_id
                
                bus.emit(start_event)
            
            # Modify method calls to include parent event ID
            # (This requires code modification or monkey patching)
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator
```

**Pros:**
- Simple and explicit
- No magical behavior

**Cons:**
- Requires modifying all method calls
- Pollutes method signatures
- Manual propagation

## Recommendation: Thread-Local Context Stack

For automatic nesting detection, **Option 1 (Thread-Local Context Stack)** is the most practical:

1. **Automatic**: No manual parent-child specification needed
2. **Transparent**: Existing code works without changes
3. **Efficient**: Minimal performance overhead
4. **Thread-safe**: Works with concurrent operations

For async support, use `contextvars` instead of `threading.local()`:

```python
import contextvars

_event_context: contextvars.ContextVar[List[Event]] = contextvars.ContextVar('event_context', default=[])

def get_current_event_context():
    return _event_context.get()

def push_event_context(event: Event):
    current = _event_context.get()
    _event_context.set(current + [event])

def pop_event_context():
    current = _event_context.get()
    if current:
        _event_context.set(current[:-1])
        return current[-1]
    return None
```

This approach enables automatic parent-child relationships while maintaining the existing decorator API.