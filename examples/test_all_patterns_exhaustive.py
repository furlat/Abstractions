#!/usr/bin/env python3
"""
Exhaustive Pattern Testing for Phase 2: Return Type Analysis and Entity Unpacking

This script systematically tests ALL return patterns (B1-B7) with multiple variations
to ensure complete coverage and correctness of the implementation.

Test Coverage:
- B1: Single Entity (basic entity, different entity types)
- B2: Tuple of Entities (2 entities, 3+ entities, mixed types)
- B3: List of Entities (empty list, single item, multiple items)
- B4: Dict of Entities (different key types, empty dict)
- B5: Mixed Container (entities + primitives in lists/tuples/dicts)
- B6: Nested Structure (complex nested combinations)
- B7: Non-entity (primitives, empty containers, objects)
"""

import sys
sys.path.append('.')

from abstractions.ecs.entity import Entity, EntityRegistry, create_dynamic_entity_class
from abstractions.ecs.return_type_analyzer import ReturnTypeAnalyzer, ReturnPattern, QuickPatternDetector
from abstractions.ecs.entity_unpacker import EntityUnpacker, ContainerReconstructor
from typing import List, Dict, Tuple, Optional, Any, Callable
from uuid import uuid4
from datetime import datetime


# Test entity classes
class Student(Entity):
    name: str = ""
    age: int = 0
    gpa: float = 0.0

class Course(Entity):
    title: str = ""
    credits: int = 0
    department: str = ""

class Grade(Entity):
    course_id: str = ""
    student_id: str = ""
    score: float = 0.0
    letter: str = ""

class Assignment(Entity):
    title: str = ""
    due_date: str = ""
    points: int = 0


def create_test_entities():
    """Create a consistent set of test entities."""
    return {
        'student1': Student(name="Alice", age=20, gpa=3.8),
        'student2': Student(name="Bob", age=21, gpa=3.6),
        'course1': Course(title="Math 101", credits=3, department="Mathematics"),
        'course2': Course(title="Physics 101", credits=4, department="Physics"),
        'grade1': Grade(course_id="math101", student_id="alice", score=3.8, letter="A-"),
        'grade2': Grade(course_id="phys101", student_id="bob", score=3.6, letter="B+"),
        'assignment1': Assignment(title="Homework 1", due_date="2024-01-15", points=100),
        'assignment2': Assignment(title="Midterm Exam", due_date="2024-02-15", points=200)
    }


class PatternTester:
    """Comprehensive pattern testing class."""
    
    def __init__(self):
        self.entities = create_test_entities()
        self.test_results = []
        self.error_count = 0
    
    def log_test(self, test_name: str, pattern: Optional[ReturnPattern], expected: ReturnPattern, 
                 entity_count: int, success: bool, details: str = ""):
        """Log test results."""
        status = "✅ PASS" if success else "❌ FAIL"
        self.test_results.append({
            'test': test_name,
            'pattern': pattern.value if pattern else "None",
            'expected': expected.value,
            'entity_count': entity_count,
            'status': status,
            'details': details
        })
        if not success:
            self.error_count += 1
        print(f"{status} {test_name}: {pattern.value if pattern else 'None'} "
              f"(expected: {expected.value}, entities: {entity_count})")
        if details:
            print(f"    Details: {details}")
    
    def test_pattern_and_unpack(self, test_name: str, result: Any, expected_pattern: ReturnPattern,
                               expected_entity_count: int, additional_checks: Optional[Callable] = None):
        """Test both pattern detection and unpacking for a result."""
        try:
            # Test pattern detection
            analysis = ReturnTypeAnalyzer.analyze_return(result)
            pattern_match = analysis.pattern == expected_pattern
            entity_count_match = analysis.entity_count == expected_entity_count
            
            # Test unpacking
            unpacking_result = EntityUnpacker.unpack_return(result, analysis)
            unpack_entity_count = len(unpacking_result.primary_entities)
            if unpacking_result.container_entity:
                unpack_entity_count += 1
                
            # Basic success criteria
            success = pattern_match and entity_count_match
            
            details = []
            if not pattern_match:
                details.append(f"Pattern mismatch: got {analysis.pattern.value}")
            if not entity_count_match:
                details.append(f"Entity count mismatch: got {analysis.entity_count}")
            
            # Run additional checks if provided
            if additional_checks and success:
                try:
                    additional_checks(analysis, unpacking_result, result)
                    details.append("Additional checks passed")
                except AssertionError as e:
                    success = False
                    details.append(f"Additional check failed: {str(e)}")
                except Exception as e:
                    success = False
                    details.append(f"Additional check error: {str(e)}")
            
            self.log_test(test_name, analysis.pattern, expected_pattern, 
                         analysis.entity_count, success, "; ".join(details))
            
            return analysis, unpacking_result
            
        except Exception as e:
            self.log_test(test_name, None, expected_pattern, 0, False, f"Exception: {str(e)}")
            return None, None


