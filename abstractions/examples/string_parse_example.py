#!/usr/bin/env python3
"""
String Parsing Example: @uuid.field Syntax and Entity Creation

This example demonstrates the newly implemented ECS address parser and 
functional API for creating entities from string-based entity references.

Features demonstrated:
- Parsing @uuid.field syntax
- Creating entities from address dictionaries
- Functional get/put API operations
- Batch resolution and validation
- Integration with borrowing and provenance tracking
"""

from typing import List, Optional, Dict, Any
from pydantic import Field

# Import the entity system and new modules
from abstractions.ecs.entity import Entity, EntityRegistry, build_entity_tree
from abstractions.ecs.ecs_address_parser import ECSAddressParser, EntityReferenceResolver, get, is_address, parse
from abstractions.ecs.functional_api import (
    create_entity_from_mapping, batch_get, resolve_data_with_tracking,
    create_composite_entity, get_entity_dependencies, validate_addresses,
    create_entity_from_address_dict
)

def log_section(title: str):
    """Clean section logging to avoid overwhelming output."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def log_entity_summary(entity: Entity, show_attributes: bool = False):
    """Log entity summary with shortened UUIDs."""
    print(f"  {entity.__class__.__name__}:")
    print(f"    ecs_id: ...{str(entity.ecs_id)[-8:]}")
    
    if show_attributes:
        entity_data = entity.model_dump()
        excluded_fields = {'ecs_id', 'live_id', 'created_at', 'forked_at', 
                          'previous_ecs_id', 'lineage_id', 'old_ids', 
                          'root_ecs_id', 'root_live_id', 'from_storage', 'attribute_source'}
        for field_name, field_value in entity_data.items():
            if field_name not in excluded_fields:
                if isinstance(field_value, list) and len(field_value) > 2:
                    print(f"    {field_name}: [list with {len(field_value)} items]")
                elif isinstance(field_value, str) and len(field_value) > 40:
                    print(f"    {field_name}: {field_value[:37]}...")
                else:
                    print(f"    {field_name}: {field_value}")

# Reuse Academic System Entities
class Student(Entity):
    """A student entity with basic information."""
    name: str
    age: int
    email: str
    student_id: str

class Course(Entity):
    """A course entity with academic details."""
    title: str
    code: str
    credits: int
    description: str = ""

class Grade(Entity):
    """A grade with course info and score."""
    course_code: str
    course_title: str
    score: float
    semester: str
    letter_grade: str = ""

class AcademicRecord(Entity):
    """Academic record containing a student's grades."""
    student: Student
    grades: List[Grade] = Field(default_factory=list)
    gpa: float = 0.0
    total_credits: int = 0

# New entities for string parsing demonstration
class StudentAnalysisInput(Entity):
    """Input entity for student analysis functions."""
    student_name: str = ""
    student_age: int = 0
    student_email: str = ""
    current_gpa: float = 0.0
    grade_scores: List[float] = Field(default_factory=list)
    analysis_threshold: float = 3.5
    analysis_date: str = ""

class PerformanceReport(Entity):
    """Output entity for performance analysis."""
    student_info: Dict[str, Any] = Field(default_factory=dict)
    performance_metrics: Dict[str, float] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)
    report_id: str = ""

