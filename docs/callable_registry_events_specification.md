# Callable Registry Events Specification

## Overview

This document specifies the exact event types and integration patterns needed for comprehensive callable registry observability using our automatic nesting system.

## Event Type Definitions

### 1. Function Execution Events

#### FunctionExecutionEvent
**Purpose**: Root event for function execution start
**Parent**: ProcessingEvent
**Fields**:
```python
function_name: str
execution_strategy: Optional[str] = None  # Determined later
input_parameter_count: int
expected_output_count: int
execution_pattern: str  # "single_entity", "multi_entity", "config_entity"
uses_config_entity: bool
is_async: bool
```

#### FunctionExecutedEvent
**Purpose**: Root event for function execution completion
**Parent**: ProcessedEvent
**Fields**:
```python
function_name: str
execution_strategy: str
output_entity_count: int
execution_duration_ms: float
semantic_results: List[str]  # ["creation", "mutation", "detachment"]
success: bool
error_message: Optional[str] = None
```

### 2. Strategy Detection Events

#### StrategyDetectionEvent
**Purpose**: Event for execution strategy detection start
**Parent**: ProcessingEvent
**Fields**:
```python
input_types: Dict[str, str]  # param_name -> type_name
entity_count: int
config_entity_count: int
primitive_count: int
metadata_available: bool
```

#### StrategyDetectedEvent
**Purpose**: Event for strategy detection completion
**Parent**: ProcessedEvent
**Fields**:
```python
detected_strategy: str  # "single_entity_with_config", "multi_entity_composite", etc.
strategy_reasoning: str
execution_path: str  # "transactional", "borrowing", "partial"
decision_factors: List[str]
```

### 3. Input Preparation Events

#### InputPreparationEvent
**Purpose**: Event for input preparation start
**Parent**: ProcessingEvent
**Fields**:
```python
preparation_type: str  # "entity_creation", "borrowing", "isolation", "config_creation"
entity_count: int
requires_isolation: bool
requires_config_entity: bool
```

#### InputPreparedEvent
**Purpose**: Event for input preparation completion
**Parent**: ProcessedEvent
**Fields**:
```python
created_entities: List[UUID]
object_identity_map_size: int
isolation_successful: bool
config_entities_created: List[UUID]
borrowing_operations: int
```

### 4. Semantic Analysis Events

#### SemanticAnalysisEvent
**Purpose**: Event for semantic analysis start
**Parent**: ProcessingEvent
**Fields**:
```python
result_type: str
analysis_method: str  # "object_identity", "ecs_id_comparison", "tree_analysis"
has_object_identity_map: bool
input_entity_count: int
```

#### SemanticAnalyzedEvent
**Purpose**: Event for semantic analysis completion
**Parent**: ProcessedEvent
**Fields**:
```python
semantic_type: str  # "creation", "mutation", "detachment"
confidence_level: str  # "high", "medium", "low"
original_entity_id: Optional[UUID]
analysis_duration_ms: float
```

### 5. Unpacking Events

#### UnpackingEvent
**Purpose**: Event for multi-entity unpacking start
**Parent**: ProcessingEvent
**Fields**:
```python
unpacking_pattern: str  # "list_return", "tuple_return", "dict_return"
expected_entity_count: int
container_type: str
supports_unpacking: bool
```

#### UnpackedEvent
**Purpose**: Event for unpacking completion
**Parent**: ProcessedEvent
**Fields**:
```python
unpacked_entity_count: int
container_entity_id: Optional[UUID]
sibling_relationships_created: bool
unpacking_successful: bool
```

### 6. Entity Operation Events

#### EntityVersioningEvent
**Purpose**: Event for entity versioning operations
**Parent**: VersioningEvent (from typed_events.py)
**Fields**:
```python
versioning_context: str  # "divergence_detected", "mutation_result", "detachment_cleanup"
triggered_by_function: str
original_entity_id: UUID
```

#### EntityVersionedEvent
**Purpose**: Event for entity versioning completion
**Parent**: VersionedEvent (from typed_events.py)
**Fields**:
```python
versioning_context: str
new_version_id: UUID
version_successful: bool
```

## Integration Points in CallableRegistry

### A. Main Execution Method (aexecute)

