# Abstractions: Entity-Native Functional Data Processing Framework

A distributed, data-centric system that brings functional programming principles to entity management, enabling traceable data transformations across distributed systems.

## Setup

```bash
git clone -b maybe_cursed_who_knows https://github.com/furlat/Abstractions.git
cd Abstractions
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
- Emitted events that track the transformation (you can observe these if needed)

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

Another challenge is observability - when transformations happen, you often can't see what triggered what or how changes flow through your system.

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

# Execute the transformation
bonus_result = CallableRegistry.execute("apply_bonus", student=original, bonus=0.2)
updated = bonus_result if not isinstance(bonus_result, list) else bonus_result[0]

# Both versions coexist - complete history preserved
assert original.gpa == 3.0  # Original unchanged
assert updated.gpa == 3.2   # New version created
assert original.lineage_id == updated.lineage_id  # Same lineage
```

This model supports distributed processing because entities are self-contained data packets that can be serialized, transmitted, and reconstructed anywhere while maintaining their identity and relationships.

### Functional transformation registry

Functions become the unit of logic in the system. Functions are registered and managed by the framework. This registration provides metadata extraction and automatic integration with the entity lifecycle:

```python
class DeanListResult(Entity):
    student_id: str = ""
    qualified: bool = False
    margin: float = 0.0

# Functions declare their data dependencies via type hints
@CallableRegistry.register("calculate_dean_list")
def calculate_dean_list(student: Student, threshold: float = 3.7) -> DeanListResult:
    return DeanListResult(
        student_id=student.ecs_id,
        qualified=student.gpa >= threshold,
        margin=student.gpa - threshold
    )

# Execute the dean list calculation
student = Student(name="Alice", gpa=3.8)
student.promote_to_root()
dean_result = CallableRegistry.execute("calculate_dean_list", student=student, threshold=3.7)
dean_list_result = dean_result if not isinstance(dean_result, list) else dean_result[0]

print(f"Qualified: {dean_list_result.qualified}, Margin: {dean_list_result.margin}")

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
from abstractions.ecs.functional_api import get

# Local entity access
student = Student(name="Carol", gpa=3.9)
student.promote_to_root()

# Same data accessible via string address
student_name = get(f"@{student.ecs_id}.name")
student_gpa = get(f"@{student.ecs_id}.gpa")

print(f"Retrieved: {student_name} with GPA {student_gpa}")

class Course(Entity):
    name: str = ""
    credits: int = 0
    grade: str = ""

# Compose new entities from distributed data sources
@CallableRegistry.register("create_transcript")
def create_transcript(name: str, gpa: float, courses: List[str]) -> Course:
    return Course(name=f"Transcript for {name}", credits=len(courses), grade=f"GPA: {gpa}")

# Execute with mixed local and remote data
transcript = CallableRegistry.execute("create_transcript",
    name=f"@{student.ecs_id}.name",      # From entity
    gpa=f"@{student.ecs_id}.gpa",        # From entity  
    courses=["Math", "Physics", "CS"]     # Direct data
)
transcript_result = transcript if not isinstance(transcript, list) else transcript[0]
print(f"Created: {transcript_result.name}")
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

# Execute the normalization
normalized_result = CallableRegistry.execute("normalize_grades", cohort=students)
normalized = normalized_result if isinstance(normalized_result, list) else [normalized_result]

print(f"Normalized {len(normalized)} students")

# Each output entity tracks its lineage and versioning
for i, norm in enumerate(normalized[:3]):  # Show first 3
    print(f"{norm.name} was created with lineage {norm.lineage_id}")
    print(f"Entity ID: {norm.ecs_id}, derived from original student data")
```

This provenance tracking supports **data lineage queries**, **reproducible computations**, and **debugging of data flows** across distributed systems.

### Event-driven observation

The framework emits events when entities change or functions execute. These events contain only UUID references and basic metadata - they don't duplicate your data. You can use them to observe what's happening in your system:

```python
from abstractions.events.events import Event, CreatedEvent, on, emit

# Define custom event types
class StudentCreatedEvent(CreatedEvent[Student]):
    type: str = "student.created"

# Event handlers using the correct patterns
@on(StudentCreatedEvent)
async def log_student_creation(event: StudentCreatedEvent):
    print(f"Student created: {event.subject_id}")

# Pattern-based event handler
@on(pattern="student.*")
def handle_all_student_events(event: Event):
    print(f"Student event: {event.type}")

# Predicate-based event handler
@on(predicate=lambda e: hasattr(e, 'subject_id') and e.subject_id is not None)
async def track_all_entities(event: Event):
    print(f"Entity event: {event.type} for {event.subject_id}")

# The events contain references, not data
# This lets you track what's happening without affecting performance
```

Events work well for debugging, monitoring, and building reactive systems. They're designed to be lightweight - you can ignore them entirely if you don't need them.

### Multi-entity transformations and unpacking

The framework natively handles functions that produce multiple entities, automatically managing their relationships and distribution:

```python
from typing import Tuple
from pydantic import Field

class Assessment(Entity):
    student_id: str = Field(default="")
    performance_level: str = Field(default="")
    gpa_score: float = Field(default=0.0)

class Recommendation(Entity):
    student_id: str = Field(default="")
    action: str = Field(default="")
    reasoning: str = Field(default="")

@CallableRegistry.register("analyze_performance")
def analyze_performance(student: Student) -> Tuple[Assessment, Recommendation]:
    assessment = Assessment(
        student_id=str(student.ecs_id),
        performance_level="high" if student.gpa > 3.5 else "standard",
        gpa_score=student.gpa
    )
    recommendation = Recommendation(
        student_id=str(student.ecs_id),
        action="advanced_placement" if student.gpa > 3.5 else "standard_track",
        reasoning=f"Based on GPA of {student.gpa}"
    )
    return assessment, recommendation

# Automatic unpacking and relationship tracking
student = Student(name="Alice", gpa=3.8)
student.promote_to_root()

result = CallableRegistry.execute("analyze_performance", student=student)

# Handle Union[Entity, List[Entity]] return type
if isinstance(result, list):
    assessment, recommendation = result[0], result[1]
else:
    assessment, recommendation = result

print(f"Assessment: {assessment.performance_level}")
print(f"Recommendation: {recommendation.action}")

# Entities know they're siblings from the same computation
if hasattr(assessment, 'sibling_output_entities'):
    print(f"Assessment siblings: {assessment.sibling_output_entities}")
if hasattr(recommendation, 'sibling_output_entities'):
    print(f"Recommendation siblings: {recommendation.sibling_output_entities}")
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

# Pattern 3: Async transformation (concurrent processing)
results = await asyncio.gather(*[
    CallableRegistry.aexecute("update_gpa", student=s, new_gpa=s.gpa + 0.1)
    for s in students
])

# Pattern 4: Composite transformation (data from multiple sources)
analysis = await CallableRegistry.aexecute("cross_reference_analysis",
    student=f"@{student_id}",          # From service A
    transcript=f"@{transcript_id}",     # From service B  
    recommendations=f"@{recs_id}"       # From service C
)
```

Each pattern maintains the same guarantees of immutability, versioning, and provenance while optimizing for different distribution scenarios.

### Async and concurrent execution without interference

The framework's immutable entity model and automatic versioning enable safe concurrent and async execution without locks or synchronization. Multiple functions can process the same entities simultaneously without interference:

```python
class AnalysisResult(Entity):
    student_id: str = ""
    avg: float = 0.0
    analysis_type: str = ""

# Register both sync and async functions
@CallableRegistry.register("analyze_grades")
def analyze_grades(student: Student, grades: List[float]) -> AnalysisResult:
    """Synchronous grade analysis"""
    return AnalysisResult(
        student_id=str(student.ecs_id),
        avg=sum(grades)/len(grades),
        analysis_type="sync"
    )

@CallableRegistry.register("analyze_grades_async")
async def analyze_grades_async(student: Student, grades: List[float]) -> AnalysisResult:
    """Async grade analysis with external API calls"""
    await asyncio.sleep(0.1)  # Simulate API call
    return AnalysisResult(
        student_id=str(student.ecs_id),
        avg=sum(grades)/len(grades),
        analysis_type="async"
    )

# Execute concurrently without interference
student = Student(name="TestStudent", gpa=3.5)
student.promote_to_root()

batch_results = await asyncio.gather(
    CallableRegistry.aexecute("analyze_grades",
        student=f"@{student.ecs_id}",
        grades=[3.8, 3.9, 3.7]
    ),
    CallableRegistry.aexecute("analyze_grades_async", 
        student=f"@{student.ecs_id}",  # Same student, no problem!
        grades=[3.8, 3.9, 3.7, 4.0]
    )
)

# Results processed concurrently without interference
for i, result in enumerate(batch_results):
    if isinstance(result, list):
        result = result[0] if result else None
    print(f"Result {i+1}: avg={result.avg:.2f}, type={result.analysis_type}")

# Each execution:
# 1. Gets its own immutable copy of input entities
# 2. Creates new output entities with unique IDs
# 3. Records its own provenance chain
# 4. Never interferes with other executions
```

