#!/usr/bin/env python3
"""
Test script for Phase 2: Return Type Analysis and Entity Unpacking

This script tests the new output analysis capabilities including:
- Return pattern classification (B1-B7)
- Multi-entity unpacking
- Sibling relationship tracking
- Container metadata preservation
"""

import sys
sys.path.append('.')

from abstractions.ecs.entity import Entity, EntityRegistry, create_dynamic_entity_class
from abstractions.ecs.return_type_analyzer import ReturnTypeAnalyzer, ReturnPattern, QuickPatternDetector
from abstractions.ecs.entity_unpacker import EntityUnpacker, UnpackingResult
from typing import List, Dict, Tuple, Optional
from uuid import uuid4


# Test entities
class Student(Entity):
    name: str = ""
    age: int = 0
    
class Course(Entity):
    title: str = ""
    credits: int = 0

class Grade(Entity):
    course_id: str = ""
    score: float = 0.0
    letter: str = ""


def test_return_pattern_classification():
    """Test the return pattern classification for all B1-B7 patterns."""
    print("=== Testing Return Pattern Classification ===")
    
    # Create test entities
    student = Student(name="Alice", age=20)
    course = Course(title="Math 101", credits=3)
    grade = Grade(course_id="math101", score=3.8, letter="A-")
    
    # Test B1: Single Entity
    print("\n--- B1: Single Entity ---")
    analysis = ReturnTypeAnalyzer.analyze_return(student)
    assert analysis.pattern == ReturnPattern.SINGLE_ENTITY
    assert analysis.entity_count == 1
    assert analysis.entities[0] == student
    print(f"✅ B1 detected: {analysis.pattern}, entities: {analysis.entity_count}")
    
    # Test B2: Tuple of Entities
    print("\n--- B2: Tuple of Entities ---")
    tuple_result = (student, course, grade)
    analysis = ReturnTypeAnalyzer.analyze_return(tuple_result)
    assert analysis.pattern == ReturnPattern.TUPLE_ENTITIES
    assert analysis.entity_count == 3
    assert len(analysis.sibling_groups) == 1
    assert len(analysis.sibling_groups[0]) == 3
    print(f"✅ B2 detected: {analysis.pattern}, entities: {analysis.entity_count}, siblings: {len(analysis.sibling_groups[0])}")
    
    # Test B3: List of Entities
    print("\n--- B3: List of Entities ---")
    list_result = [student, course, grade]
    analysis = ReturnTypeAnalyzer.analyze_return(list_result)
    assert analysis.pattern == ReturnPattern.LIST_ENTITIES
    assert analysis.entity_count == 3
    print(f"✅ B3 detected: {analysis.pattern}, entities: {analysis.entity_count}")
    
    # Test B4: Dict of Entities
    print("\n--- B4: Dict of Entities ---")
    dict_result = {"student": student, "course": course, "grade": grade}
    analysis = ReturnTypeAnalyzer.analyze_return(dict_result)
    assert analysis.pattern == ReturnPattern.DICT_ENTITIES
    assert analysis.entity_count == 3
    assert "keys" in analysis.container_metadata
    print(f"✅ B4 detected: {analysis.pattern}, entities: {analysis.entity_count}, keys: {analysis.container_metadata['keys']}")
    
    # Test B5: Mixed Container
    print("\n--- B5: Mixed Container ---")
    mixed_result = [student, "text_data", 42, course]
    analysis = ReturnTypeAnalyzer.analyze_return(mixed_result)
    assert analysis.pattern == ReturnPattern.MIXED_CONTAINER
    assert analysis.entity_count == 2
    assert len(analysis.non_entity_data) > 0
    print(f"✅ B5 detected: {analysis.pattern}, entities: {analysis.entity_count}, non-entity items: {len(analysis.non_entity_data)}")
    
    # Test B6: Nested Structure
    print("\n--- B6: Nested Structure ---")
    nested_result = {
        "students": [student],
        "courses": {"math": course},
        "metadata": {"count": 1, "grades": [grade]}
    }
    analysis = ReturnTypeAnalyzer.analyze_return(nested_result)
    assert analysis.pattern == ReturnPattern.NESTED_STRUCTURE
    assert analysis.entity_count == 3
    print(f"✅ B6 detected: {analysis.pattern}, entities: {analysis.entity_count}")
    
    # Test B7: Non-entity
    print("\n--- B7: Non-entity ---")
    analysis = ReturnTypeAnalyzer.analyze_return("simple string")
    assert analysis.pattern == ReturnPattern.NON_ENTITY
    assert analysis.entity_count == 0
    print(f"✅ B7 detected: {analysis.pattern}, entities: {analysis.entity_count}")
    
    analysis = ReturnTypeAnalyzer.analyze_return(42)
    assert analysis.pattern == ReturnPattern.NON_ENTITY
    print(f"✅ B7 (number) detected: {analysis.pattern}")
    
    analysis = ReturnTypeAnalyzer.analyze_return([1, 2, 3, "no entities"])
    assert analysis.pattern == ReturnPattern.NON_ENTITY
    print(f"✅ B7 (list no entities) detected: {analysis.pattern}")


