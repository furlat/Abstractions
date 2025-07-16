#!/usr/bin/env python3
"""
Entity-Events Integration: Correct Reference-Based Event Architecture

DESIGN PHILOSOPHY:
==================

This example demonstrates the CORRECT integration pattern between the Entity Component 
System (ECS) and the Event System, following the architectural principle of 
"Events as Pure Signals" from docs/event_systems.md.

KEY ARCHITECTURAL PRINCIPLES:
============================

1. EVENTS STORE ONLY REFERENCES, NEVER LIVE DATA
   - Events contain UUID references (subject_id, actor_id, etc.)
   - Events contain Type information for validation/FastAPI integration
   - Events NEVER store actual entity objects or their data
   - This prevents stale data and maintains ECS registry as single source of truth

2. BRIDGE FUNCTIONS HANDLE THE TRANSLATION
   - Bridge functions accept real entity objects for convenience
   - They extract UUIDs and type information to create events
   - They emit events with only references and metadata
   - This provides ergonomic API while maintaining architectural purity

3. EVENT HANDLERS FETCH FRESH DATA FROM REGISTRY
   - Event handlers receive events with UUID references
   - They use EntityRegistry to fetch current/fresh entity data when needed
   - This ensures handlers always work with up-to-date information
   - Supports natural patterns like caching, lazy loading, etc.

4. TYPE INFORMATION ENABLES POWERFUL PATTERNS
   - Events include subject_type for runtime type checking
   - Enables automatic FastAPI schema generation
   - Supports type-based event routing and filtering
   - Allows validation of fetched entities against expected types

USAGE PATTERN:
==============

```python
# ✅ CORRECT: Bridge function takes real entity, emits UUID-based events
student = Student(name="Alice", age=20)
await emit_creation_events(student, "student_registration")

# ✅ CORRECT: Event handler gets UUID reference, fetches fresh data
@on(CreatedEvent)
async def handle_student_created(event: CreatedEvent):
    if event.subject_type == Student:
        # Fetch fresh data from registry using UUID reference
        student = EntityRegistry.get_live_entity(event.subject_id)
        # Process with guaranteed fresh data
        print(f"New student: {student.name}")

# ✅ CORRECT: Function execution with entity arguments
result = await execute_function_with_events(
    "analyze_student",
    student=student,  # Real entity passed to function
    config=config     # Bridge extracts UUIDs for events
)
```

ANTI-PATTERNS TO AVOID:
=======================

❌ DON'T store entities in events:
   event.student = student  # WRONG - breaks reference model

❌ DON'T assign arbitrary attributes to typed entities:
   entity.custom_field = "value"  # WRONG - breaks type safety

❌ DON'T cache entity data in event handlers:
   cached_student = event.student  # WRONG - no such field exists

✅ DO use proper typed entity classes for new data structures
✅ DO use EntityRegistry as single source of truth
✅ DO emit events immediately after ECS operations
✅ DO use UUID references for all entity relationships

This architecture provides complete observability and reactive patterns while
maintaining the immutability, versioning, and type safety guarantees of the ECS.
"""

import sys
import asyncio
from typing import List, Optional, Dict, Any
from pydantic import Field
from uuid import UUID, uuid4

# Import entity system
from abstractions.ecs.entity import Entity, EntityRegistry, ConfigEntity
from abstractions.ecs.callable_registry import CallableRegistry

# Import event system components
from abstractions.events.events import get_event_bus, on, CreatedEvent, ModifiedEvent, StateTransitionEvent
from abstractions.events.bridge import (
    emit_creation_events, emit_modification_events, emit_processing_events,
    emit_state_transition_events, emit_validation_events, emit_timed_operation
)

def log_section(title: str):
    """Clean section logging."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")

# Define properly typed entities for the academic system
class Student(Entity):
    """Student entity with proper Pydantic fields."""
    name: str
    age: int
    email: str
    student_id: str

class Course(Entity):
    """Course entity with academic details."""
    title: str
    code: str
    credits: int
    description: str = ""

class Grade(Entity):
    """Grade entity linking students and courses."""
    student_id: str  # Reference to student
    course_code: str
    course_title: str
    score: float
    semester: str
    letter_grade: str = ""

class AcademicRecord(Entity):
    """Academic record containing student's grades."""
    student: Student  # Nested entity reference
    grades: List[Grade] = Field(default_factory=list)
    gpa: float = 0.0
    total_credits: int = 0

