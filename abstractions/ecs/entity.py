""" Implementing step by step the entity system from
source docs:  /Users/tommasofurlanello/Documents/Dev/Abstractions/abstractions/ecs/graph_entity.md"""

from pydantic import BaseModel, Field, model_validator

from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Optional, List, Dict, Tuple, Set, Self
from collections import defaultdict

from pydantic import BaseModel, Field, model_validator
from typing import Dict, List, Set, Tuple, Any, Optional, Type, Union, get_type_hints, get_origin, get_args
from uuid import UUID, uuid4
from enum import Enum
from collections import deque
import inspect

# Edge type enum
class EdgeType(str, Enum):
    """Type of edge between entities"""
    DIRECT = "direct"         # Direct field reference
    LIST = "list"             # Entity in a list
    DICT = "dict"             # Entity in a dictionary
    SET = "set"               # Entity in a set
    TUPLE = "tuple"           # Entity in a tuple
    HIERARCHICAL = "hierarchical"  # Main ownership path
    REFERENCE = "reference"   # Secondary reference path

# Edge representation
class EntityEdge(BaseModel):
    """Edge between two entities in the graph"""
    source_id: UUID
    target_id: UUID
    edge_type: EdgeType                   # The container type (DIRECT, LIST, DICT, etc.)
    field_name: str
    container_index: Optional[int] = None  # For lists and tuples
    container_key: Optional[Any] = None    # For dictionaries
    ownership: bool = True                 # Whether this represents an ownership relationship
    is_hierarchical: bool = False          # Whether this is a hierarchical edge

    def __hash__(self):
        return hash((self.source_id, self.target_id, self.field_name))