def test_b1_single_entity(tester: PatternTester):
    """Test B1: Single Entity pattern exhaustively."""
    print("\n" + "="*60)
    print("B1: SINGLE ENTITY PATTERN TESTS")
    print("="*60)
    
    entities = tester.entities
    
    # Test 1.1: Basic student entity
    def check_single_student(analysis, unpacking, result):
        assert len(unpacking.primary_entities) == 1
        assert unpacking.primary_entities[0] == result
        assert unpacking.container_entity is None
        assert unpacking.metadata["unpacking_type"] == "single_entity"
    
    tester.test_pattern_and_unpack(
        "B1.1: Basic Student Entity",
        entities['student1'],
        ReturnPattern.SINGLE_ENTITY,
        1,
        check_single_student
    )
    
    # Test 1.2: Different entity type (Course)
    tester.test_pattern_and_unpack(
        "B1.2: Course Entity",
        entities['course1'],
        ReturnPattern.SINGLE_ENTITY,
        1,
        check_single_student
    )
    
    # Test 1.3: Grade entity
    tester.test_pattern_and_unpack(
        "B1.3: Grade Entity",
        entities['grade1'],
        ReturnPattern.SINGLE_ENTITY,
        1,
        check_single_student
    )
    
    # Test 1.4: Assignment entity
    tester.test_pattern_and_unpack(
        "B1.4: Assignment Entity",
        entities['assignment1'],
        ReturnPattern.SINGLE_ENTITY,
        1,
        check_single_student
    )


def test_b2_tuple_entities(tester: PatternTester):
    """Test B2: Tuple of Entities pattern exhaustively."""
    print("\n" + "="*60)
    print("B2: TUPLE OF ENTITIES PATTERN TESTS")
    print("="*60)
    
    entities = tester.entities
    
    # Test 2.1: Two entities tuple
    def check_tuple_two(analysis, unpacking, result):
        assert len(unpacking.primary_entities) == 2
        assert unpacking.container_entity is None
        assert unpacking.metadata["sequence_type"] == "tuple"
        assert unpacking.metadata["length"] == 2
        assert unpacking.primary_entities[0] == result[0]
        assert unpacking.primary_entities[1] == result[1]
    
    tester.test_pattern_and_unpack(
        "B2.1: Tuple of Two Entities (Student, Course)",
        (entities['student1'], entities['course1']),
        ReturnPattern.TUPLE_ENTITIES,
        2,
        check_tuple_two
    )
    
    # Test 2.2: Three entities tuple
    def check_tuple_three(analysis, unpacking, result):
        assert len(unpacking.primary_entities) == 3
        assert unpacking.metadata["length"] == 3
        for i in range(3):
            assert unpacking.primary_entities[i] == result[i]
    
    tester.test_pattern_and_unpack(
        "B2.2: Tuple of Three Entities",
        (entities['student1'], entities['course1'], entities['grade1']),
        ReturnPattern.TUPLE_ENTITIES,
        3,
        check_tuple_three
    )
    
    # Test 2.3: Four entities tuple (mixed types)
    def check_tuple_four(analysis, unpacking, result):
        assert len(unpacking.primary_entities) == 4
        assert unpacking.metadata["length"] == 4
        assert all(isinstance(e, Entity) for e in unpacking.primary_entities)
    
    tester.test_pattern_and_unpack(
        "B2.3: Tuple of Four Mixed Entity Types",
        (entities['student1'], entities['course1'], entities['grade1'], entities['assignment1']),
        ReturnPattern.TUPLE_ENTITIES,
        4,
        check_tuple_four
    )
    
    # Test 2.4: Same entity type tuple
    tester.test_pattern_and_unpack(
        "B2.4: Tuple of Same Entity Type (Two Students)",
        (entities['student1'], entities['student2']),
        ReturnPattern.TUPLE_ENTITIES,
        2,
        check_tuple_two
    )


