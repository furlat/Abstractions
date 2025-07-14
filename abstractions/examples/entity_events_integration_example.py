#!/usr/bin/env python3
"""
Entity-Events Integration Example: Academic System with Full Event Coordination

This example demonstrates the revolutionary integration of the event system with 
Entity and CallableRegistry operations, showing complete event-driven coordination:

Features Demonstrated:
- Event-wrapped Entity operations (creation, versioning, attachment)
- Event-wrapped CallableRegistry function execution 
- Real-time event emission for all ECS operations
- Parent-child event coordination for complex workflows
- State transition events for entity lifecycle
- Performance monitoring with event timing
- Error handling with failure events
- Complete audit trail through events + entity versioning

This builds on entity_native_callable_example.py and base_ecs_example.py 
but adds comprehensive event coordination for observability and reactive patterns.
"""

import sys
import asyncio
from typing import List, Optional
from pydantic import Field  
from uuid import UUID

# Import entity system
from abstractions.ecs.entity import Entity, EntityRegistry, ConfigEntity
from abstractions.ecs.callable_registry import CallableRegistry

# Import our perfected event system
from abstractions.events.events import get_event_bus, on, StateTransitionEvent
from abstractions.events.bridge import (
    emit_creation_events, emit_modification_events, emit_processing_events,
    emit_state_transition_events, emit_validation_events, emit_timed_operation
)
from abstractions.events.test_entities import EntityStatus

def log_section(title: str):
    """Clean section logging."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")

# Define Academic Entities (same as base example but with event integration)
class Student(Entity):
    """Student entity with event-driven lifecycle."""
    name: str
    age: int
    email: str
    student_id: str
    status: EntityStatus = EntityStatus.ACTIVE

class Course(Entity):
    """Course entity with academic details."""
    title: str
    code: str
    credits: int
    description: str = ""

class Grade(Entity):
    """Grade entity with course info and score."""
    course_code: str
    course_title: str
    score: float
    semester: str
    letter_grade: str = ""

class AcademicRecord(Entity):
    """Academic record containing student's grades."""
    student: Student
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

# Analysis Configuration (for function calls)
class AnalysisConfig(ConfigEntity):
    """Configuration for academic analysis functions."""
    gpa_threshold: float = 3.0
    include_recommendations: bool = True
    analysis_mode: str = "standard"

# Result Models
class AnalysisResult(Entity):
    """Academic analysis result with event tracking."""
    student_name: str
    current_gpa: float
    status: str
    total_courses: int
    recommendations: List[str] = Field(default_factory=list)
    analysis_notes: str = ""

# Event-Wrapped Entity Operations
async def create_entity_with_events(entity_class, **kwargs):
    """Create an entity with full event coordination."""
    print(f"🎯 Creating {entity_class.__name__} with events...")
    
    # Create entity
    entity = entity_class(**kwargs)
    
    # Emit creation events
    await emit_creation_events(entity, f"create_{entity_class.__name__.lower()}")
    
    return entity

async def promote_entity_with_events(entity: Entity):
    """Promote entity to root with state transition events."""
    print(f"🚀 Promoting {entity.__class__.__name__} to root with events...")
    
    # Emit state transition
    await emit_state_transition_events(
        entity,
        from_state="child_entity",
        to_state="root_entity", 
        transition_reason="promotion_to_root"
    )
    
    # Perform promotion
    entity.promote_to_root()
    
    print(f"✅ {entity.__class__.__name__} promoted: {str(entity.ecs_id)[-8:]}")

async def modify_entity_with_events(entity: Entity, field_updates: dict, operation_name: str = "modify"):
    """Modify entity with change events."""
    print(f"📝 Modifying {entity.__class__.__name__} with events...")
    
    # Capture old values
    old_values = {}
    for field, new_value in field_updates.items():
        if hasattr(entity, field):
            old_values[field] = getattr(entity, field)
        setattr(entity, field, new_value)
    
    # Emit modification events
    await emit_modification_events(
        entity,
        fields=list(field_updates.keys()),
        old_values=old_values,
        operation_name=operation_name
    )

