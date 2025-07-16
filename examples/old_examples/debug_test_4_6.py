#!/usr/bin/env python3
"""
Debug script for Tests 4 and 6 execution paths.
Located in examples/ with proper import pattern.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from abstractions.ecs.entity import Entity
from abstractions.ecs.callable_registry import CallableRegistry
from pydantic import Field
from typing import List
import traceback

# Define entities like in the test file
class Student(Entity):
    name: str
    gpa: float

class Assessment(Entity):
    student_id: str
    performance_level: str
    score: float

class Recommendation(Entity):
    student_id: str
    action: str
    reasoning: str

# Register the functions (copying from test file)
@CallableRegistry.register("batch_analyze_students")
def batch_analyze_students(students: List[Student]) -> List[tuple[Assessment, Recommendation]]:
    """Test 4 function - should wrap in container but fails."""
    results = []
    for student in students:
        assessment = Assessment(
            student_id=str(student.ecs_id),
            performance_level="high" if student.gpa > 3.5 else "standard",
            score=student.gpa
        )
        recommendation = Recommendation(
            student_id=str(student.ecs_id),
            action="advanced_placement" if student.gpa > 3.5 else "standard_track",
            reasoning=f"Batch analysis: GPA {student.gpa}"
        )
        results.append((assessment, recommendation))
    return results

@CallableRegistry.register("calculate_average_gpa")
def calculate_average_gpa(students: List[Student]) -> float:
    """Test 6 function - should wrap but fails."""
    return sum(s.gpa for s in students) / len(students) if students else 0.0

def main():
    print("=== Debug Tests 4 & 6 ===")
    
    # Create test data
    students = [
        Student(name='Alice', gpa=3.8), 
        Student(name='Bob', gpa=3.2)
    ]
    
    print('\n🔍 Test 4 Debug (batch_analyze_students):')
    try:
        result4 = CallableRegistry.execute('batch_analyze_students', students=students)
        print(f'✅ Test 4 SUCCESS: {type(result4).__name__}')
        print(f'   Result type: {type(result4)}')
        if hasattr(result4, '__dict__'):
            print(f'   Result attrs: {list(result4.__dict__.keys())}')
    except Exception as e:
        print(f'❌ Test 4 ERROR: {e}')
        traceback.print_exc()

    print('\n🔍 Test 6 Debug (calculate_average_gpa):')
    try:
        result6 = CallableRegistry.execute('calculate_average_gpa', students=students)
        print(f'✅ Test 6 SUCCESS: {type(result6).__name__}')
        print(f'   Result type: {type(result6)}')
        if hasattr(result6, '__dict__'):
            print(f'   Result attrs: {list(result6.__dict__.keys())}')
    except Exception as e:
        print(f'❌ Test 6 ERROR: {e}')
        traceback.print_exc()

if __name__ == '__main__':
    main()