class University(Entity):
    """University entity containing all academic data."""
    name: str
    location: str
    courses: List[Course] = Field(default_factory=list)
    records: List[AcademicRecord] = Field(default_factory=list)
    established_year: int = 2000

# Analysis configuration (using ConfigEntity pattern)
class AnalysisConfig(ConfigEntity):
    """Configuration for academic analysis."""
    gpa_threshold: float = 3.0
    include_recommendations: bool = True
    analysis_mode: str = "standard"

# Analysis result entity (properly typed)
class AnalysisResult(Entity):
    """Academic analysis result."""
    student_name: str
    current_gpa: float
    status: str
    total_courses: int
    recommendations: List[str] = Field(default_factory=list)
    analysis_notes: str = ""

# Function execution tracking entity (properly typed)
class FunctionExecution(Entity):
    """Tracks function execution metadata."""
    function_name: str
    execution_id: str
    input_entity_ids: List[UUID] = Field(default_factory=list)
    output_entity_ids: List[UUID] = Field(default_factory=list)
    execution_status: str = "pending"
    duration_ms: Optional[float] = None

# University statistics entity (properly typed)
class UniversityStats(Entity):
    """University-wide statistics."""
    university_name: str
    total_students: int
    total_courses: int
    average_gpa: float
    stats_type: str = "university_summary"

# Event-aware wrapper functions that maintain architectural purity
async def create_entity_with_events(entity_class, **kwargs):
    """
    Create entity and emit creation events.
    
    This function demonstrates the correct pattern:
    1. Create the actual entity object
    2. Use bridge function which extracts UUIDs and types
    3. Events contain only references, never live data
    """
    print(f"🎯 Creating {entity_class.__name__} with event coordination...")
    
    # Create the actual entity
    entity = entity_class(**kwargs)
    
    # Bridge function extracts UUID and type, emits reference-based events
    await emit_creation_events(entity, f"create_{entity_class.__name__.lower()}")
    
    print(f"✅ Created {entity_class.__name__}: {str(entity.ecs_id)[-8:]}")
    return entity

async def promote_entity_with_events(entity: Entity):
    """
    Promote entity to root with state transition events.
    
    Demonstrates state transition pattern with proper reference handling.
    """
    print(f"🚀 Promoting {entity.__class__.__name__} to root...")
    
    # Emit state transition with references only
    await emit_state_transition_events(
        entity,  # Bridge function extracts UUID/type
        from_state="child_entity",
        to_state="root_entity",
        transition_reason="promotion_to_root"
    )
    
    # Perform the actual ECS operation
    entity.promote_to_root()
    
    print(f"✅ Promoted {entity.__class__.__name__}: {str(entity.ecs_id)[-8:]}")

async def modify_entity_with_events(entity: Entity, field_updates: dict, operation_name: str = "modify"):
    """
    Modify entity with change tracking events.
    
    Shows how to emit modification events with before/after state references.
    """
    print(f"📝 Modifying {entity.__class__.__name__}...")
    
    # Capture old values for metadata
    old_values = {}
    for field, new_value in field_updates.items():
        if hasattr(entity, field):
            old_values[field] = getattr(entity, field)
        setattr(entity, field, new_value)
    
    # Bridge function emits events with entity UUID reference only
    await emit_modification_events(
        entity,  # UUID extracted by bridge
        fields=list(field_updates.keys()),
        old_values=old_values,
        operation_name=operation_name
    )
    
    print(f"✅ Modified {entity.__class__.__name__}: {list(field_updates.keys())}")

