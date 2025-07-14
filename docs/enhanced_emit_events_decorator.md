# Enhanced emit_events Decorator Implementation

## Overview

This specification details the modifications needed to the existing `emit_events` decorator in `abstractions/events/events.py` to enable automatic parent-child event linking using the context management system.

## Current Decorator Location

**File**: `abstractions/events/events.py`
**Lines**: 883-1021 (existing implementation)

## Required Modifications

### 1. Import Context Management Functions

Add these imports at the top of the file:

```python
# Add to existing imports around line 28
from abstractions.events.context import (
    get_current_parent_event,
    push_event_context,
    pop_event_context,
    get_context_statistics,
    validate_context_balance
)
```

### 2. Enhanced Decorator Signature

**Current signature** (line 883):
```python
def emit_events(
    creating_factory: Optional[Callable[..., Event]] = None,
    created_factory: Optional[Callable[..., Event]] = None,
    failed_factory: Optional[Callable[..., Event]] = None,
    include_timing: bool = True,
    include_args: bool = False
) -> Callable:
```

**Enhanced signature**:
```python
def emit_events(
    creating_factory: Optional[Callable[..., Event]] = None,
    created_factory: Optional[Callable[..., Event]] = None,
    failed_factory: Optional[Callable[..., Event]] = None,
    include_timing: bool = True,
    include_args: bool = False,
    auto_parent: bool = True,  # NEW: Enable/disable automatic parent linking
    debug_context: bool = False  # NEW: Enable context debugging
) -> Callable:
```

### 3. Enhanced Async Wrapper

**Current async wrapper** (lines 922-963):
```python
@functools.wraps(func)
async def async_wrapper(*args, **kwargs):
    bus = get_event_bus()
    start_time = time.time()
    
    # Create starting event
    if creating_factory:
        start_event = creating_factory(*args, **kwargs)
        if include_args:
            start_event.metadata['args'] = str(args)
            start_event.metadata['kwargs'] = str(kwargs)
        await bus.emit(start_event)
        lineage_id = start_event.lineage_id
    else:
        lineage_id = uuid4()
    
    try:
        # Execute async method
        result = await func(*args, **kwargs)
        
        # Create completion event
        if created_factory:
            end_event = created_factory(result, *args, **kwargs)
            end_event.lineage_id = lineage_id
            if include_timing:
                end_event.duration_ms = (time.time() - start_time) * 1000
            await bus.emit(end_event)
        
        return result
        
    except Exception as e:
        # Create failure event
        if failed_factory:
            error_event = failed_factory(e, *args, **kwargs)
            error_event.lineage_id = lineage_id
            if include_timing:
                error_event.duration_ms = (time.time() - start_time) * 1000
            await bus.emit(error_event)
        raise
```

