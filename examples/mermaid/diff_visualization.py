"""
Graph Diff Visualization

Implementation of diff visualization functions that show changes between entity graphs.
Creates unified mermaid diagrams highlighting additions, removals, and modifications.
"""

import sys
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple, Any, Union
from uuid import UUID
from dataclasses import dataclass
from enum import Enum

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from abstractions.ecs.entity import Entity, EntityTree, EntityEdge, EdgeType, build_entity_tree, find_modified_entities
from entity_graph_visualization import (
    shorten_uuid, get_entity_display_name, get_entity_key_attributes, 
    create_node_id, create_edge_label
)

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
    old_tree: Optional[EntityTree]
    new_tree: Optional[EntityTree]

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
    """
    Convert find_modified_entities output into rich diff structure.
    """
    # Get the diff analysis
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
                new_entity=entity,
                old_tree=old_tree,
                new_tree=new_tree
            )
    
    # Removed entities
    for entity_id in removed_entities:
        entity = old_tree.get_entity(entity_id)
        if entity:
            entity_diffs[entity_id] = EntityDiff(
                entity_id=entity_id,
                change_type=ChangeType.REMOVED,
                old_entity=entity,
                new_entity=None,
                old_tree=old_tree,
                new_tree=new_tree
            )
    
    # Moved entities
    for entity_id in moved_entities:
        old_entity = old_tree.get_entity(entity_id)
        new_entity = new_tree.get_entity(entity_id)
        entity_diffs[entity_id] = EntityDiff(
            entity_id=entity_id,
            change_type=ChangeType.MOVED,
            old_entity=old_entity,
            new_entity=new_entity,
            old_tree=old_tree,
            new_tree=new_tree
        )
    
    # Unchanged entities
    for entity_id in unchanged_entities:
        entity = new_tree.get_entity(entity_id) or old_tree.get_entity(entity_id)
        if entity:
            entity_diffs[entity_id] = EntityDiff(
                entity_id=entity_id,
                change_type=ChangeType.UNCHANGED,
                old_entity=old_tree.get_entity(entity_id),
                new_entity=new_tree.get_entity(entity_id),
                old_tree=old_tree,
                new_tree=new_tree
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
    if entity_diff.change_type == ChangeType.ADDED:
        entity = entity_diff.new_entity
        class_name = entity.__class__.__name__
        attrs = get_entity_key_attributes(entity)
        label_parts = [f"+ {class_name}"]
        if attrs:
            label_parts.extend(attrs)
        return "\\n".join(label_parts)
    
    elif entity_diff.change_type == ChangeType.REMOVED:
        entity = entity_diff.old_entity
        class_name = entity.__class__.__name__
        attrs = get_entity_key_attributes(entity)
        label_parts = [f"- {class_name}"]
        if attrs:
            label_parts.extend(attrs)
        return "\\n".join(label_parts)
    
    elif entity_diff.change_type == ChangeType.MOVED:
        entity = entity_diff.new_entity
        class_name = entity.__class__.__name__
        attrs = get_entity_key_attributes(entity)
        label_parts = [f"→ {class_name}"]
        if attrs:
            label_parts.extend(attrs)
        return "\\n".join(label_parts)
    
    else:  # UNCHANGED
        entity = entity_diff.new_entity or entity_diff.old_entity
        class_name = entity.__class__.__name__
        attrs = get_entity_key_attributes(entity)
        label_parts = [class_name]
        if attrs:
            label_parts.extend(attrs)
        return "\\n".join(label_parts)

def tree_diff_to_mermaid_unified(tree_diff: TreeDiff) -> str:
    """
    Generate unified diff view showing all changes in one graph.
    """
    lines = ["graph TD"]
    
    # Color scheme for change types
    CHANGE_COLORS = {
        ChangeType.ADDED: {
            "fill": "#e8f5e8",
            "stroke": "#388e3c",
            "description": "Light green for additions"
        },
        ChangeType.REMOVED: {
            "fill": "#ffcdd2", 
            "stroke": "#d32f2f",
            "description": "Light red for removals"
        },
        ChangeType.MODIFIED: {
            "fill": "#fff3e0",
            "stroke": "#f57c00", 
            "description": "Light orange for modifications"
        },
        ChangeType.MOVED: {
            "fill": "#e3f2fd",
            "stroke": "#1976d2",
            "description": "Light blue for moved entities"
        },
        ChangeType.UNCHANGED: {
            "fill": "#f5f5f5",
            "stroke": "#9e9e9e",
            "description": "Light gray for unchanged entities"
        }
    }
    
    # Create nodes for all entities in the diff
    nodes_created = set()
    
    for entity_id, entity_diff in tree_diff.entity_diffs.items():
        if entity_diff.change_type == ChangeType.REMOVED:
            # Skip removed entities in unified view
            continue
            
        entity = entity_diff.new_entity or entity_diff.old_entity
        if entity:
            node_id = create_node_id(entity)
            node_label = create_diff_node_label(entity_diff)
            
            # Choose node shape based on change type
            if entity_diff.change_type == ChangeType.ADDED:
                shape = f"[{node_label}]"  # Rectangle for added
            elif entity_diff.change_type == ChangeType.MOVED:
                shape = f">{node_label}]"  # Asymmetric for moved
            else:
                shape = f"[{node_label}]"  # Standard rectangle
            
            lines.append(f"    {node_id}{shape}")
            nodes_created.add(node_id)
    
    # Create edges from the new tree (showing current state)
    for (source_id, target_id), edge in tree_diff.new_tree.edges.items():
        source_entity = tree_diff.new_tree.get_entity(source_id)
        target_entity = tree_diff.new_tree.get_entity(target_id)
        
        if source_entity and target_entity:
            source_node = create_node_id(source_entity)
            target_node = create_node_id(target_entity)
            
            if source_node in nodes_created and target_node in nodes_created:
                edge_label = create_edge_label(edge)
                lines.append(f"    {source_node} -->|\"{edge_label}\"| {target_node}")
    
    # Add styling
    lines.append("")
    lines.append("    %% Change type styling")
    
    # Group entities by change type and apply colors
    change_type_groups = {}
    for entity_id, entity_diff in tree_diff.entity_diffs.items():
        if entity_diff.change_type == ChangeType.REMOVED:
            continue
            
        change_type = entity_diff.change_type
        if change_type not in change_type_groups:
            change_type_groups[change_type] = []
        
        entity = entity_diff.new_entity or entity_diff.old_entity
        if entity:
            change_type_groups[change_type].append(create_node_id(entity))
    
    # Apply styling for each change type
    for change_type, node_ids in change_type_groups.items():
        if node_ids:
            colors = CHANGE_COLORS[change_type]
            class_name = f"change_{change_type.value}"
            lines.append(f"    classDef {class_name} fill:{colors['fill']},stroke:{colors['stroke']},stroke-width:3px")
            
            for node_id in node_ids:
                lines.append(f"    class {node_id} {class_name}")
    
    return "\n".join(lines)

def tree_diff_to_mermaid_sidebyside(tree_diff: TreeDiff) -> str:
    """
    Generate side-by-side comparison view showing before and after.
    """
    lines = ["graph LR"]
    
    # Create subgraphs for before and after
    lines.append("    subgraph \"Before (Old)\"")
    
    # Add old tree nodes
    for entity_id, entity in tree_diff.old_tree.nodes.items():
        node_id = f"old_{create_node_id(entity)}"
        entity_diff = tree_diff.entity_diffs.get(entity_id)
        
        if entity_diff and entity_diff.change_type == ChangeType.REMOVED:
            label = f"- {entity.__class__.__name__}"
        else:
            label = entity.__class__.__name__
            
        attrs = get_entity_key_attributes(entity)
        if attrs:
            label += "\\n" + "\\n".join(attrs)
            
        lines.append(f"        {node_id}[\"{label}\"]")
    
    # Add old tree edges
    for (source_id, target_id), edge in tree_diff.old_tree.edges.items():
        source_entity = tree_diff.old_tree.get_entity(source_id)
        target_entity = tree_diff.old_tree.get_entity(target_id)
        
        if source_entity and target_entity:
            source_node = f"old_{create_node_id(source_entity)}"
            target_node = f"old_{create_node_id(target_entity)}"
            edge_label = create_edge_label(edge)
            lines.append(f"        {source_node} -->|\"{edge_label}\"| {target_node}")
    
    lines.append("    end")
    lines.append("")
    lines.append("    subgraph \"After (New)\"")
    
    # Add new tree nodes
    for entity_id, entity in tree_diff.new_tree.nodes.items():
        node_id = f"new_{create_node_id(entity)}"
        entity_diff = tree_diff.entity_diffs.get(entity_id)
        
        if entity_diff and entity_diff.change_type == ChangeType.ADDED:
            label = f"+ {entity.__class__.__name__}"
        else:
            label = entity.__class__.__name__
            
        attrs = get_entity_key_attributes(entity)
        if attrs:
            label += "\\n" + "\\n".join(attrs)
            
        lines.append(f"        {node_id}[\"{label}\"]")
    
    # Add new tree edges
    for (source_id, target_id), edge in tree_diff.new_tree.edges.items():
        source_entity = tree_diff.new_tree.get_entity(source_id)
        target_entity = tree_diff.new_tree.get_entity(target_id)
        
        if source_entity and target_entity:
            source_node = f"new_{create_node_id(source_entity)}"
            target_node = f"new_{create_node_id(target_entity)}"
            edge_label = create_edge_label(edge)
            lines.append(f"        {source_node} -->|\"{edge_label}\"| {target_node}")
    
    lines.append("    end")
    lines.append("")
    
    # Add cross-links showing relationships between old and new
    lines.append("    %% Change relationships")
    for entity_id, entity_diff in tree_diff.entity_diffs.items():
        if entity_diff.change_type == ChangeType.MOVED and entity_diff.old_entity and entity_diff.new_entity:
            old_node = f"old_{create_node_id(entity_diff.old_entity)}"
            new_node = f"new_{create_node_id(entity_diff.new_entity)}"
            lines.append(f"    {old_node} -.->|\"moved\"| {new_node}")
    
    # Add styling
    lines.append("")
    lines.append("    %% Styling")
    lines.append("    classDef removed fill:#ffcdd2,stroke:#d32f2f,stroke-width:2px")
    lines.append("    classDef added fill:#e8f5e8,stroke:#388e3c,stroke-width:2px")
    
    return "\n".join(lines)

def tree_diff_to_mermaid_changes_only(tree_diff: TreeDiff) -> str:
    """
    Generate view showing only changed elements.
    """
    lines = ["graph TD"]
    
    # Only show entities that changed
    changed_entities = (
        tree_diff.added_entities | 
        tree_diff.removed_entities | 
        tree_diff.moved_entities
    )
    
    if not changed_entities:
        lines.append("    NoChanges[\"No Changes Detected\"]")
        return "\n".join(lines)
    
    # Create nodes for changed entities only
    for entity_id in changed_entities:
        entity_diff = tree_diff.entity_diffs.get(entity_id)
        if entity_diff:
            entity = entity_diff.new_entity or entity_diff.old_entity
            if entity:
                node_id = create_node_id(entity)
                node_label = create_diff_node_label(entity_diff)
                lines.append(f"    {node_id}[\"{node_label}\"]")
    
    # Show edges between changed entities
    for (source_id, target_id), edge in tree_diff.new_tree.edges.items():
        if source_id in changed_entities or target_id in changed_entities:
            source_entity = tree_diff.new_tree.get_entity(source_id)
            target_entity = tree_diff.new_tree.get_entity(target_id)
            
            if source_entity and target_entity:
                source_node = create_node_id(source_entity)
                target_node = create_node_id(target_entity)
                edge_label = create_edge_label(edge)
                lines.append(f"    {source_node} -->|\"{edge_label}\"| {target_node}")
    
    return "\n".join(lines)

def print_diff_summary(tree_diff: TreeDiff, title: str = "Diff Summary") -> None:
    """Print a summary of changes in the diff."""
    print(f"\n{'='*60}")
    print(f"[DIFF] {title}")
    print('='*60)
    
    print(f"Added entities: {len(tree_diff.added_entities)}")
    print(f"Removed entities: {len(tree_diff.removed_entities)}")
    print(f"Moved entities: {len(tree_diff.moved_entities)}")
    print(f"Unchanged entities: {len(tree_diff.unchanged_entities)}")
    
    if tree_diff.added_entities:
        print(f"\nAdded: {[shorten_uuid(eid) for eid in tree_diff.added_entities]}")
    if tree_diff.removed_entities:
        print(f"Removed: {[shorten_uuid(eid) for eid in tree_diff.removed_entities]}")
    if tree_diff.moved_entities:
        print(f"Moved: {[shorten_uuid(eid) for eid in tree_diff.moved_entities]}")
    
    print('='*60)