# HARDCODED FORMATTER PROBLEM: Complete Analysis & Solution

## CRITICAL DISCOVERY

The ASCII formatter is **COMPLETELY HARDCODED** to specific event types and process names - it's NOT generic to any function call! This explains ALL the detection failures.

## The Hardcoded Architecture Problem

### Lines 566-604: Hardcoded Event Type Prioritization
```python
def _extract_entity_type_from_sub_events(self, event_tree: Dict[str, Any]) -> str:
    # ❌ HARDCODED EVENT TYPES - Only works if function emits these!
    priority_types = {
        "entity.registered",     # Specific to certain execution paths
        "tree.built",           # Specific to certain execution paths  
        "entity.versioned"      # Specific to certain execution paths
    }
    
    # ❌ HARDCODED PROCESS NAMES - Only works if function uses these!
    priority_processes = {
        "entity_registration",   # Specific to certain strategies
        "tree_building",        # Specific to certain strategies
        "entity_versioning",    # Specific to certain strategies
        "transactional_execution"
    }
```

### Lines 799-817: Hardcoded Field Search
```python
def search_for_entity_type(events, depth=0, max_depth=4):
    """❌ HARDCODED to look for 'subject_type' field"""
    for event in events:
        if hasattr(event, 'subject_type') and event.subject_type: # HARDCODED FIELD!
            entity_type = event.subject_type.__name__
            return entity_type
```

**This is architecture-specific, not function-generic!**

## Why Each Pattern Succeeds/Fails (NOW EXPLAINED)

### ✅ Patterns That Work (Accidentally)
- **Pattern 3,5,6,8** (Direct Entity References): Work because they happen to emit events with `subject_type` fields during entity processing
- These patterns trigger the hardcoded event types the formatter expects

### ❌ Patterns That Fail Due to Hardcoding
- **Patterns 1,2** (Field Borrowing): Don't emit the hardcoded event types - use different execution strategies
- **Patterns 7,9** (Multi-Entity): Show "No entities" because sophisticated unpacking system doesn't emit the hardcoded patterns
- **Pattern 4** (Mixed): Fails due to both hardcoded search failure + address resolution issues

## The Sophisticated System vs Hardcoded Formatter Mismatch

### What the System Actually Creates (Sophisticated)
For `Tuple[Assessment, Recommendation]` returns:
```python
# 1. Registration Analysis
metadata = {
    "pattern": "tuple_return",
    "supports_unpacking": True,
    "expected_entity_count": 2,
    "element_types": [Assessment, Recommendation]
}

# 2. Runtime 3-Stage Pipeline
# Stage 1: ReturnTypeAnalyzer → ReturnPattern.TUPLE_ENTITIES (B2)
# Stage 2: EntityUnpacker → sequence_unpack strategy  
# Stage 3: TypeSafeUnpacker → individual entities with sibling relationships

# 3. Final Result
assessment.sibling_output_entities = [recommendation.ecs_id]
recommendation.sibling_output_entities = [assessment.ecs_id]
assessment.output_index = 0
recommendation.output_index = 1
assessment.derived_from_execution_id = execution_id
```

### What the Hardcoded Formatter Looks For (Broken)
```python
# ❌ Searches for hardcoded event patterns that don't exist!
if event.type == "entity.registered":  # Sophisticated unpacking doesn't emit this
    if event.process_name == "entity_registration":  # Sophisticated unpacking doesn't use this
        if hasattr(event, 'subject_type'):  # Sophisticated unpacking stores differently
```

**COMPLETE MISMATCH!** The sophisticated system creates rich entities with metadata, but the hardcoded formatter can't find them because it's looking for the wrong patterns.

## What Should Be Taken From This Analysis

