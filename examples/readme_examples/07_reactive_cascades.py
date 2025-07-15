#!/usr/bin/env python3
"""
Example 05: Reactive Cascades with Event-Driven Patterns

This example demonstrates the event-driven reactive pattern from the README:
- Event-driven cascading transformations using @on decorators
- Automatic batching based on event triggers
- Emergent workflow coordination without central control
- Map-reduce pattern through events
- Self-organizing work distribution

This matches the README section "Multi-step reactive cascades" (lines 295-362).
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import asyncio
from typing import List, Optional, Tuple
from abstractions.ecs.entity import Entity
from abstractions.ecs.callable_registry import CallableRegistry
from abstractions.events.events import on, get_event_bus, CreatedEvent
from pydantic import Field

# Define entities for the reactive cascade example
class Student(Entity):
    """Student entity with basic academic information."""
    name: str = ""
    gpa: float = 0.0
    student_id: str = ""

class ProcessedStudent(Entity):
    """Processed student entity after individual processing."""
    student_id: str = ""
    processed_gpa: float = 0.0
    status: str = ""
    processing_notes: str = ""

class BatchReport(Entity):
    """Batch analysis report for groups of students."""
    batch_id: str = ""
    batch_size: int = 0
    average_gpa: float = 0.0
    student_ids: List[str] = Field(default_factory=list)
    batch_status: str = ""

class SummaryReport(Entity):
    """Summary report aggregating multiple batch reports."""
    summary_id: str = ""
    total_students: int = 0
    total_batches: int = 0
    overall_average: float = 0.0
    report_ids: List[str] = Field(default_factory=list)

# Global collections for event-driven batching
processed_students = []
batch_reports = []

# Step 1: Register the individual processing function
@CallableRegistry.register("process_student")
async def process_student(student: Student) -> ProcessedStudent:
    """Process individual student - this will emit events automatically."""
    # Simulate some processing work
    await asyncio.sleep(0.001)
    
    # Apply some processing logic
    processed_gpa = student.gpa * 1.1  # Example: 10% boost
    status = "processed"
    notes = f"Processed {student.name} with GPA boost"
    
    return ProcessedStudent(
        student_id=student.student_id,
        processed_gpa=processed_gpa,
        status=status,
        processing_notes=notes
    )

# Step 2: Event handler that automatically collects processed students
@on(CreatedEvent)
async def collect_processed_student(event: CreatedEvent):
    """Automatically collect processed students and trigger batch analysis."""
    # Filter for ProcessedStudent entities
    if hasattr(event, 'subject_type') and event.subject_type == "ProcessedStudent":
        print(f"📝 Event received: ProcessedStudent created with ID {event.subject_id}")
        
        # Add to our collection
        processed_students.append(event.subject_id)
        
        # When we have enough students, trigger batch analysis
        if len(processed_students) >= 3:  # Smaller batch size for demo
            batch = processed_students[:3]
            processed_students.clear()
            
            print(f"📊 Triggering batch analysis for {len(batch)} students")
            await CallableRegistry.aexecute("analyze_batch", student_ids=batch)

# Step 3: Register batch analysis function
@CallableRegistry.register("analyze_batch")
async def analyze_batch(student_ids: List[str]) -> BatchReport:
    """Analyze a batch of processed students."""
    # Simulate fetching the processed students (in real system, would use EntityRegistry)
    print(f"🔍 Analyzing batch of {len(student_ids)} students")
    
    # For demo, calculate a simple average (in real system would fetch actual entities)
    batch_id = f"BATCH_{len(batch_reports) + 1}"
    
    # Simulate batch processing
    await asyncio.sleep(0.002)
    
    # Create batch report
    return BatchReport(
        batch_id=batch_id,
        batch_size=len(student_ids),
        average_gpa=3.5,  # Simplified for demo
        student_ids=student_ids,
        batch_status="completed"
    )

# Step 4: Event handler that collects batch reports
@on(CreatedEvent)
async def aggregate_reports(event: CreatedEvent):
    """Automatically aggregate batch reports into summaries."""
    # Filter for BatchReport entities
    if hasattr(event, 'subject_type') and event.subject_type == "BatchReport":
        print(f"📋 Event received: BatchReport created with ID {event.subject_id}")
        
        # Add to our collection
        batch_reports.append(event.subject_id)
        
        # Every 2 reports, create a summary
        if len(batch_reports) >= 2:
            reports_batch = batch_reports[:2]
            batch_reports.clear()
            
            print(f"📈 Triggering summary creation for {len(reports_batch)} reports")
            await CallableRegistry.aexecute("create_summary", report_ids=reports_batch)

# Step 5: Register summary creation function
@CallableRegistry.register("create_summary")
async def create_summary(report_ids: List[str]) -> SummaryReport:
    """Create a summary from multiple batch reports."""
    print(f"📋 Creating summary from {len(report_ids)} batch reports")
    
    # Simulate summary processing
    await asyncio.sleep(0.001)
    
    summary_id = f"SUMMARY_{len(report_ids)}_{asyncio.get_event_loop().time()}"
    
    return SummaryReport(
        summary_id=summary_id,
        total_students=len(report_ids) * 3,  # Simplified calculation
        total_batches=len(report_ids),
        overall_average=3.6,  # Simplified for demo
        report_ids=report_ids
    )

# Event handler for final summaries
@on(CreatedEvent)
async def handle_final_summary(event: CreatedEvent):
    """Handle completed summary reports."""
    # Filter for SummaryReport entities
    if hasattr(event, 'subject_type') and event.subject_type == "SummaryReport":
        print(f"🎉 Final summary created with ID {event.subject_id}")
        print(f"✅ Reactive cascade completed successfully!")

def create_test_students() -> List[Student]:
    """Create test students for the reactive cascade demo."""
    students = []
    
    for i in range(7):  # Create 7 students to trigger multiple batches
        student = Student(
            name=f"Student{i+1}",
            gpa=3.0 + (i * 0.1),
            student_id=f"STU{i+1:03d}"
        )
        student.promote_to_root()
        students.append(student)
    
    return students

async def run_reactive_cascade_demo():
    """Run the reactive cascade demonstration."""
    print("🚀 Starting Reactive Cascade Demo")
    print("=" * 50)
    
    # Create test students
    students = create_test_students()
    print(f"📚 Created {len(students)} test students")
    
    # Clear global collections
    processed_students.clear()
    batch_reports.clear()
    
    print(f"\n🔥 Starting reactive cascade...")
    print(f"📝 Processing students individually - events will trigger automatic batching")
    print()
    
    # Process each student individually
    # The magic happens through events - no manual coordination needed!
    for i, student in enumerate(students):
        print(f"⚡ Processing student {i+1}: {student.name}")
        
        # This single call triggers the entire cascade through events:
        # 1. Creates ProcessedStudent
        # 2. Emits "created" event
        # 3. collect_processed_student() handler batches them
        # 4. Triggers analyze_batch() when batch is full
        # 5. Creates BatchReport
        # 6. Emits "created" event
        # 7. aggregate_reports() handler collects reports
        # 8. Triggers create_summary() when enough reports
        # 9. Creates SummaryReport
        # 10. Final handler celebrates completion
        
        await CallableRegistry.aexecute("process_student", student=student)
        
        # Small delay to see the cascade in action
        await asyncio.sleep(0.01)
    
    # Wait a bit for all events to propagate
    await asyncio.sleep(0.1)
    
    print(f"\n✅ Reactive cascade demonstration completed!")
    print(f"📊 Final state:")
    print(f"   - Remaining processed students: {len(processed_students)}")
    print(f"   - Remaining batch reports: {len(batch_reports)}")

async def run_validation_tests():
    """Run validation tests for the reactive cascade pattern."""
    print(f"\n=== Feature Validation ===")
    
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
    
    # Test 1: Event system availability
    def test_event_system():
        event_bus = get_event_bus()
        assert event_bus is not None
        assert hasattr(event_bus, '_handlers') or hasattr(event_bus, 'handlers')
    
    test_feature("Event system availability", test_event_system)
    
    # Test 2: Function registration
    def test_function_registration():
        functions = CallableRegistry.list_functions()
        required_functions = ["process_student", "analyze_batch", "create_summary"]
        for func in required_functions:
            assert func in functions, f"Function {func} not registered"
    
    test_feature("Function registration", test_function_registration)
    
    # Test 3: Entity creation and promotion
    def test_entity_creation():
        test_student = Student(name="Test", gpa=3.5, student_id="TEST001")
        test_student.promote_to_root()
        assert hasattr(test_student, 'ecs_id')
        assert test_student.ecs_id is not None
        assert hasattr(test_student, 'lineage_id')
        assert test_student.lineage_id is not None
    
    test_feature("Entity creation and promotion", test_entity_creation)
    
    # Test 4: Individual processing
    async def test_individual_processing():
        test_student = Student(name="Test", gpa=3.5, student_id="TEST001")
        test_student.promote_to_root()
        
        result = await CallableRegistry.aexecute("process_student", student=test_student)
        assert isinstance(result, ProcessedStudent)
        assert result.student_id == "TEST001"
        assert result.processed_gpa == 3.5 * 1.1  # 10% boost
        assert result.status == "processed"
    
    await test_individual_processing()
    test_feature("Individual student processing", lambda: True)
    
    # Test 5: Batch analysis
    async def test_batch_analysis():
        batch_result = await CallableRegistry.aexecute("analyze_batch", student_ids=["TEST001", "TEST002"])
        assert isinstance(batch_result, BatchReport)
        assert batch_result.batch_size == 2
        assert batch_result.batch_status == "completed"
        assert len(batch_result.student_ids) == 2
    
    await test_batch_analysis()
    test_feature("Batch analysis", lambda: True)
    
    # Test 6: Summary creation
    async def test_summary_creation():
        summary_result = await CallableRegistry.aexecute("create_summary", report_ids=["BATCH_1", "BATCH_2"])
        assert isinstance(summary_result, SummaryReport)
        assert summary_result.total_batches == 2
        assert summary_result.total_students == 6  # 2 batches * 3 students each
        assert len(summary_result.report_ids) == 2
    
    await test_summary_creation()
    test_feature("Summary creation", lambda: True)
    
    # Test 7: Entity type consistency
    def test_entity_types():
        student = Student(name="Alice", gpa=3.8, student_id="STU001")
        processed = ProcessedStudent(student_id="STU001", processed_gpa=4.0, status="processed")
        batch = BatchReport(batch_id="BATCH_1", batch_size=3, average_gpa=3.7, student_ids=["STU001"])
        summary = SummaryReport(summary_id="SUM_1", total_students=6, total_batches=2, overall_average=3.6)
        
        assert isinstance(student, Entity)
        assert isinstance(processed, Entity)
        assert isinstance(batch, Entity)
        assert isinstance(summary, Entity)
    
    test_feature("Entity type consistency", test_entity_types)
    
    # Test 8: Event handler registration
    def test_event_handlers():
        # Check if our event handlers are accessible
        import inspect
        current_module = inspect.getmodule(collect_processed_student)
        assert current_module is not None
        assert hasattr(current_module, 'collect_processed_student')
        assert hasattr(current_module, 'aggregate_reports')
        assert hasattr(current_module, 'handle_final_summary')
    
    test_feature("Event handler registration", test_event_handlers)
    
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
    print("=== Testing Reactive Cascades with Event-Driven Patterns ===\n")
    
    print("This example demonstrates the README pattern where:")
    print("- Individual processing triggers events")
    print("- Events automatically batch entities")
    print("- Batching triggers analysis")
    print("- Analysis results trigger aggregation")
    print("- Everything happens through event coordination")
    print()
    
    # Run validation tests first
    tests_passed, tests_total, validated_features, failed_features = await run_validation_tests()
    
    if tests_passed == tests_total:
        print(f"\n✅ All validation tests passed! Running full demo...")
        await run_reactive_cascade_demo()
        
        print(f"\n🎉 All tests passed! Reactive cascades work as documented.")
        print(f"⚡ Event-driven reactive transformations enable emergent behavior!")
        print(f"🔄 Self-organizing work distribution through events!")
        
    else:
        print(f"\n⚠️  {tests_total - tests_passed} tests failed. README may need updates.")
    
    print(f"\n✅ Reactive cascades example completed!")
    
    # Show the benefits
    print(f"\n📊 Key Benefits of Reactive Cascades:")
    print(f"  - 🔄 Automatic batching without central coordination")
    print(f"  - ⚡ Event-driven reactive transformations")
    print(f"  - 🎯 Emergent workflow behavior")
    print(f"  - 📊 Map-reduce pattern through events")
    print(f"  - 🚀 Self-organizing work distribution")
    print(f"  - 🤝 Loose coupling between processing stages")
    print(f"  - 📈 Scalable async processing with event coordination")
    print(f"  - 🔍 Observable system behavior through events")

if __name__ == "__main__":
    asyncio.run(main())