def test_b3_list_entities(tester: PatternTester):
    """Test B3: List of Entities pattern exhaustively."""
    print("\n" + "="*60)
    print("B3: LIST OF ENTITIES PATTERN TESTS")
    print("="*60)
    
    entities = tester.entities
    
    # Test 3.1: Empty list
    def check_empty_list(analysis, unpacking, result):
        assert len(unpacking.primary_entities) == 0
        assert unpacking.metadata["sequence_type"] == "list"
        assert unpacking.metadata["length"] == 0
    
    tester.test_pattern_and_unpack(
        "B3.1: Empty List",
        [],
        ReturnPattern.NON_ENTITY,  # Empty list is non-entity
        0,
        check_empty_list
    )
    
    # Test 3.2: Single entity list
    def check_single_list(analysis, unpacking, result):
        assert len(unpacking.primary_entities) == 1
        assert unpacking.metadata["sequence_type"] == "list"
        assert unpacking.metadata["length"] == 1
        assert unpacking.primary_entities[0] == result[0]
    
    tester.test_pattern_and_unpack(
        "B3.2: List with Single Entity",
        [entities['student1']],
        ReturnPattern.LIST_ENTITIES,
        1,
        check_single_list
    )
    
    # Test 3.3: Multiple entities list
    def check_multiple_list(analysis, unpacking, result):
        assert len(unpacking.primary_entities) == len(result)
        assert unpacking.metadata["sequence_type"] == "list"
        assert unpacking.metadata["length"] == len(result)
        for i, entity in enumerate(unpacking.primary_entities):
            assert entity == result[i]
    
    tester.test_pattern_and_unpack(
        "B3.3: List of Multiple Students",
        [entities['student1'], entities['student2']],
        ReturnPattern.LIST_ENTITIES,
        2,
        check_multiple_list
    )
    
    # Test 3.4: Mixed entity types list
    tester.test_pattern_and_unpack(
        "B3.4: List of Mixed Entity Types",
        [entities['student1'], entities['course1'], entities['grade1']],
        ReturnPattern.LIST_ENTITIES,
        3,
        check_multiple_list
    )
    
    # Test 3.5: Large list
    large_list = [entities['student1'], entities['student2'], entities['course1'], 
                  entities['course2'], entities['grade1'], entities['grade2']]
    tester.test_pattern_and_unpack(
        "B3.5: Large List (6 entities)",
        large_list,
        ReturnPattern.LIST_ENTITIES,
        6,
        check_multiple_list
    )


