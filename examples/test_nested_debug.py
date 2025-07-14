#!/usr/bin/env python3
"""
Debug nested structure detection
"""

import sys
sys.path.append('.')

from abstractions.ecs.entity import Entity
from abstractions.ecs.return_type_analyzer import ReturnTypeAnalyzer, ReturnPattern

# Test entities
class Student(Entity):
    name: str = ""
    age: int = 0

class Course(Entity):
    title: str = ""
    credits: int = 0

def test_nested_cases():
    print("=== Debugging Nested Structure Cases ===")
    
    # Create real entities
    student1 = Student(name="Alice", age=20)
    student2 = Student(name="Bob", age=21) 
    course1 = Course(title="Math 101", credits=3)
    
    print(f"Student1 type: {type(student1)} - isinstance Entity: {isinstance(student1, Entity)}")
    print(f"Course1 type: {type(course1)} - isinstance Entity: {isinstance(course1, Entity)}")
    
    # Test case B6.1: Nested Lists with Entities
    print("\n--- B6.1: Nested Lists with Entities ---")
    nested_result = [[student1, student2], [course1]]
    print(f"Test data: {nested_result}")
    print(f"Is nested_result[0][0] an Entity? {isinstance(nested_result[0][0], Entity)}")
    
    analysis = ReturnTypeAnalyzer.analyze_return(nested_result)
    print(f"Pattern: {analysis.pattern}")
    print(f"Entity count: {analysis.entity_count}")
    print(f"Entities found: {[str(e.ecs_id)[-8:] for e in analysis.entities]}")
    
    # Test manual nested detection
    has_nested = ReturnTypeAnalyzer._has_nested_entities(nested_result)
    print(f"Manual nested detection: {has_nested}")
    
    # Test case B6.2: Dict with nested entity lists
    print("\n--- B6.2: Dict with Nested Entity Lists ---")
    dict_result = {
        "students": [student1, student2],
        "courses": [course1],
        "metadata": {"count": 3}
    }
    print(f"Test data keys: {list(dict_result.keys())}")
    print(f"students value: {dict_result['students']}")
    print(f"Is dict_result['students'][0] an Entity? {isinstance(dict_result['students'][0], Entity)}")
    
    analysis = ReturnTypeAnalyzer.analyze_return(dict_result)
    print(f"Pattern: {analysis.pattern}")
    print(f"Entity count: {analysis.entity_count}")
    print(f"Entities found: {[str(e.ecs_id)[-8:] for e in analysis.entities]}")
    
    has_nested = ReturnTypeAnalyzer._has_nested_entities(dict_result)
    print(f"Manual nested detection: {has_nested}")

if __name__ == "__main__":
    test_nested_cases()