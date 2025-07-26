# Event Emissions Research Plan - Terminal Streamer Implementation

## Research Objective
Study existing event emissions in the Abstractions framework to identify data sources for implementing ASCII terminal visualization of LLM agent interactions with entities and function executions.

## Key Files Analysis Summary

Based on initial file review, here's what we found:

### 1. entity.py - Rich Entity Lifecycle Events ✅
**Event Coverage**: Extensive @emit_events decorators throughout entity operations

**Key Event Types Identified**:
- `EntityRegistrationEvent` - When entities are registered in the registry
- `EntityVersioningEvent` - When entity versions are created/updated  
- `EntityPromotionEvent` - When entities are promoted to root status
- `EntityAttachmentEvent` - When entities are attached to parents
- `EntityDetachmentEvent` - When entities are detached from parents
- `EntityBorrowingEvent` - When entity attributes are borrowed via @uuid.field

**Critical Operations with Events**:
- `promote_to_root()` - Entity becomes independent root
- `detach()` - Entity removed from parent hierarchy
- `attach()` - Entity added to parent hierarchy  
- `borrow_attribute_from()` - Field-level entity borrowing
- Registry operations (registration, versioning, retrieval)

### 2. callable_registry.py - Function Execution Events ✅
**Event Coverage**: Comprehensive @emit_events decorators for function execution lifecycle

**Key Event Types Identified**:
- `FunctionExecutionEvent` - Core function execution tracking
- `StrategyDetectionEvent` - When execution strategy is determined (borrowing/direct/mixed)
- `TransactionalExecutionEvent` - For transactional entity operations
- `EntityUnpackingEvent` - When function results are unpacked into entities
- `SemanticDetectionEvent` - When semantic patterns are detected (creation/mutation/detachment)

**Critical Execution Phases**:
- Strategy detection (pure_borrowing, single_entity_direct, mixed, etc.)
- Address resolution (@uuid.field → actual values)
- Function execution with timing
- Result unpacking and entity creation
- Semantic analysis (mutation vs creation patterns)

### 3. registry_agent.py - Limited Agent Tool Events ❌
**Event Coverage**: Minimal - only in execute_function tool (lines 598-672)

**Current Gap**: The execute_function tool has comprehensive error handling and debugging but **no event emissions**

**Missing Agent Events**:
- Agent tool call initiation
- Parameter validation and address resolution  
- Tool call success/failure
- Result processing and formatting

## BREAKTHROUGH: Event Hierarchy Solution 

### Key Discovery: @emit_events Decorator Magic ✨

The events.py system provides **automatic parent-child event linking** through the `@emit_events` decorator (lines 941-1229). This is exactly what we need!

**The Solution**: Wrap `registry_agent.py` `execute_function` with `@emit_events` to create a complete event hierarchy:

```python
@emit_events(
    creating_factory=lambda function_name, **kwargs: AgentToolCallStartEvent(...),
    created_factory=lambda result, function_name, **kwargs: AgentToolCallCompletedEvent(...),
    failed_factory=lambda error, function_name, **kwargs: AgentToolCallFailedEvent(...)
)
async def execute_function(function_name: str, **kwargs) -> ExecutionResult:
    # All subsequent events become children automatically
    result = await CallableRegistry.aexecute(function_name, **kwargs)
    return result
```

**Automatic Event Hierarchy**:
```
AgentToolCallStartEvent (ROOT)
├── FunctionExecutionEvent (child - from callable_registry.py)
│   ├── StrategyDetectionEvent (grandchild)
│   ├── AddressResolutionEvent (grandchild)  
│   ├── EntityBorrowingEvent (grandchild)
│   └── SemanticDetectionEvent (grandchild)
├── EntityRegistrationEvent (child - from entity.py)
├── EntityVersioningEvent (child - from entity.py)
└── AgentToolCallCompletedEvent (child - completion)
```

### How @emit_events Works:
1. **Context Management** (lines 1048, 1155): Pushes agent event to context stack
2. **Automatic Parent Linking** (lines 1027-1037): All nested events become children
3. **Timing Capture** (lines 1078-1080): Automatic duration measurement  
4. **Error Handling** (lines 1086-1110): Failed events with proper linking
5. **Cleanup** (lines 1113-1115): Proper context stack management

## Simplified Implementation Plan

### Phase 1: Agent Event Wrapper 
1. **Create Custom Agent Events**
   - `AgentToolCallStartEvent`: Captures raw tool parameters, pattern classification
   - `AgentToolCallCompletedEvent`: Captures results and timing
   - `AgentToolCallFailedEvent`: Captures errors and debug info

2. **Wrap execute_function Tool**
   - Add `@emit_events` decorator to registry_agent.py execute_function
   - Create event factories that capture all agent-specific data
   - Test that all existing events become children automatically

### Phase 2: ASCII Visualization
1. **Event Collection**
   - Use `@on(AgentToolCallStartEvent)` to capture root agent calls
   - Collect complete event hierarchy using parent_id relationships
   - Map event data to ASCII visualization format

2. **Real-time Rendering**
   - Stream events as they occur using the event bus
   - Build ASCII representations matching the 9 patterns from format.md
   - Display timing breakdown and entity relationships

### Phase 3: Integration Testing
1. **Verify Event Hierarchy**
   - Test all 9 agent patterns create proper event trees
   - Validate timing data flows through the hierarchy
   - Ensure no events are missed or duplicated

## Major Advantages

### ✅ **Zero Code Changes to Core System**
- No modifications to entity.py or callable_registry.py
- All existing events automatically become children
- Leverages existing rich event data

### ✅ **Complete Data Coverage**  
- Agent context (tool parameters, pattern classification)
- Function execution (strategies, timing, semantics)
- Entity operations (registration, versioning, borrowing)
- Error handling (address resolution failures, execution errors)

### ✅ **Perfect Timing Correlation**
- Root agent event provides overall timing
- Child events provide detailed breakdowns
- Automatic timing inheritance through hierarchy

### ✅ **Natural Event Relationships**
- Parent-child links match actual call stack
- Events flow in execution order
- Easy to traverse and visualize

## Implementation Requirements

**No complex analysis needed** - the event system handles everything automatically:
- ✅ Event taxonomy: Already complete with existing events
- ✅ Parent-child relationships: Automatic via @emit_events  
- ✅ Timing correlation: Built into the decorator
- ✅ Data completeness: All information flows through the hierarchy

## Next Steps

### Immediate: Create Agent Event Types
1. Define `AgentToolCallStartEvent`, `AgentToolCallCompletedEvent`, `AgentToolCallFailedEvent`
2. Add `@emit_events` decorator to `registry_agent.py` execute_function  
3. Test that existing events become children automatically

### Short-term: Build ASCII Renderer
1. Create `@on` handlers for root agent events
2. Build event tree traversal and ASCII formatting
3. Test with all 9 agent execution patterns

### Medium-term: Real-time Terminal Interface  
1. Stream ASCII visualizations as events occur
2. Add interactive features (filtering, replay)
3. Integration testing with actual agent workflows

---

**Key Insight**: The `@emit_events` decorator gives us the complete event hierarchy for free. We just need to wrap the agent tool call and everything else flows automatically through the existing rich event system. This is much simpler than the original research plan and provides exactly what we need for comprehensive ASCII visualization.