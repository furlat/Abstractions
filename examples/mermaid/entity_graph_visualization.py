"""
Fresh Entity Graph Visualization

Pure functional approach to generating mermaid diagrams from entity graphs.
Creates clean, properly formatted mermaid syntax with no loops.
"""

from typing import Dict, List, Set, Optional, Tuple, Any
from uuid import UUID
import sys
from pathlib import Path

# Add the project root to the path so we can import abstractions
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from abstractions.ecs.entity import Entity, EntityTree, EntityEdge, EdgeType, build_entity_tree

def shorten_uuid(uuid_val: UUID) -> str:
    """Get last 8 characters of UUID for display."""
    return str(uuid_val)[-8:]

def get_entity_display_name(entity: Entity) -> str:
    """Get a human-readable name for an entity."""
    # Try common name fields first
    for attr in ['name', 'title', 'label']:
        if hasattr(entity, attr):
            value = getattr(entity, attr)
            if value:
                return str(value)
    
    # Fall back to class name
    return entity.__class__.__name__

def get_entity_key_attributes(entity: Entity) -> List[str]:
    """Get key attributes to display in entity node."""
    attrs = []
    
    # Add name if it exists
    display_name = get_entity_display_name(entity)
    if display_name != entity.__class__.__name__:
        attrs.append(f"name: {display_name}")
    
    # Add other interesting attributes
    for attr in ['gpa', 'score', 'status', 'level', 'action']:
        if hasattr(entity, attr):
            value = getattr(entity, attr)
            if value is not None and value != "":
                attrs.append(f"{attr}: {value}")
    
    return attrs

def create_node_id(entity: Entity) -> str:
    """Create a clean node ID for mermaid."""
    return f"entity_{shorten_uuid(entity.ecs_id)}"

def create_node_label(entity: Entity, include_attributes: bool = True) -> str:
    """Create a node label for mermaid."""
    class_name = entity.__class__.__name__
    short_id = shorten_uuid(entity.ecs_id)
    
    if not include_attributes:
        return f"{class_name}\\n{short_id}"
    
    # Get key attributes
    attrs = get_entity_key_attributes(entity)
    
    # Build label
    label_parts = [class_name]
    if attrs:
        label_parts.extend(attrs)
    
    return "\\n".join(label_parts)

def create_edge_label(edge: EntityEdge) -> str:
    """Create an edge label showing the relationship."""
    label = edge.field_name
    
    # Add container information
    if edge.container_index is not None:
        label += f"[{edge.container_index}]"
    elif edge.container_key is not None:
        label += f"[{edge.container_key}]"
    
    return label

def entity_to_mermaid_graph(entity: Entity, 
                           include_attributes: bool = True,
                           max_depth: int = 10) -> str:
    """
    Convert an entity to a mermaid graph diagram.
    
    Args:
        entity: The root entity to visualize
        include_attributes: Whether to include entity attributes in nodes
        max_depth: Maximum depth to traverse
        
    Returns:
        Mermaid diagram as string
    """
    # Build the entity tree
    tree = build_entity_tree(entity)
    
    return entity_tree_to_mermaid_graph(tree, include_attributes)

def entity_tree_to_mermaid_graph(tree: EntityTree,
                                include_attributes: bool = True) -> str:
    """
    Convert an EntityTree to a mermaid graph diagram.
    
    Args:
        tree: The entity tree to visualize
        include_attributes: Whether to include entity attributes in nodes
        
    Returns:
        Mermaid diagram as string
    """
    if not tree.nodes:
        return "graph TD\n    Empty[Empty Tree]"
    
    lines = ["graph TD"]
    
    # Create nodes
    for entity_id, entity in tree.nodes.items():
        node_id = create_node_id(entity)
        node_label = create_node_label(entity, include_attributes)
        lines.append(f"    {node_id}[\"{node_label}\"]")
    
    # Create edges
    for (source_id, target_id), edge in tree.edges.items():
        source_node = create_node_id(tree.nodes[source_id])
        target_node = create_node_id(tree.nodes[target_id])
        edge_label = create_edge_label(edge)
        
        # Use different arrow styles for different edge types
        if edge.is_hierarchical:
            arrow = "-->"
        else:
            arrow = "-.->"  # Dashed for non-hierarchical
        
        lines.append(f"    {source_node} {arrow}|\"{edge_label}\"| {target_node}")
    
    # Add styling
    lines.append("")
    lines.append("    %% Node styling")
    
    # Style root node
    root_node = create_node_id(tree.nodes[tree.root_ecs_id])
    lines.append(f"    classDef rootNode fill:#f3e5f5,stroke:#4a148c,stroke-width:3px")
    lines.append(f"    class {root_node} rootNode")
    
    # Style by entity type
    entity_types = {}
    for entity in tree.nodes.values():
        entity_type = entity.__class__.__name__
        if entity_type not in entity_types:
            entity_types[entity_type] = []
        entity_types[entity_type].append(create_node_id(entity))
    
    # Color palette for different entity types
    colors = [
        "fill:#e1f5fe,stroke:#01579b",  # Light blue
        "fill:#e8f5e8,stroke:#388e3c",  # Light green
        "fill:#fff3e0,stroke:#f57c00",  # Light orange
        "fill:#fce4ec,stroke:#c2185b",  # Light pink
        "fill:#f3e5f5,stroke:#7b1fa2",  # Light purple
        "fill:#e0f2f1,stroke:#00695c",  # Light teal
    ]
    
    for i, (entity_type, nodes) in enumerate(entity_types.items()):
        if entity_type != tree.nodes[tree.root_ecs_id].__class__.__name__:  # Skip root, already styled
            color = colors[i % len(colors)]
            class_name = f"type_{entity_type}"
            lines.append(f"    classDef {class_name} {color},stroke-width:2px")
            
            for node in nodes:
                if node != root_node:  # Don't override root styling
                    lines.append(f"    class {node} {class_name}")
    
    return "\n".join(lines)

