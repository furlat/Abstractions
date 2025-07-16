# Callable Registry UUID Timeline Analysis

## Overview

This document provides a detailed analysis of what UUIDs are available at each stage of the callable registry execution flow. This is critical for implementing proper UUID tracking in callable events for cascade implementation.

## CallableRegistry Execution Flow UUID Timeline

### 🚀 **Phase 1: Function Start** (`aexecute()` → `_execute_async()`)

**Available UUIDs:**
```python
# Input analysis from kwargs
input_entity_ids = []
input_entity_types = []
for param_name, value in kwargs.items():
    if isinstance(value, Entity):
        input_entity_ids.append(value.ecs_id)
        input_entity_types.append(type(value).__name__)
    elif isinstance(value, str) and value.startswith('@'):
        # UUID reference in address format
        uuid_ref = parse_uuid_from_address(value)
        input_entity_ids.append(uuid_ref)
```

**Event: FunctionExecutionEvent**
- ✅ `input_entity_ids: List[UUID]` - From kwargs entities
- ✅ `input_entity_types: List[str]` - From entity types
- ❌ `output_entity_ids: List[UUID]` - Not available yet
- ❌ `execution_id: UUID` - Not generated yet

### 🔍 **Phase 2: Strategy Detection** (`_detect_execution_strategy()`)

**Available UUIDs:**
```python
# Lines 422-464 in callable_registry.py
entity_params = []
config_params = []
for param_name, value in kwargs.items():
    param_type = type_hints.get(param_name)
    if is_top_level_config_entity(param_type):
        config_params.append(param_name)
        if isinstance(value, Entity):
            config_entity_ids.append(value.ecs_id)
    elif isinstance(value, Entity):
        entity_params.append(param_name)
        entity_ids.append(value.ecs_id)
```

**Event: StrategyDetectionEvent**
- ✅ `input_entity_ids: List[UUID]` - From entity analysis
- ✅ `input_entity_types: List[str]` - From type analysis
- ✅ `config_entity_ids: List[UUID]` - From config entity detection
- ✅ `entity_type_mapping: Dict[UUID, str]` - Maps entity UUIDs to types

### 🔧 **Phase 3: Input Preparation** (Various `_execute_*` methods)

#### A. `_execute_with_partial()` (Lines 493-648)
**Available UUIDs:**
```python
# Entity separation
entity_params = {}  # param_name -> Entity (with ecs_id)
config_params = {}  # param_name -> ConfigEntity (with ecs_id)

# Config entity creation (Lines 515-534)
config_entities = {}  # param_name -> ConfigEntity (with ecs_id)
for param_name, config_entity in config_entities.items():
    config_entity.promote_to_root()  # Now has ecs_id
    created_config_entity_ids.append(config_entity.ecs_id)
```

#### B. `_execute_borrowing()` (Lines 718-785)
**Available UUIDs:**
```python
# Input entity creation (Lines 722-727)
input_entity = await cls._create_input_entity_with_borrowing(...)
input_entity.promote_to_root()  # Now has ecs_id and root_ecs_id
created_input_entity_ids.append(input_entity.ecs_id)

# Execution copy (Lines 730-738)
execution_entity = EntityRegistry.get_stored_entity(
    input_entity.root_ecs_id, input_entity.ecs_id
)
execution_copy_ids.append(execution_entity.ecs_id)
```

#### C. `_execute_transactional()` (Lines 788-831)
**Available UUIDs:**
```python
# Lines 803-806
execution_kwargs, original_entities, execution_copies, object_identity_map = 
    await cls._prepare_transactional_inputs(kwargs)

# From _prepare_transactional_inputs (Lines 834-880)
original_entity_ids = [e.ecs_id for e in original_entities]
execution_copy_ids = [e.ecs_id for e in execution_copies]
isolation_entity_ids = execution_copy_ids  # Same as execution copies
```

**Event: InputPreparationEvent**
- ✅ `input_entity_ids: List[UUID]` - From original kwargs entities
- ✅ `created_entities: List[UUID]` - From input entity creation
- ✅ `config_entities_created: List[UUID]` - From config entity creation
- ✅ `execution_copy_ids: List[UUID]` - From transactional isolation
- ✅ `borrowed_from_entities: List[UUID]` - From borrowing operations

### ⚡ **Phase 4: Function Execution** (During function call)

**Available UUIDs:**
```python
# All execution paths have execution_id generated
execution_id = uuid4()  # Generated in _execute_transactional (Line 799)

# During execution, we have:
# - Input entity UUIDs (from phases 1-3)
# - Execution copy UUIDs (from transactional path)
# - Execution ID UUID
```

**Event: (No specific event during execution, but context available)**
- ✅ `execution_id: UUID` - Generated for tracking
- ✅ `input_entity_ids: List[UUID]` - From input preparation
- ✅ `execution_copy_ids: List[UUID]` - From transactional isolation

### 🔬 **Phase 5: Semantic Analysis** (`_detect_execution_semantic()`)

**Available UUIDs:**
```python
# Lines 912-938
def _detect_execution_semantic(cls, result: Entity, object_identity_map: Dict[int, Entity]):
    # object_identity_map: Maps id(execution_copy) -> original_entity
    original_entity_ids = [e.ecs_id for e in object_identity_map.values()]
    
    # Result analysis
    if isinstance(result, Entity):
        result_entity_id = result.ecs_id
        
    # Check for mutations/detachments
    for original_entity in object_identity_map.values():
        if original_entity.root_ecs_id:
            tree = EntityRegistry.get_stored_tree(original_entity.root_ecs_id)
            tree_entity_ids = list(tree.nodes.keys()) if tree else []
```

