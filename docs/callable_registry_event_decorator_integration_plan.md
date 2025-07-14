# Callable Registry Event Decorator Integration Plan
## Phase 3b.2 - Complete Event Integration with UUID Tracking

### Overview

This plan details the integration of the enhanced [`callable_events.py`](../abstractions/events/callable_events.py) module with [`callable_registry.py`](../abstractions/ecs/callable_registry.py). The new events include comprehensive UUID tracking for cascade implementation and reactive computation.

### Current State Analysis

#### Existing Event Integration
- **Current**: Simple `@emit_events` decorator on [`aexecute()`](../abstractions/ecs/callable_registry.py:361-380)
- **Problem**: Uses generic `ProcessingEvent`/`ProcessedEvent` with minimal context
- **Missing**: UUID tracking, execution phase events, specialized event types

#### New Event Architecture
- **10 specialized event pairs** with complete UUID tracking
- **Execution phase coverage** from strategy detection to finalization
- **Cascade-ready** with input/output entity relationships
- **Hierarchical nesting** with automatic parent-child linking

## Integration Strategy

### Phase 1: Import and Setup

#### 1.1 Import Specialized Events
**Location**: [`callable_registry.py:32-34`](../abstractions/ecs/callable_registry.py:32-34)

```python
# Event system imports for automatic event emission
from abstractions.events.events import emit_events, ProcessingEvent, ProcessedEvent
from abstractions.events.callable_events import (
    FunctionExecutionEvent, FunctionExecutedEvent,
    StrategyDetectionEvent, StrategyDetectedEvent,
    InputPreparationEvent, InputPreparedEvent,
    SemanticAnalysisEvent, SemanticAnalyzedEvent,
    UnpackingEvent, UnpackedEvent,
    ResultFinalizationEvent, ResultFinalizedEvent,
    ConfigEntityCreationEvent, ConfigEntityCreatedEvent,
    PartialExecutionEvent, PartialExecutedEvent,
    TransactionalExecutionEvent, TransactionalExecutedEvent,
    ValidationEvent, ValidatedEvent
)
```

#### 1.2 UUID Extraction Utilities
**Location**: After imports, before `FunctionSignatureCache`

```python
def extract_entity_uuids(kwargs: Dict[str, Any]) -> Tuple[List[UUID], List[str]]:
    """Extract UUIDs and types from kwargs for event tracking."""
    entity_ids = []
    entity_types = []
    
    for param_name, value in kwargs.items():
        if isinstance(value, Entity):
            entity_ids.append(value.ecs_id)
            entity_types.append(type(value).__name__)
        elif isinstance(value, str) and value.startswith('@'):
            # Extract UUID from address format
            try:
                uuid_part = value[1:].split('.')[0]
                entity_ids.append(UUID(uuid_part))
                entity_types.append("AddressReference")
            except (ValueError, IndexError):
                pass
    
    return entity_ids, entity_types

def extract_config_entity_uuids(config_entities: List[Any]) -> List[UUID]:
    """Extract UUIDs from config entities."""
    return [ce.ecs_id for ce in config_entities if hasattr(ce, 'ecs_id')]
```

### Phase 2: Main Execution Pipeline Integration

#### 2.1 Replace Main aexecute Decorator
**Location**: [`callable_registry.py:361-380`](../abstractions/ecs/callable_registry.py:361-380)

**Current**:
```python
@emit_events(
    creating_factory=lambda cls, func_name, **kwargs: ProcessingEvent(...),
    created_factory=lambda result, cls, func_name, **kwargs: ProcessedEvent(...)
)
```