# The main EntityGraph class
class EntityGraph(BaseModel):
    """
    A graph of entities with optimized structure for versioning operations.
    
    Maintains:
    - Complete collection of entities in the graph
    - Edge relationships between entities
    - Ancestry paths from each entity to the root
    - Root entity information
    """
    # Basic graph info
    root_ecs_id: UUID
    lineage_id: UUID
    
    # Node storage - maps entity.ecs_id to the entity object
    nodes: Dict[UUID, "Entity"] = Field(default_factory=dict)
    
    # Edge storage - maps (source_id, target_id) to edge details
    edges: Dict[Tuple[UUID, UUID], EntityEdge] = Field(default_factory=dict)
    
    # Outgoing edges by source - maps entity.ecs_id to list of target IDs
    outgoing_edges: Dict[UUID, List[UUID]] = Field(default_factory=lambda: defaultdict(list))
    
    # Incoming edges by target - maps entity.ecs_id to list of source IDs
    incoming_edges: Dict[UUID, List[UUID]] = Field(default_factory=lambda: defaultdict(list))
    
    # Ancestry paths - maps entity.ecs_id to list of IDs from entity to root
    ancestry_paths: Dict[UUID, List[UUID]] = Field(default_factory=dict)
    
    # Map of live_id to ecs_id for easy lookup
    live_id_to_ecs_id: Dict[UUID, UUID] = Field(default_factory=dict)
    
    # Metadata for debugging and tracking
    node_count: int = 0
    edge_count: int = 0
    max_depth: int = 0

    # Methods for adding entities and edges
    def add_entity(self, entity: "Entity") -> None:
        """Add an entity to the graph"""
        if entity.ecs_id not in self.nodes:
            self.nodes[entity.ecs_id] = entity
            self.live_id_to_ecs_id[entity.live_id] = entity.ecs_id
            self.node_count += 1
    
    def add_edge(self, edge: EntityEdge) -> None:
        """Add an edge to the graph"""
        edge_key = (edge.source_id, edge.target_id)
        if edge_key not in self.edges:
            self.edges[edge_key] = edge
            self.outgoing_edges[edge.source_id].append(edge.target_id)
            self.incoming_edges[edge.target_id].append(edge.source_id)
            self.edge_count += 1
    
    def add_direct_edge(self, source: "Entity", target: "Entity", field_name: str, ownership: bool = True) -> None:
        """Add a direct field reference edge"""
        edge = EntityEdge(
            source_id=source.ecs_id,
            target_id=target.ecs_id,
            edge_type=EdgeType.DIRECT,
            field_name=field_name,
            ownership=ownership
        )
        self.add_edge(edge)
    
    def add_list_edge(self, source: "Entity", target: "Entity", field_name: str, index: int, ownership: bool = True) -> None:
        """Add a list container edge"""
        edge = EntityEdge(
            source_id=source.ecs_id,
            target_id=target.ecs_id,
            edge_type=EdgeType.LIST,
            field_name=field_name,
            container_index=index,
            ownership=ownership
        )
        self.add_edge(edge)
    
    def add_dict_edge(self, source: "Entity", target: "Entity", field_name: str, key: Any, ownership: bool = True) -> None:
        """Add a dictionary container edge"""
        edge = EntityEdge(
            source_id=source.ecs_id,
            target_id=target.ecs_id,
            edge_type=EdgeType.DICT,
            field_name=field_name,
            container_key=key,
            ownership=ownership
        )
        self.add_edge(edge)
    
    def add_set_edge(self, source: "Entity", target: "Entity", field_name: str, ownership: bool = True) -> None:
        """Add a set container edge"""
        edge = EntityEdge(
            source_id=source.ecs_id,
            target_id=target.ecs_id,
            edge_type=EdgeType.SET,
            field_name=field_name,
            ownership=ownership
        )
        self.add_edge(edge)
    
    def add_tuple_edge(self, source: "Entity", target: "Entity", field_name: str, index: int, ownership: bool = True) -> None:
        """Add a tuple container edge"""
        edge = EntityEdge(
            source_id=source.ecs_id,
            target_id=target.ecs_id,
            edge_type=EdgeType.TUPLE,
            field_name=field_name,
            container_index=index,
            ownership=ownership
        )
        self.add_edge(edge)
    
    def set_ancestry_path(self, entity_id: UUID, path: List[UUID]) -> None:
        """Set the ancestry path for an entity"""
        self.ancestry_paths[entity_id] = path
        self.max_depth = max(self.max_depth, len(path))
    
    def mark_edge_as_hierarchical(self, source_id: UUID, target_id: UUID) -> None:
        """Mark an edge as the hierarchical (primary ownership) edge"""
        edge_key = (source_id, target_id)
        if edge_key in self.edges:
            edge = self.edges[edge_key]
            edge.is_hierarchical = True
    
    def mark_edge_as_reference(self, source_id: UUID, target_id: UUID) -> None:
        """Mark an edge as a reference (non-ownership) edge"""
        edge_key = (source_id, target_id)
        if edge_key in self.edges:
            edge = self.edges[edge_key]
            edge.is_hierarchical = False
    
    def get_entity(self, entity_id: UUID) -> Optional["Entity"]:
        """Get an entity by its ID"""
        return self.nodes.get(entity_id)
    
    def get_entity_by_live_id(self, live_id: UUID) -> Optional["Entity"]:
        """Get an entity by its live ID"""
        ecs_id = self.live_id_to_ecs_id.get(live_id)
        if ecs_id:
            return self.nodes.get(ecs_id)
        return None
    
    def get_edges(self, source_id: UUID, target_id: UUID) -> Optional[EntityEdge]:
        """Get the edge between two entities"""
        edge_key = (source_id, target_id)
        return self.edges.get(edge_key)
    
    def get_outgoing_edges(self, entity_id: UUID) -> List[UUID]:
        """Get all entities that this entity references"""
        return self.outgoing_edges.get(entity_id, [])
    
    def get_incoming_edges(self, entity_id: UUID) -> List[UUID]:
        """Get all entities that reference this entity"""
        return self.incoming_edges.get(entity_id, [])
    
    def get_ancestry_path(self, entity_id: UUID) -> List[UUID]:
        """Get the ancestry path from an entity to the root"""
        return self.ancestry_paths.get(entity_id, [])
    
    def get_path_distance(self, entity_id: UUID) -> int:
        """Get the distance (path length) from an entity to the root"""
        path = self.ancestry_paths.get(entity_id, [])
        return len(path)
    
    # Convenience methods for graph analysis
    def is_hierarchical_edge(self, source_id: UUID, target_id: UUID) -> bool:
        """Check if the edge is a hierarchical (ownership) edge"""
        edge_key = (source_id, target_id)
        if edge_key in self.edges:
            return self.edges[edge_key].is_hierarchical
        return False
    
    def get_hierarchical_parent(self, entity_id: UUID) -> Optional[UUID]:
        """Get the hierarchical parent of an entity"""
        for source_id in self.incoming_edges.get(entity_id, []):
            if self.is_hierarchical_edge(source_id, entity_id):
                return source_id
        return None
    
    def get_hierarchical_children(self, entity_id: UUID) -> List[UUID]:
        """Get all hierarchical children of an entity"""
        children = []
        for target_id in self.outgoing_edges.get(entity_id, []):
            if self.is_hierarchical_edge(entity_id, target_id):
                children.append(target_id)
        return children
    
    # Serialization/deserialization helpers
    def model_dump(self, *args, **kwargs) -> Dict[str, Any]:
        """Custom dump method to handle circular references"""
        # This will be implemented for efficient serialization
        return super().model_dump(*args, **kwargs)

# Functions to build the entity graph

def get_field_ownership(entity: "Entity", field_name: str) -> bool:
    """
    Since we're not handling circular references yet, all fields are treated as hierarchical.
    This is a simplification that will be enhanced later.
    
    Returns:
        Always returns True for now
    """
    return True