**Enhanced async wrapper**:
```python
@functools.wraps(func)
async def async_wrapper(*args, **kwargs):
    bus = get_event_bus()
    start_time = time.time()
    
    # Get current parent from context
    parent_event = get_current_parent_event() if auto_parent else None
    context_depth = len(get_context_stack()) if debug_context else 0
    
    # Debug logging
    if debug_context:
        logger.debug(
            f"Executing {func.__name__} with context depth {context_depth}, "
            f"parent: {parent_event.id if parent_event else None}"
        )
    
    # Create starting event
    start_event = None
    if creating_factory:
        start_event = creating_factory(*args, **kwargs)
        
        # Apply automatic parent linking
        if parent_event and auto_parent:
            start_event.parent_id = parent_event.id
            start_event.root_id = parent_event.root_id or parent_event.id
            start_event.lineage_id = parent_event.lineage_id
            
            # Add context metadata
            if debug_context:
                start_event.metadata['context_depth'] = context_depth
                start_event.metadata['parent_event_type'] = parent_event.type
        else:
            # No parent - this is a root event
            start_event.root_id = start_event.id
        
        # Add arguments metadata
        if include_args:
            start_event.metadata['args'] = str(args)
            start_event.metadata['kwargs'] = str(kwargs)
        
        # Push to context stack BEFORE emitting
        push_event_context(start_event)
        
        # Emit the start event
        await bus.emit(start_event)
        lineage_id = start_event.lineage_id
    else:
        lineage_id = uuid4()
    
    try:
        # Execute async method (nested calls will see start_event as parent)
        result = await func(*args, **kwargs)
        
        # Create completion event
        if created_factory:
            end_event = created_factory(result, *args, **kwargs)
            end_event.lineage_id = lineage_id
            
            # Apply automatic parent linking to completion event
            if parent_event and auto_parent:
                end_event.parent_id = parent_event.id
                end_event.root_id = parent_event.root_id or parent_event.id
                
                # Add context metadata
                if debug_context:
                    end_event.metadata['context_depth'] = context_depth
                    end_event.metadata['parent_event_type'] = parent_event.type
            else:
                # No parent - this is a root event
                end_event.root_id = end_event.id
            
            # Add timing information
            if include_timing:
                end_event.duration_ms = (time.time() - start_time) * 1000
            
            await bus.emit(end_event)
        
        return result
        
    except Exception as e:
        # Create failure event
        if failed_factory:
            error_event = failed_factory(e, *args, **kwargs)
            error_event.lineage_id = lineage_id
            
            # Apply automatic parent linking to error event
            if parent_event and auto_parent:
                error_event.parent_id = parent_event.id
                error_event.root_id = parent_event.root_id or parent_event.id
                
                # Add context metadata
                if debug_context:
                    error_event.metadata['context_depth'] = context_depth
                    error_event.metadata['parent_event_type'] = parent_event.type
                    error_event.metadata['exception_type'] = type(e).__name__
            else:
                # No parent - this is a root event
                error_event.root_id = error_event.id
            
            # Add timing information
            if include_timing:
                error_event.duration_ms = (time.time() - start_time) * 1000
            
            await bus.emit(error_event)
        raise
    
    finally:
        # Pop from context stack (critical for cleanup)
        if start_event:
            popped_event = pop_event_context()
            
            # Validation in debug mode
            if debug_context and popped_event:
                if popped_event.id != start_event.id:
                    logger.warning(
                        f"Context stack corruption in {func.__name__}: "
                        f"expected {start_event.id}, got {popped_event.id}"
                    )
                    
                # Validate context balance
                stats = get_context_statistics()
                if not stats['balance_check']:
                    logger.warning(
                        f"Context imbalance detected after {func.__name__}: {stats}"
                    )
```

### 4. Enhanced Sync Wrapper

**Current sync wrapper** (lines 965-1019):
```python
@functools.wraps(func)
def sync_wrapper(*args, **kwargs):
    bus = get_event_bus()
    start_time = time.time()
    
    # Create starting event
    if creating_factory:
        start_event = creating_factory(*args, **kwargs)
        if include_args:
            start_event.metadata['args'] = str(args)
            start_event.metadata['kwargs'] = str(kwargs)
        # Use asyncio.create_task for async event emission in sync context
        try:
            asyncio.create_task(bus.emit(start_event))
        except RuntimeError:
            # No event loop running, skip event
            pass
        lineage_id = start_event.lineage_id
    else:
        lineage_id = uuid4()
    
    try:
        # Execute sync method
        result = func(*args, **kwargs)
        
        # Create completion event
        if created_factory:
            end_event = created_factory(result, *args, **kwargs)
            end_event.lineage_id = lineage_id
            if include_timing:
                end_event.duration_ms = (time.time() - start_time) * 1000
            # Use asyncio.create_task for async event emission in sync context
            try:
                asyncio.create_task(bus.emit(end_event))
            except RuntimeError:
                # No event loop running, skip event
                pass
        
        return result
        
    except Exception as e:
        # Create failure event
        if failed_factory:
            error_event = failed_factory(e, *args, **kwargs)
            error_event.lineage_id = lineage_id
            if include_timing:
                error_event.duration_ms = (time.time() - start_time) * 1000
            try:
                asyncio.create_task(bus.emit(error_event))
            except RuntimeError:
                pass
        raise
```