def test_b4_dict_entities(tester: PatternTester):
    """Test B4: Dict of Entities pattern exhaustively."""
    print("\n" + "="*60)
    print("B4: DICT OF ENTITIES PATTERN TESTS")
    print("="*60)
    
    entities = tester.entities
    
    # Test 4.1: Empty dict
    def check_empty_dict(analysis, unpacking, result):
        assert len(unpacking.primary_entities) == 0
        assert unpacking.metadata.get("keys", []) == []
    
    tester.test_pattern_and_unpack(
        "B4.1: Empty Dict",
        {},
        ReturnPattern.NON_ENTITY,  # Empty dict is non-entity
        0,
        check_empty_dict
    )
    
    # Test 4.2: Single entity dict
    def check_single_dict(analysis, unpacking, result):
        assert len(unpacking.primary_entities) == 1
        assert unpacking.metadata["unpacking_type"] == "dict"
        keys = list(result.keys())
        assert unpacking.metadata["keys"] == keys
        assert unpacking.primary_entities[0] == list(result.values())[0]
    
    tester.test_pattern_and_unpack(
        "B4.2: Dict with Single Entity",
        {"student": entities['student1']},
        ReturnPattern.DICT_ENTITIES,
        1,
        check_single_dict
    )
    
    # Test 4.3: Multiple entities dict with string keys
    def check_multiple_dict(analysis, unpacking, result):
        assert len(unpacking.primary_entities) == len(result)
        assert unpacking.metadata["unpacking_type"] == "dict"
        keys = list(result.keys())
        values = list(result.values())
        assert unpacking.metadata["keys"] == keys
        for i, entity in enumerate(unpacking.primary_entities):
            assert entity == values[i]
    
    tester.test_pattern_and_unpack(
        "B4.3: Dict with String Keys",
        {
            "alice": entities['student1'],
            "bob": entities['student2'],
            "math": entities['course1']
        },
        ReturnPattern.DICT_ENTITIES,
        3,
        check_multiple_dict
    )
    
    # Test 4.4: Dict with integer keys
    tester.test_pattern_and_unpack(
        "B4.4: Dict with Integer Keys",
        {
            1: entities['student1'],
            2: entities['course1'],
            3: entities['grade1']
        },
        ReturnPattern.DICT_ENTITIES,
        3,
        check_multiple_dict
    )
    
    # Test 4.5: Dict with mixed key types
    tester.test_pattern_and_unpack(
        "B4.5: Dict with Mixed Key Types",
        {
            "student": entities['student1'],
            1: entities['course1'],
            "grade_a": entities['grade1']
        },
        ReturnPattern.DICT_ENTITIES,
        3,
        check_multiple_dict
    )


def test_b5_mixed_container(tester: PatternTester):
    """Test B5: Mixed Container pattern exhaustively."""
    print("\n" + "="*60)
    print("B5: MIXED CONTAINER PATTERN TESTS")
    print("="*60)
    
    entities = tester.entities
    
    # Test 5.1: List with entities and primitives
    def check_mixed_list(analysis, unpacking, result):
        assert analysis.entity_count > 0
        assert len(analysis.non_entity_data) > 0
        assert unpacking.metadata["unpacking_type"] == "mixed"
        assert unpacking.container_entity is not None  # Should have container for non-entity data
    
    tester.test_pattern_and_unpack(
        "B5.1: List with Entities and Primitives",
        [entities['student1'], "metadata", 42, entities['course1'], 3.14],
        ReturnPattern.MIXED_CONTAINER,
        2,  # 2 entities
        check_mixed_list
    )
    
    # Test 5.2: Tuple with entities and primitives
    tester.test_pattern_and_unpack(
        "B5.2: Tuple with Entities and Primitives",
        (entities['student1'], "info", entities['grade1'], True),
        ReturnPattern.MIXED_CONTAINER,
        2,  # 2 entities
        check_mixed_list
    )
    
    # Test 5.3: Dict with entity and non-entity values
    def check_mixed_dict(analysis, unpacking, result):
        assert analysis.entity_count > 0
        assert len(analysis.non_entity_data) > 0
        assert unpacking.metadata["unpacking_type"] == "mixed"
    
    tester.test_pattern_and_unpack(
        "B5.3: Dict with Mixed Values",
        {
            "student": entities['student1'],
            "count": 42,
            "course": entities['course1'],
            "active": True,
            "score": 3.8
        },
        ReturnPattern.MIXED_CONTAINER,
        2,  # 2 entities
        check_mixed_dict
    )
    
    # Test 5.4: Mostly primitives with one entity
    tester.test_pattern_and_unpack(
        "B5.4: Mostly Primitives with One Entity",
        [1, 2, 3, entities['student1'], "text", False],
        ReturnPattern.MIXED_CONTAINER,
        1,  # 1 entity
        check_mixed_list
    )
    
    # Test 5.5: Mostly entities with one primitive
    tester.test_pattern_and_unpack(
        "B5.5: Mostly Entities with One Primitive",
        [entities['student1'], entities['course1'], entities['grade1'], "metadata"],
        ReturnPattern.MIXED_CONTAINER,
        3,  # 3 entities
        check_mixed_list
    )


