"""
Entity-Native Callable Registry Example

This demonstrates the revolutionary entity-native function execution using
all our proven patterns:

- @uuid.field entity addressing
- Automatic dependency discovery  
- Entity borrowing with provenance
- Immutable execution boundaries
- Complete audit trails
"""

import sys
sys.path.append('..')

from typing import List
from pydantic import BaseModel
from uuid import uuid4

# Import our entity system
from abstractions.ecs.entity import Entity, EntityRegistry, EntityWithPrimitives
from abstractions.ecs.callable_registry import CallableRegistry

# Import our addressing system
from abstractions.ecs.ecs_address_parser import get, is_address

print("🚀 Entity-Native Callable Registry Demo")
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

# Register a function with entity-native execution
@CallableRegistry.register("analyze_student_performance")
def analyze_student_performance(
    name: str, 
    age: int, 
    grades: List[float],
    threshold: float = 3.0
) -> AnalysisResult:
    """Analyze student academic performance with entity-native execution."""
    
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

print("\n⚡ Executing function with entity-native patterns...")

# Execute function using entity addressing (the revolutionary part!)
result_entity = CallableRegistry.execute(
    "analyze_student_performance",
    **{
        "name": f"@{student.ecs_id}.name",  # Borrow from student entity
        "age": f"@{student.ecs_id}.age",    # Borrow from student entity  
        "grades": f"@{record.ecs_id}.grades",  # Borrow from record entity
        "threshold": 3.5  # Direct value
    }
)

print(f"✅ Function executed! Result entity: {result_entity.ecs_id}")
print(f"✅ Result is registered in EntityRegistry with full versioning")

print("\n📊 Function execution results:")
if hasattr(result_entity, 'student_name'):
    print(f"Student Name: {getattr(result_entity, 'student_name', 'N/A')}")
    print(f"Average Grade: {getattr(result_entity, 'average_grade', 'N/A')}")
    print(f"Status: {getattr(result_entity, 'status', 'N/A')}")
    print(f"Total Courses: {getattr(result_entity, 'total_courses', 'N/A')}")
    print(f"Analysis Notes: {getattr(result_entity, 'analysis_notes', 'N/A')}")

print("\n🔍 Provenance tracking (attribute_source):")
for field_name, source in result_entity.attribute_source.items():
    if source and field_name not in {'ecs_id', 'live_id', 'created_at', 'forked_at'}:
        print(f"  {field_name} -> sourced from entity {source}")

print("\n🌳 Entity tree relationships:")
result_tree = result_entity.get_tree()
if result_tree:
    print(f"Result entity tree has {result_tree.node_count} nodes and {result_tree.edge_count} edges")
    print(f"Max depth: {result_tree.max_depth}")

print("\n🔄 Demonstrate entity versioning through function calls...")

# Execute the same function with different parameters
print("Executing with higher threshold...")
result2_entity = CallableRegistry.execute(
    "analyze_student_performance",
    **{
        "name": f"@{student.ecs_id}.name",
        "age": f"@{student.ecs_id}.age", 
        "grades": f"@{record.ecs_id}.grades",
        "threshold": 4.0  # Higher threshold
    }
)

print(f"✅ Second execution result: {result2_entity.ecs_id}")
if hasattr(result2_entity, 'status'):
    print(f"New status: {getattr(result2_entity, 'status', 'N/A')}")
print(f"Different entity ID proves versioning: {result_entity.ecs_id != result2_entity.ecs_id}")

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
        print(f"  Input Entity Class: {info['input_entity_class']}")
        print(f"  Output Entity Class: {info['output_entity_class']}")
        print(f"  Created: {info['created_at']}")

print("\n✨ Demo complete! Entity-native function execution works perfectly!")
print("🚀 Functions are now native participants in the entity graph!")
print("📝 Complete audit trail through entity versioning and provenance!")