def get_pydantic_field_type_entities(entity: "Entity", field_name: str) -> Optional[Type]:
    """
    Get the entity type from a Pydantic field, handling container types properly.
    
    This function uses Pydantic's model_fields metadata, field annotations, and runtime
    type checking to determine if a field contains entities or entity containers,
    even when they're empty.
    
    Args:
        entity: The entity to inspect
        field_name: The name of the field to check
        
    Returns:
        The Entity type or subclass if the field contains entities, None otherwise
    """
    # Skip if field doesn't exist
    if field_name not in entity.model_fields:
        return None
    
    # First use Pydantic's model_fields which has rich metadata
    field_info = entity.model_fields[field_name]
    annotation = field_info.annotation
    
    # Directly analyze Pydantic field annotations
    if annotation:
        # Handle direct Entity field type
        try:
            # Check if it's an Entity type or subclass
            if annotation == Entity or (isinstance(annotation, type) and issubclass(annotation, Entity)):
                return annotation
        except TypeError:
            # Not a class or Entity, continue to other checks
            pass
            
        # Handle Optional fields
        origin = get_origin(annotation)
        if origin is Union:
            args = get_args(annotation)
            # Find the non-None type in Optional[T]
            inner_type = next((arg for arg in args if arg is not type(None)), None)
            if inner_type:
                try:
                    if inner_type == Entity or (isinstance(inner_type, type) and issubclass(inner_type, Entity)):
                        return inner_type
                except TypeError:
                    # Not a class or Entity, continue to other checks
                    pass
                
            # Handle Optional containers of entities
            origin = get_origin(inner_type) if inner_type else None
        
        # Handle container types
        if origin in (list, set, tuple, dict):
            args = get_args(annotation)
            if origin is dict and len(args) >= 2:
                # For dictionaries, check value type (second argument)
                value_type = args[1]
                try:
                    if value_type == Entity or (isinstance(value_type, type) and issubclass(value_type, Entity)):
                        return value_type
                except TypeError:
                    # Not a class or Entity, continue to other checks
                    pass
            elif origin in (list, set, tuple) and args:
                # For other containers, check first argument
                item_type = args[0]
                try:
                    if item_type == Entity or (isinstance(item_type, type) and issubclass(item_type, Entity)):
                        return item_type
                except TypeError:
                    # Not a class or Entity, continue to other checks
                    pass
    
    # Check field default factory for extra information
    # For empty containers created with default_factory, this helps determine item type
    if field_info.default_factory is not None:
        # Skip trying to call default_factory, it might not be safely callable here
        pass
    
    # If we can't determine from field metadata, check instance value
    field_value = getattr(entity, field_name)
    
    # For direct entity instances, return immediately
    if isinstance(field_value, Entity):
        return type(field_value)
    
    # For populated containers, check content types directly
    if field_value is not None:
        # Check list type
        if isinstance(field_value, list) and field_value:
            if isinstance(field_value[0], Entity):
                return type(field_value[0])
                
        # Check dict type
        elif isinstance(field_value, dict) and field_value:
            first_value = next(iter(field_value.values()), None)
            if isinstance(first_value, Entity):
                return type(first_value)
                
        # Check tuple type
        elif isinstance(field_value, tuple) and field_value:
            if isinstance(field_value[0], Entity):
                return type(field_value[0])
                
        # Check set type
        elif isinstance(field_value, set) and field_value:
            first_value = next(iter(field_value))
            if isinstance(first_value, Entity):
                return type(first_value)
    
    # Fallback to type hints as last resort
    try:
        # Get type hints for the class
        hints = get_type_hints(entity.__class__)
        if field_name not in hints:
            return None
        
        field_type = hints[field_name]
        
        # Handle Optional types
        origin = get_origin(field_type)
        if origin is Union:
            args = get_args(field_type)
            # Check if this is Optional[Entity]
            field_type = next((arg for arg in args if arg is not type(None)), None)
            # If we unwrapped an Optional, get its origin
            if field_type:
                origin = get_origin(field_type)
        
        # Check if field_type is directly Entity or a subclass
        if field_type and not origin and (field_type == Entity or issubclass(field_type, Entity)):
            return field_type
        
        # Handle container types
        if origin in (list, set, tuple, dict):
            args = get_args(field_type)
            if origin is dict and len(args) >= 2:
                # For dictionaries, check value type (second argument)
                value_type = args[1]
                if value_type == Entity or (inspect.isclass(value_type) and issubclass(value_type, Entity)):
                    return value_type
            elif origin in (list, set, tuple) and args:
                # For other containers, check first argument
                item_type = args[0]
                if item_type == Entity or (inspect.isclass(item_type) and issubclass(item_type, Entity)):
                    return item_type
    except Exception:
        # Fall back to direct instance check if type hint analysis fails
        pass
    
    return None

