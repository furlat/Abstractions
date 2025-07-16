#!/usr/bin/env python3
"""
Simple test script for Phase 2: Return Type Analysis and Entity Unpacking

This script tests the core functionality without complex features.
"""

import sys
sys.path.append('.')

from abstractions.ecs.entity import Entity, EntityRegistry
from abstractions.ecs.return_type_analyzer import ReturnTypeAnalyzer, ReturnPattern
from abstractions.ecs.entity_unpacker import EntityUnpacker
from typing import List, Dict


# Test entities
class Student(Entity):
    name: str = ""
    age: int = 0
    
class Course(Entity):
    title: str = ""
    credits: int = 0


def test_basic_return_patterns():
    """Test basic return pattern classification."""
    print("=== Testing Basic Return Pattern Classification ===")
    
    # Create test entities
    student = Student(name="Alice", age=20)
    course = Course(title="Math 101", credits=3)
    
    # Test B1: Single Entity
    print("\n--- B1: Single Entity ---")
    analysis = ReturnTypeAnalyzer.analyze_return(student)
    assert analysis.pattern == ReturnPattern.SINGLE_ENTITY
    assert analysis.entity_count == 1
    print(f"✅ B1 detected: {analysis.pattern}, entities: {analysis.entity_count}")
    
    # Test B2: Tuple of Entities
    print("\n--- B2: Tuple of Entities ---")
    tuple_result = (student, course)
    analysis = ReturnTypeAnalyzer.analyze_return(tuple_result)
    assert analysis.pattern == ReturnPattern.TUPLE_ENTITIES
    assert analysis.entity_count == 2
    print(f"✅ B2 detected: {analysis.pattern}, entities: {analysis.entity_count}")
    
    # Test B3: List of Entities
    print("\n--- B3: List of Entities ---")
    list_result = [student, course]
    analysis = ReturnTypeAnalyzer.analyze_return(list_result)
    assert analysis.pattern == ReturnPattern.LIST_ENTITIES
    assert analysis.entity_count == 2
    print(f"✅ B3 detected: {analysis.pattern}, entities: {analysis.entity_count}")
    
    # Test B7: Non-entity
    print("\n--- B7: Non-entity ---")
    analysis = ReturnTypeAnalyzer.analyze_return("simple string")
    assert analysis.pattern == ReturnPattern.NON_ENTITY
    assert analysis.entity_count == 0
    print(f"✅ B7 detected: {analysis.pattern}, entities: {analysis.entity_count}")


def test_basic_unpacking():
    """Test basic entity unpacking."""
    print("\n=== Testing Basic Entity Unpacking ===")
    
    # Create test entities
    student = Student(name="Bob", age=21)
    course = Course(title="Physics 101", credits=4)
    
    # Test unpacking single entity
    print("\n--- Unpacking Single Entity ---")
    analysis = ReturnTypeAnalyzer.analyze_return(student)
    unpacking_result = EntityUnpacker.unpack_return(student, analysis)
    
    assert len(unpacking_result.primary_entities) == 1
    assert unpacking_result.primary_entities[0] == student
    assert unpacking_result.metadata["unpacking_type"] == "single_entity"
    print(f"✅ Single entity unpacked: {len(unpacking_result.primary_entities)} entity")
    
    # Test unpacking tuple of entities
    print("\n--- Unpacking Tuple of Entities ---")
    tuple_result = (student, course)
    analysis = ReturnTypeAnalyzer.analyze_return(tuple_result)
    unpacking_result = EntityUnpacker.unpack_return(tuple_result, analysis)
    
    assert len(unpacking_result.primary_entities) == 2
    assert unpacking_result.metadata["unpacking_type"] == "sequence"
    assert unpacking_result.metadata["sequence_type"] == "tuple"
    print(f"✅ Tuple unpacked: {len(unpacking_result.primary_entities)} entities")
    
    # Test wrapping non-entity
    print("\n--- Wrapping Non-Entity ---")
    simple_result = "just a string"
    analysis = ReturnTypeAnalyzer.analyze_return(simple_result)
    unpacking_result = EntityUnpacker.unpack_return(simple_result, analysis)
    
    assert len(unpacking_result.primary_entities) == 1
    assert unpacking_result.metadata["unpacking_type"] == "wrapped_non_entity"
    wrapped_entity = unpacking_result.primary_entities[0]
    assert hasattr(wrapped_entity, 'wrapped_value')
    print(f"✅ Non-entity wrapped: {unpacking_result.metadata['original_type']}")


def test_enhanced_function_execution():
    """Test the enhanced FunctionExecution entity."""
    print("\n=== Testing Enhanced FunctionExecution ===")
    
    from abstractions.ecs.entity import FunctionExecution
    from uuid import uuid4
    
    # Create enhanced execution record
    execution = FunctionExecution(
        function_name="test_function",
        input_entity_id=uuid4(),
        output_entity_ids=[uuid4(), uuid4()],
        return_analysis={
            "pattern": "tuple_entities",
            "entity_count": 2
        },
        unpacking_metadata={
            "unpacking_type": "sequence",
            "sequence_type": "tuple"
        }
    )
    
    assert len(execution.output_entity_ids) == 2
    assert execution.return_analysis["pattern"] == "tuple_entities"
    assert execution.unpacking_metadata["unpacking_type"] == "sequence"
    print(f"✅ Enhanced FunctionExecution created with {len(execution.output_entity_ids)} outputs")
    print(f"   - Return pattern: {execution.return_analysis['pattern']}")
    print(f"   - Unpacking type: {execution.unpacking_metadata['unpacking_type']}")


if __name__ == "__main__":
    # Clear registry
    EntityRegistry.tree_registry.clear()
    EntityRegistry.lineage_registry.clear()
    EntityRegistry.live_id_registry.clear()
    EntityRegistry.ecs_id_to_root_id.clear()
    EntityRegistry.type_registry.clear()
    
    # Run tests
    test_basic_return_patterns()
    test_basic_unpacking()
    test_enhanced_function_execution()
    
    print("\n✨ Basic Phase 2 testing complete!")
    print("✅ Return Type Analyzer: Core patterns working")
    print("✅ Entity Unpacker: Basic unpacking functional")
    print("✅ Enhanced FunctionExecution: Ready for integration")