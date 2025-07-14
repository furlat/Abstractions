# Abstractions: Entity-Native Functional Data Processing Framework

A distributed, data-centric system that brings functional programming principles to entity management, enabling traceable data transformations across distributed systems.

## Setup

```bash
git clone https://github.com/your-org/abstractions.git
cd abstractions
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

## First steps

This framework treats data as first-class entities that flow through pure functional transformations. Every piece of data has identity, versioning, and provenance. Every transformation is a registered function with automatic tracking. Here's the minimal pattern:

```python
from abstractions.ecs.entity import Entity
from abstractions.ecs.callable_registry import CallableRegistry

# 1. Define your data as entities - the native unit of computation
class Student(Entity):
    name: str = ""
    gpa: float = 0.0

# 2. Register pure functions that transform entities  
@CallableRegistry.register("update_gpa")
def update_gpa(student: Student, new_gpa: float) -> Student:
    student.gpa = new_gpa
    return student

# 3. Execute functional transformations
student = Student(name="Alice", gpa=3.5)
student.promote_to_root()  # Enter the distributed entity space

updated = CallableRegistry.execute("update_gpa", student=student, new_gpa=3.8)
print(f"{updated.name} now has GPA {updated.gpa}")
```

Behind this simple API, the framework automatically:
- Created an immutable version when GPA changed
- Tracked data lineage through the transformation
- Established provenance (which function created which data)
- Enabled distributed access via string addressing

You can now reference this data from anywhere using its address:

```python
from abstractions.ecs.functional_api import get

# Access entity data using distributed addressing
student_name = get(f"@{updated.ecs_id}.name")
student_gpa = get(f"@{updated.ecs_id}.gpa")

# Data is addressable across process boundaries
print(f"Retrieved: {student_name} with GPA {student_gpa}")
```

## What this solves

Traditional data processing systems force you to choose between functional purity and practical data management. Pure functional languages give you immutability and composability but struggle with identity and state. Object-oriented systems give you identity and encapsulation but make functional composition difficult. Distributed systems add another layer where you must manually serialize, address, and track data across boundaries.

This framework unifies these paradigms: your data lives as **entities** with persistent identity, your logic lives as **pure functions** that transform entities, and the system automatically handles **distributed addressing**, **versioning**, and **provenance tracking**. 

Data transformations in distributed systems often follow predictable patterns: data flows through pipelines of transformations, each transformation needs to be traceable, and the results need to be addressable from anywhere. The framework handles these patterns automatically, reducing boilerplate code.

## Theoretical foundation

### Entity-native computation model

In this framework, entities are the fundamental unit of computation. Entities are pure data structures that flow through functional transformations. This separation allows for several useful patterns:

```python
# Entities are immutable snapshots in time
original = Student(name="Bob", gpa=3.0)
original.promote_to_root()

# Transformations create new versions, preserving history
@CallableRegistry.register("apply_bonus")
def apply_bonus(student: Student, bonus: float) -> Student:
    student.gpa = min(4.0, student.gpa + bonus)
    return student

updated = CallableRegistry.execute("apply_bonus", 
    student=original, bonus=0.2)

# Both versions coexist - complete history preserved
assert original.gpa == 3.0  # Original unchanged
assert updated.gpa == 3.2   # New version created
assert original.lineage_id == updated.lineage_id  # Same lineage
```

This model supports distributed processing because entities are self-contained data packets that can be serialized, transmitted, and reconstructed anywhere while maintaining their identity and relationships.

### Functional transformation registry

Functions become the unit of logic in the system. Functions are registered and managed by the framework. This registration provides metadata extraction and automatic integration with the entity lifecycle:

```python
# Functions declare their data dependencies via type hints
@CallableRegistry.register("calculate_dean_list")
def calculate_dean_list(student: Student, threshold: float = 3.7) -> DeanListResult:
    return DeanListResult(
        student_id=student.ecs_id,
        qualified=student.gpa >= threshold,
        margin=student.gpa - threshold
    )

# The framework automatically:
# 1. Creates input/output entity models from signatures
# 2. Validates types at execution time
# 3. Tracks data flow through the function
# 4. Records provenance in output entities
```

This approach creates a **distributed function registry** where any function can be invoked with any data from anywhere, with complete type safety and tracking.

### String-based distributed addressing

The framework implements a unified addressing scheme that makes all entity data accessible via string addresses. String addresses serve as the foundation for distributed data processing:

```python
# Local entity access
student = Student(name="Carol", gpa=3.9)
student.promote_to_root()

# Same data accessible via string address
student_data = {
    "name": f"@{student.ecs_id}.name",
    "gpa": f"@{student.ecs_id}.gpa"
}

# Compose new entities from distributed data sources
@CallableRegistry.register("create_transcript")
def create_transcript(name: str, gpa: float, courses: List[str]) -> Transcript:
    return Transcript(student_name=name, final_gpa=gpa, course_list=courses)

