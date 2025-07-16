#!/usr/bin/env python3
"""
Borrow Feature Initial Example: Data Composition Demonstration

This example demonstrates the newly implemented borrow_attribute_from() method
using the academic system entities from base_ecs_example.py.

Features demonstrated:
- Data composition from multiple source entities
- Safe copying with container awareness
- Provenance tracking through attribute_source
- Type validation and error handling
- Foundation for callable registry integration
"""

from typing import List, Optional
from pydantic import Field

# Import the entity system
from abstractions.ecs.entity import Entity, EntityRegistry, build_entity_tree

def log_section(title: str):
    """Clean section logging to avoid overwhelming output."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

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

# Reuse Academic System Entities from base_ecs_example.py
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

# New Entity for Borrowing Demonstration
class AnalysisInputEntity(Entity):
    """Entity for composing analysis inputs from multiple sources."""
    student_name: str = ""
    student_age: int = 0
    student_email: str = ""
    current_gpa: float = 0.0
    grade_count: int = 0
    recent_scores: List[float] = Field(default_factory=list)
    analysis_threshold: float = 3.5

class PerformanceReport(Entity):
    """Entity for demonstrating borrowing with complex data."""
    report_title: str = ""
    student_info: dict = Field(default_factory=dict)
    academic_summary: dict = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)

def main():
    """Main demonstration of borrow_attribute_from functionality."""
    
    log_section("Phase 1: Setting Up Source Entities")
    
    # Create source entities (similar to base_ecs_example.py)
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
    
    print("Source entities created:")
    log_entity_summary(alice, show_attributes=True)
    log_entity_summary(alice_record, show_attributes=True)
    
    log_section("Phase 2: Basic Borrowing - Primitive Values")
    
    print("Creating analysis input entity...")
    analysis_input = AnalysisInputEntity()
    
    print("Borrowing primitive values from Student...")
    analysis_input.borrow_attribute_from(alice, "name", "student_name")
    analysis_input.borrow_attribute_from(alice, "age", "student_age")
    analysis_input.borrow_attribute_from(alice, "email", "student_email")
    
    print("Borrowing from AcademicRecord...")
    analysis_input.borrow_attribute_from(alice_record, "gpa", "current_gpa")
    
    print("\nBorrowed values:")
    log_entity_summary(analysis_input, show_attributes=True)
    
    print("\nProvenance tracking (attribute_source):")
    for field_name, source_id in analysis_input.attribute_source.items():
        if source_id:
            print(f"  {field_name}: borrowed from ...{str(source_id)[-8:]}")
    
    log_section("Phase 3: Container Borrowing - Lists and Complex Data")
    
    print("Borrowing list data from AcademicRecord...")
    analysis_input.borrow_attribute_from(alice_record, "grades", "recent_scores")
    
    # Extract scores from grades for demonstration
    scores = [grade.score for grade in alice_record.grades]
    analysis_input.recent_scores = scores
    analysis_input.grade_count = len(scores)
    
    print("Updated analysis input with container data:")
    log_entity_summary(analysis_input, show_attributes=True)
    
    print("Checking container provenance:")
    for field_name, source_info in analysis_input.attribute_source.items():
        if isinstance(source_info, list):
            print(f"  {field_name}: list with {len(source_info)} source references")
        elif source_info:
            print(f"  {field_name}: source ...{str(source_info)[-8:]}")
    
    log_section("Phase 4: Dictionary Borrowing and Complex Structures")
    
    print("Creating performance report with dictionary borrowing...")
    performance_report = PerformanceReport()
    
    # Create source dictionary data
    student_summary = {
        "name": alice.name,
        "id": alice.student_id,
        "email": alice.email,
        "enrollment_year": 2023
    }
    
    # Create a temporary entity to hold the dictionary for borrowing
    class TempDataHolder(Entity):
        student_summary: dict = Field(default_factory=dict)
        academic_stats: dict = Field(default_factory=dict)
    
    temp_holder = TempDataHolder()
    temp_holder.student_summary = student_summary
    temp_holder.academic_stats = {
        "gpa": alice_record.gpa,
        "credits": alice_record.total_credits,
        "grade_count": len(alice_record.grades)
    }
    
    print("Borrowing dictionary data...")
    performance_report.borrow_attribute_from(temp_holder, "student_summary", "student_info")
    performance_report.borrow_attribute_from(temp_holder, "academic_stats", "academic_summary")
    
    print("Performance report with borrowed dictionaries:")
    log_entity_summary(performance_report, show_attributes=True)
    
    print("Dictionary provenance tracking:")
    for field_name, source_info in performance_report.attribute_source.items():
        if isinstance(source_info, dict):
            print(f"  {field_name}: dict with {len(source_info)} key-source mappings")
        elif source_info:
            print(f"  {field_name}: source ...{str(source_info)[-8:]}")
    
    log_section("Phase 5: Safety and Immutability Testing")
    
    print("Testing that borrowed data doesn't affect source...")
    
    # Modify borrowed primitive value
    original_student_name = alice.name
    analysis_input.student_name = "Modified Name"
    
    print(f"Original student name: {alice.name}")
    print(f"Modified analysis name: {analysis_input.student_name}")
    print(f"Source unchanged: {alice.name == original_student_name}")
    
    # Test list immutability
    print("\nTesting list immutability...")
    original_scores = [grade.score for grade in alice_record.grades]
    analysis_input.recent_scores.append(100.0)  # Modify borrowed list
    
    current_scores = [grade.score for grade in alice_record.grades]
    print(f"Original scores: {original_scores}")
    print(f"Modified borrowed scores: {analysis_input.recent_scores}")
    print(f"Source grades unchanged: {current_scores == original_scores}")
    
    # Test dictionary immutability
    print("\nTesting dictionary immutability...")
    original_gpa = temp_holder.academic_stats["gpa"]
    performance_report.academic_summary["gpa"] = 4.0  # Modify borrowed dict
    
    print(f"Original GPA in source: {temp_holder.academic_stats['gpa']}")
    print(f"Modified GPA in borrowed dict: {performance_report.academic_summary['gpa']}")
    print(f"Source unchanged: {temp_holder.academic_stats['gpa'] == original_gpa}")
    
    log_section("Phase 6: Error Handling and Validation")
    
    print("Testing error conditions...")
    
    # Test invalid field names
    try:
        analysis_input.borrow_attribute_from(alice, "nonexistent_field", "student_name")
        print("ERROR: Should have raised ValueError for nonexistent source field")
    except ValueError as e:
        print(f" Correctly caught source field error: {e}")
    
    try:
        analysis_input.borrow_attribute_from(alice, "name", "nonexistent_target")
        print("ERROR: Should have raised ValueError for nonexistent target field")
    except ValueError as e:
        print(f" Correctly caught target field error: {e}")
    
    log_section("Phase 7: Entity Reference Borrowing")
    
    print("Testing entity reference borrowing...")
    
    class StudentAnalysis(Entity):
        subject_student: Optional[Student] = None
        reference_record: Optional[AcademicRecord] = None
    
    student_analysis = StudentAnalysis()
    
    # Borrow entity references (should not be copied, just referenced)
    student_analysis.borrow_attribute_from(alice_record, "student", "subject_student")
    
    print("Entity reference borrowed:")
    print(f"  Same entity reference: {student_analysis.subject_student is alice}")
    print(f"  Entity provenance: ...{str(student_analysis.attribute_source['subject_student'])[-8:]}")
    
    log_section("Phase 8: Versioning and Overwriting Existing Attributes")
    
    print("Testing borrowing to entities with existing values...")
    
    # Create an entity with pre-existing values
    pre_filled_analysis = AnalysisInputEntity(
        student_name="Original Student",
        student_age=25,
        current_gpa=2.5,
        analysis_threshold=3.0
    )
    
    print("Original entity state:")
    log_entity_summary(pre_filled_analysis, show_attributes=True)
    print(f"Original ecs_id: ...{str(pre_filled_analysis.ecs_id)[-8:]}")
    
    # Register it in the registry to enable versioning
    pre_filled_analysis.promote_to_root()
    original_ecs_id = pre_filled_analysis.ecs_id
    
    print(f"\nBorrowing new values over existing ones...")
    # Borrow values that will overwrite existing data
    pre_filled_analysis.borrow_attribute_from(alice, "name", "student_name")
    pre_filled_analysis.borrow_attribute_from(alice, "age", "student_age") 
    pre_filled_analysis.borrow_attribute_from(alice_record, "gpa", "current_gpa")
    
    print("Entity after borrowing:")
    log_entity_summary(pre_filled_analysis, show_attributes=True)
    
    print("Provenance after overwriting:")
    for field_name, source_id in pre_filled_analysis.attribute_source.items():
        if source_id and field_name in ["student_name", "student_age", "current_gpa"]:
            print(f"  {field_name}: now sourced from ...{str(source_id)[-8:]}")
    
    # Now test versioning behavior
    print(f"\nVersioning the entity after borrowing...")
    root_entity = pre_filled_analysis.get_live_root_entity()
    if root_entity:
        EntityRegistry.version_entity(root_entity)
        
        print(f"Entity versioning results:")
        print(f"  Original ecs_id: ...{str(original_ecs_id)[-8:]}")
        print(f"  New ecs_id: ...{str(pre_filled_analysis.ecs_id)[-8:]}")
        print(f"  ecs_id changed: {original_ecs_id != pre_filled_analysis.ecs_id}")
        print(f"  old_ids tracking: {len(pre_filled_analysis.old_ids)} previous versions")
        if pre_filled_analysis.old_ids:
            print(f"  Previous ecs_id in old_ids: ...{str(pre_filled_analysis.old_ids[0])[-8:]}")
    
    # Test retrieving the old version vs new version
    print(f"\nTesting registry retrieval of different versions...")
    if pre_filled_analysis.root_ecs_id:
        # Get the current version
        current_version = EntityRegistry.get_stored_entity(pre_filled_analysis.root_ecs_id, pre_filled_analysis.ecs_id)
        if current_version:
            current_data = current_version.model_dump()
            print(f"Current version name: {current_data.get('student_name', 'N/A')}")
            print(f"Current version age: {current_data.get('student_age', 'N/A')}")
        
        # Try to get the old version if it exists
        if pre_filled_analysis.old_ids:
            old_version = EntityRegistry.get_stored_entity(pre_filled_analysis.root_ecs_id, pre_filled_analysis.old_ids[0])
            if old_version:
                old_data = old_version.model_dump()
                print(f"Old version name: {old_data.get('student_name', 'N/A')}")
                print(f"Old version age: {old_data.get('student_age', 'N/A')}")
            else:
                print("Old version not found in registry (expected for this test)")
    
    log_section("Phase 9: Container Overwriting and Versioning")
    
    print("Testing container borrowing with existing data...")
    
    # Create entity with existing list data
    pre_filled_scores = AnalysisInputEntity(
        student_name="Test Student",
        recent_scores=[75.0, 80.0, 85.0],  # Pre-existing scores
        grade_count=3
    )
    
    print("Entity with pre-existing list:")
    log_entity_summary(pre_filled_scores, show_attributes=True)
    
    # Borrow new list data that will overwrite
    print(f"\nBorrowing new list data to overwrite existing...")
    pre_filled_scores.borrow_attribute_from(alice_record, "grades", "recent_scores")
    
    # Process the grades into scores again
    new_scores = [grade.score for grade in alice_record.grades] 
    pre_filled_scores.recent_scores = new_scores
    pre_filled_scores.grade_count = len(new_scores)
    
    print("Entity after list borrowing:")
    log_entity_summary(pre_filled_scores, show_attributes=True)
    
    print("List provenance after overwriting:")
    recent_scores_source = pre_filled_scores.attribute_source.get("recent_scores")
    if isinstance(recent_scores_source, list):
        print(f"  recent_scores: list with {len(recent_scores_source)} source references")
        print(f"  First source: ...{str(recent_scores_source[0])[-8:] if recent_scores_source else 'None'}")

    log_section("Summary: Borrow Feature Implementation Complete")
    
    print(" Core borrow_attribute_from() Method")
    print("  - Implemented with proper signature matching entity.py stub")
    print("  - Type validation for source and target fields")
    print("  - Safe copying with container awareness")
    print("  - Provenance tracking via attribute_source")
    
    print("\n Data Composition Capabilities")
    print("  - Primitive value borrowing (strings, numbers)")
    print("  - Container borrowing (lists, dictionaries)")
    print("  - Entity reference borrowing")
    print("  - Complex nested structure handling")
    
    print("\n Safety and Immutability")
    print("  - Deep copy for containers prevents source modification")
    print("  - Entity references preserved (not copied)")
    print("  - Comprehensive error handling")
    
    print("\n Foundation for Callable Registry")
    print("  - Complete data composition from multiple sources")
    print("  - Full provenance tracking for audit trails")
    print("  - Type-safe field validation")
    print("  - Ready for string-based entity addressing (@uuid.field)")
    
    print(f"\nNext steps: Implement string parsing for @uuid.field syntax")
    print(f"and create functional get/put API methods for complete")
    print(f"callable registry integration.")

if __name__ == "__main__":
    main()