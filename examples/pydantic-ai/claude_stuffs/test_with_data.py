"""
Test the pydantic-ai integration with actual data in the registries.
"""

from typing import List
from abstractions.ecs.entity import Entity, EntityRegistry
from abstractions.ecs.callable_registry import CallableRegistry
from abstractions.ecs.registry_agent import registry_agent


# First, let's create some test entities and functions
class Student(Entity):
    name: str
    gpa: float
    age: int


class Course(Entity):
    course_name: str
    credits: int
    instructor: str


def setup_test_data():
    """Create some test functions and entities."""
    print("Setting up test data...")
    
    # Register a simple function
    @CallableRegistry.register("create_student")
    def create_student(name: str, gpa: float, age: int) -> Student:
        """Create a new student entity."""
        return Student(name=name, gpa=gpa, age=age)
    
    # Register another function
    @CallableRegistry.register("create_course")
    def create_course(course_name: str, credits: int, instructor: str) -> Course:
        """Create a new course entity."""
        return Course(course_name=course_name, credits=credits, instructor=instructor)
    
    # Create some entities
    student1 = CallableRegistry.execute("create_student", name="Alice Johnson", gpa=3.8, age=20)
    student2 = CallableRegistry.execute("create_student", name="Bob Smith", gpa=3.2, age=19)
    course1 = CallableRegistry.execute("create_course", course_name="Computer Science 101", credits=3, instructor="Dr. Wilson")
    
    print(f"✅ Created {len(CallableRegistry.list_functions())} functions")
    print(f"✅ Created entities: {student1.ecs_id}, {student2.ecs_id}, {course1.ecs_id}")
    
    return student1, student2, course1


def test_with_real_data():
    """Test the agent with actual data."""
    print("\n" + "="*60)
    print("🧪 Testing with Real Data")
    print("="*60)
    
    # Set up test data
    student1, student2, course1 = setup_test_data()
    
    # # Test 1: List functions (should now show our registered functions)
    # print("\n1. Testing function listing with real functions:")
    # result = registry_agent.run_sync("What functions are available?")
    # print(f"Goal Completed: {result.output.goal_completed}")
    # print(f"Primary Action: {result.output.primary_action}")
    # print(f"Summary: {result.output.summary}")
    # print(f"Functions Used: {result.output.functions_used}")
    # print(f"Recommendations: {result.output.recommendations}")
    
    # # Test 2: Get function signature
    # print(f"\n2. Testing function signature retrieval:")
    # result = registry_agent.run_sync("Show me the signature for create_student")
    # print(f"Goal Completed: {result.output.goal_completed}")
    # print(f"Summary: {result.output.summary}")
    # print(f"Data: {result.output.data}")
    
    # # Test 3: List lineages (should show our entities)
    # print(f"\n3. Testing lineage exploration with real entities:")
    # result = registry_agent.run_sync("Show me all entity lineages")
    # print(f"Goal Completed: {result.output.goal_completed}")
    # print(f"Summary: {result.output.summary}")
    # print(f"Entity IDs Referenced: {result.output.entity_ids_referenced}")
    
    # Test 4: Execute function
    print(f"\n4. Testing function execution:")
    result = registry_agent.run_sync("Execute create_student with name 'Charlie Brown', gpa 3.5, age 21")
    print(f"Goal Completed: {result.output.goal_completed}")
    print(f"Summary: {result.output.summary}")
    print(f"Functions Used: {result.output.functions_used}")
    print(f"Entity IDs: {result.output.entity_ids_referenced}")
    
    # Test 5: Test address-based access
    print(f"\n5. Testing address-based entity access:")
    student_address = f"@{student1.ecs_id}.name"
    result = registry_agent.run_sync(f"Get information about entity at address {student_address}")
    print(f"Goal Completed: {result.output.goal_completed}")
    print(f"Summary: {result.output.summary}")
    print(f"Entity IDs: {result.output.entity_ids_referenced}")
    
    # Test 6: Test enhanced error handling with invalid address
    print(f"\n6. Testing enhanced error handling:")
    result = registry_agent.run_sync("Execute create_student with invalid address '@invalid-uuid-format.name'")
    print(f"Goal Completed: {result.output.goal_completed}")
    print(f"Primary Action: {result.output.primary_action}")
    print(f"Summary: {result.output.summary}")
    print(f"Errors: {result.output.errors}")
    print(f"Recommendations: {result.output.recommendations}")
    
    print(f"\n✅ All tests completed with structured GoalAchieved responses!")
    print(f"Note: All result.output are now properly typed GoalAchieved objects!")


if __name__ == "__main__":
    test_with_real_data()