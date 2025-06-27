#!/usr/bin/env python3
"""
Test script for the enhanced ECS address parser functionality.
"""

import sys
sys.path.append('.')

from abstractions.ecs.entity import Entity, EntityRegistry
from abstractions.ecs.ecs_address_parser import ECSAddressParser, InputPatternClassifier
from abstractions.ecs.functional_api import create_composite_entity_with_pattern_detection_advanced
from typing import List, Dict, Optional

# Test entities
class Student(Entity):
    name: str = ""
    age: int = 0
    
class Course(Entity):
    title: str = ""
    credits: int = 0

class AcademicRecord(Entity):
    student_id: str = ""
    grades: List[float] = []
    courses: Dict[str, Course] = {}

def test_enhanced_address_parsing():
    """Test the enhanced address parsing functionality."""
    print("=== Testing Enhanced ECS Address Parser ===")
    
    # Create test entities
    student = Student(name="Alice", age=20)
    student.promote_to_root()
    
    course = Course(title="Math 101", credits=3)
    course.promote_to_root()
    
    record = AcademicRecord(
        student_id="alice123",
        grades=[3.8, 3.9, 4.0],
        courses={"math_101": course}
    )
    record.promote_to_root()
    
    print(f"Created student: {student.ecs_id}")
    print(f"Created course: {course.ecs_id}")
    print(f"Created record: {record.ecs_id}")
    
    # Test 1: Entity-only address resolution
    print("\n--- Test 1: Entity-only address resolution ---")
    try:
        entity_address = f"@{student.ecs_id}"
        resolved_entity, resolution_type = ECSAddressParser.resolve_address_advanced(entity_address)
        print(f"✅ Entity address '{entity_address}' resolved to: {resolved_entity.name} (type: {resolution_type})")
    except Exception as e:
        print(f"❌ Entity address resolution failed: {e}")
    
    # Test 2: Sub-entity via address with list index
    print("\n--- Test 2: Sub-entity via address with list index ---")
    try:
        list_address = f"@{record.ecs_id}.grades.1"  # Second grade
        resolved_value, resolution_type = ECSAddressParser.resolve_address_advanced(list_address)
        print(f"✅ List address '{list_address}' resolved to: {resolved_value} (type: {resolution_type})")
    except Exception as e:
        print(f"❌ List address resolution failed: {e}")
    
    # Test 3: Sub-entity via address with dict key
    print("\n--- Test 3: Sub-entity via address with dict key ---")
    try:
        dict_address = f"@{record.ecs_id}.courses.math_101"
        resolved_value, resolution_type = ECSAddressParser.resolve_address_advanced(dict_address)
        print(f"✅ Dict address '{dict_address}' resolved to entity: {resolved_value.title} (type: {resolution_type})")
    except Exception as e:
        print(f"❌ Dict address resolution failed: {e}")
    
    # Test 4: Advanced pattern classification
    print("\n--- Test 4: Advanced pattern classification ---")
    test_kwargs = {
        "student": student,  # Direct entity
        "student_name": f"@{student.ecs_id}.name",  # Field address
        "student_ref": f"@{student.ecs_id}",  # Entity address
        "grade": f"@{record.ecs_id}.grades.0",  # List address
        "course": f"@{record.ecs_id}.courses.math_101",  # Dict address (sub-entity)
        "threshold": 3.5  # Direct value
    }
    
    try:
        pattern_type, classification = InputPatternClassifier.classify_kwargs_advanced(test_kwargs)
        print(f"✅ Pattern type: {pattern_type}")
        for field_name, field_info in classification.items():
            print(f"  {field_name}: {field_info['type']} -> {field_info['resolution_metadata']}")
    except Exception as e:
        print(f"❌ Advanced pattern classification failed: {e}")

def test_advanced_composite_creation():
    """Test advanced composite entity creation."""
    print("\n=== Testing Advanced Composite Entity Creation ===")
    
    # Get existing entities
    students = [e for e in EntityRegistry.live_id_registry.values() if isinstance(e, Student)]
    records = [e for e in EntityRegistry.live_id_registry.values() if isinstance(e, AcademicRecord)]
    
    if not students or not records:
        print("❌ No test entities found in registry")
        return
        
    student = students[0]
    record = records[0]
    
    # Create a composite entity using advanced patterns
    class AnalysisInput(Entity):
        student_name: str = ""
        student_entity: Optional[Student] = None
        first_grade: float = 0.0
        course_entity: Optional[Course] = None
        threshold: float = 0.0
    
    field_mappings = {
        "student_name": f"@{student.ecs_id}.name",  # Field address
        "student_entity": f"@{student.ecs_id}",  # Entity address
        "first_grade": f"@{record.ecs_id}.grades.0",  # List index address
        "course_entity": f"@{record.ecs_id}.courses.math_101",  # Dict key address (entity)
        "threshold": 3.5  # Direct value
    }
    
    try:
        entity, classification, dependencies = create_composite_entity_with_pattern_detection_advanced(
            AnalysisInput, field_mappings, register=False
        )
        
        print(f"✅ Created composite entity with {len(dependencies)} dependencies")
        print(f"  Student name: {getattr(entity, 'student_name', 'N/A')}")
        student_entity = getattr(entity, 'student_entity', None)
        print(f"  Student entity: {student_entity.name if student_entity else 'None'}")
        print(f"  First grade: {getattr(entity, 'first_grade', 'N/A')}")
        course_entity = getattr(entity, 'course_entity', None)
        print(f"  Course entity: {course_entity.title if course_entity else 'None'}")
        print(f"  Threshold: {getattr(entity, 'threshold', 'N/A')}")
        print(f"  Dependencies: {[str(dep.ecs_id) for dep in dependencies]}")
        
    except Exception as e:
        print(f"❌ Advanced composite creation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Clear registry
    EntityRegistry.tree_registry.clear()
    EntityRegistry.lineage_registry.clear()
    EntityRegistry.live_id_registry.clear()
    EntityRegistry.ecs_id_to_root_id.clear()
    EntityRegistry.type_registry.clear()
    
    test_enhanced_address_parsing()
    test_advanced_composite_creation()
    
    print("\n✨ Enhanced parser testing complete!")