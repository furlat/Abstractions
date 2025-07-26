# Registry Agent Events Implementation Plan

## Overview

This document provides a complete implementation plan for adding missing event definitions and factories to all registry agent tools in `abstractions/registry_agent.py`.

## Current Status Analysis

### Tools with Complete Event Implementation
- ✅ `execute_function` - Has events + `@emit_events` decorator

### Tools with Partial Implementation  
- ⚠️ `list_functions` - Has event definitions but missing `@emit_events` decorator

### Tools Missing All Events
- ❌ `get_function_signature` - Missing events and decorator
- ❌ `get_all_lineages` - Missing events and decorator  
- ❌ `get_lineage_history` - Missing events and decorator
- ❌ `get_entity` - Missing events and decorator

## Implementation Plan

### Phase 1: Add Missing Event Definitions

**Location**: After line 650 (after existing event definitions)

#### 1.1 get_function_signature Events

```python
class AgentGetFunctionSignatureEvent(ProcessingEvent):
    """Event emitted when agent gets function signature."""
    type: str = "agent.get_function_signature.start"
    phase: EventPhase = EventPhase.STARTED
    
    function_name: str = Field(description="Function name being queried")


class AgentGetFunctionSignatureCompletedEvent(ProcessedEvent):
    """Event emitted when agent successfully gets function signature."""
    type: str = "agent.get_function_signature.completed"
    phase: EventPhase = EventPhase.COMPLETED
    
    function_name: str = Field(description="Function name queried")
    signature_found: bool = Field(description="Whether function signature was found")


class AgentGetFunctionSignatureFailedEvent(ProcessingEvent):
    """Event emitted when agent fails to get function signature."""
    type: str = "agent.get_function_signature.failed"
    phase: EventPhase = EventPhase.FAILED
    
    function_name: str = Field(description="Function name that failed")
    error_type: str = Field(description="Type of error")
```

#### 1.2 get_all_lineages Events

```python
class AgentGetAllLineagesEvent(ProcessingEvent):
    """Event emitted when agent gets all lineages."""
    type: str = "agent.get_all_lineages.start"
    phase: EventPhase = EventPhase.STARTED


class AgentGetAllLineagesCompletedEvent(ProcessedEvent):
    """Event emitted when agent successfully gets all lineages."""
    type: str = "agent.get_all_lineages.completed"
    phase: EventPhase = EventPhase.COMPLETED
    
    total_lineages: int = Field(description="Total number of lineages found")


class AgentGetAllLineagesFailedEvent(ProcessingEvent):
    """Event emitted when agent fails to get all lineages."""
    type: str = "agent.get_all_lineages.failed"
    phase: EventPhase = EventPhase.FAILED
    
    error_type: str = Field(description="Type of error")
```

#### 1.3 get_lineage_history Events

```python
class AgentGetLineageHistoryEvent(ProcessingEvent):
    """Event emitted when agent gets lineage history."""
    type: str = "agent.get_lineage_history.start"
    phase: EventPhase = EventPhase.STARTED
    
    lineage_id: str = Field(description="Lineage ID being queried")


class AgentGetLineageHistoryCompletedEvent(ProcessedEvent):
    """Event emitted when agent successfully gets lineage history."""
    type: str = "agent.get_lineage_history.completed"
    phase: EventPhase = EventPhase.COMPLETED
    
    lineage_id: str = Field(description="Lineage ID queried")
    history_found: bool = Field(description="Whether lineage history was found")
    total_versions: Optional[int] = Field(default=None, description="Number of versions in lineage")


class AgentGetLineageHistoryFailedEvent(ProcessingEvent):
    """Event emitted when agent fails to get lineage history."""
    type: str = "agent.get_lineage_history.failed"
    phase: EventPhase = EventPhase.FAILED
    
    lineage_id: str = Field(description="Lineage ID that failed")
    error_type: str = Field(description="Type of error")
```

#### 1.4 get_entity Events