def main():
    """Main demonstration of string parsing and entity creation functionality."""
    
    log_section("Phase 1: Setting Up Source Entities for Address References")
    
    # Create and register source entities
    print("Creating source entities...")
    
    alice = Student(
        name="Alice Johnson",
        age=20,
        email="alice.johnson@university.edu",
        student_id="STU001"
    )
    
    math_grade = Grade(
        course_code="MATH101",
        course_title="Calculus I",
        score=92.5,
        semester="Fall 2023",
        letter_grade="A"
    )
    
    cs_grade = Grade(
        course_code="CS200",
        course_title="Data Structures",
        score=95.0,
        semester="Spring 2024",
        letter_grade="A"
    )
    
    alice_record = AcademicRecord(
        student=alice,
        grades=[math_grade, cs_grade],
        gpa=3.90,
        total_credits=7
    )
    
    # Register entities so they can be addressed by @uuid.field
    print("Registering entities for addressing...")
    alice.promote_to_root()
    math_grade.promote_to_root()
    cs_grade.promote_to_root()
    alice_record.promote_to_root()
    
    print("Registered entities with addresses:")
    print(f"  Alice: @{alice.ecs_id}")
    print(f"  Math Grade: @{math_grade.ecs_id}")
    print(f"  CS Grade: @{cs_grade.ecs_id}")
    print(f"  Alice Record: @{alice_record.ecs_id}")
    
    log_section("Phase 2: Basic Address Parsing and Validation")
    
    # Test address parsing
    test_addresses = [
        f"@{alice.ecs_id}.name",
        f"@{alice.ecs_id}.age",
        f"@{alice_record.ecs_id}.gpa",
        f"@{math_grade.ecs_id}.score",
        "@invalid-uuid.field",
        "not_an_address"
    ]
    
    print("Testing address validation:")
    for address in test_addresses:
        is_valid = ECSAddressParser.validate_address_format(address)
        is_addr = is_address(address)
        print(f"  {address[:50]:<50} Valid: {is_valid}, Is Address: {is_addr}")
    
    print("\nTesting address parsing:")
    valid_addresses = [addr for addr in test_addresses if ECSAddressParser.validate_address_format(addr)]
    for address in valid_addresses:
        try:
            entity_id, field_path = parse(address)
            print(f"  {address} -> Entity: ...{str(entity_id)[-8:]}, Fields: {field_path}")
        except Exception as e:
            print(f"  {address} -> Error: {e}")
    
    log_section("Phase 3: Functional get() API")
    
    print("Testing functional get() operations:")
    
    # Test direct field access
    alice_name = get(f"@{alice.ecs_id}.name")
    alice_age = get(f"@{alice.ecs_id}.age")
    alice_gpa = get(f"@{alice_record.ecs_id}.gpa")
    math_score = get(f"@{math_grade.ecs_id}.score")
    
    print(f"  Alice name: {alice_name}")
    print(f"  Alice age: {alice_age}")
    print(f"  Alice GPA: {alice_gpa}")
    print(f"  Math score: {math_score}")
    
    # Test batch get operations
    print("\nTesting batch get operations:")
    batch_addresses = [
        f"@{alice.ecs_id}.name",
        f"@{alice.ecs_id}.age",
        f"@{alice_record.ecs_id}.gpa",
        f"@{math_grade.ecs_id}.score",
        f"@{cs_grade.ecs_id}.score"
    ]
    
    batch_results = batch_get(batch_addresses)
    for address, value in batch_results.items():
        short_addr = f"...{address[-20:]}"
        print(f"  {short_addr:<25} -> {value}")
    
    log_section("Phase 4: Entity Creation from Address Mappings")
    
    print("Creating analysis input entity from address mappings...")
    
    analysis_input = create_entity_from_mapping(StudentAnalysisInput, {
        "student_name": f"@{alice.ecs_id}.name",
        "student_age": f"@{alice.ecs_id}.age", 
        "student_email": f"@{alice.ecs_id}.email",
        "current_gpa": f"@{alice_record.ecs_id}.gpa",
        "analysis_threshold": 3.5,  # Direct value
        "analysis_date": "2024-06-26"  # Direct value
    })
    
    print("Created analysis input entity:")
    log_entity_summary(analysis_input, show_attributes=True)
    
    print("\nProvenance tracking from address mapping:")
    for field_name, source_id in analysis_input.attribute_source.items():
        if source_id:
            print(f"  {field_name}: sourced from ...{str(source_id)[-8:]}")
        else:
            print(f"  {field_name}: direct value (no source)")
    
    log_section("Phase 5: Factory Method Entity Creation")
    
    print("Testing factory method entity creation...")
    
    # Using the create_entity_from_address_dict function
    analysis_input_2 = create_entity_from_address_dict(StudentAnalysisInput, {
        "student_name": f"@{alice.ecs_id}.name",
        "student_age": f"@{alice.ecs_id}.age",
        "current_gpa": f"@{alice_record.ecs_id}.gpa"
    })
    
    print("Created entity using factory method:")
    log_entity_summary(analysis_input_2, show_attributes=True)
    
    log_section("Phase 6: Enhanced Composite Entity Creation")
    
    print("Creating composite entity with registration...")
    
    composite_analysis = create_composite_entity(
        StudentAnalysisInput,
        {
            "student_name": f"@{alice.ecs_id}.name",
            "student_age": f"@{alice.ecs_id}.age",
            "student_email": f"@{alice.ecs_id}.email",
            "current_gpa": f"@{alice_record.ecs_id}.gpa",
            "grade_scores": [92.5, 95.0],  # Direct list value
            "analysis_threshold": 3.8,
            "analysis_date": "2024-06-26"
        },
        register=True  # This will promote to root and register
    )
    
    print("Created and registered composite entity:")
    log_entity_summary(composite_analysis, show_attributes=True)
    print(f"  Registered as root: {composite_analysis.is_root_entity()}")
    print(f"  Root ecs_id: ...{str(composite_analysis.root_ecs_id)[-8:] if composite_analysis.root_ecs_id else 'None'}")
    
    log_section("Phase 7: Dependency Tracking and Analysis")
    
    print("Analyzing entity dependencies...")
    
    # Use EntityReferenceResolver for detailed dependency tracking
    test_data = {
        "student_info": {
            "name": f"@{alice.ecs_id}.name",
            "age": f"@{alice.ecs_id}.age"
        },
        "academic_data": {
            "gpa": f"@{alice_record.ecs_id}.gpa",
            "grades": [
                f"@{math_grade.ecs_id}.score",
                f"@{cs_grade.ecs_id}.score"
            ]
        },
        "direct_values": {
            "threshold": 3.5,
            "date": "2024-06-26"
        }
    }
    
    resolved_data, dependencies = resolve_data_with_tracking(test_data)
    
    print("Dependency tracking results:")
    print(f"  Total entities referenced: {len(dependencies)}")
    print(f"  Referenced entity IDs:")
    for entity_id in dependencies:
        print(f"    ...{str(entity_id)[-8:]}")
    
    print(f"\nResolved data structure:")
    print(f"  student_info: {resolved_data['student_info']}")
    print(f"  academic_data: {resolved_data['academic_data']}")
    print(f"  direct_values: {resolved_data['direct_values']}")
    
    # Get dependencies for the composite entity
    composite_deps = get_entity_dependencies(composite_analysis)
    print(f"\nComposite entity dependencies:")
    print(f"  Total dependencies: {composite_deps['total_dependencies']}")
    print(f"  Direct dependencies: {[str(dep)[-8:] for dep in composite_deps['direct_dependencies']]}")
    
    log_section("Phase 8: Complex Nested Address Resolution")
    
    print("Testing complex nested data with multiple addresses...")
    
    nested_test_data = {
        "analysis_params": {
            "student_data": {
                "basic_info": {
                    "name": f"@{alice.ecs_id}.name",
                    "age": f"@{alice.ecs_id}.age",
                    "email": f"@{alice.ecs_id}.email"
                },
                "academic_performance": {
                    "gpa": f"@{alice_record.ecs_id}.gpa",
                    "total_credits": f"@{alice_record.ecs_id}.total_credits"
                }
            },
            "grade_analysis": [
                {
                    "course": f"@{math_grade.ecs_id}.course_title",
                    "score": f"@{math_grade.ecs_id}.score",
                    "grade": f"@{math_grade.ecs_id}.letter_grade"
                },
                {
                    "course": f"@{cs_grade.ecs_id}.course_title", 
                    "score": f"@{cs_grade.ecs_id}.score",
                    "grade": f"@{cs_grade.ecs_id}.letter_grade"
                }
            ]
        },
        "metadata": {
            "analysis_date": "2024-06-26",
            "threshold": 3.5,
            "analyst": "System"
        }
    }
    
    resolver = EntityReferenceResolver()
    resolved_nested, nested_deps = resolver.resolve_references(nested_test_data)
    
    print("Complex nested resolution results:")
    print(f"  Entities referenced: {len(nested_deps)}")
    
    dependency_summary = resolver.get_dependency_summary()
    print(f"  Resolution summary: {dependency_summary['total_entities_referenced']} entities")
    print(f"  Resolution mappings: {len(dependency_summary['resolution_mapping'])} addresses resolved")
    
    print(f"\nSample resolved nested data:")
    student_basic = resolved_nested['analysis_params']['student_data']['basic_info']
    print(f"  Student basic info: {student_basic}")
    
    grade_analysis = resolved_nested['analysis_params']['grade_analysis'][0]
    print(f"  First grade analysis: {grade_analysis}")
    
    log_section("Phase 9: Error Handling and Edge Cases")
    
    print("Testing error handling...")
    
    # Test invalid addresses
    invalid_addresses = [
        "@nonexistent-uuid.field",
        f"@{alice.ecs_id}.nonexistent_field", 
        "@invalid-format",
        ""
    ]
    
    for address in invalid_addresses:
        try:
            result = get(address)
            print(f"  {address} -> Unexpected success: {result}")
        except Exception as e:
            error_type = type(e).__name__
            print(f"  {address} -> {error_type}: {str(e)[:50]}...")
    
    # Test address validation
    print(f"\nValidation results for problematic addresses:")
    validation_results = validate_addresses(invalid_addresses + [
        f"@{alice.ecs_id}.name",  # Valid
        f"@{alice_record.ecs_id}.gpa"  # Valid
    ])
    
    for address, is_valid in validation_results.items():
        status = " Valid" if is_valid else " Invalid"
        print(f"  {address[:40]:<40} {status}")
    
    log_section("Summary: String Parsing and Entity Creation Complete")
    
    print(" ECS Address Parser Implementation")
    print("  - @uuid.field syntax parsing and validation")
    print("  - Functional get() API for value resolution")
    print("  - Batch operations for efficient multi-resolution")
    print("  - Comprehensive error handling and validation")
    
    print("\n Entity Creation from Addresses")
    print("  - create_entity_from_mapping() for mixed value/address mappings")
    print("  - create_entity_from_address_dict() factory function")
    print("  - create_composite_entity() with registration options")
    print("  - Complete provenance tracking through attribute_source")
    
    print("\n Dependency Tracking and Analysis")
    print("  - EntityReferenceResolver for complex nested resolution")
    print("  - get_entity_dependencies() for dependency analysis")
    print("  - Automatic tracking of all referenced entities")
    print("  - Resolution statistics and mapping information")
    
    print("\n Integration with Borrowing System")
    print("  - borrow_from_address() method integration")
    print("  - Automatic attribute_source tracking")
    print("  - Seamless integration with entity versioning")
    print("  - Foundation for callable registry input composition")
    
    print(f"\n Foundation for Callable Registry")
    print(f"  - Complete @uuid.field syntax support")
    print(f"  - Function input composition from entity references")
    print(f"  - Automatic dependency discovery and tracking")
    print(f"  - Ready for function execution with entity boundaries")
    
    print(f"\nNext steps: Integrate with callable registry for complete")
    print(f"entity-based function execution with string-based addressing.")

if __name__ == "__main__":
    main()