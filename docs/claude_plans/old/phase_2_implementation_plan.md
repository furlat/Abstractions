# Phase 2 Implementation Plan: Output Analysis & Unpacking

## Overview

With Phase 1 complete (Enhanced Input Pattern Support), Phase 2 focuses on implementing sophisticated output analysis and unpacking capabilities for the callable registry system. This phase enables the registry to handle complex function return patterns and maintain complete audit trails for all entity transformations.

## Core Goals

1. **Return Type Analysis**: Detect and classify different output patterns from function execution
2. **Multi-Entity Unpacking**: Handle functions that return tuples, lists, or dicts containing multiple entities
3. **Sibling Relationship Tracking**: Track entities created together from the same function execution
4. **Complete Execution Audit**: Expand FunctionExecution entity to capture all execution metadata

## Implementation Tasks

### Task 2.1: Return Type Analyzer (Priority: High)

**Objective**: Create a sophisticated analyzer to classify function return types and determine unpacking strategies.

**Implementation Details**:
```python
class ReturnTypeAnalyzer:
    @classmethod
    def analyze_return(cls, result: Any) -> Dict[str, Any]:
        """Analyze function return and determine unpacking strategy"""
        return {
            "return_pattern": str,  # "single_entity", "multi_entity", "mixed_container", etc.
            "entity_count": int,
            "unpacking_strategy": str,  # "none", "tuple", "dict_values", etc.
            "entities": List[Entity],
            "non_entity_data": Dict[str, Any]
        }
    
    @classmethod
    def classify_return_pattern(cls, result: Any) -> str:
        """Classify the return pattern (B1-B7 from design)"""
        # B1: Single Entity
        # B2: Tuple of Entities  
        # B3: List of Entities
        # B4: Dict of Entities
        # B5: Mixed containers (entities + values)
        # B6: Nested structures
        # B7: Non-entity returns (wrapped in ResultEntity)
```

**Files to Create/Modify**:
- Create: `abstractions/ecs/return_type_analyzer.py`
- Modify: `abstractions/ecs/functional_api.py` (add return analysis integration)

### Task 2.2: Multi-Entity Unpacking System (Priority: High)

**Objective**: Implement unpacking logic for functions that return multiple entities.

**Implementation Details**:
```python
class EntityUnpacker:
    @classmethod
    def unpack_return(cls, result: Any, analysis: Dict[str, Any]) -> Tuple[List[Entity], Dict[str, Any]]:
        """Unpack function return into separate entities and metadata"""
        
    @classmethod
    def handle_tuple_return(cls, result: Tuple) -> List[Entity]:
        """Handle tuple unpacking with sibling relationship tracking"""
        
    @classmethod
    def handle_container_return(cls, result: Union[List, Dict]) -> Tuple[List[Entity], Dict]:
        """Handle list/dict returns with mixed content"""
```

**Key Features**:
- Automatic detection of entity containers (tuples, lists, dicts)
- Preservation of container structure metadata
- Sibling relationship establishment between entities from same return
- Handling of mixed containers (entities + primitive values)

### Task 2.3: Sibling Relationship Tracking (Priority: Medium)

**Objective**: Track entities that were created together from the same function execution.

**Implementation Details**:
```python
# Add to Entity class:
class Entity(BaseModel):
    # ... existing fields ...
    sibling_execution_id: Optional[UUID] = None  # Links to FunctionExecution
    sibling_entities: List[UUID] = Field(default_factory=list)  # Other entities from same execution
    return_position: Optional[Union[int, str]] = None  # Position in return structure (tuple index, dict key, etc.)
```

**Features**:
- Link entities created in the same function execution
- Track position within return structure (tuple index, dict key, list index)
- Enable querying of entity siblings
- Support for complex nested return structures

### Task 2.4: Enhanced FunctionExecution Entity (Priority: Medium)

**Objective**: Expand the FunctionExecution entity to capture complete execution metadata.