**Event: SemanticAnalysisEvent**
- ✅ `input_entity_ids: List[UUID]` - From object_identity_map
- ✅ `result_entity_ids: List[UUID]` - From result analysis
- ✅ `analyzed_entity_ids: List[UUID]` - From semantic analysis
- ✅ `original_entity_id: Optional[UUID]` - From mutation detection

### 📦 **Phase 6: Result Processing** (Unpacking & Finalization)

#### A. `_finalize_multi_entity_result()` (Lines 994-1061)
**Available UUIDs:**
```python
# Lines 1012-1018
unpacking_result = ContainerReconstructor.unpack_with_signature_analysis(...)

# Unpacking results
primary_entity_ids = [e.ecs_id for e in unpacking_result.primary_entities]
container_entity_id = unpacking_result.container_entity.ecs_id if unpacking_result.container_entity else None

# Sibling relationships (Lines 1051-1052)
sibling_entity_ids = [e.ecs_id for e in final_entities]
```

#### B. `_setup_sibling_relationships()` (Lines 1107-1132)
**Available UUIDs:**
```python
# Lines 1114-1125
entity_ids = [e.ecs_id for e in entities]
for i, entity in enumerate(entities):
    # Sibling IDs (all others from same execution)
    entity.sibling_output_entities = [
        eid for j, eid in enumerate(entity_ids) if j != i
    ]
```

**Event: UnpackingEvent**
- ✅ `source_entity_ids: List[UUID]` - From unpacking source
- ✅ `unpacked_entity_ids: List[UUID]` - From unpacking results
- ✅ `container_entity_id: Optional[UUID]` - From container creation
- ✅ `sibling_entity_ids: List[UUID]` - From sibling setup

### 🏁 **Phase 7: Execution Completion** (Recording & Finalization)

#### A. `_record_multi_entity_execution()` (Lines 1135-1173)
**Available UUIDs:**
```python
# Lines 1148-1166
execution_record = FunctionExecution(
    ecs_id=execution_id,
    input_entity_id=input_entity.ecs_id if input_entity else None,
    output_entity_ids=[e.ecs_id for e in output_entities]
)

# Additional UUIDs
config_entity_ids = [c.ecs_id for c in (config_entities or [])]
sibling_groups = [[e.ecs_id for e in output_entities]]
```

**Event: FunctionExecutedEvent**
- ✅ `input_entity_ids: List[UUID]` - From input tracking
- ✅ `output_entity_ids: List[UUID]` - From output entities
- ✅ `created_entity_ids: List[UUID]` - From semantic analysis
- ✅ `modified_entity_ids: List[UUID]` - From mutation detection
- ✅ `config_entity_ids: List[UUID]` - From config entity creation
- ✅ `execution_record_id: UUID` - From execution record
- ✅ `sibling_entity_ids: List[UUID]` - From sibling relationships

## Complete UUID Tracking Pattern

Based on this analysis, here's the complete UUID tracking pattern needed for each callable event:

### **Base UUID Fields for All Events**
```python
# Core entity tracking
input_entity_ids: List[UUID] = Field(default_factory=list)
input_entity_types: List[str] = Field(default_factory=list)

# Function execution tracking
execution_id: Optional[UUID] = None
function_execution_id: Optional[UUID] = None
```

### **Event-Specific UUID Fields**

#### **FunctionExecutionEvent/FunctionExecutedEvent**
```python
# Input/Output tracking
input_entity_ids: List[UUID] = Field(default_factory=list)
output_entity_ids: List[UUID] = Field(default_factory=list)
created_entity_ids: List[UUID] = Field(default_factory=list)
modified_entity_ids: List[UUID] = Field(default_factory=list)
config_entity_ids: List[UUID] = Field(default_factory=list)
execution_record_id: Optional[UUID] = None
```

#### **InputPreparationEvent/InputPreparedEvent**
```python
# Input processing
input_entity_ids: List[UUID] = Field(default_factory=list)
created_entities: List[UUID] = Field(default_factory=list)
config_entities_created: List[UUID] = Field(default_factory=list)
execution_copy_ids: List[UUID] = Field(default_factory=list)
borrowed_from_entities: List[UUID] = Field(default_factory=list)
```

#### **SemanticAnalysisEvent/SemanticAnalyzedEvent**
```python
# Semantic analysis
input_entity_ids: List[UUID] = Field(default_factory=list)
result_entity_ids: List[UUID] = Field(default_factory=list)
analyzed_entity_ids: List[UUID] = Field(default_factory=list)
original_entity_id: Optional[UUID] = None
```

#### **UnpackingEvent/UnpackedEvent**
```python
# Unpacking results
source_entity_ids: List[UUID] = Field(default_factory=list)
unpacked_entity_ids: List[UUID] = Field(default_factory=list)
container_entity_id: Optional[UUID] = None
sibling_entity_ids: List[UUID] = Field(default_factory=list)
```

This analysis provides the complete foundation for implementing proper UUID tracking in callable events for cascade implementation.