async def execute_function_with_events(func_name: str, **kwargs):
    """
    Execute function with comprehensive event tracking.
    
    This demonstrates the pattern for function execution events:
    1. Create execution tracking entity (properly typed)
    2. Extract input entities for processing events
    3. Use timed operation wrapper for performance tracking
    4. All events contain only UUID references
    """
    print(f"⚡ Executing '{func_name}' with event coordination...")
    
    # Create properly typed execution tracking entity
    execution = FunctionExecution(
        function_name=func_name,
        execution_id=str(uuid4())[-8:],
        input_entity_ids=[
            entity_id for entity_id in [
                getattr(v, 'ecs_id', getattr(v, 'id', None)) 
                for v in kwargs.values() 
                if isinstance(v, Entity) and hasattr(v, 'ecs_id')
            ] if entity_id is not None
        ]
    )
    
    # Timed operation with reference-based events
    async def execute_function():
        return CallableRegistry.execute(func_name, **kwargs)
    
    result = await emit_timed_operation(
        f"function_execution_{func_name}",
        execute_function,
        execution  # Bridge extracts UUID/type for events
    )
    
    print(f"✅ Function '{func_name}' completed")
    return result

# Academic analysis functions (unchanged - pure business logic)
def analyze_student_performance(
    student: Student,
    record: AcademicRecord,
    config: AnalysisConfig
) -> AnalysisResult:
    """Analyze student academic performance."""
    
    # Calculate GPA from grades
    if record.grades:
        avg_score = sum(g.score for g in record.grades) / len(record.grades)
        gpa = avg_score / 25.0  # Convert to 4.0 scale
    else:
        gpa = 0.0
    
    # Determine status
    status = "excellent" if gpa >= config.gpa_threshold else "needs_improvement"
    
    # Generate recommendations
    recommendations = []
    if config.include_recommendations:
        if gpa < 2.0:
            recommendations.extend(["Consider tutoring", "Meet with advisor"])
        elif gpa < 3.0:
            recommendations.append("Focus on challenging courses")
        else:
            recommendations.extend(["Consider advanced coursework", "Explore research"])
    
    return AnalysisResult(
        student_name=student.name,
        current_gpa=gpa,
        status=status,
        total_courses=len(record.grades),
        recommendations=recommendations,
        analysis_notes=f"Analysis mode: {config.analysis_mode}, Threshold: {config.gpa_threshold}"
    )

def calculate_university_stats(university: University) -> UniversityStats:
    """Calculate university-wide statistics."""
    
    # Calculate average GPA
    avg_gpa = 0.0
    if university.records:
        total_gpa = sum(record.gpa for record in university.records)
        avg_gpa = total_gpa / len(university.records)
    
    return UniversityStats(
        university_name=university.name,
        total_students=len(university.records),
        total_courses=len(university.courses),
        average_gpa=avg_gpa
    )

# Event handlers demonstrating correct reference-based patterns
@on(CreatedEvent)
async def handle_entity_created(event: CreatedEvent):
    """
    Handle entity creation events.
    
    Demonstrates correct pattern:
    1. Receive event with UUID reference and type info
    2. Use type information for filtering/validation
    3. Fetch fresh data from registry when needed
    4. Never assume event contains live data
    """
    if event.subject_type == Student and event.subject_id:
        # ✅ CORRECT: Fetch fresh data using UUID reference
        student = EntityRegistry.get_live_entity(event.subject_id)
        if student and isinstance(student, Student):
            print(f"📚 New student registered: {student.name} (ID: {student.student_id})")

@on(ModifiedEvent)
async def handle_entity_modified(event: ModifiedEvent):
    """
    Handle entity modification events.
    
    Shows how to process modification events with fresh data retrieval.
    """
    if event.subject_type == Student and 'age' in event.fields and event.subject_id:
        # ✅ CORRECT: Use UUID to fetch current state
        student = EntityRegistry.get_live_entity(event.subject_id)
        if student and isinstance(student, Student):
            print(f"🎂 Student birthday: {student.name} is now {student.age}")

@on(StateTransitionEvent)
async def handle_state_transitions(event: StateTransitionEvent):
    """
    Handle state transition events.
    
    Demonstrates reactive patterns with reference-based events.
    """
    print(f"🔄 State transition: {event.from_state} → {event.to_state}")
    if event.transition_reason:
        print(f"   Reason: {event.transition_reason}")