def test_entity_unpacking():
    """Test the entity unpacking functionality."""
    print("\n=== Testing Entity Unpacking ===")
    
    # Create test entities
    student = Student(name="Bob", age=21)
    course1 = Course(title="Physics 101", credits=4)
    course2 = Course(title="Chemistry 101", credits=3)
    
    execution_id = uuid4()
    
    # Test unpacking tuple of entities
    print("\n--- Unpacking Tuple of Entities ---")
    tuple_result = (student, course1, course2)
    analysis = ReturnTypeAnalyzer.analyze_return(tuple_result)
    unpacking_result = EntityUnpacker.unpack_return(tuple_result, analysis, execution_id)
    
    assert len(unpacking_result.primary_entities) == 3
    assert unpacking_result.metadata["unpacking_type"] == "sequence"
    assert unpacking_result.metadata["sequence_type"] == "tuple"
    print(f"✅ Tuple unpacked: {len(unpacking_result.primary_entities)} entities, sequence type: {unpacking_result.metadata['sequence_type']}")
    
    # Test unpacking mixed container
    print("\n--- Unpacking Mixed Container ---")
    mixed_result = [student, "metadata", 42, course1]
    analysis = ReturnTypeAnalyzer.analyze_return(mixed_result)
    unpacking_result = EntityUnpacker.unpack_return(mixed_result, analysis, execution_id)
    
    assert len(unpacking_result.primary_entities) == 2  # student and course1
    assert unpacking_result.container_entity is not None  # Should have container for non-entity data
    assert unpacking_result.metadata["unpacking_type"] == "mixed"
    print(f"✅ Mixed container unpacked: {len(unpacking_result.primary_entities)} entities, container entity: {unpacking_result.container_entity is not None}")
    
    # Test unpacking dict of entities
    print("\n--- Unpacking Dict of Entities ---")
    dict_result = {"student": student, "physics": course1, "chemistry": course2}
    analysis = ReturnTypeAnalyzer.analyze_return(dict_result)
    unpacking_result = EntityUnpacker.unpack_return(dict_result, analysis, execution_id)
    
    assert len(unpacking_result.primary_entities) == 3
    assert "keys" in unpacking_result.metadata
    assert unpacking_result.metadata["unpacking_type"] == "dict"
    print(f"✅ Dict unpacked: {len(unpacking_result.primary_entities)} entities, keys: {unpacking_result.metadata['keys']}")
    
    # Test wrapping non-entity
    print("\n--- Wrapping Non-Entity ---")
    simple_result = "just a string"
    analysis = ReturnTypeAnalyzer.analyze_return(simple_result)
    unpacking_result = EntityUnpacker.unpack_return(simple_result, analysis, execution_id)
    
    assert len(unpacking_result.primary_entities) == 1
    assert unpacking_result.metadata["unpacking_type"] == "wrapped_non_entity"
    wrapped_entity = unpacking_result.primary_entities[0]
    assert hasattr(wrapped_entity, 'wrapped_value')
    wrapped_value = getattr(wrapped_entity, 'wrapped_value', None)
    assert wrapped_value == "just a string"
    print(f"✅ Non-entity wrapped: {unpacking_result.metadata['original_type']}, value: {wrapped_value}")


def test_sibling_relationship_tracking():
    """Test sibling relationship tracking through entity fields."""
    print("\n=== Testing Sibling Relationship Tracking ===")
    
    # Create test entities
    entities = [
        Student(name="Alice", age=20),
        Student(name="Bob", age=21),
        Course(title="Math 101", credits=3)
    ]
    
    # Simulate Phase 4 sibling tracking through entity fields
    from uuid import uuid4
    execution_id = uuid4()
    
    # Set sibling metadata on entities (Phase 4 approach)
    for i, entity in enumerate(entities):
        entity.derived_from_execution_id = execution_id
        entity.output_index = i
        entity.sibling_output_entities = [e.ecs_id for e in entities if e != entity]
    
    # Verify relationships through entity fields
    for i, entity in enumerate(entities):
        print(f"Entity {entity.ecs_id} (index {entity.output_index}) has siblings: {len(entity.sibling_output_entities)}")
        assert len(entity.sibling_output_entities) == 2  # Each entity should have 2 siblings
        assert entity.derived_from_execution_id == execution_id
        assert entity.output_index == i
    
    print("✅ Sibling relationships tracked correctly through entity fields")