def process_entity_reference(
    graph: EntityGraph,
    source: "Entity",
    target: "Entity",
    field_name: str,
    list_index: Optional[int] = None,
    dict_key: Optional[Any] = None,
    tuple_index: Optional[int] = None,
    to_process: Optional[deque] = None,
    distance_map: Optional[Dict[UUID, int]] = None
):
    """Process a single entity reference, updating the graph"""
    # Get ownership information from the field
    ownership = get_field_ownership(source, field_name)
    
    # Add the appropriate edge type
    if list_index is not None:
        graph.add_list_edge(source, target, field_name, list_index, ownership)
    elif dict_key is not None:
        graph.add_dict_edge(source, target, field_name, dict_key, ownership)
    elif tuple_index is not None:
        graph.add_tuple_edge(source, target, field_name, tuple_index, ownership)
    else:
        graph.add_direct_edge(source, target, field_name, ownership)
    
    # Set the edge type immediately based on ownership
    edge_key = (source.ecs_id, target.ecs_id)
    if edge_key in graph.edges:
        if ownership:
            graph.mark_edge_as_hierarchical(source.ecs_id, target.ecs_id)
        else:
            graph.mark_edge_as_reference(source.ecs_id, target.ecs_id)
    
    # Update distance map for shortest path tracking
    if distance_map is not None:
        source_distance = distance_map.get(source.ecs_id, float('inf'))
        target_distance = distance_map.get(target.ecs_id, float('inf'))
        new_target_distance = source_distance + 1
        
        if new_target_distance < target_distance:
            # Found a shorter path to target
            distance_map[target.ecs_id] = int(new_target_distance)
    
    # Add to processing queue
    if to_process is not None:
        to_process.append(target)

def process_field_value(
    graph: EntityGraph,
    entity: "Entity",
    field_name: str,
    value: Any,
    field_type: Optional[Type],
    to_process: Optional[deque],
    distance_map: Optional[Dict[UUID, int]]
) -> None:
    """
    Process an entity field value and add any contained entities to the graph.
    
    Args:
        graph: The entity graph to update
        entity: The source entity containing the field
        field_name: The name of the field being processed
        value: The field value to process
        field_type: The expected entity type for this field, if known
        to_process: Queue of entities to process
        distance_map: Maps entity IDs to their distance from root
    """
    # Direct entity reference
    if isinstance(value, Entity):
        process_entity_reference(
            graph=graph,
            source=entity,
            target=value,
            field_name=field_name,
            to_process=to_process,
            distance_map=distance_map
        )
    
    # List of entities
    elif isinstance(value, list) and field_type:
        for i, item in enumerate(value):
            if isinstance(item, Entity):
                process_entity_reference(
                    graph=graph,
                    source=entity,
                    target=item,
                    field_name=field_name,
                    list_index=i,
                    to_process=to_process,
                    distance_map=distance_map
                )
    
    # Dict of entities
    elif isinstance(value, dict) and field_type:
        for k, v in value.items():
            if isinstance(v, Entity):
                process_entity_reference(
                    graph=graph,
                    source=entity,
                    target=v,
                    field_name=field_name,
                    dict_key=k,
                    to_process=to_process,
                    distance_map=distance_map
                )
    
    # Tuple of entities
    elif isinstance(value, tuple) and field_type:
        for i, item in enumerate(value):
            if isinstance(item, Entity):
                process_entity_reference(
                    graph=graph,
                    source=entity,
                    target=item,
                    field_name=field_name,
                    tuple_index=i,
                    to_process=to_process,
                    distance_map=distance_map
                )
    
    # Set of entities
    elif isinstance(value, set) and field_type:
        for item in value:
            if isinstance(item, Entity):
                process_entity_reference(
                    graph=graph,
                    source=entity,
                    target=item,
                    field_name=field_name,
                    to_process=to_process,
                    distance_map=distance_map
                )

