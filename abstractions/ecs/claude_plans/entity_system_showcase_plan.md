# Entity System Showcase Plan: Comprehensive Feature Demo

## Overview
This document outlines a comprehensive example that demonstrates all key features of the Entity system in a logical progression, building from basic concepts to advanced functionality while keeping output manageable and understandable.

## Available Features Analysis

### Core Entity System Features ✅
1. **Entity Identity Management**:
   - `ecs_id` (persistent version identifier)
   - `live_id` (runtime object identifier)  
   - `lineage_id` (tracks entity lineage across versions)
   - `root_ecs_id`/`root_live_id` (tree context)

2. **Entity Tree Construction** (`build_entity_tree()`):
   - Automatic discovery of nested entities in all containers (list, dict, tuple, set)
   - Edge classification (DIRECT, LIST, DICT, SET, TUPLE, HIERARCHICAL)
   - Ancestry path calculation
   - Circular reference detection

3. **EntityRegistry - Versioned Storage**:
   - `register_entity()` / `register_entity_tree()`
   - `get_stored_tree()` / `get_stored_entity()` (with immutable deep copies)
   - `version_entity()` (automatic change detection and versioning)
   - Multi-dimensional indexing (by root_ecs_id, lineage_id, live_id, type)

4. **Change Detection** (`find_modified_entities()`):
   - Set-based structural comparison (added/removed/moved entities)
   - Attribute-level comparison for unchanged structure
   - Path-based change propagation
   - Efficient greedy diffing

5. **Entity Lifecycle Management**:
   - `promote_to_root()` (convert sub-entity to root entity)
   - `detach()` / `attach()` (entity movement between trees)
   - `update_ecs_ids()` (versioning with lineage tracking)

6. **Attribute Source Tracking**:
   - `attribute_source` dictionary for provenance
   - Container-aware source tracking (lists/dicts maintain structured sources)
   - Automatic initialization and validation

7. **Immutable Retrieval**:
   - `get_stored_tree()` creates deep copies with new `live_id`s
   - Complete isolation between retrievals
   - `update_live_ids()` for fresh runtime contexts

8. **Tree Analysis & Visualization**:
   - `generate_mermaid_diagram()` for visual representation
   - Hierarchical relationship queries
   - Ancestry path analysis

### Missing Features (Stubs) ❌
1. **`borrow_attribute_from()`** - Critical for data composition
2. **`add_to()`** - Entity movement and attachment
3. **String-based entity addressing** - Need parser for `@uuid.field` syntax
4. **Functional get/put methods** - High-level API for entity data access

## Proposed Showcase Example: "Academic System"

### Phase 1: Basic Entity Creation and Registration
**Scenario**: Create a university academic system with students, courses, and grades.

**Entities to Create**:
```python
class Student(Entity):
    name: str
    age: int
    email: str
    
class Course(Entity):
    title: str
    code: str
    credits: int
    
class Grade(Entity):
    student: Student
    course: Course
    score: float
    semester: str
    
class AcademicRecord(Entity):
    student: Student
    grades: List[Grade] = Field(default_factory=list)
    gpa: float = 0.0
    
class University(Entity):
    name: str
    students: List[Student] = Field(default_factory=list)
    courses: List[Course] = Field(default_factory=list)
    records: List[AcademicRecord] = Field(default_factory=list)
```

**Demonstrations**:
1. **Entity Creation**: Create individual entities, show identity fields
2. **Tree Registration**: Register University entity, demonstrate automatic tree building
3. **Registry Storage**: Show multi-dimensional indexing and storage
4. **Tree Visualization**: Generate Mermaid diagram of the academic system

**Key Insights to Highlight**:
- Automatic `ecs_id`/`live_id` assignment
- `build_entity_tree()` discovering all nested entities
- EntityRegistry storage and indexing
- Visual representation of entity relationships

### Phase 2: Immutable Retrieval and Versioning
**Scenario**: Retrieve university data, make modifications, demonstrate versioning.

**Demonstrations**:
1. **Immutable Retrieval**: 
   - `EntityRegistry.get_stored_tree()` creates isolated copies
   - Show different `live_id`s but same `ecs_id`s
   - Multiple independent retrievals

2. **Change Detection**:
   - Modify student information
   - Add new grades
   - Move students between different structures
   - Use `find_modified_entities()` to detect changes

3. **Automatic Versioning**:
   - `EntityRegistry.version_entity()` creates new versions
   - Show `old_ids` tracking and lineage preservation
   - Demonstrate path-based change propagation