This concurrency model scales naturally to distributed systems where different nodes process the same data. Since entities are immutable and every transformation creates new versions, there's no shared mutable state to coordinate. The framework handles all the complexity of maintaining consistency and tracking lineage across concurrent executions.

### Multi-step reactive cascades

You can combine async execution with event handlers to create cascading computations that work across distributed systems. Here's a simple example that processes student data in multiple steps:

```python
from abstractions.events.events import Event, CreatedEvent, on, emit
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class ProcessedStudent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    student_id: UUID
    processed_gpa: float = 0.0
    processing_notes: str = ""
    status: str = "processed"

class BatchReport(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    batch_id: str
    student_count: int = 0
    average_gpa: float = 0.0
    batch_status: str = "completed"

class StudentProcessedEvent(CreatedEvent[ProcessedStudent]):
    type: str = "student.processed"

class BatchCompletedEvent(CreatedEvent[BatchReport]):
    type: str = "batch.completed"

# Global collections for event-driven batching
processed_students: List[UUID] = []

# Step 1: Process individual students
async def process_student(student: Student) -> ProcessedStudent:
    # Some processing work
    processed = ProcessedStudent(
        student_id=student.id,
        processed_gpa=student.gpa * 1.1,  # 10% boost
        processing_notes=f"Processed {student.name} with GPA boost",
        status="processed"
    )
    
    # Emit event to trigger cascade
    await emit(StudentProcessedEvent(
        subject_type=ProcessedStudent,
        subject_id=processed.id,
        created_id=processed.id
    ))
    
    return processed

# Step 2: Event handler that automatically collects processed students
@on(StudentProcessedEvent)
async def collect_processed_students(event: StudentProcessedEvent):
    if event.subject_id is not None:
        processed_students.append(event.subject_id)
        
        # When we have enough students, trigger batch analysis
        if len(processed_students) >= 3:
            batch = processed_students[:3]
            processed_students.clear()
            await trigger_batch_analysis(batch)

async def trigger_batch_analysis(batch_students):
    """Process a batch of students."""
    print(f"Processing batch of {len(batch_students)} students...")
    
    # Create batch report
    batch_report = BatchReport(
        batch_id=f"BATCH_{len(batch_students)}",
        student_count=len(batch_students),
        average_gpa=3.6,  # Simplified calculation
        batch_status="completed"
    )
    
    # Emit batch completion event
    await emit(BatchCompletedEvent(
        subject_type=BatchReport,
        subject_id=batch_report.id,
        created_id=batch_report.id
    ))

# Usage: Just process students, everything else happens automatically
students = [Student(name=f"Student_{i}", gpa=3.0 + i*0.1) for i in range(7)]
for student in students:
    await process_student(student)

# Step 3: Analyze batches and create reports
@CallableRegistry.register("analyze_batch")
async def analyze_batch(student_ids: List[str]) -> BatchReport:
    # Fetch the processed students
    students = [EntityRegistry.get_stored_entity(id) for id in student_ids]
    
    # Simple map-reduce pattern
    avg_gpa = sum(s.processed_gpa for s in students) / len(students)
    
    return BatchReport(
        batch_size=len(students),
        average_gpa=avg_gpa,
        student_ids=student_ids
    )

# Step 4: When reports are created, trigger final aggregation
reports = []

@on(lambda event: event.type == "created" and event.subject_type == BatchReport)
async def aggregate_reports(event):
    reports.append(event.subject_id)
    
    # Every 3 reports, create a summary
    if len(reports) >= 3:
        batch_reports = reports[:3]
        reports.clear()
        await CallableRegistry.aexecute("create_summary", report_ids=batch_reports)

# Usage: Just process students, everything else happens automatically
for student in students:
    await CallableRegistry.aexecute("process_student", student=student)

# The system automatically:
# 1. Processes each student individually (async)
# 2. Collects processed students into batches of 10
# 3. Analyzes each batch to create reports
# 4. Aggregates reports into summaries
# This creates a simple map-reduce pipeline through events
```

