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
        student_id=str(student.ecs_id),
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
    if result and isinstance(result, AnalysisResult):
        print(f"Result {i+1}: avg={result.avg:.2f}, type={result.analysis_type}")
    else:
        print(f"Result {i+1}: No valid result")

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

- **[01_basic_entity_transformation.py](examples/readme_examples/01_basic_entity_transformation.py)** - Core entity operations and transformations
- **[02_distributed_addressing.py](examples/readme_examples/02_distributed_addressing.py)** - String-based entity addressing across system boundaries  
- **[03_multi_entity_transformations.py](examples/readme_examples/03_multi_entity_transformations.py)** - Tuple unpacking and sibling relationships
- **[04_distributed_grade_processing.py](examples/readme_examples/04_distributed_grade_processing.py)** - Complex multi-stage data pipelines
- **[05_async_patterns.py](examples/readme_examples/05_async_patterns.py)** - Async and concurrent execution without interference
- **[06_event_system_working.py](examples/readme_examples/06_event_system_working.py)** - Event-driven observation and coordination
- **[07_reactive_cascades.py](examples/readme_examples/07_reactive_cascades.py)** - Multi-step reactive cascades with emergent behavior

Each example includes comprehensive test suites validating the documented behavior and can be run directly to see the framework in action.


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

### Polymorphic Parallel Operator for Branched Compositions
In the process of designing a domain-specific language for the Abstractions framework, we turn our attention to mechanisms that allow functions returning values of a parent type to compose smoothly with transformations specific to subtypes. This polymorphic selector provides a way to examine the runtime instance, determine its concrete subtype through inheritance, and route it to the corresponding path. The approach establishes a connection between parent types and their subtypes on one hand, and union types as explicit disjunctions on the other. Drawing from classical ideas in type theory, such as Hoare's formalizations where a parent type includes its subtypes as refinements, we see the subtype relationship as a particular instance of a set relation—the parent acts as a superset encompassing its specializations. Similarly, a union type constructs a disjunctive set from its components, where any one might be the runtime realization. This duality means that both can be resolved using the same selector logic: whether the return is declared as a parent like Entity or as Union[Student, Teacher], the runtime check verifies if the concrete value fits a handler's input via subtype matching.

To make this concrete, suppose we have a function that processes a raw entity and returns a parent type, but produces subtypes at runtime. The selector inspects this and directs the flow:

```python
@CallableRegistry.register("process_raw")
def process_raw(raw: Entity) -> Entity:  # Parent return
    if "gpa" in raw.fields:
        return Student(name=raw.name, gpa=raw.gpa)
    else:
        return Teacher(name=raw.name, courses=raw.courses)
```

With handlers for subtypes:

```python
@CallableRegistry.register("handle_student")
def handle_student(student: Student) -> str:
    return f"Processed student with GPA {student.gpa}"

@CallableRegistry.register("handle_teacher")
def handle_teacher(teacher: Teacher) -> str:
    return f"Processed teacher with courses {teacher.courses}"
```

The selector could be a function that checks the type and prepares the next step:

```python
@CallableRegistry.register("type_selector")
def type_selector(result: Entity) -> ExecutionSpec:
    if isinstance(result, Student):
        return ExecutionSpec(function="handle_student", args={"student": result})
    elif isinstance(result, Teacher):
        return ExecutionSpec(function="handle_teacher", args={"teacher": result})
```

Execution chains them:

```python
raw = Entity(name="Alice", gpa=3.8)
processed = CallableRegistry.execute("process_raw", raw=raw)
spec = CallableRegistry.execute("type_selector", result=processed)
output = CallableRegistry.execute(spec.function, **spec.args)
```

This resolves the parent return to the subtype path. For an explicit union declaration—Union[Student, Teacher]—the selector works identically, highlighting the duality: the union lists possibilities explicitly, while the parent implies them through inheritance, but both rely on runtime subtype checks for routing.

As hierarchies nest, however, this selector reveals limitations. Introduce a deeper structure, such as ClassRepresentative inheriting from Student, which inherits from Person, all under Entity. A concrete ClassRepresentative would pass isinstance checks for ClassRepresentative, Student, Person, and Entity. If we have handlers for multiple levels:

```python
@CallableRegistry.register("handle_class_rep")
def handle_class_rep(rep: ClassRepresentative) -> str:
    return f"Handled representative role: {rep.role}"

@CallableRegistry.register("handle_student_general")
def handle_student_general(student: Student) -> str:
    return f"Handled general student: GPA {student.gpa}"
```

The selector must decide which to invoke. Prioritizing the most fine-grained (ClassRepresentative) might miss useful general processing, while including both requires explicit logic to avoid arbitrary order in checks. This choice disrupts the selector's simplicity, as it forces assumptions about hierarchy or preferences, complicating what should be a straightforward type-based dispatch.

The way forward with fewest assumptions is to execute all matching paths, defining a polymorphic parallel operator that activates handlers for every level the instance fits. For the ClassRepresentative, this runs the specific role handler and the general student one concurrently, without choosing. In cases with a broad Entity handler, it joins the parallels, producing multiple outputs linked in provenance.

To understand why this parallelism fits, consider that alternatives like ordered resolution demand knowing the hierarchy or adding configurations, which we may not have or want to implement. Parallel execution requires none—it lets the type matches drive the branches naturally, and if only one matches, it behaves as single-path. This makes the polymorphic par a building block for compositions, where forking is the default for overlaps.

The polymorphic par operator emerges as a way to apply handlers in parallel where subtype matches occur, effectively a simplified parallel composition with pattern matching based on the type hierarchy. It processes the output by checking against declared handlers, executing all that fit the concrete type, and collecting the results. The operator's behavior is driven by the event system in the framework, where events are emitted for the output, and handlers respond to those events by triggering executions.

