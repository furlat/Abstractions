# ASCII Formatter Implementation Plan

## Research Summary: Event Types and Data Sources

### 1. Base Event Class Structure
From `/abstractions/events/events.py` - `Event` class (lines 96-184):

**Core Fields Available:**
- `id: UUID` - Unique event identifier
- `type: str` - Event type identifier for routing
- `phase: EventPhase` - Current lifecycle phase (PENDING, STARTED, COMPLETED, FAILED)
- `subject_type: Optional[Type[T]]` - Type of subject entity
- `subject_id: Optional[UUID]` - ID of subject entity
- `actor_type: Optional[Type[BaseModel]]` - Type of actor entity
- `actor_id: Optional[UUID]` - ID of actor entity
- `context: Dict[str, UUID]` - Additional entity references
- `timestamp: datetime` - Event creation timestamp
- `lineage_id: UUID` - Shared ID across event evolution
- `parent_id: Optional[UUID]` - Parent event ID for sub-events
- `root_id: Optional[UUID]` - Root event ID in hierarchy
- `children_ids: List[UUID]` - Child event IDs
- `metadata: Dict[str, Any]` - Arbitrary metadata
- `error: Optional[str]` - Error message if phase is FAILED
- `duration_ms: Optional[float]` - Duration in milliseconds

### 2. Agent-Specific Events (Custom)
From `/examples/terminal_streamer/event_tracking_test.py`:

**AgentToolCallStartEvent (ProcessingEvent):**
- `function_name: str` - Function being called
- `raw_parameters: Dict[str, Any]` - Raw tool parameters
- `pattern_classification: Optional[str]` - Input pattern type
- `parameter_count: int` - Number of parameters

**AgentToolCallCompletedEvent (ProcessedEvent):**
- `function_name: str` - Function that was called
- `result_type: str` - Type of result returned
- `entity_id: Optional[str]` - ID of result entity
- `entity_count: Optional[int]` - Number of entities returned
- `success: bool` - Whether execution succeeded

**AgentToolCallFailedEvent (ProcessingEvent):**
- `function_name: str` - Function that failed
- `error_type: str` - Type of error
- `failed_parameters: Dict[str, Any]` - Parameters that caused failure

### 3. Callable Registry Events
From `/abstractions/events/callable_events.py`:

**FunctionExecutionEvent (ProcessingEvent):**
- `function_name: str`
- `execution_strategy: Optional[str]`
- `input_entity_ids: List[UUID]` - Input entities
- `input_entity_types: List[str]` - Input entity types
- `input_parameter_count: int`
- `input_entity_count: int`
- `input_primitive_count: int`
- `is_async: bool`
- `uses_config_entity: bool`
- `expected_output_count: int`
- `execution_pattern: str` - Pattern type
- `execution_id: Optional[UUID]`

**FunctionExecutedEvent (ProcessedEvent):**
- `function_name: str`
- `execution_successful: bool`
- `input_entity_ids: List[UUID]`
- `output_entity_ids: List[UUID]`
- `created_entity_ids: List[UUID]`
- `modified_entity_ids: List[UUID]`
- `config_entity_ids: List[UUID]`
- `execution_record_id: Optional[UUID]`
- `execution_strategy: str`
- `output_entity_count: int`
- `semantic_results: List[str]` - ["creation", "mutation", "detachment"]
- `execution_duration_ms: float`
- `total_events_generated: int`
- `error_message: Optional[str]`
- `error_type: Optional[str]`

**Strategy/Input/Semantic/Unpacking/Result Events:**
- Similar structured data for each phase of execution
- UUID tracking for entities at each step
- Performance metrics and error handling

### 4. Entity-Specific Events
From `/abstractions/events/entity_events.py`:

**EntityRegistrationEvent/EntityRegisteredEvent:**
- `entity_type: str`
- `entity_id: UUID`
- `is_root_entity: bool`
- Tree metrics and performance data

**Entity State Transition Events:**
- Promotion, detachment, attachment events
- Complete entity lifecycle tracking
- Tree building and versioning events

### 5. Event Hierarchy Pattern (Observed)
From testing in `event_tracking_test.py`, we see this consistent hierarchy:

```
AgentToolCallStartEvent (root)
├─ FunctionExecutionEvent
│  ├─ StrategyDetectionEvent
│  │  └─ StrategyDetectedEvent
│  ├─ InputPreparationEvent
│  │  └─ InputPreparedEvent
│  ├─ SemanticAnalysisEvent
│  │  └─ SemanticAnalyzedEvent
│  ├─ [Actual Function Call - varies by function]
│  ├─ UnpackingEvent
│  │  └─ UnpackedEvent
│  ├─ ResultFinalizationEvent
│  │  └─ ResultFinalizedEvent
│  └─ FunctionExecutedEvent
└─ AgentToolCallCompletedEvent
```

## Implementation Approach

### Phase 1: Event Data Extraction Helpers

**1.1 Root Event Analysis**
```python
def extract_agent_call_info(root_event: AgentToolCallStartEvent) -> AgentCallInfo:
    """Extract function name, parameters, timing, and classification"""
    return {
        'function_name': root_event.function_name,
        'raw_parameters': root_event.raw_parameters,
        'parameter_count': root_event.parameter_count,
        'start_time': root_event.timestamp,
        'pattern_classification': root_event.pattern_classification
    }
```

**1.2 Execution Strategy Detection**
```python
def extract_strategy_info(strategy_events: List[Event]) -> StrategyInfo:
    """Extract execution strategy and reasoning from strategy detection events"""
    # Find StrategyDetectedEvent in hierarchy
    # Extract detected_strategy, strategy_reasoning, execution_path
    # Map to registry strategies: pure_borrowing, single_entity_direct, mixed, etc.
```

**1.3 Parameter Resolution**
```python
def extract_parameter_resolution(input_events: List[Event]) -> List[ParameterResolution]:
    """Extract parameter resolution from InputPreparationEvent/InputPreparedEvent"""
    # For each parameter in raw_parameters:
    #   - Determine if it's @uuid.field (borrowing) or @uuid (direct)
    #   - Extract entity type and resolved value
    #   - Format as: param_name -> "@EntityType|shortid : field = value"
```

**1.4 Function Call Extraction**
```python
def extract_function_call_info(execution_events: List[Event]) -> FunctionCallInfo:
    """Extract actual function call details"""
    # From FunctionExecutionEvent/FunctionExecutedEvent:
    #   - Execution duration
    #   - Input/output entity tracking
    #   - Success/failure status
    #   - Semantic results (creation, mutation, detachment)
```

**1.5 Output Analysis**
```python
def extract_output_info(unpacking_events: List[Event], result_events: List[Event]) -> OutputInfo:
    """Extract output entity information and unpacking details"""
    # From UnpackingEvent/UnpackedEvent and ResultFinalizationEvent:
    #   - Output entity types and IDs
    #   - Unpacking operations performed
    #   - Multi-entity output handling
    #   - Sibling entity relationships
```

**1.6 Timing Extraction**
```python
def extract_timing_info(event_hierarchy: EventTree) -> TimingBreakdown:
    """Extract complete timing breakdown from event hierarchy"""
    # From various event durations:
    #   - Resolution time (strategy + input preparation)
    #   - Execution time (actual function call)
    #   - Unpacking time (if applicable)
    #   - Total time (start to finish)
```

### Phase 2: Pattern Detection and Classification

**2.1 Agent Input Pattern Detection**
```python
def classify_agent_input_pattern(raw_parameters: Dict[str, Any]) -> str:
    """Classify the agent input pattern from raw parameters"""
    # Analyze raw_parameters to determine:
    #   - Pure field borrowing (all @uuid.field from same entity)
    #   - Multi-entity field borrowing (all @uuid.field from different entities)
    #   - Direct entity reference (single @uuid, no field)
    #   - Mixed pattern (@uuid + @uuid.field combinations)
    #   - Multiple direct entities (multiple @uuid references)
```

**2.2 Registry Strategy Mapping**
```python
def map_to_registry_strategy(detected_strategy: str, execution_path: str) -> str:
    """Map internal strategy to display strategy names"""
    # Convert callable registry internal strategies to display names:
    #   - "single_entity_direct" -> "single_entity_direct" 
    #   - "multi_entity_composite" -> "multi_entity_composite"
    #   - "pure_borrowing" -> "pure_borrowing"
    #   - etc.
```

**2.3 Semantic Detection**
```python
def determine_execution_semantic(semantic_results: List[str], input_ids: List[UUID], output_ids: List[UUID]) -> str:
    """Determine execution semantic (creation, mutation, detachment)"""
    # From semantic_results and entity ID comparison:
    #   - "creation" if new entities created
    #   - "mutation" if same entity IDs in/out
    #   - "detachment" if entities removed/separated
```

### Phase 3: ASCII Formatting

