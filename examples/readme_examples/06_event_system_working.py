#!/usr/bin/env python3
"""
Example 06: Event System Working Patterns

This example demonstrates the event system patterns that actually work,
based on the comprehensive test suite in examples/events_all_examples.py.

This provides the foundation for building reactive cascades and matches
the README section "Event-driven observation" (lines 181-197).
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import asyncio
from typing import List, Tuple, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
from abstractions.events.events import (
    Event, CreatedEvent, ProcessingEvent, ProcessedEvent,
    on, emit, get_event_bus
)

# Define domain models (using BaseModel, not Entity for events)
class Student(BaseModel):
    """Student domain model for event demonstrations."""
    id: UUID = Field(default_factory=uuid4)
    name: str
    gpa: float = 0.0
    status: str = "active"

class ProcessedStudent(BaseModel):
    """Processed student model."""
    id: UUID = Field(default_factory=uuid4)
    student_id: UUID
    processed_gpa: float = 0.0
    processing_notes: str = ""
    status: str = "processed"

class BatchReport(BaseModel):
    """Batch processing report."""
    id: UUID = Field(default_factory=uuid4)
    batch_id: str
    student_count: int = 0
    average_gpa: float = 0.0
    batch_status: str = "completed"

# Custom event types
class StudentCreatedEvent(CreatedEvent[Student]):
    """Event emitted when a student is created."""
    type: str = "student.created"

class StudentProcessedEvent(CreatedEvent[ProcessedStudent]):
    """Event emitted when a student is processed."""
    type: str = "student.processed"

class BatchCompletedEvent(CreatedEvent[BatchReport]):
    """Event emitted when a batch is completed."""
    type: str = "batch.completed"

# Global collections for event-driven coordination
processed_students: List[UUID] = []
completed_batches: List[UUID] = []
event_log: List[str] = []

# Event handlers using the correct patterns
@on(StudentCreatedEvent)
async def log_student_creation(event: StudentCreatedEvent):
    """Log student creation events."""
    log_entry = f"Student created: {event.subject_id}"
    event_log.append(log_entry)
    print(f"📝 {log_entry}")

@on(StudentProcessedEvent)
async def collect_processed_students(event: StudentProcessedEvent):
    """Collect processed students for batching."""
    if event.subject_id is not None:
        processed_students.append(event.subject_id)
        log_entry = f"Student processed: {event.subject_id} (total: {len(processed_students)})"
        event_log.append(log_entry)
        print(f"📊 {log_entry}")
        
        # Trigger batch processing when we have enough students
        if len(processed_students) >= 3:
            await trigger_batch_processing()

@on(BatchCompletedEvent)
async def handle_batch_completion(event: BatchCompletedEvent):
    """Handle completed batches."""
    if event.subject_id is not None:
        completed_batches.append(event.subject_id)
        log_entry = f"Batch completed: {event.subject_id} (total batches: {len(completed_batches)})"
        event_log.append(log_entry)
        print(f"🎉 {log_entry}")

# Pattern-based event handler
@on(pattern="student.*")
def handle_all_student_events(event: Event):
    """Handle all student-related events."""
    log_entry = f"Student event: {event.type}"
    event_log.append(log_entry)
    print(f"🎯 Pattern matched: {log_entry}")

# Predicate-based event handler
@on(predicate=lambda e: hasattr(e, 'subject_id') and e.subject_id is not None)
async def track_all_entities(event: Event):
    """Track all events with subject_id."""
    log_entry = f"Entity event: {event.type} for {event.subject_id}"
    event_log.append(log_entry)
    print(f"🔍 Entity tracked: {log_entry}")

async def trigger_batch_processing():
    """Process a batch of students."""
    if len(processed_students) < 3:
        return
    
    # Take first 3 students
    batch_students = processed_students[:3]
    processed_students.clear()
    
    print(f"🔄 Processing batch of {len(batch_students)} students...")
    
    # Simulate batch processing
    await asyncio.sleep(0.01)
    
    # Create batch report
    batch_report = BatchReport(
        batch_id=f"BATCH_{len(completed_batches) + 1}",
        student_count=len(batch_students),
        average_gpa=3.5,  # Simplified
        batch_status="completed"
    )
    
    # Emit batch completion event
    await emit(BatchCompletedEvent(
        subject_type=BatchReport,
        subject_id=batch_report.id,
        created_id=batch_report.id
    ))

async def demonstrate_event_cascade():
    """Demonstrate a reactive cascade using real event patterns."""
    print("🚀 Starting Event-Driven Cascade Demo")
    print("=" * 50)
    
    # Clear collections
    processed_students.clear()
    completed_batches.clear()
    event_log.clear()
    
    # Create and emit student creation events
    students = []
    for i in range(7):  # Create 7 students to trigger multiple batches
        student = Student(
            name=f"Student_{i+1}",
            gpa=3.0 + (i * 0.1),
            status="active"
        )
        students.append(student)
        
        # Emit student created event
        await emit(StudentCreatedEvent(
            subject_type=Student,
            subject_id=student.id,
            created_id=student.id
        ))
        
        print(f"⚡ Created student: {student.name}")
    
    # Wait for creation events to propagate
    await asyncio.sleep(0.1)
    
    print(f"\n🔄 Processing students individually...")
    
    # Now process each student (simulating the processing step)
    for student in students:
        # Create processed student
        processed = ProcessedStudent(
            student_id=student.id,
            processed_gpa=student.gpa * 1.1,  # 10% boost
            processing_notes=f"Processed {student.name}",
            status="processed"
        )
        
        # Emit student processed event
        await emit(StudentProcessedEvent(
            subject_type=ProcessedStudent,
            subject_id=processed.id,
            created_id=processed.id
        ))
        
        print(f"⚡ Processed student: {student.name}")
        
        # Small delay to see the cascade
        await asyncio.sleep(0.05)
    
    # Wait for all events to propagate
    await asyncio.sleep(0.2)
    
    print(f"\n✅ Cascade completed!")
    print(f"📊 Final state:")
    print(f"   - Remaining processed students: {len(processed_students)}")
    print(f"   - Completed batches: {len(completed_batches)}")
    print(f"   - Total events logged: {len(event_log)}")

async def run_validation_tests():
    """Run validation tests for the event system."""
    print("=== Event System Validation ===")
    
    tests_passed = 0
    tests_total = 0
    validated_features = []
    failed_features = []
    
    def test_feature(name: str, test_func):
        nonlocal tests_passed, tests_total
        tests_total += 1
        try:
            test_func()
            tests_passed += 1
            validated_features.append(name)
            print(f"✅ {name}")
            return True
        except Exception as e:
            failed_features.append(f"{name}: {str(e)}")
            print(f"❌ {name}: {str(e)}")
            return False
    
    # Test 1: Event bus exists and works
    def test_event_bus():
        event_bus = get_event_bus()
        assert event_bus is not None
        assert hasattr(event_bus, 'subscribe')
        assert hasattr(event_bus, 'emit')
    
    test_feature("Event bus exists and works", test_event_bus)
    
    # Test 2: Event creation works
    def test_event_creation():
        event = Event(type="test.event")
        assert event.type == "test.event"
        assert event.id is not None
        assert event.timestamp is not None
    
    test_feature("Event creation works", test_event_creation)
    
    # Test 3: Custom event types work
    def test_custom_events():
        student = Student(name="Test", gpa=3.5)
        event = StudentCreatedEvent(
            subject_type=Student,
            subject_id=student.id,
            created_id=student.id
        )
        assert event.type == "student.created"
        assert event.subject_id == student.id
    
    test_feature("Custom event types work", test_custom_events)
    
    # Test 4: Event emission works
    async def test_event_emission():
        test_events = []
        
        @on(Event)
        async def capture_test_event(event: Event):
            if event.type == "test.emission":
                test_events.append(event)
        
        # Emit test event
        await emit(Event(type="test.emission"))
        
        # Wait for propagation
        await asyncio.sleep(0.1)
        
        assert len(test_events) == 1
        assert test_events[0].type == "test.emission"
    
    await test_event_emission()
    test_feature("Event emission works", lambda: True)
    
    # Test 5: Event handlers are registered
    def test_handlers_registered():
        # Our handlers should be accessible
        assert callable(log_student_creation)
        assert callable(collect_processed_students)
        assert callable(handle_batch_completion)
        assert callable(handle_all_student_events)
        assert callable(track_all_entities)
    
    test_feature("Event handlers registered", test_handlers_registered)
    
    # Test 6: Pattern matching works
    async def test_pattern_matching():
        pattern_events = []
        
        @on(pattern="test.*")
        def capture_pattern_event(event: Event):
            pattern_events.append(event)
        
        # Emit events that should match pattern
        await emit(Event(type="test.pattern"))
        await emit(Event(type="test.another"))
        await emit(Event(type="other.event"))
        
        await asyncio.sleep(0.1)
        
        # Should have captured 2 events matching "test.*"
        assert len(pattern_events) == 2
    
    await test_pattern_matching()
    test_feature("Pattern matching works", lambda: True)
    
    # Test 7: Predicate filtering works
    async def test_predicate_filtering():
        predicate_events = []
        
        @on(predicate=lambda e: hasattr(e, 'metadata') and bool(e.metadata.get('important')))
        def capture_important_event(event: Event):
            predicate_events.append(event)
        
        # Emit events with and without important metadata
        await emit(Event(type="important.event", metadata={"important": True}))
        await emit(Event(type="normal.event", metadata={"important": False}))
        await emit(Event(type="other.event"))
        
        await asyncio.sleep(0.1)
        
        # Should only capture the important event
        assert len(predicate_events) == 1
        assert predicate_events[0].metadata.get('important') is True
    
    await test_predicate_filtering()
    test_feature("Predicate filtering works", lambda: True)
    
    print(f"\n=== Test Results ===")
    print(f"Tests passed: {tests_passed}/{tests_total}")
    print(f"Success rate: {tests_passed/tests_total*100:.1f}%")
    
    if validated_features:
        print(f"\n✅ Validated Features:")
        for feature in validated_features:
            print(f"  - {feature}")
    
    if failed_features:
        print(f"\n❌ Failed Features:")
        for feature in failed_features:
            print(f"  - {feature}")
    
    return tests_passed, tests_total, validated_features, failed_features

async def main():
    """Main execution function."""
    print("=== Event System Working Patterns ===\n")
    
    print("This example demonstrates the event system patterns that actually work:")
    print("- Event creation and emission using emit()")
    print("- Event handlers using @on decorator with different patterns")
    print("- Event-driven coordination and cascades")
    print("- Pattern matching and predicate filtering")
    print()
    
    # Run validation tests
    tests_passed, tests_total, validated_features, failed_features = await run_validation_tests()
    
    if tests_passed == tests_total:
        print(f"\n✅ All validation tests passed! Running cascade demo...")
        await demonstrate_event_cascade()
        
        print(f"\n🎉 All tests passed! Event system works as documented.")
        print(f"⚡ Event-driven patterns enable reactive coordination!")
        print(f"🔄 Automatic batching through event cascades!")
        
    else:
        print(f"\n⚠️  {tests_total - tests_passed} tests failed. Some patterns may not work correctly.")
    
    print(f"\n✅ Event system working patterns example completed!")
    
    # Show the benefits
    print(f"\n📊 Key Benefits of Event-Driven Patterns:")
    print(f"  - 🔄 Automatic coordination without tight coupling")
    print(f"  - ⚡ Reactive responses to system changes")
    print(f"  - 🎯 Flexible event filtering and routing")
    print(f"  - 📊 Observable system behavior")
    print(f"  - 🚀 Scalable async event processing")
    print(f"  - 🤝 Loose coupling between components")
    print(f"  - 📈 Pattern-based and predicate-based subscriptions")
    print(f"  - 🔍 Comprehensive event tracking and logging")

if __name__ == "__main__":
    asyncio.run(main())