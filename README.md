# Abstractions

Entity-Component-System with function-based systems and automatic entity lifecycle management.

## Setup

```bash
git clone https://github.com/your-org/abstractions.git
cd abstractions
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

## First steps

The system has three main components: entities (your data structures), functions (your logic), and automatic management (versioning, relationships, audit trails). Here's the minimal pattern:

```python
from abstractions.ecs.entity import Entity
from abstractions.ecs.callable_registry import CallableRegistry

# 1. Define your data as entities
class Student(Entity):
    name: str = ""
    gpa: float = 0.0

# 2. Register functions that operate on entities  
@CallableRegistry.register("update_gpa")
def update_gpa(student: Student, new_gpa: float) -> Student:
    student.gpa = new_gpa
    return student

# 3. Use the system
student = Student(name="Alice", gpa=3.5)
student.promote_to_root()  # Register with entity system

updated = CallableRegistry.execute("update_gpa", student=student, new_gpa=3.8)
print(f"{updated.name} now has GPA {updated.gpa}")
```

The system automatically handled entity storage, created a new version when the GPA changed, tracked that the update came from the `update_gpa` function, and maintained the relationship between the original and updated entities.

To see what happened, you can check the entity registry:

```python
from abstractions.ecs.entity import EntityRegistry

# See all entities in the system
print(f"Total entities: {len(EntityRegistry.live_id_registry)}")

# Get the version history for this student
lineage = EntityRegistry.lineage_registry[student.lineage_id]
print(f"Student has {len(lineage)} versions")
```

## What this solves

Traditional Entity-Component-System implementations force you to build most of the ECS framework yourself. You define entities and components, but then you have to manually register components, write system execution logic, manage entity-component relationships, and build data access patterns between systems. Most ECS libraries give you the data structures but leave the hard problems unsolved.

This implementation takes a different approach: your functions become systems automatically, and the framework handles entity lifecycle, relationship management, and data flow. Instead of building an ECS framework, you write your domain logic and get ECS capabilities automatically.

The core insight is that most data processing can be modeled as functions that transform entities, and these transformations can be tracked automatically to build complete audit trails and provenance graphs. Rather than manually managing which systems operate on which components, you write functions with type hints and let the system figure out data dependencies and execution patterns.

## Theoretical foundation

### Entity identity and versioning

Every entity has multiple types of identity that serve different purposes. The `ecs_id` is the persistent identity that survives across versions - when you modify an entity, it gets a new `ecs_id` but maintains the same `lineage_id` to track version history. The `live_id` is the runtime identity used for in-memory references and object tracking.

```python
student = Student(name="Bob", gpa=3.0)
original_ecs_id = student.ecs_id
original_lineage = student.lineage_id

student.gpa = 3.5
EntityRegistry.version_entity(student)

# New persistent identity, same lineage
assert student.ecs_id != original_ecs_id
assert student.lineage_id == original_lineage
```

This multi-layered identity system enables sophisticated versioning where you can track how entities evolve over time while maintaining referential integrity. When a function modifies an entity, the system automatically detects the change, assigns new IDs, and preserves the version lineage. This creates a Git-like version history for your data structures.

### Function-based systems

Instead of writing traditional ECS systems that iterate over entities with specific components, you write regular Python functions with type hints. The callable registry analyzes your function signatures and automatically creates the necessary input and output entity models using Pydantic's `create_model` functionality.

```python
# Traditional ECS: write system boilerplate
class GradeSystem:
    def update(self, entities_with_grade_component):
        for entity in entities_with_grade_component:
            # ... manual iteration and component access

# This ECS: write domain logic
@CallableRegistry.register("apply_grade_curve")
def apply_grade_curve(student: Student, curve_factor: float) -> Student:
    student.gpa = min(4.0, student.gpa * curve_factor)
    return student