# Execute with mixed local and remote data
transcript = CallableRegistry.execute("create_transcript",
    name=f"@{student.ecs_id}.name",      # From entity
    gpa=f"@{student.ecs_id}.gpa",        # From entity  
    courses=["Math", "Physics", "CS"]     # Direct data
)
```

This addressing provides **location transparency** - your functions don't need to know where data lives, just how to address it. The framework handles resolution, whether the entity is in local memory, a remote cache, or a distributed store.

### Automatic provenance and lineage tracking

Every transformation is recorded in the entity graph, creating a complete audit trail of how data was derived. Provenance tracking is built into the computation model:

```python
# Create a complex transformation pipeline
@CallableRegistry.register("normalize_grades")
def normalize_grades(cohort: List[Student]) -> List[Student]:
    avg_gpa = sum(s.gpa for s in cohort) / len(cohort)
    return [
        Student(name=s.name, gpa=s.gpa / avg_gpa * 3.0)
        for s in cohort
    ]

students = [Student(name=f"S{i}", gpa=3.0+i*0.2) for i in range(5)]
for s in students:
    s.promote_to_root()

normalized = CallableRegistry.execute("normalize_grades", cohort=students)

# Each output entity knows its provenance
for norm in normalized:
    execution = EntityRegistry.get_function_execution(norm.ecs_id)
    print(f"{norm.name} was created by {execution.function_name}")
    print(f"From inputs: {execution.input_entity_ids}")
```

This provenance tracking supports **data lineage queries**, **reproducible computations**, and **debugging of data flows** across distributed systems.

### Multi-entity transformations and unpacking

The framework natively handles functions that produce multiple entities, automatically managing their relationships and distribution:

```python
@CallableRegistry.register("analyze_performance")
def analyze_performance(student: Student) -> Tuple[Assessment, Recommendation]:
    assessment = Assessment(
        student_id=student.ecs_id,
        performance_level="high" if student.gpa > 3.5 else "standard"
    )
    recommendation = Recommendation(
        action="advanced_placement" if student.gpa > 3.5 else "standard_track",
        reasoning=f"Based on GPA of {student.gpa}"
    )
    return assessment, recommendation

# Automatic unpacking and relationship tracking
assessment, rec = CallableRegistry.execute("analyze_performance", student=student)

# Entities know they're siblings from the same computation
print(assessment.sibling_output_entities)  # [rec.ecs_id]
print(rec.sibling_output_entities)         # [assessment.ecs_id]
```

This enables **complex data flows** where single computations produce multiple related outputs that may be consumed by different downstream systems.

### Distributed execution patterns

The framework supports multiple execution patterns optimized for different distributed scenarios:

```python
# Pattern 1: Direct entity transformation (local computation)
result = CallableRegistry.execute("update_gpa", student=student, new_gpa=3.9)

# Pattern 2: Address-based transformation (remote data)
result = CallableRegistry.execute("update_gpa", 
    student=f"@{remote_student_id}",  # Fetched from distributed store
    new_gpa=3.9
)

# Pattern 3: Batch transformation (parallel processing)
results = CallableRegistry.execute_batch([
    {"func_name": "update_gpa", "student": s, "new_gpa": s.gpa + 0.1}
    for s in students
])

# Pattern 4: Composite transformation (data from multiple sources)
analysis = CallableRegistry.execute("cross_reference_analysis",
    student=f"@{student_id}",          # From service A
    transcript=f"@{transcript_id}",     # From service B  
    recommendations=f"@{recs_id}"       # From service C
)
```

Each pattern maintains the same guarantees of immutability, versioning, and provenance while optimizing for different distribution scenarios.

### Async and concurrent execution without interference

The framework's immutable entity model and automatic versioning enable safe concurrent and async execution without locks or synchronization. Multiple functions can process the same entities simultaneously without interference:

```python
# Register both sync and async functions
@CallableRegistry.register("analyze_grades")
def analyze_grades(student: Student, grades: List[float]) -> AnalysisResult:
    """Synchronous grade analysis"""
    return AnalysisResult(avg=sum(grades)/len(grades))

@CallableRegistry.register("analyze_grades_async")
async def analyze_grades_async(student: Student, grades: List[float]) -> AnalysisResult:
    """Async grade analysis with external API calls"""
    await asyncio.sleep(0.1)  # Simulate API call
    return AnalysisResult(avg=sum(grades)/len(grades))

# Execute concurrently without interference
batch_results = await CallableRegistry.execute_batch([
    {
        "func_name": "analyze_grades",
        "student": f"@{student_id}",
        "grades": [3.8, 3.9, 3.7]
    },
    {
        "func_name": "analyze_grades_async", 
        "student": f"@{student_id}",  # Same student, no problem!
        "grades": [3.8, 3.9, 3.7, 4.0]
    }
])

