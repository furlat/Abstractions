# Event Decorator Analysis: All Decorators Across Codebase

## Current Event Decorator Usage

I found 6 `@emit_events` decorators across the codebase. Let me analyze each one:

### 1. ✅ CORRECT: EntityRegistry.version_entity() (entity.py:1415)

```python
@emit_events(
    creating_factory=lambda cls, entity, force_versioning=False: ModifyingEvent(
        subject_type=type(entity),        # ✅ References actual entity parameter
        subject_id=entity.ecs_id,         # ✅ References actual entity parameter
        fields=["ecs_id", "version"]
    ),
    created_factory=lambda result, cls, entity, force_versioning=False: ModifiedEvent(
        subject_type=type(entity),        # ✅ References actual entity parameter
        subject_id=entity.ecs_id,         # ✅ References actual entity parameter
        fields=["ecs_id", "version"]
    )
)
def version_entity(cls, entity: "Entity", force_versioning: bool = False) -> bool:
```

**Why this is correct:**
- References the actual `entity` parameter passed to the function
- Uses `type(entity)` for subject_type and `entity.ecs_id` for subject_id
- Events contain references to the ACTUAL entity being versioned

### 2. ✅ CORRECT: Entity.promote_to_root() (entity.py:1717)

```python
@emit_events(
    creating_factory=lambda self: StateTransitionEvent(
        subject_type=type(self),          # ✅ References actual entity (self)
        subject_id=self.ecs_id,           # ✅ References actual entity (self)
        from_state="child_entity",
        to_state="root_entity",
        transition_reason="promotion"
    )
)
def promote_to_root(self) -> None:
```

**Why this is correct:**
- References `self` which is the actual entity being promoted
- Events contain references to the ACTUAL entity undergoing state transition

### 3. ✅ CORRECT: Entity.detach() (entity.py:1735)

```python
@emit_events(
    creating_factory=lambda self: StateTransitionEvent(
        subject_type=type(self),          # ✅ References actual entity (self)
        subject_id=self.ecs_id,           # ✅ References actual entity (self)
        from_state="attached_entity",
        to_state="detached_entity",
        transition_reason="detachment"
    )
)
def detach(self) -> None:
```

**Why this is correct:**
- References `self` which is the actual entity being detached
- Events contain references to the ACTUAL entity undergoing state transition

### 4. ✅ CORRECT: Entity.attach() (entity.py:1849)

```python
@emit_events(
    creating_factory=lambda self, new_root_entity: StateTransitionEvent(
        subject_type=type(self),          # ✅ References actual entity (self)
        subject_id=self.ecs_id,           # ✅ References actual entity (self)
        from_state="root_entity",
        to_state="attached_entity",
        transition_reason="attachment",
        metadata={"new_root_id": str(new_root_entity.ecs_id)}  # ✅ References actual target entity
    )
)
def attach(self, new_root_entity: "Entity") -> None:
```

**Why this is correct:**
- References `self` (the entity being attached) and `new_root_entity` (the target)
- Events contain references to the ACTUAL entities involved in the operation

### 5. ❌ INCORRECT: CallableRegistry.aexecute() (callable_registry.py:361)

```python
@emit_events(
    creating_factory=lambda cls, func_name, **kwargs: ProcessingEvent(
        subject_type=None,                # ❌ Should reference actual input entity
        subject_id=None,                  # ❌ Should reference actual input entity
        process_name="function_execution",
        metadata={
            "function_name": func_name,
            "input_count": len(kwargs)
        }
    ),
    created_factory=lambda result, cls, func_name, **kwargs: ProcessedEvent(
        subject_type=type(result[0]) if isinstance(result, list) else type(result),  # ✅ This is correct
        subject_id=result[0].ecs_id if isinstance(result, list) else result.ecs_id,  # ✅ This is correct
        process_name="function_execution",
        result_summary={
            "function_name": func_name,
            "output_count": len(result) if isinstance(result, list) else 1
        }
    )
)
```

**Why this is wrong:**
- `creating_factory` uses `subject_type=None, subject_id=None` instead of referencing actual input entities
- `created_factory` is actually CORRECT - it references the actual output entities
- Should extract the primary input entity from `kwargs` to reference in events

### 6. ✅ CORRECT: Example in events.py (events.py:901)

This is just documentation/example code, not actual usage.

## Correct Pattern Summary

The correct pattern for event decorators is:

1. **Reference ACTUAL entities involved in the operation**
2. **For entity methods**: Use `self` to reference the entity
3. **For class methods**: Use the actual entity parameters
4. **For function calls**: Extract actual entities from parameters

## The Fix Needed

**Only ONE decorator needs fixing:** `CallableRegistry.aexecute()` 

The problem is in the `creating_factory` - it should:
1. Extract the primary input entity from `kwargs`
2. Reference that entity in the event
3. If no entities in kwargs, then use `None` (which is correct for pure primitive functions)

## Recommended Fix

```python
@emit_events(
    creating_factory=lambda cls, func_name, **kwargs: ProcessingEvent(
        subject_type=cls._get_primary_input_entity_type(kwargs),  # ✅ Extract from actual inputs
        subject_id=cls._get_primary_input_entity_id(kwargs),      # ✅ Extract from actual inputs
        process_name="function_execution",
        metadata={
            "function_name": func_name,
            "input_count": len(kwargs),
            "input_entity_types": [type(v).__name__ for v in kwargs.values() if isinstance(v, Entity)]
        }
    ),
    created_factory=lambda result, cls, func_name, **kwargs: ProcessedEvent(
        subject_type=type(result[0]) if isinstance(result, list) else type(result),  # ✅ Keep as is
        subject_id=result[0].ecs_id if isinstance(result, list) else result.ecs_id,  # ✅ Keep as is
        process_name="function_execution",
        result_summary={
            "function_name": func_name,
            "output_count": len(result) if isinstance(result, list) else 1
        }
    )
)
```

## Helper Methods Needed

Add these to CallableRegistry:

```python
@classmethod
def _get_primary_input_entity_type(cls, kwargs: Dict[str, Any]) -> Optional[Type]:
    """Get the type of the primary input entity from kwargs."""
    for value in kwargs.values():
        if isinstance(value, Entity):
            return type(value)
    return None

@classmethod  
def _get_primary_input_entity_id(cls, kwargs: Dict[str, Any]) -> Optional[UUID]:
    """Get the ID of the primary input entity from kwargs."""
    for value in kwargs.values():
        if isinstance(value, Entity):
            return value.ecs_id
    return None
```

## Summary

- **4 decorators are CORRECT** - they properly reference actual entities
- **1 decorator needs fixing** - CallableRegistry.aexecute() creating_factory
- **1 is just documentation** - no action needed

The fix maintains the architectural principle of "Events as Pure Signals" while ensuring events reference the ACTUAL entities involved in computations, not fake tracking entities.