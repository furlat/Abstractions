"""
Example 1: Basic Entity Transformation

This example demonstrates core entity operations from the README:
- Define data as entities (Section 1: lines 19-60)
- Entity-native computation model (Section 2: lines 78-96)
- Functional transformation registry (Section 3: lines 104-119)
- Automatic provenance and lineage tracking (Section 5: lines 157-177)

All code blocks from these README sections are implemented exactly as documented.
"""

from typing import Union, List, Tuple
from abstractions.ecs.entity import Entity
from abstractions.ecs.callable_registry import CallableRegistry

# =============================================================================
# Section 1: First Steps (README lines 19-60)
# =============================================================================

# 1. Define your data as entities - the native unit of computation
class Student(Entity):
    name: str = ""
    gpa: float = 0.0

# 2. Register pure functions that transform entities  
@CallableRegistry.register("update_gpa")
def update_gpa(student: Student, new_gpa: float) -> Student:
    student.gpa = new_gpa
    return student

# =============================================================================
# Section 2: Entity-native Computation Model (README lines 78-96)
# =============================================================================

@CallableRegistry.register("apply_bonus")
def apply_bonus(student: Student, bonus: float) -> Student:
    student.gpa = min(4.0, student.gpa + bonus)
    return student

# =============================================================================
# Section 3: Functional Transformation Registry (README lines 104-119)
# =============================================================================

class DeanListResult(Entity):
    student_id: str = ""
    qualified: bool = False
    margin: float = 0.0

# Functions declare their data dependencies via type hints
@CallableRegistry.register("calculate_dean_list")
def calculate_dean_list(student: Student, threshold: float = 3.7) -> DeanListResult:
    return DeanListResult(
        student_id=str(student.ecs_id),
        qualified=student.gpa >= threshold,
        margin=student.gpa - threshold
    )

# =============================================================================
# Section 5: Automatic Provenance and Lineage (README lines 157-177)
# =============================================================================

# Create a complex transformation pipeline
@CallableRegistry.register("normalize_grades")
def normalize_grades(cohort: List[Student]) -> List[Student]:
    avg_gpa = sum(s.gpa for s in cohort) / len(cohort)
    return [
        Student(name=s.name, gpa=s.gpa / avg_gpa * 3.0)
        for s in cohort
    ]

def run_tests() -> Tuple[int, int, List[str], List[str]]:
    """Run tests and validate README claims."""
    
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
    
    print("=== Testing Basic Entity Transformation ===\n")
    
    # 3. Execute functional transformations
    student = Student(name="Alice", gpa=3.5)
    student.promote_to_root()  # Enter the distributed entity space
    
    print(f"Original student: {student.name} has GPA {student.gpa}")
    print(f"Student ECS ID: {student.ecs_id}")
    print(f"Student lineage ID: {student.lineage_id}")
    
    # Execute the function and get the result
    result = CallableRegistry.execute("update_gpa", student=student, new_gpa=3.8)
    
    # Handle the fact that execute can return Union[Entity, List[Entity]]
    if isinstance(result, list):
        # If it's a list, take the first element
        updated = result[0] if result else None
        if updated is None:
            print("❌ No result returned from execute")
            return tests_passed, tests_total, validated_features, failed_features
    else:
        # If it's a single entity
        updated = result
    
    # Type guard to ensure we have a Student
    if not isinstance(updated, Student):
        print(f"❌ Expected Student, got {type(updated)}")
        return tests_passed, tests_total, validated_features, failed_features
    
    print(f"\nAfter update: {updated.name} now has GPA {updated.gpa}")
    print(f"Updated ECS ID: {updated.ecs_id}")
    print(f"Updated lineage ID: {updated.lineage_id}")
    
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
    
    # Test 3: Function registration and execution
    def test_execution():
        assert updated is not None
        assert updated.name == "Alice"
        assert updated.gpa == 3.8
    
    test_feature("Function registration and execution", test_execution)
    
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
    
    # Test 7: Function registry metadata
    def test_metadata():
        assert "update_gpa" in CallableRegistry.list_functions()
        assert CallableRegistry.get_metadata("update_gpa") is not None
    
    test_feature("Function registry metadata", test_metadata)
    
    # Test 8: Entity type preservation
    def test_types():
        assert isinstance(student, Student)
        assert isinstance(updated, Student)
        assert type(student) == type(updated)
    
    test_feature("Entity type preservation", test_types)
    
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

if __name__ == "__main__":
    tests_passed, tests_total, validated_features, failed_features = run_tests()
    
    if tests_passed == tests_total:
        print(f"\n🎉 All tests passed! Basic entity transformation works as documented.")
    else:
        print(f"\n⚠️  {tests_total - tests_passed} tests failed. README may need updates.")
    
    print(f"\n✅ Basic entity transformation example completed!")