**Enhanced sync wrapper**:
```python
@functools.wraps(func)
def sync_wrapper(*args, **kwargs):
    bus = get_event_bus()
    start_time = time.time()
    
    # Get current parent from context
    parent_event = get_current_parent_event() if auto_parent else None
    context_depth = len(get_context_stack()) if debug_context else 0
    
    # Debug logging
    if debug_context:
        logger.debug(
            f"Executing {func.__name__} (sync) with context depth {context_depth}, "
            f"parent: {parent_event.id if parent_event else None}"
        )
    
    # Create starting event
    start_event = None
    if creating_factory:
        start_event = creating_factory(*args, **kwargs)
        
        # Apply automatic parent linking
        if parent_event and auto_parent:
            start_event.parent_id = parent_event.id
            start_event.root_id = parent_event.root_id or parent_event.id
            start_event.lineage_id = parent_event.lineage_id
            
            # Add context metadata
            if debug_context:
                start_event.metadata['context_depth'] = context_depth
                start_event.metadata['parent_event_type'] = parent_event.type
                start_event.metadata['sync_execution'] = True
        else:
            # No parent - this is a root event
            start_event.root_id = start_event.id
        
        # Add arguments metadata
        if include_args:
            start_event.metadata['args'] = str(args)
            start_event.metadata['kwargs'] = str(kwargs)
        
        # Push to context stack BEFORE emitting
        push_event_context(start_event)
        
        # Emit the start event
        try:
            asyncio.create_task(bus.emit(start_event))
        except RuntimeError:
            # No event loop running, skip event
            logger.warning(f"No event loop for emitting start event in {func.__name__}")
        
        lineage_id = start_event.lineage_id
    else:
        lineage_id = uuid4()
    
    try:
        # Execute sync method (nested calls will see start_event as parent)
        result = func(*args, **kwargs)
        
        # Create completion event
        if created_factory:
            end_event = created_factory(result, *args, **kwargs)
            end_event.lineage_id = lineage_id
            
            # Apply automatic parent linking to completion event
            if parent_event and auto_parent:
                end_event.parent_id = parent_event.id
                end_event.root_id = parent_event.root_id or parent_event.id
                
                # Add context metadata
                if debug_context:
                    end_event.metadata['context_depth'] = context_depth
                    end_event.metadata['parent_event_type'] = parent_event.type
                    end_event.metadata['sync_execution'] = True
            else:
                # No parent - this is a root event
                end_event.root_id = end_event.id
            
            # Add timing information
            if include_timing:
                end_event.duration_ms = (time.time() - start_time) * 1000
            
            # Emit completion event
            try:
                asyncio.create_task(bus.emit(end_event))
            except RuntimeError:
                logger.warning(f"No event loop for emitting completion event in {func.__name__}")
        
        return result
        
    except Exception as e:
        # Create failure event
        if failed_factory:
            error_event = failed_factory(e, *args, **kwargs)
            error_event.lineage_id = lineage_id
            
            # Apply automatic parent linking to error event
            if parent_event and auto_parent:
                error_event.parent_id = parent_event.id
                error_event.root_id = parent_event.root_id or parent_event.id
                
                # Add context metadata
                if debug_context:
                    error_event.metadata['context_depth'] = context_depth
                    error_event.metadata['parent_event_type'] = parent_event.type
                    error_event.metadata['exception_type'] = type(e).__name__
                    error_event.metadata['sync_execution'] = True
            else:
                # No parent - this is a root event
                error_event.root_id = error_event.id
            
            # Add timing information
            if include_timing:
                error_event.duration_ms = (time.time() - start_time) * 1000
            
            # Emit error event
            try:
                asyncio.create_task(bus.emit(error_event))
            except RuntimeError:
                logger.warning(f"No event loop for emitting error event in {func.__name__}")
        raise
    
    finally:
        # Pop from context stack (critical for cleanup)
        if start_event:
            popped_event = pop_event_context()
            
            # Validation in debug mode
            if debug_context and popped_event:
                if popped_event.id != start_event.id:
                    logger.warning(
                        f"Context stack corruption in {func.__name__}: "
                        f"expected {start_event.id}, got {popped_event.id}"
                    )
                    
                # Validate context balance
                stats = get_context_statistics()
                if not stats['balance_check']:
                    logger.warning(
                        f"Context imbalance detected after {func.__name__}: {stats}"
                    )
```

