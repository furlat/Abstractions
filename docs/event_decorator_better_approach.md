# Better Event Decorator Approach: Leverage Existing Resolution Logic

## The Problem with Duplication

You're absolutely right! The current approach would require duplicating all the sophisticated entity resolution logic that already exists in:

- `_detect_execution_strategy()` - Strategy detection
- `_prepare_transactional_inputs()` - Entity isolation and copying
- `_create_input_entity_with_borrowing()` - Entity borrowing patterns
- `EntityReferenceResolver` - Address parsing "@entity_id.field"
- `InputPatternClassifier` - Pattern classification

This violates DRY principle and creates maintenance overhead.

## Current Event Decorator Position

```python
@emit_events(...)  # ← Events emitted HERE (before processing)
async def aexecute(cls, func_name: str, **kwargs):
    return await cls._execute_async(func_name, **kwargs)  # ← Processing happens HERE
```

The decorator runs BEFORE the execution paths are chosen, but entity resolution happens INSIDE the execution paths.

## Better Approach: Leverage Existing Resolution

Instead of duplicating logic, we can:

### Option 1: Call Existing Resolution from Decorator

```python
@emit_events(
    creating_factory=lambda cls, func_name, **kwargs: ProcessingEvent(
        subject_type=cls._get_resolved_input_entity_type(func_name, kwargs),
        subject_id=cls._get_resolved_input_entity_id(func_name, kwargs),
        process_name="function_execution",
        metadata={"function_name": func_name, "input_count": len(kwargs)}
    ),
    created_factory=lambda result, cls, func_name, **kwargs: ProcessedEvent(
        subject_type=type(result[0]) if isinstance(result, list) else type(result),
        subject_id=result[0].ecs_id if isinstance(result, list) else result.ecs_id,
        process_name="function_execution",
        result_summary={"function_name": func_name, "output_count": len(result) if isinstance(result, list) else 1}
    )
)
async def aexecute(cls, func_name: str, **kwargs):
    return await cls._execute_async(func_name, **kwargs)
```

### Option 2: Move Event Emission Deeper

Instead of decorating `aexecute()`, emit events from inside each execution path AFTER entities are resolved:

```python
# Inside _execute_transactional()
async def _execute_transactional(cls, metadata, kwargs, classification):
    # ... existing resolution logic ...
    
    # Emit processing event with resolved entities
    await emit_processing_event(
        subject_type=type(input_entity),
        subject_id=input_entity.ecs_id,
        process_name="function_execution"
    )
    
    # ... execute function ...
    
    # Emit completion event
    await emit_processed_event(
        subject_type=type(result),
        subject_id=result.ecs_id,
        process_name="function_execution"
    )
```

## Recommended Implementation: Option 1

Create lightweight resolution methods that reuse existing logic:

```python
@classmethod
def _get_resolved_input_entity_type(cls, func_name: str, kwargs: Dict[str, Any]) -> Optional[Type]:
    """Get primary input entity type by leveraging existing resolution logic."""
    try:
        # Get function metadata
        metadata = cls.get_metadata(func_name)
        if not metadata:
            return None
            
        # Use existing strategy detection
        strategy = cls._detect_execution_strategy(kwargs, metadata)
        
        # Use existing pattern classification
        pattern_type, classification = InputPatternClassifier.classify_kwargs(kwargs)
        
        # Extract primary entity based on strategy
        if strategy in ["single_entity_direct", "single_entity_with_config"]:
            # Find first entity parameter
            for value in kwargs.values():
                if isinstance(value, Entity):
                    return type(value)
        elif strategy == "multi_entity_composite":
            # Find first entity parameter (primary one)
            for value in kwargs.values():
                if isinstance(value, Entity):
                    return type(value)
        elif strategy == "pure_borrowing":
            # Use existing EntityReferenceResolver
            resolver = EntityReferenceResolver(kwargs)
            primary_entity = resolver.get_primary_entity()
            if primary_entity:
                return type(primary_entity)
        
        return None
    except Exception:
        # Fallback to simple detection
        for value in kwargs.values():
            if isinstance(value, Entity):
                return type(value)
        return None

@classmethod
def _get_resolved_input_entity_id(cls, func_name: str, kwargs: Dict[str, Any]) -> Optional[UUID]:
    """Get primary input entity ID by leveraging existing resolution logic."""
    try:
        # Similar logic as above but return ecs_id
        # ... (implementation follows same pattern)
    except Exception:
        # Fallback to simple detection
        for value in kwargs.values():
            if isinstance(value, Entity):
                return value.ecs_id
        return None
```

## Benefits of This Approach

1. **No Logic Duplication**: Reuses existing resolution infrastructure
2. **Consistent Behavior**: Same resolution logic used for events and execution
3. **Maintainable**: Changes to resolution logic automatically affect events
4. **Robust**: Fallback to simple detection if resolution fails
5. **Performance**: Lightweight calls to existing methods

## Error Handling

If resolution fails, fallback to simple entity detection:
```python
# Fallback: Simple entity detection
for value in kwargs.values():
    if isinstance(value, Entity):
        return type(value), value.ecs_id
return None, None
```

This approach leverages the existing "wheel" instead of reinventing it, ensuring consistency and maintainability.