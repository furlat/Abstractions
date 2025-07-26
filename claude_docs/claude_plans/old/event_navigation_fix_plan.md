# Event Navigation Fix Plan: Extract Entity Type from Sub-Events

## Problem Statement

The ASCII formatters in `examples/terminal_streamer/event_tracking_test.py` are displaying `[No entities]` instead of the correct entity type (e.g., `[Student|49eb130e...]`) because they only look at the `agent.tool_call.completed` event, which doesn't have `subject_type` information.

## Root Cause Analysis

1. **Event Tree Structure**: The execution creates a hierarchy of events with parent-child relationships
2. **Type Information Location**: Entity type information is stored in **sub-events** via the `subject_type` field from the base `Event` class
3. **Current Formatter Logic**: Both formatters (`_extract_output_info` and `format_from_working_tree`) only examine the completion event
4. **Missing Navigation**: No traversal of the event hierarchy to find sub-events with `subject_type`

## Events Containing Entity Type Information

Based on the callable registry and entity system analysis:

### Primary Events (High Priority)
- **EntityRegistrationEvent**: `subject_type=type(entity), subject_id=entity.ecs_id`
- **TreeBuildingEvent**: `subject_type=type(root_entity), subject_id=root_entity.ecs_id`
- **EntityVersioningEvent**: `subject_type=type(entity), subject_id=entity.ecs_id`

### Secondary Events (Medium Priority)
- **ProcessingEvent**: `subject_type=type(entity)` (from function execution)
- **ModifyingEvent**: `subject_type=type(entity)` (from entity modifications)
- **Any event with `process_name="entity_registration"`**
- **Any event with `process_name="tree_building"`**

### Event Tree Example
```
agent.tool_call.start (root) - NO subject_type
├── processing | function_execution 
│   ├── processing | transactional_execution
│   │   ├── processing | tree_building - HAS subject_type=Student ✓
│   │   ├── processing | semantic_analysis
│   │   ├── processing | entity_registration - HAS subject_type=Student ✓
│   │   └── modifying - HAS subject_type=Student ✓
│   └── processed | function_execution
└── agent.tool_call.completed - NO subject_type
```

## Solution Design

### 1. Helper Method: `_extract_entity_type_from_sub_events`

**Purpose**: Navigate event tree to find and extract actual entity type

**Signature**:
```python
def _extract_entity_type_from_sub_events(self, event_tree: Dict[str, Any]) -> str:
    """
    Navigate event tree to extract actual entity type from sub-events.
    
    Args:
        event_tree: The event tree structure from EventCollector
        
    Returns:
        str: Actual entity type name (e.g., "Student") or "Entity" as fallback
    """
```

**Algorithm**:
1. **Depth-first traversal** of event tree hierarchy
2. **Priority search** for high-value events first
3. **Extract `subject_type.__name__`** from matching events
4. **Return first match** (all events in same execution should have same type)
5. **Fallback to "Entity"** if no subject_type found

### 2. Search Strategy

**Priority Order**:
1. **Entity Lifecycle Events**: `EntityRegistrationEvent`, `TreeBuildingEvent`, `EntityVersioningEvent`
2. **Process-Specific Events**: Events with `process_name` matching entity operations
3. **General Events**: Any event with `subject_type` field
4. **Fallback**: Return "Entity"

**Search Pattern**:
```python
# High priority event types
priority_types = [
    "entity.registered", 
    "tree.built", 
    "entity.versioned"
]

# High priority process names
priority_processes = [
    "entity_registration",
    "tree_building", 
    "entity_versioning"
]

# Traverse tree looking for events with subject_type
for event in traverse_event_tree_depth_first(event_tree):
    if hasattr(event, 'subject_type') and event.subject_type:
        # Prioritize by event type and process name
        if event.type in priority_types or event.process_name in priority_processes:
            return event.subject_type.__name__
```

### 3. Integration Points

#### A. Update `ASCIIFormatter._extract_output_info`

**Current Code**:
```python
def _extract_output_info(self, event_tree: Dict[str, Any]) -> OutputInfo:
    completion_events = self._find_events_by_type(event_tree, "agent.tool_call.completed")
    # ... only looks at completion event
    entity_type = "Entity"  # ❌ Hard-coded fallback
```

