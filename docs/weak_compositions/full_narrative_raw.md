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



# Reactive Scatter-Gather: Event-Driven Gathering from Parallel Results

## The Missing Piece: Reactive Gathering

The Abstractions framework's true power emerges when you combine `∘par` execution with event-driven gathering. Instead of explicit borrowing, you can use `@on` decorators to reactively process parallel results based on their type patterns.

### The Pattern

```python
# Step 1: Scatter via ∘par - returns TupleEntity
result = execute_par("analyze_entity" ∘par (
    "student_processor": Student |
    "teacher_processor": Teacher |
    "admin_processor": Admin
))
# Result type: TupleEntity[Union[StudentResult, None], Union[TeacherResult, None], Union[AdminResult, None]]

# Step 2: TupleEntity creation emits event
# CreatedEvent[TupleEntity] with the specific Union type signature

# Step 3: Reactive gathering via @on
@on(lambda e: isinstance(e.subject_type, TupleEntity) and 
    hasattr(e.subject_type, '__args__') and 
    len(e.subject_type.__args__) == 3)
async def gather_analysis_results(event: CreatedEvent[TupleEntity]):
    """Automatically gather when matching tuple pattern detected"""
    tuple_entity = get(f"@{event.subject_id}")
    
    # Extract non-None results
    results = [r for r in tuple_entity.results if r is not None]
    
    # Create comprehensive report from gathered data
    report = ComprehensiveReport(
        analyses=results,
        source_count=len(results),
        pattern="multi_analysis"
    )
    
    # Emit the gathered result
    await emit(CreatedEvent[ComprehensiveReport](
        subject_type=ComprehensiveReport,
        subject_id=report.ecs_id
    ))
```

## Type-Safe Reactive Gathering

The real magic comes from being able to match specific `TupleEntity` patterns:

```python
# Define specific TupleEntity types for better matching
StudentTeacherTuple = TupleEntity[
    Optional[StudentAnalysis], 
    Optional[TeacherAnalysis]
]

# Now you can write type-specific gatherers
@on(CreatedEvent[StudentTeacherTuple])
async def gather_education_analysis(event: CreatedEvent[StudentTeacherTuple]):
    """Gather specifically for student-teacher analysis pairs"""
    tuple_result = get(f"@{event.subject_id}")
    
    student_analysis = tuple_result[0]
    teacher_analysis = tuple_result[1]
    
    # Both might be present (for a teaching assistant)
    # Or only one (for pure student or teacher)
    
    if student_analysis and teacher_analysis:
        # Create combined analysis
        combined = TeachingAssistantAnalysis(
            student_side=student_analysis,
            teacher_side=teacher_analysis
        )
    elif student_analysis:
        combined = StudentOnlyAnalysis(data=student_analysis)
    else:
        combined = TeacherOnlyAnalysis(data=teacher_analysis)
    
    await emit(CreatedEvent(subject_type=type(combined), subject_id=combined.ecs_id))
```

## Multi-Stage Reactive Pipelines

This pattern enables complex multi-stage processing without explicit coordination:

```python
# Stage 1: Initial parallel analysis
@CallableRegistry.register("initial_analysis")
def initial_analysis(doc: Document) -> Union[TextAnalysis, ImageAnalysis, VideoAnalysis]:
    # Returns one of several types based on document content
    if doc.type == "text":
        return TextAnalysis(...)
    elif doc.type == "image":
        return ImageAnalysis(...)
    else:
        return VideoAnalysis(...)

# Stage 2: Type-specific parallel processing
@on(CreatedEvent[TextAnalysis])
async def process_text_analysis(event: CreatedEvent[TextAnalysis]):
    # Scatter across text-specific processors
    result = await execute_par("text_pipeline" ∘par (
        "sentiment": TextAnalysis |
        "entities": TextAnalysis |
        "summary": TextAnalysis
    ))
    # This creates a TupleEntity[Sentiment, Entities, Summary]

@on(CreatedEvent[ImageAnalysis])
async def process_image_analysis(event: CreatedEvent[ImageAnalysis]):
    # Scatter across image-specific processors
    result = await execute_par("image_pipeline" ∘par (
        "objects": ImageAnalysis |
        "faces": ImageAnalysis |
        "text_ocr": ImageAnalysis
    ))
    # This creates a TupleEntity[Objects, Faces, OCRText]

# Stage 3: Gather from specific tuple patterns
@on(lambda e: e.type == "created" and 
    hasattr(e.subject_type, '__origin__') and
    e.subject_type.__origin__ is TupleEntity and
    "Sentiment" in str(e.subject_type))
async def gather_text_results(event: CreatedEvent):
    """Gather text analysis results"""
    tuple_entity = get(f"@{event.subject_id}")
    
    # Create unified text report
    text_report = TextReport(
        sentiment=tuple_entity[0],
        entities=tuple_entity[1], 
        summary=tuple_entity[2]
    )
    
    await emit(CreatedEvent(
        subject_type=TextReport,
        subject_id=text_report.ecs_id
    ))
```