**3.1 Core ASCII Formatter**
```python
class ASCIIFormatter:
    def format_execution_pattern(self, event_tree: EventTree) -> str:
        """Generate complete ASCII pattern matching format document"""
        
        # Extract all information using helpers
        agent_info = self.extract_agent_call_info(event_tree.root)
        strategy_info = self.extract_strategy_info(event_tree.find_strategy_events())
        resolution_info = self.extract_parameter_resolution(event_tree.find_input_events())
        call_info = self.extract_function_call_info(event_tree.find_execution_events())
        output_info = self.extract_output_info(event_tree.find_unpacking_events(), event_tree.find_result_events())
        timing_info = self.extract_timing_info(event_tree)
        
        # Build formatted output
        return self.build_pattern_display(agent_info, strategy_info, resolution_info, call_info, output_info, timing_info)
```

**3.2 Pattern-Specific Formatters**
```python
def format_pure_borrowing_pattern(self, ....) -> str:
    """Format Pattern 1: Pure Field Borrowing"""
    
def format_multi_entity_borrowing_pattern(self, ....) -> str:
    """Format Pattern 2: Multi-Entity Field Borrowing"""
    
def format_direct_entity_pattern(self, ....) -> str:
    """Format Pattern 3: Direct Entity Reference"""
    
def format_mixed_pattern(self, ....) -> str:
    """Format Pattern 4: Mixed Direct Entity + Field Borrowing"""
    
def format_multiple_direct_entities_pattern(self, ....) -> str:
    """Format Pattern 5: Multiple Direct Entity References"""
    
def format_mutation_pattern(self, ....) -> str:
    """Format Pattern 6: Same Entity In, Same Entity Out (Mutation)"""
    
def format_lineage_continuation_pattern(self, ....) -> str:
    """Format Pattern 7: Same Entity In, Multiple Entities Out"""
    
def format_creation_pattern(self, ....) -> str:
    """Format Pattern 8: Same Entity Type Out But Not Lineage Continuation"""
    
def format_multi_entity_output_pattern(self, ....) -> str:
    """Format Pattern 9: Multi-Entity Output (Tuple Return)"""
```

**3.3 Component Formatters**
```python
def format_header(self, start_time: datetime, function_name: str, signature: str) -> str:
    """Format: ⏱️ START: timestamp + 🚀 function signature"""
    
def format_raw_tool_call(self, raw_parameters: Dict[str, Any]) -> str:
    """Format: 📝 RAW TOOL CALL: { parameters }"""
    
def format_resolution_steps(self, resolutions: List[ParameterResolution]) -> str:
    """Format: 🔍 RESOLVING: parameter resolution steps"""
    
def format_function_call(self, function_name: str, resolved_params: Dict[str, Any]) -> str:
    """Format: 📥 FUNCTION CALL: function(resolved_parameters)"""
    
def format_output(self, outputs: List[OutputEntity]) -> str:
    """Format: 📤 OUTPUT: entity details with tree structure"""
    
def format_entity_flow(self, inputs: List[UUID], function: str, outputs: List[UUID]) -> str:
    """Format: [Input Entities] ---> [Function] ---> [Output Entities]"""
    
def format_timing_breakdown(self, end_time: datetime, timing: TimingBreakdown) -> str:
    """Format: ⏱️ END + timing breakdown (resolution/execution/unpacking/total)"""
```

### Phase 4: Validation Against All 9 Patterns