def build_entity_graph(root_entity: "Entity") -> EntityGraph:
    """
    Build a complete entity graph from a root entity in a single pass.
    
    This algorithm:
    1. Builds the graph structure and ancestry paths in a single traversal
    2. Immediately classifies edges based on ownership
    3. Maintains shortest paths for each entity
    4. Creates ancestry paths for path-based diffing on-the-fly
    
    Args:
        root_entity: The root entity of the graph
        
    Returns:
        EntityGraph: A complete graph of the entity hierarchy
    """
    # Initialize the graph
    graph = EntityGraph(
        root_ecs_id=root_entity.ecs_id,
        lineage_id=root_entity.lineage_id
    )
    
    # Maps entity ecs_id to its ancestry path (list of entity IDs from root to this entity)
    ancestry_paths = {root_entity.ecs_id: [root_entity.ecs_id]}
    
    # Queue for breadth-first traversal with path information
    # Each item is (entity, parent_id)
    # For the root, parent is None
    # Using direct annotation instead of a type alias
    to_process: deque[tuple[Entity, Optional[UUID]]] = deque([(root_entity, None)])
    
    # Set of processed entities to avoid cycles
    processed = set()
    
    # Add root entity to graph
    graph.add_entity(root_entity)
    graph.set_ancestry_path(root_entity.ecs_id, [root_entity.ecs_id])
    
    # Process all entities
    while to_process:
        entity, parent_id = to_process.popleft()
        
        # Raise error if we encounter a circular reference
        # We don't allow circular entities at this stage
        if entity.ecs_id in processed and parent_id is not None:
            raise ValueError(f"Circular entity reference detected: {entity.ecs_id}. Circular entities are not supported.")
        
        # If we've seen this entity before but now found a new parent relationship,
        # we only need to process the edge, not the entity's fields again
        entity_needs_processing = entity.ecs_id not in processed
        
        # Mark as processed
        processed.add(entity.ecs_id)
        
        # Process edge from parent if this isn't the root
        if parent_id is not None:
            # Update the edge's hierarchical status - all edges are hierarchical for now
            edge_key = (parent_id, entity.ecs_id)
            if edge_key in graph.edges:
                # Always mark as hierarchical (since we're not handling circular references yet)
                graph.mark_edge_as_hierarchical(parent_id, entity.ecs_id)
                
                # Update ancestry path
                if parent_id in ancestry_paths:
                    parent_path = ancestry_paths[parent_id]
                    entity_path = parent_path + [entity.ecs_id]
                    
                    # If we have no path yet or found a shorter path
                    if entity.ecs_id not in ancestry_paths or len(entity_path) < len(ancestry_paths[entity.ecs_id]):
                        ancestry_paths[entity.ecs_id] = entity_path
                        graph.set_ancestry_path(entity.ecs_id, entity_path)
        
        # If we've already processed this entity's fields, skip to the next one
        if not entity_needs_processing:
            continue
            
        # Process all fields if the entity hasn't been processed yet
        for field_name in entity.model_fields:
            value = getattr(entity, field_name)
            
            # Skip None values
            if value is None:
                continue
            
            # Get expected type for this field
            field_type = get_pydantic_field_type_entities(entity, field_name)
            
            # Direct entity reference
            if isinstance(value, Entity):
                # Add entity to graph if not already present
                if value.ecs_id not in graph.nodes:
                    graph.add_entity(value)
                
                # Add the appropriate edge type
                process_entity_reference(
                    graph=graph,
                    source=entity,
                    target=value,
                    field_name=field_name,
                    to_process=None,  # We'll handle queue manually
                    distance_map=None  # Not using distance map in single-pass version
                )
                
                # Add to processing queue
                to_process.append((value, entity.ecs_id))
            
            # List of entities
            elif isinstance(value, list) and field_type:
                for i, item in enumerate(value):
                    if isinstance(item, Entity):
                        # Add entity to graph if not already present
                        if item.ecs_id not in graph.nodes:
                            graph.add_entity(item)
                        
                        # Add the appropriate edge type
                        process_entity_reference(
                            graph=graph,
                            source=entity,
                            target=item,
                            field_name=field_name,
                            list_index=i,
                            to_process=None,  # We'll handle queue manually
                            distance_map=None  # Not using distance map in single-pass version
                        )
                        
                        # Add to processing queue
                        to_process.append((item, entity.ecs_id))
            
            # Dict of entities
            elif isinstance(value, dict) and field_type:
                for k, v in value.items():
                    if isinstance(v, Entity):
                        # Add entity to graph if not already present
                        if v.ecs_id not in graph.nodes:
                            graph.add_entity(v)
                        
                        # Add the appropriate edge type
                        process_entity_reference(
                            graph=graph,
                            source=entity,
                            target=v,
                            field_name=field_name,
                            dict_key=k,
                            to_process=None,  # We'll handle queue manually
                            distance_map=None  # Not using distance map in single-pass version
                        )
                        
                        # Add to processing queue
                        to_process.append((v, entity.ecs_id))
            
            # Tuple of entities
            elif isinstance(value, tuple) and field_type:
                for i, item in enumerate(value):
                    if isinstance(item, Entity):
                        # Add entity to graph if not already present
                        if item.ecs_id not in graph.nodes:
                            graph.add_entity(item)
                        
                        # Add the appropriate edge type
                        process_entity_reference(
                            graph=graph,
                            source=entity,
                            target=item,
                            field_name=field_name,
                            tuple_index=i,
                            to_process=None,  # We'll handle queue manually
                            distance_map=None  # Not using distance map in single-pass version
                        )
                        
                        # Add to processing queue
                        to_process.append((item, entity.ecs_id))
            
            # Set of entities
            elif isinstance(value, set) and field_type:
                for item in value:
                    if isinstance(item, Entity):
                        # Add entity to graph if not already present
                        if item.ecs_id not in graph.nodes:
                            graph.add_entity(item)
                        
                        # Add the appropriate edge type
                        process_entity_reference(
                            graph=graph,
                            source=entity,
                            target=item,
                            field_name=field_name,
                            to_process=None,  # We'll handle queue manually
                            distance_map=None  # Not using distance map in single-pass version
                        )
                        
                        # Add to processing queue
                        to_process.append((item, entity.ecs_id))
    
    # Ensure all entities have an ancestry path
    # This is just a safety check - all entities should have paths by now
    for entity_id in graph.nodes:
        if entity_id not in ancestry_paths:
            raise ValueError(f"Entity {entity_id} does not have an ancestry path")
    
    return graph

