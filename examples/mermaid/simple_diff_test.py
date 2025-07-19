#!/usr/bin/env python3
"""
Simple working diff visualization test.
Just shows the basic concept without overthinking it.
"""

import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from abstractions.ecs.entity import Entity, build_entity_tree
from entity_graph_visualization import entity_tree_to_mermaid_graph
from utils.mermaid_renderer import quick_render, print_mermaid_code
from pydantic import Field
from typing import Optional

# Simple test entities
class Person(Entity):
    name: str = Field(default="")
    age: int = Field(default=0)

class Address(Entity):
    street: str = Field(default="")
    city: str = Field(default="")

class PersonWithAddress(Entity):
    name: str = Field(default="")
    age: int = Field(default=0)
    address: Optional[Address] = Field(default=None)

def create_sidebyside_visualization(tree_before, tree_after):
    """Create side-by-side visualization using exact same style as individual trees."""
    from entity_graph_visualization import create_node_id, create_node_label, create_edge_label
    
    lines = ["graph TD"]
    
    # Add all nodes first - before nodes (left side)
    for entity_id, entity in tree_before.nodes.items():
        node_id = f"L_{create_node_id(entity)}"
        node_label = f"BEFORE: {create_node_label(entity, include_attributes=True)}"
        lines.append(f"    {node_id}[\"{node_label}\"]")
    
    # Add all nodes - after nodes (right side)  
    for entity_id, entity in tree_after.nodes.items():
        node_id = f"R_{create_node_id(entity)}"
        node_label = f"AFTER: {create_node_label(entity, include_attributes=True)}"
        lines.append(f"    {node_id}[\"{node_label}\"]")
    
    lines.append("")
    
    # Add before tree edges (hierarchical)
    for (source_id, target_id), edge in tree_before.edges.items():
        source_entity = tree_before.get_entity(source_id)
        target_entity = tree_before.get_entity(target_id)
        
        if source_entity and target_entity:
            source_node = f"L_{create_node_id(source_entity)}"
            target_node = f"L_{create_node_id(target_entity)}"
            edge_label = create_edge_label(edge)
            lines.append(f"    {source_node} -->|\"{edge_label}\"| {target_node}")
    
    # Add after tree edges (hierarchical)
    for (source_id, target_id), edge in tree_after.edges.items():
        source_entity = tree_after.get_entity(source_id)
        target_entity = tree_after.get_entity(target_id)
        
        if source_entity and target_entity:
            source_node = f"R_{create_node_id(source_entity)}"
            target_node = f"R_{create_node_id(target_entity)}"
            edge_label = create_edge_label(edge)
            lines.append(f"    {source_node} -->|\"{edge_label}\"| {target_node}")
    
    # Force horizontal layout with invisible edge between roots
    before_root = tree_before.get_entity(tree_before.root_ecs_id)
    after_root = tree_after.get_entity(tree_after.root_ecs_id)
    if before_root and after_root:
        before_root_node = f"L_{create_node_id(before_root)}"
        after_root_node = f"R_{create_node_id(after_root)}"
        lines.append(f"    {before_root_node} -.-> {after_root_node}")
    
    lines.append("")
    
    # Add exact same styling as individual trees
    lines.append("    %% Node styling")
    
    # Style root nodes
    before_root = tree_before.get_entity(tree_before.root_ecs_id)
    after_root = tree_after.get_entity(tree_after.root_ecs_id)
    
    lines.append("    classDef rootNode fill:#f3e5f5,stroke:#4a148c,stroke-width:3px")
    if before_root:
        lines.append(f"    class L_{create_node_id(before_root)} rootNode")
    if after_root:
        lines.append(f"    class R_{create_node_id(after_root)} rootNode")
    
    # Style by entity type (same colors as original)
    colors = [
        "fill:#e1f5fe,stroke:#01579b",  # Light blue
        "fill:#e8f5e8,stroke:#388e3c",  # Light green
        "fill:#fff3e0,stroke:#f57c00",  # Light orange
        "fill:#fce4ec,stroke:#c2185b",  # Light pink
        "fill:#f3e5f5,stroke:#7b1fa2",  # Light purple
        "fill:#e0f2f1,stroke:#00695c",  # Light teal
    ]
    
    # Collect entity types from both trees
    entity_types = {}
    for entity in list(tree_before.nodes.values()) + list(tree_after.nodes.values()):
        entity_type = entity.__class__.__name__
        if entity_type not in entity_types:
            entity_types[entity_type] = []
    
    # Apply type styling
    for i, entity_type in enumerate(entity_types.keys()):
        if entity_type != before_root.__class__.__name__ and entity_type != after_root.__class__.__name__:
            color = colors[i % len(colors)]
            class_name = f"type_{entity_type}"
            lines.append(f"    classDef {class_name} {color},stroke-width:2px")
            
            # Apply to before tree
            for entity in tree_before.nodes.values():
                if entity.__class__.__name__ == entity_type and entity != before_root:
                    lines.append(f"    class L_{create_node_id(entity)} {class_name}")
            
            # Apply to after tree
            for entity in tree_after.nodes.values():
                if entity.__class__.__name__ == entity_type and entity != after_root:
                    lines.append(f"    class R_{create_node_id(entity)} {class_name}")
    
    return "\n".join(lines)

def test_simple_diff():
    """Test a simple None-to-Entity diff scenario."""
    print("=== SIMPLE DIFF TEST ===")
    
    # Before: Person with no address
    person_before = PersonWithAddress(name="Bob", age=25, address=None)
    person_before.promote_to_root()
    
    # After: Person with address
    person_after = PersonWithAddress(
        name="Bob", 
        age=25, 
        address=Address(street="123 Main St", city="Springfield")
    )
    person_after.promote_to_root()
    
    # Build trees
    tree_before = build_entity_tree(person_before)
    tree_after = build_entity_tree(person_after)
    
    # Generate basic visualizations
    print("\n--- BEFORE ---")
    mermaid_before = entity_tree_to_mermaid_graph(tree_before)
    print_mermaid_code(mermaid_before, "Before: No Address")
    quick_render(mermaid_before, "Before State")
    
    print("\n--- AFTER ---")
    mermaid_after = entity_tree_to_mermaid_graph(tree_after)
    print_mermaid_code(mermaid_after, "After: With Address")
    quick_render(mermaid_after, "After State")
    
    print("\n--- SIDE-BY-SIDE ---")
    mermaid_sidebyside = create_sidebyside_visualization(tree_before, tree_after)
    print_mermaid_code(mermaid_sidebyside, "Side-by-Side Comparison")
    quick_render(mermaid_sidebyside, "Side-by-Side Diff")
    
    print("\n--- SUMMARY ---")
    print(f"Before: {len(tree_before.nodes)} nodes, {len(tree_before.edges)} edges")
    print(f"After: {len(tree_after.nodes)} nodes, {len(tree_after.edges)} edges")
    print(f"Change: Added {len(tree_after.nodes) - len(tree_before.nodes)} nodes")
    
    print("\nDiff visualization completed successfully!")
    print("Three browser windows opened: before, after, and side-by-side.")

if __name__ == "__main__":
    test_simple_diff()