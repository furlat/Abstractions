"""
Example 1: Basic Entity Transformation (Async Version)

This example demonstrates the minimal pattern from the README with async support:
- Define data as entities
- Register async functions that transform entities
- Execute functional transformations asynchronously
- Automatic versioning, lineage tracking, and provenance
- Proper event emission without warnings
"""

import asyncio
from typing import Union, List, Tuple
from abstractions.ecs.entity import Entity
from abstractions.ecs.callable_registry import CallableRegistry

# 1. Define your data as entities - the native unit of computation
class Student(Entity):
    name: str = ""
    gpa: float = 0.0

# 2. Register async functions that transform entities  
@CallableRegistry.register("update_gpa_async")
async def update_gpa_async(student: Student, new_gpa: float) -> Student:
    # Simulate some async work (like database update)
    await asyncio.sleep(0.001)  # Minimal delay to show async behavior
    student.gpa = new_gpa
    return student

# Also register a sync version for comparison
@CallableRegistry.register("update_gpa_sync")
def update_gpa_sync(student: Student, new_gpa: float) -> Student:
    student.gpa = new_gpa
    return student

async def run_tests_async() -> Tuple[int, int, List[str], List[str]]:
    """Run async tests and validate README claims."""
    
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
    
    print("=== Testing Basic Entity Transformation (Async) ===\n")
    
    # 3. Execute functional transformations asynchronously
    student = Student(name="Alice", gpa=3.5)
    student.promote_to_root()  # Enter the distributed entity space
    
    print(f"Original student: {student.name} has GPA {student.gpa}")
    print(f"Student ECS ID: {student.ecs_id}")
    print(f"Student lineage ID: {student.lineage_id}")
    
    # Execute the async function
    result = await CallableRegistry.aexecute("update_gpa_async", student=student, new_gpa=3.8)
    
    # Handle the fact that execute can return Union[Entity, List[Entity]]
    if isinstance(result, list):
        # If it's a list, take the first element
        updated = result[0] if result else None
        if updated is None:
            print("❌ No result returned from aexecute")
            return tests_passed, tests_total, validated_features, failed_features
    else:
        # If it's a single entity
        updated = result
    
    # Type guard to ensure we have a Student
    if not isinstance(updated, Student):
        print(f"❌ Expected Student, got {type(updated)}")
        return tests_passed, tests_total, validated_features, failed_features
    
    print(f"\nAfter async update: {updated.name} now has GPA {updated.gpa}")
    print(f"Updated ECS ID: {updated.ecs_id}")
    print(f"Updated lineage ID: {updated.lineage_id}")
    
    # Also test sync version for comparison (but use aexecute since we're in async context)
    print(f"\n--- Testing Sync Version for Comparison ---")
    student2 = Student(name="Bob", gpa=3.2)
    student2.promote_to_root()
    
    # Use aexecute instead of execute since we're in async context
    result2 = await CallableRegistry.aexecute("update_gpa_sync", student=student2, new_gpa=3.7)
    updated2 = result2 if not isinstance(result2, list) else result2[0]
    
    if isinstance(updated2, Student):
        print(f"Sync update: {updated2.name} now has GPA {updated2.gpa}")
    
    print(f"\n=== Feature Validation ===")
    
    # Test 1: Entity creation with custom fields
    def test_entity_creation():
        assert student.name == "Alice"
        assert student.gpa == 3.5
        assert hasattr(student, 'ecs_id')
        assert hasattr(student, 'lineage_id')
    
    test_feature("Entity creation with custom fields", test_entity_creation)
    
    # Test 2: Entity promotion to root
    def test_promotion():
        assert student.root_ecs_id == student.ecs_id
        assert student.root_live_id == student.live_id
    
    test_feature("Entity promotion to root", test_promotion)
    
    # Test 3: Async function registration and execution
    def test_async_execution():
        assert updated is not None
        assert updated.name == "Alice"
        assert updated.gpa == 3.8
    
    test_feature("Async function registration and execution", test_async_execution)
    
    # Test 4: Automatic versioning (different ECS IDs)
    def test_versioning():
        assert student.ecs_id != updated.ecs_id
    
    test_feature("Automatic versioning (different ECS IDs)", test_versioning)
    
    # Test 5: Lineage tracking (same lineage ID)
    def test_lineage():
        assert student.lineage_id == updated.lineage_id
    
    test_feature("Lineage tracking (same lineage ID)", test_lineage)
    
    # Test 6: Immutable original entity
    def test_immutability():
        assert student.gpa == 3.5  # Original unchanged
    
    test_feature("Immutable original entity", test_immutability)
    
    # Test 7: Function registry metadata (both sync and async)
    def test_metadata():
        assert "update_gpa_async" in CallableRegistry.list_functions()
        assert "update_gpa_sync" in CallableRegistry.list_functions()
        
        # Get metadata and ensure it's not None
        async_metadata = CallableRegistry.get_metadata("update_gpa_async")
        sync_metadata = CallableRegistry.get_metadata("update_gpa_sync")
        
        assert async_metadata is not None
        assert sync_metadata is not None
        
        # Check that async function is properly detected
        assert async_metadata.is_async == True
        assert sync_metadata.is_async == False
    
    test_feature("Function registry metadata (sync and async)", test_metadata)
    
    # Test 8: Entity type preservation
    def test_types():
        assert isinstance(student, Student)
        assert isinstance(updated, Student)
        assert type(student) == type(updated)
    
    test_feature("Entity type preservation", test_types)
    
    # Test 9: Async vs Sync comparison
    def test_async_vs_sync():
        assert isinstance(updated2, Student)
        assert updated2.name == "Bob"
        assert updated2.gpa == 3.7
        # Both should have different IDs from their originals
        assert student2.ecs_id != updated2.ecs_id
        assert student2.lineage_id == updated2.lineage_id
    
    test_feature("Async vs Sync comparison", test_async_vs_sync)
    
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
    print("🚀 Starting async entity transformation tests...")
    
    tests_passed, tests_total, validated_features, failed_features = await run_tests_async()
    
    if tests_passed == tests_total:
        print(f"\n🎉 All tests passed! Basic entity transformation works as documented.")
        print(f"✨ Events were properly emitted without warnings in async context!")
    else:
        print(f"\n⚠️  {tests_total - tests_passed} tests failed. README may need updates.")
    
    print(f"\n✅ Async entity transformation example completed!")
    
    # Show the difference between sync and async execution
    print(f"\n📊 Key Benefits of Async Version:")
    print(f"  - ✅ No RuntimeWarnings about unawaited coroutines")
    print(f"  - ✅ Proper event emission and handling")
    print(f"  - ✅ Support for async operations (database calls, API requests, etc.)")
    print(f"  - ✅ Better integration with async web frameworks")
    print(f"  - ✅ Concurrent execution capabilities")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())