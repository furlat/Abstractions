#!/usr/bin/env python3
"""
Base ECS Example: Academic System Showcase

This example demonstrates the core features of the Entity system using
an academic system with students, courses, grades, and universities.

Features demonstrated:
- Entity creation with automatic identity management
- Entity tree construction and registration
- Multi-dimensional registry indexing
- Immutable retrieval with fresh live_ids
- Change detection and automatic versioning
- Mermaid diagram generation for visualization
"""

from typing import List, Optional
from pydantic import Field
from uuid import UUID

# Import the entity system
import sys
import os
# Add parent directory to path to find abstractions module
# sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from abstractions.ecs.entity import (
    Entity, EntityRegistry, build_entity_tree, 
    find_modified_entities, generate_mermaid_diagram
)

def log_section(title: str):
    """Clean section logging to avoid overwhelming output."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def log_entity_summary(entity: Entity, show_fields: bool = False):
    """Log entity summary with shortened UUIDs."""
    print(f"  {entity.__class__.__name__}:")
    print(f"    ecs_id: ...{str(entity.ecs_id)[-8:]}")
    print(f"    live_id: ...{str(entity.live_id)[-8:]}")
    # Check for name field dynamically
    entity_data = entity.model_dump()
    if 'name' in entity_data:
        print(f"    name: {entity_data['name']}")
    if show_fields:
        excluded_fields = {'ecs_id', 'live_id', 'created_at', 'forked_at', 
                          'previous_ecs_id', 'lineage_id', 'old_ids', 
                          'root_ecs_id', 'root_live_id', 'from_storage', 'attribute_source'}
        for field_name, field_value in entity_data.items():
            if field_name not in excluded_fields:
                if isinstance(field_value, list) and len(field_value) > 2:
                    print(f"    {field_name}: [list with {len(field_value)} items]")
                elif isinstance(field_value, str) and len(field_value) > 50:
                    print(f"    {field_name}: {field_value[:47]}...")
                else:
                    print(f"    {field_name}: {field_value}")

# Define Academic System Entities
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
    """A grade with course info and score - no student reference to avoid circular refs."""
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

class University(Entity):
    """University entity containing courses and records - simplified to avoid circular refs."""
    name: str
    location: str
    courses: List[Course] = Field(default_factory=list)
    records: List[AcademicRecord] = Field(default_factory=list)
    established_year: int = 2000

def main():
    """Main demonstration of entity system features."""
    
    log_section("Phase 1: Entity Creation and Identity Management")
    
    # Create individual entities
    print("Creating Student entities...")
    alice = Student(
        name="Alice Johnson",
        age=20,
        email="alice.johnson@university.edu",
        student_id="STU001"
    )
    bob = Student(
        name="Bob Smith", 
        age=22,
        email="bob.smith@university.edu",
        student_id="STU002"
    )
    
    print("Creating Course entities...")
    math101 = Course(
        title="Calculus I",
        code="MATH101", 
        credits=4,
        description="Introduction to differential calculus"
    )
    cs200 = Course(
        title="Data Structures",
        code="CS200",
        credits=3,
        description="Fundamental data structures and algorithms"
    )
    
    print("Creating Grade entities...")
    alice_math_grade = Grade(
        course_code="MATH101",
        course_title="Calculus I",
        score=92.5,
        semester="Fall 2023",
        letter_grade="A"
    )
    bob_cs_grade = Grade(
        course_code="CS200",
        course_title="Data Structures",
        score=87.0,
        semester="Fall 2023", 
        letter_grade="B+"
    )
    
    print("Creating AcademicRecord entities...")
    alice_record = AcademicRecord(
        student=alice,
        grades=[alice_math_grade],
        gpa=3.85,
        total_credits=4
    )
    bob_record = AcademicRecord(
        student=bob,
        grades=[bob_cs_grade],
        gpa=3.33,
        total_credits=3
    )
    
    print("Creating University entity...")
    # Create a simplified university without circular references
    university = University(
        name="Tech University",
        location="Silicon Valley",
        courses=[math101, cs200],
        records=[alice_record, bob_record],
        established_year=1995
    )
    
    # Show entity identities
    print(f"\nEntity Identity Examples:")
    log_entity_summary(alice)
    log_entity_summary(math101)
    log_entity_summary(university)
    
    log_section("Phase 2: Entity Tree Construction and Registration")
    
    print("Building entity tree from University root...")
    university_tree = build_entity_tree(university)
    
    print(f"Tree Statistics:")
    print(f"  Nodes: {len(university_tree.nodes)}")
    print(f"  Edges: {len(university_tree.edges)}")
    print(f"  Max Depth: {university_tree.max_depth}")
    
    print(f"\nDiscovered Entities:")
    for ecs_id, entity in university_tree.nodes.items():
        entity_data = entity.model_dump()
        name = entity_data.get('name', 'N/A')
        print(f"  {entity.__class__.__name__}: {name} (...{str(ecs_id)[-8:]})")
    
    print(f"\nPromoting university to root and registering...")
    university.promote_to_root()
    
    print(f"Registry Statistics:")
    print(f"  Trees registered: {len(EntityRegistry.tree_registry)}")
    print(f"  Type registry: {len(EntityRegistry.type_registry)}")
    print(f"  Live entity mappings: {len(EntityRegistry.live_id_registry)}")
    
    log_section("Phase 3: Immutable Retrieval and Fresh Contexts")
    
    print("Retrieving university tree with fresh live_ids...")
    if university.root_ecs_id is None:
        raise ValueError("University has no root_ecs_id")
    retrieved_university_tree = EntityRegistry.get_stored_tree(university.root_ecs_id)
    if retrieved_university_tree is None:
        raise ValueError("Failed to retrieve university tree")
    retrieved_university = retrieved_university_tree.nodes[university.ecs_id]
    
    print(f"Original vs Retrieved University:")
    print(f"  Original ecs_id: ...{str(university.ecs_id)[-8:]}")
    print(f"  Retrieved ecs_id: ...{str(retrieved_university.ecs_id)[-8:]}")
    print(f"  Original live_id: ...{str(university.live_id)[-8:]}")
    print(f"  Retrieved live_id: ...{str(retrieved_university.live_id)[-8:]}")
    print(f"  Identity preserved: {university.ecs_id == retrieved_university.ecs_id}")
    print(f"  Runtime isolated: {university.live_id != retrieved_university.live_id}")
    
    # Show that changes to retrieved copy don't affect original
    print(f"\nTesting immutability - modifying retrieved copy...")
    original_name = university.name
    # Use setattr to modify the name dynamically since it's not part of base Entity
    setattr(retrieved_university, 'name', "Modified University Name")
    
    print(f"  Original name: {university.name}")
    print(f"  Retrieved name: {getattr(retrieved_university, 'name')}")
    print(f"  Original unchanged: {university.name == original_name}")
    
    log_section("Phase 4: Change Detection and Versioning")
    
    print("Making changes to the university...")
    # Add a new student by creating a new academic record
    charlie = Student(
        name="Charlie Brown",
        age=19,
        email="charlie.brown@university.edu", 
        student_id="STU003"
    )
    charlie_grade = Grade(
        course_code="MATH101",
        course_title="Calculus I", 
        score=88.0,
        semester="Spring 2024",
        letter_grade="B+"
    )
    charlie_record = AcademicRecord(
        student=charlie,
        grades=[charlie_grade],
        gpa=3.30,
        total_credits=4
    )
    university.records.append(charlie_record)
    
    # Modify existing student
    alice.age = 21  # Birthday!
    
    # Add new grade
    alice_cs_grade = Grade(
        course_code="CS200",
        course_title="Data Structures",
        score=95.0,
        semester="Spring 2024",
        letter_grade="A"
    )
    alice_record.grades.append(alice_cs_grade)
    alice_record.gpa = 3.90
    
    print("Detecting changes...")
    current_tree = build_entity_tree(university)
    if university.root_ecs_id is None:
        raise ValueError("University has no root_ecs_id for change detection")
    original_tree = EntityRegistry.get_stored_tree(university.root_ecs_id)
    if original_tree is None:
        raise ValueError("Failed to retrieve original tree")
    
    modified_entities = find_modified_entities(current_tree, original_tree)
    
    print(f"Modified entities detected: {len(modified_entities)}")
    for ecs_id in modified_entities:
        if isinstance(ecs_id, UUID):
            entity = current_tree.nodes.get(ecs_id)
            if entity:
                print(f"  Modified: {entity.__class__.__name__} (...{str(ecs_id)[-8:]})")
    
    print("Versioning the university with changes...")
    root_entity = university.get_live_root_entity()
    if root_entity is None:
        raise ValueError("Failed to get live root entity")
    EntityRegistry.version_entity(root_entity)
    
    print(f"Updated registry statistics:")
    print(f"  Trees: {len(EntityRegistry.tree_registry)}")
    versioned_entities = [e for e in EntityRegistry.live_id_registry.values() if e.old_ids]
    print(f"  Versioned entities: {len(versioned_entities)}")
    
    log_section("Phase 5: Tree Visualization")
    
    print("Generating Mermaid diagram of the academic system...")
    mermaid_diagram = generate_mermaid_diagram(current_tree, include_attributes=False)
    
    print("Mermaid Diagram (excerpt):")
    lines = mermaid_diagram.split('\n')
    for i, line in enumerate(lines[:15]):  # Show first 15 lines
        print(f"  {line}")
    if len(lines) > 15:
        print(f"  ... ({len(lines) - 15} more lines)")
    
    print(f"\nFull diagram contains {len(lines)} lines showing:")
    print(f"  - Entity nodes with types and names")
    print(f"  - Hierarchical relationships") 
    print(f"  - Container relationships (lists, direct references)")
    print(f"  - Root entity highlighting")
    
    log_section("Phase 6: Registry Query Capabilities")
    
    print("Demonstrating registry query features...")
    
    # Get entities by type from type registry  
    university_lineages = EntityRegistry.type_registry.get(University, [])
    course_lineages = EntityRegistry.type_registry.get(Course, [])
    
    print(f"Entity lineages by type:")
    print(f"  University lineages: {len(university_lineages)}")
    print(f"  Course lineages: {len(course_lineages)}")
    
    # Find root from university (which is a root entity)
    university_root = EntityRegistry.get_live_root_from_entity(university)
    if university_root is None:
        raise ValueError("Failed to get university's root entity")
    university_data = university_root.model_dump()
    print(f"\nRoot entity from University: {university_data.get('name', 'Unknown')} (...{str(university_root.ecs_id)[-8:]})")
    
    # Get specific entity from tree
    if university.root_ecs_id is None:
        raise ValueError("University has no root_ecs_id for entity retrieval")
    retrieved_alice = EntityRegistry.get_stored_entity(university.root_ecs_id, alice.ecs_id)
    if retrieved_alice is None:
        raise ValueError("Failed to retrieve Alice")
    alice_data = retrieved_alice.model_dump()
    print(f"Retrieved Alice: {alice_data.get('name', 'Unknown')} (age: {alice_data.get('age', 'Unknown')})")
    
    # Show entity lookup by live_id (for live entities in memory)
    alice_from_registry = EntityRegistry.get_live_entity(alice.live_id)
    if alice_from_registry:
        alice_data = alice_from_registry.model_dump()
        print(f"Alice from live registry: {alice_data.get('name', 'Unknown')} (...{str(alice_from_registry.ecs_id)[-8:]})")
    
    log_section("Summary: Entity System Core Features Demonstrated")
    
    print(" Entity Identity Management")
    print("  - Automatic ecs_id/live_id assignment")
    print("  - Lineage tracking with lineage_id")
    print("  - Root context with root_ecs_id/root_live_id")
    
    print("\n Entity Tree Construction")
    print("  - Automatic discovery of nested entities")
    print("  - Edge classification (DIRECT, LIST, etc.)")
    print("  - Circular reference detection")
    
    print("\n Registry Storage & Retrieval")  
    print("  - Multi-dimensional indexing")
    print("  - Immutable deep copy retrieval")
    print("  - Type-based entity queries")
    
    print("\n Change Detection & Versioning")
    print("  - Structural and attribute-level comparison")
    print("  - Automatic propagation of changes")
    print("  - Complete lineage preservation")
    
    print("\n Tree Analysis & Visualization")
    print("  - Mermaid diagram generation")
    print("  - Relationship queries")
    print("  - Ancestry path analysis")
    
    print(f"\nThe entity system successfully managed {len(current_tree.nodes)} entities")
    print(f"across {len(current_tree.edges)} relationships with complete")
    print(f"version tracking and audit trail capabilities.")

if __name__ == "__main__":
    main()