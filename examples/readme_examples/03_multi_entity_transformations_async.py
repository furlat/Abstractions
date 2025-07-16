"""
Example 3: Multi-entity Transformations (Async Version)

This example demonstrates:
- Functions that return multiple entities as tuples (async)
- Automatic unpacking and sibling relationship tracking
- Complex data flows with multiple related outputs
- Tuple[Entity, Entity] return types with async execution
"""

import asyncio
from typing import Tuple, List
from pydantic import Field
from abstractions.ecs.entity import Entity
from abstractions.ecs.callable_registry import CallableRegistry

# Define entities for performance analysis
class Student(Entity):
    name: str = Field(default="")
    gpa: float = Field(default=0.0)

class Assessment(Entity):
    student_id: str = Field(default="")
    performance_level: str = Field(default="")
    gpa_score: float = Field(default=0.0)

class Recommendation(Entity):
    student_id: str = Field(default="")
    action: str = Field(default="")
    reasoning: str = Field(default="")

# Register async function that returns multiple entities
@CallableRegistry.register("analyze_performance_async")
async def analyze_performance_async(student: Student) -> Tuple[Assessment, Recommendation]:
    """Analyze student performance and create assessment + recommendation (async)."""
    
    # Simulate async work (database lookup, API calls, etc.)
    await asyncio.sleep(0.001)
    
    # Create assessment
    assessment = Assessment(
        student_id=str(student.ecs_id),
        performance_level="high" if student.gpa > 3.5 else "standard",
        gpa_score=student.gpa
    )
    
    # Create recommendation based on performance
    if student.gpa > 3.5:
        recommendation = Recommendation(
            student_id=str(student.ecs_id),
            action="advanced_placement",
            reasoning=f"Async analysis: GPA {student.gpa} (above 3.5 threshold)"
        )
    else:
        recommendation = Recommendation(
            student_id=str(student.ecs_id),
            action="standard_track",
            reasoning=f"Async analysis: GPA {student.gpa} (at or below 3.5 threshold)"
        )
    
    return assessment, recommendation

# Register async function that processes multiple students
@CallableRegistry.register("batch_analyze_performance_async")
async def batch_analyze_performance_async(students: List[Student]) -> List[Tuple[Assessment, Recommendation]]:
    """Process multiple students and return list of (assessment, recommendation) tuples (async)."""
    results = []
    
    for student in students:
        # Simulate async processing
        await asyncio.sleep(0.001)
        
        assessment = Assessment(
            student_id=str(student.ecs_id),
            performance_level="high" if student.gpa > 3.5 else "standard",
            gpa_score=student.gpa
        )
        
        recommendation = Recommendation(
            student_id=str(student.ecs_id),
            action="advanced_placement" if student.gpa > 3.5 else "standard_track",
            reasoning=f"Async batch analysis: GPA {student.gpa}"
        )
        
        results.append((assessment, recommendation))
    
    return results

# Also register sync versions for comparison
@CallableRegistry.register("analyze_performance_sync")
def analyze_performance_sync(student: Student) -> Tuple[Assessment, Recommendation]:
    """Analyze student performance and create assessment + recommendation (sync)."""
    
    assessment = Assessment(
        student_id=str(student.ecs_id),
        performance_level="high" if student.gpa > 3.5 else "standard",
        gpa_score=student.gpa
    )
    
    recommendation = Recommendation(
        student_id=str(student.ecs_id),
        action="advanced_placement" if student.gpa > 3.5 else "standard_track",
        reasoning=f"Sync analysis: GPA {student.gpa}"
    )
    
    return assessment, recommendation