## The Complete Scatter-Gather Loop

Here's how everything connects:

```python
# 1. SCATTER: Execute parallel branches based on type affordances
async def process_mixed_entity(entity: Entity) -> None:
    """Process entity that might match multiple types"""
    
    # This scatters based on type matching
    result = await execute_par("classify_and_process" ∘par (
        "as_student": Student |
        "as_teacher": Teacher |
        "as_researcher": Researcher
    ))
    # Returns: TupleEntity with results in known positions

# 2. EMIT: TupleEntity creation automatically emits event
# The framework emits: CreatedEvent[TupleEntity[...]]

# 3. GATHER: React to specific tuple patterns
@on(predicate=lambda e: 
    e.type == "created" and 
    isinstance(getattr(e, 'subject_type', None), type) and
    issubclass(e.subject_type, TupleEntity))
async def universal_tuple_gatherer(event: CreatedEvent):
    """Gather any TupleEntity results"""
    
    tuple_entity = get(f"@{event.subject_id}")
    
    # Inspect what we got
    active_results = [(i, r) for i, r in enumerate(tuple_entity.results) if r is not None]
    
    if len(active_results) == 0:
        # No matches - emit warning
        await emit(NoMatchesEvent(original_entity_id=event.subject_id))
    elif len(active_results) == 1:
        # Single match - simple forward
        idx, result = active_results[0]
        await emit(SingleMatchEvent(
            result_id=result.ecs_id,
            branch_name=tuple_entity.branch_names[idx]
        ))
    else:
        # Multiple matches - need resolution
        await emit(MultipleMatchesEvent(
            result_ids=[r.ecs_id for _, r in active_results],
            branch_names=[tuple_entity.branch_names[i] for i, _ in active_results]
        ))

# 4. REDUCE: Handle gathered results based on pattern
@on(MultipleMatchesEvent)
async def resolve_multiple_matches(event: MultipleMatchesEvent):
    """Decide how to handle multiple parallel results"""
    
    # Could merge, select best, or create composite
    if "student" in event.branch_names and "researcher" in event.branch_names:
        # PhD student case - merge both aspects
        merged = await create_phd_student_profile(
            student_id=event.result_ids[event.branch_names.index("student")],
            researcher_id=event.result_ids[event.branch_names.index("researcher")]
        )
        await emit(CreatedEvent(subject_type=PhDStudent, subject_id=merged.ecs_id))
```

## Advanced Pattern: Conditional Gathering

You can create sophisticated gathering logic based on tuple contents:

```python
# Type alias for clarity
AnalysisTuple = TupleEntity[
    Optional[FinancialAnalysis],
    Optional[RiskAnalysis],
    Optional[ComplianceCheck]
]

@on(CreatedEvent[AnalysisTuple])
async def conditional_compliance_gathering(event: CreatedEvent[AnalysisTuple]):
    """Gather based on what's present in the tuple"""
    
    tuple_result = get(f"@{event.subject_id}")
    financial = tuple_result[0]
    risk = tuple_result[1] 
    compliance = tuple_result[2]
    
    # Different gathering strategies based on what succeeded
    if financial and risk and compliance:
        # All three - create full report
        report = FullComplianceReport(
            financial=financial,
            risk=risk,
            compliance=compliance,
            status="complete"
        )
    elif financial and risk and not compliance:
        # Missing compliance - create provisional report
        report = ProvisionalReport(
            financial=financial,
            risk=risk,
            status="pending_compliance"
        )
    elif compliance and not financial and not risk:
        # Only compliance - create alert
        report = ComplianceOnlyAlert(
            compliance=compliance,
            status="insufficient_data"
        )
    else:
        # Other patterns...
        report = IncompleteAnalysis(
            available_components=sum(1 for x in [financial, risk, compliance] if x),
            status="incomplete"
        )
    
    # Report emits its own event, continuing the cascade
    await emit(CreatedEvent(subject_type=type(report), subject_id=report.ecs_id))
```

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

## Complete Example: Multi-Stage Document Processing

```python
# Stage 1: Classify document
@CallableRegistry.register("classify_document")
def classify_document(doc: Document) -> Union[LegalDoc, TechnicalDoc, MarketingDoc]:
    # Classification logic
    return classified_doc

# Stage 2: Scatter based on classification
@on(CreatedEvent[LegalDoc])
async def process_legal_doc(event: CreatedEvent[LegalDoc]):
    result = await execute_par("legal_analysis" ∘par (
        "contract_review": LegalDoc |
        "compliance_check": LegalDoc |
        "risk_assessment": LegalDoc
    ))
    # Emits: CreatedEvent[TupleEntity[ContractReview, ComplianceResult, RiskReport]]

# Stage 3: Gather legal results
@on(lambda e: e.type == "created" and 
    is_tuple_containing(e.subject_type, [ContractReview, ComplianceResult, RiskReport]))
async def gather_legal_analysis(event: CreatedEvent):
    tuple_entity = get(f"@{event.subject_id}")
    
    # Create comprehensive legal report
    legal_report = LegalReport(
        contract_issues=tuple_entity[0].issues if tuple_entity[0] else [],
        compliance_status=tuple_entity[1].status if tuple_entity[1] else "pending",
        risk_level=tuple_entity[2].level if tuple_entity[2] else "unknown"
    )
    
    await emit(CreatedEvent(subject_type=LegalReport, subject_id=legal_report.ecs_id))

# Stage 4: React to reports from all document types
@on(Union[LegalReport, TechnicalReport, MarketingReport])
async def create_executive_summary(event: CreatedEvent):
    # Another level of gathering
    report = get(f"@{event.subject_id}")
    
    summary = ExecutiveSummary(
        document_type=type(report).__name__,
        key_findings=report.get_key_findings(),
        recommended_actions=report.get_recommendations()
    )
    
    await emit(CreatedEvent(subject_type=ExecutiveSummary, subject_id=summary.ecs_id))
```

## Conclusion

By using `@on` decorators to gather from `TupleEntity` results, you complete the reactive scatter-gather pattern. The type system (via Union types and tuple parameters) drives both the scattering (which handlers execute) and the gathering (which events to react to).

This creates a fully reactive system where:
- **Scatter** happens through type affordances (`∘par`)
- **Intermediate results** are addressable entities (TupleEntity)
- **Gather** happens through event reactions (`@on`)
- **Type safety** is maintained throughout
- **No orchestration** is needed

The entire pattern emerges from local rules: functions declare what they can process, the framework executes all matches in parallel, results emit events, and handlers react to continue the flow. Complex workflows self-organize from these simple principles.

# The Affordance Philosophy: Types as Possibilities

## From Essence to Potential

Traditional type systems are rooted in an essentialist philosophy. They ask "what *is* this data?" and answer with structural descriptions: a `Student` *has* a name, *has* a GPA, *has* an enrollment date. This mirrors the classical philosophical tradition dating back to Aristotle - things have essential properties that define their being.

The Abstractions framework represents a philosophical shift from essence to potential. Types don't describe what data *is*, but what data *affords* - what transformations are possible, what operations can be applied, what futures can unfold from the current state.