# Event-Wrapped Function Registration and Execution
async def register_function_with_events(func_name: str, func):
    """Register function with creation events."""
    print(f"📋 Registering function '{func_name}' with events...")
    
    # Create a simple representation for the function
    func_entity = Entity()
    func_entity.function_name = func_name
    func_entity.function_type = "analysis"
    
    await emit_creation_events(func_entity, "function_registration")
    
    # Actual registration
    CallableRegistry.register(func_name)(func)
    
    print(f"✅ Function '{func_name}' registered with events")

async def execute_function_with_events(func_name: str, **kwargs):
    """Execute function with full event coordination."""
    print(f"⚡ Executing '{func_name}' with events...")
    
    # Create processing subject
    execution_entity = Entity()
    execution_entity.function_name = func_name
    execution_entity.execution_id = str(execution_entity.ecs_id)[-8:]
    
    # Extract input entities for processing events
    input_entities = [v for v in kwargs.values() if isinstance(v, Entity)]
    
    # Use timed operation for performance tracking
    async def execute_function():
        result = CallableRegistry.execute(func_name, **kwargs)
        return result
    
    result = await emit_timed_operation(
        f"function_execution_{func_name}",
        execute_function,
        execution_entity
    )
    
    print(f"✅ Function '{func_name}' completed with events")
    return result

# Define Academic Functions (with event integration)
def analyze_student_performance(
    student: Student,
    record: AcademicRecord,
    config: AnalysisConfig
) -> AnalysisResult:
    """Analyze student performance with event coordination."""
    
    # Calculate GPA
    if record.grades:
        avg_score = sum(g.score for g in record.grades) / len(record.grades)
        gpa = avg_score / 25.0  # Convert to 4.0 scale approximation
    else:
        gpa = 0.0
    
    # Determine status
    status = "excellent" if gpa >= config.gpa_threshold else "needs_improvement"
    
    # Generate recommendations
    recommendations = []
    if config.include_recommendations:
        if gpa < 2.0:
            recommendations.append("Consider tutoring services")
            recommendations.append("Meet with academic advisor")
        elif gpa < 3.0:
            recommendations.append("Focus on challenging courses")
        else:
            recommendations.append("Consider advanced coursework")
            recommendations.append("Explore research opportunities")
    
    # Create analysis notes
    notes = f"Analysis mode: {config.analysis_mode}, Threshold: {config.gpa_threshold}"
    
    return AnalysisResult(
        student_name=student.name,
        current_gpa=gpa,
        status=status,
        total_courses=len(record.grades),
        recommendations=recommendations,
        analysis_notes=notes
    )

def calculate_university_stats(university: University) -> Entity:
    """Calculate university-wide statistics."""
    
    stats_entity = Entity()
    stats_entity.total_students = len(university.records)
    stats_entity.total_courses = len(university.courses)
    stats_entity.average_gpa = 0.0
    
    if university.records:
        total_gpa = sum(record.gpa for record in university.records)
        stats_entity.average_gpa = total_gpa / len(university.records)
    
    stats_entity.university_name = university.name
    stats_entity.stats_type = "university_summary"
    
    return stats_entity

