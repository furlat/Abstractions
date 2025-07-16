#!/usr/bin/env python3
"""
Debug script to check why Phase 4 multi-entity unpacking isn't working
"""

import sys
sys.path.append('.')

from abstractions.ecs.callable_registry import CallableRegistry
from abstractions.ecs.entity import Entity
from typing import List, Tuple

# Test entities
class Course(Entity):
    course_id: str = ''
    title: str = ''
    credits: int = 3

class AnalysisReport(Entity):
    student_name: str = ''
    
class Recommendation(Entity):
    action: str = ''

def create_course_sequence(base_title: str, count: int) -> List[Course]:
    """Function that should return List[Course] and trigger unpacking."""
    return [Course(title=f'{base_title} {i}') for i in range(count)]

def analyze_comprehensive(grades: List[Entity]) -> Tuple[AnalysisReport, List[Recommendation]]:
    """Function with mixed tuple - should NOT unpack (creates unified entity)."""
    return AnalysisReport(student_name="Test"), [Recommendation(action="test")]

def analyze_pure_entities(student_name: str) -> Tuple[AnalysisReport, Recommendation]:
    """Function with pure entity tuple - should unpack to multiple entities."""
    return AnalysisReport(student_name=student_name), Recommendation(action="pure")

print("=== Debugging Phase 4 Metadata ===")

# Register functions and check metadata
CallableRegistry.register('test_list')(create_course_sequence)
CallableRegistry.register('test_tuple_mixed')(analyze_comprehensive)
CallableRegistry.register('test_tuple_pure')(analyze_pure_entities)

for name in ['test_list', 'test_tuple_mixed', 'test_tuple_pure']:
    print(f"\n--- Function: {name} ---")
    info = CallableRegistry.get_function_info(name)
    if info:
        print(f'  supports_unpacking: {info.get("supports_unpacking", "N/A")}')
        print(f'  expected_output_count: {info.get("expected_output_count", "N/A")}')
        print(f'  return_analysis: {info.get("return_analysis", {})}')
        print(f'  output_pattern: {info.get("output_pattern", "N/A")}')
        
        # Check the metadata object directly
        metadata = CallableRegistry._functions.get(name)
        if metadata:
            print(f'  metadata.supports_unpacking: {metadata.supports_unpacking}')
            print(f'  metadata.expected_output_count: {metadata.expected_output_count}')
            print(f'  metadata.return_analysis: {metadata.return_analysis}')
            
print("\n=== Testing Actual Execution ===")

# Test execution to see what happens
result1 = CallableRegistry.execute('test_list', base_title="Math", count=2)
print(f"\ntest_list result type: {type(result1)}")
print(f"test_list result: {result1}")
if isinstance(result1, list):
    print(f"  List length: {len(result1)}")
else:
    print(f"  Single entity ID: {result1.ecs_id}")

result2 = CallableRegistry.execute('test_tuple_mixed', grades=[])
print(f"\ntest_tuple_mixed result type: {type(result2)}")
print(f"test_tuple_mixed should be single entity (no unpacking): {not isinstance(result2, list)}")

result3 = CallableRegistry.execute('test_tuple_pure', student_name="Alice")
print(f"\ntest_tuple_pure result type: {type(result3)}")
print(f"test_tuple_pure should be list (unpacking): {isinstance(result3, list)}")
if isinstance(result3, list):
    print(f"  List length: {len(result3)}")