def find_modified_entities(
    new_graph: EntityGraph,
    old_graph: EntityGraph
) -> Set[UUID]:
    """
    Find entities that have been modified between two graphs.
    
    Uses the path-based diffing algorithm to efficiently identify changes.
    
    Args:
        new_graph: The new entity graph
        old_graph: The old entity graph (from storage)
        
    Returns:
        Set[UUID]: Set of entity ecs_ids that need new versions
    """
    # This is just a stub for now
    # The real implementation will follow the algorithm in the design doc
    return set()

def update_entity_versions(
    graph: EntityGraph,
    entities_to_version: Set[UUID]
) -> None:
    """
    Update ecs_ids for entities that need new versions.
    
    Args:
        graph: The entity graph
        entities_to_version: Set of entity ecs_ids that need new versions
    """
    # This is just a stub for now
    # The real implementation will follow the algorithm in the design doc
    pass


def generate_mermaid_diagram(graph: EntityGraph, include_attributes: bool = False) -> str:
    """
    Generate a Mermaid diagram from an EntityGraph.
    
    Args:
        graph: The entity graph to visualize
        include_attributes: Whether to include entity attributes in the diagram
        
    Returns:
        A string containing the Mermaid diagram code
    """
    if not graph.nodes:
        return "```mermaid\ngraph TD\n  Empty[Empty Graph]\n```"
        
    lines = ["```mermaid", "graph TD"]
    
    # Entity nodes
    for entity_id, entity in graph.nodes.items():
        # Use a shortened version of ID for display
        short_id = str(entity_id)[-8:]
        
        # Create node with label
        entity_type = entity.__class__.__name__
        
        if include_attributes:
            # Include some attributes in the label
            attrs = [
                f"ecs_id: {short_id}",
                f"lineage_id: {str(entity.lineage_id)[-8:]}"
            ]
            if entity.root_ecs_id:
                attrs.append(f"root: {str(entity.root_ecs_id)[-8:]}")
                
            node_label = f"{entity_type}\\n{' | '.join(attrs)}"
        else:
            # Simple label with just type and short ID
            node_label = f"{entity_type} {short_id}"
            
        lines.append(f"  {entity_id}[\"{node_label}\"]")
    
    # Root node styling
    lines.append(f"  {graph.root_ecs_id}:::rootNode")
    
    # Add edges
    for edge_key, edge in graph.edges.items():
        source_id, target_id = edge_key
        
        # Determine edge style based on hierarchical status
        if edge.is_hierarchical:
            # Hierarchical edges (solid, with arrow)
            edge_style = "-->"
            edge_class = "hierarchicalEdge"
        else:
            # Reference edges (dashed, with arrow)
            edge_style = "-.->"
            edge_class = "referenceEdge"
            
        # Add edge label based on field name and container info
        edge_label = edge.field_name
        
        if edge.container_index is not None:
            edge_label += f"[{edge.container_index}]"
        elif edge.container_key is not None:
            edge_label += f"[{edge.container_key}]"
            
        # Create the edge line
        edge_line = f"  {source_id} {edge_style}|{edge_label}| {target_id}"
        if edge.is_hierarchical:
            edge_line += ":::hierarchicalEdge"
        else:
            edge_line += ":::referenceEdge"
            
        lines.append(edge_line)
    
    # Add styling classes
    lines.extend([
        "  classDef rootNode fill:#f9f,stroke:#333,stroke-width:2px",
        "  classDef hierarchicalEdge stroke:#333,stroke-width:2px",
        "  classDef referenceEdge stroke:#999,stroke-width:1px,stroke-dasharray:5 5"
    ])
    
    lines.append("```")
    return "\n".join(lines)