```

This approach eliminates the impedance mismatch between your domain logic and the ECS framework. You write functions that make sense for your problem domain, and the system automatically integrates them into the entity lifecycle. Functions become first-class citizens in the entity graph, with complete tracking of inputs, outputs, and semantic classification.

### Semantic detection through object identity

One of the key innovations is using Python's object identity system to automatically classify function semantics. When a function executes, the system tracks the object identity of inputs and outputs to determine whether the function performed a mutation (modifying an existing entity), creation (producing a new entity), or detachment (extracting a child entity from a parent).

```python
@CallableRegistry.register("mutate_student")
def mutate_student(student: Student) -> Student:
    student.gpa += 0.1  # Modifies input object
    return student      # Returns same object
# Detected as: MUTATION (same object identity)

@CallableRegistry.register("copy_student")  
def copy_student(student: Student) -> Student:
    return Student(name=student.name, gpa=student.gpa)
# Detected as: CREATION (new object, new ecs_id)

@CallableRegistry.register("extract_profile")
def extract_profile(record: AcademicRecord) -> StudentProfile:
    return record.student_profile  # Returns existing child
# Detected as: DETACHMENT (different object, existing ecs_id)
```

This semantic classification happens automatically using `id()` comparisons rather than fragile heuristics. If the output entity has the same object identity as an input entity, it's a mutation. If the output has the same `ecs_id` as an entity in the input graph but different object identity, it's a detachment. Otherwise, it's creation. This deterministic approach provides reliable semantic information for audit trails.

### String-based entity addressing

The system implements a string-based addressing scheme that lets you reference any field in any entity using `@uuid.field.subfield` syntax. This eliminates the need to pass entity references around manually and enables dynamic data composition.

```python
# Instead of manual object passing
result = CallableRegistry.execute("analyze_performance", {
    "student_name": f"@{student.ecs_id}.name",
    "current_gpa": f"@{student.ecs_id}.gpa", 
    "course_credits": f"@{course.ecs_id}.credits"
})

# Navigate nested structures
profile_name = f"@{record.ecs_id}.student_profile.name"
first_grade = f"@{student.ecs_id}.grades.0"  # List index
course_title = f"@{enrollment.ecs_id}.course.title"  # Entity reference
```

The address parser can navigate complex nested structures, including lists, dictionaries, and entity hierarchies. When you use an address in a function call, the system automatically resolves it to the actual value and tracks the dependency relationship. This creates a declarative way to specify data dependencies rather than imperative object passing.

### Automatic graph construction and change detection

When you register an entity, the system automatically builds a complete graph of all entity relationships by introspecting Pydantic field types and traversing object references. This graph captures the hierarchical structure of your data and enables sophisticated change detection algorithms.

```python
class Course(Entity):
    title: str = ""

class StudentRecord(Entity):
    student: Student = None
    courses: List[Course] = Field(default_factory=list)

record = StudentRecord(
    student=Student(name="Alice"), 
    courses=[Course(title="Math"), Course(title="Physics")]
)
record.promote_to_root()

# System automatically discovered:
tree = build_entity_tree(record)
print(f"Found {tree.node_count} entities")  # 4: record + student + 2 courses
print(f"Found {tree.edge_count} relationships")  # 3: record->student, record->course1, record->course2
```

The change detection system uses set-based comparison of graph structures to identify what changed between versions. Instead of comparing individual field values, it compares the structural differences between entity graphs, which is more efficient and captures relationship changes that field-level comparison would miss.

### Multi-entity function returns with automatic unpacking

Functions can return multiple entities in various container types (lists, tuples, dictionaries), and the system automatically analyzes the return type annotations to determine the appropriate unpacking strategy. This enables functions to produce complex outputs while maintaining proper entity relationships and sibling tracking.

```python
@CallableRegistry.register("create_student_cohort")
def create_student_cohort(names: List[str]) -> List[Student]:
    return [Student(name=name) for name in names]
# Returns: List of students with sibling relationships

@CallableRegistry.register("analyze_student") 
def analyze_student(student: Student) -> Tuple[Student, Recommendation]:
    updated = Student(name=student.name, gpa=student.gpa + 0.1)
    rec = Recommendation(action="study_abroad")
    return updated, rec