```python
class AgentGetEntityEvent(ProcessingEvent):
    """Event emitted when agent gets entity."""
    type: str = "agent.get_entity.start"
    phase: EventPhase = EventPhase.STARTED
    
    root_ecs_id: str = Field(description="Root entity ID")
    ecs_id: str = Field(description="Entity ID being queried")


class AgentGetEntityCompletedEvent(ProcessedEvent):
    """Event emitted when agent successfully gets entity."""
    type: str = "agent.get_entity.completed"
    phase: EventPhase = EventPhase.COMPLETED
    
    root_ecs_id: str = Field(description="Root entity ID")
    ecs_id: str = Field(description="Entity ID queried")
    entity_found: bool = Field(description="Whether entity was found")
    entity_type: Optional[str] = Field(default=None, description="Type of entity found")


class AgentGetEntityFailedEvent(ProcessingEvent):
    """Event emitted when agent fails to get entity."""
    type: str = "agent.get_entity.failed"
    phase: EventPhase = EventPhase.FAILED
    
    root_ecs_id: str = Field(description="Root entity ID that failed")
    ecs_id: str = Field(description="Entity ID that failed")
    error_type: str = Field(description="Type of error")
```

### Phase 2: Apply @emit_events Decorators

#### 2.1 list_functions (Line 762)

**Current:**
```python
@registry_toolset.tool
def list_functions() -> FunctionList:
```

**Updated:**
```python
@registry_toolset.tool
@emit_events(
    creating_factory=lambda: AgentListFunctionsEvent(
        process_name="list_functions"
    ),
    created_factory=lambda result: AgentListFunctionsCompletedEvent(
        process_name="list_functions",
        total_functions=result.total_functions,
        function_list=result
    ),
    failed_factory=lambda error: AgentListFunctionsEvent(
        process_name="list_functions",
        phase=EventPhase.FAILED,
        error_type=type(error).__name__,
        error=str(error)
    )
)
def list_functions() -> FunctionList:
```

#### 2.2 get_function_signature (Line 787)

**Current:**
```python
@registry_toolset.tool
def get_function_signature(function_name: str) -> Union[FunctionInfo, ToolError]:
```

**Updated:**
```python
@registry_toolset.tool
@emit_events(
    creating_factory=lambda function_name: AgentGetFunctionSignatureEvent(
        process_name="get_function_signature",
        function_name=function_name
    ),
    created_factory=lambda result, function_name: AgentGetFunctionSignatureCompletedEvent(
        process_name="get_function_signature",
        function_name=function_name,
        signature_found=not isinstance(result, ToolError)
    ),
    failed_factory=lambda error, function_name: AgentGetFunctionSignatureFailedEvent(
        process_name="get_function_signature",
        function_name=function_name,
        error_type=type(error).__name__,
        error=str(error)
    )
)
def get_function_signature(function_name: str) -> Union[FunctionInfo, ToolError]:
```

#### 2.3 get_all_lineages (Line 812)

**Current:**
```python
@registry_toolset.tool
def get_all_lineages() -> LineageList:
```

**Updated:**
```python
@registry_toolset.tool
@emit_events(
    creating_factory=lambda: AgentGetAllLineagesEvent(
        process_name="get_all_lineages"
    ),
    created_factory=lambda result: AgentGetAllLineagesCompletedEvent(
        process_name="get_all_lineages",
        total_lineages=result.total_lineages
    ),
    failed_factory=lambda error: AgentGetAllLineagesFailedEvent(
        process_name="get_all_lineages",
        error_type=type(error).__name__,
        error=str(error)
    )
)
def get_all_lineages() -> LineageList:
```

#### 2.4 get_lineage_history (Line 838)

**Current:**
```python
@registry_toolset.tool
def get_lineage_history(lineage_id: str) -> Union[LineageInfo, ToolError]:
```

