"""
Comprehensive Diff Test Scenarios

This script creates various before/after scenarios to test the diff algorithm
and visualize different types of changes in entity graphs.
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set, Any
from uuid import UUID
import copy

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from abstractions.ecs.entity import Entity, EntityTree, build_entity_tree, find_modified_entities
from entity_graph_visualization import entity_to_mermaid_graph, entity_tree_to_mermaid_graph
from utils.mermaid_renderer import quick_render, print_mermaid_code

from pydantic import Field
from enum import Enum
from dataclasses import dataclass

# Diff Visualization Functions
class ChangeType(Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    MOVED = "moved"
    UNCHANGED = "unchanged"

@dataclass
class EntityDiff:
    entity_id: UUID
    change_type: ChangeType
    old_entity: Optional[Entity]
    new_entity: Optional[Entity]

@dataclass
class TreeDiff:
    added_entities: Set[UUID]
    removed_entities: Set[UUID]
    modified_entities: Set[UUID]
    moved_entities: Set[UUID]
    unchanged_entities: Set[UUID]
    entity_diffs: Dict[UUID, EntityDiff]
    old_tree: EntityTree
    new_tree: EntityTree

def analyze_tree_diff(old_tree: EntityTree, new_tree: EntityTree) -> TreeDiff:
    """Convert find_modified_entities output into rich diff structure."""
    result = find_modified_entities(
        new_tree=new_tree,
        old_tree=old_tree,
        debug=True
    )
    
    if isinstance(result, tuple):
        modified_entities, debug_info = result
    else:
        modified_entities = result
        debug_info = {
            "comparison_count": 0,
            "added_entities": set(),
            "removed_entities": set(),
            "moved_entities": set(),
            "unchanged_entities": set()
        }
    
    # Extract change sets
    added_entities = debug_info["added_entities"]
    removed_entities = debug_info["removed_entities"]
    moved_entities = debug_info["moved_entities"]
    unchanged_entities = debug_info["unchanged_entities"]
    
    # Create entity diffs
    entity_diffs = {}
    
    # Added entities
    for entity_id in added_entities:
        entity = new_tree.get_entity(entity_id)
        if entity:
            entity_diffs[entity_id] = EntityDiff(
                entity_id=entity_id,
                change_type=ChangeType.ADDED,
                old_entity=None,
                new_entity=entity
            )
    
    # Removed entities
    for entity_id in removed_entities:
        entity = old_tree.get_entity(entity_id)
        if entity:
            entity_diffs[entity_id] = EntityDiff(
                entity_id=entity_id,
                change_type=ChangeType.REMOVED,
                old_entity=entity,
                new_entity=None
            )
    
    # Moved entities
    for entity_id in moved_entities:
        old_entity = old_tree.get_entity(entity_id)
        new_entity = new_tree.get_entity(entity_id)
        entity_diffs[entity_id] = EntityDiff(
            entity_id=entity_id,
            change_type=ChangeType.MOVED,
            old_entity=old_entity,
            new_entity=new_entity
        )
    
    # Unchanged entities
    for entity_id in unchanged_entities:
        entity = new_tree.get_entity(entity_id) or old_tree.get_entity(entity_id)
        if entity:
            entity_diffs[entity_id] = EntityDiff(
                entity_id=entity_id,
                change_type=ChangeType.UNCHANGED,
                old_entity=old_tree.get_entity(entity_id),
                new_entity=new_tree.get_entity(entity_id)
            )
    
    return TreeDiff(
        added_entities=added_entities,
        removed_entities=removed_entities,
        modified_entities=modified_entities,
        moved_entities=moved_entities,
        unchanged_entities=unchanged_entities,
        entity_diffs=entity_diffs,
        old_tree=old_tree,
        new_tree=new_tree
    )

def create_diff_node_label(entity_diff: EntityDiff) -> str:
    """Create a node label showing the change type and entity info."""
    from entity_graph_visualization import get_entity_key_attributes
    
    if entity_diff.change_type == ChangeType.ADDED and entity_diff.new_entity:
        entity = entity_diff.new_entity
        class_name = entity.__class__.__name__
        attrs = get_entity_key_attributes(entity)
        label_parts = [f"+ {class_name}"]
        if attrs:
            label_parts.extend(attrs)
        return "\\n".join(label_parts)
    
    elif entity_diff.change_type == ChangeType.REMOVED and entity_diff.old_entity:
        entity = entity_diff.old_entity
        class_name = entity.__class__.__name__
        attrs = get_entity_key_attributes(entity)
        label_parts = [f"- {class_name}"]
        if attrs:
            label_parts.extend(attrs)
        return "\\n".join(label_parts)
    
    elif entity_diff.change_type == ChangeType.MOVED and entity_diff.new_entity:
        entity = entity_diff.new_entity
        class_name = entity.__class__.__name__
        attrs = get_entity_key_attributes(entity)
        label_parts = [f"→ {class_name}"]
        if attrs:
            label_parts.extend(attrs)
        return "\\n".join(label_parts)
    
    else:  # UNCHANGED
        entity = entity_diff.new_entity or entity_diff.old_entity
        if entity:
            class_name = entity.__class__.__name__
            attrs = get_entity_key_attributes(entity)
            label_parts = [class_name]
            if attrs:
                label_parts.extend(attrs)
            return "\\n".join(label_parts)
        return "Unknown"

def tree_diff_to_mermaid_unified(tree_diff: TreeDiff) -> str:
    """Generate unified diff view showing all changes in one graph."""
    from entity_graph_visualization import create_node_id, create_edge_label
    
    lines = ["graph TD"]
    
    # Create nodes for all entities in the diff (except removed ones)
    nodes_created = set()
    
    for entity_id, entity_diff in tree_diff.entity_diffs.items():
        if entity_diff.change_type == ChangeType.REMOVED:
            continue
            
        entity = entity_diff.new_entity or entity_diff.old_entity
        if entity:
            node_id = create_node_id(entity)
            node_label = create_diff_node_label(entity_diff)
            lines.append(f"    {node_id}[\"{node_label}\"]")
            nodes_created.add(node_id)
    
    # Create edges from the new tree
    for (source_id, target_id), edge in tree_diff.new_tree.edges.items():
        source_entity = tree_diff.new_tree.get_entity(source_id)
        target_entity = tree_diff.new_tree.get_entity(target_id)
        
        if source_entity and target_entity:
            source_node = create_node_id(source_entity)
            target_node = create_node_id(target_entity)
            
            if source_node in nodes_created and target_node in nodes_created:
                edge_label = create_edge_label(edge)
                lines.append(f"    {source_node} -->|\\\"{edge_label}\\\"| {target_node}")
    
    # Add styling
    lines.append("")
    lines.append("    %% Change type styling")
    lines.append("    classDef added fill:#e8f5e8,stroke:#388e3c,stroke-width:3px")
    lines.append("    classDef removed fill:#ffcdd2,stroke:#d32f2f,stroke-width:3px")
    lines.append("    classDef moved fill:#e3f2fd,stroke:#1976d2,stroke-width:3px")
    lines.append("    classDef unchanged fill:#f5f5f5,stroke:#9e9e9e,stroke-width:2px")
    
    # Apply styling
    for entity_id, entity_diff in tree_diff.entity_diffs.items():
        if entity_diff.change_type == ChangeType.REMOVED:
            continue
            
        entity = entity_diff.new_entity or entity_diff.old_entity
        if entity:
            node_id = create_node_id(entity)
            class_name = entity_diff.change_type.value
            lines.append(f"    class {node_id} {class_name}")
    
    return "\n".join(lines)

def tree_diff_to_mermaid_sidebyside(tree_diff: TreeDiff) -> str:
    """Generate side-by-side comparison view showing before and after."""
    from entity_graph_visualization import create_node_id, create_edge_label, create_node_label
    
    lines = ["graph TB"]
    
    # Create all nodes first
    # Old tree nodes (left side)
    for entity_id, entity in tree_diff.old_tree.nodes.items():
        node_id = f"old_{create_node_id(entity)}"
        node_label = create_node_label(entity, include_attributes=True)
        lines.append(f"    {node_id}[\"{node_label}\"]")
    
    # New tree nodes (right side)
    for entity_id, entity in tree_diff.new_tree.nodes.items():
        node_id = f"new_{create_node_id(entity)}"
        node_label = create_node_label(entity, include_attributes=True)
        lines.append(f"    {node_id}[\"{node_label}\"]")
    
    lines.append("")
    
    # Create edges within old tree (hierarchical)
    for (source_id, target_id), edge in tree_diff.old_tree.edges.items():
        source_entity = tree_diff.old_tree.get_entity(source_id)
        target_entity = tree_diff.old_tree.get_entity(target_id)
        
        if source_entity and target_entity:
            source_node = f"old_{create_node_id(source_entity)}"
            target_node = f"old_{create_node_id(target_entity)}"
            edge_label = create_edge_label(edge)
            lines.append(f"    {source_node} -->|\"{edge_label}\"| {target_node}")
    
    # Create edges within new tree (hierarchical)
    for (source_id, target_id), edge in tree_diff.new_tree.edges.items():
        source_entity = tree_diff.new_tree.get_entity(source_id)
        target_entity = tree_diff.new_tree.get_entity(target_id)
        
        if source_entity and target_entity:
            source_node = f"new_{create_node_id(source_entity)}"
            target_node = f"new_{create_node_id(target_entity)}"
            edge_label = create_edge_label(edge)
            lines.append(f"    {source_node} -->|\"{edge_label}\"| {target_node}")
    
    lines.append("")
    
    # Add horizontal connection between roots for alignment
    old_root = tree_diff.old_tree.get_entity(tree_diff.old_tree.root_ecs_id)
    new_root = tree_diff.new_tree.get_entity(tree_diff.new_tree.root_ecs_id)
    if old_root and new_root:
        old_root_node = f"old_{create_node_id(old_root)}"
        new_root_node = f"new_{create_node_id(new_root)}"
        lines.append(f"    {old_root_node} -.-> {new_root_node}")
    
    lines.append("")
    
    # Add styling with diff colors
    lines.append("    %% Base styling (keep existing)")
    lines.append("    classDef rootNode fill:#f3e5f5,stroke:#4a148c,stroke-width:3px")
    lines.append("    classDef type_Address fill:#e8f5e8,stroke:#388e3c,stroke-width:2px")
    lines.append("    classDef type_Person fill:#e1f5fe,stroke:#01579b,stroke-width:2px")
    lines.append("    classDef type_Task fill:#fff3e0,stroke:#f57c00,stroke-width:2px")
    lines.append("    classDef type_Project fill:#fce4ec,stroke:#c2185b,stroke-width:2px")
    lines.append("")
    lines.append("    %% Diff styling (overlay on base)")
    lines.append("    classDef removed fill:#ffcdd2,stroke:#d32f2f,stroke-width:4px")
    lines.append("    classDef added fill:#c8e6c9,stroke:#388e3c,stroke-width:4px") 
    lines.append("    classDef changed fill:#e1bee7,stroke:#7b1fa2,stroke-width:4px")
    lines.append("")
    
    # Apply diff styling to nodes
    for entity_id, entity_diff in tree_diff.entity_diffs.items():
        if entity_diff.change_type == ChangeType.REMOVED and entity_diff.old_entity:
            old_node = f"old_{create_node_id(entity_diff.old_entity)}"
            lines.append(f"    class {old_node} removed")
        elif entity_diff.change_type == ChangeType.ADDED and entity_diff.new_entity:
            new_node = f"new_{create_node_id(entity_diff.new_entity)}"
            lines.append(f"    class {new_node} added")
        elif entity_diff.change_type == ChangeType.MOVED and entity_diff.old_entity and entity_diff.new_entity:
            old_node = f"old_{create_node_id(entity_diff.old_entity)}"
            new_node = f"new_{create_node_id(entity_diff.new_entity)}"
            lines.append(f"    class {old_node} changed")
            lines.append(f"    class {new_node} changed")
    
    return "\n".join(lines)

def validate_mermaid_code(mermaid_code: str) -> bool:
    """Basic validation of mermaid code to catch common issues."""
    lines = mermaid_code.split('\n')
    
    # Check for basic structure
    if not lines[0].strip().startswith('graph'):
        print(f"[MERMAID ERROR] First line should start with 'graph', got: {lines[0]}")
        return False
    
    # Check for balanced quotes
    for i, line in enumerate(lines, 1):
        if line.count('"') % 2 != 0:
            print(f"[MERMAID ERROR] Line {i} has unbalanced quotes: {line}")
            return False
    
    # Check for common syntax issues
    for i, line in enumerate(lines, 1):
        if '\\n' in line and not line.strip().startswith('//'):
            print(f"[MERMAID ERROR] Line {i} contains literal \\n: {line}")
            return False
    
    return True

def print_diff_summary(tree_diff: TreeDiff, title: str = "Diff Summary") -> None:
    """Print a summary of changes in the diff."""
    from entity_graph_visualization import shorten_uuid
    
    print(f"\\n{'='*60}")
    print(f"[DIFF] {title}")
    print('='*60)
    
    print(f"Added entities: {len(tree_diff.added_entities)}")
    print(f"Removed entities: {len(tree_diff.removed_entities)}")
    print(f"Moved entities: {len(tree_diff.moved_entities)}")
    print(f"Unchanged entities: {len(tree_diff.unchanged_entities)}")
    
    if tree_diff.added_entities:
        print(f"\\nAdded: {[shorten_uuid(eid) for eid in tree_diff.added_entities]}")
    if tree_diff.removed_entities:
        print(f"Removed: {[shorten_uuid(eid) for eid in tree_diff.removed_entities]}")
    if tree_diff.moved_entities:
        print(f"Moved: {[shorten_uuid(eid) for eid in tree_diff.moved_entities]}")
    
    print('='*60)

# Test Entity Definitions
class Person(Entity):
    name: str = ""
    age: int = 0
    email: str = ""
    active: bool = True

class Address(Entity):
    street: str = ""
    city: str = ""
    state: str = ""
    zipcode: str = ""

class Task(Entity):
    title: str = ""
    description: str = ""
    status: str = "pending"
    priority: int = 1
    completed: bool = False

class Project(Entity):
    name: str = ""
    description: str = ""
    status: str = "active"
    budget: float = 0.0
    tasks: List[Task] = Field(default_factory=list)

class PersonWithAddress(Entity):
    name: str = ""
    age: int = 0
    address: Optional[Address] = None

class Company(Entity):
    name: str = ""
    founded: int = 0
    employees: List[Person] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)

def analyze_diff_detailed(old_tree: EntityTree, new_tree: EntityTree) -> Dict[str, Any]:
    """Analyze diff with detailed debug information."""
    result = find_modified_entities(
        new_tree=new_tree,
        old_tree=old_tree,
        debug=True
    )
    
    # Handle the Union[Set[UUID], Tuple[Set[UUID], Dict[str, Any]]] return type
    if isinstance(result, tuple):
        modified_entities, debug_info = result
    else:
        # This shouldn't happen when debug=True, but handle gracefully
        modified_entities = result
        debug_info = {
            "comparison_count": 0,
            "added_entities": set(),
            "removed_entities": set(),
            "moved_entities": set(),
            "unchanged_entities": set()
        }
    
    return {
        "modified_entities": modified_entities,
        "debug_info": debug_info,
        "summary": {
            "total_changes": len(modified_entities),
            "added_count": len(debug_info["added_entities"]),
            "removed_count": len(debug_info["removed_entities"]),
            "moved_count": len(debug_info["moved_entities"]),
            "unchanged_count": len(debug_info["unchanged_entities"]),
            "comparisons": debug_info["comparison_count"]
        }
    }

def print_diff_analysis(scenario_name: str, diff_analysis: Dict[str, Any]) -> None:
    """Print detailed diff analysis."""
    print(f"\n{'='*60}")
    print(f"DIFF ANALYSIS: {scenario_name}")
    print('='*60)
    
    summary = diff_analysis["summary"]
    debug_info = diff_analysis["debug_info"]
    
    print(f"Total entities requiring versioning: {summary['total_changes']}")
    print(f"Added entities: {summary['added_count']}")
    print(f"Removed entities: {summary['removed_count']}")
    print(f"Moved entities: {summary['moved_count']}")
    print(f"Unchanged entities: {summary['unchanged_count']}")
    print(f"Attribute comparisons: {summary['comparisons']}")
    
    if debug_info["added_entities"]:
        print(f"\nAdded entities: {[str(e)[-8:] for e in debug_info['added_entities']]}")
    if debug_info["removed_entities"]:
        print(f"Removed entities: {[str(e)[-8:] for e in debug_info['removed_entities']]}")
    if debug_info["moved_entities"]:
        print(f"Moved entities: {[str(e)[-8:] for e in debug_info['moved_entities']]}")
    
    modified_entities = diff_analysis["modified_entities"]
    print(f"\nAll modified entities: {[str(e)[-8:] for e in modified_entities]}")

def scenario_1_simple_attribute_change():
    """Test 1: Simple attribute change - single field modification."""
    print("\n" + "="*60)
    print("SCENARIO 1: Simple Attribute Change")
    print("="*60)
    
    # Before: Person with age 30
    person_before = Person(name="Alice", age=30, email="alice@example.com")
    person_before.promote_to_root()
    
    # After: Person with age 31
    person_after = Person(name="Alice", age=31, email="alice@example.com")
    person_after.promote_to_root()
    
    # Build trees
    tree_before = build_entity_tree(person_before)
    tree_after = build_entity_tree(person_after)
    
    # Analyze diff
    diff_analysis = analyze_diff_detailed(tree_before, tree_after)
    print_diff_analysis("Simple Attribute Change", diff_analysis)
    
    # Create actual diff visualization
    tree_diff = analyze_tree_diff(tree_before, tree_after)
    print_diff_summary(tree_diff, "Simple Attribute Change")
    
    # Unified diff view
    print("\nUNIFIED DIFF:")
    mermaid_unified = tree_diff_to_mermaid_unified(tree_diff)
    
    # Skip validation for now - test if it works like the original
    print_mermaid_code(mermaid_unified, "Unified Diff - Person Age Change")
    quick_render(mermaid_unified, "Scenario 1 - Unified Diff")
    
    # Side-by-side diff view
    print("\nSIDE-BY-SIDE DIFF:")
    mermaid_sidebyside = tree_diff_to_mermaid_sidebyside(tree_diff)
    print_mermaid_code(mermaid_sidebyside, "Side-by-Side Diff - Person Age Change")
    quick_render(mermaid_sidebyside, "Scenario 1 - Side-by-Side Diff")
    
    return tree_before, tree_after, diff_analysis

def scenario_2_none_to_entity():
    """Test 2: None to entity - optional field gets populated."""
    print("\n" + "="*60)
    print("SCENARIO 2: None to Entity")
    print("="*60)
    
    # Before: Person with no address
    person_before = PersonWithAddress(name="Bob", age=25, address=None)
    person_before.promote_to_root()
    
    # After: Person with address
    person_after = PersonWithAddress(
        name="Bob", 
        age=25, 
        address=Address(street="123 Main St", city="Springfield", state="IL", zipcode="12345")
    )
    person_after.promote_to_root()
    
    # Build trees
    tree_before = build_entity_tree(person_before)
    tree_after = build_entity_tree(person_after)
    
    # Analyze diff
    diff_analysis = analyze_diff_detailed(tree_before, tree_after)
    print_diff_analysis("None to Entity", diff_analysis)
    
    # Create actual diff visualization
    tree_diff = analyze_tree_diff(tree_before, tree_after)
    print_diff_summary(tree_diff, "None to Entity")
    
    # Side-by-side diff view
    print("\nSIDE-BY-SIDE DIFF:")
    mermaid_sidebyside = tree_diff_to_mermaid_sidebyside(tree_diff)
    print_mermaid_code(mermaid_sidebyside, "Side-by-Side Diff - None to Entity")
    quick_render(mermaid_sidebyside, "Scenario 2 - Side-by-Side Diff")
    
    return tree_before, tree_after, diff_analysis

def scenario_3_entity_to_none():
    """Test 3: Entity to None - optional field gets cleared."""
    print("\n" + "="*60)
    print("SCENARIO 3: Entity to None")
    print("="*60)
    
    # Before: Person with address
    person_before = PersonWithAddress(
        name="Charlie", 
        age=35, 
        address=Address(street="456 Oak Ave", city="Boston", state="MA", zipcode="02101")
    )
    person_before.promote_to_root()
    
    # After: Person with no address
    person_after = PersonWithAddress(name="Charlie", age=35, address=None)
    person_after.promote_to_root()
    
    # Build trees
    tree_before = build_entity_tree(person_before)
    tree_after = build_entity_tree(person_after)
    
    # Analyze diff
    diff_analysis = analyze_diff_detailed(tree_before, tree_after)
    print_diff_analysis("Entity to None", diff_analysis)
    
    # Visualize before/after
    print("\nBEFORE:")
    mermaid_before = entity_tree_to_mermaid_graph(tree_before)
    print_mermaid_code(mermaid_before, "Before - With Address")
    quick_render(mermaid_before, "Scenario 3 - Before")
    
    print("\nAFTER:")
    mermaid_after = entity_tree_to_mermaid_graph(tree_after)
    print_mermaid_code(mermaid_after, "After - No Address")
    quick_render(mermaid_after, "Scenario 3 - After")
    
    return tree_before, tree_after, diff_analysis

def scenario_4_list_item_addition():
    """Test 4: List item addition - new entity added to list."""
    print("\n" + "="*60)
    print("SCENARIO 4: List Item Addition")
    print("="*60)
    
    # Before: Project with 2 tasks
    project_before = Project(
        name="Website Redesign",
        description="Modernize website",
        tasks=[
            Task(title="Design mockups", status="completed", priority=1),
            Task(title="Implement frontend", status="in_progress", priority=2)
        ]
    )
    project_before.promote_to_root()
    
    # After: Project with 3 tasks (added new task)
    project_after = Project(
        name="Website Redesign",
        description="Modernize website",
        tasks=[
            Task(title="Design mockups", status="completed", priority=1),
            Task(title="Implement frontend", status="in_progress", priority=2),
            Task(title="Backend integration", status="pending", priority=3)
        ]
    )
    project_after.promote_to_root()
    
    # Build trees
    tree_before = build_entity_tree(project_before)
    tree_after = build_entity_tree(project_after)
    
    # Analyze diff
    diff_analysis = analyze_diff_detailed(tree_before, tree_after)
    print_diff_analysis("List Item Addition", diff_analysis)
    
    # Visualize before/after
    print("\nBEFORE:")
    mermaid_before = entity_tree_to_mermaid_graph(tree_before)
    print_mermaid_code(mermaid_before, "Before - 2 Tasks")
    quick_render(mermaid_before, "Scenario 4 - Before")
    
    print("\nAFTER:")
    mermaid_after = entity_tree_to_mermaid_graph(tree_after)
    print_mermaid_code(mermaid_after, "After - 3 Tasks")
    quick_render(mermaid_after, "Scenario 4 - After")
    
    return tree_before, tree_after, diff_analysis

def scenario_5_list_item_removal():
    """Test 5: List item removal - entity removed from list."""
    print("\n" + "="*60)
    print("SCENARIO 5: List Item Removal")
    print("="*60)
    
    # Before: Project with 3 tasks
    project_before = Project(
        name="Mobile App",
        description="Create mobile app",
        tasks=[
            Task(title="UI Design", status="completed", priority=1),
            Task(title="Backend API", status="in_progress", priority=2),
            Task(title="Testing", status="pending", priority=3)
        ]
    )
    project_before.promote_to_root()
    
    # After: Project with 2 tasks (removed middle task)
    project_after = Project(
        name="Mobile App",
        description="Create mobile app",
        tasks=[
            Task(title="UI Design", status="completed", priority=1),
            Task(title="Testing", status="pending", priority=3)
        ]
    )
    project_after.promote_to_root()
    
    # Build trees
    tree_before = build_entity_tree(project_before)
    tree_after = build_entity_tree(project_after)
    
    # Analyze diff
    diff_analysis = analyze_diff_detailed(tree_before, tree_after)
    print_diff_analysis("List Item Removal", diff_analysis)
    
    # Visualize before/after
    print("\nBEFORE:")
    mermaid_before = entity_tree_to_mermaid_graph(tree_before)
    print_mermaid_code(mermaid_before, "Before - 3 Tasks")
    quick_render(mermaid_before, "Scenario 5 - Before")
    
    print("\nAFTER:")
    mermaid_after = entity_tree_to_mermaid_graph(tree_after)
    print_mermaid_code(mermaid_after, "After - 2 Tasks")
    quick_render(mermaid_after, "Scenario 5 - After")
    
    return tree_before, tree_after, diff_analysis

def scenario_6_list_reordering():
    """Test 6: List reordering - same entities, different order."""
    print("\n" + "="*60)
    print("SCENARIO 6: List Reordering")
    print("="*60)
    
    # Before: Tasks in original order
    project_before = Project(
        name="Data Migration",
        description="Migrate legacy data",
        tasks=[
            Task(title="Extract data", status="completed", priority=1),
            Task(title="Transform data", status="in_progress", priority=2),
            Task(title="Load data", status="pending", priority=3)
        ]
    )
    project_before.promote_to_root()
    
    # After: Tasks reordered (same tasks, different indices)
    project_after = Project(
        name="Data Migration",
        description="Migrate legacy data",
        tasks=[
            Task(title="Load data", status="pending", priority=3),
            Task(title="Extract data", status="completed", priority=1),
            Task(title="Transform data", status="in_progress", priority=2)
        ]
    )
    project_after.promote_to_root()
    
    # Build trees
    tree_before = build_entity_tree(project_before)
    tree_after = build_entity_tree(project_after)
    
    # Analyze diff
    diff_analysis = analyze_diff_detailed(tree_before, tree_after)
    print_diff_analysis("List Reordering", diff_analysis)
    
    # Visualize before/after
    print("\nBEFORE:")
    mermaid_before = entity_tree_to_mermaid_graph(tree_before)
    print_mermaid_code(mermaid_before, "Before - Original Order")
    quick_render(mermaid_before, "Scenario 6 - Before")
    
    print("\nAFTER:")
    mermaid_after = entity_tree_to_mermaid_graph(tree_after)
    print_mermaid_code(mermaid_after, "After - Reordered")
    quick_render(mermaid_after, "Scenario 6 - After")
    
    return tree_before, tree_after, diff_analysis

def scenario_7_deep_hierarchy_addition():
    """Test 7: Deep hierarchy addition - multi-level new structure."""
    print("\n" + "="*60)
    print("SCENARIO 7: Deep Hierarchy Addition")
    print("="*60)
    
    # Before: Company with no projects
    company_before = Company(
        name="Tech Solutions Inc",
        founded=2020,
        employees=[
            Person(name="John Manager", age=35, email="john@tech.com"),
            Person(name="Jane Developer", age=28, email="jane@tech.com")
        ],
        projects=[]
    )
    company_before.promote_to_root()
    
    # After: Company with project containing multiple tasks
    company_after = Company(
        name="Tech Solutions Inc",
        founded=2020,
        employees=[
            Person(name="John Manager", age=35, email="john@tech.com"),
            Person(name="Jane Developer", age=28, email="jane@tech.com")
        ],
        projects=[
            Project(
                name="AI Platform",
                description="Build AI platform",
                budget=500000.0,
                tasks=[
                    Task(title="Research phase", status="completed", priority=1),
                    Task(title="Prototype development", status="in_progress", priority=2),
                    Task(title="Production deployment", status="pending", priority=3)
                ]
            )
        ]
    )
    company_after.promote_to_root()
    
    # Build trees
    tree_before = build_entity_tree(company_before)
    tree_after = build_entity_tree(company_after)
    
    # Analyze diff
    diff_analysis = analyze_diff_detailed(tree_before, tree_after)
    print_diff_analysis("Deep Hierarchy Addition", diff_analysis)
    
    # Visualize before/after
    print("\nBEFORE:")
    mermaid_before = entity_tree_to_mermaid_graph(tree_before)
    print_mermaid_code(mermaid_before, "Before - No Projects")
    quick_render(mermaid_before, "Scenario 7 - Before")
    
    print("\nAFTER:")
    mermaid_after = entity_tree_to_mermaid_graph(tree_after)
    print_mermaid_code(mermaid_after, "After - With AI Platform Project")
    quick_render(mermaid_after, "Scenario 7 - After")
    
    return tree_before, tree_after, diff_analysis

def scenario_8_complex_mixed_changes():
    """Test 8: Complex mixed changes - multiple change types at once."""
    print("\n" + "="*60)
    print("SCENARIO 8: Complex Mixed Changes")
    print("="*60)
    
    # Before: Company with basic structure
    company_before = Company(
        name="StartupCorp",
        founded=2023,
        employees=[
            Person(name="Alice CEO", age=30, email="alice@startup.com"),
            Person(name="Bob CTO", age=32, email="bob@startup.com")
        ],
        projects=[
            Project(
                name="MVP",
                description="Minimum viable product",
                budget=100000.0,
                tasks=[
                    Task(title="Market research", status="completed", priority=1),
                    Task(title="Product design", status="in_progress", priority=2)
                ]
            )
        ]
    )
    company_before.promote_to_root()
    
    # After: Multiple changes
    # - Company name changed
    # - Employee added
    # - Employee modified (age)
    # - Project budget changed
    # - Task status changed
    # - New task added
    company_after = Company(
        name="StartupCorp Ltd",  # Changed name
        founded=2023,
        employees=[
            Person(name="Alice CEO", age=31, email="alice@startup.com"),  # Changed age
            Person(name="Bob CTO", age=32, email="bob@startup.com"),
            Person(name="Charlie Designer", age=27, email="charlie@startup.com")  # Added employee
        ],
        projects=[
            Project(
                name="MVP",
                description="Minimum viable product",
                budget=150000.0,  # Changed budget
                tasks=[
                    Task(title="Market research", status="completed", priority=1),
                    Task(title="Product design", status="completed", priority=2),  # Changed status
                    Task(title="Development", status="in_progress", priority=3)  # Added task
                ]
            )
        ]
    )
    company_after.promote_to_root()
    
    # Build trees
    tree_before = build_entity_tree(company_before)
    tree_after = build_entity_tree(company_after)
    
    # Analyze diff
    diff_analysis = analyze_diff_detailed(tree_before, tree_after)
    print_diff_analysis("Complex Mixed Changes", diff_analysis)
    
    # Visualize before/after
    print("\nBEFORE:")
    mermaid_before = entity_tree_to_mermaid_graph(tree_before)
    print_mermaid_code(mermaid_before, "Before - StartupCorp")
    quick_render(mermaid_before, "Scenario 8 - Before")
    
    print("\nAFTER:")
    mermaid_after = entity_tree_to_mermaid_graph(tree_after)
    print_mermaid_code(mermaid_after, "After - StartupCorp Ltd")
    quick_render(mermaid_after, "Scenario 8 - After")
    
    return tree_before, tree_after, diff_analysis

def run_all_scenarios():
    """Run all test scenarios and collect results."""
    print("COMPREHENSIVE DIFF TESTING")
    print("="*60)
    
    scenarios = [
        ("Simple Attribute Change", scenario_1_simple_attribute_change),
        ("None to Entity", scenario_2_none_to_entity),
        ("Entity to None", scenario_3_entity_to_none),
        ("List Item Addition", scenario_4_list_item_addition),
        ("List Item Removal", scenario_5_list_item_removal),
        ("List Reordering", scenario_6_list_reordering),
        ("Deep Hierarchy Addition", scenario_7_deep_hierarchy_addition),
        ("Complex Mixed Changes", scenario_8_complex_mixed_changes)
    ]
    
    results = []
    for name, scenario_func in scenarios:
        try:
            print(f"\n{'='*60}")
            print(f"RUNNING: {name}")
            print('='*60)
            
            tree_before, tree_after, diff_analysis = scenario_func()
            results.append((name, tree_before, tree_after, diff_analysis))
            
            print(f"[SUCCESS] {name} completed")
            
        except Exception as e:
            print(f"[ERROR] {name} failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY OF ALL SCENARIOS")
    print("="*60)
    
    for name, tree_before, tree_after, diff_analysis in results:
        summary = diff_analysis["summary"]
        print(f"\n{name}:")
        print(f"  - Total changes: {summary['total_changes']}")
        print(f"  - Added: {summary['added_count']}, Removed: {summary['removed_count']}")
        print(f"  - Moved: {summary['moved_count']}, Unchanged: {summary['unchanged_count']}")
        print(f"  - Before: {len(tree_before.nodes)} nodes, After: {len(tree_after.nodes)} nodes")
    
    return results

if __name__ == "__main__":
    results = run_all_scenarios()
    
    print(f"\n[COMPLETED] Tested {len(results)} diff scenarios")
    print("All visualizations have been generated and opened in browser")