**4.1 Pattern Coverage Matrix**
```python
PATTERN_VALIDATION_MATRIX = {
    "Pattern 1 - Pure Field Borrowing": {
        "input_pattern": "all_field_borrowing_same_entity",
        "strategy": "pure_borrowing",
        "semantic": "any",
        "formatter": "format_pure_borrowing_pattern"
    },
    "Pattern 2 - Multi-Entity Field Borrowing": {
        "input_pattern": "all_field_borrowing_different_entities", 
        "strategy": "pure_borrowing",
        "semantic": "any",
        "formatter": "format_multi_entity_borrowing_pattern"
    },
    "Pattern 3 - Direct Entity Reference": {
        "input_pattern": "single_direct_entity",
        "strategy": "single_entity_direct", 
        "semantic": "any",
        "formatter": "format_direct_entity_pattern"
    },
    "Pattern 4 - Mixed Direct + Borrowing": {
        "input_pattern": "mixed_direct_and_borrowing",
        "strategy": "mixed",
        "semantic": "any", 
        "formatter": "format_mixed_pattern"
    },
    "Pattern 5 - Multiple Direct Entities": {
        "input_pattern": "multiple_direct_entities",
        "strategy": "multi_entity_composite",
        "semantic": "any",
        "formatter": "format_multiple_direct_entities_pattern"
    },
    "Pattern 6 - Mutation (Same Entity I/O)": {
        "input_pattern": "single_direct_entity",
        "strategy": "single_entity_direct",
        "semantic": "mutation",
        "formatter": "format_mutation_pattern"
    },
    "Pattern 7 - Lineage Continuation": {
        "input_pattern": "single_direct_entity", 
        "strategy": "single_entity_direct",
        "semantic": "mutation_with_creation",
        "formatter": "format_lineage_continuation_pattern"
    },
    "Pattern 8 - Same Type Creation": {
        "input_pattern": "single_direct_entity",
        "strategy": "single_entity_direct", 
        "semantic": "creation",
        "formatter": "format_creation_pattern"
    },
    "Pattern 9 - Multi-Entity Output": {
        "input_pattern": "single_direct_entity",
        "strategy": "single_entity_direct",
        "semantic": "multiple_creation", 
        "formatter": "format_multi_entity_output_pattern"
    }
}
```

**4.2 Validation Functions**
```python
def validate_pattern_detection(event_tree: EventTree) -> bool:
    """Validate that we can correctly detect which pattern to use"""
    
def validate_data_extraction(event_tree: EventTree) -> bool:
    """Validate that all required data can be extracted from events"""
    
def validate_formatting_completeness(pattern: str, event_tree: EventTree) -> bool:
    """Validate that formatting produces complete, accurate output"""
```

## Why This Approach Works for All 9 Scenarios

### 1. **Complete Data Coverage**
The event hierarchy contains ALL information needed:
- **Agent input patterns** from `AgentToolCallStartEvent.raw_parameters`
- **Strategy detection** from `StrategyDetectedEvent.detected_strategy`
- **Parameter resolution** from `InputPreparedEvent` entity tracking
- **Function execution** from `FunctionExecutedEvent` with timing and semantics
- **Output handling** from `UnpackedEvent` and `ResultFinalizedEvent`
- **Entity relationships** from UUID tracking throughout the hierarchy

### 2. **Pattern Detection Logic**
Each pattern has unique identifying characteristics:
- **Patterns 1-2**: All parameters are `@uuid.field` (borrowing vs multi-entity)
- **Pattern 3**: Single `@uuid` parameter (direct entity)
- **Pattern 4**: Mix of `@uuid` and `@uuid.field` parameters
- **Pattern 5**: Multiple `@uuid` parameters
- **Patterns 6-9**: Distinguished by semantic analysis (`mutation` vs `creation`) and I/O entity comparison

### 3. **Registry Strategy Mapping**
The callable registry's internal strategies map directly to our display patterns:
- `pure_borrowing` → Patterns 1-2
- `single_entity_direct` → Patterns 3, 6-9 (differentiated by semantics)
- `mixed` → Pattern 4
- `multi_entity_composite` → Pattern 5

### 4. **Timing Information**
Every event has `timestamp` and `duration_ms`, allowing us to reconstruct:
- Start/end times from root events
- Resolution time from strategy + input preparation events
- Execution time from function execution events
- Unpacking time from unpacking events
- Total time from event hierarchy span

### 5. **Error Handling**
Events contain error information when things fail:
- `error` field in base events
- `error_message` and `error_type` in execution events
- Failed address resolution can be detected and formatted

### 6. **Entity Flow Tracking**
UUID tracking through the event hierarchy allows complete entity flow reconstruction:
- Input entities from `input_entity_ids`
- Output entities from `output_entity_ids`
- Created entities from `created_entity_ids`
- Modified entities from `modified_entity_ids`
- Entity types from `input_entity_types` and subject types

### 7. **Extensibility**
The helper-based approach allows easy extension:
- New event types can be added to extraction helpers
- New patterns can be added with new formatters
- The core framework remains stable

## Next Steps

1. **Implement helper functions** for data extraction from events
2. **Create pattern detection logic** using the validation matrix
3. **Build component formatters** for each display element
4. **Implement pattern-specific formatters** for all 9 scenarios
5. **Create validation suite** to test against all patterns
6. **Integration testing** with real event hierarchies

The approach is **robust** because it uses the actual event data structure, **complete** because events contain all needed information, and **scalable** because the helper-based design allows easy extension for new patterns or event types.