### 5. Enhanced Docstring

**Enhanced docstring** (replace existing docstring):
```python
"""
Decorator that emits events around method execution with automatic parent-child linking.

This decorator creates a complete event lifecycle around method execution:
1. Creates and emits a 'creating' event before method execution
2. Automatically links events to parent context if available
3. Manages context stack for nested event hierarchies
4. Creates completion or failure events after execution
5. Provides timing and debugging information

Args:
    creating_factory: Function to create the 'started' event
    created_factory: Function to create the 'completed' event  
    failed_factory: Function to create the 'failed' event
    include_timing: Whether to include execution time in events
    include_args: Whether to include method arguments in event metadata
    auto_parent: Whether to automatically link to parent events (default: True)
    debug_context: Whether to enable context debugging and validation (default: False)

Automatic Parent Linking:
    When auto_parent=True (default), events are automatically linked to any parent
    event in the current context stack. This creates proper hierarchical relationships:
    - parent_id: Set to current parent event's ID
    - root_id: Set to root event's ID (or parent's root_id)
    - lineage_id: Inherited from parent event
    
Context Management:
    The decorator automatically manages the context stack:
    - Pushes start event to context before method execution
    - Pops from context after method completion (in finally block)
    - Nested decorated methods automatically become children
    
Error Handling:
    - Context stack is always properly cleaned up in finally block
    - Failed events are created and linked to parent context
    - Context validation available in debug mode
    
Example:
    @emit_events(
        creating_factory=lambda self: ProcessingEvent(
            subject_type=type(self),
            subject_id=self.id,
            process_name="analyze"
        ),
        created_factory=lambda result, self: ProcessedEvent(
            subject_type=type(self),
            subject_id=self.id,
            process_name="analyze",
            output_ids=[result.id]
        ),
        auto_parent=True,  # Enable automatic nesting
        debug_context=False  # Disable debug logging
    )
    async def analyze(self, data):
        # This method's events will be children of any parent context
        # Any decorated methods called from here will be grandchildren
        return await self.process_data(data)
        
Context Isolation:
    Uses contextvars for proper async and thread isolation:
    - Each async task gets its own context stack
    - Each thread gets its own context stack
    - Context is automatically cleaned up when tasks complete
    
Performance:
    - Minimal overhead: O(1) context operations
    - Small memory footprint (typically 1-3 events in stack)
    - Optional debug mode for development/troubleshooting
"""
```

## Key Changes Summary

1. **New Parameters**: `auto_parent` and `debug_context` for controlling behavior
2. **Context Integration**: Automatic parent detection and linking
3. **Stack Management**: Push/pop operations with proper cleanup
4. **Enhanced Metadata**: Context depth, parent info, execution type
5. **Debug Support**: Validation and logging in debug mode
6. **Error Handling**: Robust cleanup in finally blocks
7. **Performance**: Minimal overhead, optional debug features

## Backward Compatibility

- All existing decorators continue to work unchanged
- New parameters have sensible defaults
- No breaking changes to existing event structure
- Opt-out available via `auto_parent=False`

## Testing Impact

The enhanced decorator maintains all existing functionality while adding automatic nesting. Existing tests should pass unchanged, with additional tests needed for the new nesting behavior.