**Updated:**
```python
@registry_toolset.tool
@emit_events(
    creating_factory=lambda lineage_id: AgentGetLineageHistoryEvent(
        process_name="get_lineage_history",
        lineage_id=lineage_id
    ),
    created_factory=lambda result, lineage_id: AgentGetLineageHistoryCompletedEvent(
        process_name="get_lineage_history",
        lineage_id=lineage_id,
        history_found=not isinstance(result, ToolError),
        total_versions=result.total_versions if isinstance(result, LineageInfo) else None
    ),
    failed_factory=lambda error, lineage_id: AgentGetLineageHistoryFailedEvent(
        process_name="get_lineage_history",
        lineage_id=lineage_id,
        error_type=type(error).__name__,
        error=str(error)
    )
)
def get_lineage_history(lineage_id: str) -> Union[LineageInfo, ToolError]:
```

#### 2.5 get_entity (Line 895)

**Current:**
```python
@registry_toolset.tool
def get_entity(root_ecs_id: str, ecs_id: str) -> Union[EntityInfo, ToolError]:
```

**Updated:**
```python
@registry_toolset.tool
@emit_events(
    creating_factory=lambda root_ecs_id, ecs_id: AgentGetEntityEvent(
        process_name="get_entity",
        root_ecs_id=root_ecs_id,
        ecs_id=ecs_id
    ),
    created_factory=lambda result, root_ecs_id, ecs_id: AgentGetEntityCompletedEvent(
        process_name="get_entity",
        root_ecs_id=root_ecs_id,
        ecs_id=ecs_id,
        entity_found=not isinstance(result, ToolError),
        entity_type=result.entity_type if isinstance(result, EntityInfo) else None
    ),
    failed_factory=lambda error, root_ecs_id, ecs_id: AgentGetEntityFailedEvent(
        process_name="get_entity",
        root_ecs_id=root_ecs_id,
        ecs_id=ecs_id,
        error_type=type(error).__name__,
        error=str(error)
    )
)
def get_entity(root_ecs_id: str, ecs_id: str) -> Union[EntityInfo, ToolError]:
```

### Phase 3: Fix Missing Failed Event for list_functions

The existing `AgentListFunctionsEvent` needs a corresponding failed event. We need to add:

```python
class AgentListFunctionsFailedEvent(ProcessingEvent):
    """Event emitted when agent fails to list functions."""
    type: str = "agent.list_functions.failed"
    phase: EventPhase = EventPhase.FAILED
    
    error_type: str = Field(description="Type of error")
```

## Event Field Validation

### Compliance with Event Rules

All new events follow these rules:
- ✅ Only UUID references as strings (no UUID objects)
- ✅ Only primitive metadata (str, int, bool, Optional types) 
- ✅ No entity objects or complex nested structures
- ✅ Consistent field naming across similar events
- ✅ Proper inheritance from base event types

### Field Analysis

**Start Events:**
- `function_name: str` - primitive string ✅
- `lineage_id: str` - UUID as string ✅
- `root_ecs_id: str` - UUID as string ✅
- `ecs_id: str` - UUID as string ✅

**Completed Events:**
- `signature_found: bool` - primitive boolean ✅
- `total_lineages: int` - primitive integer ✅
- `history_found: bool` - primitive boolean ✅
- `total_versions: Optional[int]` - optional primitive ✅
- `entity_found: bool` - primitive boolean ✅
- `entity_type: Optional[str]` - optional string ✅

**Failed Events:**
- `error_type: str` - primitive string ✅

## Implementation Order

1. **Add missing event definitions** (after line 650)
2. **Add missing failed event for list_functions** 
3. **Apply @emit_events decorators** to all tools in order:
   - list_functions
   - get_function_signature  
   - get_all_lineages
   - get_lineage_history
   - get_entity

## File Locations

- **Target file**: `abstractions/registry_agent.py`
- **Event definitions insertion point**: After line 650 
- **Decorator applications**: At each tool function definition

## Testing Validation

After implementation:
1. Verify all events serialize to JSON without errors
2. Confirm no entity objects are stored in event fields
3. Test that all factory functions execute without errors
4. Validate event hierarchy inheritance is correct
5. Check that all tools emit appropriate events during execution

## Summary

- **12 new event classes** to be added
- **4 @emit_events decorators** to be applied (plus fix for list_functions)
- **All events follow UUID-as-string rule**
- **Consistent naming and inheritance patterns**
- **Complete event coverage for all registry agent tools**