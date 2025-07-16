# Callable Events Module Specification

## Overview

This document specifies the exact implementation details for `abstractions/events/callable_events.py` - the specialized module for callable registry-specific events.

## Module Structure

### Imports
```python
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import Field

# Import base events from events.py
from abstractions.events.events import (
    ProcessingEvent, ProcessedEvent
)
```

## Event Classes

### 1. Function Execution Events

#### FunctionExecutionEvent
```python
class FunctionExecutionEvent(ProcessingEvent):
    """Event emitted when function execution starts."""
    function_name: str
    execution_strategy: Optional[str] = None  # Will be determined
    
    # Input context
    input_parameter_count: int
    input_entity_count: int
    input_primitive_count: int
    
    # Function metadata
    is_async: bool
    uses_config_entity: bool
    expected_output_count: int
    
    # Execution context
    execution_pattern: str  # "single_entity", "multi_entity", "config_entity"
```

#### FunctionExecutedEvent
```python
class FunctionExecutedEvent(ProcessedEvent):
    """Event emitted when function execution completes."""
    function_name: str
    execution_successful: bool
    
    # Execution results
    execution_strategy: str
    output_entity_count: int
    semantic_results: List[str]  # ["creation", "mutation", "detachment"]
    
    # Performance metrics
    execution_duration_ms: float
    total_events_generated: int
    
    # Error context
    error_message: Optional[str] = None
```

### 2. Strategy Detection Events

#### StrategyDetectionEvent
```python
class StrategyDetectionEvent(ProcessingEvent):
    """Event emitted when execution strategy detection starts."""
    function_name: str
    
    # Input analysis
    input_types: Dict[str, str]  # param_name -> type_name
    entity_count: int
    config_entity_count: int
    primitive_count: int
    
    # Detection context
    has_metadata: bool
    detection_method: str  # "signature_analysis", "runtime_analysis"
```

#### StrategyDetectedEvent
```python
class StrategyDetectedEvent(ProcessedEvent):
    """Event emitted when execution strategy detection completes."""
    function_name: str
    detection_successful: bool
    
    # Strategy results
    detected_strategy: str  # "single_entity_with_config", "multi_entity_composite", etc.
    strategy_reasoning: str
    execution_path: str  # "transactional", "borrowing", "partial"
    
    # Decision factors
    decision_factors: List[str]
    confidence_level: str  # "high", "medium", "low"
```

### 3. Input Processing Events

#### InputPreparationEvent
```python
class InputPreparationEvent(ProcessingEvent):
    """Event emitted when input preparation starts."""
    function_name: str
    preparation_type: str  # "entity_creation", "borrowing", "isolation", "config_creation"
    
    # Input context
    entity_count: int
    requires_isolation: bool
    requires_config_entity: bool
    
    # Preparation metadata
    pattern_classification: Optional[str] = None
    borrowing_operations_needed: int = 0
```

#### InputPreparedEvent
```python
class InputPreparedEvent(ProcessedEvent):
    """Event emitted when input preparation completes."""
    function_name: str
    preparation_successful: bool
    
    # Preparation results
    created_entities: List[UUID]
    config_entities_created: List[UUID]
    object_identity_map_size: int
    
    # Operation metrics
    isolation_successful: bool
    borrowing_operations_completed: int
    preparation_duration_ms: Optional[float] = None
```

### 4. Semantic Analysis Events

#### SemanticAnalysisEvent
```python
class SemanticAnalysisEvent(ProcessingEvent):
    """Event emitted when semantic analysis starts."""
    function_name: str
    
    # Analysis context
    result_type: str
    analysis_method: str  # "object_identity", "ecs_id_comparison", "tree_analysis"
    
    # Analysis input
    has_object_identity_map: bool
    input_entity_count: int
    result_entity_count: int
```

#### SemanticAnalyzedEvent
```python
class SemanticAnalyzedEvent(ProcessedEvent):
    """Event emitted when semantic analysis completes."""
    function_name: str
    analysis_successful: bool
    
    # Analysis results
    semantic_type: str  # "creation", "mutation", "detachment"
    confidence_level: str  # "high", "medium", "low"
    original_entity_id: Optional[UUID] = None
    
    # Analysis metrics
    analysis_duration_ms: float
    entities_analyzed: int
```

### 5. Output Processing Events

#### UnpackingEvent
```python
class UnpackingEvent(ProcessingEvent):
    """Event emitted when result unpacking starts."""
    function_name: str
    
    # Unpacking context
    unpacking_pattern: str  # "list_return", "tuple_return", "dict_return", "single_return"
    expected_entity_count: int
    container_type: str
    
    # Unpacking metadata
    supports_unpacking: bool
    requires_container_entity: bool
```

#### UnpackedEvent
```python
class UnpackedEvent(ProcessedEvent):
    """Event emitted when result unpacking completes."""
    function_name: str
    unpacking_successful: bool
    
    # Unpacking results
    unpacked_entity_count: int
    container_entity_id: Optional[UUID] = None
    sibling_relationships_created: bool
    
    # Performance metrics
    unpacking_duration_ms: Optional[float] = None
```

#### ResultFinalizationEvent
```python
class ResultFinalizationEvent(ProcessingEvent):
    """Event emitted when result finalization starts."""
    function_name: str
    
    # Finalization context
    result_count: int
    finalization_type: str  # "single_entity", "multi_entity", "with_siblings"
    
    # Finalization metadata
    requires_sibling_setup: bool
    requires_provenance_tracking: bool
```

