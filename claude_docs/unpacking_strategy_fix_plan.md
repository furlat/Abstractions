# Unpacking Strategy Fix Plan

## Problem Statement

The current unpacking strategy logic is incorrect and creates atomic data unpacking issues:

**Current Wrong Behavior:**
- `List[Entity]` → `sequence_unpack` ❌ (unpacks to atomic list elements)
- `Dict[str, Entity]` → `dict_unpack` ❌ (unpacks to atomic dict values)
- `List[Tuple[Entity, Entity]]` → `nested_unpack` ❌ (unpacks to atomic nested data)

**Result:** The system tries to unpack containers and creates non-addressable atomic elements instead of maintaining container structures as addressable entities.

## Root Cause Analysis

### 1. **Wrong Default in `_determine_unpacking_strategy()`**
Location: `/abstractions/ecs/return_type_analyzer.py:286-307`

Current logic defaults to unpacking for:
- `LIST_ENTITIES` → `sequence_unpack`
- `DICT_ENTITIES` → `dict_unpack` 
- `NESTED_STRUCTURE` → `nested_unpack`

### 2. **Missing Force Unpacking Option**
The system has no way to explicitly request unpacking when needed.

### 3. **Conflated Concepts**
The system treats "contains entities" as "should unpack", when it should be "only unpack if each element becomes individually addressable".

## Correct Design Principles

### Core Rule: **Only Unpack to Pure Entities**
- **Unpack:** When each unpacked element is a pure entity addressable via `@uuid`
- **Wrap:** When the result is a container structure that should be addressable as a single entity

### Default Behavior (Conservative)
- `Tuple[Entity, Entity]` → unpack to `[entity1, entity2]` ✅ (only safe case)
- `List[Entity]` → wrap in `ContainerEntity(entities_list)` ✅ (container structure)
- `Dict[str, Entity]` → wrap in `ContainerEntity(entities_dict)` ✅ (container structure)
- `List[Tuple[Entity, Entity]]` → wrap in `ContainerEntity(list_of_tuples)` ✅ (nested container)

### Force Unpacking (Explicit Opt-in)
- `List[Entity]` → unpack to `[entity1, entity2, ...]` if `force_unpack=True`
- `Dict[str, Entity]` → unpack to `[entity1, entity2, ...]` if `force_unpack=True`

## Implementation Plan

### Phase 1: Fix Default Unpacking Strategy

#### 1.1 Update `_determine_unpacking_strategy()` 
**File:** `/abstractions/ecs/return_type_analyzer.py:286-307`

**Current:**
```python
def _determine_unpacking_strategy(cls, pattern: ReturnPattern, entity_count: int, original_result: Any = None) -> str:
    if pattern == ReturnPattern.SINGLE_ENTITY:
        return "none"
    elif pattern in [ReturnPattern.TUPLE_ENTITIES, ReturnPattern.LIST_ENTITIES]:  # ❌ Wrong
        return "sequence_unpack"
    elif pattern == ReturnPattern.DICT_ENTITIES:  # ❌ Wrong
        return "dict_unpack"
    elif pattern == ReturnPattern.NESTED_STRUCTURE:  # ❌ Wrong
        return "nested_unpack"
    # ... rest
```

**Fixed:**
```python
def _determine_unpacking_strategy(cls, pattern: ReturnPattern, entity_count: int, original_result: Any = None, force_unpack: bool = False) -> str:
    if pattern == ReturnPattern.SINGLE_ENTITY:
        return "none"
    elif pattern == ReturnPattern.TUPLE_ENTITIES:
        # Only tuple of pure entities gets unpacked by default
        return "sequence_unpack"
    elif force_unpack and pattern in [ReturnPattern.LIST_ENTITIES, ReturnPattern.DICT_ENTITIES, ReturnPattern.NESTED_STRUCTURE]:
        # Explicit force unpacking
        if pattern == ReturnPattern.LIST_ENTITIES:
            return "sequence_unpack"
        elif pattern == ReturnPattern.DICT_ENTITIES:
            return "dict_unpack"
        elif pattern == ReturnPattern.NESTED_STRUCTURE:
            return "nested_unpack"
    else:
        # Default: wrap everything else in container entities
        return "wrap_in_entity"
```

#### 1.2 Update `analyze_return()` method
**File:** `/abstractions/ecs/return_type_analyzer.py:60-90`

Add `force_unpack` parameter:
```python
def analyze_return(cls, result: Any, force_unpack: bool = False) -> ReturnAnalysis:
    # ... existing logic
    unpacking_strategy = cls._determine_unpacking_strategy(pattern, len(entities), result, force_unpack)
    # ... rest
```

### Phase 2: Add Force Unpacking Support

#### 2.1 Update Function Registration
**File:** `/abstractions/ecs/callable_registry.py:366-413`

Add `force_unpack` parameter to `register()`:
```python
def register(cls, name: str, force_unpack: bool = False) -> Callable:
    def decorator(func: Callable) -> Callable:
        # ... existing validation
        
        # Pass force_unpack to output model creation
        output_entity_class, output_pattern, return_analysis = FunctionSignatureCache.get_or_create_output_model(func, name, force_unpack=force_unpack)
        
        # Store force_unpack in metadata
        metadata = FunctionMetadata(
            # ... existing fields
            force_unpack=force_unpack,  # Add this field
            # ... rest
        )
```

