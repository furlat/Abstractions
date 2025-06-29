"""
Fully Async Entity-Native Callable Registry Example

This demonstrates the fully async callable registry with both sync and async functions:

- Complete async execution pipeline
- Mixed sync/async function execution  
- Concurrent function execution
- All proven entity patterns with async support
"""

import sys
sys.path.append('..')

import asyncio
from typing import List
from pydantic import BaseModel
from uuid import uuid4

# Import our entity system
from abstractions.ecs.entity import Entity, EntityRegistry, EntityWithPrimitives
from abstractions.ecs.callable_registry import CallableRegistry

# Import our addressing system
from abstractions.ecs.ecs_address_parser import get, is_address

async def main():
    print("🚀 Async Entity-Native Callable Registry Demo")
    print("=" * 50)

    # Define some entities for our demo
    class Student(Entity):
        """Student entity with basic info."""
        name: str = ""
        age: int = 0
        student_id: str = ""

    class AcademicRecord(Entity):
        """Academic record with grades."""
        student_id: str = ""
        grades: List[float] = []
        semester: str = ""

    class AnalysisResult(BaseModel):
        """Function output model."""
        student_name: str
        average_grade: float
        status: str
        total_courses: int
        analysis_notes: str

    class AsyncAnalysisResult(BaseModel):
        """Async function output model."""
        student_name: str
        average_grade: float
        status: str
        total_courses: int
        analysis_notes: str
        processing_time: float

    # Register a sync function
    @CallableRegistry.register("analyze_student_performance")
    def analyze_student_performance(
        name: str, 
        age: int, 
        grades: List[float],
        threshold: float = 3.0
    ) -> AnalysisResult:
        """Analyze student academic performance synchronously."""
        
        if not grades:
            avg_grade = 0.0
            status = "no_data"
        else:
            avg_grade = sum(grades) / len(grades)
            status = "excellent" if avg_grade >= threshold else "needs_improvement"
        
        # Generate analysis notes
        notes = f"Student aged {age} with {len(grades)} courses completed."
        if avg_grade > 0:
            notes += f" Average performance: {avg_grade:.2f}"
        
        return AnalysisResult(
            student_name=name,
            average_grade=avg_grade,
            status=status,
            total_courses=len(grades),
            analysis_notes=notes
        )

    # Register an async function
    @CallableRegistry.register("analyze_student_performance_async")
    async def analyze_student_performance_async(
        name: str, 
        age: int, 
        grades: List[float],
        threshold: float = 3.0
    ) -> AsyncAnalysisResult:
        """Analyze student academic performance asynchronously."""
        import time
        start_time = time.time()
        
        # Simulate async processing (database lookup, API call, etc.)
        await asyncio.sleep(0.1)
        
        if not grades:
            avg_grade = 0.0
            status = "no_data"
        else:
            avg_grade = sum(grades) / len(grades)
            status = "excellent" if avg_grade >= threshold else "needs_improvement"
        
        processing_time = time.time() - start_time
        
        # Generate analysis notes
        notes = f"Student aged {age} with {len(grades)} courses completed."
        if avg_grade > 0:
            notes += f" Average performance: {avg_grade:.2f}"
        notes += f" (Processed in {processing_time:.3f}s)"
        
        return AsyncAnalysisResult(
            student_name=name,
            average_grade=avg_grade,
            status=status,
            total_courses=len(grades),
            analysis_notes=notes,
            processing_time=processing_time
        )

    # Create and register some test entities
    print("\n📚 Creating test entities...")

    # Create student
    student = Student(
        name="Alice Johnson",
        age=20,
        student_id="STU001"
    )
    student.promote_to_root()
    print(f"✅ Created student: {student.ecs_id}")

    # Create academic record
    record = AcademicRecord(
        student_id="STU001",
        grades=[3.8, 3.9, 3.7, 4.0, 3.6],
        semester="Fall 2023"
    )
    record.promote_to_root()
    print(f"✅ Created academic record: {record.ecs_id}")

    print("\n🔗 Entity addressing examples:")
    print(f"Student name via address: {get(f'@{student.ecs_id}.name')}")
    print(f"Student age via address: {get(f'@{student.ecs_id}.age')}")
    print(f"Grades via address: {get(f'@{record.ecs_id}.grades')}")

    print("\n⚡ Executing sync function with async runtime...")

    # Execute sync function using async execution
    result_entity = await CallableRegistry.aexecute(
        "analyze_student_performance",
        **{
            "name": f"@{student.ecs_id}.name",  # Borrow from student entity
            "age": f"@{student.ecs_id}.age",    # Borrow from student entity  
            "grades": f"@{record.ecs_id}.grades",  # Borrow from record entity
            "threshold": 3.5  # Direct value
        }
    )

    # Handle potential multi-entity return (Phase 4 compatibility)
    if isinstance(result_entity, list):
        actual_result = result_entity[0]  # Take first entity for single-entity functions
        print(f"✅ Sync function executed! Result entities: {len(result_entity)} (using first one)")
    else:
        actual_result = result_entity
        print(f"✅ Sync function executed! Result entity: {actual_result.ecs_id}")
        
    if hasattr(actual_result, 'student_name'):
        print(f"Student Name: {getattr(actual_result, 'student_name', 'N/A')}")
        print(f"Average Grade: {getattr(actual_result, 'average_grade', 'N/A')}")
        print(f"Status: {getattr(actual_result, 'status', 'N/A')}")
        print(f"Analysis Notes: {getattr(actual_result, 'analysis_notes', 'N/A')}")

    print("\n⚡ Executing async function...")

    # Execute async function
    async_result_entity = await CallableRegistry.aexecute(
        "analyze_student_performance_async",
        **{
            "name": f"@{student.ecs_id}.name",
            "age": f"@{student.ecs_id}.age",
            "grades": f"@{record.ecs_id}.grades",
            "threshold": 3.5
        }
    )

    # Handle potential multi-entity return (Phase 4 compatibility)
    if isinstance(async_result_entity, list):
        actual_async_result = async_result_entity[0]  # Take first entity for single-entity functions
        print(f"✅ Async function executed! Result entities: {len(async_result_entity)} (using first one)")
    else:
        actual_async_result = async_result_entity
        print(f"✅ Async function executed! Result entity: {actual_async_result.ecs_id}")
        
    if hasattr(actual_async_result, 'student_name'):
        print(f"Student Name: {getattr(actual_async_result, 'student_name', 'N/A')}")
        print(f"Average Grade: {getattr(actual_async_result, 'average_grade', 'N/A')}")
        processing_time = getattr(actual_async_result, 'processing_time', 0)
        print(f"Processing Time: {processing_time:.3f}s" if isinstance(processing_time, (int, float)) else f"Processing Time: {processing_time}")

    print("\n🚀 Demonstrating concurrent execution...")

    # Execute multiple functions concurrently
    batch_executions = [
        {
            "func_name": "analyze_student_performance",
            "name": f"@{student.ecs_id}.name",
            "age": f"@{student.ecs_id}.age",
            "grades": f"@{record.ecs_id}.grades",
            "threshold": 3.0
        },
        {
            "func_name": "analyze_student_performance_async",
            "name": f"@{student.ecs_id}.name", 
            "age": f"@{student.ecs_id}.age",
            "grades": f"@{record.ecs_id}.grades",
            "threshold": 4.0
        }
    ]

    batch_results = await CallableRegistry.execute_batch(batch_executions)
    
    print(f"✅ Executed {len(batch_results)} functions concurrently!")
    for i, result in enumerate(batch_results):
        # Handle potential multi-entity return (Phase 4 compatibility)
        if isinstance(result, list):
            actual_batch_result = result[0]
            print(f"  Result {i+1}: {len(result)} entities (using first: {actual_batch_result.ecs_id})")
        else:
            actual_batch_result = result
            print(f"  Result {i+1}: {actual_batch_result.ecs_id}")
            
        status = getattr(actual_batch_result, 'status', 'unknown') if hasattr(actual_batch_result, 'status') else 'unknown'
        print(f"    Status: {status}")

    print("\n🔍 Provenance tracking (attribute_source):")
    for field_name, source in actual_result.attribute_source.items():
        if source and field_name not in {'ecs_id', 'live_id', 'created_at', 'forked_at'}:
            print(f"  {field_name} -> sourced from entity {source}")

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
            print(f"  Input Entity Class: {info['input_entity_class']}")
            print(f"  Output Entity Class: {info['output_entity_class']}")
            print(f"  Created: {info['created_at']}")

    print("\n✨ Demo complete! Fully async entity-native function execution!")
    print("🚀 Both sync and async functions execute seamlessly in async runtime!")
    print("⚡ Concurrent execution enables powerful parallel processing!")
    print("📝 Complete audit trail through entity versioning and provenance!")

if __name__ == "__main__":
    asyncio.run(main())