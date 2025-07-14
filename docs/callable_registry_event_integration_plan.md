# Callable Registry Event Integration Plan

## Overview

With the successful implementation of automatic event nesting, we can now provide complete observability into callable registry operations using typed events and hierarchical event structures.

## Key Principles

1. **Never Predict Information** - Events only contain information available at that specific execution point
2. **Automatic Nesting** - Use context management to create hierarchical event structures
3. **Typed Events** - Use specific event types for different operations
4. **Complete Observability** - Every significant operation emits events

## Event Hierarchy Design

### Root Level: Function Execution
```
FunctionExecutionEvent (root)
├── StrategyDetectionEvent
│   └── StrategyDetectedEvent
├── InputPreparationEvent
│   ├── EntityCreationEvent
│   │   └── EntityCreatedEvent
│   └── InputPreparedEvent
├── ExecutionEvent
│   ├── SemanticAnalysisEvent
│   │   └── SemanticAnalyzedEvent
│   ├── UnpackingEvent (if multi-entity)
│   │   └── UnpackedEvent
│   └── ExecutedEvent
└── FunctionExecutedEvent
```

## New Typed Events Needed

### 1. Function Execution Events
```python
class FunctionExecutionEvent(ProcessingEvent):
    """Event for function execution start."""
    function_name: str
    execution_strategy: Optional[str] = None
    input_parameter_count: int
    expected_output_count: int
    execution_pattern: str  # "single_entity", "multi_entity", "config_entity"

class FunctionExecutedEvent(ProcessedEvent):
    """Event for function execution completion."""
    function_name: str
    execution_strategy: str
    output_entity_count: int
    execution_duration_ms: float
    semantic_results: List[str]  # ["creation", "mutation", "detachment"]
```

### 2. Strategy Detection Events
```python
class StrategyDetectionEvent(ProcessingEvent):
    """Event for execution strategy detection."""
    input_types: Dict[str, str]  # param_name -> type
    entity_count: int
    config_entity_count: int
    primitive_count: int

class StrategyDetectedEvent(ProcessedEvent):
    """Event for strategy detection completion."""
    detected_strategy: str
    strategy_reasoning: str
    execution_path: str  # "transactional", "borrowing", "partial"
```

### 3. Input Preparation Events
```python
class InputPreparationEvent(ProcessingEvent):
    """Event for input preparation start."""
    preparation_type: str  # "entity_creation", "borrowing", "isolation"
    entity_count: int

class InputPreparedEvent(ProcessedEvent):
    """Event for input preparation completion."""
    created_entities: List[UUID]
    object_identity_map_size: int
    isolation_successful: bool
```

### 4. Semantic Analysis Events
```python
class SemanticAnalysisEvent(ProcessingEvent):
    """Event for semantic analysis start."""
    result_type: str
    analysis_method: str  # "object_identity", "ecs_id_comparison"

class SemanticAnalyzedEvent(ProcessedEvent):
    """Event for semantic analysis completion."""
    semantic_type: str  # "creation", "mutation", "detachment"
    confidence_level: str  # "high", "medium", "low"
    original_entity_id: Optional[UUID]
```

### 5. Unpacking Events
```python
class UnpackingEvent(ProcessingEvent):
    """Event for multi-entity unpacking start."""
    unpacking_pattern: str  # "list_return", "tuple_return", "dict_return"
    expected_entity_count: int
    container_type: str

class UnpackedEvent(ProcessedEvent):
    """Event for unpacking completion."""
    unpacked_entity_count: int
    container_entity_id: Optional[UUID]
    sibling_relationships_created: bool
```

## Implementation Strategy

### Phase 1: Create Typed Events
1. Add new event types to `typed_events.py`
2. Ensure proper inheritance and field definitions
3. No circular dependencies

### Phase 2: Integrate with Callable Registry
1. Replace basic `ProcessingEvent`/`ProcessedEvent` with specific types
2. Add `@emit_events` decorators to internal methods
3. Use automatic nesting for hierarchical structure

### Phase 3: Strategic Integration Points

#### A. Main Execution Methods
```python
@emit_events(
    creating_factory=lambda cls, func_name, **kwargs: FunctionExecutionEvent(
        subject_type=None,
        subject_id=None,
        process_name="function_execution",
        function_name=func_name,
        input_parameter_count=len(kwargs),
        execution_pattern="unknown"  # Will be determined
    ),
    created_factory=lambda result, cls, func_name, **kwargs: FunctionExecutedEvent(
        subject_type=type(result[0]) if isinstance(result, list) else type(result),
        subject_id=result[0].ecs_id if isinstance(result, list) else result.ecs_id,
        process_name="function_execution",
        function_name=func_name,
        output_entity_count=len(result) if isinstance(result, list) else 1
    )
)
async def aexecute(cls, func_name: str, **kwargs):
    # Existing implementation
```

#### B. Strategy Detection
```python
@emit_events(
    creating_factory=lambda cls, kwargs, metadata: StrategyDetectionEvent(
        subject_type=None,
        subject_id=None,
        process_name="strategy_detection",
        input_types={k: type(v).__name__ for k, v in kwargs.items()},
        entity_count=sum(1 for v in kwargs.values() if isinstance(v, Entity))
    ),
    created_factory=lambda result, cls, kwargs, metadata: StrategyDetectedEvent(
        subject_type=None,
        subject_id=None,
        process_name="strategy_detection",
        detected_strategy=result,
        execution_path="determined"
    )
)
def _detect_execution_strategy(cls, kwargs, metadata):
    # Existing implementation
```

#### C. Semantic Analysis
```python
@emit_events(
    creating_factory=lambda cls, result, object_identity_map: SemanticAnalysisEvent(
        subject_type=type(result),
        subject_id=result.ecs_id if hasattr(result, 'ecs_id') else None,
        process_name="semantic_analysis",
        result_type=type(result).__name__,
        analysis_method="object_identity"
    ),
    created_factory=lambda semantic_result, cls, result, object_identity_map: SemanticAnalyzedEvent(
        subject_type=type(result),
        subject_id=result.ecs_id if hasattr(result, 'ecs_id') else None,
        process_name="semantic_analysis",
        semantic_type=semantic_result[0],
        original_entity_id=semantic_result[1].ecs_id if semantic_result[1] else None
    )
)
def _detect_execution_semantic(cls, result, object_identity_map):
    # Existing implementation
```

## Benefits

### 1. Complete Observability
- Every significant operation is tracked
- Hierarchical structure shows relationships
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

## Implementation Steps

1. **Create new typed events** in `typed_events.py`
2. **Add event decorators** to strategic methods in `callable_registry.py`
3. **Test automatic nesting** with sample functions
4. **Verify no circular dependencies** 
5. **Update documentation** with event patterns

## Testing Strategy

1. **Unit tests** for each new event type
2. **Integration tests** for nested event structures
3. **Performance tests** to ensure minimal overhead
4. **Behavioral tests** to verify automatic nesting works correctly

## Success Criteria

- [ ] All major callable registry operations emit typed events
- [ ] Events are properly nested using automatic context management
- [ ] No circular dependencies introduced
- [ ] Complete observability into function execution
- [ ] Minimal performance impact
- [ ] Clean, maintainable code structure