```python
# Essentialist view: Student IS a structure
class Student:
    name: str
    gpa: float
    enrollment_date: datetime

# Affordance view: Student AFFORDS transformations
Student → can_be_enrolled_in(Course)
Student → can_calculate_gpa()
Student → can_graduate_to(Alumni)
Student → can_be_processed_by(functions_accepting_Student)
```

This shift has profound implications for how we think about computation, especially in distributed systems.

## Gibson's Ecological Psychology in Code

James J. Gibson revolutionized psychology by arguing that we don't perceive abstract properties of objects - we perceive their affordances. A cup isn't perceived as "a cylindrical ceramic object with a handle" but as "something I can drink from." The perception is directly of the action possibility, not of abstract properties that we then reason about.

The Abstractions framework applies this insight to computation. When a function encounters an entity, it doesn't ask "what fields does this have?" but "what can I do with this?" The polymorphic parallel operator makes this explicit - it finds all functions that can process an entity and executes them in parallel.

```python
# Traditional: Analyze structure, then decide action
def process_entity(entity):
    if hasattr(entity, 'gpa') and hasattr(entity, 'enrollment_date'):
        # It's probably a student
        return process_student(entity)
    elif hasattr(entity, 'department') and hasattr(entity, 'courses'):
        # It's probably a teacher
        return process_teacher(entity)

# Affordance-based: Let the type system discover possibilities
result = execute_par("process_entity" ∘par (
    "student_processor": Student |
    "teacher_processor": Teacher |
    "person_processor": Person
))
# All applicable processors run in parallel
# The entity "affords" whatever transformations match its type
```

## The Ontology of Possibility

In philosophy, there's a fundamental distinction between the actual and the possible. Traditional programming languages focus on the actual - what data exists right now. The Abstractions framework elevates the possible to first-class status.

### Possibility as Computation

When you declare `Union[Student, Teacher]`, you're not just saying "this could be either type." You're defining a space of possible transformations:

```python
Union[Student, Teacher] = {
    all transformations applicable to Student
    ∪ all transformations applicable to Teacher
}
```

The `∘par` operator explores this possibility space in parallel. It doesn't choose one possibility - it actualizes all possibilities simultaneously, then lets you work with the results.

### Sparsity as Natural Selection

Not all possibilities are actualized. When a `Student` flows through handlers for `Student`, `Teacher`, and `Administrator`, only the `Student` handler executes. The others return `None` - they're possibilities that weren't actualized for this particular entity.

```python
TupleEntity[
    Optional[StudentResult],  # Actualized
    Optional[TeacherResult],  # Possibility not actualized (None)
    Optional[AdminResult]     # Possibility not actualized (None)
]
```

This sparsity isn't a failure - it's information. It tells you which affordances were relevant for this particular entity.

## Types as Capabilities, Not Categories

Traditional type systems are taxonomic - they categorize data into hierarchies. `ClassRepresentative` IS-A `Student` IS-A `Person`. This creates the classic problem: which level of the hierarchy should handle the entity?

The affordance model dissolves this problem. Types are capabilities, not categories. A `ClassRepresentative` doesn't belong to one category - it affords multiple sets of transformations:

- It affords `Student` transformations (calculate GPA, enroll in courses)
- It affords `ClassRepresentative` transformations (schedule meetings, represent class)
- It affords `Person` transformations (send notifications, update contact info)

All these affordances coexist. There's no "correct" level - all levels that match are correct.

## The Phenomenology of Distributed Systems

In distributed systems, the affordance model aligns with reality better than essentialist models. Consider:

### Location-Dependent Affordances

An entity in different services affords different operations:

```python
# Same Student entity, different affordances based on location
RegistrationService: Student → affords → enroll_in_course()
BillingService: Student → affords → calculate_tuition()
HousingService: Student → affords → assign_dormitory()
```

The entity hasn't changed, but its affordances have. This is natural in the affordance model but awkward in essentialist models.

### Emergent Affordances

When entities combine, new affordances emerge:

```python
Student + Course → affords → create_enrollment()
Student + Scholarship → affords → apply_financial_aid()
Student + Violation → affords → initiate_disciplinary_action()
```

These composite affordances aren't properties of either entity alone - they emerge from the relationship.

## The Ethics of Computation

The affordance model has ethical implications. In essentialist systems, entities are passive data to be operated upon. In the affordance model, entities actively afford certain operations while remaining closed to others.

### Capability-Based Security

Affordances are capabilities. An entity that doesn't afford a transformation is naturally protected from it:

```python
PublicStudent = Student without private_fields
PublicStudent → affords → view_public_profile()
PublicStudent → does_not_afford → view_medical_records()
```

Security becomes intrinsic to the type system rather than bolted on through access control.

### Consent Through Affordance

Entities can be designed to afford only operations they consent to:

```python
ConsentingStudent = Student with explicit_permissions
ConsentingStudent → affords → share_data() only_if consent_given
```

## The Metaphysics of Events

Events in the framework aren't just notifications - they're the medium through which possibilities propagate through the system. When an entity is created, its affordances ripple outward through events, activating handlers that can process it.

```python
# Entity creation is a possibility explosion
student = Student(name="Alice", gpa=3.9)
emit(CreatedEvent(student))

# This event carries the affordances outward
# Handlers that can process Student activate
# The possibility space unfolds into actuality
```

Events are how the possible becomes actual in a distributed system.

## Emergence and Self-Organization

The affordance model naturally leads to emergent behavior. You don't program workflows - you define affordances and let workflows emerge:

1. **Entities afford transformations** (based on their types)
2. **Transformations create new entities** (with new affordances)
3. **New affordances trigger new transformations** (through events)
4. **Complex workflows emerge** (without central coordination)

This is computational autopoiesis - the system continuously creates itself through the interplay of affordances and actualizations.

## The Paradox of Choice Resolved

The polymorphic parallel operator resolves an ancient paradox: the problem of choice. Traditional systems force choice ("should we handle this as a Student or as a Person?"). The affordance model says: don't choose - actualize all possibilities in parallel.

This isn't inefficiency - it's completeness. In a world of cheap parallel computation, why choose when you can explore all paths? The sparse tuple results tell you which paths were productive.

## Implications for Programming

The affordance philosophy suggests a new way of programming:

### 1. **Design Affordances, Not Structures**
Instead of asking "what fields should this type have?", ask "what transformations should this type afford?"

### 2. **Think in Possibilities**
Instead of linear workflows, think in possibility spaces that unfold through parallel exploration.

### 3. **Embrace Sparsity**
Not all possibilities actualize, and that's information, not failure.

### 4. **Let Behavior Emerge**
Define local affordances and let global behavior emerge through their interaction.

### 5. **Events as Possibility Propagation**
Use events not just for notification but for propagating possibilities through the system.

## The Future: Possibility-Oriented Programming

The Abstractions framework points toward a new paradigm: Possibility-Oriented Programming (POP). In this paradigm:

- **Types are possibility spaces**
- **Functions are possibility actualizers**
- **Events are possibility propagators**
- **Composition is possibility combination**
- **Programs are possibility gardens** that grow and evolve

This isn't just a technical shift - it's a philosophical reorientation. We stop thinking of programs as machines that transform data and start thinking of them as possibility spaces that unfold through parallel exploration.

## Conclusion: The Dance of Affordance and Actuality

The Abstractions framework embodies a profound philosophical insight: computation is not about transforming essential data structures but about exploring possibility spaces defined by affordances. Types don't describe what data *is* but what data *can become*. Functions don't operate on passive data but actualize possibilities that entities afford. Events don't just notify but propagate possibilities through distributed space.

This creates a programming model more aligned with how complex systems actually work - through local interactions creating global patterns, through possibilities unfolding into actualities, through affordances creating opportunities for transformation.

In the end, the framework suggests that the question "what is this data?" is less important than "what can this data become?" And in a world of distributed systems, parallel computation, and emergent complexity, that might be exactly the right question to ask.


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