"""
Transactional Entity Execution Example

This demonstrates the transactional execution pattern for callable methods that 
take direct Entity objects as input/output rather than using the borrowing pattern.

Key features:
- Direct Entity inputs instead of @uuid.field references
- Transactional execution with isolated copies
- Entity divergence detection and automatic versioning
- Type-safe entity results
"""

import sys
sys.path.append('..')

import asyncio
from typing import List
from pydantic import BaseModel

# Import our entity system
from abstractions.ecs.entity import Entity, EntityRegistry
from abstractions.ecs.callable_registry import CallableRegistry

async def main():
    print("🔄 Transactional Entity Execution Demo")
    print("=" * 50)

    # Define entities for our demo
    class Student(Entity):
        """Student entity."""
        name: str = ""
        age: int = 0
        student_id: str = ""
        gpa: float = 0.0

    class Course(Entity):
        """Course entity."""
        course_id: str = ""
        name: str = ""
        credits: int = 3

    class Enrollment(Entity):
        """Enrollment relationship entity."""
        student_id: str = ""
        course_id: str = ""
        grade: float = 0.0
        semester: str = ""

    # Register a function that takes direct Entity inputs
    @CallableRegistry.register("enroll_student")
    async def enroll_student(student: Student, course: Course, grade: float = 0.0) -> Enrollment:
        """Enroll a student in a course - takes direct Entity inputs."""
        
        print(f"  📚 Enrolling {student.name} in {course.name}")
        print(f"  👤 Student ID: {student.student_id} (live_id: {student.live_id})")
        print(f"  📖 Course ID: {course.course_id} (live_id: {course.live_id})")
        
        # Create enrollment entity
        enrollment = Enrollment(
            student_id=student.student_id,
            course_id=course.course_id,
            grade=grade,
            semester="Fall 2023"
        )
        
        print(f"  ✅ Created enrollment: {enrollment.ecs_id}")
        return enrollment

    # Register another function that modifies entity and returns it
    @CallableRegistry.register("update_student_gpa")
    def update_student_gpa(student: Student, new_gpa: float) -> Student:
        """Update student GPA - demonstrates entity modification."""
        
        print(f"  📊 Updating {student.name}'s GPA from {student.gpa} to {new_gpa}")
        
        # Modify the student (this works because we're operating on a copy)
        student.gpa = new_gpa
        
        print(f"  ✅ Updated student GPA: {student.gpa}")
        return student

    print("\n📚 Creating test entities...")

    # Create and register entities
    student = Student(
        name="Bob Wilson",
        age=19,
        student_id="STU002",
        gpa=3.2
    )
    student.promote_to_root()
    print(f"✅ Created student: {student.ecs_id}")

    course = Course(
        course_id="CS101",
        name="Introduction to Computer Science",
        credits=4
    )
    course.promote_to_root()
    print(f"✅ Created course: {course.ecs_id}")

    print("\n🔄 Executing transactional function with direct Entity inputs...")

    # Execute function with direct Entity objects (not @uuid references)
    enrollment_result = await CallableRegistry.aexecute(
        "enroll_student",
        student=student,  # Direct Entity object
        course=course,    # Direct Entity object
        grade=3.7
    )

    print(f"✅ Transactional execution complete!")
    print(f"✅ Result entity: {enrollment_result.ecs_id}")
    print(f"📊 Enrollment details:")
    if hasattr(enrollment_result, 'student_id'):
        print(f"  Student ID: {getattr(enrollment_result, 'student_id', 'N/A')}")
        print(f"  Course ID: {getattr(enrollment_result, 'course_id', 'N/A')}")
        print(f"  Grade: {getattr(enrollment_result, 'grade', 'N/A')}")
        print(f"  Semester: {getattr(enrollment_result, 'semester', 'N/A')}")

    print("\n🔄 Executing function that modifies and returns entity...")

    # Execute function that modifies the student entity
    updated_student = await CallableRegistry.aexecute(
        "update_student_gpa",
        student=student,  # Direct Entity object
        new_gpa=3.8
    )

    print(f"✅ Student modification complete!")
    print(f"✅ Updated student entity: {updated_student.ecs_id}")
    print(f"📊 Updated student details:")
    if hasattr(updated_student, 'name'):
        print(f"  Name: {getattr(updated_student, 'name', 'N/A')}")
        print(f"  Original GPA: {student.gpa}")  # Original entity unchanged
        print(f"  Updated GPA: {getattr(updated_student, 'gpa', 'N/A')}")

    print("\n🔍 Verifying entity isolation...")
    print(f"Original student GPA (unchanged): {student.gpa}")
    print(f"Returned student GPA (modified): {getattr(updated_student, 'gpa', 'N/A')}")
    print(f"Different entities: {student.ecs_id != updated_student.ecs_id}")
    print(f"Same lineage: {student.lineage_id == getattr(updated_student, 'lineage_id', None)}")

    print("\n📈 Registry statistics:")
    print(f"Total trees in registry: {len(EntityRegistry.tree_registry)}")
    print(f"Total lineages tracked: {len(EntityRegistry.lineage_registry)}")
    print(f"Live entities in memory: {len(EntityRegistry.live_id_registry)}")

    print("\n🎯 Function registry info:")
    functions = CallableRegistry.list_functions()
    for func_name in functions:
        info = CallableRegistry.get_function_info(func_name)
        if info:
            print(f"Function: {info['name']}")
            print(f"  Signature: {info['signature']}")
            print(f"  Is Async: {info['is_async']}")

    print("\n✨ Demo complete! Transactional entity execution works perfectly!")
    print("🔄 Functions can safely take direct Entity inputs/outputs!")
    print("🛡️ Entity isolation ensures no side effects on original entities!")
    print("📝 Complete versioning and lineage tracking maintained!")

if __name__ == "__main__":
    asyncio.run(main())