class Entity(BaseModel):
    ecs_id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    live_id: UUID = Field(default_factory=uuid4, description="Live/warm identifier")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    forked_at: Optional[datetime] = Field(default=None, description="Timestamp of the last fork")
    previous_ecs_id: Optional[UUID] = None
    lineage_id: UUID = Field(default_factory=uuid4)
    old_ids: List[UUID] = Field(default_factory=list)
    root_ecs_id: Optional[UUID] = Field(default=None, description="The ecs_id of the root entity of this entity's graph")
    root_live_id: Optional[UUID] = Field(default=None, description="The live_id of the root entity of this entity's graph")
    from_storage: bool = Field(default=False, description="Whether the entity was loaded from storage, used to prevent re-registration")
    untyped_data: str = Field(default="", description="Default data container for untyped data, string diff will be used to detect changes")
    attribute_source: Dict[str, Optional[UUID]] = Field(default_factory=dict, description="Tracks the source entity for each attribute")

    @model_validator(mode='after')
    def validate_attribute_source(self) -> Self:
        """
        Validates that the attribute_source dictionary only contains keys 
        that match fields in the model. Initializes the dictionary if not present,
        and adds missing fields with source=None to indicate initialization from Python.
        """
        # Initialize the attribute_source if not present
        if self.attribute_source is None:
            raise ValueError("attribute_source is None factory did not work")
        
        # Get all valid field names for this model
        valid_fields = set(self.model_fields.keys())
        
        # Remove 'attribute_source' itself from valid fields to prevent recursion
        valid_fields.discard('attribute_source')
        
        # Check that all keys in attribute_source are valid field names
        invalid_keys = set(self.attribute_source.keys()) - valid_fields
        if invalid_keys:
            raise ValueError(f"Invalid keys in attribute_source: {invalid_keys}. Valid fields are: {valid_fields}")
        
        # Initialize missing fields with None source (originated in Python)
        for field_name in valid_fields:
            if field_name not in self.attribute_source:
                self.attribute_source[field_name] = None
        
        return self

    def _hash_str(self) -> str:
        """Generate a hash string from identity fields."""
        return f"{self.ecs_id}-{self.live_id}-{self.root_ecs_id}-{self.root_live_id}"
        
    def __hash__(self) -> int:
        """
        Make entity hashable using a string representation of identity fields.
        """
        return hash(self._hash_str())
        
    def __eq__(self, other: object) -> bool:
        """
        Simple equality comparison using the hash string.
        """
        if not isinstance(other, Entity):
            return False
        return self._hash_str() == other._hash_str()

    
    def is_root_entity(self) -> bool:
        """
        Check if the entity is the root of its graph.
        """
        return self.root_ecs_id == self.ecs_id
    
    def is_orphan(self) -> bool:
        """
        Check if the entity is an orphan.
        """
        return self.root_ecs_id is None or self.root_live_id is None
    
    def fork(self, new_root_ecs_id: Optional[UUID] = None) -> None:
        """
        Fork the entity.
        Assign new ecs_id 
        Assign a forked_at timestamp
        Updates previous_ecs_id to the previous ecs_id
        Adds the previous ecs_id to old_ids
        If new_root_ecs_id is provided, updates root_ecs_id to the new value
        """
        old_ecs_id = self.ecs_id
        new_ecs_id = uuid4()
        
        self.ecs_id = new_ecs_id
        self.forked_at = datetime.now(timezone.utc)
        self.old_ecs_id = old_ecs_id
        self.old_ids.append(old_ecs_id)
        if new_root_ecs_id:
            self.root_ecs_id = new_root_ecs_id
    
    def get_root_entity(self) -> "Entity": #type: ignore
        """
        This method will use the registry to get the live python object of the root entity of the graph
        """
        pass

    def get_graph(self, recompute: bool = False) -> "EntityGraph": #type: ignore
        """
        This method will use the registry to get the whole graph of the entity if 
        recompute is True it will recompute the graph from the live root entity
        otherwise it will return the cached graph based on the ecs_id of the root entity
        """
        pass

    def get_stored_reference(self) -> "Entity": #type: ignore
        """
        This method will use the registry to get the stored reference of the entity using the
        ecs_id and root_ecs_id of the entity, this may differet from the carrent live object
        """
        pass
    
    def prevalidate_detach(self) -> None:
        """
        Pre-validate the detachment of the entity from its graph.
        for later optimizaiton phases this should be safe to run before the fork
        because if the entity is effectively detached this graph can be stored as the new cold reference
        """
        pass
    
    def detach(self, promote_to_root: bool = False) -> None:
        """
        Detach the entity from its graph due to disconnection from the root entity.
        Sets the entity root to either None or promotes the entity to the root of its graph. And then forks the entity.
        If the entity is to be promoted the forks happens first so that the root is directly assigned to the new self ecs id
        If the entity is to be re-atached to a new root it must be first detached.
        """
        if self.is_root_entity():
            #if is already root it can not be detached from anything
            return None
        # here we will have to add a method once we implement the registry which checks if the entity has really been actually from the root entity in the python object,
        #  this method role is not to remove the entity from the python root but to update the registry to reflect the detachment of the in memory reference between python objects
        self.prevalidate_detach()

        #set root to None the entity is effectively an orphan detached from the registry
        self.root_ecs_id = None
        self.root_live_id = None
        #forks the entity to assign a new ecs_id and update the old_ecs_id to the previous ecs_id and adds the previous ecs_id to old_ids
        self.fork()
        if promote_to_root:
            #if promoting to root, set the new root to the new ecs_id
            self.root_ecs_id = self.ecs_id
            self.root_live_id = self.live_id

    def prevalidate_attach(self, new_entity: "Entity") -> None:
        """
        Pre-validate the attachment of the entity to a new entity. Will raise an error if the new entity is in practice an orphan
        this will trigger reconstruction of the graph from the live root entity 
        we can do it before the fork and use it for the comparisong that will guide the 
        upstream ecs_id update for all the entities in the graph we need that update to be triggered
        in order to have the new root ecs id anyway.
        """
        pass

    def attach(self, new_entity: "Entity") -> None:
        """
        Attach the entity to a new entity.
        """
        #check that the new entity is not an orphan
        if new_entity.is_orphan():
            raise ValueError("Cannot attach an orphan entity")
         #first detach the entity if it is not already an orphan

        if not self.is_orphan():
            self.detach()
        #prevalidate the attachment of the entity to the new entity this will 
        self.prevalidate_attach(new_entity)

        #attach the entity to the new entity root in reality this in the future will happen during the validation of the attachment 
        #since there is where we globally define for the whoel graph which nodes needs new ecs id 
        # due to the attachment
        self.root_ecs_id = new_entity.root_ecs_id
        self.root_live_id = new_entity.root_live_id
        self.lineage_id = new_entity.lineage_id
        #fork the entity to assign a new ecs_id and update the old_ecs_id to the previous ecs_id and adds the previous ecs_id to old_ids
        self.fork()


