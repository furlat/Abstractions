# Multi-Entity Display Fix Plan

## 🔍 Problem Analysis

Based on the test output, we have a clear architectural issue with multi-entity result display:

### Current Behavior (Pattern 9 - Multi-Entity Output)
```
Result: success=True function_name='analyze_performance' result_type='entity_list' entity_id=None entity_type='Assessment' entity_count=2 error_message=None debug_info={'entity_ids': ['94c03ca0-a51e-48f2-8b3b-99fc670bdc86', 'ef0aec8b-7126-412a-be91-a0ee166d8ed1']}

🎨 ASCII FORMATTER: Detected completed agent call for analyze_performance
🎯 Entity type extracted from ExecutionResult: Assessment

[Student|fe3994a6-9abc-4d2b-b6a6-1acc4b303b47] ---> [analyze_performance|exec-42946710] ---> [No entities]
```

### ✅ What Works
- ExecutionResult has correct data: `entity_count=2`, `entity_type='Assessment'`
- Entity type extraction works: Shows "Assessment" correctly
- Debug info contains actual entity IDs: `['94c03ca0...', 'ef0aec8b...']`

### ❌ What's Broken
- Entity flow shows `[No entities]` instead of actual entities
- AgentToolCallCompletedEvent doesn't capture `debug_info`
- Formatter can't access multi-entity information

## 🎯 Root Cause

The issue is in the event creation factory:

```python
created_factory=lambda result, function_name, **kwargs: AgentToolCallCompletedEvent(
    # ... other fields ...
    entity_id=result.entity_id if hasattr(result, 'entity_id') else None,  # ❌ None for multi-entity
    entity_count=result.entity_count if hasattr(result, 'entity_count') else None,  # ✅ Works
    # ❌ MISSING: No extraction of debug_info.entity_ids
    output_ids=[]  # ❌ Should contain actual entity IDs
),
```

For multi-entity results:
- `result.entity_id = None` (single entity field doesn't apply)
- `result.debug_info = {'entity_ids': [actual_ids]}` (contains the data we need)
- But the event factory doesn't extract from `debug_info`

## 🏗️ Proposed Solution

### 1. Enhance AgentToolCallCompletedEvent

Add proper multi-entity support:

```python
class AgentToolCallCompletedEvent(ProcessedEvent):
    """Event emitted when agent tool call completes successfully."""
    type: str = "agent.tool_call.completed"
    phase: EventPhase = EventPhase.COMPLETED
    
    # Agent-specific data
    function_name: str = Field(description="Function that was called")
    result_type: str = Field(description="Type of result returned")
    entity_id: Optional[str] = Field(default=None, description="ID of result entity (single entity)")
    entity_type: Optional[str] = Field(default=None, description="Type of result entity")
    entity_count: Optional[int] = Field(default=None, description="Number of entities returned")
    entity_ids: List[str] = Field(default_factory=list, description="All entity IDs (multi-entity)")  # ✅ NEW
    success: bool = Field(default=True, description="Whether execution succeeded")
```

### 2. Fix Event Creation Factory

Extract multi-entity information properly:

```python
def create_completion_event(result, function_name, **kwargs):
    """Enhanced event creation with multi-entity support"""
    
    # Extract entity IDs for multi-entity results
    entity_ids = []
    if hasattr(result, 'debug_info') and result.debug_info:
        debug_info = result.debug_info
        if isinstance(debug_info, dict) and 'entity_ids' in debug_info:
            entity_ids = debug_info['entity_ids'] or []
    
    return AgentToolCallCompletedEvent(
        process_name="execute_function", 
        function_name=function_name,
        result_type=result.result_type if hasattr(result, 'result_type') else "unknown",
        entity_id=result.entity_id if hasattr(result, 'entity_id') else None,
        entity_type=result.entity_type if hasattr(result, 'entity_type') else None,
        entity_count=result.entity_count if hasattr(result, 'entity_count') else None,
        entity_ids=entity_ids,  # ✅ Extract from debug_info
        success=result.success if hasattr(result, 'success') else True,
        output_ids=entity_ids  # ✅ Use for compatibility
    )
```

### 3. Update Formatter Logic

Use the enhanced event data:

```python
def format_multi_entity_output(completion_event, entity_type):
    """Format multi-entity output using proper event data"""
    
    output_entities = []
    
    if completion_event.entity_id:
        # Single entity case
        output_entities.append(f"{entity_type}|{completion_event.entity_id}")
    elif completion_event.entity_ids and len(completion_event.entity_ids) > 0:
        # Multi-entity case - use the actual entity IDs
        first_id = completion_event.entity_ids[0]
        if len(completion_event.entity_ids) > 1:
            output_entities.append(f"{entity_type}|{first_id}, +{len(completion_event.entity_ids)-1} more")
        else:
            output_entities.append(f"{entity_type}|{first_id}")
    elif completion_event.entity_count and completion_event.entity_count > 1:
        # Fallback case
        output_entities.append(f"{completion_event.entity_count} {entity_type} entities")
    
    return output_entities or ["No entities"]
```

## 📋 Implementation Steps

### Step 1: Enhance Event Structure
1. Add `entity_ids` field to `AgentToolCallCompletedEvent`
2. Update event creation factory to extract from `debug_info`
3. Test single entity cases still work

### Step 2: Update Formatter
1. Modify output entity logic to use `entity_ids` 
2. Handle both single and multi-entity cases
3. Test all 9 patterns

### Step 3: Clean Up Duplicates
1. Fix duplicate entity issue in input flow
2. Improve entity deduplication logic
3. Test entity flow display

## 🎯 Expected Results

After implementing this fix:

### Pattern 9 Multi-Entity (Fixed)
```
🎯 Entity type extracted from ExecutionResult: Assessment

📤 OUTPUT: 2 entities (first: Assessment#94c03ca0-7423-4086-ada7-281bf9aa7580)
   ├─ entity_count: 2
   ├─ result_type: "entity_list"
   ├─ success: true

[Student|fe3994a6-9abc-4d2b-b6a6-1acc4b303b47] ---> [analyze_performance|exec-42946710] ---> [Assessment|94c03ca0-7423-4086-ada7-281bf9aa7580, +1 more]
```

### Pattern 7 Multi-Entity (When Fixed)
```
[Student|e5c54fd8-a5ec-49a7-8121-63c8cd691aa3] ---> [split_student_record|exec-34384371] ---> [Student|e5c54fd8-a5ec-49a7-8121-63c8cd691aa3, AcademicRecord|rec-b3c4-d5e6-7890-123456789012]
```

## 🚀 Benefits

1. **Clean Architecture**: Event contains all necessary data
2. **No Hacky Workarounds**: No need to dig into debug_info in formatter
3. **Type Safety**: Proper structured data instead of generic debugging info
4. **Extensible**: Easy to add more multi-entity metadata later
5. **Consistent**: Same pattern works for all multi-entity scenarios

This approach fixes the root cause rather than patching symptoms, making the system more robust and maintainable.