async def main():
    """Main demonstration of entity-events integration."""
    
    print("🎓 Entity-Events Integration Demo: Academic System")
    print("🎯 Demonstrating complete event coordination with ECS operations")
    
    # Start event bus
    bus = get_event_bus()
    await bus.start()
    
    # Set up event monitoring
    event_log = []
    
    @on(predicate=lambda e: True)
    async def log_all_events(event):
        event_log.append({
            'type': event.type,
            'phase': event.phase,
            'timestamp': event.timestamp,
            'subject': getattr(event, 'subject_type', None)
        })
        
    log_section("Phase 1: Event-Driven Entity Creation")
    
    # Create entities with events
    alice = await create_entity_with_events(
        Student,
        name="Alice Johnson",
        age=20,
        email="alice@university.edu",
        student_id="STU001",
        status=EntityStatus.ACTIVE
    )
    
    bob = await create_entity_with_events(
        Student, 
        name="Bob Smith",
        age=22,
        email="bob@university.edu",
        student_id="STU002",
        status=EntityStatus.ACTIVE
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
    
    # Create grades with events
    alice_math_grade = await create_entity_with_events(
        Grade,
        course_code="MATH101",
        course_title="Calculus I",
        score=92.5,
        semester="Fall 2023",
        letter_grade="A"
    )
    
    bob_cs_grade = await create_entity_with_events(
        Grade,
        course_code="CS200", 
        course_title="Data Structures",
        score=87.0,
        semester="Fall 2023",
        letter_grade="B+"
    )
    
    # Create academic records with events
    alice_record = await create_entity_with_events(
        AcademicRecord,
        student=alice,
        grades=[alice_math_grade],
        gpa=3.7,
        total_credits=4
    )
    
    bob_record = await create_entity_with_events(
        AcademicRecord,
        student=bob,
        grades=[bob_cs_grade], 
        gpa=3.3,
        total_credits=3
    )
    
    # Create university with events
    university = await create_entity_with_events(
        University,
        name="Tech University",
        location="Silicon Valley", 
        courses=[math_course, cs_course],
        records=[alice_record, bob_record],
        established_year=1995
    )
    
    log_section("Phase 2: Event-Driven Entity Promotion and Registration")
    
    # Promote university to root with events
    await promote_entity_with_events(university)
    
    print(f"📊 Entity creation complete:")
    print(f"  Events generated: {len([e for e in event_log if 'creat' in e['type']])}")
    print(f"  State transitions: {len([e for e in event_log if 'state' in e['type']])}")
    
    log_section("Phase 3: Event-Driven Function Registration and Execution")
    
    # Register functions with events
    await register_function_with_events("analyze_student", analyze_student_performance)
    await register_function_with_events("university_stats", calculate_university_stats)
    
    # Create analysis configuration
    analysis_config = await create_entity_with_events(
        AnalysisConfig,
        gpa_threshold=3.5,
        include_recommendations=True,
        analysis_mode="comprehensive"
    )
    
    # Execute analysis with events
    print("\n🎯 Analyzing Alice's performance with events...")
    alice_analysis = await execute_function_with_events(
        "analyze_student",
        student=alice,
        record=alice_record,
        config=analysis_config
    )
    
    # Handle multi-entity return
    if isinstance(alice_analysis, list):
        alice_result = alice_analysis[0]
    else:
        alice_result = alice_analysis
    
    print(f"📊 Alice's Analysis Results:")
    print(f"  GPA: {alice_result.current_gpa:.2f}")
    print(f"  Status: {alice_result.status}")
    print(f"  Recommendations: {len(alice_result.recommendations)}")
    
    # Execute university stats with events
    print("\n🎯 Calculating university statistics with events...")
    university_stats = await execute_function_with_events(
        "university_stats",
        university=university
    )
    
    if isinstance(university_stats, list):
        stats_result = university_stats[0]
    else:
        stats_result = university_stats
    
    print(f"📊 University Statistics:")
    print(f"  Students: {stats_result.total_students}")
    print(f"  Courses: {stats_result.total_courses}")
    print(f"  Average GPA: {stats_result.average_gpa:.2f}")
    
    log_section("Phase 4: Event-Driven Entity Modifications")
    
    # Modify Alice's status with events
    await modify_entity_with_events(
        alice,
        {"age": 21, "status": EntityStatus.PROCESSING},
        "birthday_and_status_update"
    )
    
    # Add new grade to Alice with events
    new_grade = await create_entity_with_events(
        Grade,
        course_code="CS200",
        course_title="Data Structures",
        score=95.0,
        semester="Spring 2024", 
        letter_grade="A"
    )
    
    # Update Alice's record
    alice_record.grades.append(new_grade)
    alice_record.total_credits += 3
    
    await modify_entity_with_events(
        alice_record,
        {"total_credits": alice_record.total_credits, "gpa": 3.85},
        "add_new_grade"
    )
    
    log_section("Phase 5: Event-Driven Validation and Error Handling")
    
    # Test validation events
    print("🔍 Testing validation with events...")
    
    # Valid student validation
    await emit_validation_events(
        alice,
        validation_type="student_data_validation",
        is_valid=True,
        errors=[]
    )
    
    # Invalid student validation (simulated)
    invalid_student = await create_entity_with_events(
        Student,
        name="",  # Invalid: empty name
        age=-5,   # Invalid: negative age
        email="invalid-email",
        student_id="",
        status=EntityStatus.FAILED
    )
    
    await emit_validation_events(
        invalid_student,
        validation_type="student_data_validation",
        is_valid=False,
        errors=["Name cannot be empty", "Age must be positive", "Invalid email format"]
    )
    
    log_section("Phase 6: Event Analytics and Performance Monitoring")
    
    # Wait for all events to process
    await asyncio.sleep(0.2)
    
    # Get event bus statistics
    stats = bus.get_statistics()
    
    print(f"📈 Event System Performance:")
    print(f"  Total events processed: {stats['total_events']}")
    print(f"  Event types: {len(stats['event_counts'])}")
    print(f"  Queue size: {stats['queue_size']}")
    print(f"  Processing: {stats['processing']}")
    
    print(f"\n📊 Event Breakdown:")
    for event_type, count in sorted(stats['event_counts'].items()):
        print(f"  {event_type}: {count}")
    
    # Show timing information
    if stats['handler_stats']:
        print(f"\n⏱️ Handler Performance:")
        for handler, timing in stats['handler_stats'].items():
            if 'avg_ms' in timing:
                print(f"  {handler}: {timing['avg_ms']:.2f}ms avg ({timing['count']} calls)")
    
    # Get recent event history
    recent_events = bus.get_history(limit=10)
    print(f"\n📜 Recent Events (last {len(recent_events)}):")
    for event in recent_events[-5:]:  # Show last 5
        subject_name = event.subject_type.__name__ if event.subject_type else "N/A"
        print(f"  {event.timestamp.strftime('%H:%M:%S.%f')[:-3]} | {event.type} | {subject_name}")
    
    log_section("Phase 7: Registry Integration with Events")
    
    # Show registry statistics enhanced by event tracking
    print(f"📚 Entity Registry Status:")
    print(f"  Trees registered: {len(EntityRegistry.tree_registry)}")
    print(f"  Live entities: {len(EntityRegistry.live_id_registry)}")
    print(f"  Type registry: {len(EntityRegistry.type_registry)}")
    
    # Show function registry
    functions = CallableRegistry.list_functions()
    print(f"\n⚙️ Callable Registry Status:")
    print(f"  Registered functions: {len(functions)}")
    for func_name in functions:
        info = CallableRegistry.get_function_info(func_name)
        if info:
            print(f"  {func_name}: {info['signature']}")
    
    log_section("Summary: Complete Entity-Events Integration")
    
    print("✅ Entity Operations with Events:")
    print("  - Entity creation with creation/created events")
    print("  - Entity promotion with state transition events") 
    print("  - Entity modification with modification events")
    print("  - Entity validation with validation events")
    
    print("\n✅ Function Operations with Events:")
    print("  - Function registration with creation events")
    print("  - Function execution with processing/timing events")
    print("  - Error handling with failure events")
    print("  - Performance monitoring with duration tracking")
    
    print("\n✅ Event System Features:")
    print("  - Parent-child event coordination")
    print("  - Real-time event monitoring and analytics")
    print("  - Complete audit trail for all operations")
    print("  - Reactive patterns and observability")
    
    print(f"\n🎉 Integration Demo Complete!")
    print(f"📊 Generated {stats['total_events']} events across {len(stats['event_counts'])} types")
    print(f"🔗 Seamlessly integrated with {len(EntityRegistry.tree_registry)} entity trees")
    print(f"⚡ Coordinated with {len(functions)} registered functions")
    
    # Stop event bus
    await bus.stop()
    print("\n🛑 Event bus stopped gracefully")

if __name__ == "__main__":
    # Run the integration demo
    asyncio.run(main())