# Each execution:
# 1. Gets its own immutable copy of input entities
# 2. Creates new output entities with unique IDs
# 3. Records its own provenance chain
# 4. Never interferes with other executions
```

This concurrency model scales naturally to distributed systems where different nodes process the same data. Since entities are immutable and every transformation creates new versions, there's no shared mutable state to coordinate. The framework handles all the complexity of maintaining consistency and tracking lineage across concurrent executions.

## Core concepts for distributed data processing

### Entity as distributed data unit

Entities in this framework are designed for distribution. Each entity is a self-contained data unit with:
- **Globally unique identity** (ecs_id) that works across system boundaries
- **Immutable state** that can be safely cached and replicated
- **Complete metadata** for versioning, lineage, and provenance
- **Efficient serialization** for network transport

### Function as distributed computation unit  

Functions are the unit of computation that can be deployed and executed anywhere:
- **Location independent** - functions can run wherever the data is
- **Self-describing** - type signatures enable automatic validation
- **Composable** - functions can be chained into complex pipelines
- **Traceable** - every execution is recorded in the entity graph

### Address as distributed reference

String addresses provide a universal way to reference data across systems:
- **Human readable** - `@uuid.field.subfield` is self-documenting  
- **Network portable** - strings work across any transport
- **Lazy resolution** - addresses are resolved only when needed
- **Access control ready** - addresses can be filtered by permissions

## Implementation architecture for distributed systems

The framework is architected to support distributed deployment patterns:

**Entity Layer**: Provides persistent identity and versioning suitable for distributed stores. Entities can be serialized to any format and reconstructed with full fidelity.

**Function Registry**: Acts as a distributed function catalog where functions can be discovered, invoked remotely, and composed into workflows.

**Address Resolution**: Implements a pluggable resolver architecture that can fetch entities from local memory, remote caches, databases, or microservices.

**Execution Engine**: Supports multiple execution strategies from local in-process to distributed map-reduce patterns while maintaining the same API.

## Real-world example: Distributed grade processing pipeline

```python
from abstractions.ecs import Entity, CallableRegistry
from typing import List, Dict, Tuple

# Define entities for a distributed gradebook system
class Assignment(Entity):
    name: str = ""
    points_possible: float = 100.0
    weight: float = 1.0

class Submission(Entity):
    student_id: str = ""
    assignment_id: str = ""  
    points_earned: float = 0.0
    submitted_at: datetime = None

class GradeReport(Entity):
    student_id: str = ""
    course_id: str = ""
    assignments: Dict[str, float] = Field(default_factory=dict)
    weighted_average: float = 0.0
    letter_grade: str = ""

# Register distributed processing functions
@CallableRegistry.register("calculate_weighted_grade")
def calculate_weighted_grade(
    submissions: List[Submission],
    assignments: List[Assignment]
) -> GradeReport:
    """Calculate grades with proper weighting"""
    
    assignment_map = {a.ecs_id: a for a in assignments}
    grade_map = {}
    total_weight = 0
    weighted_sum = 0
    
    for sub in submissions:
        assignment = assignment_map.get(sub.assignment_id)
        if assignment:
            percentage = sub.points_earned / assignment.points_possible
            grade_map[assignment.name] = percentage * 100
            weighted_sum += percentage * assignment.weight
            total_weight += assignment.weight
    
    weighted_avg = (weighted_sum / total_weight * 100) if total_weight > 0 else 0
    
    return GradeReport(
        student_id=submissions[0].student_id if submissions else "",
        assignments=grade_map,
        weighted_average=weighted_avg,
        letter_grade=_calculate_letter_grade(weighted_avg)
    )

# Execute across distributed data
report = CallableRegistry.execute("calculate_weighted_grade",
    # Submissions might come from one service
    submissions=f"@{submission_collection_id}.items",
    # Assignments from another service
    assignments=f"@{course_catalog_id}.assignments"  
)

# Result is automatically versioned and addressable
print(f"Grade report created: @{report.ecs_id}")
print(f"Student average: {report.weighted_average}%")
print(f"Letter grade: {report.letter_grade}")

# Other services can now reference this computed data
notification_service.send(
    template="grade_report",
    student=f"@{report.ecs_id}.student_id",
    grade=f"@{report.ecs_id}.letter_grade"
)
```

## Why this approach scales

This framework scales well with distributed systems:

1. **Data is naturally distributed** - The framework embraces this rather than hiding it
2. **Computation follows data** - Functions can execute wherever data lives  
3. **Everything needs tracking** - Built-in provenance eliminates custom audit code
4. **Immutability simplifies distribution** - No distributed state synchronization problems
5. **Addresses enable loose coupling** - Services can share data without tight integration

By making these distributed patterns first-class concepts in the framework, you get the benefits of functional programming (immutability, composability, testability) with the pragmatic needs of distributed systems (identity, addressing, versioning) in a single coherent model.

The result is a framework where you can start with a simple single-process application and scale to a distributed system without changing your core logic - just your deployment topology. Your functions remain pure, your data remains traceable, and your system remains comprehensible even as it grows.