**Updated Code**:
```python
def _extract_output_info(self, event_tree: Dict[str, Any]) -> OutputInfo:
    completion_events = self._find_events_by_type(event_tree, "agent.tool_call.completed")
    # ... existing completion event logic
    
    # ✅ Extract actual entity type from sub-events
    entity_type = self._extract_entity_type_from_sub_events(event_tree)
    
    # Use extracted type in entity info
    entities.append({
        'id': entity_id,
        'type': entity_type,  # ✅ Now "Student" instead of "Entity"
        'count': entity_count
    })
```

#### B. Update `format_from_working_tree` Function

**Current Code**:
```python
def format_from_working_tree(working_tree: Dict[str, Any]) -> str:
    # ... existing logic
    entity_type = getattr(agent_completed_event, 'entity_type', 'Entity')  # ❌ No entity_type field
```

**Updated Code**:
```python
def format_from_working_tree(working_tree: Dict[str, Any]) -> str:
    # ... existing logic
    
    # ✅ Extract actual entity type from sub-events
    entity_type = _extract_entity_type_from_sub_events_standalone(working_tree)
    
    # Use in output display
    lines.append(f"📤 OUTPUT: {entity_type}#{entity_id}")  # ✅ Now "Student#49eb130e..."
```

### 4. Implementation Details

#### Event Tree Traversal

```python
def _traverse_event_tree_depth_first(self, event_tree: Dict[str, Any]):
    """Generate events in depth-first order."""
    
    def traverse_node(node):
        # Yield current event
        if "event" in node:
            yield node["event"]
        
        # Recursively traverse children
        for child in node.get("children", []):
            yield from traverse_node(child)
    
    # Traverse all root nodes
    for root in event_tree.get("roots", []):
        yield from traverse_node(root)
```

#### Entity Type Extraction

```python
def _extract_entity_type_from_sub_events(self, event_tree: Dict[str, Any]) -> str:
    """Extract entity type from sub-events with priority ordering."""
    
    # Priority event types and process names
    priority_types = {"entity.registered", "tree.built", "entity.versioned"}
    priority_processes = {"entity_registration", "tree_building", "entity_versioning"}
    
    found_types = []
    
    # Collect all events with subject_type
    for event in self._traverse_event_tree_depth_first(event_tree):
        if hasattr(event, 'subject_type') and event.subject_type:
            event_type = getattr(event, 'type', '')
            process_name = getattr(event, 'process_name', '')
            
            # Calculate priority
            priority = 0
            if event_type in priority_types:
                priority += 100
            if process_name in priority_processes:
                priority += 50
            
            found_types.append((priority, event.subject_type.__name__))
    
    # Return highest priority type or fallback
    if found_types:
        found_types.sort(key=lambda x: x[0], reverse=True)
        return found_types[0][1]
    
    return "Entity"  # Fallback
```

### 5. Expected Results

**Before Fix**:
```
📤 OUTPUT: Entity#49eb130e-ef4e-4603-8401-6900881af7c5
[Student|f1aad21f-a8cd-4024-8b52-2e483cbe25c7] ---> [update_student_gpa|exec-30893413] ---> [No entities]
```

**After Fix**:
```
📤 OUTPUT: Student#49eb130e-ef4e-4603-8401-6900881af7c5
[Student|f1aad21f-a8cd-4024-8b52-2e483cbe25c7] ---> [update_student_gpa|exec-30893413] ---> [Student|49eb130e-ef4e-4603-8401-6900881af7c5]
```

### 6. Testing Strategy

1. **Run existing test**: `python examples/terminal_streamer/event_tracking_test.py`
2. **Verify output shows "Student"** in both live and post-hoc formatters
3. **Check entity flow line** shows correct output entity type
4. **Ensure no regression** in other parts of the output

### 7. Implementation Steps

1. **Add helper method** `_extract_entity_type_from_sub_events` to `ASCIIFormatter` class
2. **Add standalone function** for post-hoc formatter
3. **Update `_extract_output_info`** to use helper method
4. **Update `format_from_working_tree`** to use helper function
5. **Test and verify** output shows correct entity types

### 8. Future Enhancements

Once event navigation works:
- **Enhance event decorator** to include entity_type in AgentToolCallCompletedEvent
- **Add output_entity_types field** for multiple entity returns
- **Optimize traversal** by caching frequently accessed event data
- **Add validation** to ensure consistency between sub-events and completion event

## Files to Modify

- `examples/terminal_streamer/event_tracking_test.py` (main fix)

## Success Criteria

- ✅ ASCII output shows "Student" instead of "Entity"
- ✅ Entity flow line shows correct output entity type  
- ✅ Both live and post-hoc formatters work correctly
- ✅ No regression in other output formatting
- ✅ Solution is extensible for multiple entity types