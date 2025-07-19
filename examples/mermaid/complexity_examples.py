"""
Multiple Examples of Increasing Complexity

This script demonstrates the entity visualization system with examples of increasing complexity,
from simple entities to complex hierarchical structures.
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from abstractions.ecs.entity import Entity, build_entity_tree
from entity_graph_visualization import entity_to_mermaid_graph, analyze_entity_tree_structure
from utils.mermaid_renderer import quick_render, print_mermaid_code

from pydantic import Field

def example_1_simple_entity():
    """Example 1: Single entity with basic attributes."""
    print("Example 1: Simple Entity")
    print("-" * 40)
    
    class Person(Entity):
        name: str = ""
        age: int = 0
        email: str = ""
    
    person = Person(name="Alice", age=30, email="alice@example.com")
    person.promote_to_root()
    
    mermaid_code = entity_to_mermaid_graph(person)
    print_mermaid_code(mermaid_code, "Example 1: Simple Entity")
    quick_render(mermaid_code, "Example 1: Simple Entity")
    
    return person

def example_2_parent_child():
    """Example 2: Parent-child relationship."""
    print("\nExample 2: Parent-Child Relationship")
    print("-" * 40)
    
    class Person(Entity):
        name: str = ""
        age: int = 0
    
    class Address(Entity):
        street: str = ""
        city: str = ""
        zipcode: str = ""
    
    class PersonWithAddress(Entity):
        name: str = ""
        age: int = 0
        address: Address = Field(default_factory=lambda: Address())
    
    person = PersonWithAddress(
        name="Bob",
        age=25,
        address=Address(street="123 Main St", city="Springfield", zipcode="12345")
    )
    person.promote_to_root()
    
    mermaid_code = entity_to_mermaid_graph(person)
    print_mermaid_code(mermaid_code, "Example 2: Parent-Child Relationship")
    quick_render(mermaid_code, "Example 2: Parent-Child Relationship")
    
    return person

def example_3_list_container():
    """Example 3: Entity with list of sub-entities."""
    print("\nExample 3: List Container")
    print("-" * 40)
    
    class Task(Entity):
        title: str = ""
        status: str = ""
        priority: int = 0
    
    class Project(Entity):
        name: str = ""
        description: str = ""
        tasks: List[Task] = Field(default_factory=list)
    
    project = Project(
        name="Website Redesign",
        description="Modernize company website",
        tasks=[
            Task(title="Design mockups", status="completed", priority=1),
            Task(title="Implement frontend", status="in_progress", priority=2),
            Task(title="Backend integration", status="pending", priority=3),
            Task(title="Testing", status="pending", priority=4)
        ]
    )
    project.promote_to_root()
    
    mermaid_code = entity_to_mermaid_graph(project)
    print_mermaid_code(mermaid_code, "Example 3: List Container")
    quick_render(mermaid_code, "Example 3: List Container")
    
    # Show analysis
    tree = build_entity_tree(project)
    analysis = analyze_entity_tree_structure(tree)
    print(f"Tree Analysis: {analysis['node_count']} nodes, {analysis['edge_count']} edges")
    
    return project

def example_4_multiple_containers():
    """Example 4: Multiple container types."""
    print("\nExample 4: Multiple Container Types")
    print("-" * 40)
    
    class Student(Entity):
        name: str = ""
        gpa: float = 0.0
        year: str = ""
    
    class Instructor(Entity):
        name: str = ""
        department: str = ""
        title: str = ""
    
    class Course(Entity):
        name: str = ""
        code: str = ""
        credits: int = 0
        instructor: Instructor = Field(default_factory=lambda: Instructor())
        students: List[Student] = Field(default_factory=list)
    
    course = Course(
        name="Advanced Computer Science",
        code="CS401",
        credits=4,
        instructor=Instructor(name="Dr. Smith", department="Computer Science", title="Professor"),
        students=[
            Student(name="Alice", gpa=3.8, year="Senior"),
            Student(name="Bob", gpa=3.2, year="Junior"),
            Student(name="Charlie", gpa=3.9, year="Senior")
        ]
    )
    course.promote_to_root()
    
    mermaid_code = entity_to_mermaid_graph(course)
    print_mermaid_code(mermaid_code, "Example 4: Multiple Container Types")
    quick_render(mermaid_code, "Example 4: Multiple Container Types")
    
    # Show analysis
    tree = build_entity_tree(course)
    analysis = analyze_entity_tree_structure(tree)
    print(f"Tree Analysis: {analysis['node_count']} nodes, {analysis['edge_count']} edges")
    print(f"Entity types: {analysis['entity_types']}")
    
    return course

def example_5_nested_hierarchy():
    """Example 5: Nested hierarchical structure."""
    print("\nExample 5: Nested Hierarchical Structure")
    print("-" * 40)
    
    class Address(Entity):
        street: str = ""
        city: str = ""
        state: str = ""
        zipcode: str = ""
    
    class Contact(Entity):
        email: str = ""
        phone: str = ""
        address: Address = Field(default_factory=lambda: Address())
    
    class Employee(Entity):
        name: str = ""
        title: str = ""
        salary: float = 0.0
        contact: Contact = Field(default_factory=lambda: Contact())
    
    class Department(Entity):
        name: str = ""
        budget: float = 0.0
        manager: Employee = Field(default_factory=lambda: Employee())
        employees: List[Employee] = Field(default_factory=list)
    
    class Company(Entity):
        name: str = ""
        founded: int = 0
        departments: List[Department] = Field(default_factory=list)
    
    company = Company(
        name="Tech Corp",
        founded=2010,
        departments=[
            Department(
                name="Engineering",
                budget=1000000,
                manager=Employee(
                    name="John Manager",
                    title="VP Engineering",
                    salary=150000,
                    contact=Contact(
                        email="john@techcorp.com",
                        phone="555-0101",
                        address=Address(street="123 Tech St", city="San Francisco", state="CA", zipcode="94105")
                    )
                ),
                employees=[
                    Employee(
                        name="Alice Developer",
                        title="Senior Developer",
                        salary=120000,
                        contact=Contact(
                            email="alice@techcorp.com",
                            phone="555-0102",
                            address=Address(street="456 Code Ave", city="San Francisco", state="CA", zipcode="94107")
                        )
                    ),
                    Employee(
                        name="Bob Tester",
                        title="QA Engineer",
                        salary=90000,
                        contact=Contact(
                            email="bob@techcorp.com",
                            phone="555-0103",
                            address=Address(street="789 Test Blvd", city="San Francisco", state="CA", zipcode="94108")
                        )
                    )
                ]
            ),
            Department(
                name="Sales",
                budget=500000,
                manager=Employee(
                    name="Sarah Sales",
                    title="Sales Director",
                    salary=130000,
                    contact=Contact(
                        email="sarah@techcorp.com",
                        phone="555-0201",
                        address=Address(street="321 Sales St", city="San Francisco", state="CA", zipcode="94109")
                    )
                ),
                employees=[
                    Employee(
                        name="Mike Seller",
                        title="Account Manager",
                        salary=80000,
                        contact=Contact(
                            email="mike@techcorp.com",
                            phone="555-0202",
                            address=Address(street="654 Deal Dr", city="San Francisco", state="CA", zipcode="94110")
                        )
                    )
                ]
            )
        ]
    )
    company.promote_to_root()
    
    mermaid_code = entity_to_mermaid_graph(company)
    print_mermaid_code(mermaid_code, "Example 5: Nested Hierarchical Structure")
    quick_render(mermaid_code, "Example 5: Nested Hierarchical Structure")
    
    # Show analysis
    tree = build_entity_tree(company)
    analysis = analyze_entity_tree_structure(tree)
    print(f"Tree Analysis: {analysis['node_count']} nodes, {analysis['edge_count']} edges")
    print(f"Max depth: {analysis['max_depth']}")
    print(f"Entity types: {analysis['entity_types']}")
    print(f"Edge types: {analysis['edge_types']}")
    
    return company

def example_6_complex_multi_type():
    """Example 6: Complex structure with multiple entity types and relationships."""
    print("\nExample 6: Complex Multi-Type Structure")
    print("-" * 40)
    
    class Tag(Entity):
        name: str = ""
        color: str = ""
    
    class Comment(Entity):
        author: str = ""
        content: str = ""
        timestamp: str = ""
    
    class Attachment(Entity):
        filename: str = ""
        size: int = 0
        type: str = ""
    
    class Task(Entity):
        title: str = ""
        description: str = ""
        status: str = ""
        priority: int = 0
        assignee: str = ""
        tags: List[Tag] = Field(default_factory=list)
        comments: List[Comment] = Field(default_factory=list)
        attachments: List[Attachment] = Field(default_factory=list)
    
    class Sprint(Entity):
        name: str = ""
        start_date: str = ""
        end_date: str = ""
        tasks: List[Task] = Field(default_factory=list)
    
    class Project(Entity):
        name: str = ""
        description: str = ""
        status: str = ""
        sprints: List[Sprint] = Field(default_factory=list)
        global_tags: List[Tag] = Field(default_factory=list)
    
    project = Project(
        name="E-commerce Platform",
        description="Full-stack e-commerce solution",
        status="active",
        global_tags=[
            Tag(name="urgent", color="red"),
            Tag(name="backend", color="blue"),
            Tag(name="frontend", color="green")
        ],
        sprints=[
            Sprint(
                name="Sprint 1 - Foundation",
                start_date="2024-01-01",
                end_date="2024-01-14",
                tasks=[
                    Task(
                        title="Setup database schema",
                        description="Design and implement initial database structure",
                        status="completed",
                        priority=1,
                        assignee="Alice",
                        tags=[
                            Tag(name="database", color="purple"),
                            Tag(name="backend", color="blue")
                        ],
                        comments=[
                            Comment(author="Alice", content="Database schema ready for review", timestamp="2024-01-05T10:30:00Z"),
                            Comment(author="Bob", content="Looks good, approved!", timestamp="2024-01-05T14:15:00Z")
                        ],
                        attachments=[
                            Attachment(filename="schema.sql", size=15632, type="sql"),
                            Attachment(filename="er_diagram.png", size=98765, type="image")
                        ]
                    ),
                    Task(
                        title="User authentication API",
                        description="Implement JWT-based authentication system",
                        status="in_progress",
                        priority=2,
                        assignee="Bob",
                        tags=[
                            Tag(name="auth", color="orange"),
                            Tag(name="api", color="yellow")
                        ],
                        comments=[
                            Comment(author="Bob", content="Working on JWT implementation", timestamp="2024-01-08T09:00:00Z")
                        ],
                        attachments=[
                            Attachment(filename="auth_spec.pdf", size=45678, type="pdf")
                        ]
                    )
                ]
            ),
            Sprint(
                name="Sprint 2 - Core Features",
                start_date="2024-01-15",
                end_date="2024-01-28",
                tasks=[
                    Task(
                        title="Product catalog UI",
                        description="Create responsive product listing and details pages",
                        status="planned",
                        priority=1,
                        assignee="Charlie",
                        tags=[
                            Tag(name="ui", color="pink"),
                            Tag(name="frontend", color="green")
                        ],
                        comments=[],
                        attachments=[]
                    )
                ]
            )
        ]
    )
    project.promote_to_root()
    
    mermaid_code = entity_to_mermaid_graph(project)
    print_mermaid_code(mermaid_code, "Example 6: Complex Multi-Type Structure")
    quick_render(mermaid_code, "Example 6: Complex Multi-Type Structure")
    
    # Show detailed analysis
    tree = build_entity_tree(project)
    analysis = analyze_entity_tree_structure(tree)
    print(f"Tree Analysis:")
    print(f"  - Nodes: {analysis['node_count']}")
    print(f"  - Edges: {analysis['edge_count']}")
    print(f"  - Max depth: {analysis['max_depth']}")
    print(f"  - Entity types: {analysis['entity_types']}")
    print(f"  - Edge types: {analysis['edge_types']}")
    print(f"  - Hierarchical edges: {analysis['hierarchical_edges']}")
    
    return project

def run_all_examples():
    """Run all examples in sequence."""
    print("Entity Visualization - Complexity Examples")
    print("=" * 60)
    
    examples = [
        example_1_simple_entity,
        example_2_parent_child,
        example_3_list_container,
        example_4_multiple_containers,
        example_5_nested_hierarchy,
        example_6_complex_multi_type
    ]
    
    results = []
    for example_func in examples:
        try:
            result = example_func()
            results.append(result)
        except Exception as e:
            print(f"Error in {example_func.__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("All examples completed!")
    print(f"Generated {len(results)} visualizations of increasing complexity")
    
    # Summary
    print("\nComplexity Summary:")
    for i, result in enumerate(results, 1):
        if result:
            tree = build_entity_tree(result)
            analysis = analyze_entity_tree_structure(tree)
            print(f"  Example {i}: {analysis['node_count']} nodes, {analysis['edge_count']} edges, depth {analysis['max_depth']}")
    
    return results

if __name__ == "__main__":
    run_all_examples()