**Implementation Details**:
```python
class FunctionExecution(Entity):
    # Existing fields
    function_name: str
    input_entity_id: UUID
    output_entity_ids: List[UUID]  # Support multiple outputs
    execution_timestamp: datetime
    
    # New fields for Phase 2
    return_analysis: Dict[str, Any]  # Full return type analysis
    unpacking_metadata: Dict[str, Any]  # How the return was unpacked
    sibling_groups: List[List[UUID]]  # Groups of entities created together
    performance_metrics: Dict[str, Any]  # Execution time, memory usage, etc.
    input_pattern_classification: Dict[str, Any]  # From Phase 1
    semantic_classification: str  # MUTATION, CREATION, DETACHMENT
    
    # Audit trail expansion
    pre_execution_snapshots: Dict[UUID, Dict[str, Any]]  # Entity states before execution
    post_execution_changes: Dict[UUID, Dict[str, Any]]   # What changed after execution
```

### Task 2.5: Output Pattern Integration (Priority: High)

**Objective**: Integrate output analysis with the callable registry system.

**Implementation Details**:
- Modify the main execution flow to use return analysis
- Update entity registration to handle multiple outputs
- Ensure proper versioning for all output entities
- Integrate with existing object identity detection

**Key Integration Points**:
```python
def execute_with_full_analysis(func_name: str, **kwargs) -> ExecutionResult:
    """Enhanced execution with complete input/output analysis"""
    # Phase 1: Input analysis (already implemented)
    input_analysis = InputPatternClassifier.classify_kwargs_advanced(kwargs)
    
    # Create composite input entity
    composite_input = create_composite_entity_with_pattern_detection_advanced(...)
    
    # Execute function
    result = execute_function(func_name, composite_input)
    
    # Phase 2: Output analysis (new)
    return_analysis = ReturnTypeAnalyzer.analyze_return(result)
    entities, metadata = EntityUnpacker.unpack_return(result, return_analysis)
    
    # Create comprehensive execution record
    execution = FunctionExecution(
        input_pattern_classification=input_analysis,
        return_analysis=return_analysis,
        unpacking_metadata=metadata,
        # ... other fields
    )
    
    return ExecutionResult(entities=entities, execution=execution)
```

## Testing Strategy

### Test Coverage Areas
1. **Return Pattern Detection**: Test all 7 output patterns (B1-B7)
2. **Unpacking Logic**: Validate correct entity extraction from complex returns
3. **Sibling Tracking**: Ensure proper relationship establishment
4. **Integration Testing**: Full end-to-end execution with input/output analysis
5. **Performance Testing**: Validate performance with large entity structures

### Test Files to Create
- `tests/test_return_type_analyzer.py`
- `tests/test_entity_unpacker.py`
- `tests/test_sibling_tracking.py`  
- `tests/test_phase2_integration.py`

## Implementation Order

1. **Week 1**: Return Type Analyzer (Task 2.1)
2. **Week 1**: Multi-Entity Unpacking System (Task 2.2)
3. **Week 2**: Enhanced FunctionExecution Entity (Task 2.4)
4. **Week 2**: Output Pattern Integration (Task 2.5)
5. **Week 3**: Sibling Relationship Tracking (Task 2.3)
6. **Week 3**: Comprehensive testing and optimization

## Success Criteria

Phase 2 will be considered complete when:

1. ✅ All 7 output patterns (B1-B7) are correctly detected and classified
2. ✅ Multi-entity returns are properly unpacked with sibling tracking
3. ✅ FunctionExecution entities capture complete execution metadata
4. ✅ Integration with Phase 1 input analysis provides end-to-end execution tracking
5. ✅ Comprehensive test suite validates all functionality
6. ✅ Performance benchmarks meet acceptable thresholds

## Future Phases

**Phase 3**: Advanced Registry Operations
- Complex query capabilities
- Performance optimization for large-scale operations
- Registry persistence and recovery

**Phase 4**: Production Integration
- API design for external consumption
- Error handling and validation
- Documentation and examples