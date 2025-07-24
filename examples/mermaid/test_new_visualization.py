"""
Test New Entity Visualization Functions

Test the fresh entity visualization functions with entities from readme examples.
"""

import sys
from pathlib import Path

# Add the project root to the path so we can import abstractions
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from abstractions.ecs.entity import Entity, build_entity_tree
from entity_graph_visualization import entity_to_mermaid_graph, entity_tree_to_mermaid_graph, analyze_entity_tree_structure
from utils.mermaid_renderer import quick_render, print_mermaid_code

from pydantic import Field
from typing import List

# Define entities from readme examples
class Student(Entity):
    name: str = ""
    gpa: float = 0.0

class Assessment(Entity):
    student_id: str = Field(default="")
    performance_level: str = Field(default="")
    gpa_score: float = Field(default=0.0)

class Recommendation(Entity):
    student_id: str = Field(default="")
    action: str = Field(default="")
    reasoning: str = Field(default="")

class Course(Entity):
    name: str = ""
    credits: int = 0
    grade: str = ""

class GradeBook(Entity):
    course_name: str = ""
    students: List[Student] = Field(default_factory=list)
    assessments: List[Assessment] = Field(default_factory=list)

def test_simple_entity():
    """Test with a simple single entity."""
    print("Testing simple entity visualization...")
    
    student = Student(name="Alice", gpa=3.8)
    student.promote_to_root()
    
    # Generate mermaid
    mermaid_code = entity_to_mermaid_graph(student)
    print_mermaid_code(mermaid_code, "Simple Entity - Student")
    
    # Render
    quick_render(mermaid_code, "Simple Entity - Student")
    
    return mermaid_code

def test_entity_with_relationships():
    """Test with entity that has relationships."""
    print("\\nTesting entity with relationships...")
    
    # Create entities
    student = Student(name="Bob", gpa=3.5)
    
    assessment = Assessment(
        student_id=str(student.ecs_id),
        performance_level="high",
        gpa_score=3.5
    )
    
    recommendation = Recommendation(
        student_id=str(student.ecs_id),
        action="advanced_placement",
        reasoning="Strong performance"
    )
    
    # Create a container entity to hold relationships
    class StudentProfile(Entity):
        student: Student = Field(default_factory=lambda: Student())
        assessment: Assessment = Field(default_factory=lambda: Assessment())
        recommendation: Recommendation = Field(default_factory=lambda: Recommendation())
    
    profile = StudentProfile(
        student=student,
        assessment=assessment,
        recommendation=recommendation
    )
    profile.promote_to_root()
    
    # Generate mermaid
    mermaid_code = entity_to_mermaid_graph(profile)
    print_mermaid_code(mermaid_code, "Entity with Relationships")
    
    # Render
    quick_render(mermaid_code, "Entity with Relationships")
    
    return mermaid_code

def test_container_entities():
    """Test with entities that contain lists."""
    print("\\nTesting container entities...")
    
    # Create students
    alice = Student(name="Alice", gpa=3.8)
    bob = Student(name="Bob", gpa=3.2)
    charlie = Student(name="Charlie", gpa=3.9)
    
    # Create assessments
    alice_assessment = Assessment(
        student_id=str(alice.ecs_id),
        performance_level="high",
        gpa_score=3.8
    )
    
    bob_assessment = Assessment(
        student_id=str(bob.ecs_id),
        performance_level="standard",
        gpa_score=3.2
    )
    
    # Create gradebook
    gradebook = GradeBook(
        course_name="Advanced Computer Science",
        students=[alice, bob, charlie],
        assessments=[alice_assessment, bob_assessment]
    )
    gradebook.promote_to_root()
    
    # Generate mermaid
    mermaid_code = entity_to_mermaid_graph(gradebook)
    print_mermaid_code(mermaid_code, "Container Entities - GradeBook")
    
    # Render
    quick_render(mermaid_code, "Container Entities - GradeBook")
    
    # Analyze structure
    tree = build_entity_tree(gradebook)
    analysis = analyze_entity_tree_structure(tree)
    
    print("\\nTree Analysis:")
    print(f"   - Nodes: {analysis['node_count']}")
    print(f"   - Edges: {analysis['edge_count']}")
    print(f"   - Max depth: {analysis['max_depth']}")
    print(f"   - Entity types: {analysis['entity_types']}")
    print(f"   - Edge types: {analysis['edge_types']}")
    print(f"   - Hierarchical edges: {analysis['hierarchical_edges']}")
    
    return mermaid_code

def test_different_styles():
    """Test different visualization styles."""
    print("\\nTesting different visualization styles...")
    
    # Create a simple hierarchy
    student = Student(name="Diana", gpa=3.6)
    assessment = Assessment(
        student_id=str(student.ecs_id),
        performance_level="high",
        gpa_score=3.6
    )
    
    class StudentRecord(Entity):
        student: Student = Field(default_factory=lambda: Student())
        assessment: Assessment = Field(default_factory=lambda: Assessment())
    
    record = StudentRecord(student=student, assessment=assessment)
    record.promote_to_root()
    
    # Test with attributes
    mermaid_with_attrs = entity_to_mermaid_graph(record, include_attributes=True)
    print_mermaid_code(mermaid_with_attrs, "With Attributes")
    quick_render(mermaid_with_attrs, "With Attributes")
    
    # Test without attributes
    mermaid_simple = entity_to_mermaid_graph(record, include_attributes=False)
    print_mermaid_code(mermaid_simple, "Simple Style")
    quick_render(mermaid_simple, "Simple Style")
    
    return mermaid_with_attrs, mermaid_simple

def main():
    """Main test function."""
    print("Testing New Entity Visualization Functions")
    print("=" * 60)
    
    try:
        # Test simple entity
        simple_code = test_simple_entity()
        
        # Test entity with relationships
        relationship_code = test_entity_with_relationships()
        
        # Test container entities
        container_code = test_container_entities()
        
        # Test different styles
        with_attrs, simple_style = test_different_styles()
        
        print("\\nAll tests completed successfully!")
        print("\\nGenerated visualizations:")
        print("   - Simple entity")
        print("   - Entity with relationships")
        print("   - Container entities (GradeBook)")
        print("   - Different styles (with/without attributes)")
        
    except Exception as e:
        print(f"\\nError during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()