def test_b6_nested_structure(tester: PatternTester):
    """Test B6: Nested Structure pattern exhaustively."""
    print("\n" + "="*60)
    print("B6: NESTED STRUCTURE PATTERN TESTS")
    print("="*60)
    
    entities = tester.entities
    
    # Test 6.1: Nested lists with entities
    def check_nested(analysis, unpacking, result):
        assert analysis.entity_count > 0
        assert unpacking.metadata["unpacking_type"] == "nested"
        assert unpacking.container_entity is not None
    
    tester.test_pattern_and_unpack(
        "B6.1: Nested Lists with Entities",
        [[entities['student1'], entities['student2']], [entities['course1']]],
        ReturnPattern.NESTED_STRUCTURE,
        3,  # Total entities found
        check_nested
    )
    
    # Test 6.2: Dict with nested entity lists
    tester.test_pattern_and_unpack(
        "B6.2: Dict with Nested Entity Lists",
        {
            "students": [entities['student1'], entities['student2']],
            "courses": [entities['course1'], entities['course2']],
            "metadata": {"count": 4}
        },
        ReturnPattern.NESTED_STRUCTURE,
        4,  # 4 entities total
        check_nested
    )
    
    # Test 6.3: Complex nested structure
    complex_structure = {
        "data": {
            "students": [entities['student1']],
            "courses": {
                "math": entities['course1'],
                "physics": entities['course2']
            }
        },
        "grades": [entities['grade1'], entities['grade2']],
        "count": 5
    }
    tester.test_pattern_and_unpack(
        "B6.3: Complex Nested Structure",
        complex_structure,
        ReturnPattern.NESTED_STRUCTURE,
        5,  # 5 entities total
        check_nested
    )
    
    # Test 6.4: Deeply nested structure
    deep_structure = [
        {
            "level1": [
                {"level2": [entities['student1']]},
                {"level2": entities['course1']}
            ]
        },
        entities['grade1']
    ]
    tester.test_pattern_and_unpack(
        "B6.4: Deeply Nested Structure",
        deep_structure,
        ReturnPattern.NESTED_STRUCTURE,
        3,  # 3 entities total
        check_nested
    )


