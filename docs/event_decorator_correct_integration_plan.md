# Event Decorator CORRECT Integration Plan

## Core Understanding

**WE ARE KEEPING THE DECORATORS** but fixing them to reference the **ACTUAL ENTITIES** involved in the computation, not create fake entities.

## Problem Analysis

The other agent's implementation has the right idea (decorators on CallableRegistry methods) but wrong execution:

### Current INCORRECT Implementation:

```python
@emit_events(
    creating_factory=lambda cls, func_name, **kwargs: ProcessingEvent(
        subject_type=None,  # 🚨 WRONG - should be actual input entity
        subject_id=None,    # 🚨 WRONG - should be actual input entity
        process_name="function_execution",
        metadata={
            "function_name": func_name,
            "input_count": len(kwargs)
        }
    ),
    created_factory=lambda result, cls, func_name, **kwargs: ProcessedEvent(
        subject_type=type(result[0]) if isinstance(result, list) else type(result),
        subject_id=result[0].ecs_id if isinstance(result, list) else result.ecs_id,  # ✅ This part is correct
        process_name="function_execution",
        result_summary={
            "function_name": func_name,
            "output_count": len(result) if isinstance(result, list) else 1
        }
    )
)
```

### Problems Identified:

1. **creating_factory**: Uses `subject_type=None, subject_id=None` instead of referencing actual INPUT entities from `kwargs`
2. **created_factory**: This part is actually CORRECT - it references the actual output entities  
3. **FunctionExecution constructor**: Uses non-existent `ecs_id=execution_id` parameter

## CORRECT Event Decorator Integration

### ✅ CORRECT creating_factory:
Should extract the actual input entities from `kwargs`:

```python
creating_factory=lambda cls, func_name, **kwargs: ProcessingEvent(
    subject_type=cls._get_primary_input_entity_type(kwargs),  # Actual input entity type
    subject_id=cls._get_primary_input_entity_id(kwargs),      # Actual input entity ID
    process_name="function_execution",
    metadata={
        "function_name": func_name,
        "input_count": len(kwargs),
        "input_entity_types": [type(v).__name__ for v in kwargs.values() if isinstance(v, Entity)]
    }
)
```

### ✅ CORRECT created_factory:
The current implementation is actually mostly correct:

```python
created_factory=lambda result, cls, func_name, **kwargs: ProcessedEvent(
    subject_type=type(result[0]) if isinstance(result, list) else type(result),  # ✅ Correct
    subject_id=result[0].ecs_id if isinstance(result, list) else result.ecs_id,  # ✅ Correct
    process_name="function_execution",
    result_summary={
        "function_name": func_name,
        "output_count": len(result) if isinstance(result, list) else 1
    }
)
```

## Required Helper Methods

Add these helper methods to CallableRegistry:

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

## Fix FunctionExecution Constructor

**Current INCORRECT:**
```python
execution_record = FunctionExecution(
    ecs_id=execution_id,  # 🚨 WRONG - no ecs_id parameter
    function_name=function_name,
    input_entity_id=input_entity.ecs_id if input_entity else None,
    output_entity_ids=[e.ecs_id for e in output_entities]
)
```

**CORRECT:**
```python
execution_record = FunctionExecution(
    function_name=function_name,
    input_entity_id=input_entity.ecs_id if input_entity else None,
    output_entity_ids=[e.ecs_id for e in output_entities]
)
# ecs_id is automatically assigned by Entity base class
```

## Complete CORRECT Implementation

```python
@classmethod
@emit_events(
    creating_factory=lambda cls, func_name, **kwargs: ProcessingEvent(
        subject_type=cls._get_primary_input_entity_type(kwargs),
        subject_id=cls._get_primary_input_entity_id(kwargs),
        process_name="function_execution",
        metadata={
            "function_name": func_name,
            "input_count": len(kwargs),
            "input_entity_types": [type(v).__name__ for v in kwargs.values() if isinstance(v, Entity)]
        }
    ),
    created_factory=lambda result, cls, func_name, **kwargs: ProcessedEvent(
        subject_type=type(result[0]) if isinstance(result, list) else type(result),
        subject_id=result[0].ecs_id if isinstance(result, list) else result.ecs_id,
        process_name="function_execution",
        result_summary={
            "function_name": func_name,
            "output_count": len(result) if isinstance(result, list) else 1
        }
    )
)
async def aexecute(cls, func_name: str, **kwargs) -> Union[Entity, List[Entity]]:
    """Execute function using entity-native patterns (async)."""
    return await cls._execute_async(func_name, **kwargs)
```

## Architectural Principles Maintained

1. **Events as Pure Signals**: Events contain only UUID references to ACTUAL entities involved
2. **Entity Reference Integrity**: Events reference the real input/output entities from the computation
3. **No Fake Entities**: No creation of artificial tracking entities - use the real ones
4. **Decorator Pattern**: Proper event decoration of registry methods for automatic event emission

## Key Changes Required

1. **Fix creating_factory**: Reference actual input entities instead of None
2. **Add helper methods**: `_get_primary_input_entity_type` and `_get_primary_input_entity_id`
3. **Fix FunctionExecution constructor**: Remove `ecs_id=execution_id` parameter
4. **Keep created_factory**: It's already correct - references actual output entities

This maintains the decorator pattern while ensuring events reference the ACTUAL entities involved in the computation, not fake tracking entities.