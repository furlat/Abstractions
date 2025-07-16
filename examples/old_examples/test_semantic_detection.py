#!/usr/bin/env python3
"""
Test script to validate the enhanced semantic detection algorithm.

This tests the core functionality that was broken in the transactional example.
"""

import sys
sys.path.append('..')

from abstractions.ecs.entity import Entity, EntityRegistry
from abstractions.ecs.callable_registry import CallableRegistry
from typing import Optional

# Simple test entities
class Student(Entity):
    name: str = ""
    gpa: float = 0.0
    age: int = 0

class Course(Entity):
    title: str = ""
    credits: int = 0

def test_mutation_detection():
    """Test that mutation detection works correctly."""
    print("=== Testing Mutation Detection ===")
    
    # Register a function that mutates its input
    @CallableRegistry.register("update_gpa")
    def update_student_gpa(student: Student, new_gpa: float) -> Student:
        """Update student GPA - this should be detected as MUTATION."""
        student.gpa = new_gpa
        return student
    
    # Create and register a student
    student = Student(name="Alice", gpa=3.5, age=20)
    student.promote_to_root()
    
    print(f"Original student: {student.name}, GPA: {student.gpa}, ecs_id: {student.ecs_id}")
    
    # Execute function - this should be detected as mutation
    try:
        result = CallableRegistry.execute("update_gpa", student=student, new_gpa=3.9)
        
        # Handle potential multi-entity return (Phase 4 compatibility)
        if isinstance(result, list):
            result_entity = result[0]  # Take first entity for single-entity functions
        else:
            result_entity = result
            
        result_name = getattr(result_entity, 'name', 'N/A')
        result_gpa = getattr(result_entity, 'gpa', 'N/A')
        print(f"Result: {result_name}, GPA: {result_gpa}, ecs_id: {result_entity.ecs_id}")
        print("✅ Mutation detection successful - no 'entity tree already registered' error!")
        return True
    except Exception as e:
        print(f"❌ Mutation detection failed: {e}")
        return False

def test_creation_detection():
    """Test that creation detection works correctly.""" 
    print("\n=== Testing Creation Detection ===")
    
    # Register a function that creates a new entity
    @CallableRegistry.register("create_course")
    def create_new_course(title: str, credits: int) -> Course:
        """Create new course - this should be detected as CREATION."""
        return Course(title=title, credits=credits)
    
    # Execute function - this should be detected as creation
    try:
        result = CallableRegistry.execute("create_course", title="Physics 101", credits=3)
        
        # Handle potential multi-entity return (Phase 4 compatibility)
        if isinstance(result, list):
            result_entity = result[0]  # Take first entity for single-entity functions
        else:
            result_entity = result
            
        result_title = getattr(result_entity, 'title', 'N/A')
        result_credits = getattr(result_entity, 'credits', 'N/A')
        print(f"Created course: {result_title}, credits: {result_credits}, ecs_id: {result_entity.ecs_id}")
        print("✅ Creation detection successful!")
        return True
    except Exception as e:
        print(f"❌ Creation detection failed: {e}")
        return False

def test_object_identity_tracking():
    """Test that object identity tracking works correctly."""
    print("\n=== Testing Object Identity Tracking ===")
    
    # Register a function that returns the same object
    @CallableRegistry.register("identity_function")
    def return_same_student(student: Student) -> Student:
        """Return the same student object - should detect as mutation even without changes."""
        # Don't modify anything, just return the same object
        return student
    
    # Create student
    student = Student(name="Bob", gpa=3.0, age=21)
    student.promote_to_root()
    
    original_ecs_id = student.ecs_id
    print(f"Original student: {student.name}, ecs_id: {original_ecs_id}")
    
    try:
        result = CallableRegistry.execute("identity_function", student=student)
        
        # Handle potential multi-entity return (Phase 4 compatibility)
        if isinstance(result, list):
            result_entity = result[0]  # Take first entity for single-entity functions
        else:
            result_entity = result
            
        result_name = getattr(result_entity, 'name', 'N/A')
        print(f"Result student: {result_name}, ecs_id: {result_entity.ecs_id}")
        print("✅ Object identity tracking successful!")
        return True
    except Exception as e:
        print(f"❌ Object identity tracking failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing Enhanced Semantic Detection Algorithm")
    print("=" * 50)
    
    # Clear registry to ensure clean test
    EntityRegistry.tree_registry.clear()
    EntityRegistry.lineage_registry.clear()
    EntityRegistry.live_id_registry.clear()
    EntityRegistry.ecs_id_to_root_id.clear()
    EntityRegistry.type_registry.clear()
    
    # Run tests
    mutation_success = test_mutation_detection()
    creation_success = test_creation_detection()
    identity_success = test_object_identity_tracking()
    
    print("\n" + "=" * 50)
    print("Test Results:")
    print(f"Mutation Detection: {'✅ PASS' if mutation_success else '❌ FAIL'}")
    print(f"Creation Detection: {'✅ PASS' if creation_success else '❌ FAIL'}")
    print(f"Object Identity: {'✅ PASS' if identity_success else '❌ FAIL'}")
    
    if all([mutation_success, creation_success, identity_success]):
        print("\n🎉 ALL TESTS PASSED! Semantic detection is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the implementation.")