To see this in action, let's first consider how the framework's event system enables it. When a function completes, it emits a CreatedEvent carrying the output's type and ID. @on decorators then listen for specific types, fetching the entity and executing the next step. For hierarchical outputs, multiple @on decorators match because of inheritance, leading to parallel firing as the event system dispatches asynchronously to all listeners:

```python
@on(Student)
async def student_path(event: CreatedEvent[Student]):
    # The event carries the subject_type and subject_id; since the concrete type is ClassRepresentative, it matches Student via inheritance
    student = get(f"@{event.subject_id}")
    # Execute the general handler for Student
    await CallableRegistry.aexecute("handle_student_general", student=student)
    # This path runs, producing its output

@on(ClassRepresentative)
async def rep_path(event: CreatedEvent[ClassRepresentative]):
    rep = get(f"@{event.subject_id}")
    # Execute the specific handler for ClassRepresentative
    await CallableRegistry.aexecute("handle_class_rep", rep=rep)
    # This path also runs, in parallel with the Student one
```

The emission happens after the initial function:

```python
classified = CallableRegistry.execute("process_hierarchical", raw=raw)
# The framework could auto-emit, or we do it manually for clarity
emit(CreatedEvent(subject_type=type(classified), subject_id=classified.ecs_id))
# The event broadcasts, and both handlers activate for a ClassRepresentative output, running concurrently due to the async nature of the event dispatch
# Provenance records the fork: "Event matched 2 handlers due to subtype overlap; executed in parallel"
```

This parallel firing is automatic—the event system doesn't prevent multiple matches; it embraces them, allowing the hierarchy to drive the number of branches. If the output was a plain Student without further specialization, only the Student handler would fire, reducing to a single path. The connection here is that the operator leverages the event system's broadcast to achieve parallelism without additional orchestration; the @on decorators act as the pattern matchers, and the subtype checks are implicit in how the event matching works with type inheritance.

To declare this in the DSL, we use a syntax that lists the handlers with their expected types, which under the hood generates the @on handlers:

```python
composition = "process_hierarchical" ∘par (
    "handle_student_general": Student |
    "handle_class_rep": ClassRepresentative
)
# This DSL compiles to the @on definitions shown above, registering them dynamically for this composition
# At runtime, the par operator ensures the emission and collects outputs from the fired paths
results = CallableRegistry.execute_par(composition, raw=some_raw)
```

The generated handlers are scoped to the composition's context, perhaps by adding a unique step ID to the event:

```python
emit(CreatedEvent(subject_type=type(classified), subject_id=classified.ecs_id, composition_id=composition.id))
# Handlers include predicate=lambda e: e.composition_id == current_id
```

This prevents cross-composition interference. The outputs form a tuple of results from non-muted paths, with provenance noting any forks, such as "Forked to 2 branches for single input due to hierarchy match."

The operator's static signature is Tuple[OutputType1, OutputType2, ...], where each position corresponds to a declared branch's output if not muted. For over-representation—multiple branches for one input—the tuple nests sub-tuples, e.g., Tuple[Tuple[GeneralOutput, SpecificOutput]] if two handlers match. This signature captures branching as multiplicity in the return type, propagating uncertainty or parallelism downstream—callers expect a container holding all completed paths, which they can unpack or process further.

```
Static Signature for par with 2 branches:
Input -> process_hierarchical -> Entity (hierarchical)
     -> par -> Tuple[GeneralStr, SpecificStr]  # If fork, Tuple[Tuple[Str, Str]]

+---------------+     +---------------------+     +---------------------+
| process_hier  |     | par Operator        |     | Output Tuple        |
| returns Entity| --> | Emit event          | --> | (general_result,    |
+---------------+     | Match @on subtypes  |     |  specific_result)   |
                      | Fire parallel if    |     | If no fork: (result)|
                      | multiple match      |     +---------------------+
                      +---------------------+
```

This models the return as a container of non-muted results, connecting the parallel execution to a structured output that reflects the branches taken.

To build on this, consider tuples of types as explicit outputs—fixed collections of mixed entities, where the par operator processes each position independently, connecting to the idea that tuples provide a natural structure for parallel branches:

```python
@CallableRegistry.register("multi_output")
def multi_output(input: Entity) -> Tuple[Student, Teacher]:
    # Produce mixed subtypes
    return Student(name="Alice", gpa=3.8), Teacher(name="Bob", courses=["Math"])
```

The DSL declares the par with handlers for each expected type:

```python
composition = "multi_output" ∘par (
    "handle_student": Student |
    "handle_teacher": Teacher
)
# Generates @on for Student and Teacher
```

To handle the tuple, the execution emits separate events for each element:

```python
student, teacher = multi_output(input)
emit(CreatedEvent(subject_type=type(student), subject_id=student.ecs_id))
emit(CreatedEvent(subject_type=type(teacher), subject_id=teacher.ecs_id))
# The generated @on handlers fire in parallel: student_path for first, teacher_path for second
# Outputs collected as Tuple[str, str], with provenance "Parallel branches for tuple positions 0 and 1"
```

If a hierarchy overlap occurs on one element—say the first is ClassRepresentative—the event for that position matches multiple @on, forking for that slot, and the output tuple becomes Tuple[Tuple[general_str, specific_str], teacher_str], nesting to capture the multiplicity. The connection is that the tuple's positions define the base structure for branches, while the par operator adds forks within positions if inheritance allows, ensuring the return signature reflects both the fixed multiplicity and any additional parallelism.

```
Tuple Flow with par:
Tuple[Student, Teacher] -> Emit per element -> Match @on -> Execute parallel

+---------------+     +---------------------+     +---------------------+
| multi_output  |     | Emit events per pos |     | Tuple Outputs:      |
| returns tuple | --> | Pos0: Student event | --> | Pos0: student_res   |
+---------------+     | Pos1: Teacher event |     | Pos1: teacher_res   |
                      | Match & fire par    |     | If fork on Pos0:    |
                      +---------------------+     |   (gen_res, spec_res)|
                                                  +---------------------+
```