### 1. ExecutionResult Contains Everything Needed
```python
# ✅ The completion event already has the data!
completion_event = find_agent_completion_event()
result = getattr(completion_event, 'result', None)

# Single entity case
if result.result_type == "single_entity":
    entity_id = result.entity_id
    entity_type = result.entity_type  # Already available!

# Multi-entity case  
elif result.result_type == "entity_list":
    entity_ids = result.debug_info.get("entity_ids", [])
    # Query EntityRegistry for sophisticated entities
    entities = [EntityRegistry.get_entity_by_id(eid) for eid in entity_ids]
    # Full metadata: sibling_output_entities, output_index, derived_from_execution_id
```

### 2. Generic Approach Works for ALL Functions
```python
# ✅ GENERIC - Works for any registered function
def extract_output_entities_generic(completion_event):
    result = getattr(completion_event, 'result', None)
    
    if result.result_type == "single_entity":
        return [{
            'id': result.entity_id,
            'type': result.entity_type,
            'count': 1
        }]
    
    elif result.result_type == "entity_list": 
        entities = []
        for entity_id in result.debug_info.get("entity_ids", []):
            entity = EntityRegistry.get_entity_by_id(entity_id)
            entities.append({
                'id': entity_id,
                'type': type(entity).__name__,
                'sibling_entities': getattr(entity, 'sibling_output_entities', []),
                'output_index': getattr(entity, 'output_index', None),
                'execution_id': getattr(entity, 'derived_from_execution_id', None)
            })
        return entities
    
    return []
```

### 3. Display Multi-Entity Results with Full Sophistication
```python
# ✅ Show sophisticated unpacking results
def display_multi_entity_results(entities):
    if len(entities) == 1:
        entity = entities[0]
        return f"{entity['type']}#{entity['id']}"
    
    else:
        # Multi-entity with relationships
        result_parts = []
        for i, entity in enumerate(entities):
            part = f"{entity['type']}#{entity['id'][:8]}"
            if entity.get('output_index') is not None:
                part += f"[{entity['output_index']}]"
            result_parts.append(part)
        
        return f"[{', '.join(result_parts)}] (siblings: {len(entities)} entities)"
```

## Implementation Plan

### Phase 1: Replace Hardcoded Search (CRITICAL)
1. **Remove all hardcoded event type lists**
2. **Remove hardcoded process name searches**  
3. **Remove hardcoded field searches (`subject_type`)**
4. **Use ExecutionResult data structure exclusively**

### Phase 2: Add Generic Entity Extraction (HIGH PRIORITY)
1. **Extract entity data from completion event's ExecutionResult**
2. **Query EntityRegistry for actual entity objects** 
3. **Extract sophisticated metadata (siblings, provenance, indices)**
4. **Handle both single and multi-entity cases generically**

### Phase 3: Enhance Display Format (MEDIUM PRIORITY)
1. **Show actual entity types instead of "Entity"**
2. **Display multi-entity results with sibling relationships**
3. **Show provenance and execution metadata**
4. **Format tuple positions and semantic classifications**

## Expected Results After Fix

### Single Entity Functions
```
📤 OUTPUT: FunctionExecutionResult#ca99910c
   ├─ entity_type: "FunctionExecutionResult"  # ✅ Actual type, not "Entity"
   ├─ result_type: "single_entity"
   ├─ success: true
```

### Multi-Entity Functions (NEW)
```
📤 OUTPUT: [Assessment#279480d4[0], Recommendation#1228dc0b[1]] (siblings: 2 entities)
   ├─ Assessment: derived_from_execution_id: abc123, sibling: 1228dc0b
   ├─ Recommendation: derived_from_execution_id: abc123, sibling: 279480d4
   ├─ result_type: "entity_list"
   ├─ success: true
```

## Conclusion

The formatter fails because it's **hardcoded to specific architecture patterns** instead of using the **generic ExecutionResult interface** that works for all functions. The sophisticated unpacking system creates rich metadata, but the hardcoded formatter can't access it because it's looking in the wrong places with the wrong assumptions.

**Fix: Replace hardcoded searches with ExecutionResult-based generic extraction.**