# Returns: Two entities unpacked automatically

students = CallableRegistry.execute("create_student_cohort", names=["A", "B", "C"])
updated, recommendation = CallableRegistry.execute("analyze_student", student=students[0])
```

The unpacking system preserves the semantic meaning of different container types. A `List[Entity]` return indicates a collection of similar entities that should be treated as siblings. A `Tuple[Entity, Entity]` indicates related but distinct entities. A mixed tuple like `Tuple[Entity, List[Recommendation]]` gets wrapped in a container entity that preserves the relationship structure.

## Core concepts

### Entity lifecycle

Entities progress through a well-defined lifecycle managed automatically by the system. When you create an entity, it's initially an orphan with no relationships. Calling `promote_to_root()` registers it as a root entity in the system, giving it persistent storage and versioning capabilities.

Entities can be attached to and detached from other entities, with the system automatically managing the relationship graph and ID updates. When you detach an entity from its parent, it's automatically promoted to root status. When you attach an entity to a new parent, its IDs are updated to reflect the new relationship.

### Function registration and execution

Functions are registered using the `@CallableRegistry.register()` decorator, which analyzes the function signature and creates the necessary entity models. The system supports multiple execution patterns based on the input types and configuration.

For simple entity-to-entity transformations, the system uses a transactional approach where input entities are copied, the function executes on the copies, and the results are processed with semantic detection. For address-based references, it uses a borrowing approach where data is composed from multiple entities into a temporary input entity.

### Configuration management

Configuration parameters are handled through ConfigEntity, which extends the base Entity class with special semantics. ConfigEntity instances are treated as persistent configuration that should be tracked and versioned like any other entity, but they follow different patterns for creation and management.

When you pass primitive parameters to a function that expects a ConfigEntity, the system automatically creates the appropriate ConfigEntity subclass and populates it with your parameters. This enables flexible configuration management while maintaining type safety and audit trails.

## Implementation architecture

The codebase is organized around several key modules that each handle specific aspects of the system. The entity module provides the core data structures and relationship management. The callable registry handles function registration and execution with multiple strategies for different use cases.

The address parser implements the string-based field resolution with support for complex navigation patterns. The return type analyzer examines function signatures to determine appropriate unpacking strategies. The entity unpacker handles the complex logic of converting function outputs into properly structured entity collections.

All modules follow a clean import hierarchy with no circular dependencies. Lower-level modules provide data structures and algorithms, while higher-level modules orchestrate the overall functionality. This creates a maintainable architecture where each component has clear responsibilities.

## Example usage

```python
from abstractions.ecs.entity import Entity
from abstractions.ecs.callable_registry import CallableRegistry

class Student(Entity):
    name: str = ""
    age: int = 0
    gpa: float = 0.0

@CallableRegistry.register("calculate_honors_eligibility")
def calculate_honors_eligibility(student: Student, min_gpa: float = 3.5) -> bool:
    return student.gpa >= min_gpa

student = Student(name="Alice", age=20, gpa=3.8)
student.promote_to_root()

is_eligible = CallableRegistry.execute("calculate_honors_eligibility", 
    student=student, min_gpa=3.7)
```

This simple example demonstrates the core pattern: define entities as Pydantic models, register functions with type hints, and execute them through the callable registry. The system automatically handles entity storage, versioning, provenance tracking, and audit trails.

## Why this approach works

The key insight is that most data processing follows predictable patterns that can be automated. Functions transform data in well-defined ways, entities have clear identity and lifecycle requirements, and relationships between data elements can be tracked automatically.

By encoding these patterns into the framework, you eliminate the repetitive work of entity management while getting sophisticated capabilities like versioning, audit trails, and semantic detection. The result is a system where you can focus on your domain logic while getting enterprise-grade data management automatically.

The theoretical foundation is sound because it builds on proven concepts from functional programming (immutable data with versioning), object-oriented design (entity relationships and lifecycle), and type systems (automatic model generation from signatures). The combination creates a practical system that scales from simple scripts to complex data processing pipelines.