**New**:
```python
@emit_events(
    creating_factory=lambda cls, func_name, **kwargs: FunctionExecutionEvent(
        function_name=func_name,
        execution_strategy=None,  # Will be determined during execution
        input_entity_ids=extract_entity_uuids(kwargs)[0],
        input_entity_types=extract_entity_uuids(kwargs)[1],
        input_parameter_count=len(kwargs),
        input_entity_count=len([v for v in kwargs.values() if isinstance(v, Entity)]),
        input_primitive_count=len([v for v in kwargs.values() if not isinstance(v, Entity)]),
        is_async=cls.get_metadata(func_name).is_async if cls.get_metadata(func_name) else False,
        uses_config_entity=cls.get_metadata(func_name).uses_config_entity if cls.get_metadata(func_name) else False,
        expected_output_count=cls.get_metadata(func_name).expected_output_count if cls.get_metadata(func_name) else 1,
        execution_pattern="determining"
    ),
    created_factory=lambda result, cls, func_name, **kwargs: FunctionExecutedEvent(
        function_name=func_name,
        execution_successful=True,
        input_entity_ids=extract_entity_uuids(kwargs)[0],
        output_entity_ids=[result.ecs_id] if isinstance(result, Entity) else [e.ecs_id for e in result] if isinstance(result, list) else [],
        created_entity_ids=[],  # Will be populated during execution
        modified_entity_ids=[],  # Will be populated during execution
        config_entity_ids=[],  # Will be populated during execution
        execution_record_id=None,  # Will be populated during execution
        execution_strategy="completed",
        output_entity_count=1 if isinstance(result, Entity) else len(result) if isinstance(result, list) else 0,
        semantic_results=[],  # Will be populated during execution
        execution_duration_ms=0.0,  # Will be calculated during execution
        total_events_generated=0,  # Will be calculated during execution
        execution_id=None  # Will be populated during execution
    )
)
```

### Phase 3: Execution Phase Event Integration

#### 3.1 Strategy Detection Events
**Location**: [`_detect_execution_strategy()`](../abstractions/ecs/callable_registry.py:422-464)

**Add at start of method**:
```python
@emit_events(
    creating_factory=lambda cls, kwargs, metadata: StrategyDetectionEvent(
        function_name=metadata.name,
        input_entity_ids=extract_entity_uuids(kwargs)[0],
        input_entity_types=extract_entity_uuids(kwargs)[1],
        config_entity_ids=[],  # Will be populated during detection
        entity_type_mapping={str(uuid): type_name for uuid, type_name in zip(*extract_entity_uuids(kwargs))},
        input_types={name: type(value).__name__ for name, value in kwargs.items()},
        entity_count=len([v for v in kwargs.values() if isinstance(v, Entity)]),
        config_entity_count=0,  # Will be calculated
        primitive_count=len([v for v in kwargs.values() if not isinstance(v, Entity)]),
        has_metadata=metadata is not None,
        detection_method="signature_analysis"
    ),
    created_factory=lambda result, cls, kwargs, metadata: StrategyDetectedEvent(
        function_name=metadata.name,
        detection_successful=True,
        input_entity_ids=extract_entity_uuids(kwargs)[0],
        config_entity_ids=[],  # Will be populated
        entity_type_mapping={str(uuid): type_name for uuid, type_name in zip(*extract_entity_uuids(kwargs))},
        detected_strategy=result,
        strategy_reasoning=f"Detected {result} based on input analysis",
        execution_path="determined_from_strategy",
        decision_factors=[],
        confidence_level="high"
    )
)
```

#### 3.2 Input Preparation Events
**Location**: [`_execute_with_partial()`](../abstractions/ecs/callable_registry.py:493-648), [`_execute_borrowing()`](../abstractions/ecs/callable_registry.py:718-785), [`_execute_transactional()`](../abstractions/ecs/callable_registry.py:788-831)

**Add to each method**:
```python
@emit_events(
    creating_factory=lambda cls, metadata, kwargs: InputPreparationEvent(
        function_name=metadata.name,
        preparation_type="entity_creation",  # or "borrowing", "isolation", "config_creation"
        input_entity_ids=extract_entity_uuids(kwargs)[0],
        entity_count=len([v for v in kwargs.values() if isinstance(v, Entity)]),
        requires_isolation=True,  # Based on method
        requires_config_entity=metadata.uses_config_entity,
        pattern_classification=None,  # Will be determined
        borrowing_operations_needed=0  # Will be calculated
    ),
    created_factory=lambda result, cls, metadata, kwargs: InputPreparedEvent(
        function_name=metadata.name,
        preparation_successful=True,
        input_entity_ids=extract_entity_uuids(kwargs)[0],
        created_entities=[],  # Will be populated with created entity UUIDs
        config_entities_created=[],  # Will be populated with config entity UUIDs
        execution_copy_ids=[],  # Will be populated with execution copy UUIDs
        borrowed_from_entities=[],  # Will be populated with borrowed entity UUIDs
        object_identity_map_size=0,  # Will be calculated
        isolation_successful=True,
        borrowing_operations_completed=0,  # Will be calculated
        preparation_duration_ms=0.0  # Will be calculated
    )
)
```

