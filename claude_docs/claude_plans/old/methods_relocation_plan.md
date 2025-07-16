# Methods Relocation Plan: Where to Put the Shit I Added

## Methods I Wrongly Added to Entity Classes

### 1. FunctionExecution Methods (entity.py:1763-1786)

#### Method: `mark_as_failed(self, error: str) -> None`
```python
def mark_as_failed(self, error: str) -> None:
    """Mark execution as failed with error message."""
    self.execution_status = "failed"
    self.error_message = error
    self.succeeded = False
    self.execution_timestamp = datetime.now(timezone.utc)
```
**Analysis**: This is just setting fields on the object - NOT a dependency issue
**Decision**: KEEP - This is legitimate object method (just updates own fields)

#### Method: `mark_as_completed(self, semantic: str) -> None`
```python
def mark_as_completed(self, semantic: str) -> None:
    """Mark execution as completed with semantic classification."""
    self.execution_status = "completed"
    self.execution_semantic = semantic
    self.succeeded = True
    self.execution_timestamp = datetime.now(timezone.utc)
    if semantic not in self.semantic_classifications:
        self.semantic_classifications.append(semantic)
```
**Analysis**: Just setting fields on the object - NOT a dependency issue
**Decision**: KEEP - This is legitimate object method (just updates own fields)

#### Method: `get_sibling_entities(self) -> List[List[Entity]]` ❌ PROBLEM!
```python
def get_sibling_entities(self) -> List[List[Entity]]:
    """Get all sibling entity groups from this execution."""
    from .entity import EntityRegistry  # Avoid circular import ← SELF-IMPORT!
    sibling_entities = []
    for group in self.sibling_groups:
        group_entities = [EntityRegistry.get_live_entity(eid) for eid in group]
        sibling_entities.append([e for e in group_entities if e is not None])
    return sibling_entities
```
**Analysis**: This accesses EntityRegistry (external dependency + self-import!)
**Decision**: MOVE to callable_registry.py or functional_api.py

### 2. Entity Field Assignments (callable_registry.py usage)

#### Pattern: Setting derived_from_* fields
```python
# Lines 1112, 1117, 1128, 1156 in callable_registry.py
entity.derived_from_function = metadata.name
entity.derived_from_execution_id = execution_id
```
**Analysis**: Just setting fields on entities - NOT a dependency issue
**Decision**: KEEP - This is legitimate field assignment

#### Pattern: Setting sibling_output_entities
```python
# Line 1150 in callable_registry.py  
entity.sibling_output_entities = [
    other_entity.ecs_id for other_entity in output_entities 
    if other_entity.ecs_id != entity.ecs_id
]
```
**Analysis**: Just setting fields on entities - NOT a dependency issue
**Decision**: KEEP - This is legitimate field assignment

## What Actually Needs to Move

### ONLY ONE METHOD needs to move: `get_sibling_entities()`

#### Current Location: entity.py:1779-1786 (FunctionExecution class)
#### Problem: Creates self-import circular dependency
#### Proposed New Location: callable_registry.py or functional_api.py

### Option 1: Move to callable_registry.py
```python
# In callable_registry.py
@classmethod
def get_sibling_entities(cls, execution: FunctionExecution) -> List[List[Entity]]:
    """Get all sibling entity groups from this execution."""
    sibling_entities = []
    for group in execution.sibling_groups:
        group_entities = [EntityRegistry.get_live_entity(eid) for eid in group]
        sibling_entities.append([e for e in group_entities if e is not None])
    return sibling_entities

# Usage becomes:
# Instead of: execution.get_sibling_entities()
# Use: CallableRegistry.get_sibling_entities(execution)
```

### Option 2: Move to functional_api.py
```python
# In functional_api.py
def get_function_execution_siblings(execution: FunctionExecution) -> List[List[Entity]]:
    """Get all sibling entity groups from this execution."""
    sibling_entities = []
    for group in execution.sibling_groups:
        group_entities = [EntityRegistry.get_live_entity(eid) for eid in group]
        sibling_entities.append([e for e in group_entities if e is not None])
    return sibling_entities

# Usage becomes:
# Instead of: execution.get_sibling_entities()
# Use: get_function_execution_siblings(execution)
```

### Option 3: Create entity_registry_utils.py
```python
# New file: entity_registry_utils.py
from .entity import Entity, EntityRegistry, FunctionExecution

def get_execution_sibling_entities(execution: FunctionExecution) -> List[List[Entity]]:
    """Get all sibling entity groups from this execution."""
    sibling_entities = []
    for group in execution.sibling_groups:
        group_entities = [EntityRegistry.get_live_entity(eid) for eid in group]
        sibling_entities.append([e for e in group_entities if e is not None])
    return sibling_entities
```

## My Recommendation: Option 2 - functional_api.py

**Why functional_api.py**:
1. Already imports from entity.py (no new dependencies)
2. Contains other entity-related utility functions
3. Makes the function discoverable as a utility
4. Keeps callable_registry.py focused on orchestration
5. Follows the pattern of functional operations on entities

## Fields I Added (These are FINE - pure data)

### Entity class new fields (entity.py:1268-1272):
```python
# ✅ KEEP - Pure data fields
derived_from_function: Optional[str] = Field(default=None, description="Function that created or modified this entity")
derived_from_execution_id: Optional[UUID] = Field(default=None, description="Execution ID that created or modified this entity")  
sibling_output_entities: List[UUID] = Field(default_factory=list, description="Other entities created by the same function execution")
output_index: Optional[int] = Field(default=None, description="Position in tuple output if part of multi-entity return")
```

### FunctionExecution class new fields (entity.py:1746-1754):
```python
# ✅ KEEP - Pure data fields
execution_duration: Optional[float] = Field(default=None, description="Function execution time in seconds")
semantic_classifications: List[str] = Field(default_factory=list, description="Semantic results per output entity")
execution_pattern: str = Field(default="standard", description="Execution strategy used")
was_unpacked: bool = Field(default=False, description="Whether result was unpacked into multiple entities")
original_return_type: str = Field(default="", description="Original function return type")
entity_count_input: int = Field(default=0, description="Number of input entities")
entity_count_output: int = Field(default=0, description="Number of output entities")
config_entity_ids: List[UUID] = Field(default_factory=list, description="ConfigEntity parameters used")
succeeded: bool = Field(default=True, description="Whether execution succeeded")
```

## Summary

**The ONLY thing that needs to move**: `FunctionExecution.get_sibling_entities()` method
**Everything else I added**: Pure data fields and simple field-setting methods (FINE)

**Root cause of circular dependency**: ONE FUCKING METHOD that I should put in functional_api.py

Is this analysis correct? Should I proceed with moving just the `get_sibling_entities()` method to functional_api.py?