For optionals in tuples—Tuple[Optional[Student], Optional[Teacher]]—the par propagates uncertainty by muting branches for None or unmatched subtypes. The function might produce partial results:

```python
@CallableRegistry.register("optional_multi")
def optional_multi(input: Entity) -> Tuple[Optional[Student], Optional[Teacher]]:
    student = Student(...) if "gpa" in input.fields else None
    teacher = Teacher(...) if "courses" in input.fields else None
    return student, teacher
```

The DSL remains the same, but generated handlers include checks for None:

```python
@on(Student)
async def student_path(event: CreatedEvent[Student]):
    if event.subject_id is None:
        return None  # Mute the branch, no execution
    student = get(f"@{event.subject_id}")
    return await CallableRegistry.aexecute("handle_student", student=student)

# Similar for Teacher
```

Emission handles None by emitting with subject_id=None or skipping, but to propagate:

```python
student, teacher = optional_multi(input)
if student is not None:
    emit(CreatedEvent(subject_type=type(student), subject_id=student.ecs_id))
else:
    emit(CreatedEvent(subject_type=Student, subject_id=None))  # Signal optional mute
# Handlers detect None and return None
```

The static signature is Tuple[Optional[str], Optional[str]], with outputs like (student_result, None) if second muted. Guaranteed branches (always non-None) remain non-optional in the signature, while uncertain ones introduce optionality. This monadic-like propagation connects to the idea that the par operator treats absences as silenced paths, keeping the tuple structure but allowing sparsity, which models uncertainty without halting the flow.

```
Optional Tuple Flow:
Tuple[Opt[Student], Opt[Teacher]] -> Emit (with None signal) -> Match & mute if None

+---------------+     +---------------------+     +---------------------+
| optional_multi|     | Emit per pos,       |     | Tuple Outputs:      |
| returns opt   | --> | signal None if abs  | --> | (student_res, None) |
| tuple         |     | Match @on, mute None|     | If both: (res1, res2)|
+---------------+     +---------------------+     | If none: (None, None)|
                                                  +---------------------+
```

This setup now enables analyzing union returns by reframing Union[Student, Teacher] as Tuple[Optional[Student], Optional[Teacher]], applying par virtually. Statically, the operator enumerates branches as if parallel over optionals: one for potential Student, one for Teacher, with matches to handlers. The hypothesis space is this virtual tuple's paths, where each optional represents a possible activation.

At runtime, the concrete output—say Student—activates the Student branch, mutes the Teacher one by treating it as None, collapsing to a single path. The return signature becomes Tuple[Optional[str], Optional[str]], but in practice, the non-muted result is in the first position, None in the second, which callers can unpack knowing the sparsity.

```python
# DSL for union as virtual optional tuple
composition = "classify_union" ∘par (
    "handle_student": Optional[Student] |
    "handle_teacher": Optional[Teacher]
)
# Static enumeration: virtual pos0 for Student, pos1 for Teacher
# Runtime: concrete Student -> execute pos0, mute pos1 with None
```

Diagram:

```
Union as Virtual Opt Tuple: Union[S, T] -> Tuple[Opt[S], Opt[T]]

+---------------+     +---------------------+     +---------------------+
| classify_union|     | Virtual par:        |     | Collapsed Output:   |
| returns Union | --> | Pos0: Opt[S] match  | --> | (student_res, None) |
+---------------+     | Pos1: Opt[T] match  |     | Or (None, teach_res)|
                      | Runtime concrete S: |     | Single path via mute|
                      |   activate pos0     |     +---------------------+
                      |   mute pos1         |
                      +---------------------+
```

Single execution emerges as a particular instance within this broader model, where the muting of non-matching branches prunes the virtual structure down to a solitary path. This connects directly back to the original intent of the polymorphic selector—to resolve ambiguity through type-based routing—but now generalized under the umbrella of the par operator. In the simpler selector approach, we aimed for a single, determined continuation based on the concrete subtype; with par, that outcome becomes one possible realization of a multipath setup, achieved when the runtime value activates only one branch in the virtual optional tuple, silencing the rest. The framework doesn't need to distinguish this case specially; it follows from the same enumeration and muting logic, ensuring that what appears as a linear flow is merely the sparse result of a parallel enumeration that collapses efficiently.

To see how this works in practice, recall the reframing of a union return like Union[Student, Teacher] as Tuple[Optional[Student], Optional[Teacher]]. The par operator treats this virtually as two parallel branches: one attempting to match and process the Student optional, the other the Teacher. Statically, the DSL declaration:

```python
composition = "classify_union" ∘par (
    "handle_student": Optional[Student] |
    "handle_teacher": Optional[Teacher]
)
```

generates @on handlers that account for the optionality, such as:

```python
@on(Student)
async def student_branch(event: CreatedEvent[Student]):
    if event.subject_id is None:  # Representing the optional None
        return None  # Mute this virtual position
    student = get(f"@{event.subject_id}")
    return await CallableRegistry.aexecute("handle_student", student=student)

# Similar for Teacher branch
```