def entity_tree_to_simple_mermaid(tree: EntityTree) -> str:
    """
    Create a simple mermaid diagram without attributes.
    
    Args:
        tree: The entity tree to visualize
        
    Returns:
        Simple mermaid diagram as string
    """
    if not tree.nodes:
        return "graph TD\n    Empty[Empty Tree]"
    
    lines = ["graph TD"]
    
    # Create simple nodes
    for entity_id, entity in tree.nodes.items():
        node_id = create_node_id(entity)
        class_name = entity.__class__.__name__
        short_id = shorten_uuid(entity.ecs_id)
        display_name = get_entity_display_name(entity)
        
        if display_name != class_name:
            label = f"{class_name}\\n{display_name}"
        else:
            label = f"{class_name}\\n{short_id}"
        
        lines.append(f"    {node_id}[\"{label}\"]")
    
    # Create edges
    for (source_id, target_id), edge in tree.edges.items():
        source_node = create_node_id(tree.nodes[source_id])
        target_node = create_node_id(tree.nodes[target_id])
        edge_label = create_edge_label(edge)
        
        lines.append(f"    {source_node} --> {target_node}")
    
    return "\n".join(lines)

def analyze_entity_tree_structure(tree: EntityTree) -> Dict[str, Any]:
    """
    Analyze the structure of an entity tree for debugging.
    
    Args:
        tree: The entity tree to analyze
        
    Returns:
        Dictionary with analysis results
    """
    analysis = {
        'node_count': len(tree.nodes),
        'edge_count': len(tree.edges),
        'max_depth': tree.max_depth,
        'entity_types': {},
        'edge_types': {},
        'hierarchical_edges': 0,
        'ancestry_paths': {}
    }
    
    # Count entity types
    for entity in tree.nodes.values():
        entity_type = entity.__class__.__name__
        analysis['entity_types'][entity_type] = analysis['entity_types'].get(entity_type, 0) + 1
    
    # Count edge types
    for edge in tree.edges.values():
        edge_type = edge.edge_type
        analysis['edge_types'][edge_type] = analysis['edge_types'].get(edge_type, 0) + 1
        
        if edge.is_hierarchical:
            analysis['hierarchical_edges'] += 1
    
    # Analyze ancestry paths
    for entity_id, path in tree.ancestry_paths.items():
        entity = tree.get_entity(entity_id)
        if entity:
            entity_name = get_entity_display_name(entity)
            analysis['ancestry_paths'][entity_name] = len(path)
    
    return analysis

# Test functions
def test_entity_visualization():
    """Test entity visualization with sample data."""
    print("🧪 Testing entity visualization...")
    
    # Create sample entities
    class Student(Entity):
        name: str = ""
        gpa: float = 0.0
    
    class Course(Entity):
        name: str = ""
        credits: int = 0
    
    class StudentWithCourse(Entity):
        name: str = ""
        gpa: float = 0.0
        course: Course = Field(default_factory=lambda: Course())
    
    # Create entity hierarchy
    course = Course(name="Computer Science", credits=4)
    student = StudentWithCourse(name="Alice", gpa=3.8, course=course)
    student.promote_to_root()
    
    # Test visualization
    mermaid_code = entity_to_mermaid_graph(student)
    print("Generated mermaid code:")
    print(mermaid_code)
    
    return mermaid_code

if __name__ == "__main__":
    test_entity_visualization()