**Key Insights to Highlight**:
- Immutability prevents accidental side effects
- Change detection works at multiple levels (structural + attribute)
- Versioning preserves complete lineage history
- Path-based propagation ensures consistency

### Phase 3: Entity Movement and Lifecycle
**Scenario**: Transfer students between universities, handle mergers and transfers.

**Demonstrations**:
1. **Entity Detachment**:
   - Remove student from one university
   - Show `detach()` promoting to root entity
   - Registry tracking of orphaned entities

2. **Entity Attachment**:
   - Attach student to different university
   - Show `attach()` updating tree relationships
   - Proper versioning of both source and target trees

3. **Complex Restructuring**:
   - Merge two universities
   - Transfer entire academic records
   - Demonstrate tree rebuilding and relationship updates

**Key Insights to Highlight**:
- Entity movement preserves identity and lineage
- Complex restructuring handled automatically
- Registry maintains consistency across operations

### Phase 4: Attribute Source Tracking and Provenance
**Scenario**: Track data sources for compliance and auditing.

**Demonstrations**:
1. **Automatic Source Tracking**:
   - Show `attribute_source` initialization
   - Container-aware source tracking for grades lists
   - Provenance preservation across operations

2. **Manual Source Attribution**:
   - Manually set attribute sources for imported data
   - Track data lineage from external systems
   - Container source management

3. **Provenance Queries**:
   - Query where specific data originated
   - Track changes back to source entities
   - Audit trail generation

**Key Insights to Highlight**:
- Complete data provenance without manual tracking
- Container-aware source management
- Foundation for audit trails and compliance

### Phase 5: Advanced Tree Analysis
**Scenario**: Complex queries and analysis of the academic system.

**Demonstrations**:
1. **Relationship Queries**:
   - Find all students in specific courses
   - Trace academic record lineage
   - Analyze entity relationship patterns

2. **Change Impact Analysis**:
   - Modify course requirements
   - Show propagation through dependent records
   - Impact visualization

3. **Performance Analysis**:
   - Demonstrate efficient change detection
   - Show registry indexing performance
   - Tree construction optimization

**Key Insights to Highlight**:
- Rich query capabilities through entity relationships
- Efficient change propagation algorithms
- Scalable performance characteristics

## Implementation Strategy

### ✅ Step 1: Base ECS Example (`base_ecs_example.py`) - COMPLETE
- ✅ **Core Concepts** demonstrated successfully with academic system
- ✅ Created 5 entity types with clear hierarchical relationships (no circular refs)
- ✅ Demonstrated registration, retrieval, versioning, and change detection
- ✅ Generated comprehensive 31-line Mermaid diagram
- ✅ **Output Control**: Clean, structured logging with clear sections
- ✅ **Results**: 9 entities, 8 edges, 6 modified entities detected, 2 trees after versioning

### 🔨 Step 2: Borrow Attribute Implementation (`borrow_init_example.py`) - PLANNED
- 📋 **Implementation Plan Created**: `borrow_feature_implementation_plan.md`
- 🎯 Implement `borrow_attribute_from()` method with type validation and safe copying
- 🎯 Show data composition from multiple sources with provenance tracking
- 🎯 Demonstrate attribute source tracking for containers and primitives
- 🎯 **Lead into**: String parsing for `@uuid.field` syntax

### 🔨 Step 3: String Parsing Example (`string_parse_example.py`) - PLANNED  
- 📋 **Design Complete**: ECS address parser (`ecs_address_parser.py`) specified
- 🎯 Create get/put functional methods with borrowing integration
- 🎯 Show factory methods for entity creation from string dictionaries
- 🎯 Demonstrate complete data composition workflow with mixed value/address patterns

## Output Management Strategy

To avoid overwhelming logs:

1. **Structured Logging**:
   ```python
   def log_section(title: str):
       print(f"\n{'='*50}")
       print(f"  {title}")
       print(f"{'='*50}")
   
   def log_entity_summary(entity: Entity):
       print(f"Entity: {entity.__class__.__name__}")
       print(f"  ecs_id: {str(entity.ecs_id)[-8:]}...")
       print(f"  live_id: {str(entity.live_id)[-8:]}...")
   ```

2. **Selective Tree Display**:
   - Only show relevant tree sections
   - Use shortened UUIDs (last 8 characters)
   - Focus on changed entities in diffs

3. **Progressive Complexity**:
   - Start with 2-3 entities
   - Build complexity incrementally
   - Each phase introduces 1-2 new concepts

4. **Visual Aids**:
   - Mermaid diagrams for key tree states
   - Before/after comparisons
   - Clear section breaks

This approach will showcase the full power of the entity system while maintaining clarity and preventing information overload.