#### 3.3 Semantic Analysis Events
**Location**: [`_detect_execution_semantic()`](../abstractions/ecs/callable_registry.py:912-938)

```python
@emit_events(
    creating_factory=lambda cls, result, object_identity_map: SemanticAnalysisEvent(
        function_name="semantic_analysis",  # Will be passed from context
        input_entity_ids=[e.ecs_id for e in object_identity_map.values()],
        result_entity_ids=[result.ecs_id] if isinstance(result, Entity) else [],
        result_type=type(result).__name__,
        analysis_method="object_identity",
        has_object_identity_map=len(object_identity_map) > 0,
        input_entity_count=len(object_identity_map),
        result_entity_count=1 if isinstance(result, Entity) else 0
    ),
    created_factory=lambda semantic_result, cls, result, object_identity_map: SemanticAnalyzedEvent(
        function_name="semantic_analysis",
        analysis_successful=True,
        input_entity_ids=[e.ecs_id for e in object_identity_map.values()],
        result_entity_ids=[result.ecs_id] if isinstance(result, Entity) else [],
        analyzed_entity_ids=[result.ecs_id] if isinstance(result, Entity) else [],
        original_entity_id=semantic_result[1].ecs_id if semantic_result[1] else None,
        semantic_type=semantic_result[0],
        confidence_level="high",
        analysis_duration_ms=0.0,
        entities_analyzed=1
    )
)
```

#### 3.4 Unpacking Events
**Location**: [`_finalize_multi_entity_result()`](../abstractions/ecs/callable_registry.py:994-1061)

```python
@emit_events(
    creating_factory=lambda cls, result, metadata, object_identity_map, input_entity, execution_id: UnpackingEvent(
        function_name=metadata.name,
        source_entity_ids=[input_entity.ecs_id] if input_entity else [],
        unpacking_pattern=metadata.output_pattern,
        expected_entity_count=metadata.expected_output_count,
        container_type=type(result).__name__,
        supports_unpacking=metadata.supports_unpacking,
        requires_container_entity=True
    ),
    created_factory=lambda unpacked_result, cls, result, metadata, object_identity_map, input_entity, execution_id: UnpackedEvent(
        function_name=metadata.name,
        unpacking_successful=True,
        source_entity_ids=[input_entity.ecs_id] if input_entity else [],
        unpacked_entity_ids=[e.ecs_id for e in unpacked_result if isinstance(e, Entity)],
        container_entity_id=unpacked_result.container_entity.ecs_id if hasattr(unpacked_result, 'container_entity') and unpacked_result.container_entity else None,
        sibling_entity_ids=[e.ecs_id for e in unpacked_result if isinstance(e, Entity)],
        unpacked_entity_count=len([e for e in unpacked_result if isinstance(e, Entity)]),
        sibling_relationships_created=len([e for e in unpacked_result if isinstance(e, Entity)]) > 1,
        unpacking_duration_ms=0.0
    )
)
```

#### 3.5 Config Entity Creation Events
**Location**: [`create_config_entity_from_primitives()`](../abstractions/ecs/callable_registry.py:651-690)

```python
@emit_events(
    creating_factory=lambda cls, function_name, primitive_params, expected_config_type: ConfigEntityCreationEvent(
        function_name=function_name,
        source_entity_ids=[],  # Config entities created from primitives
        config_type="dynamic" if expected_config_type is None else "explicit",
        expected_config_class=expected_config_type.__name__ if expected_config_type else None,
        primitive_params_count=len(primitive_params),
        has_expected_type=expected_config_type is not None
    ),
    created_factory=lambda config_entity, cls, function_name, primitive_params, expected_config_type: ConfigEntityCreatedEvent(
        function_name=function_name,
        creation_successful=True,
        config_entity_id=config_entity.ecs_id,
        source_entity_ids=[],  # Created from primitives
        config_entity_type=type(config_entity).__name__,
        fields_populated=len(primitive_params),
        registered_in_ecs=True,
        creation_duration_ms=0.0
    )
)
```

### Phase 4: Validation and Error Handling

#### 4.1 Validation Events
**Location**: Function registration and validation points

