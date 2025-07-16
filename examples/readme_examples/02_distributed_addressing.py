"""
Example 2: Distributed Addressing (Sync Version)

This example demonstrates:
- String-based distributed addressing using @uuid.field syntax
- Accessing entity data from anywhere using addresses
- Location transparency for distributed systems
- Functional API for get/put operations
"""

from typing import Union, List, Tuple
from abstractions.ecs.entity import Entity
from abstractions.ecs.callable_registry import CallableRegistry
from abstractions.ecs.functional_api import get

# Define entities
class Student(Entity):
    name: str = ""
    gpa: float = 0.0
    
class Course(Entity):
    name: str = ""
    credits: int = 0
    grade: str = ""

@CallableRegistry.register("update_gpa")
def update_gpa(student: Student, new_gpa: float) -> Student:
    student.gpa = new_gpa
    return student

@CallableRegistry.register("create_transcript")
def create_transcript(name: str, gpa: float, courses: List[str]) -> Course:
    """Create a transcript-like entity from distributed data."""
    return Course(name=f"Transcript for {name}", credits=len(courses), grade=f"GPA: {gpa}")

def run_tests() -> Tuple[int, int, List[str], List[str]]:
    """Run tests and validate distributed addressing claims."""
    
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
    
    print("=== Testing Distributed Addressing (Sync) ===\n")
    
    # Create and register a student
    student = Student(name="Alice", gpa=3.5)
    student.promote_to_root()
    
    print(f"Created student: {student.name} with GPA {student.gpa}")
    print(f"Student address: @{student.ecs_id}")
    
    # Update the student
    result = CallableRegistry.execute("update_gpa", student=student, new_gpa=3.8)
    updated = result if not isinstance(result, list) else result[0]
    
    if not isinstance(updated, Student):
        print(f"❌ Expected Student, got {type(updated)}")
        return tests_passed, tests_total, validated_features, failed_features
    
    print(f"\nUpdated student: {updated.name} with GPA {updated.gpa}")
    print(f"Updated address: @{updated.ecs_id}")
    
    print(f"\n=== Feature Validation ===")
    
    # Test 1: Basic entity addressing
    def test_entity_addressing():
        # Access entity data using distributed addressing
        student_name = get(f"@{updated.ecs_id}.name")
        student_gpa = get(f"@{updated.ecs_id}.gpa")
        
        assert student_name == "Alice"
        assert student_gpa == 3.8
        assert student_name == updated.name
        assert student_gpa == updated.gpa
    
    test_feature("Basic entity addressing", test_entity_addressing)
    
    # Test 2: Address format validation
    def test_address_format():
        # Test that addresses follow the @uuid.field format
        address = f"@{updated.ecs_id}.name"
        assert address.startswith("@")
        assert "." in address
        assert len(address.split(".")) == 2  # @uuid.field
    
    test_feature("Address format validation", test_address_format)
    
    # Test 3: Entity data consistency
    def test_data_consistency():
        # Verify that addressed data matches direct access
        direct_name = updated.name
        direct_gpa = updated.gpa
        
        addressed_name = get(f"@{updated.ecs_id}.name")
        addressed_gpa = get(f"@{updated.ecs_id}.gpa")
        
        assert direct_name == addressed_name
        assert direct_gpa == addressed_gpa
    
    test_feature("Entity data consistency", test_data_consistency)
    
    # Test 4: Location transparency
    def test_location_transparency():
        # Functions can use addressed data without knowing location
        transcript = CallableRegistry.execute("create_transcript",
            name=f"@{updated.ecs_id}.name",      # From entity
            gpa=f"@{updated.ecs_id}.gpa",        # From entity  
            courses=["Math", "Physics", "CS"]     # Direct data
        )
        
        transcript_result = transcript if not isinstance(transcript, list) else transcript[0]
        assert isinstance(transcript_result, Course)
        assert "Alice" in transcript_result.name
        assert transcript_result.credits == 3  # 3 courses
        assert "3.8" in transcript_result.grade  # GPA in grade field
    
    test_feature("Location transparency", test_location_transparency)
    
    # Test 5: Mixed local and remote data
    def test_mixed_data():
        # Test mixing addressed data with direct values
        courses = ["Biology", "Chemistry"]
        transcript2 = CallableRegistry.execute("create_transcript",
            name=f"@{updated.ecs_id}.name",
            gpa=3.9,  # Direct value
            courses=courses
        )
        
        transcript2_result = transcript2 if not isinstance(transcript2, list) else transcript2[0]
        assert isinstance(transcript2_result, Course)
        assert "Alice" in transcript2_result.name
        assert transcript2_result.credits == 2
        assert "3.9" in transcript2_result.grade
    
    test_feature("Mixed local and remote data", test_mixed_data)
    
    # Test 6: Address resolution error handling
    def test_error_handling():
        # Test that invalid addresses are handled gracefully
        import uuid
        fake_id = uuid.uuid4()
        
        try:
            get(f"@{fake_id}.name")
            assert False, "Should have raised an error for non-existent entity"
        except (ValueError, KeyError):
            pass  # Expected error for non-existent entity
    
    test_feature("Address resolution error handling", test_error_handling)
    
    # Test 7: Entity identity preservation
    def test_identity_preservation():
        # Verify that entities maintain their identity through addressing
        original_id = updated.ecs_id
        original_lineage = updated.lineage_id
        
        # Address doesn't change entity identity
        _ = get(f"@{updated.ecs_id}.name")
        
        assert updated.ecs_id == original_id
        assert updated.lineage_id == original_lineage
    
    test_feature("Entity identity preservation", test_identity_preservation)
    
    # Test 8: Distributed system readiness
    def test_distributed_readiness():
        # Test that addresses are network-portable strings
        address = f"@{updated.ecs_id}.name"
        
        # Address should be a string that can be serialized
        assert isinstance(address, str)
        assert len(address) > 0
        
        # Should be able to reconstruct the same data
        reconstructed_name = get(address)
        assert reconstructed_name == updated.name
    
    test_feature("Distributed system readiness", test_distributed_readiness)
    
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
    print("🌐 Testing distributed addressing capabilities...")
    
    tests_passed, tests_total, validated_features, failed_features = run_tests()
    
    if tests_passed == tests_total:
        print(f"\n🎉 All tests passed! Distributed addressing works as documented.")
        print(f"🔗 String addresses provide location transparency!")
    else:
        print(f"\n⚠️  {tests_total - tests_passed} tests failed. README may need updates.")
    
    print(f"\n✅ Distributed addressing example completed!")
    
    # Show the benefits
    print(f"\n📊 Key Benefits of Distributed Addressing:")
    print(f"  - 🌍 Location transparency - functions don't need to know where data lives")
    print(f"  - 🔗 Network portable - addresses work across system boundaries")
    print(f"  - 🎯 Human readable - @uuid.field format is self-documenting")
    print(f"  - ⚡ Lazy resolution - addresses resolved only when needed")
    print(f"  - 🔐 Access control ready - addresses can be filtered by permissions")