**Location**: `CallableRegistry.aexecute`
**Decorator**:
```python
@emit_events(
    creating_factory=lambda cls, func_name, **kwargs: FunctionExecutionEvent(
        subject_type=None,
        subject_id=None,
        process_name="function_execution",
        function_name=func_name,
        input_parameter_count=len(kwargs),
        execution_pattern="determining",
        uses_config_entity=False,  # Will be updated
        is_async=True
    ),
    created_factory=lambda result, cls, func_name, **kwargs: FunctionExecutedEvent(
        subject_type=type(result[0]) if isinstance(result, list) else type(result),
        subject_id=result[0].ecs_id if isinstance(result, list) else result.ecs_id,
        process_name="function_execution",
        function_name=func_name,
        execution_strategy="completed",
        output_entity_count=len(result) if isinstance(result, list) else 1,
        execution_duration_ms=0.0,  # Will be calculated
        semantic_results=[],  # Will be populated
        success=True
    )
)
```

### B. Strategy Detection Method

**Location**: `CallableRegistry._detect_execution_strategy`
**Decorator**:
```python
@emit_events(
    creating_factory=lambda cls, kwargs, metadata: StrategyDetectionEvent(
        subject_type=None,
        subject_id=None,
        process_name="strategy_detection",
        input_types={k: type(v).__name__ for k, v in kwargs.items()},
        entity_count=sum(1 for v in kwargs.values() if isinstance(v, Entity)),
        config_entity_count=sum(1 for v in kwargs.values() if isinstance(v, ConfigEntity)),
        primitive_count=sum(1 for v in kwargs.values() if not isinstance(v, Entity)),
        metadata_available=metadata is not None
    ),
    created_factory=lambda result, cls, kwargs, metadata: StrategyDetectedEvent(
        subject_type=None,
        subject_id=None,
        process_name="strategy_detection",
        detected_strategy=result,
        strategy_reasoning=f"Based on {len(kwargs)} parameters",
        execution_path="determined",
        decision_factors=[]  # Will be populated
    )
)
```

### C. Input Preparation Method

**Location**: `CallableRegistry._prepare_transactional_inputs`
**Decorator**:
```python
@emit_events(
    creating_factory=lambda cls, kwargs: InputPreparationEvent(
        subject_type=None,
        subject_id=None,
        process_name="input_preparation",
        preparation_type="transactional_isolation",
        entity_count=sum(1 for v in kwargs.values() if isinstance(v, Entity)),
        requires_isolation=True,
        requires_config_entity=False
    ),
    created_factory=lambda result, cls, kwargs: InputPreparedEvent(
        subject_type=None,
        subject_id=None,
        process_name="input_preparation",
        created_entities=[],  # Will be populated from result
        object_identity_map_size=len(result[3]) if len(result) > 3 else 0,
        isolation_successful=True,
        config_entities_created=[],
        borrowing_operations=0
    )
)
```

### D. Semantic Analysis Method

**Location**: `CallableRegistry._detect_execution_semantic`
**Decorator**:
```python
@emit_events(
    creating_factory=lambda cls, result, object_identity_map: SemanticAnalysisEvent(
        subject_type=type(result),
        subject_id=result.ecs_id if hasattr(result, 'ecs_id') else None,
        process_name="semantic_analysis",
        result_type=type(result).__name__,
        analysis_method="object_identity",
        has_object_identity_map=bool(object_identity_map),
        input_entity_count=len(object_identity_map)
    ),
    created_factory=lambda semantic_result, cls, result, object_identity_map: SemanticAnalyzedEvent(
        subject_type=type(result),
        subject_id=result.ecs_id if hasattr(result, 'ecs_id') else None,
        process_name="semantic_analysis",
        semantic_type=semantic_result[0],
        confidence_level="high",  # Object identity gives high confidence
        original_entity_id=semantic_result[1].ecs_id if semantic_result[1] else None,
        analysis_duration_ms=0.0  # Will be calculated
    )
)
```

### E. Multi-Entity Unpacking Method

**Location**: `CallableRegistry._finalize_multi_entity_result`
**Decorator**:
```python
@emit_events(
    creating_factory=lambda cls, result, metadata, object_identity_map, input_entity, execution_id: UnpackingEvent(
        subject_type=type(result),
        subject_id=None,
        process_name="multi_entity_unpacking",
        unpacking_pattern=metadata.output_pattern,
        expected_entity_count=metadata.expected_output_count,
        container_type=type(result).__name__,
        supports_unpacking=metadata.supports_unpacking
    ),
    created_factory=lambda final_result, cls, result, metadata, object_identity_map, input_entity, execution_id: UnpackedEvent(
        subject_type=type(final_result[0]) if isinstance(final_result, list) else type(final_result),
        subject_id=final_result[0].ecs_id if isinstance(final_result, list) else final_result.ecs_id,
        process_name="multi_entity_unpacking",
        unpacked_entity_count=len(final_result) if isinstance(final_result, list) else 1,
        container_entity_id=None,  # Will be populated if container created
        sibling_relationships_created=len(final_result) > 1 if isinstance(final_result, list) else False,
        unpacking_successful=True
    )
)
```