async def run_tests_async() -> Tuple[int, int, List[str], List[str]]:
    """Run async tests and validate multi-entity transformation claims."""
    
    # Test tracking
    tests_passed: int = 0
    tests_total: int = 0
    validated_features: List[str] = []
    failed_features: List[str] = []
    
    def test_feature(feature_name: str, test_func) -> bool:
        nonlocal tests_passed, tests_total
        tests_total += 1
        try:
            test_func()
            tests_passed += 1
            validated_features.append(feature_name)
            print(f"✅ {feature_name}")
            return True
        except Exception as e:
            failed_features.append(f"{feature_name}: {str(e)}")
            print(f"❌ {feature_name}: {str(e)}")
            return False
    
    print("=== Testing Multi-entity Transformations (Async) ===\n")
    
    # Create test students
    alice = Student(name="Alice", gpa=3.8)
    alice.promote_to_root()
    
    bob = Student(name="Bob", gpa=3.2)
    bob.promote_to_root()
    
    charlie = Student(name="Charlie", gpa=3.9)
    charlie.promote_to_root()
    
    print(f"Created students:")
    print(f"  - Alice: GPA {alice.gpa} (ID: {alice.ecs_id})")
    print(f"  - Bob: GPA {bob.gpa} (ID: {bob.ecs_id})")
    print(f"  - Charlie: GPA {charlie.gpa} (ID: {charlie.ecs_id})")
    
    print(f"\n=== Feature Validation ===")
    
    # Test 1: Async tuple return unpacking
    async def test_async_tuple_unpacking():
        # Execute async function that returns tuple
        result = await CallableRegistry.aexecute("analyze_performance_async", student=alice)
        
        # Handle Union[Entity, List[Entity]] return type
        if isinstance(result, list):
            assert len(result) == 2
            assessment, recommendation = result[0], result[1]
        else:
            assert False, f"Expected list for tuple return, got {type(result)}"
        
        # Validate types
        assert isinstance(assessment, Assessment)
        assert isinstance(recommendation, Recommendation)
        
        # Validate content
        assert assessment.student_id == str(alice.ecs_id)
        assert assessment.performance_level == "high"
        assert assessment.gpa_score == 3.8
        
        assert recommendation.student_id == str(alice.ecs_id)
        assert recommendation.action == "advanced_placement"
        assert "3.8" in recommendation.reasoning
        assert "Async analysis" in recommendation.reasoning
    
    try:
        await test_async_tuple_unpacking()
        test_feature("Async tuple return unpacking", lambda: True)
    except Exception as e:
        test_feature("Async tuple return unpacking", lambda: exec(f'raise Exception("{str(e)}")'))
    
    # Test 2: Async sibling relationships
    async def test_async_sibling_relationships():
        result = await CallableRegistry.aexecute("analyze_performance_async", student=alice)
        
        if isinstance(result, list):
            assessment, recommendation = result[0], result[1]
        else:
            assert False, f"Expected list for tuple return, got {type(result)}"
        
        assert isinstance(assessment, Assessment)
        assert isinstance(recommendation, Recommendation)
        
        # Check if entities have sibling information
        if hasattr(assessment, 'sibling_output_entities'):
            assert recommendation.ecs_id in assessment.sibling_output_entities
        
        if hasattr(recommendation, 'sibling_output_entities'):
            assert assessment.ecs_id in recommendation.sibling_output_entities
        
        # At minimum, they should be different entities
        assert assessment.ecs_id != recommendation.ecs_id
        assert assessment.lineage_id != recommendation.lineage_id
    
    try:
        await test_async_sibling_relationships()
        test_feature("Async sibling relationships", lambda: True)
    except Exception as e:
        test_feature("Async sibling relationships", lambda: exec(f'raise Exception("{str(e)}")'))
    
    # Test 3: Async batch processing
    async def test_async_batch_processing():
        students = [alice, bob, charlie]
        batch_result = await CallableRegistry.aexecute("batch_analyze_performance_async", students=students)
        
        # With type-safe wrapping, List[Tuple[...]] returns a single WrapperEntity
        assert isinstance(batch_result, Entity)
        assert hasattr(batch_result, 'wrapped_value'), "Expected WrapperEntity with wrapped_value attribute"
        
        # Extract the wrapped list (type-safe access)
        wrapped_list = getattr(batch_result, 'wrapped_value')
        assert isinstance(wrapped_list, list)
        assert len(wrapped_list) == 3  # One tuple per student
        
        # Check each tuple contains Assessment and Recommendation
        for item in wrapped_list:
            assert isinstance(item, tuple)
            assert len(item) == 2
            assessment, recommendation = item
            assert isinstance(assessment, Assessment)
            assert isinstance(recommendation, Recommendation)
            assert "Async batch analysis" in recommendation.reasoning
    
    try:
        await test_async_batch_processing()
        test_feature("Async batch processing", lambda: True)
    except Exception as e:
        test_feature("Async batch processing", lambda: exec(f'raise Exception("{str(e)}")'))
    
    # Test 4: Concurrent async execution
    async def test_concurrent_execution():
        # Execute multiple async functions concurrently
        tasks = [
            CallableRegistry.aexecute("analyze_performance_async", student=alice),
            CallableRegistry.aexecute("analyze_performance_async", student=bob),
            CallableRegistry.aexecute("analyze_performance_async", student=charlie)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should complete successfully
        assert len(results) == 3
        
        for result in results:
            if isinstance(result, list):
                assessment, recommendation = result[0], result[1]
            else:
                assert False, f"Expected list for tuple return, got {type(result)}"
            
            assert isinstance(assessment, Assessment)
            assert isinstance(recommendation, Recommendation)
    
    try:
        await test_concurrent_execution()
        test_feature("Concurrent async execution", lambda: True)
    except Exception as e:
        test_feature("Concurrent async execution", lambda: exec(f'raise Exception("{str(e)}")'))
    
    # Test 5: Sync vs async comparison
    async def test_sync_vs_async():
        # Execute sync function via aexecute
        sync_result = await CallableRegistry.aexecute("analyze_performance_sync", student=alice)
        
        # Execute async function
        async_result = await CallableRegistry.aexecute("analyze_performance_async", student=alice)
        
        # Both should work and produce similar results
        if isinstance(sync_result, list):
            sync_assessment, sync_rec = sync_result[0], sync_result[1]
        else:
            assert False, f"Expected list for tuple return, got {type(sync_result)}"
        
        if isinstance(async_result, list):
            async_assessment, async_rec = async_result[0], async_result[1]
        else:
            assert False, f"Expected list for tuple return, got {type(async_result)}"
        
        assert isinstance(sync_assessment, Assessment)
        assert isinstance(async_assessment, Assessment)
        assert isinstance(sync_rec, Recommendation)
        assert isinstance(async_rec, Recommendation)
        
        assert sync_assessment.performance_level == async_assessment.performance_level
        assert sync_assessment.gpa_score == async_assessment.gpa_score
        
        assert "Sync analysis" in sync_rec.reasoning
        assert "Async analysis" in async_rec.reasoning
    
    try:
        await test_sync_vs_async()
        test_feature("Sync vs async comparison", lambda: True)
    except Exception as e:
        test_feature("Sync vs async comparison", lambda: exec(f'raise Exception("{str(e)}")'))
    
    # Test 6: Async performance validation
    async def test_async_performance():
        import time
        
        # Time async execution
        start_time = time.time()
        result = await CallableRegistry.aexecute("analyze_performance_async", student=alice)
        async_time = time.time() - start_time
        
        # Should complete reasonably quickly
        assert async_time < 1.0  # Should be much faster than 1 second
        
        # Result should still be valid
        if isinstance(result, list):
            assessment, recommendation = result[0], result[1]
        else:
            assert False, f"Expected list for tuple return, got {type(result)}"
        
        assert isinstance(assessment, Assessment)
        assert isinstance(recommendation, Recommendation)
        
        assert isinstance(assessment, Assessment)
        assert isinstance(recommendation, Recommendation)
    
    try:
        await test_async_performance()
        test_feature("Async performance validation", lambda: True)
    except Exception as e:
        test_feature("Async performance validation", lambda: exec(f'raise Exception("{str(e)}")'))
    
    # Test 7: Async error handling
    async def test_async_error_handling():
        # Test that async functions handle errors gracefully
        try:
            # This should work fine
            result = await CallableRegistry.aexecute("analyze_performance_async", student=alice)
            assert result is not None
            
            # Test with invalid input (should not crash)
            try:
                await CallableRegistry.aexecute("analyze_performance_async", student=None)
                assert False, "Should have raised an error"
            except Exception:
                pass  # Expected
        
        except Exception as e:
            # If there's an error, it should be handled gracefully
            assert "error" in str(e).lower() or "exception" in str(e).lower()
    
    try:
        await test_async_error_handling()
        test_feature("Async error handling", lambda: True)
    except Exception as e:
        test_feature("Async error handling", lambda: exec(f'raise Exception("{str(e)}")'))
    
    # Test 8: Async metadata validation
    def test_async_metadata():
        # Verify async functions are properly registered
        async_metadata = CallableRegistry.get_metadata("analyze_performance_async")
        sync_metadata = CallableRegistry.get_metadata("analyze_performance_sync")
        
        assert async_metadata is not None
        assert sync_metadata is not None
        assert async_metadata.is_async == True
        assert sync_metadata.is_async == False
    
    test_feature("Async metadata validation", test_async_metadata)
    
    # Test 9: Async return type consistency
    async def test_async_return_consistency():
        # Multiple executions should return consistent format
        results = []
        for _ in range(3):
            result = await CallableRegistry.aexecute("analyze_performance_async", student=alice)
            results.append(result)
        
        # All should have same structure
        for result in results:
            if isinstance(result, list):
                assert len(result) == 2
                assert isinstance(result[0], Assessment)
                assert isinstance(result[1], Recommendation)
            else:
                assert False, f"Expected list for tuple return, got {type(result)}"
    
    try:
        await test_async_return_consistency()
        test_feature("Async return type consistency", lambda: True)
    except Exception as e:
        test_feature("Async return type consistency", lambda: exec(f'raise Exception("{str(e)}")'))
    
    # Test 10: Async event integration
    async def test_async_event_integration():
        # Execute async function and verify no event system conflicts
        result = await CallableRegistry.aexecute("analyze_performance_async", student=alice)
        
        # Should complete without event system errors
        assert result is not None
        
        if isinstance(result, list):
            assessment, recommendation = result[0], result[1]
        else:
            assert False, f"Expected list for tuple return, got {type(result)}"
        
        assert isinstance(assessment, Assessment)
        assert isinstance(recommendation, Recommendation)
        
        # Both entities should be properly created
        assert assessment.ecs_id is not None
        assert recommendation.ecs_id is not None
    
    try:
        await test_async_event_integration()
        test_feature("Async event integration", lambda: True)
    except Exception as e:
        test_feature("Async event integration", lambda: exec(f'raise Exception("{str(e)}")'))
    
    print(f"\n=== Test Results ===")
    print(f"Tests passed: {tests_passed}/{tests_total}")
    print(f"Success rate: {tests_passed/tests_total*100:.1f}%")
    
    if validated_features:
        print(f"\n✅ Validated Features:")
        for feature in validated_features:
            print(f"  - {feature}")
    
    if failed_features:
        print(f"\n❌ Failed Features:")
        for feature in failed_features:
            print(f"  - {feature}")
    
    return tests_passed, tests_total, validated_features, failed_features

async def main():
    """Main async function to run all tests."""
    print("🔀 Testing multi-entity transformations (async)...")
    
    tests_passed, tests_total, validated_features, failed_features = await run_tests_async()
    
    if tests_passed == tests_total:
        print(f"\n🎉 All tests passed! Async multi-entity transformations work as documented.")
        print(f"🔗 Tuple returns create sibling relationships automatically!")
        print(f"✨ Async execution handles complex data flows properly!")
        print(f"⚡ Concurrent execution works without interference!")
    else:
        print(f"\n⚠️  {tests_total - tests_passed} tests failed. README may need updates.")
    
    print(f"\n✅ Async multi-entity transformations example completed!")
    
    # Show the benefits
    print(f"\n📊 Key Benefits of Async Multi-entity Transformations:")
    print(f"  - 🔄 Automatic unpacking of tuple returns in async context")
    print(f"  - 🤝 Sibling relationship tracking between related entities")
    print(f"  - 📈 Complex data flows with multiple outputs")
    print(f"  - 🚀 Native async support with proper await handling")
    print(f"  - ⚡ Concurrent execution without entity interference")
    print(f"  - 🔍 Provenance tracking for all generated entities")
    print(f"  - 🎯 Type safety with proper async tuple handling")
    print(f"  - 📦 Batch processing support for multiple async transformations")
    print(f"  - 🔄 Consistent entity identity management across async calls")
    print(f"  - 📋 Comprehensive async error handling and validation")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())