```python
@emit_events(
    creating_factory=lambda cls, func_name, validation_context: ValidationEvent(
        function_name=func_name,
        validated_entity_ids=[],  # Will be populated with validated entity UUIDs
        validation_type="signature",
        items_to_validate=1,
        has_type_hints=True,
        has_constraints=False
    ),
    created_factory=lambda validation_result, cls, func_name, validation_context: ValidatedEvent(
        function_name=func_name,
        validation_successful=validation_result,
        validated_entity_ids=[],  # Will be populated with validated entity UUIDs
        validation_errors=[],
        warnings=[],
        validation_duration_ms=0.0
    )
)
```

### Phase 5: Execution Context Enhancement

#### 5.1 Execution ID Generation
**Location**: All execution methods

```python
def generate_execution_context():
    """Generate execution context with UUID tracking."""
    execution_id = uuid4()
    execution_start_time = time.time()
    
    return {
        'execution_id': execution_id,
        'start_time': execution_start_time,
        'entity_tracking': {
            'input_entities': [],
            'created_entities': [],
            'modified_entities': [],
            'config_entities': []
        }
    }
```

#### 5.2 Context Propagation
**Location**: Throughout execution pipeline

```python
def propagate_execution_context(context: Dict[str, Any], event_data: Dict[str, Any]):
    """Propagate execution context to events."""
    event_data['execution_id'] = context['execution_id']
    event_data['execution_duration_ms'] = (time.time() - context['start_time']) * 1000
    
    # Merge entity tracking
    event_data.update(context['entity_tracking'])
```

### Phase 6: Entity Lifecycle Integration

#### 6.1 Entity Creation Tracking
**Location**: Entity creation points

```python
def track_entity_creation(entity: Entity, context: Dict[str, Any]):
    """Track entity creation in execution context."""
    context['entity_tracking']['created_entities'].append(entity.ecs_id)

def track_entity_modification(entity: Entity, context: Dict[str, Any]):
    """Track entity modification in execution context."""
    context['entity_tracking']['modified_entities'].append(entity.ecs_id)

def track_config_entity_creation(config_entity: ConfigEntity, context: Dict[str, Any]):
    """Track config entity creation in execution context."""
    context['entity_tracking']['config_entities'].append(config_entity.ecs_id)
```

## Implementation Order

### Step 1: Core Infrastructure (Priority: HIGH)
1. **Import statements** and **UUID extraction utilities**
2. **Main aexecute decorator** replacement
3. **Execution context generation** and **propagation**

### Step 2: Execution Phase Events (Priority: HIGH)
1. **Strategy detection events** (`_detect_execution_strategy`)
2. **Input preparation events** (all `_execute_*` methods)
3. **Semantic analysis events** (`_detect_execution_semantic`)

### Step 3: Specialized Events (Priority: MEDIUM)
1. **Config entity creation events** (`create_config_entity_from_primitives`)
2. **Unpacking events** (`_finalize_multi_entity_result`)
3. **Validation events** (registration and validation points)

### Step 4: Entity Lifecycle Integration (Priority: LOW)
1. **Entity creation tracking** throughout pipeline
2. **Entity modification tracking** in semantic analysis
3. **Context cleanup** and **resource management**

## Expected Outcomes

### Immediate Benefits
- **Complete UUID tracking** for cascade implementation
- **Hierarchical event nesting** with automatic parent-child relationships
- **Execution phase visibility** from strategy detection to finalization
- **Entity lifecycle observability** throughout function execution

### Cascade Implementation Ready
- **Input/output entity relationships** tracked for dependency analysis
- **Execution context preservation** for reactive computation
- **Config entity lifecycle** managed for parameter tracking
- **Semantic analysis results** available for cache invalidation

### Performance Monitoring
- **Execution duration tracking** at each phase
- **Entity count metrics** for performance analysis
- **Error context preservation** for debugging
- **Resource usage tracking** for optimization

## Testing Strategy

### Unit Tests
- **Event emission verification** at each execution phase
- **UUID tracking accuracy** for entity relationships
- **Context propagation integrity** through execution pipeline
- **Error handling robustness** with event preservation

### Integration Tests
- **Hierarchical event nesting** with nested function calls
- **Entity lifecycle events** with complex entity operations
- **Config entity management** with dynamic creation
- **Multi-entity result unpacking** with sibling relationships

### Performance Tests
- **Event emission overhead** measurement
- **UUID extraction performance** with large entity sets
- **Context propagation efficiency** through execution pipeline
- **Memory usage tracking** with event accumulation

This comprehensive integration will transform the callable registry into a fully observable, cascade-ready execution engine with complete UUID tracking and hierarchical event emission.