#### 2.2 Update Execution Methods
**File:** `/abstractions/ecs/callable_registry.py:1219` (in `_finalize_multi_entity_result`)

Pass `force_unpack` to unpacker:
```python
# Get force_unpack from metadata
force_unpack = metadata.force_unpack if hasattr(metadata, 'force_unpack') else False

# Pass to unpacker
unpack_result = ContainerReconstructor.unpack_with_signature_analysis(
    result, 
    func_name, 
    signature_analysis,
    force_unpack=force_unpack  # Add this parameter
)
```

#### 2.3 Update ContainerReconstructor
**File:** `/abstractions/ecs/entity_unpacker.py:335`

Add `force_unpack` parameter to `unpack_with_signature_analysis()` and pass it through to the analysis chain.

### Phase 3: Add Execution-Time Force Unpacking

#### 3.1 Update Execute Methods
**File:** `/abstractions/ecs/callable_registry.py` (execute/aexecute methods)

Add optional `force_unpack` parameter:
```python
def execute(cls, func_name: str, force_unpack: Optional[bool] = None, **kwargs) -> Union[Entity, List[Entity]]:
    # If force_unpack is provided at execution time, it overrides function-level setting
    metadata = cls._functions[func_name]
    effective_force_unpack = force_unpack if force_unpack is not None else getattr(metadata, 'force_unpack', False)
    
    # Pass to execution pipeline
```

### Phase 4: Update Data Structures

#### 4.1 Add force_unpack to FunctionMetadata
**File:** `/abstractions/ecs/callable_registry.py` (FunctionMetadata dataclass)

```python
@dataclass
class FunctionMetadata:
    # ... existing fields
    force_unpack: bool = False  # Add this field
    # ... rest
```

#### 4.2 Update ReturnAnalysis
**File:** `/abstractions/ecs/return_type_analyzer.py:34-53`

Add `force_unpack` tracking:
```python
class ReturnAnalysis:
    def __init__(
        self,
        # ... existing parameters
        force_unpack: bool = False,  # Add this
        # ... rest
    ):
        # ... existing assignments
        self.force_unpack = force_unpack
        # ... rest
```

## Benefits of This Approach

### 1. **Safe by Default**
- No more accidental atomic data unpacking
- Container structures preserved as addressable entities
- Maintains referential integrity

### 2. **Explicit Intent**
- Force unpacking requires explicit opt-in
- Clear distinction between "contains entities" and "should unpack"
- No surprising behavior

### 3. **Flexible When Needed**
- Function-level: `@register("func", force_unpack=True)`
- Execution-level: `execute("func", force_unpack=True)`
- Both levels supported with execution-time override

### 4. **Backward Compatible**
- Existing `Tuple[Entity, Entity]` functions continue to work
- Only changes default behavior for containers
- No breaking changes to entity wrapping

## Validation Plan

### Test Cases

#### 1. **Default Safe Behavior**
```python
@register("process_students")
def process_students(ids: List[str]) -> List[Student]:
    return [Student(name=f"Student {i}") for i in ids]

# Should return: ContainerEntity(students_list) - NOT unpacked
result = execute("process_students", ids=["1", "2", "3"])
assert isinstance(result, Entity)  # Single container entity
assert len(result) == 1  # Not unpacked to 3 entities
```

#### 2. **Force Unpacking**
```python
@register("process_students_unpack", force_unpack=True)
def process_students_unpack(ids: List[str]) -> List[Student]:
    return [Student(name=f"Student {i}") for i in ids]

# Should return: [student1, student2, student3] - unpacked
result = execute("process_students_unpack", ids=["1", "2", "3"])
assert isinstance(result, list)  # List of entities
assert len(result) == 3  # Unpacked to 3 entities
```

#### 3. **Execution-Time Override**
```python
# Function registered without force_unpack
result1 = execute("process_students", ids=["1", "2"])  # Wrapped
result2 = execute("process_students", force_unpack=True, ids=["1", "2"])  # Unpacked
```

#### 4. **Tuple Behavior Unchanged**
```python
@register("analyze_student")
def analyze_student(student: Student) -> Tuple[Assessment, Recommendation]:
    return Assessment(...), Recommendation(...)

# Should still unpack by default (no change)
result = execute("analyze_student", student=student)
assert isinstance(result, list)  # Unpacked tuple
assert len(result) == 2
```

## Risk Assessment

### Low Risk
- Changes are additive (new parameters with defaults)
- Core unpacking logic unchanged (just strategy selection)
- Backward compatibility maintained

### Medium Risk
- Need to update multiple files in coordination
- Test coverage must be comprehensive
- Documentation needs updates

### Mitigation
- Implement in phases with testing at each step
- Keep force_unpack optional with safe defaults
- Comprehensive test suite before deployment

## Justification

This fix addresses the fundamental design flaw where the system confuses "contains entities" with "should unpack". The new approach:

1. **Follows the principle of least surprise** - containers stay as containers by default
2. **Provides escape hatches** when unpacking is genuinely needed
3. **Maintains entity addressability** - every result can be addressed via `@uuid`
4. **Prevents atomic data leakage** - no more non-entity elements in results
5. **Supports power users** while keeping novices safe

The force unpacking option addresses legitimate use cases where unpacking is desired (e.g., batch processing returning individual entities), while the safe default prevents accidental atomic data exposure.