## Event Hierarchy Examples

### Example 1: Single Entity Function

```
FunctionExecutionEvent (function_name="analyze_student")
├── StrategyDetectionEvent
│   └── StrategyDetectedEvent (detected_strategy="single_entity_direct")
├── InputPreparationEvent (preparation_type="entity_creation")
│   └── InputPreparedEvent (created_entities=[uuid1])
├── SemanticAnalysisEvent (analysis_method="object_identity")
│   └── SemanticAnalyzedEvent (semantic_type="creation")
└── FunctionExecutedEvent (output_entity_count=1)
```

### Example 2: Multi-Entity Function with Config

```
FunctionExecutionEvent (function_name="batch_analysis")
├── StrategyDetectionEvent
│   └── StrategyDetectedEvent (detected_strategy="single_entity_with_config")
├── InputPreparationEvent (preparation_type="config_creation")
│   └── InputPreparedEvent (config_entities_created=[uuid1])
├── UnpackingEvent (unpacking_pattern="list_return")
│   └── UnpackedEvent (unpacked_entity_count=3)
└── FunctionExecutedEvent (output_entity_count=3)
```

### Example 3: Entity Mutation with Versioning

```
FunctionExecutionEvent (function_name="update_student")
├── StrategyDetectionEvent
│   └── StrategyDetectedEvent (detected_strategy="single_entity_direct")
├── SemanticAnalysisEvent
│   └── SemanticAnalyzedEvent (semantic_type="mutation")
├── EntityVersioningEvent (versioning_context="mutation_result")
│   └── EntityVersionedEvent (version_successful=true)
└── FunctionExecutedEvent (semantic_results=["mutation"])
```

## Implementation Guidelines

### 1. Event Factory Guidelines

- **Never predict information**: Only include data available at event creation time
- **Use Optional fields**: For information that might not be available
- **Populate during execution**: Update fields as information becomes available
- **Fail gracefully**: Handle missing information without breaking events

### 2. Automatic Nesting Guidelines

- **Trust the context system**: Let automatic nesting handle parent-child relationships
- **Focus on operation-specific data**: Don't duplicate context information
- **Use meaningful process names**: Clear identification of operation type
- **Maintain event boundaries**: Each operation should have clear start/end events

### 3. Performance Considerations

- **Lazy evaluation**: Only create events when bus is active
- **Minimal overhead**: Keep event creation lightweight
- **Batch operations**: Group related events when possible
- **Async-safe**: All event operations must be async-compatible

## Testing Strategy

### Unit Tests
- Test each event type creation
- Verify field validation
- Check inheritance relationships

### Integration Tests
- Test automatic nesting behavior
- Verify event hierarchy structure
- Check parent-child relationships

### Performance Tests
- Measure event creation overhead
- Test high-frequency operations
- Verify memory usage patterns

### End-to-End Tests
- Test complete function execution flows
- Verify event completeness
- Check error handling paths

## Benefits of This Approach

### 1. Complete Observability
- Every significant operation is tracked
- Clear hierarchy shows relationships
- No black boxes in execution

### 2. Debugging Capability
- Clear event trail for troubleshooting
- Semantic analysis results visible
- Strategy detection transparent

### 3. Performance Monitoring
- Execution duration tracking
- Strategy effectiveness analysis
- Bottleneck identification

### 4. Audit Trail
- Complete function execution history
- Entity transformation tracking
- Error context preservation

### 5. Automatic Nesting Benefits
- No manual parent-child management
- Consistent event hierarchy
- Context-aware event creation
- Thread-safe operation

## Success Metrics

- [ ] All major callable registry operations emit typed events
- [ ] Events are properly nested using automatic context management
- [ ] No circular dependencies introduced
- [ ] Complete observability into function execution
- [ ] Performance impact < 5% of execution time
- [ ] Event hierarchy depth correctly represents operation complexity
- [ ] All event types validate correctly
- [ ] Error paths properly tracked