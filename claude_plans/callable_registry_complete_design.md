# Entity-Native Callable Registry: Complete Design Document

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Core Design Principles](#core-design-principles)
3. [Input Processing Strategy](#input-processing-strategy)
4. [Output Analysis & Unpacking](#output-analysis--unpacking)
5. [Semantic Detection via live_id](#semantic-detection-via-live_id)
6. [Functional Relationship Tracking](#functional-relationship-tracking)
7. [Enhanced Execution Flow](#enhanced-execution-flow)
8. [Entity System Integration](#entity-system-integration)
9. [Implementation Architecture](#implementation-architecture)
10. [Current Gaps & Required Primitives](#current-gaps--required-primitives)
11. [Benefits & Design Validation](#benefits--design-validation)

## Executive Summary

This document presents a comprehensive design for an entity-native callable registry that treats all function execution as entity-to-entity transformations. The system maintains complete audit trails, sophisticated semantic analysis, and seamless integration with the existing ECS while supporting complex execution patterns including borrowing, transactional operations, parameter handling, and multi-entity outputs.

### **Key Innovation: live_id-Based Semantic Detection**

The core breakthrough is using `live_id` comparison to deterministically classify function execution semantics:
- **MUTATION**: `output.live_id == input_copy.live_id` → In-place modification
- **CREATION**: `output.live_id ∉ input_live_ids` → New entity creation  
- **DETACHMENT**: `output.live_id ∈ input_tree_live_ids` → Child extraction from parent tree

This eliminates complex heuristics while providing precise semantic classification.

## Core Design Principles

### **1. Universal Entity Boundary**
**Principle**: Every function execution has exactly one input entity and one output entity from the ECS perspective, regardless of the actual function signature complexity.

**Reasoning**: This simplifies the execution model dramatically while maintaining complete audit trails. Complex inputs (multiple entities, parameters, references) are unified into a single composite input entity. Complex outputs are either unpacked into multiple entities or wrapped in container entities based on configuration.

**Benefits**:
- Consistent execution model across all patterns
- Simplified detection algorithms 
- Complete provenance tracking
- Natural integration with existing entity primitives

### **2. Everything ECS-Tracked**
**Principle**: All data flowing into and out of functions must have ECS counterparts - no "raw" data bypassing the entity system.

**Reasoning**: This ensures complete audit trails and enables sophisticated analysis. Parameters become parameter entities, borrowed data creates composite entities, and all results are registered in the ECS.

**Implementation**: 
- Non-entity parameters → `ParameterEntity` (flat entities with primitive fields)
- @uuid.field references → Borrowing via `attribute_source` tracking
- Mixed inputs → Composite input entities combining all patterns

### **3. Always Work on Copies**
**Principle**: Function execution operates on `get_stored_entity()` copies, naturally breaking `live_id` lifespan and providing complete isolation.

**Reasoning**: This eliminates fears about input modification while enabling sophisticated semantic detection. The original entities remain untouched, and we can analyze what the function actually did by comparing the results.

**Flow**:
1. Create frozen snapshot in ECS
2. Get isolated execution copies  
3. Disconnect live inputs from registry (prevent mutation propagation)
4. Execute function with complete mutation freedom
5. Analyze results and reconnect/version as appropriate

### **4. live_id as Truth Source**
**Principle**: The `live_id` of returned entities tells us everything we need to know about execution semantics.

**Reasoning**: Since execution works on copies with fresh `live_ids`, comparing the output `live_ids` with input `live_ids` provides deterministic classification without complex heuristics.

**Detection Logic**:
```python
if output.live_id == input_copy.live_id:
    # MUTATION: Function modified input in-place
    # → Preserve lineage_id, update ecs_id via update_ecs_ids()
elif output.live_id in input_tree_live_ids:
    # DETACHMENT: Function extracted child from input tree  
    # → Call detach(), promote to root, update parent tree
else:
    # CREATION: Function created new entity
    # → New lineage_id, track functional derivation
```

## Input Processing Strategy

### **The Challenge: Unified Input Model**

The callable registry must handle diverse input patterns:

```python
# Pattern A1: Pure Borrowing - Address References
execute("func", name="@uuid.name", age="@uuid.age")

# Pattern A2: Direct Entity Reference
execute("func", student=student_entity)

# Pattern A3: Sub-entity Direct Reference 
execute("func", grade=student_entity.record.grades[0])

# Pattern A4: Entity Reference via Address
execute("func", student="@uuid")

# Pattern A5: Sub-entity via Address
execute("func", grade="@uuid.record.grades.0")

# Pattern A6: Entity + Parameters  
execute("func", student=student_entity, threshold=3.5, reason="update")

# Pattern A7: Mixed Everything
execute("func", name="@uuid.name", student=entity, grade="@uuid.record.grades.0", threshold=3.5)
```

### **Solution: Composite Input Entity Pattern**

All patterns reduce to a single composite input entity:

#### **Pattern A1 Implementation: Pure Borrowing - Address References**
```python
# Input: Pure borrowing with field addresses
input_entity = create_composite_entity(
    InputEntity, 
    {"name": "@uuid.name", "age": "@uuid.age"}
)
# Result: InputEntity with borrowed fields and attribute_source tracking
```

#### **Pattern A2 Implementation: Direct Entity Reference** 
```python
# Input: Direct entity object
input_entity = InputEntity(student=student_entity)
# Result: InputEntity with entity field
```

#### **Pattern A3 Implementation: Sub-entity Direct Reference**
```python
# Input: Direct reference to sub-entity
grade_entity = student_entity.record.grades[0]  # Direct object reference
input_entity = InputEntity(grade=grade_entity)
# Result: InputEntity with sub-entity field
```

#### **Pattern A4 Implementation: Entity Reference via Address**
```python
# Input: Entity via address string
input_entity = create_composite_entity(
    InputEntity,
    {"student": "@uuid"}  # Resolves to full entity
)
# Result: InputEntity with resolved entity field
```

#### **Pattern A5 Implementation: Sub-entity via Address**
```python
# Input: Sub-entity via address string (supports dict keys and list indices)
input_entity = create_composite_entity(
    InputEntity,
    {
        "grade": "@uuid.record.grades.0",        # List index navigation
        "course": "@uuid.courses.math_101",      # Dict key navigation  
        "metadata": "@uuid.data.tags.primary"   # Nested dict navigation
    }
)
# Result: InputEntity with resolved sub-entity/field values and dependency tracking
```

#### **Pattern A6 Implementation: Entity + Parameters**
```python
# Input: Entity + parameters
param_entity = ParameterEntity(threshold=3.5, reason="update")
input_entity = InputEntity(student=student_entity, parameters=param_entity)
# Result: Composite entity combining entity and parameter data
```

#### **Pattern A7 Implementation: Mixed Everything**
```python
# Input: Mixed everything - addresses, entities, sub-entities, dict navigation, parameters
param_entity = ParameterEntity(threshold=3.5)
input_entity = create_composite_entity(
    InputEntity,
    {
        "name": "@uuid.profile.name",            # Nested field address
        "student": student_entity,               # Direct entity
        "grade": "@uuid.record.grades.0",       # List index navigation
        "course": "@uuid.courses.math_101",     # Dict key navigation
        "metadata": "@uuid.tags.primary.value", # Nested dict navigation
        "parameters": param_entity               # Parameter entity
    }
)
# Result: Complex composite with all input patterns unified, including dict navigation
```

### **Parameter Entity Pattern**

**Concept**: Non-entity parameters become flat parameter entities, enabling:
- **Currying**: Pre-create parameter entities and reuse them
- **Caching**: Store common parameter configurations  
- **Provenance**: Full ECS tracking of parameter data

**Implementation**:
```python
# Manual parameter entity creation for currying
analysis_params = ParameterEntity(threshold=85.0, weight=1.2, bonus=5.0)
analysis_params.promote_to_root()  # Cache in registry

# Reuse in multiple executions
execute("analyze", grades="@record.grades", **analysis_params.model_dump())
```

### **Enhanced Input Pattern Processing**

**Leveraging Existing Entity System Infrastructure**:

After comprehensive analysis, **~70% of callable registry functionality already exists** in entity.py. Here's the reuse strategy:

**✅ DIRECT REUSE (No Changes Needed)**:
- `EntityRegistry.ecs_id_to_root_id` - O(1) root tree resolution
- `EntityRegistry.get_stored_entity()` - Immutable execution copies (lines 1145-1155)
- `Entity.detach()` - Complete detachment handling (lines 1467-1498)
- `Entity.attach()` - Parent attachment (lines 1624-1655)
- `Entity.update_ecs_ids()` - Mutation with lineage preservation (lines 1382-1405)
- `Entity.attribute_source` - Complete provenance tracking (lines 1264-1339)
- `create_composite_entity()` - Mixed address/value processing (functional_api.py)
- `Entity.create_from_address_dict()` - Multi-address borrowing (lines 1601-1621)

**🔧 ENHANCE EXISTING (Minor Modifications)**:
- `ECSAddressParser.resolve_address()` - Add EntityTree navigation instead of getattr chain
- `Entity.borrow_from_address()` - Extend to support sub-entity extraction (line 1599 TODO)
- Input pattern classification - Add to existing create_composite_entity workflow

**❌ BUILD NEW (Truly Missing)**:
- Semantic detection algorithm (live_id comparison logic)
- FunctionExecution entity class
- Output unpacking system

**Enhancement Strategy - Leverage Existing Code**:

```python
# 🔧 ENHANCE: Extend existing ECSAddressParser instead of building new class
class ECSAddressParser:
    """Enhanced existing parser with EntityTree navigation."""
    
    @classmethod 
    def resolve_subentity_reference(cls, address: str) -> Any:
        """🔧 ENHANCE existing resolve_address() method."""
        # Use existing parse_address (✅ REUSE)
        entity_id, field_path = cls.parse_address(address)
        
        # Use existing registry lookup (✅ REUSE) 
        root_id = EntityRegistry.ecs_id_to_root_id.get(entity_id)
        if not root_id:
            raise ValueError(f"Entity {entity_id} not found")
        
        # Use existing get_stored_tree (✅ REUSE)
        tree = EntityRegistry.get_stored_tree(root_id)
        if not tree:
            raise ValueError(f"Tree not found")
        
        # 🔧 ENHANCE: Replace getattr chain with EntityTree navigation
        return cls._navigate_using_entity_edges(tree, entity_id, field_path)
    
    @classmethod
    def _navigate_using_entity_edges(cls, tree: EntityTree, entity_id: UUID, field_path: List[str]) -> Any:
        """🔧 ENHANCE: Use EntityTree edges instead of getattr chain."""
        current_entity = tree.get_entity(entity_id)  # ✅ REUSE existing method
        
        for field_part in field_path:
            if hasattr(current_entity, field_part):
                # Standard field access (✅ REUSE existing pattern)
                current_entity = getattr(current_entity, field_part)
            else:
                # 🔧 ENHANCE: Use pre-computed edge metadata for container navigation
                current_entity = cls._find_in_containers(tree, current_entity.ecs_id, field_part)
                if current_entity is None:
                    raise ValueError(f"Cannot navigate to {field_part}")
        
        return current_entity
    
    @classmethod
    def _find_in_containers(cls, tree: EntityTree, entity_id: UUID, key_or_index: str) -> Optional[Entity]:
        """🔧 ENHANCE: Add container navigation using existing EntityEdge metadata."""
        for target_id in tree.get_outgoing_edges(entity_id):  # ✅ REUSE existing method
            edge = tree.get_edges(entity_id, target_id)  # ✅ REUSE existing method
            if not edge:
                continue
            
            # Use existing container metadata (✅ REUSE)
            if (edge.container_key == key_or_index or 
                (key_or_index.isdigit() and edge.container_index == int(key_or_index))):
                return tree.get_entity(target_id)  # ✅ REUSE existing method
        
        return None

# 🔧 ENHANCE: Add classification to existing create_composite_entity workflow  
def classify_input_value(value: Any) -> str:
    """🔧 ENHANCE: Add pattern classification to existing workflow."""
    if isinstance(value, Entity):
        return "DIRECT_ENTITY"
    elif isinstance(value, str) and value.startswith("@"):
        return "ENTITY_ADDRESS" if "." not in value[1:] else "SUBENTITY_ADDRESS"
    else:
        return "PRIMITIVE"
```

### **Enhanced Composite Input Creation - Reusing Existing Infrastructure**

```python
# 🔧 ENHANCE: Extend existing create_composite_entity instead of building new function
async def create_enhanced_composite_input(
    input_entity_class: Type[Entity],
    kwargs: Dict[str, Any]
) -> Tuple[Entity, List[Entity]]:
    """🔧 ENHANCE existing create_composite_entity with pattern awareness."""
    
    # 🔧 ENHANCE: Add classification to existing workflow
    classified_inputs = {}
    entity_dependencies = []
    
    for field_name, value in kwargs.items():
        value_type = classify_input_value(value)  # 🔧 ENHANCE: New helper function
        
        if value_type == "SUBENTITY_ADDRESS":
            # 🔧 ENHANCE: Use enhanced ECSAddressParser
            resolved_value = ECSAddressParser.resolve_subentity_reference(value)
            classified_inputs[field_name] = resolved_value
            
            # Track entity dependencies using existing registry (✅ REUSE)
            entity_id = UUID(value[1:].split(".")[0])
            root_id = EntityRegistry.ecs_id_to_root_id.get(entity_id)
            if root_id:
                root_entity = EntityRegistry.get_live_entity(root_id)
                if root_entity:
                    entity_dependencies.append(root_entity)
        else:
            classified_inputs[field_name] = value
            if isinstance(value, Entity):
                entity_dependencies.append(value)
    
    # ✅ REUSE: Use existing create_composite_entity (no changes needed)
    input_entity = create_composite_entity(
        input_entity_class,
        classified_inputs,
        register=False  # ✅ REUSE existing parameter
    )
    
    return input_entity, entity_dependencies
```

### **Input Isolation Protocol**

**Goal**: Create completely isolated execution environment while maintaining audit trail.

**Steps**:
1. **Classify Input Patterns**: Analyze each input value type (A1-A7)
2. **Resolve All Addresses**: Convert @uuid and @uuid.field.path to entity objects  
3. **Validate Live Inputs**: Check for divergence from stored versions, auto-version if needed
4. **Create Composite Input**: Unify all input patterns into single input entity
5. **Register Frozen Snapshot**: `input_entity.promote_to_root()` creates immutable record
6. **Get Execution Copies**: `get_stored_entity()` for each entity input  
7. **Disconnect Live Objects**: Temporarily disconnect from registry to prevent mutation propagation

**New Primitives Needed**: 
- Enhanced `ECSAddressParser` with entity/sub-entity resolution
- `disconnect_from_registry(entities)` to temporarily break live connections

## Output Analysis & Unpacking

### **The Challenge: Output Type Diversity**

Functions can return:
- Primitives/non-entities → Always wrap in output entity
- Single entities → Apply semantic detection  
- Tuples with non-entities → Always pack into single entity
- Tuples with entities → Unpacking decision required
- Mixed tuples → Complex analysis needed

### **Output Classification Matrix**

#### **1. Non-Entity Results**
```python
def calculate() -> float:
    return 42.5

# Decision: Wrap in OutputEntity(result=42.5)
# Rationale: Maintains entity boundary, tracks function execution
```

#### **2. Non-Entity Tuple Results** 
```python
def analyze() -> Tuple[str, int, float]:
    return "result", 42, 3.14

# Decision: Pack into OutputEntity(field_0="result", field_1=42, field_2=3.14)
# Rationale: Contains non-entities, cannot unpack meaningfully
```

#### **3. Single Entity Results**
```python
def process(student: Student) -> Student:
    return student

# Decision: Apply live_id semantic detection
# No class metageneration needed (Student class already exists)
# Outcome: MUTATION | CREATION | DETACHMENT based on live_id analysis
```

#### **4. Multi-Entity Tuple Results**
```python
def split_record(student: Student) -> Tuple[Student, AcademicRecord, FinancialRecord]:
    return modified_student, new_academic, new_financial

# Decision: Default unpack=True (configurable per execution)
# If unpack=True:
#   - Register each entity individually 
#   - Don't create packed container entity
#   - Apply semantic detection to each output
#   - Link all outputs to same function execution
# If unpack=False:
#   - Create ContainerEntity(outputs=(student, academic, financial))
#   - Register container as single unit
```

### **Unpacking Strategy Deep Dive**

**Unpacking Trigger**: Return type annotation is `Tuple[...]` with multiple elements

**Unpacking Benefits**:
- Avoids unnecessary container entities
- Prevents de-rooting/re-rooting of individual entities
- Natural integration with existing entity operations
- Maintains fine-grained semantic analysis

**No-Unpack Benefits**:
- Simpler provenance (single output entity)
- Atomic operations (all-or-nothing registration)
- Container semantics when tuple structure matters

**Configuration**:
```python
# Per-execution control
execute("split_record", student=entity, unpack=True)  # Default
execute("split_record", student=entity, unpack=False) # Force container
```

### **Complex Tree Extraction Cases**

#### **Case A: Root + Sub-entity Returned**
```python
def update_and_extract(student: Student) -> Tuple[Student, Grade]:
    student.gpa = 3.9  # Modify root
    return student, student.record.grades[0]  # Return root + child

# Analysis Required:
# 1. student.live_id == input_copy.live_id → MUTATION
# 2. grade.live_id ∈ input_tree_live_ids → POTENTIAL DETACHMENT
# 3. Tree Analysis: Is grade still in student's tree post-execution?
#    - If removed: Detachment + Root mutation
#    - If present: In-place change + Root mutation (fine-grained result)
```

#### **Case B: Only Sub-entity Returned**  
```python
def extract_best_grade(student: Student) -> Grade:
    return student.record.grades[0]

# Analysis: grade.live_id ∈ input_tree_live_ids → DETACHMENT
# Design Decision: Always interpret as detachment (avoid ambiguity)
# Rationale: Consistent semantics, clear separation between extraction and reference
```

## Semantic Detection via live_id

### **The Core Innovation**

Traditional approaches use complex heuristics to determine if a function:
- Modified its input (mutation)
- Created a new entity (creation)  
- Extracted a child entity (detachment)

Our approach: **Use `live_id` comparison as ground truth**.

### **Why live_id Works**

1. **Execution Isolation**: Functions work on copies with fresh `live_ids`
2. **Deterministic Comparison**: Object identity is preserved through `live_id`
3. **No Heuristics Needed**: Direct comparison eliminates guesswork
4. **Works with All Patterns**: Same logic handles borrowing, transactional, and mixed modes

### **❌ BUILD NEW: Semantic Detection Algorithm**

```python
# ❌ BUILD NEW: Core semantic detection (truly missing functionality)
def analyze_execution_result(
    result: Any,
    input_entities: List[Entity], 
    execution_copies: List[Entity],
    input_trees: List[EntityTree]
) -> ExecutionSemantics:
    """❌ BUILD NEW: live_id-based semantic classification."""
    
    if not isinstance(result, Entity):
        return ExecutionSemantics.CREATION  # Non-entity results are new creations
    
    # ❌ BUILD NEW: live_id comparison logic (core innovation)
    for i, exec_copy in enumerate(execution_copies):
        if result.live_id == exec_copy.live_id:
            # ✅ REUSE: Use existing mutation handling
            result.update_ecs_ids()  # Existing method (lines 1382-1405)
            EntityRegistry.register_entity(result)  # Existing method
            return ExecutionSemantics.MUTATION
    
    # ❌ BUILD NEW: Enhanced detachment detection with sub-entity support
    for tree in input_trees:
        if result.live_id in tree.live_id_to_ecs_id:  # ✅ REUSE: existing mapping
            # ✅ REUSE: Use existing detachment handling
            result.detach()  # Existing method handles all 4 scenarios (lines 1467-1498)
            return ExecutionSemantics.DETACHMENT
    
    # ❌ BUILD NEW: Creation detection and registration
    # ✅ REUSE: Use existing entity promotion
    result.promote_to_root()  # Existing method (lines 1458-1465)
    return ExecutionSemantics.CREATION
```

### **Semantic Action Mapping**

#### **MUTATION Detected**
```python
# Actions:
# 1. Preserve lineage via update_ecs_ids() 
# 2. Maintain lineage_id (mutation chain)
# 3. Register updated entity
# 4. Version original entity tree

result.update_ecs_ids()  # New ecs_id, preserve lineage
EntityRegistry.register_entity(result)
EntityRegistry.version_entity(original_entity)
```

#### **CREATION Detected**
```python
# Actions:
# 1. New lineage_id (independent entity)
# 2. Add functional derivation tracking
# 3. Register as new root entity

result.derived_from_function = function_name
result.derived_from_execution_id = execution_id
result.function_input_entities = [e.ecs_id for e in input_entities]
result.promote_to_root()
```

#### **DETACHMENT Detected**
```python
# Actions:
# 1. Call detach() to promote child to root
# 2. Update parent tree to remove child
# 3. Version both parent and detached child

result.detach()  # Handles all detachment scenarios
parent_entity = get_parent_from_tree(result, input_tree)
EntityRegistry.version_entity(parent_entity)
```

## Functional Relationship Tracking

### **Beyond attribute_source**

The existing `attribute_source` tracks data provenance (where data came from) but not functional relationships (how data was transformed). We need explicit function execution tracking.

### **Required New Entity Fields**

```python
class Entity(BaseModel):
    # ... existing fields ...
    
    # Function execution tracking
    derived_from_function: Optional[str] = None
    derived_from_execution_id: Optional[UUID] = None  
    function_input_entities: List[UUID] = Field(default_factory=list)
    execution_timestamp: Optional[datetime] = None
    
    # For unpacked multi-entity outputs
    sibling_output_entities: List[UUID] = Field(default_factory=list)
    output_index: Optional[int] = None  # Position in tuple output
```

### **Function Execution Entity**

```python
class FunctionExecution(Entity):
    """Tracks a single function execution with complete lineage."""
    function_name: str
    input_entity_id: UUID  # The composite input entity
    output_entity_ids: List[UUID]  # All output entities (1+ if unpacked)
    execution_duration: float
    execution_mode: str  # "borrowing" | "transactional" | "mixed"
    
    # Unpacking information
    was_unpacked: bool = False
    original_return_type: str = ""
    
    # Error tracking
    succeeded: bool = True
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    
    # Performance metrics
    input_entity_count: int = 0
    output_entity_count: int = 0
```

### **Complete Execution Graph**

The functional relationship tracking creates a comprehensive execution graph:

```
[Input Entities] → [CompositeInputEntity] → [FunctionExecution] → [OutputEntity(s)]
       ↓                     ↓                      ↓                     ↓
[via function_input_    [registers all      [tracks execution    [via derived_from_
 entities field]         input sources]      metadata]            execution_id field]
```

**Graph Properties**:
- **Bidirectional Navigation**: From any entity, find all related function executions
- **Complete Audit Trail**: Every transformation tracked with full context
- **Performance Analysis**: Execution duration and entity counts
- **Error Attribution**: Failed executions linked to specific inputs

### **Sibling Relationship Tracking**

For unpacked multi-entity outputs:

```python
def split_student(student: Student) -> Tuple[Student, AcademicRecord, FinancialRecord]:
    # ... implementation

# Result entities all get:
# - Same derived_from_execution_id
# - sibling_output_entities = [other_output_ecs_ids]  
# - output_index = 0, 1, 2 respectively

# Enables queries like:
# "Find all entities created together with this academic record"
siblings = [EntityRegistry.get_entity(ecs_id) 
           for ecs_id in academic_record.sibling_output_entities]
```

## Enhanced Execution Flow

### **Complete End-to-End Flow**

#### **Phase 1: Optimized Input Preprocessing**
```python
# 1.1 Create optimized composite input using EntityTree primitives
input_entity, entity_inputs = await create_optimized_composite_input(
    InputEntity, kwargs
)

# 1.2 Get immutable tree copies for all dependency trees (O(1) lookups)
input_trees = []
execution_copies = []
dependency_trees = set()

for entity in entity_inputs:
    # Fast tree resolution using existing registry
    if entity.root_ecs_id:
        dependency_trees.add(entity.root_ecs_id)

# Get immutable copies of all dependency trees
for tree_root_id in dependency_trees:
    tree = EntityRegistry.get_stored_tree(tree_root_id)  # Deep copy with new live_ids
    if tree:
        input_trees.append(tree)
        
        # Get execution copies for each input entity
        for entity in entity_inputs:
            if entity.root_ecs_id == tree_root_id:
                copy = tree.get_entity(entity.ecs_id)
                if copy:
                    execution_copies.append(copy)

# 1.3 Validate live inputs using tree comparison
for i, entity in enumerate(entity_inputs):
    if entity.root_ecs_id and i < len(input_trees):
        check_entity_divergence_using_tree(entity, input_trees[i])

# 1.4 Register frozen input snapshot
input_entity.promote_to_root()  # Creates immutable record

# 1.5 No need to disconnect - execution copies are already isolated with new live_ids
```

#### **Phase 2: Function Execution**
```python
# 2.1 Prepare function arguments
function_args = prepare_function_args(execution_copies, primitive_params)

# 2.2 Execute with complete isolation
start_time = time.time()
try:
    if metadata.is_async:
        result = await metadata.original_function(**function_args)
    else:
        result = metadata.original_function(**function_args)
    succeeded = True
    error_info = None
except Exception as e:
    result = None
    succeeded = False
    error_info = capture_error_info(e)
execution_duration = time.time() - start_time
```

#### **Phase 3: Output Analysis & Unpacking**
```python
# 3.1 Analyze return type signature
return_type = get_function_return_type(metadata)
should_unpack = should_unpack_result(return_type, execution_config)

# 3.2 Handle unpacking if needed
if should_unpack and is_multi_entity_tuple(result):
    output_entities = list(result)  # Unpack tuple
    register_packed_entity = False
else:
    output_entities = [result] if result else []
    register_packed_entity = True

# 3.3 Apply semantic detection to each output
semantic_results = []
for output in output_entities:
    semantics = analyze_execution_result(
        output, entity_inputs, execution_copies, input_trees
    )
    semantic_results.append(semantics)
```

#### **Phase 4: Functional Relationship Registration**
```python
# 4.1 Create function execution entity
execution_entity = FunctionExecution(
    function_name=metadata.name,
    input_entity_id=input_entity.ecs_id,
    execution_duration=execution_duration,
    succeeded=succeeded,
    was_unpacked=should_unpack,
    # ... other fields
)
execution_entity.promote_to_root()

# 4.2 Process each output based on semantics
final_outputs = []
for output, semantics in zip(output_entities, semantic_results):
    if semantics.type == ExecutionSemantics.MUTATION:
        # Handle mutation
        output.update_ecs_ids()
        EntityRegistry.register_entity(output) 
        EntityRegistry.version_entity(semantics.source_entity)
        
    elif semantics.type == ExecutionSemantics.CREATION:
        # Handle creation
        output.derived_from_function = metadata.name
        output.derived_from_execution_id = execution_entity.ecs_id
        output.function_input_entities = [e.ecs_id for e in entity_inputs]
        output.promote_to_root()
        
    elif semantics.type == ExecutionSemantics.DETACHMENT:
        # Handle detachment
        output.detach()  # Uses existing primitive
        EntityRegistry.version_entity(semantics.parent_entity)
    
    final_outputs.append(output)

# 4.3 Set up sibling relationships for unpacked outputs
if len(final_outputs) > 1:
    setup_sibling_relationships(final_outputs, execution_entity.ecs_id)

# 4.4 Update execution entity with output references
execution_entity.output_entity_ids = [e.ecs_id for e in final_outputs]
EntityRegistry.version_entity(execution_entity)
```

#### **Phase 5: ECS Transaction Finalization**
```python
# 5.1 Reconnect or discard live inputs based on analysis
for entity, semantics in zip(entity_inputs, input_semantics):
    if semantics.was_mutated:
        reconnect_to_registry(entity, updated_version)
    else:
        # Keep disconnected, original entity unchanged
        reconnect_to_registry(entity, entity)

# 5.2 Return final result
if len(final_outputs) == 1:
    return final_outputs[0]
else:
    # Multiple outputs - return based on unpacking strategy
    if should_unpack:
        return final_outputs  # List of entities
    else:
        # Create and return container entity
        container = ContainerEntity(outputs=final_outputs)
        container.promote_to_root()
        return container
```

## Entity System Integration

### **Leveraging Existing Primitives**

The design maximizes use of existing entity system capabilities:

#### **From entity.py (Lines Referenced)**

**Identity & Versioning:**
- `entity.update_ecs_ids()` (1382-1405): Mutation handling with lineage preservation
- `entity.is_root_entity()` (1369-1373): Root detection for registration
- `entity.promote_to_root()` (1458-1465): Independent entity creation

**Tree Operations:**
- `entity.detach()` (1467-1498): Complete 4-scenario detachment handling
- `entity.attach(parent)` (1624-1655): Parent attachment with lineage updates
- `build_entity_tree()` (596-795): Full tree reconstruction for analysis

**Data Composition:**
- `entity.borrow_attribute_from()` (1516-1567): Direct borrowing with provenance
- `entity.borrow_from_address()` (1569-1598): Address-based borrowing
- `attribute_source` validation (1269-1339): Container-aware provenance tracking

**Registry Integration:**
- `EntityRegistry.get_stored_entity()` (1145-1155): Immutable copy retrieval
- `EntityRegistry.version_entity()` (1186-1247): Change detection and versioning
- `find_modified_entities()` (856-998): Sophisticated tree diffing

### **New Primitives Required**

#### **1. disconnect_from_registry(entities)**
**Purpose**: Temporarily disconnect live entities during function execution to prevent mutation propagation.

**Implementation**:
```python
def disconnect_from_registry(entities: List[Entity]) -> Dict[Entity, RegistryState]:
    """Temporarily disconnect entities from registry, return restoration state."""
    restoration_state = {}
    for entity in entities:
        # Save current registry state
        restoration_state[entity] = capture_registry_state(entity)
        
        # Remove from live_id_registry temporarily
        if entity.live_id in EntityRegistry.live_id_registry:
            del EntityRegistry.live_id_registry[entity.live_id]
    
    return restoration_state

def reconnect_to_registry(entity: Entity, updated_entity: Entity, 
                         restoration_state: RegistryState):
    """Reconnect entity to registry, potentially with updates."""
    # Restore registry connections with potentially updated entity
    EntityRegistry.live_id_registry[updated_entity.live_id] = updated_entity
```

#### **2. Enhanced Return Type Analysis**
**Purpose**: Sophisticated analysis of function return types for unpacking decisions.

**Implementation**:
```python
def analyze_return_type(func: Callable) -> ReturnTypeInfo:
    """Analyze function return type for unpacking strategy."""
    type_hints = get_type_hints(func)
    return_type = type_hints.get('return', Any)
    
    # Handle Tuple types
    if get_origin(return_type) is tuple:
        args = get_args(return_type)
        return ReturnTypeInfo(
            is_tuple=True,
            element_count=len(args),
            element_types=args,
            has_entities=any(is_entity_type(arg) for arg in args),
            has_non_entities=any(not is_entity_type(arg) for arg in args)
        )
    
    # Handle single types
    return ReturnTypeInfo(
        is_tuple=False,
        element_count=1,
        element_types=[return_type],
        has_entities=is_entity_type(return_type),
        has_non_entities=not is_entity_type(return_type)
    )
```

#### **3. Sibling Relationship Management**
**Purpose**: Link multiple outputs from same function execution.

**Implementation**:
```python
def setup_sibling_relationships(outputs: List[Entity], execution_id: UUID):
    """Set up sibling relationships for unpacked outputs."""
    output_ecs_ids = [e.ecs_id for e in outputs]
    
    for i, entity in enumerate(outputs):
        entity.derived_from_execution_id = execution_id
        entity.output_index = i
        entity.sibling_output_entities = [
            ecs_id for j, ecs_id in enumerate(output_ecs_ids) if j != i
        ]
```

## Implementation Architecture

### **Class Structure**

```python
# Core execution engine
class CallableRegistry:
    """Main registry with unified execution model."""
    
    @classmethod
    async def execute(cls, func_name: str, unpack: bool = True, **kwargs) -> Union[Entity, List[Entity]]:
        """Unified execution entry point."""
        
    @classmethod  
    async def _analyze_inputs(cls, kwargs: Dict[str, Any]) -> InputAnalysisResult:
        """Classify and process all input patterns."""
        
    @classmethod
    async def _create_composite_input(cls, analysis: InputAnalysisResult) -> Entity:
        """Create unified input entity from all patterns."""
        
    @classmethod
    async def _analyze_outputs(cls, result: Any, metadata: FunctionMetadata, 
                              inputs: InputAnalysisResult) -> OutputAnalysisResult:
        """Perform semantic detection and unpacking analysis."""
        
    @classmethod
    async def _register_execution(cls, analysis: OutputAnalysisResult) -> List[Entity]:
        """Register function execution and all resulting entities."""

# Enhanced metadata
@dataclass
class FunctionMetadata:
    """Extended metadata with return type analysis."""
    name: str
    original_function: Callable
    return_type_info: ReturnTypeInfo
    input_entity_class: Type[Entity]
    output_entity_class: Type[Entity]
    # ... other fields

# Analysis result types
@dataclass
class InputAnalysisResult:
    """Result of input pattern analysis."""
    input_pattern: InputPattern  # BORROWING | TRANSACTIONAL | MIXED
    entity_inputs: List[Entity]
    primitive_params: Dict[str, Any]
    composite_input_entity: Entity
    execution_copies: List[Entity]
    restoration_state: Dict[Entity, RegistryState]

@dataclass  
class OutputAnalysisResult:
    """Result of output semantic analysis."""
    should_unpack: bool
    output_entities: List[Entity]
    semantic_classifications: List[ExecutionSemantics]
    function_execution_entity: FunctionExecution
    sibling_relationships: List[Tuple[int, int]]  # (entity_index, sibling_index) pairs
```

### **Configuration System**

```python
class ExecutionConfig(BaseModel):
    """Per-execution configuration."""
    unpack_tuples: bool = True
    max_execution_time: float = 300.0
    track_performance: bool = True
    enable_error_recovery: bool = True
    force_parameter_entities: bool = False  # Always create param entities

class RegistryConfig(BaseModel):
    """Global registry configuration."""
    default_execution_config: ExecutionConfig
    enable_function_caching: bool = True
    max_cached_executions: int = 1000
    enable_execution_tracing: bool = False
```

## Current Gaps & Required Primitives

### **Missing from Current Implementation**

#### **1. Complete Input Pattern Support**
- **Current**: Basic dual-mode detection (borrowing vs transactional)
- **Missing**: Entity reference via address (`execute("func", student="@uuid")`)
- **Missing**: Sub-entity direct reference (`execute("func", grade=student.record.grades[0])`)
- **Missing**: Sub-entity via address (`execute("func", grade="@uuid.record.grades.0")`)
- **Needed**: Enhanced ECS Address Parser with entity/sub-entity resolution
- **Gap**: Only handles field borrowing and direct entity patterns

#### **2. Enhanced Input Processing**
- **Current**: Simple composite entity creation for borrowing pattern
- **Needed**: Unified processing for all 7 input patterns (A1-A7)
- **Gap**: No classification system for input value types

#### **3. Sophisticated Output Analysis**
- **Current**: Basic type checking and entity promotion
- **Needed**: Return type signature analysis and unpacking logic  
- **Gap**: No tuple unpacking, no semantic detection

#### **4. Enhanced live_id-Based Detection**
- **Current**: Placeholder lineage tracking (callable_registry.py:405-408)
- **Needed**: Complete semantic classification engine with sub-entity support
- **Gap**: Core detection algorithm not implemented, no sub-entity handling

#### **5. Functional Relationship Tracking**
- **Current**: Only `attribute_source` for data provenance
- **Needed**: `FunctionExecution` entities and derivation fields
- **Gap**: No audit trail for function calls

#### **6. Registry Disconnection**
- **Current**: No isolation mechanism during execution
- **Needed**: `disconnect_from_registry()` and `reconnect_to_registry()`
- **Gap**: Risk of mutation propagation during execution

### **Implementation Priority**

#### **Phase 1: Optimized EntityTree Integration** (Critical Priority)
1. **Leverage Existing EntityTree Primitives**:
   - Use `tree.get_entity()` for O(1) entity lookup instead of string parsing
   - Use `tree.get_outgoing_edges()` with `EntityEdge.container_key` for dict navigation  
   - Use `EntityEdge.container_index` for list/tuple navigation
   - Use `EntityRegistry.ecs_id_to_root_id` for fast tree resolution
2. **Implement OptimizedEntityResolver**:
   - Create `_navigate_using_tree()` leveraging pre-computed relationships
   - Implement `_find_container_entity()` using edge metadata
   - Use `tree.get_entity_by_live_id()` for live entity resolution
3. **Optimized Input Processing**:
   - Create `create_optimized_composite_input()` using tree navigation
   - Track dependency trees instead of complex string parsing
   - Leverage `EntityRegistry.get_stored_tree()` for immutable execution copies

#### **Phase 2: Enhanced Semantic Detection** (High Priority)
1. Implement enhanced `analyze_execution_result()` with sub-entity support
2. Add semantic classification enum and action mapping for all patterns
3. Integrate detection with existing entity primitives (detach, update_ecs_ids, etc.)
4. Handle sub-entity mutation vs detachment scenarios

#### **Phase 3: Output Unpacking** (Medium Priority)
1. Add return type signature analysis
2. Implement tuple unpacking logic with configuration
3. Handle mixed entity/non-entity tuple results

#### **Phase 4: Functional Tracking** (Medium Priority)
1. Add FunctionExecution entity and related fields
2. Implement complete execution graph tracking
3. Create audit trail and query capabilities

#### **Phase 5: Advanced Features** (Lower Priority)
1. Registry disconnection for perfect isolation
2. Performance metrics and execution tracing
3. Advanced error recovery and constraint validation

## Benefits & Design Validation

### **Consistency Benefits**

#### **Unified Execution Model**
- All patterns (borrowing, transactional, mixed) use same detection logic
- Single composite input entity regardless of complexity
- Consistent semantic classification across all scenarios

#### **Predictable Semantics**
- live_id comparison eliminates heuristic-based guesswork
- Clear rules for ambiguous cases (child extraction → detachment)
- Same entity operations (detach, update_ecs_ids) across all patterns

### **Flexibility Benefits**

#### **Configurable Unpacking**
- Per-execution control over tuple unpacking strategy
- Support for both fine-grained and atomic operation modes
- Natural extension to batch operations and complex return types

#### **Parameter Entity Pattern**
- Enables currying via cached parameter entities
- Reusable configuration patterns across multiple executions
- Complete ECS tracking of parameter provenance

### **Auditability Benefits**

#### **Complete Function Execution Tracking**
- Every function call becomes first-class entity in the system
- Full lineage from inputs through execution to outputs
- Bidirectional navigation (entity → executions, execution → entities)

#### **Sophisticated Provenance**
- Beyond data provenance (`attribute_source`) to functional relationships
- Sibling tracking for multi-entity outputs  
- Complete audit trail for complex transformation chains

### **Performance Benefits**

#### **Efficient Detection**
- O(1) live_id comparison vs complex tree analysis
- Minimal entity operations through primitive reuse
- Isolated execution prevents registry contamination

#### **Leverages Existing Infrastructure**
- Maximum reuse of proven entity system capabilities
- No duplication of tree construction, versioning, or diff logic
- Natural integration with existing registry and storage systems

### **Design Validation Through Scenarios**

The design has been validated against 12+ complex scenarios including:

- **Multi-entity unpacking** with mixed semantics (mutation + creation)
- **Tree extraction** requiring structural analysis beyond live_id comparison  
- **Cross-tree operations** with multiple dependency sources
- **Error handling** with complete audit trails on failure
- **Recursive operations** creating complex entity relationship graphs
- **Batch processing** with individual entity analysis within collections

Each scenario demonstrates that the unified approach handles the full range of execution patterns while maintaining complete audit trails and consistent semantics.

### **Comparison with Alternatives**

#### **vs. Heuristic-Based Detection**
- **Our Approach**: Deterministic live_id comparison
- **Alternative**: Complex attribute analysis and tree diffing
- **Advantage**: Eliminates false positives/negatives, simpler implementation

#### **vs. Separate Execution Modes**
- **Our Approach**: Unified composite input entity pattern
- **Alternative**: Different processing paths for different input types
- **Advantage**: Consistent provenance tracking, simpler codebase

#### **vs. No Unpacking**
- **Our Approach**: Configurable tuple unpacking with semantic detection
- **Alternative**: Always wrap multi-entity results in containers
- **Advantage**: Natural entity operations, avoids unnecessary container entities

The design represents a sophisticated yet implementable approach that maintains the full power of the entity system while extending it to handle complex function execution semantics in a consistent, auditable, and performant manner.