This pattern creates emergent behavior where the system automatically organizes work into batches and aggregates results without central coordination. Each step only knows about its immediate inputs and outputs, but the event system coordinates the overall flow.

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

### Event as optional signal

The framework emits events to signal when things happen:
- **UUID-based** - events contain entity IDs, not copies of data
- **Hierarchical** - events can be grouped by operation
- **Optional** - you can ignore events entirely if you don't need them
- **Reactive** - events can trigger other functions automatically

## Implementation architecture for distributed systems

The framework is architected to support distributed deployment patterns:

**Entity Layer**: Provides persistent identity and versioning suitable for distributed stores. Entities can be serialized to any format and reconstructed with full fidelity.

**Function Registry**: Acts as a distributed function catalog where functions can be discovered, invoked remotely, and composed into workflows.

**Address Resolution**: Implements a pluggable resolver architecture that can fetch entities from local memory, remote caches, databases, or microservices.

**Execution Engine**: Supports multiple execution strategies from local in-process to distributed map-reduce patterns while maintaining the same API.

## Validated examples and patterns

The framework includes comprehensive examples demonstrating real-world usage patterns:

- **[01_basic_entity_transformation.py](examples/readme_examples/01_basic_entity_transformation.py)** - Core entity operations and transformations (sync + async)
- **[02_distributed_addressing.py](examples/readme_examples/02_distributed_addressing.py)** - String-based entity addressing across system boundaries (sync + async)  
- **[03_multi_entity_transformations.py](examples/readme_examples/03_multi_entity_transformations.py)** - Tuple unpacking and sibling relationships (sync + async)
- **[04_distributed_grade_processing.py](examples/readme_examples/04_distributed_grade_processing.py)** - Complex multi-stage data pipelines (sync + async)
- **[05_reactive_cascades.py](examples/readme_examples/05_reactive_cascades.py)** - Event-driven reactive workflows (async only)

Each example includes comprehensive test suites validating the documented behavior and can be run directly to see the framework in action.

## Real-world example: Distributed grade processing pipeline

```python
from abstractions.ecs import Entity, CallableRegistry
from typing import List, Dict, Tuple
from datetime import datetime
from pydantic import Field

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
        letter_grade=calculate_letter_grade(weighted_avg)
    )

def calculate_letter_grade(weighted_avg: float) -> str:
    """Helper function to calculate letter grade from weighted average."""
    if weighted_avg >= 90:
        return "A"
    elif weighted_avg >= 80:
        return "B"
    elif weighted_avg >= 70:
        return "C"
    elif weighted_avg >= 60:
        return "D"
    else:
        return "F"

# Execute across distributed data (use aexecute for async)
report = await CallableRegistry.aexecute("calculate_weighted_grade",
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

# React to new grade reports (optional)
from abstractions.events.events import on

@on(lambda event: event.type == "created" and event.subject_type == GradeReport)
async def handle_new_grade_report(event):
    # Send notification when grades are calculated
    await send_notification(event.subject_id)

# The rest of your code stays the same
# Events are just a way to react to changes if you need to
```

## Why this approach scales

This framework scales well with distributed systems:

1. **Data is naturally distributed** - The framework embraces this rather than hiding it
2. **Computation follows data** - Functions can execute wherever data lives
3. **Everything needs tracking** - Built-in provenance eliminates custom audit code
4. **Immutability simplifies distribution** - No distributed state synchronization problems
5. **Addresses enable loose coupling** - Services can share data without tight integration
6. **Observability helps understanding** - Events help you understand what's happening as systems grow

By making these distributed patterns first-class concepts in the framework, you get the benefits of functional programming (immutability, composability, testability) with the pragmatic needs of distributed systems (identity, addressing, versioning) in a single coherent model.

The result is a framework where you can start with a simple single-process application and scale to a distributed system without changing your core logic - just your deployment topology. Your functions remain pure, your data remains traceable, and your system remains comprehensible even as it grows.