At runtime, the concrete output—suppose a Student instance—leads to an event emission that matches only the Student branch, with the Teacher branch receiving a virtual None signal (or simply not firing if the event type doesn't match), resulting in muting. The output tuple becomes (student_result, None), which can be unpacked or pattern-matched downstream to ignore the muted slot, effectively yielding the single result. This pruning happens without explicit intervention; the optional structure models the disjunctive uncertainty inherent in the union—the "or" between Student and Teacher translates to parallel optionals, where runtime sparsity resolves to one active path and one silenced.

The connection to the selector's original goal is that this generalization preserves the type-driven resolution while accommodating more complex scenarios. The selector was a sequential dispatcher; par extends it to a parallel one where muting enforces sequential-like behavior when appropriate. This sparsity is "lucky" in the sense that unions often resolve to exactly one subtype, making the virtual tuple's branches mutually exclusive in practice, even though statically they are enumerated as independent. The framework benefits from this by allowing static validation to explore the full hypothesis space—the set of all possible branch activations—while runtime execution remains lightweight, only pursuing the non-muted paths.

```
Virtual Optional Tuple for Union[S, T]: Tuple[Opt[S], Opt[T]]

Static Enumeration:
+---------------+     +---------------------+     +---------------------+
| classify_union|     | par over virtual    |     | Hypothesis Space:   |
| returns Union | --> | tuple positions:    | --> | Pos0: Opt[S] -> h_s |
+---------------+     | Pos0 for Opt[S]     |     | Pos1: Opt[T] -> h_t |
                      | Pos1 for Opt[T]     |     | All branches listed  |
                      | Enumerate matches   |     | for validation      |
                      +---------------------+     +---------------------+

Runtime with concrete S:
Emit event for S -> Match Pos0 (activate h_s), Pos1 gets virtual None (mute)
Output: (result_s, None)  # Collapses to single effective path
```

The optional tuple thus serves as a model for disjunctive uncertainty: each position represents a potential realization of the union, with the par operator enumerating them statically to build the hypothesis space—a graph of all conceivable executions based on which optionals might activate. At runtime, the concrete value determines the sparsity pattern, resolving the space by muting non-applicable positions and producing a tuple that captures only the active results. This resolution is deterministic and tied to the subtype, ensuring no arbitrary choices; the framework's event system handles the dispatch, and provenance logs the muting, such as "Virtual position 1 muted due to type mismatch; only position 0 executed."

Expanding on this, the par operator's handling of sparsity connects to how it manages cases where the hypothesis space has more potential branches than the runtime needs. In under-represented scenarios, where a union component has no matching handler, the corresponding optional position mutes statically as well as at runtime, flagging potential gaps during analysis without runtime cost. The tuple signature reflects this uncertainty upfront—Tuple[Optional[Output1], Optional[Output2]]—guiding callers to handle possibles, while guaranteed matches (if a branch always activates) remain non-optional, tightening the type.

In over-represented cases, where multiple matches occur per virtual position—such as a hierarchy fork on Student, with handlers for both Student and a supertype like Person—the pruning of the hypothesis space can incorporate goal-conditioned learning to select or limit branches. Here, the space grows with the overlaps: for a single position in the virtual tuple, multiple handlers might activate, leading to nested tuples in the output, like Tuple[Tuple[student_result, person_result], None]. To manage this expansion, we can model an LLM agent tasked with navigating the space toward a goal defined as reaching a target subtype of Entity. The agent operates within the finite hierarchical type system deriving from Entity and draws from the registry's finite set of typed functions as tools.

The enumeration of the space starts from the starting type (the input to the composition) and the goal type, generating chains of function applications that transform step by step, with each step a potential fork if multiple functions match the current type. The LLM acts as an adaptive selector at each juncture, choosing which function to call and with which input (perhaps addressing entities via strings), evaluating based on how the choice advances toward the target subtype. For example, if the goal is a Report subtype, and the current state is a Student entity, the LLM might select a grading function that outputs Report, pruning alternatives like scheduling that lead elsewhere.

Over iterations, outcomes from executions—success in reaching the goal, efficiency in steps, or accuracy in results—feed back to refine the agent's choices, pruning inefficient paths by favoring those with higher learned utility. This extends the par's multipath nature into a learnable framework: the hypothesis space, initially enumerated fully for analysis, becomes navigable, with the LLM's decisions acting as a dynamic reducer that collapses branches based on goals. In the framework, this could integrate with provenance to log traversals, allowing the agent to learn from past chains, ultimately optimizing compositions for specific objectives like minimizing latency while achieving the desired output type.

```
Over-Represented Hypothesis Space with Pruning:

Static Space for Union[S, T] with multiple handlers per:
Tuple[Opt[S], Opt[T]] -> par -> Nested Tuple possibilities
  Pos0 Opt[S]: fork to h_student and h_person if overlap
  Pos1 Opt[T]: single h_teacher

+---------------+     +---------------------+     +---------------------+
| Union return  |     | par Enumeration     |     | Pruned by LLM:      |
| reframed opt  | --> | Pos0: fork if over  | --> | Choose h_student    |
| tuple         |     | Pos1: single        |     | over h_person if    |
+---------------+     | Full space generated|     | goal favors detail  |
                      +---------------------+     | Runtime: sparse res |
                                                  +---------------------+
```

This goal-conditioned pruning transforms the static enumeration into a dynamic process, where the par operator's branches are not just executed but selected adaptively, refining the hypothesis space over time to focus on paths that efficiently reach the target subtype. The connection back to the initial selector is that learning elevates the type-based routing to a purposeful navigation, where the framework's event system and async execution support the parallelism, but the agent's choices ensure sparsity aligns with intentions.

### Reactive Scatter-Gather: Event-Driven Parallel Composition

The polymorphic parallel operator showed us how to scatter computation across multiple type-matched handlers. But this creates a new challenge: how do we gather the parallel results back together? The framework provides two approaches - explicit borrowing (shown earlier) and reactive gathering through events.

Consider what happens after `∘par` execution:

```python
# Execute parallel branches based on type matching
result = execute_par("analyze_entity" ∘par (
    "student_processor": Student |
    "teacher_processor": Teacher |
    "admin_processor": Admin
))

# This returns a TupleEntity containing all results
# TupleEntity[Optional[StudentResult], Optional[TeacherResult], Optional[AdminResult]]
```

We now have a tuple of results, some of which may be None (muted branches). The traditional approach would be to explicitly access and combine these results. But the framework offers something more elegant: reactive gathering through the event system.

#### The Reactive Pattern

When the `TupleEntity` is created, it's promoted to root like any other entity, which triggers a `CreatedEvent`. This event carries the tuple's type signature, allowing handlers to pattern-match on specific tuple shapes:

```python
# The TupleEntity creation automatically emits:
# CreatedEvent[TupleEntity[Optional[StudentResult], Optional[TeacherResult], Optional[AdminResult]]]

# We can react to this specific pattern
@on(CreatedEvent[TupleEntity])
async def gather_analysis_results(event: CreatedEvent[TupleEntity]):
    """React to any TupleEntity creation"""
    tuple_entity = get(f"@{event.subject_id}")
    
    # Extract non-None results
    active_results = [r for r in tuple_entity.results if r is not None]
    
    # Create gathered report
    if active_results:
        report = ComprehensiveReport(
            analyses=active_results,
            source_count=len(active_results),
            pattern="parallel_analysis"
        )
        
        # Continue the cascade
        await emit(CreatedEvent(
            subject_type=ComprehensiveReport,
            subject_id=report.ecs_id
        ))
```

This simple pattern completes the scatter-gather loop: `∘par` scatters computation across type-matched handlers, creating a `TupleEntity` that emits an event, which triggers gathering handlers that react based on the tuple's content.

#### Type-Specific Gathering

The power of this approach becomes clear when we make the gathering type-aware. Just as `∘par` uses type matching to determine which handlers to execute, we can use type patterns to determine which gatherers to activate:

```python
# Define specific tuple type aliases for clarity
StudentTeacherTuple = TupleEntity[
    Optional[StudentAnalysis], 
    Optional[TeacherAnalysis]
]

# Create type-specific gatherer
@on(CreatedEvent[StudentTeacherTuple])
async def gather_education_analysis(event: CreatedEvent[StudentTeacherTuple]):
    """Gather results from student-teacher parallel analysis"""
    tuple_result = get(f"@{event.subject_id}")
    
    student_analysis = tuple_result[0]
    teacher_analysis = tuple_result[1]
    
    # Handle different sparsity patterns
    if student_analysis and teacher_analysis:
        # Both present - perhaps a teaching assistant
        combined = TeachingAssistantAnalysis(
            student_side=student_analysis,
            teacher_side=teacher_analysis,
            dual_role=True
        )
    elif student_analysis:
        # Only student analysis succeeded
        combined = StudentOnlyAnalysis(
            data=student_analysis,
            teacher_data_absent=True
        )
    else:
        # Only teacher analysis succeeded
        combined = TeacherOnlyAnalysis(
            data=teacher_analysis,
            student_data_absent=True
        )
    
    # Continue the reactive cascade
    await emit(CreatedEvent(subject_type=type(combined), subject_id=combined.ecs_id))
```

The gatherer examines the sparsity pattern in the tuple and creates different outputs based on what actually executed. This is the same principle as the polymorphic parallel operator - we don't force a choice about how to handle the results, we react to what actually happened.

#### Multi-Stage Reactive Pipelines

The reactive scatter-gather pattern naturally extends to multiple stages. Each scatter creates a tuple, which triggers a gather, which might scatter again. This creates pipelines where data flows through alternating phases of parallel exploration and focused aggregation:

```python
# Stage 1: Initial classification returns a single type
@CallableRegistry.register("classify_document")
def classify_document(doc: Document) -> Union[TextDoc, ImageDoc, VideoDoc]:
    """Classify document into specific type"""
    if doc.mime_type.startswith("text/"):
        return TextDoc(content=doc.content, format=doc.format)
    elif doc.mime_type.startswith("image/"):
        return ImageDoc(data=doc.content, dimensions=doc.metadata)
    else:
        return VideoDoc(stream=doc.content, duration=doc.metadata)

# Stage 2: Type-specific handlers scatter into parallel analysis
@on(CreatedEvent[TextDoc])
async def analyze_text_document(event: CreatedEvent[TextDoc]):
    """When TextDoc is created, scatter into parallel text analyses"""
    doc = get(f"@{event.subject_id}")
    
    # Scatter across text-specific processors
    result = await execute_par("text_pipeline" ∘par (
        "sentiment": TextDoc |      # Sentiment analysis
        "entities": TextDoc |       # Entity extraction
        "summary": TextDoc          # Text summarization
    ))
    # Creates: TupleEntity[Optional[Sentiment], Optional[Entities], Optional[Summary]]

# Stage 3: Gather text analysis results reactively
@on(lambda e: e.type == "created" and 
    isinstance(getattr(e, 'subject_type', None), type) and
    issubclass(e.subject_type, TupleEntity) and
    hasattr(e.subject_type, '__args__') and
    any("Sentiment" in str(arg) for arg in e.subject_type.__args__))
async def gather_text_analyses(event: CreatedEvent):
    """Gather results from text analysis scatter"""
    tuple_entity = get(f"@{event.subject_id}")
    
    # Create unified report from whatever succeeded
    report = TextAnalysisReport(
        sentiment=tuple_entity[0] if tuple_entity[0] else None,
        entities=tuple_entity[1].entities if tuple_entity[1] else [],
        summary=tuple_entity[2].text if tuple_entity[2] else "No summary available"
    )
    
    await emit(CreatedEvent(subject_type=TextAnalysisReport, subject_id=report.ecs_id))
```

Each stage operates independently - the document classifier doesn't know about the parallel analyses, and the analyses don't know about the gathering. The pattern emerges from the type relationships and event propagation.

#### Understanding the Complete Flow

To see how scatter and gather work together reactively, let's trace through a complete example:

```python
# 1. SCATTER: The ∘par operator creates parallel branches
async def process_mixed_entity(entity: Entity) -> None:
    """Process an entity that might match multiple handler types"""
    
    # The par operator scatters based on type matching
    result = await execute_par("classify_and_process" ∘par (
        "as_student": Student |
        "as_teacher": Teacher |
        "as_researcher": Researcher
    ))
    # Returns: TupleEntity[Optional[StudentResult], Optional[TeacherResult], Optional[ResearcherResult]]
    # The framework automatically emits: CreatedEvent[TupleEntity[...]]

# 2. GATHER: React to tuple creation with pattern matching
@on(predicate=lambda e: 
    e.type == "created" and 
    isinstance(getattr(e, 'subject_type', None), type) and
    issubclass(e.subject_type, TupleEntity))
async def examine_parallel_results(event: CreatedEvent):
    """Examine what the parallel execution produced"""
    
    tuple_entity = get(f"@{event.subject_id}")
    
    # Count active results (non-None branches)
    active_results = [(i, r) for i, r in enumerate(tuple_entity.results) if r is not None]
    
    if len(active_results) == 0:
        # No handlers matched - unusual case
        await emit(NoMatchesWarning(
            original_entity_id=event.subject_id,
            attempted_branches=len(tuple_entity.results)
        ))
        
    elif len(active_results) == 1:
        # Single match - common case for union types
        idx, result = active_results[0]
        await emit(SingleMatchEvent(
            result_id=result.ecs_id,
            branch_name=tuple_entity.branch_names[idx],
            branch_index=idx
        ))
        
    else:
        # Multiple matches - interesting case for hierarchies
        await emit(MultipleMatchesEvent(
            result_ids=[r.ecs_id for _, r in active_results],
            branch_names=[tuple_entity.branch_names[i] for i, _ in active_results],
            match_count=len(active_results)
        ))
```

The gathering handler doesn't make assumptions about what should happen - it observes the sparsity pattern and emits appropriate events. Other handlers can then react to these patterns.

#### Conditional Gathering Based on Sparsity

The sparsity pattern in the tuple - which branches executed and which were muted - carries information. Reactive gatherers can create different outputs based on these patterns:

```python
# Type alias for a compliance checking tuple
ComplianceTuple = TupleEntity[
    Optional[FinancialAnalysis],
    Optional[RiskAnalysis],
    Optional[ComplianceCheck]
]

@on(CreatedEvent[ComplianceTuple])
async def adaptive_compliance_gathering(event: CreatedEvent[ComplianceTuple]):
    """Create different reports based on what analyses completed"""
    
    tuple_result = get(f"@{event.subject_id}")
    financial = tuple_result[0]
    risk = tuple_result[1] 
    compliance = tuple_result[2]
    
    # The sparsity pattern determines the output type
    if financial and risk and compliance:
        # Full analysis completed - create comprehensive report
        report = FullComplianceReport(
            financial_data=financial,
            risk_assessment=risk,
            compliance_status=compliance,
            confidence="high",
            completeness=1.0
        )
        
    elif financial and risk and not compliance:
        # Compliance check failed or wasn't applicable
        report = ProvisionalReport(
            financial_data=financial,
            risk_assessment=risk,
            missing_components=["compliance"],
            confidence="medium",
            completeness=0.67
        )
        
    elif any([financial, risk, compliance]):
        # Partial results - create what we can
        available = [name for name, result in 
                    [("financial", financial), ("risk", risk), ("compliance", compliance)]
                    if result is not None]
        
        report = PartialAnalysis(
            available_components=available,
            completeness=len(available) / 3.0,
            confidence="low"
        )
        
    else:
        # Nothing succeeded - this itself is information
        report = AnalysisFailure(
            reason="No analysis components completed successfully",
            timestamp=datetime.now()
        )
    
    # The report type itself carries information about what happened
    await emit(CreatedEvent(subject_type=type(report), subject_id=report.ecs_id))
```

This pattern embraces the information in sparsity. Instead of treating None results as failures, they become part of the computation - different combinations lead to different outcomes.

## Why This Pattern is Powerful

### 1. **No Explicit Coordination**
The scatter happens through `∘par`, the gather happens through `@on`. No orchestrator needed.

### 2. **Type-Safe Cascades**
Each stage has clear input/output types. The `TupleEntity` type parameters ensure type safety through the entire flow.

### 3. **Composable Patterns**
You can chain scatter-gather stages indefinitely:
```python
Document → ∘par → TupleEntity → @on → Report → ∘par → TupleEntity → @on → Summary
```

### 4. **Natural Sparsity Handling**
`Optional[T]` in tuple positions naturally handles muted branches. Gatherers can react appropriately to missing data.

### 5. **Distributed-Ready**
Since everything is event-driven, gatherers can run anywhere. The tuple entity is just another addressable entity in the system.

#### Chaining Reactive Scatter-Gather Stages

The true power emerges when multiple scatter-gather stages chain together. Each gather can trigger another scatter, creating complex processing pipelines that emerge from simple local rules:

```python
# Stage 1: Document classification
@CallableRegistry.register("classify_document")
def classify_document(doc: Document) -> Union[LegalDoc, TechnicalDoc, MarketingDoc]:
    """Classify document into specific type based on content"""
    # Classification logic returns one specific type
    return classified_doc

# Stage 2: Type-specific parallel analysis
@on(CreatedEvent[LegalDoc])
async def analyze_legal_document(event: CreatedEvent[LegalDoc]):
    """When a legal document is created, scatter into parallel legal analyses"""
    doc = get(f"@{event.subject_id}")
    
    result = await execute_par("legal_analysis" ∘par (
        "contract_review": LegalDoc |     # Contract clause analysis
        "compliance_check": LegalDoc |    # Regulatory compliance
        "risk_assessment": LegalDoc       # Legal risk analysis
    ))
    # Creates: TupleEntity[Optional[ContractReview], Optional[ComplianceResult], Optional[RiskReport]]

# Stage 3: Gather legal analyses into unified report
@on(lambda e: e.type == "created" and 
    isinstance(getattr(e, 'subject_type', None), type) and
    issubclass(e.subject_type, TupleEntity) and
    hasattr(e.subject_type, '__args__') and
    any("ContractReview" in str(arg) for arg in e.subject_type.__args__))
async def create_legal_report(event: CreatedEvent):
    """Gather legal analysis results into comprehensive report"""
    tuple_entity = get(f"@{event.subject_id}")
    
    # Build report from available analyses
    report = LegalReport(
        contract_issues=tuple_entity[0].issues if tuple_entity[0] else [],
        compliance_status=tuple_entity[1].status if tuple_entity[1] else "pending",
        risk_level=tuple_entity[2].level if tuple_entity[2] else "unknown",
        completeness=sum(1 for r in tuple_entity.results if r is not None) / 3.0
    )
    
    await emit(CreatedEvent(subject_type=LegalReport, subject_id=report.ecs_id))

# Stage 4: Executive summary reacts to any report type
@on(Union[LegalReport, TechnicalReport, MarketingReport])
async def create_executive_summary(event: CreatedEvent):
    """Create executive summary from any report type"""
    report = get(f"@{event.subject_id}")
    
    # Extract key information based on report type
    summary = ExecutiveSummary(
        document_type=type(report).__name__,
        key_findings=report.extract_key_findings(),
        recommended_actions=report.get_recommendations(),
        confidence_level=report.completeness if hasattr(report, 'completeness') else 1.0
    )
    
    await emit(CreatedEvent(subject_type=ExecutiveSummary, subject_id=summary.ecs_id))
```

Each stage operates independently:
- The classifier doesn't know about parallel analyses
- The parallel analyses don't know about report generation
- The report generator doesn't know about executive summaries

Yet they form a cohesive pipeline through type relationships and event propagation.

## Conclusion

By using `@on` decorators to gather from `TupleEntity` results, you complete the reactive scatter-gather pattern. The type system (via Union types and tuple parameters) drives both the scattering (which handlers execute) and the gathering (which events to react to).

This creates a fully reactive system where:
- **Scatter** happens through type affordances (`∘par`)
- **Intermediate results** are addressable entities (TupleEntity)
- **Gather** happens through event reactions (`@on`)
- **Type safety** is maintained throughout
- **No orchestration** is needed

The entire pattern emerges from local rules: functions declare what they can process, the framework executes all matches in parallel, results emit events, and handlers react to continue the flow. Complex workflows self-organize from these simple principles.

### Types as Affordances: What Functions Make Possible

The reactive scatter-gather pattern revealed something profound about the framework. When `∘par` scatters computation and `@on` gathers results, what's really happening is that types are creating possibilities for transformation. Each registered function that accepts a type is declaring an affordance - a transformation that type makes possible.

Consider what we just saw with reactive gathering:

```python
# These functions define what Student affords
@CallableRegistry.register("calculate_gpa")
def calculate_gpa(student: Student) -> GradeReport:
    pass

@CallableRegistry.register("check_enrollment")  
def check_enrollment(student: Student) -> EnrollmentStatus:
    pass

@CallableRegistry.register("generate_transcript")
def generate_transcript(student: Student) -> Transcript:
    pass

# When we execute ∘par, we're exploring all affordances
result = execute_par("process_student" ∘par (
    "gpa": Student |
    "enrollment": Student |
    "transcript": Student
))

# The Student type affords all three transformations
# They execute in parallel because they're all possible
```

The key insight: **types don't describe data structure - they describe what functions are available**. When you register a function that accepts `Student`, you're adding to what `Student` affords in the system.

#### Composition Creates Scoped Affordances

Here's where it gets interesting. When you compose functions, you're not just chaining transformations - you're declaring what affordances are available at each step of the computation:

```python
# Global affordances - available anywhere
@on(CreatedEvent[Student])
async def global_student_handler(event):
    # This fires whenever ANY Student is created
    
# But composition creates scoped affordances
composition = "get_student" >> "calculate_gpa" >> "determine_honors"

# This is essentially creating:
# @on(type:Student, from:["get_student"], execute:"calculate_gpa")
# @on(type:GradeReport, from:["calculate_gpa"], execute:"determine_honors")
```

The composition operator (`>>` or `∘`) is really creating event handlers that only fire in the context of that specific computation chain. When `get_student` produces a `Student`, only the `calculate_gpa` in this composition fires, not every function that accepts `Student`.

This is the crucial difference:
- **Global `@on`**: Fires whenever the type appears anywhere in the system
- **Composed functions**: Fire only when the type appears at that specific depth in the computation

Let's make this concrete:

```python
# These are global affordances
@CallableRegistry.register("validate_student")
def validate_student(s: Student) -> ValidationResult:
    pass

@CallableRegistry.register("enroll_in_course")
def enroll_in_course(s: Student, c: Course) -> Enrollment:
    pass

# But when we compose, we create a specific path
academic_pipeline = (
    "fetch_student" >>           # Produces Student
    "calculate_gpa" >>           # Student → GradeReport (only from fetch_student)
    "check_academic_standing"    # GradeReport → Standing (only from calculate_gpa)
)

# Even though validate_student and enroll_in_course accept Student,
# they don't fire in this composition - the affordances are scoped
```

The composition declares: "At this step, Student affords calculate_gpa transformation, and that's it."

#### The Polymorphic Parallel Operator and Scoped Affordances

The `∘par` operator becomes even more powerful in this light. It's not just exploring all type matches - it's exploring all affordances available at that specific point in the computation:

```python
# Define a branching composition
analysis_pipeline = (
    "fetch_entity" >>
    "classify_entity" ∘par (
        "as_student": Student |
        "as_teacher": Teacher |
        "as_admin": Admin
    ) >>
    "generate_report"
)

# This creates scoped affordances:
# 1. After fetch_entity: Entity affords classify_entity
# 2. After classify_entity: 
#    - Student output affords as_student (scoped to this pipeline)
#    - Teacher output affords as_teacher (scoped to this pipeline)
#    - Admin output affords as_admin (scoped to this pipeline)
# 3. The TupleEntity result affords generate_report
```

The brilliance is that these affordances are isolated to this composition. If you have another pipeline:

```python
enrollment_pipeline = (
    "fetch_entity" >>
    "validate_identity" >>
    "check_prerequisites" ∘par (
        "for_student": Student |
        "for_teacher": Teacher
    ) >>
    "create_enrollment"
)
```

The `Student` type has different affordances at each step:
- In `analysis_pipeline`: Student affords `as_student` after classification
- In `enrollment_pipeline`: Student affords `for_student` after prerequisites

Same type, different context, different affordances. The composition declares what's possible at each depth.

#### Why This Matters for Distributed Systems

In a monolithic application, you might maintain the illusion of global type knowledge - every function that accepts `Student` is available everywhere. But distributed systems shatter this illusion in a useful way:

```python
# Registration Service - local affordances
@CallableRegistry.register("enroll_in_course")
def enroll_in_course(student: Student, course: Course) -> Enrollment:
    pass

# Billing Service - different local affordances  
@CallableRegistry.register("calculate_tuition")
def calculate_tuition(student: Student) -> TuitionBill:
    pass

# Same Student type, but:
# - In Registration Service: Student affords enrollment
# - In Billing Service: Student affords tuition calculation
# - In composition: Student affords what the composition declares
```

The framework embraces this reality. Types have:
1. **Global affordances** via `@on` decorators - available whenever the type appears
2. **Service affordances** via local function registry - available in that service
3. **Composition affordances** via `>>` and `∘par` - available at specific computation steps

This creates a rich, context-sensitive system where the same type can afford different transformations based on where and how it appears.

#### The Connection to Reactive Scatter-Gather

Now we can see the reactive scatter-gather pattern in a new light. When a `TupleEntity` is created and emits its event, the `@on` handlers that fire are declaring global affordances for that tuple pattern:

```python
# Composition creates scoped affordances
pipeline = "classify" ∘par (
    "student_path": Student |
    "teacher_path": Teacher
) 

# This produces TupleEntity[Optional[StudentResult], Optional[TeacherResult]]

# Global affordance for this tuple pattern
@on(CreatedEvent[TupleEntity[Optional[StudentResult], Optional[TeacherResult]]])
async def gather_education_results(event):
    # This handler declares that this specific tuple pattern
    # affords education result gathering
    pass

# Different global affordance for same pattern
@on(lambda e: is_education_tuple(e))
async def audit_education_processing(event):
    # This tuple pattern also affords auditing
    pass
```

The `@on` decorators are declaring what the `TupleEntity` affords globally, while the composition that created it declared what affordances were available at that computation step.

#### The Philosophy: Types Define Possibilities

This leads to a fundamental shift in how we think about types:

**Traditional view**: Types describe data structure
- `Student` has fields: name, gpa, enrollment_date
- Functions validate they receive correct fields
- Type checking ensures structural compatibility

**Affordance view**: Types describe transformation possibilities
- `Student` affords: enrollment, grading, transcript generation
- Functions declare what transformations they provide
- Type checking ensures transformation compatibility

The difference is profound. In the traditional view, types are passive descriptions. In the affordance view, types are active declarations of possibility. When you create a new type, you're not just defining data structure - you're opening a space of potential transformations.

#### Composition as Affordance Declaration

When we compose functions, we're explicitly declaring which affordances are available at each step:

```python
# This composition declares a specific affordance path
academic_flow = (
    "fetch_student" >>           # Start: produces Student
    "calculate_gpa" >>           # Step 1: Student affords GPA calculation here
    "determine_standing" >>      # Step 2: GradeReport affords standing determination here
    "generate_letter"            # Step 3: Standing affords letter generation here
)

# At each step, we've declared what transformation is possible
# Other functions that accept these types don't interfere
# The composition creates its own affordance scope
```

This is why composition is so powerful in the framework. You're not just chaining functions - you're creating a specific path through the space of possibilities, declaring which affordances are available at each step.

#### Emergent Behavior Through Affordance Interaction

Complex behavior emerges when affordances interact:

1. **Types afford transformations** (via registered functions)
2. **Compositions scope affordances** (via >> and ∘par operators)  
3. **Events propagate affordances** (via @on decorators)
4. **Parallel execution explores affordances** (via polymorphic dispatch)

The system's behavior emerges from these interactions without central planning. You don't design workflows - you declare affordances and let the system discover paths through the possibility space.

#### Practical Implications

This philosophy suggests concrete practices:

**Design functions as affordance providers**:
```python
# Don't think: "This function needs a Student with these fields"
# Think: "This function provides the enrollment affordance for Student"
@CallableRegistry.register("enroll_in_course")
def enroll_in_course(student: Student, course: Course) -> Enrollment:
    pass
```

**Use composition to declare affordance paths**:
```python
# Don't manually orchestrate
# Declare the affordance path and let it execute
registration_flow = (
    "validate_student" >>
    "check_prerequisites" >>
    "create_enrollment" >>
    "send_confirmation"
)
```

**Let types flow through natural affordances**:
```python
# Don't force type conversions
# Let entities flow through their natural affordances
result = execute_par("process_entity" ∘par (
    "academic": Student |
    "administrative": Employee |
    "general": Person
))
```

#### Conclusion: A New Way of Thinking

The Abstractions framework embodies a simple but powerful idea: **types are not descriptions of what data is, but declarations of what data can become**. 

Functions don't operate on passive data structures - they actualize possibilities that types afford. Compositions don't just chain operations - they declare paths through possibility space. Events don't just notify - they propagate affordances for reactive handling.

This creates a programming model where:
- The same type affords different transformations in different contexts
- Parallel execution explores multiple affordances without choosing
- Complex workflows emerge from simple affordance declarations
- The system adapts by discovering new paths through the possibility space

In distributed systems, where services have partial knowledge and contexts vary, this affordance-based model aligns perfectly with reality. You stop fighting to maintain global type consistency and embrace that affordances are naturally scoped, contextual, and composable.

The question shifts from "what is this data?" to "what can this data become here, in this context, at this step?" And that's exactly the right question for building flexible, evolvable distributed systems.