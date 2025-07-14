# emit_events Decorator Enhancement Specification

## Overview
Enhance the existing `emit_events` decorator to automatically handle parent-child event relationships using the context management system, while maintaining backward compatibility.

## Current Implementation Location
**File**: `abstractions/events/events.py`
**Lines**: 892-1030

## Enhancement Strategy
- **Keep existing signature unchanged** for backward compatibility
- **Enable automatic nesting by default** - no opt-in required
- **Use context management functions** already imported (lines 31-37)
- **Enhance both async and sync wrappers** identically

## Required Changes

### 1. Async Wrapper Enhancement (lines 932-972)

**Current Pattern**:
```python
# Create starting event
if creating_factory:
    start_event = creating_factory(*args, **kwargs)
    if include_args:
        start_event.metadata['args'] = str(args)
        start_event.metadata['kwargs'] = str(kwargs)
    await bus.emit(start_event)
    lineage_id = start_event.lineage_id
```

**Enhanced Pattern**:
```python
# Get current parent from context stack
parent_event = get_current_parent_event()

# Create starting event
start_event = None
if creating_factory:
    start_event = creating_factory(*args, **kwargs)
    
    # Apply automatic parent linking
    if parent_event:
        start_event.parent_id = parent_event.id
        start_event.root_id = parent_event.root_id or parent_event.id
        start_event.lineage_id = parent_event.lineage_id
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
```

### 2. Completion Event Enhancement

**Current Pattern**:
```python
# Create completion event
if created_factory:
    end_event = created_factory(result, *args, **kwargs)
    end_event.lineage_id = lineage_id
    if include_timing:
        end_event.duration_ms = (time.time() - start_time) * 1000
    await bus.emit(end_event)
```

**Enhanced Pattern**:
```python
# Create completion event
if created_factory:
    end_event = created_factory(result, *args, **kwargs)
    end_event.lineage_id = lineage_id
    
    # Apply automatic parent linking to completion event
    if parent_event:
        end_event.parent_id = parent_event.id
        end_event.root_id = parent_event.root_id or parent_event.id
    else:
        # No parent - this is a root event
        end_event.root_id = end_event.id
    
    # Add timing information
    if include_timing:
        end_event.duration_ms = (time.time() - start_time) * 1000
    
    await bus.emit(end_event)
```

### 3. Error Event Enhancement

**Current Pattern**:
```python
# Create failure event
if failed_factory:
    error_event = failed_factory(e, *args, **kwargs)
    error_event.lineage_id = lineage_id
    if include_timing:
        error_event.duration_ms = (time.time() - start_time) * 1000
    await bus.emit(error_event)
```

**Enhanced Pattern**:
```python
# Create failure event
if failed_factory:
    error_event = failed_factory(e, *args, **kwargs)
    error_event.lineage_id = lineage_id
    
    # Apply automatic parent linking to error event
    if parent_event:
        error_event.parent_id = parent_event.id
        error_event.root_id = parent_event.root_id or parent_event.id
    else:
        # No parent - this is a root event
        error_event.root_id = error_event.id
    
    # Add timing information
    if include_timing:
        error_event.duration_ms = (time.time() - start_time) * 1000
    
    await bus.emit(error_event)
```

### 4. Context Cleanup (Critical)

**Add finally block** to both async and sync wrappers:
```python
finally:
    # Pop from context stack (critical for cleanup)
    if start_event:
        pop_event_context()
```

### 5. Sync Wrapper Enhancement (lines 975-1028)

Apply the same patterns to the sync wrapper:
- Get parent event from context
- Apply parent linking to all events
- Push start event to context
- Pop from context in finally block
- Handle asyncio.create_task calls safely

## Key Benefits

1. **Backward Compatibility**: No signature changes, existing code works unchanged
2. **Automatic Nesting**: Parent-child relationships work automatically
3. **Proper Cleanup**: Context stack managed safely with finally blocks
4. **Thread Safety**: Context isolation works correctly
5. **Error Handling**: Failed events still linked to parent context

## Testing Requirements

1. **Basic functionality**: Existing tests should pass unchanged
2. **Automatic nesting**: New tests for parent-child relationships
3. **Context cleanup**: Verify stack balance after errors
4. **Thread isolation**: Async tasks get separate context stacks

## Implementation Steps

1. **Enhance async wrapper** with context management
2. **Enhance sync wrapper** with context management  
3. **Add context cleanup** in finally blocks
4. **Test basic functionality** to ensure no regression
5. **Test automatic nesting** with new test scenarios

## Backward Compatibility Guarantee

- **No signature changes** - existing calls work unchanged
- **Opt-out not needed** - automatic nesting is safe by default
- **Existing behavior preserved** - events without parents work as before
- **Performance impact minimal** - O(1) context operations

This enhancement provides automatic event nesting while maintaining complete backward compatibility and adding robust error handling.