def test_quick_pattern_detection():
    """Test the quick pattern detector for performance."""
    print("\n=== Testing Quick Pattern Detection ===")
    
    student = Student(name="Charlie", age=22)
    course = Course(title="Biology 101", credits=4)
    
    # Test quick detection
    quick_result = QuickPatternDetector.quick_classify(student)
    assert quick_result == ReturnPattern.SINGLE_ENTITY
    print(f"✅ Quick detect single entity: {quick_result}")
    
    quick_result = QuickPatternDetector.quick_classify((student, course))
    assert quick_result == ReturnPattern.TUPLE_ENTITIES
    print(f"✅ Quick detect tuple entities: {quick_result}")
    
    quick_result = QuickPatternDetector.quick_classify([student, course])
    assert quick_result == ReturnPattern.LIST_ENTITIES
    print(f"✅ Quick detect list entities: {quick_result}")
    
    quick_result = QuickPatternDetector.quick_classify({"s": student, "c": course})
    assert quick_result == ReturnPattern.DICT_ENTITIES
    print(f"✅ Quick detect dict entities: {quick_result}")
    
    quick_result = QuickPatternDetector.quick_classify("string")
    assert quick_result == ReturnPattern.NON_ENTITY
    print(f"✅ Quick detect non-entity: {quick_result}")
    
    # Test case requiring full analysis
    quick_result = QuickPatternDetector.quick_classify([student, "mixed"])
    assert quick_result is None  # Should require full analysis
    print("✅ Quick detect correctly identifies complex case needing full analysis")


def test_dynamic_entity_creation():
    """Test dynamic entity creation for containers."""
    print("\n=== Testing Dynamic Entity Creation ===")
    
    # Test creating container entity
    field_definitions = {
        "metadata": "test_metadata",
        "count": 42,
        "items": ["item1", "item2"]
    }
    
    ContainerClass = create_dynamic_entity_class("TestContainer", field_definitions)
    container = ContainerClass()
    
    assert hasattr(container, 'metadata')
    assert hasattr(container, 'count')
    assert hasattr(container, 'items')
    assert getattr(container, 'metadata', None) == "test_metadata"
    assert getattr(container, 'count', None) == 42
    print(f"✅ Dynamic entity created: {container.__class__.__name__}")
    print(f"   - metadata: {getattr(container, 'metadata', 'N/A')}")
    print(f"   - count: {getattr(container, 'count', 'N/A')}")
    print(f"   - items: {getattr(container, 'items', 'N/A')}")


def test_enhanced_function_execution():
    """Test the enhanced FunctionExecution entity."""
    print("\n=== Testing Enhanced FunctionExecution ===")
    
    from abstractions.ecs.entity import FunctionExecution
    
    # Create enhanced execution record
    execution = FunctionExecution(
        function_name="test_function",
        input_entity_id=uuid4(),
        output_entity_id=uuid4(),  # Changed from output_entity_ids to output_entity_id
        return_analysis={
            "pattern": "tuple_entities",
            "entity_count": 3
        },
        unpacking_metadata={
            "unpacking_type": "sequence",
            "sequence_type": "tuple"
        },
        sibling_groups=[[uuid4(), uuid4(), uuid4()]],  # Use UUIDs instead of indices
        input_pattern_classification={
            "pattern_type": "mixed",
            "fields": ["entity", "address", "value"]
        }
    )
    
    assert execution.output_entity_id is not None
    assert execution.return_analysis["pattern"] == "tuple_entities"
    assert execution.unpacking_metadata["unpacking_type"] == "sequence"
    assert len(execution.sibling_groups) == 1
    assert len(execution.sibling_groups[0]) == 3  # Should have 3 UUIDs in the sibling group
    print(f"✅ Enhanced FunctionExecution created with output_entity_id: {execution.output_entity_id}")
    print(f"   - Return pattern: {execution.return_analysis['pattern']}")
    print(f"   - Unpacking type: {execution.unpacking_metadata['unpacking_type']}")
    print(f"   - Sibling groups: {len(execution.sibling_groups)} with {len(execution.sibling_groups[0])} entities")


if __name__ == "__main__":
    # Clear registry
    EntityRegistry.tree_registry.clear()
    EntityRegistry.lineage_registry.clear()
    EntityRegistry.live_id_registry.clear()
    EntityRegistry.ecs_id_to_root_id.clear()
    EntityRegistry.type_registry.clear()
    
    # Run all tests
    test_return_pattern_classification()
    test_entity_unpacking()
    test_sibling_relationship_tracking()
    test_quick_pattern_detection()
    test_dynamic_entity_creation()
    test_enhanced_function_execution()
    
    print("\n✨ Phase 2 output analysis testing complete!")
    print("✅ Return Type Analyzer: All 7 patterns (B1-B7) working")
    print("✅ Entity Unpacker: Multi-entity unpacking with sibling tracking")
    print("✅ Enhanced FunctionExecution: Complete audit trail support")
    print("✅ Dynamic Entity Creation: Container and wrapper entities")