async def main():
    """
    Main demonstration of correct entity-events integration patterns.
    
    This function shows the complete workflow while maintaining
    architectural purity and type safety.
    """
    
    print("🎓 Entity-Events Integration: Reference-Based Architecture Demo")
    print("🎯 Demonstrating correct event patterns with UUID references only")
    
    # Start event bus
    bus = get_event_bus()
    await bus.start()
    
    # Event statistics tracking
    initial_stats = bus.get_statistics()
    
    log_section("Phase 1: Entity Creation with Reference-Based Events")
    
    # Create entities using correct pattern
    alice = await create_entity_with_events(
        Student,
        name="Alice Johnson",
        age=20,
        email="alice@university.edu",
        student_id="STU001"
    )
    
    bob = await create_entity_with_events(
        Student,
        name="Bob Smith", 
        age=22,
        email="bob@university.edu",
        student_id="STU002"
    )
    
    math_course = await create_entity_with_events(
        Course,
        title="Calculus I",
        code="MATH101",
        credits=4,
        description="Introduction to differential calculus"
    )
    
    cs_course = await create_entity_with_events(
        Course,
        title="Data Structures",
        code="CS200", 
        credits=3,
        description="Fundamental data structures and algorithms"
    )
    
    # Create grades
    alice_grade = await create_entity_with_events(
        Grade,
        student_id="STU001",
        course_code="MATH101",
        course_title="Calculus I",
        score=92.5,
        semester="Fall 2023",
        letter_grade="A"
    )
    
    bob_grade = await create_entity_with_events(
        Grade,
        student_id="STU002", 
        course_code="CS200",
        course_title="Data Structures",
        score=87.0,
        semester="Fall 2023",
        letter_grade="B+"
    )
    
    # Create academic records
    alice_record = await create_entity_with_events(
        AcademicRecord,
        student=alice,
        grades=[alice_grade],
        gpa=3.7,
        total_credits=4
    )
    
    bob_record = await create_entity_with_events(
        AcademicRecord,
        student=bob,
        grades=[bob_grade],
        gpa=3.3,
        total_credits=3
    )
    
    # Create university
    university = await create_entity_with_events(
        University,
        name="Tech University",
        location="Silicon Valley",
        courses=[math_course, cs_course],
        records=[alice_record, bob_record],
        established_year=1995
    )
    
    log_section("Phase 2: Entity Promotion with State Events")
    
    # Promote university to root (triggers state transition events)
    await promote_entity_with_events(university)
    
    log_section("Phase 3: Function Registration and Execution")
    
    # Register functions (these work with the existing registry)
    CallableRegistry.register("analyze_student")(analyze_student_performance)
    CallableRegistry.register("university_stats")(calculate_university_stats)
    
    # Create analysis configuration
    config = await create_entity_with_events(
        AnalysisConfig,
        gpa_threshold=3.5,
        include_recommendations=True,
        analysis_mode="comprehensive"
    )
    
    # Execute analysis with event coordination
    print("\n🎯 Analyzing Alice's performance...")
    alice_analysis = await execute_function_with_events(
        "analyze_student",
        student=alice,  # Real entities passed to function
        record=alice_record,
        config=config
    )
    
    # Handle result (accounting for possible multi-entity return)
    if isinstance(alice_analysis, list):
        alice_result = alice_analysis[0]
    else:
        alice_result = alice_analysis
    
    print(f"📊 Analysis Results:")
    print(f"  Student: {alice_result.student_name}")
    print(f"  GPA: {alice_result.current_gpa:.2f}")
    print(f"  Status: {alice_result.status}")
    print(f"  Recommendations: {len(alice_result.recommendations)}")
    
    # Calculate university statistics
    print("\n🎯 Calculating university statistics...")
    stats_result = await execute_function_with_events(
        "university_stats",
        university=university
    )
    
    if isinstance(stats_result, list):
        stats = stats_result[0]
    else:
        stats = stats_result
    
    print(f"📊 University Statistics:")
    print(f"  Name: {stats.university_name}")
    print(f"  Students: {stats.total_students}")
    print(f"  Courses: {stats.total_courses}")
    print(f"  Average GPA: {stats.average_gpa:.2f}")
    
    log_section("Phase 4: Entity Modifications with Change Events")
    
    # Modify Alice's data (triggers modification events)
    await modify_entity_with_events(
        alice,
        {"age": 21},  # Birthday update
        "birthday_update"
    )
    
    # Add new grade to Alice's record
    new_grade = await create_entity_with_events(
        Grade,
        student_id="STU001",
        course_code="CS200",
        course_title="Data Structures", 
        score=95.0,
        semester="Spring 2024",
        letter_grade="A"
    )
    
    # Update academic record
    alice_record.grades.append(new_grade)
    alice_record.total_credits += 3
    
    await modify_entity_with_events(
        alice_record,
        {"total_credits": alice_record.total_credits, "gpa": 3.85},
        "add_new_grade"
    )
    
    log_section("Phase 5: Event System Analytics")
    
    # Wait for all events to process
    await asyncio.sleep(0.2)
    
    # Get comprehensive event statistics
    final_stats = bus.get_statistics()
    
    print(f"📈 Event System Performance:")
    print(f"  Total events processed: {final_stats['total_events']}")
    print(f"  Events since start: {final_stats['total_events'] - initial_stats['total_events']}")
    print(f"  Event types: {len(final_stats['event_counts'])}")
    print(f"  Queue size: {final_stats['queue_size']}")
    print(f"  Currently processing: {final_stats['processing']}")
    
    print(f"\n📊 Event Type Breakdown:")
    for event_type, count in sorted(final_stats['event_counts'].items()):
        if count > 0:
            print(f"  {event_type}: {count}")
    
    # Show recent event history (with references only)
    recent_events = bus.get_history(limit=10)
    print(f"\n📜 Recent Events (UUID references only):")
    for event in recent_events[-5:]:
        subject_type = event.subject_type.__name__ if event.subject_type else "N/A"
        subject_ref = str(event.subject_id)[-8:] if event.subject_id else "N/A"
        print(f"  {event.timestamp.strftime('%H:%M:%S.%f')[:-3]} | {event.type} | {subject_type}({subject_ref})")
    
    log_section("Phase 6: Registry Integration Status")
    
    print(f"📚 Entity Registry Status:")
    print(f"  Trees registered: {len(EntityRegistry.tree_registry)}")
    print(f"  Live entities: {len(EntityRegistry.live_id_registry)}")
    print(f"  Type registry: {len(EntityRegistry.type_registry)}")
    
    functions = CallableRegistry.list_functions()
    print(f"\n⚙️ Function Registry Status:")
    print(f"  Registered functions: {len(functions)}")
    for func_name in functions:
        print(f"  - {func_name}")
    
    log_section("Summary: Reference-Based Event Architecture Success")
    
    print("✅ Architectural Principles Maintained:")
    print("  - Events contain only UUID references, never live data")
    print("  - Type information preserved for validation/FastAPI integration")
    print("  - EntityRegistry remains single source of truth") 
    print("  - Event handlers fetch fresh data when needed")
    print("  - Complete type safety with Pydantic validation")
    
    print("\n✅ Event Patterns Demonstrated:")
    print("  - Entity creation/modification with reference events")
    print("  - State transitions with proper reference handling")
    print("  - Function execution with performance tracking")
    print("  - Reactive event handlers with fresh data access")
    
    print("\n✅ Integration Benefits Achieved:")
    print("  - Complete observability without data duplication")
    print("  - Reactive patterns with architectural purity")
    print("  - Type-safe event processing")
    print("  - Performance monitoring and analytics")
    
    print(f"\n🎉 Demo Complete!")
    print(f"📊 Generated {final_stats['total_events'] - initial_stats['total_events']} events")
    print(f"🔗 All events contain UUID references only - no data duplication")
    print(f"🎯 Architecture maintains ECS purity with reactive capabilities")
    
    # Stop event bus
    await bus.stop()
    print("\n🛑 Event bus stopped gracefully")

if __name__ == "__main__":
    asyncio.run(main())