# Example hierarchical entities

class EntityinEntity(Entity):
    """
    An entity that contains other entities.
    """
    sub_entity: Entity = Field(description="The sub entity of the entity", default_factory=Entity)


class EntityinList(Entity):
    """
    An entity that contains a list of entities.
    """
    entities: List[Entity] = Field(description="The list of entities of the entity", default_factory=list)

class EntityinDict(Entity):
    """
    An entity that contains a dictionary of entities.
    """
    entities: Dict[str, Entity] = Field(description="The dictionary of entities of the entity", default_factory=dict)

class EntityinTuple(Entity):
    """
    An entity that contains a tuple of entities.
    """
    entities: Tuple[Entity, ...] = Field(description="The tuple of entities of the entity")

class EntityinSet(Entity):
    """
    An entity that contains a set of entities.
    """
    entities: Set[Entity] = Field(description="The set of entities of the entity")

class BaseModelWithEntity(BaseModel):
    """
    A base model that contains an entity.
    """
    entity: Entity = Field(description="The entity of the model", default_factory=Entity)

class EntityinBaseModel(Entity):
    """
    An entity that contains a base model.
    """
    base_model: BaseModelWithEntity = Field(description="The base model of the entity", default_factory=BaseModelWithEntity)

class EntityInEntityInEntity(Entity):
    """
    An entity that contains an entity that contains an entity.
    """
    entity_of_entity: EntityinEntity = Field(description="The entity of the entity", default_factory=EntityinEntity)

# Entities with non-entity data types

class EntityWithPrimitives(Entity):
    """
    An entity with primitive data types.
    """
    string_value: str = ""
    int_value: int = 0
    float_value: float = 0.0
    bool_value: bool = False
    datetime_value: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    uuid_value: UUID = Field(default_factory=uuid4)

class EntityWithContainersOfPrimitives(Entity):
    """
    An entity with containers of primitive types.
    """
    string_list: List[str] = Field(default_factory=list)
    int_dict: Dict[str, int] = Field(default_factory=dict)
    float_tuple: Tuple[float, ...] = Field(default_factory=tuple)
    bool_set: Set[bool] = Field(default_factory=set)

class EntityWithMixedContainers(Entity):
    """
    An entity with containers that mix entity and non-entity types.
    """
    mixed_list: List[Union[Entity, str]] = Field(default_factory=list)
    mixed_dict: Dict[str, Union[Entity, int]] = Field(default_factory=dict)

class EntityWithNestedContainers(Entity):
    """
    An entity with nested containers.
    """
    list_of_lists: List[List[str]] = Field(default_factory=list)
    dict_of_dicts: Dict[str, Dict[str, int]] = Field(default_factory=dict)
    list_of_dicts: List[Dict[str, Entity]] = Field(default_factory=list)

class OptionalEntityContainers(Entity):
    """
    An entity with optional containers of entities.
    """
    optional_entity: Optional[Entity] = None
    optional_entity_list: Optional[List[Entity]] = None
    optional_entity_dict: Optional[Dict[str, Entity]] = None

# Hierachical entities

class HierachicalEntity(Entity):
    """
    A hierachical entity.
    """
    entity_of_entity_1: EntityinEntity = Field(description="The entity of the entity", default_factory=EntityinEntity)
    entity_of_entity_2: EntityinEntity = Field(description="The entity of the entity", default_factory=EntityinEntity)
    flat_entity: Entity = Field(description="The flat entity", default_factory=Entity)
    entity_of_entity_of_entity: EntityInEntityInEntity = Field(description="The entity of the entity of the entity", default_factory=EntityInEntityInEntity)
    primitive_data: EntityWithPrimitives = Field(description="Entity with primitive data", default_factory=EntityWithPrimitives)