def test_b7_non_entity(tester: PatternTester):
    """Test B7: Non-entity pattern exhaustively."""
    print("\n" + "="*60)
    print("B7: NON-ENTITY PATTERN TESTS")
    print("="*60)
    
    # Test 7.1: String primitive
    def check_wrapped_primitive(analysis, unpacking, result):
        assert analysis.entity_count == 0
        assert unpacking.metadata["unpacking_type"] == "wrapped_non_entity"
        assert len(unpacking.primary_entities) == 1
        wrapped_entity = unpacking.primary_entities[0]
        assert hasattr(wrapped_entity, 'wrapped_value')
        assert getattr(wrapped_entity, 'wrapped_value') == result
    
    tester.test_pattern_and_unpack(
        "B7.1: String Primitive",
        "Hello World",
        ReturnPattern.NON_ENTITY,
        0,
        check_wrapped_primitive
    )
    
    # Test 7.2: Integer primitive
    tester.test_pattern_and_unpack(
        "B7.2: Integer Primitive",
        42,
        ReturnPattern.NON_ENTITY,
        0,
        check_wrapped_primitive
    )
    
    # Test 7.3: Float primitive
    tester.test_pattern_and_unpack(
        "B7.3: Float Primitive",
        3.14159,
        ReturnPattern.NON_ENTITY,
        0,
        check_wrapped_primitive
    )
    
    # Test 7.4: Boolean primitive
    tester.test_pattern_and_unpack(
        "B7.4: Boolean Primitive",
        True,
        ReturnPattern.NON_ENTITY,
        0,
        check_wrapped_primitive
    )
    
    # Test 7.5: None value
    tester.test_pattern_and_unpack(
        "B7.5: None Value",
        None,
        ReturnPattern.NON_ENTITY,
        0,
        check_wrapped_primitive
    )
    
    # Test 7.6: List of primitives
    def check_wrapped_container(analysis, unpacking, result):
        assert analysis.entity_count == 0
        assert unpacking.metadata["unpacking_type"] == "wrapped_non_entity"
        assert len(unpacking.primary_entities) == 1
    
    tester.test_pattern_and_unpack(
        "B7.6: List of Primitives",
        [1, 2, 3, "text", True],
        ReturnPattern.NON_ENTITY,
        0,
        check_wrapped_container
    )
    
    # Test 7.7: Dict of primitives
    tester.test_pattern_and_unpack(
        "B7.7: Dict of Primitives",
        {"count": 42, "name": "test", "active": False},
        ReturnPattern.NON_ENTITY,
        0,
        check_wrapped_container
    )
    
    # Test 7.8: Complex object (datetime)
    tester.test_pattern_and_unpack(
        "B7.8: Complex Object (datetime)",
        datetime.now(),
        ReturnPattern.NON_ENTITY,
        0,
        check_wrapped_primitive
    )


def test_quick_pattern_detector(tester: PatternTester):
    """Test the QuickPatternDetector for performance optimization."""
    print("\n" + "="*60)
    print("QUICK PATTERN DETECTOR TESTS")
    print("="*60)
    
    entities = tester.entities
    
    # Quick detection tests
    quick_tests = [
        ("Single Entity", entities['student1'], ReturnPattern.SINGLE_ENTITY),
        ("Tuple Entities", (entities['student1'], entities['course1']), ReturnPattern.TUPLE_ENTITIES),
        ("List Entities", [entities['student1'], entities['course1']], ReturnPattern.LIST_ENTITIES),
        ("Dict Entities", {"s": entities['student1'], "c": entities['course1']}, ReturnPattern.DICT_ENTITIES),
        ("String Primitive", "test", ReturnPattern.NON_ENTITY),
        ("Integer Primitive", 42, ReturnPattern.NON_ENTITY),
        ("Mixed Container", [entities['student1'], "text"], None),  # Should require full analysis
    ]
    
    for test_name, test_value, expected_quick in quick_tests:
        try:
            quick_result = QuickPatternDetector.quick_classify(test_value)
            full_result = ReturnTypeAnalyzer.analyze_return(test_value).pattern
            
            if expected_quick is None:
                # Should require full analysis
                success = quick_result is None
                details = "Correctly identified as needing full analysis"
            else:
                # Should be quickly detected
                success = quick_result == expected_quick == full_result
                details = f"Quick: {quick_result.value if quick_result else 'None'}, Full: {full_result.value}"
            
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} Quick Detect {test_name}: {details}")
            
            if not success:
                tester.error_count += 1
                
        except Exception as e:
            print(f"❌ FAIL Quick Detect {test_name}: Exception: {str(e)}")
            tester.error_count += 1


