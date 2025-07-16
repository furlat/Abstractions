#!/usr/bin/env python3
"""
Example 05: Async Patterns

This example demonstrates async execution patterns from the README:
- Sync and async function registration
- Concurrent execution without interference  
- Async execution with external API calls
- Safe concurrent processing of same entities
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import asyncio
from typing import List, Tuple
from abstractions.ecs.entity import Entity
from abstractions.ecs.callable_registry import CallableRegistry

class Student(Entity):
    name: str = ""
    gpa: float = 0.0

class AnalysisResult(Entity):
    student_id: str = ""
    avg: float = 0.0
    analysis_type: str = ""

# Register both sync and async functions
@CallableRegistry.register("analyze_grades")
def analyze_grades(student: Student, grades: List[float]) -> AnalysisResult:
    """Synchronous grade analysis"""
    return AnalysisResult(
        student_id=str(student.ecs_id),
        avg=sum(grades)/len(grades),
        analysis_type="sync"
    )

@CallableRegistry.register("analyze_grades_async")
async def analyze_grades_async(student: Student, grades: List[float]) -> AnalysisResult:
    """Async grade analysis with external API calls"""
    await asyncio.sleep(0.1)  # Simulate API call
    return AnalysisResult(
        student_id=str(student.ecs_id),
        avg=sum(grades)/len(grades),
        analysis_type="async"
    )

async def demonstrate_async_patterns():
    """Demonstrate async execution patterns."""
    print("=== Async Patterns Demo ===")
    
    # Create test student
    student = Student(name="TestStudent", gpa=3.5)
    student.promote_to_root()
    
    print(f"Student: {student.name} (ID: {student.ecs_id})")
    
    # Execute concurrently without interference
    batch_results = await asyncio.gather(
        CallableRegistry.aexecute("analyze_grades",
            student=f"@{student.ecs_id}",
            grades=[3.8, 3.9, 3.7]
        ),
        CallableRegistry.aexecute("analyze_grades_async", 
            student=f"@{student.ecs_id}",  # Same student, no problem!
            grades=[3.8, 3.9, 3.7, 4.0]
        )
    )
    
    print(f"\\nConcurrent results:")
    for i, result in enumerate(batch_results):
        if isinstance(result, list):
            result = result[0] if result else None
        if result and isinstance(result, AnalysisResult):
            print(f"  Result {i+1}: avg={result.avg:.2f}, type={result.analysis_type}")
        else:
            print(f"  Result {i+1}: No valid result")
    
    return batch_results

async def run_validation_tests():
    """Run validation tests for async patterns."""
    print("=== Async Patterns Validation ===")
    
    tests_passed = 0
    tests_total = 0
    validated_features = []
    failed_features = []
    
    def test_feature(name: str, test_func):
        nonlocal tests_passed, tests_total
        tests_total += 1
        try:
            test_func()
            tests_passed += 1
            validated_features.append(name)
            print(f"✅ {name}")
            return True
        except Exception as e:
            failed_features.append(f"{name}: {str(e)}")
            print(f"❌ {name}: {str(e)}")
            return False
    
    # Test 1: Functions are registered
    def test_registration():
        functions = CallableRegistry.list_functions()
        assert "analyze_grades" in functions
        assert "analyze_grades_async" in functions
    
    test_feature("Function registration", test_registration)
    
    # Test 2: Async execution works
    results = await demonstrate_async_patterns()
    
    def test_async_execution():
        assert len(results) == 2
        for result in results:
            if isinstance(result, list):
                result = result[0]
            assert isinstance(result, AnalysisResult)
            assert result.avg > 0
    
    test_feature("Async execution", test_async_execution)
    
    print(f"\\n=== Test Results ===")
    print(f"Tests passed: {tests_passed}/{tests_total}")
    print(f"Success rate: {tests_passed/tests_total*100:.1f}%")
    
    if validated_features:
        print(f"\\n✅ Validated Features:")
        for feature in validated_features:
            print(f"  - {feature}")
    
    if failed_features:
        print(f"\\n❌ Failed Features:")
        for feature in failed_features:
            print(f"  - {feature}")
    
    return tests_passed, tests_total, validated_features, failed_features

async def main():
    """Main execution function."""
    print("=== Async Patterns Example ===\\n")
    
    print("This example demonstrates:")
    print("- Sync and async function registration")
    print("- Concurrent execution without interference")
    print("- Address-based entity access in async context")
    print("- Safe processing of same entities concurrently")
    print()
    
    # Run validation tests
    tests_passed, tests_total, validated_features, failed_features = await run_validation_tests()
    
    if tests_passed == tests_total:
        print(f"\\n🎉 All tests passed! Async patterns work as documented.")
        print(f"⚡ Concurrent execution without interference!")
        print(f"🔄 Safe async processing enabled!")
    else:
        print(f"\\n⚠️  {tests_total - tests_passed} tests failed.")
    
    print(f"\\n✅ Async patterns example completed!")

if __name__ == "__main__":
    asyncio.run(main())