#### ResultFinalizedEvent
```python
class ResultFinalizedEvent(ProcessedEvent):
    """Event emitted when result finalization completes."""
    function_name: str
    finalization_successful: bool
    
    # Finalization results
    final_entity_count: int
    sibling_groups_created: int
    provenance_records_created: int
    
    # Performance metrics
    finalization_duration_ms: Optional[float] = None
```

### 6. Configuration Events

#### ConfigEntityCreationEvent
```python
class ConfigEntityCreationEvent(ProcessingEvent):
    """Event emitted when config entity creation starts."""
    function_name: str
    
    # Creation context
    config_type: str  # "explicit", "dynamic", "from_primitives"
    expected_config_class: Optional[str] = None
    
    # Creation metadata
    primitive_params_count: int
    has_expected_type: bool
```

#### ConfigEntityCreatedEvent
```python
class ConfigEntityCreatedEvent(ProcessedEvent):
    """Event emitted when config entity creation completes."""
    function_name: str
    creation_successful: bool
    
    # Creation results
    config_entity_id: UUID
    config_entity_type: str
    fields_populated: int
    
    # Registration results
    registered_in_ecs: bool
    creation_duration_ms: Optional[float] = None
```

### 7. Execution Pattern Events

#### PartialExecutionEvent
```python
class PartialExecutionEvent(ProcessingEvent):
    """Event emitted when partial execution starts."""
    function_name: str
    
    # Partial context
    partial_type: str  # "config_partial", "entity_partial", "mixed_partial"
    bound_parameters: List[str]
    
    # Execution metadata
    has_entity_params: bool
    has_config_params: bool
```

#### PartialExecutedEvent
```python
class PartialExecutedEvent(ProcessedEvent):
    """Event emitted when partial execution completes."""
    function_name: str
    execution_successful: bool
    
    # Execution results
    result_entity_count: int
    partial_function_created: bool
    
    # Performance metrics
    execution_duration_ms: float
```

#### TransactionalExecutionEvent
```python
class TransactionalExecutionEvent(ProcessingEvent):
    """Event emitted when transactional execution starts."""
    function_name: str
    
    # Transaction context
    isolated_entities_count: int
    has_object_identity_map: bool
    
    # Transaction metadata
    isolation_successful: bool
    transaction_id: UUID
```

#### TransactionalExecutedEvent
```python
class TransactionalExecutedEvent(ProcessedEvent):
    """Event emitted when transactional execution completes."""
    function_name: str
    execution_successful: bool
    
    # Transaction results
    output_entities_count: int
    semantic_analysis_completed: bool
    
    # Performance metrics
    transaction_duration_ms: float
    transaction_id: UUID
```

## Export List

```python
__all__ = [
    # Function execution events
    'FunctionExecutionEvent',
    'FunctionExecutedEvent',
    
    # Strategy detection events
    'StrategyDetectionEvent',
    'StrategyDetectedEvent',
    
    # Input processing events
    'InputPreparationEvent',
    'InputPreparedEvent',
    
    # Semantic analysis events
    'SemanticAnalysisEvent',
    'SemanticAnalyzedEvent',
    
    # Output processing events
    'UnpackingEvent',
    'UnpackedEvent',
    'ResultFinalizationEvent',
    'ResultFinalizedEvent',
    
    # Configuration events
    'ConfigEntityCreationEvent',
    'ConfigEntityCreatedEvent',
    
    # Execution pattern events
    'PartialExecutionEvent',
    'PartialExecutedEvent',
    'TransactionalExecutionEvent',
    'TransactionalExecutedEvent',
]
```

## Integration Points

### 1. Main Execution Methods
- `CallableRegistry.aexecute()` → FunctionExecutionEvent/FunctionExecutedEvent
- `CallableRegistry._execute_async()` → Various execution pattern events

### 2. Strategy and Analysis
- `CallableRegistry._detect_execution_strategy()` → StrategyDetectionEvent/StrategyDetectedEvent
- `CallableRegistry._detect_execution_semantic()` → SemanticAnalysisEvent/SemanticAnalyzedEvent

### 3. Input Processing
- `CallableRegistry._prepare_transactional_inputs()` → InputPreparationEvent/InputPreparedEvent
- `CallableRegistry._create_input_entity_with_borrowing()` → Related to input preparation

### 4. Execution Patterns
- `CallableRegistry._execute_with_partial()` → PartialExecutionEvent/PartialExecutedEvent
- `CallableRegistry._execute_transactional()` → TransactionalExecutionEvent/TransactionalExecutedEvent

### 5. Output Processing
- `CallableRegistry._finalize_multi_entity_result()` → UnpackingEvent/UnpackedEvent
- `CallableRegistry._finalize_single_entity_result()` → ResultFinalizationEvent/ResultFinalizedEvent

### 6. Configuration
- `CallableRegistry.create_config_entity_from_primitives()` → ConfigEntityCreationEvent/ConfigEntityCreatedEvent

## Event Metadata Design Principles

### 1. Function-Centric Information
- Always include function name
- Provide execution context and strategy
- Include performance metrics

### 2. Hierarchical Event Structure
- Root events for main operations
- Child events for sub-operations
- Automatic nesting via context management

### 3. Comprehensive Observability
- Cover all significant callable registry operations
- Provide debugging and monitoring information
- Track performance and resource usage

### 4. Integration with Entity Events
- Callable events will contain entity events via automatic nesting
- No duplication of entity-specific information
- Clear separation between callable and entity concerns

This specification ensures complete observability of callable registry operations while maintaining clean separation from entity-specific events.