def test_container_reconstruction(tester: PatternTester):
    """Test container reconstruction from unpacked entities."""
    print("\n" + "="*60)
    print("CONTAINER RECONSTRUCTION TESTS")
    print("="*60)
    
    entities = tester.entities
    
    # Test reconstruction of different container types
    test_cases = [
        ("Single Entity", entities['student1']),
        ("Tuple", (entities['student1'], entities['course1'])),
        ("List", [entities['student1'], entities['course1'], entities['grade1']]),
        ("Dict", {"student": entities['student1'], "course": entities['course1']}),
    ]
    
    for test_name, original in test_cases:
        try:
            # Analyze and unpack
            analysis = ReturnTypeAnalyzer.analyze_return(original)
            unpacking_result = EntityUnpacker.unpack_return(original, analysis)
            
            # Reconstruct
            reconstructed = ContainerReconstructor.reconstruct_from_metadata(
                unpacking_result.primary_entities,
                unpacking_result.metadata
            )
            
            # Check reconstruction
            if isinstance(original, tuple):
                success = isinstance(reconstructed, tuple) and len(reconstructed) == len(original)
                success = success and all(r == o for r, o in zip(reconstructed, original))
            elif isinstance(original, list):
                success = isinstance(reconstructed, list) and len(reconstructed) == len(original)
                success = success and all(r == o for r, o in zip(reconstructed, original))
            elif isinstance(original, dict):
                success = isinstance(reconstructed, dict) and len(reconstructed) == len(original)
                success = success and all(reconstructed.get(k) == v for k, v in original.items())
            else:
                success = reconstructed == original
            
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} Reconstruct {test_name}: {'Success' if success else 'Failed'}")
            
            if not success:
                tester.error_count += 1
                
        except Exception as e:
            print(f"❌ FAIL Reconstruct {test_name}: Exception: {str(e)}")
            tester.error_count += 1


def print_summary(tester: PatternTester):
    """Print comprehensive test summary."""
    print("\n" + "="*80)
    print("COMPREHENSIVE TEST SUMMARY")
    print("="*80)
    
    total_tests = len(tester.test_results)
    passed_tests = total_tests - tester.error_count
    
    print(f"Total Tests Run: {total_tests}")
    print(f"Tests Passed: {passed_tests}")
    print(f"Tests Failed: {tester.error_count}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "No tests run")
    
    if tester.error_count > 0:
        print(f"\n❌ FAILED TESTS ({tester.error_count}):")
        for result in tester.test_results:
            if "FAIL" in result['status']:
                print(f"  - {result['test']}: {result['details']}")
    else:
        print(f"\n🎉 ALL TESTS PASSED! 🎉")
    
    # Pattern coverage summary
    patterns_tested = set(result['expected'] for result in tester.test_results)
    print(f"\nPattern Coverage: {len(patterns_tested)}/7 patterns tested")
    for pattern in ReturnPattern:
        tested = pattern.value in patterns_tested
        status = "✅" if tested else "❌"
        print(f"  {status} {pattern.value}")
    
    print("\n" + "="*80)


def main():
    """Run all exhaustive pattern tests."""
    print("🚀 Starting Exhaustive Pattern Testing for Phase 2")
    print("Testing Return Type Analysis and Entity Unpacking")
    
    # Clear registry
    EntityRegistry.tree_registry.clear()
    EntityRegistry.lineage_registry.clear()
    EntityRegistry.live_id_registry.clear()
    EntityRegistry.ecs_id_to_root_id.clear()
    EntityRegistry.type_registry.clear()
    
    # Create tester
    tester = PatternTester()
    
    # Run all pattern tests
    test_b1_single_entity(tester)
    test_b2_tuple_entities(tester)
    test_b3_list_entities(tester)
    test_b4_dict_entities(tester)
    test_b5_mixed_container(tester)
    test_b6_nested_structure(tester)
    test_b7_non_entity(tester)
    
    # Run additional tests
    test_quick_pattern_detector(tester)
    test_container_reconstruction(tester)
    
    # Print comprehensive summary
    print_summary(tester)


if __name__ == "__main__":
    main()