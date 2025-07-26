"""
Patterns 6 & 7 Debug - Minimal Isolation Test

This isolates just the problematic patterns 6 and 7 to debug the 
"entity tree already registered" error without any event wrappers.
"""

import asyncio
from typing import Tuple
from abstractions.ecs.entity import Entity
from abstractions.ecs.callable_registry import CallableRegistry

# Test entities
class Student(Entity):
    name: str = ""
    gpa: float = 0.0

class AcademicRecord(Entity):
    student_id: str = ""
    total_credits: int = 0
    graduation_eligible: bool = False

class ClassStatistics(Entity):
    class_average: float = 0.0
    student_count: int = 0
    highest_gpa: float = 0.0
    lowest_gpa: float = 0.0

# Pattern 5: Multiple Direct Entity References (for contamination)
@CallableRegistry.register("calculate_class_average")
async def calculate_class_average(student1: Student, student2: Student, student3: Student) -> ClassStatistics:
    """Pattern 5: Multiple direct entity references."""
    print(f"🔧 Pattern 5: Processing {student1.name}, {student2.name}, {student3.name}")
    gpas = [student1.gpa, student2.gpa, student3.gpa]
    result = ClassStatistics(
        class_average=sum(gpas) / len(gpas),
        student_count=3,
        highest_gpa=max(gpas),
        lowest_gpa=min(gpas)
    )
    print(f"🔧 Pattern 5: Computed class average {result.class_average:.2f}")
    return result

# Pattern 6: Same Entity In, Same Entity Out (Mutation)
@CallableRegistry.register("update_student_gpa")
async def update_student_gpa(student: Student) -> Student:
    """Pattern 6: Mutation - same entity in and out."""
    print(f"🔧 Pattern 6: Received student {student.name} (GPA: {student.gpa})")
    student.gpa = min(4.0, student.gpa + 0.1)  # Small boost
    print(f"🔧 Pattern 6: Updated GPA to {student.gpa}")
    return student

# Pattern 7: Same Entity In, Multiple Entities Out (One Continues Lineage)
@CallableRegistry.register("split_student_record")
async def split_student_record(student: Student) -> Tuple[Student, AcademicRecord]:
    """Pattern 7: Split into multiple entities, one continues lineage."""
    print(f"🔧 Pattern 7: Received student {student.name} (GPA: {student.gpa})")
    record = AcademicRecord(
        student_id=str(student.ecs_id),
        total_credits=48,
        graduation_eligible=student.gpa >= 3.0
    )
    print(f"🔧 Pattern 7: Created academic record for {student.name}")
    return student, record

async def test_patterns_6_7():
    """Test patterns 5, 6, and 7 with entity reuse to reproduce the real problem."""
    
    print("🚀 Testing Entity Reuse Across Multiple Registry Calls")
    print("=" * 60)
    
    try:
        # Create test entities EXACTLY like the main test
        print("\n📝 Creating test entities...")
        
        student1 = Student(name="Alice", gpa=3.8)
        student1.promote_to_root()
        print(f"Created Student1 (Alice): {student1.ecs_id}")
        
        student2 = Student(name="Bob", gpa=3.2)
        student2.promote_to_root()
        print(f"Created Student2 (Bob): {student2.ecs_id}")
        
        student3 = Student(name="Carol", gpa=3.5)
        student3.promote_to_root()
        print(f"Created Student3 (Carol): {student3.ecs_id}")
        
        print(f"\n🔍 Initial entity states:")
        print(f"  Alice: {student1.name}, GPA: {student1.gpa}, ID: {student1.ecs_id}")
        print(f"  Bob: {student2.name}, GPA: {student2.gpa}, ID: {student2.ecs_id}")
        print(f"  Carol: {student3.name}, GPA: {student3.gpa}, ID: {student3.ecs_id}")
        
        # FIRST: Test Pattern 5 to "contaminate" the entities
        print(f"\n{'='*60}")
        print(f"🎯 Testing Pattern 5: calculate_class_average (CONTAMINATION)")
        print(f"{'='*60}")
        
        print(f"Calling calculate_class_average with ALL THREE entities...")
        result5 = await CallableRegistry.aexecute("calculate_class_average",
                                                   student1=student1,
                                                   student2=student2,
                                                   student3=student3)
        print(f"Pattern 5 Result: {result5}")
        print(f"Pattern 5 completed - entities now have registry history")
        
        # NOW: Test Pattern 6 with the REUSED student2
        print(f"\n{'='*60}")
        print(f"🎯 Testing Pattern 6: update_student_gpa (REUSED ENTITY)")
        print(f"{'='*60}")
        
        print(f"Calling update_student_gpa with REUSED Bob entity...")
        result6 = await CallableRegistry.aexecute("update_student_gpa", student=student2)
        print(f"Pattern 6 Result: {result6}")
        print(f"Result type: {type(result6)}")
        
        # Handle both single entity and list returns
        if isinstance(result6, list):
            if result6 and hasattr(result6[0], 'ecs_id'):
                print(f"Result ECS ID: {result6[0].ecs_id}")
                if isinstance(result6[0], Student):
                    print(f"Result GPA: {result6[0].gpa}")
        elif hasattr(result6, 'ecs_id'):
            print(f"Result ECS ID: {result6.ecs_id}")
            if isinstance(result6, Student):
                print(f"Result GPA: {result6.gpa}")
        
        # FINALLY: Test Pattern 7 with the REUSED student3
        print(f"\n{'='*60}")
        print(f"🎯 Testing Pattern 7: split_student_record (REUSED ENTITY)")
        print(f"{'='*60}")
        
        print(f"Calling split_student_record with REUSED Carol entity...")
        result7 = await CallableRegistry.aexecute("split_student_record", student=student3)
        print(f"Pattern 7 Result: {result7}")
        print(f"Result type: {type(result7)}")
        
        if isinstance(result7, (list, tuple)):
            print(f"Result is collection with {len(result7)} items:")
            for i, item in enumerate(result7):
                print(f"  [{i}]: {type(item).__name__}")
                if hasattr(item, 'ecs_id'):
                    print(f"       ECS ID: {item.ecs_id}")
                if isinstance(item, Student) and hasattr(item, 'gpa'):
                    print(f"       GPA: {item.gpa}")
                if isinstance(item, AcademicRecord) and hasattr(item, 'total_credits'):
                    print(f"       Credits: {item.total_credits}")
        elif hasattr(result7, 'ecs_id'):
            print(f"Single result ECS ID: {result7.ecs_id}")
        
        print(f"\n✅ All patterns executed successfully with entity reuse!")
        
    except Exception as e:
        print(f"❌ Error during execution: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()

# Run the isolated test
print("🔧 Running isolated patterns 6 & 7 debug test...")
asyncio.run(test_patterns_6_7())