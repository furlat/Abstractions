""" Implementing step by step the entity system from
source docs:  /Users/tommasofurlanello/Documents/Dev/Abstractions/abstractions/ecs/tree_entity.md"""

from pydantic import BaseModel, Field, model_validator

from uuid import UUID, uuid4
from datetime import datetime, timezone
from collections import defaultdict

from pydantic import BaseModel, Field, model_validator
from typing import Dict, List, Set, Tuple, Any, Optional, Type, Union, get_type_hints, get_origin, get_args, Self
from uuid import UUID, uuid4
from enum import Enum
from collections import deque
import inspect
from pydantic import create_model

# Event system imports for automatic event emission
from abstractions.events.events import emit_events, StateTransitionEvent, ModifyingEvent, ModifiedEvent

from abstractions.events.entity_events import (
    EntityRegistrationEvent, EntityRegisteredEvent,
    EntityVersioningEvent, EntityVersionedEvent,
    EntityPromotionEvent, EntityPromotedEvent,
    EntityDetachmentEvent, EntityDetachedEvent,
    EntityAttachmentEvent, EntityAttachedEvent,
    DataBorrowingEvent, DataBorrowedEvent,
    IDUpdateEvent, IDUpdatedEvent,
    TreeBuildingEvent, TreeBuiltEvent,
    ChangeDetectionEvent, ChangesDetectedEvent
)

# Edge type enum
class EdgeType(str, Enum):
    """Type of edge between entities"""
    DIRECT = "direct"         # Direct field reference
    LIST = "list"             # Entity in a list
    DICT = "dict"             # Entity in a dictionary
    SET = "set"               # Entity in a set
    TUPLE = "tuple"           # Entity in a tuple
    HIERARCHICAL = "hierarchical"  # Main ownership path

# Edge representation
class EntityEdge(BaseModel):
    """Edge between two entities in the tree"""
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

# The main EntityTree class
class EntityTree(BaseModel):
    """
    A tree of entities with optimized structure for versioning operations.
    
    Maintains:
    - Complete collection of entities in the tree
    - Edge relationships between entities
    - Ancestry paths from each entity to the root
    - Root entity information
    """
    # Basic tree info
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
        """Add an entity to the tree"""
        if entity.ecs_id not in self.nodes:
            self.nodes[entity.ecs_id] = entity
            self.live_id_to_ecs_id[entity.live_id] = entity.ecs_id
            self.node_count += 1
    
    def add_edge(self, edge: EntityEdge) -> None:
        """Add an edge to the tree"""
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
    
    # Convenience methods for tree analysis
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
    
    def update_live_ids(self) -> None:
        """ update the live id of all nodes in the tree used when a stored tree is loaded from the registry to enforce immutability
        and map them to the new live id """
        root_node = self.get_entity(self.root_ecs_id)
        if root_node is None:
            raise ValueError("root node not found in tree")
        old_root_live_id = root_node.live_id
        new_root_live_id = uuid4()
        root_node.live_id = new_root_live_id
        root_node.root_live_id = new_root_live_id
        self.live_id_to_ecs_id[new_root_live_id] = self.root_ecs_id
        # Only remove the old ID if it's in the map
        if old_root_live_id in self.live_id_to_ecs_id:
            self.live_id_to_ecs_id.pop(old_root_live_id)
        for node in self.nodes.values():
            if node.live_id != new_root_live_id:
                old_node_live_id = node.live_id  # Save the old ID before changing it
                node.live_id = uuid4()  # Generate a new ID
                node.root_live_id = new_root_live_id  # Update the root reference
                self.live_id_to_ecs_id[node.live_id] = node.ecs_id  # Map new ID to ecs_id
                # Only remove the old ID if it's in the map
                if old_node_live_id in self.live_id_to_ecs_id:
                    self.live_id_to_ecs_id.pop(old_node_live_id)

        # Serialization/deserialization helpers


# Functions to build the entity tree

def get_field_ownership(entity: "Entity", field_name: str) -> bool:
    """
    Since we're not handling circular references yet, all fields are treated as hierarchical.
    This is a simplification that will be enhanced later.
    
    Returns:
        Always returns True for now
    """
    return True

def get_pydantic_field_type_entities(entity: "Entity", field_name: str, detect_non_entities: bool = False) -> Union[Optional[Type], bool]:
    """
    Get the entity type from a Pydantic field, handling container types properly.
    
    This function uses Pydantic's model_fields metadata, field annotations, and runtime
    type checking to determine if a field contains entities or entity containers,
    even when they're empty.
    
    Args:
        entity: The entity to inspect
        field_name: The name of the field to check
        detect_non_entities: If True, returns None for entity fields and True for non-entity fields
        
    Returns:
        If detect_non_entities=False (default):
            - The Entity type or subclass if the field contains entities
            - None otherwise
        If detect_non_entities=True:
            - None for entity fields
            - True for non-entity fields
    """
    # Skip if field doesn't exist
    if field_name not in entity.model_fields:
        return None
    
    # First use Pydantic's model_fields which has rich metadata
    field_info = entity.model_fields[field_name]
    annotation = field_info.annotation
    
    # Check for identity fields that should be ignored in comparisons
    if field_name in ('ecs_id', 'live_id', 'created_at', 'forked_at', 'previous_ecs_id', 
                      'old_ids', 'old_ecs_id', 'from_storage', 'attribute_source', 'root_ecs_id', 
                      'root_live_id', 'lineage_id'):
        return None
    
    # For direct entity instance, handle based on detect_non_entities flag
    field_value = getattr(entity, field_name)
    if isinstance(field_value, Entity):
        return None if detect_non_entities else type(field_value)
    
    # First check for container values with entities
    is_entity_container = False
    
    # For populated containers, check content types directly
    if field_value is not None:
        # Check list type
        if isinstance(field_value, list) and field_value:
            if any(isinstance(item, Entity) for item in field_value):
                is_entity_container = True
                if not detect_non_entities:
                    # Find the first entity to use its type
                    for item in field_value:
                        if isinstance(item, Entity):
                            return type(item)
                
        # Check dict type
        elif isinstance(field_value, dict) and field_value:
            if any(isinstance(v, Entity) for v in field_value.values()):
                is_entity_container = True
                if not detect_non_entities:
                    # Find the first entity to use its type
                    for v in field_value.values():
                        if isinstance(v, Entity):
                            return type(v)
                
        # Check tuple type
        elif isinstance(field_value, tuple) and field_value:
            if any(isinstance(item, Entity) for item in field_value):
                is_entity_container = True
                if not detect_non_entities:
                    # Find the first entity to use its type
                    for item in field_value:
                        if isinstance(item, Entity):
                            return type(item)
                
        # Check set type
        elif isinstance(field_value, set) and field_value:
            if any(isinstance(item, Entity) for item in field_value):
                is_entity_container = True
                if not detect_non_entities:
                    # Find the first entity to use its type
                    for item in field_value:
                        if isinstance(item, Entity):
                            return type(item)
    
    # If we've determined it's a container with entities
    if is_entity_container:
        return None if detect_non_entities else None  # We return type above if not detect_non_entities
    
    # If we're looking for non-entity fields and we've gotten this far,
    # it's a non-entity field
    if detect_non_entities:
        return True
    
    # Directly analyze Pydantic field annotations only if we need to detect entity types
    if annotation and not detect_non_entities:
        # Handle direct Entity field type
        try:
            # Check if it's an Entity type or subclass
            if annotation == Entity or (isinstance(annotation, type) and issubclass(annotation, Entity)):
                return None if detect_non_entities else annotation
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
                        return None if detect_non_entities else inner_type
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
                        return None if detect_non_entities else value_type
                except TypeError:
                    # Not a class or Entity, continue to other checks
                    pass
            elif origin in (list, set, tuple) and args:
                # For other containers, check first argument
                item_type = args[0]
                try:
                    if item_type == Entity or (isinstance(item_type, type) and issubclass(item_type, Entity)):
                        return None if detect_non_entities else item_type
                except TypeError:
                    # Not a class or Entity, continue to other checks
                    pass
    
    # Check field default factory for extra information
    # For empty containers created with default_factory, this helps determine item type
    if field_info.default_factory is not None and not detect_non_entities:
        # Skip trying to call default_factory, it might not be safely callable here
        pass
    
    # Fallback to type hints as last resort for entity detection
    if not detect_non_entities:
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
                return None if detect_non_entities else field_type
            
            # Handle container types
            if origin in (list, set, tuple, dict):
                args = get_args(field_type)
                if origin is dict and len(args) >= 2:
                    # For dictionaries, check value type (second argument)
                    value_type = args[1]
                    if value_type == Entity or (inspect.isclass(value_type) and issubclass(value_type, Entity)):
                        return None if detect_non_entities else value_type
                elif origin in (list, set, tuple) and args:
                    # For other containers, check first argument
                    item_type = args[0]
                    if item_type == Entity or (inspect.isclass(item_type) and issubclass(item_type, Entity)):
                        return None if detect_non_entities else item_type
        except Exception:
            # Fall back to direct instance check if type hint analysis fails
            pass
    
    # If detect_non_entities is True and we've gotten this far without detecting an entity,
    # return True to indicate this is a non-entity field
    if detect_non_entities:
        return True
        
    # Otherwise, return None to indicate no entity type was found
    return None

def process_entity_reference(
    tree: EntityTree,
    source: "Entity",
    target: "Entity",
    field_name: str,
    list_index: Optional[int] = None,
    dict_key: Optional[Any] = None,
    tuple_index: Optional[int] = None,
    to_process: Optional[deque] = None,
    distance_map: Optional[Dict[UUID, int]] = None
):
    """Process a single entity reference, updating the tree"""
    # Get ownership information from the field
    ownership = True
    
    # Add the appropriate edge type
    if list_index is not None:
        tree.add_list_edge(source, target, field_name, list_index, ownership)
    elif dict_key is not None:
        tree.add_dict_edge(source, target, field_name, dict_key, ownership)
    elif tuple_index is not None:
        tree.add_tuple_edge(source, target, field_name, tuple_index, ownership)
    else:
        tree.add_direct_edge(source, target, field_name, ownership)
    
    # Set the edge type immediately based on ownership
    edge_key = (source.ecs_id, target.ecs_id)
    if edge_key in tree.edges:
        if ownership:
            tree.mark_edge_as_hierarchical(source.ecs_id, target.ecs_id)

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
    tree: EntityTree,
    entity: "Entity",
    field_name: str,
    value: Any,
    field_type: Optional[Type],
    to_process: Optional[deque],
    distance_map: Optional[Dict[UUID, int]]
) -> None:
    """
    Process an entity field value and add any contained entities to the tree.
    
    Args:
        tree: The entity tree to update
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
            tree=tree,
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
                    tree=tree,
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
                    tree=tree,
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
                    tree=tree,
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
                    tree=tree,
                    source=entity,
                    target=item,
                    field_name=field_name,
                    to_process=to_process,
                    distance_map=distance_map
                )

@emit_events(
    creating_factory=lambda root_entity: TreeBuildingEvent(
        subject_type=type(root_entity),
        subject_id=root_entity.ecs_id,
        process_name="tree_building",
        root_entity_type=type(root_entity).__name__,
        root_entity_id=root_entity.ecs_id,
        building_method="full_build",
        starting_from_storage=False,
        has_existing_tree=False
    ),
    created_factory=lambda result, root_entity: TreeBuiltEvent(
        subject_type=type(root_entity),
        subject_id=root_entity.ecs_id,
        process_name="tree_building",
        root_entity_type=type(root_entity).__name__,
        root_entity_id=root_entity.ecs_id,
        build_successful=True,
        node_count=result.node_count,
        edge_count=result.edge_count,
        max_depth=result.max_depth,
        build_duration_ms=None,
        entities_processed=result.node_count
    )
)
def build_entity_tree(root_entity: "Entity") -> EntityTree:
    """
    Build a complete entity tree from a root entity in a single pass.
    
    This algorithm:
    1. Builds the tree structure and ancestry paths in a single traversal
    2. Immediately classifies edges based on ownership
    3. Maintains shortest paths for each entity
    4. Creates ancestry paths for path-based diffing on-the-fly
    
    Args:
        root_entity: The root entity of the tree
        
    Returns:
        EntityTree: A complete tree of the entity hierarchy
    """
    # Initialize the tree
    tree = EntityTree(
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
    
    # Add root entity to tree
    tree.add_entity(root_entity)
    tree.set_ancestry_path(root_entity.ecs_id, [root_entity.ecs_id])
    
    # Process all entities
    while to_process:
        entity, parent_id = to_process.popleft()
        
        # Raise error if we encounter a circular reference
        # We don't allow circular entities at this stage
        if entity.ecs_id in processed and parent_id is not None:
            raise ValueError(f"Circular entity reference detected: {entity.ecs_id}. Circular entities are not supported Entities must form hierarchical trees.")
        
        # If we've seen this entity before but now found a new parent relationship,
        # we only need to process the edge, not the entity's fields again
        entity_needs_processing = entity.ecs_id not in processed
        
        # Mark as processed
        processed.add(entity.ecs_id)
        
        # Process edge from parent if this isn't the root
        if parent_id is not None:
            # Update the edge's hierarchical status - all edges are hierarchical for now
            edge_key = (parent_id, entity.ecs_id)
            if edge_key in tree.edges:
                # Always mark as hierarchical (since we're not handling circular references yet)
                tree.mark_edge_as_hierarchical(parent_id, entity.ecs_id)
                
                # Update ancestry path
                if parent_id in ancestry_paths:
                    parent_path = ancestry_paths[parent_id]
                    entity_path = parent_path + [entity.ecs_id]
                    
                    # If we have no path yet or found a shorter path
                    if entity.ecs_id not in ancestry_paths or len(entity_path) < len(ancestry_paths[entity.ecs_id]):
                        ancestry_paths[entity.ecs_id] = entity_path
                        tree.set_ancestry_path(entity.ecs_id, entity_path)
        
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
                # Add entity to tree if not already present
                if value.ecs_id not in tree.nodes:
                    tree.add_entity(value)
                
                # Add the appropriate edge type
                process_entity_reference(
                    tree=tree,
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
                        # Add entity to tree if not already present
                        if item.ecs_id not in tree.nodes:
                            tree.add_entity(item)
                        
                        # Add the appropriate edge type
                        process_entity_reference(
                            tree=tree,
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
                        # Add entity to tree if not already present
                        if v.ecs_id not in tree.nodes:
                            tree.add_entity(v)
                        
                        # Add the appropriate edge type
                        process_entity_reference(
                            tree=tree,
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
                        # Add entity to tree if not already present
                        if item.ecs_id not in tree.nodes:
                            tree.add_entity(item)
                        
                        # Add the appropriate edge type
                        process_entity_reference(
                            tree=tree,
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
                        # Add entity to tree if not already present
                        if item.ecs_id not in tree.nodes:
                            tree.add_entity(item)
                        
                        # Add the appropriate edge type
                        process_entity_reference(
                            tree=tree,
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
    for entity_id in tree.nodes:
        if entity_id not in ancestry_paths:
            raise ValueError(f"Entity {entity_id} does not have an ancestry path")
    
    return tree

def get_non_entity_attributes(entity: "Entity") -> Dict[str, Any]:
    """
    Get all non-entity attributes of an entity.
    
    This includes primitive types and containers that don't contain entities.
    Identity fields and entity-containing fields are excluded.
    
    Args:
        entity: The entity to inspect
        
    Returns:
        Dict[str, Any]: Dictionary of field_name -> field_value for non-entity fields
    """
    non_entity_attrs = {}
    
    # Check all fields
    for field_name in entity.model_fields:
        # Use our helper to check if this is a non-entity field
        if get_pydantic_field_type_entities(entity, field_name, detect_non_entities=True) is True:
            non_entity_attrs[field_name] = getattr(entity, field_name)
    
    return non_entity_attrs


def compare_non_entity_attributes(entity1: "Entity", entity2: "Entity") -> bool:
    """
    Compare non-entity attributes between two entities.
    
    Args:
        entity1: First entity to compare
        entity2: Second entity to compare
        
    Returns:
        bool: True if the entities have different non-entity attributes, False if they're the same
    """
    # Get non-entity attributes for both entities
    attrs1 = get_non_entity_attributes(entity1)
    attrs2 = get_non_entity_attributes(entity2)
    
    # Different set of non-entity attributes
    if set(attrs1.keys()) != set(attrs2.keys()):
        return True
    
    # Empty sets of attributes means no changes
    if not attrs1 and not attrs2:
        return False
    
    # Compare values of non-entity attributes
    for field_name, value1 in attrs1.items():
        value2 = attrs2[field_name]
        
        # Direct comparison for non-entity values
        if value1 != value2:
            return True
    
    # No differences found
    return False


def find_modified_entities(
    new_tree: EntityTree,
    old_tree: EntityTree,
    greedy: bool = True,
    debug: bool = False
) -> Union[Set[UUID], Tuple[Set[UUID], Dict[str, Any]]]:
    """
    Find entities that have been modified between two trees.
    
    Uses a set-based approach to identify changes:
    1. Compares node sets to identify added/removed entities
    2. Compares edge sets to identify moved entities (same entity, different parent)
    3. Checks attribute changes only for entities not already marked for versioning
    
    Args:
        new_tree: The new entity tree
        old_tree: The old tree (from storage)
        greedy: If True, stops checking parents once an entity is marked for change
        debug: If True, collects and returns debugging information
        
    Returns:
        If debug=False:
            Set[UUID]: Set of entity ecs_ids that need new versions
        If debug=True:
            Tuple[Set[UUID], Dict[str, Any]]: Set of modified entity IDs and debugging info
    """
    # Set to track entities that need versioning
    modified_entities = set()
    
    # For debugging
    comparison_count = 0
    moved_entities = set()
    unchanged_entities = set()
    
    # Step 1: Compare node sets to identify added/removed entities
    new_entity_ids = set(new_tree.nodes.keys())
    old_entity_ids = set(old_tree.nodes.keys())
    
    added_entities = new_entity_ids - old_entity_ids
    removed_entities = old_entity_ids - new_entity_ids
    common_entities = new_entity_ids & old_entity_ids
    
    # Mark all added entities and their ancestry paths for versioning
    for entity_id in added_entities:
        path = new_tree.get_ancestry_path(entity_id)
        modified_entities.update(path)
    
    # Step 2: Compare edge sets to identify moved entities
    # Collect all parent-child relationships in both trees
    new_edges = set()
    old_edges = set()
    
    for (source_id, target_id), edge in new_tree.edges.items():
        new_edges.add((source_id, target_id))
        
    for (source_id, target_id), edge in old_tree.edges.items():
        old_edges.add((source_id, target_id))
    
    # Find edges that exist in new tree but not in old tree
    added_edges = new_edges - old_edges
    # Find edges that exist in old tree but not in new tree
    removed_edges = old_edges - new_edges
    
    # Identify moved entities - common entities with different connections
    for source_id, target_id in added_edges:
        # If target is a common entity but has a new connection
        if target_id in common_entities:
            # Check if this entity has a different parent in the old tree
            old_parents = set()
            for old_source_id, old_target_id in old_edges:
                if old_target_id == target_id:
                    old_parents.add(old_source_id)
            
            new_parents = set()
            for new_source_id, new_target_id in new_edges:
                if new_target_id == target_id:
                    new_parents.add(new_source_id)
            
            # If the entity has different parents, it's been moved
            if old_parents != new_parents:
                moved_entities.add(target_id)
                
                # Mark the entire path for the moved entity for versioning
                path = new_tree.get_ancestry_path(target_id)
                modified_entities.update(path)
    
    # Step 3: Check attribute changes for remaining common entities
    # Create a list of remaining entities sorted by path length
    remaining_entities = []
    
    for entity_id in common_entities:
        if entity_id not in modified_entities and entity_id not in moved_entities:
            # Get path length as priority (longer paths = higher priority)
            path_length = len(new_tree.get_ancestry_path(entity_id))
            remaining_entities.append((path_length, entity_id))
    
    # Sort by path length (descending) - process leaf nodes first
    remaining_entities.sort(reverse=True)
    
    # Process entities in order of path length
    for _, entity_id in remaining_entities:
        # Skip if already processed
        if entity_id in modified_entities or entity_id in unchanged_entities:
            continue
        
        # Get the entities to compare
        new_entity = new_tree.get_entity(entity_id)
        old_entity = old_tree.get_entity(entity_id)
        
        # Ensure both entities are not None before comparing
        if new_entity is None or old_entity is None:
            # If either entity is None, mark as changed
            path = new_tree.get_ancestry_path(entity_id)
            modified_entities.update(path)
            continue
            
        # Compare the non-entity attributes
        comparison_count += 1
        has_changes = compare_non_entity_attributes(new_entity, old_entity)
        
        if has_changes:
            # Mark the entire path as changed
            path = new_tree.get_ancestry_path(entity_id)
            modified_entities.update(path)
            
            # If greedy, we can skip processing parents now
            if greedy:
                continue
        else:
            # Mark just this entity as unchanged
            unchanged_entities.add(entity_id)
    
    # Return the debug info if requested
    if debug:
        return modified_entities, {
            "comparison_count": comparison_count,
            "added_entities": added_entities,
            "removed_entities": removed_entities,
            "moved_entities": moved_entities,
            "unchanged_entities": unchanged_entities
        }
    
    return modified_entities



def update_tree_mappings_after_versioning(tree: EntityTree, id_mapping: Dict[UUID, UUID]) -> None:
    """
    Update all tree mappings to use new ECS IDs after versioning.
    
    This fixes the tree desynchronization bug where tree mappings still reference
    old ECS IDs after entities have been updated with new IDs.
    
    Args:
        tree: The EntityTree to update
        id_mapping: Maps old_ecs_id -> new_ecs_id for all updated entities
    """
    
    # Step 1: Update nodes mapping
    updated_nodes = {}
    for old_ecs_id, entity in tree.nodes.items():
        new_ecs_id = id_mapping.get(old_ecs_id, old_ecs_id)
        updated_nodes[new_ecs_id] = entity
    tree.nodes = updated_nodes
    
    # Step 2: Update edges mapping and edge object IDs
    updated_edges = {}
    for (old_source_id, old_target_id), edge in tree.edges.items():
        new_source_id = id_mapping.get(old_source_id, old_source_id)
        new_target_id = id_mapping.get(old_target_id, old_target_id)
        
        # Update edge object's IDs
        edge.source_id = new_source_id
        edge.target_id = new_target_id
        
        updated_edges[(new_source_id, new_target_id)] = edge
    tree.edges = updated_edges
    
    # Step 3: Update outgoing_edges mapping
    updated_outgoing = defaultdict(list)
    for old_source_id, target_list in tree.outgoing_edges.items():
        new_source_id = id_mapping.get(old_source_id, old_source_id)
        new_target_list = [id_mapping.get(tid, tid) for tid in target_list]
        updated_outgoing[new_source_id] = new_target_list
    tree.outgoing_edges = updated_outgoing
    
    # Step 4: Update incoming_edges mapping
    updated_incoming = defaultdict(list)
    for old_target_id, source_list in tree.incoming_edges.items():
        new_target_id = id_mapping.get(old_target_id, old_target_id)
        new_source_list = [id_mapping.get(sid, sid) for sid in source_list]
        updated_incoming[new_target_id] = new_source_list
    tree.incoming_edges = updated_incoming
    
    # Step 5: Update ancestry_paths mapping
    updated_ancestry_paths = {}
    for old_entity_id, path in tree.ancestry_paths.items():
        new_entity_id = id_mapping.get(old_entity_id, old_entity_id)
        new_path = [id_mapping.get(pid, pid) for pid in path]
        updated_ancestry_paths[new_entity_id] = new_path
    tree.ancestry_paths = updated_ancestry_paths
    
    # Step 6: Update live_id_to_ecs_id mapping
    for live_id, old_ecs_id in tree.live_id_to_ecs_id.items():
        if old_ecs_id in id_mapping:
            tree.live_id_to_ecs_id[live_id] = id_mapping[old_ecs_id]
    
    # Step 7: Update tree's root_ecs_id if the root was versioned
    if tree.root_ecs_id in id_mapping:
        tree.root_ecs_id = id_mapping[tree.root_ecs_id]


def rebuild_tree_from_scratch_after_versioning(tree: EntityTree) -> EntityTree:
    """
    EXPENSIVE: Completely rebuild the tree from scratch using current entity state.
    
    This is the worst-case scenario method that does a full graph traversal
    and rebuilds all tree mappings from the ground up. Should only be used
    for testing consistency against the optimized update method.
    
    Args:
        tree: The EntityTree to rebuild
        
    Returns:
        New EntityTree built from scratch with current entity state
    """
    # Get the root entity from current tree
    root_entity = tree.get_entity(tree.root_ecs_id)
    if root_entity is None:
        raise ValueError(f"Root entity {tree.root_ecs_id} not found in tree")
    
    # Completely rebuild tree from scratch
    rebuilt_tree = build_entity_tree(root_entity)
    
    # Preserve original lineage_id (build_entity_tree might use entity's current lineage)
    rebuilt_tree.lineage_id = tree.lineage_id
    
    return rebuilt_tree


def compare_tree_structures(tree1: EntityTree, tree2: EntityTree, comparison_name: str = "") -> bool:
    """
    Compare two EntityTree structures to verify they're equivalent.
    
    Used to test that the optimized update method produces the same result
    as the expensive full rebuild method.
    
    Args:
        tree1: First tree to compare
        tree2: Second tree to compare
        comparison_name: Optional name for debugging output
        
    Returns:
        True if trees are structurally equivalent, False otherwise
    """
    try:
        # Check basic properties
        assert tree1.root_ecs_id == tree2.root_ecs_id, f"Root ECS IDs differ: {tree1.root_ecs_id} vs {tree2.root_ecs_id}"
        assert tree1.lineage_id == tree2.lineage_id, f"Lineage IDs differ: {tree1.lineage_id} vs {tree2.lineage_id}"
        assert tree1.node_count == tree2.node_count, f"Node counts differ: {tree1.node_count} vs {tree2.node_count}"
        assert tree1.edge_count == tree2.edge_count, f"Edge counts differ: {tree1.edge_count} vs {tree2.edge_count}"
        
        # Check nodes mapping
        assert set(tree1.nodes.keys()) == set(tree2.nodes.keys()), "Node keys differ"
        for ecs_id in tree1.nodes:
            entity1 = tree1.nodes[ecs_id]
            entity2 = tree2.nodes[ecs_id]
            assert entity1.ecs_id == entity2.ecs_id, f"Entity ECS IDs differ for {ecs_id}"
            assert entity1.live_id == entity2.live_id, f"Entity live IDs differ for {ecs_id}"
        
        # Check edges mapping
        assert set(tree1.edges.keys()) == set(tree2.edges.keys()), "Edge keys differ"
        for edge_key in tree1.edges:
            edge1 = tree1.edges[edge_key]
            edge2 = tree2.edges[edge_key]
            assert edge1.source_id == edge2.source_id, f"Edge source IDs differ for {edge_key}"
            assert edge1.target_id == edge2.target_id, f"Edge target IDs differ for {edge_key}"
            assert edge1.field_name == edge2.field_name, f"Edge field names differ for {edge_key}"
            assert edge1.edge_type == edge2.edge_type, f"Edge types differ for {edge_key}"
        
        # Check ancestry paths
        assert set(tree1.ancestry_paths.keys()) == set(tree2.ancestry_paths.keys()), "Ancestry path keys differ"
        for ecs_id in tree1.ancestry_paths:
            path1 = tree1.ancestry_paths[ecs_id]
            path2 = tree2.ancestry_paths[ecs_id]
            assert path1 == path2, f"Ancestry paths differ for {ecs_id}: {path1} vs {path2}"
        
        # Check outgoing edges
        assert set(tree1.outgoing_edges.keys()) == set(tree2.outgoing_edges.keys()), "Outgoing edge keys differ"
        for ecs_id in tree1.outgoing_edges:
            targets1 = set(tree1.outgoing_edges[ecs_id])
            targets2 = set(tree2.outgoing_edges[ecs_id])
            assert targets1 == targets2, f"Outgoing targets differ for {ecs_id}: {targets1} vs {targets2}"
        
        # Check incoming edges
        assert set(tree1.incoming_edges.keys()) == set(tree2.incoming_edges.keys()), "Incoming edge keys differ"
        for ecs_id in tree1.incoming_edges:
            sources1 = set(tree1.incoming_edges[ecs_id])
            sources2 = set(tree2.incoming_edges[ecs_id])
            assert sources1 == sources2, f"Incoming sources differ for {ecs_id}: {sources1} vs {sources2}"
        
        # Check live_id mappings
        assert tree1.live_id_to_ecs_id == tree2.live_id_to_ecs_id, "Live ID mappings differ"
        
        if comparison_name:
            print(f"  ✅ Tree structures match for {comparison_name}")
        return True
        
    except AssertionError as e:
        if comparison_name:
            print(f"  ❌ Tree structures differ for {comparison_name}: {e}")
        return False


def validate_tree_consistency_after_versioning(tree: EntityTree, test_name: str = "") -> bool:
    """
    Validate that all tree mappings are consistent after versioning.
    
    Args:
        tree: The EntityTree to validate
        test_name: Optional name for debugging output
        
    Returns:
        True if tree is consistent, False otherwise
    """
    try:
        # Check 1: All entities have their ecs_id as key in nodes
        for ecs_id, entity in tree.nodes.items():
            assert entity.ecs_id == ecs_id, f"Entity ecs_id {entity.ecs_id} != nodes key {ecs_id}"
        
        # Check 2: All edge source/target IDs exist in nodes
        for (source_id, target_id), edge in tree.edges.items():
            assert source_id in tree.nodes, f"Edge source {source_id} not in nodes"
            assert target_id in tree.nodes, f"Edge target {target_id} not in nodes"
            assert edge.source_id == source_id, f"Edge source_id {edge.source_id} != key {source_id}"
            assert edge.target_id == target_id, f"Edge target_id {edge.target_id} != key {target_id}"
        
        # Check 3: All ancestry path IDs exist in nodes
        for entity_id, path in tree.ancestry_paths.items():
            assert entity_id in tree.nodes, f"Ancestry entity {entity_id} not in nodes"
            for path_id in path:
                assert path_id in tree.nodes, f"Path entity {path_id} not in nodes"
        
        # Check 4: Root entity exists in nodes
        assert tree.root_ecs_id in tree.nodes, f"Root {tree.root_ecs_id} not in nodes"
        
        # Check 5: All live_id mappings point to valid ecs_ids
        for live_id, ecs_id in tree.live_id_to_ecs_id.items():
            assert ecs_id in tree.nodes, f"Live ID {live_id} points to non-existent ecs_id {ecs_id}"
        
        # Check 6: Outgoing/incoming edges consistency
        for source_id, targets in tree.outgoing_edges.items():
            assert source_id in tree.nodes, f"Outgoing source {source_id} not in nodes"
            for target_id in targets:
                assert target_id in tree.nodes, f"Outgoing target {target_id} not in nodes"
                assert (source_id, target_id) in tree.edges, f"Outgoing edge ({source_id}, {target_id}) not in edges"
        
        for target_id, sources in tree.incoming_edges.items():
            assert target_id in tree.nodes, f"Incoming target {target_id} not in nodes"
            for source_id in sources:
                assert source_id in tree.nodes, f"Incoming source {source_id} not in nodes"
                assert (source_id, target_id) in tree.edges, f"Incoming edge ({source_id}, {target_id}) not in edges"
        
        if test_name:
            print(f"  ✅ Tree consistency valid for {test_name}")
        return True
        
    except AssertionError as e:
        if test_name:
            print(f"  ❌ Tree consistency failed for {test_name}: {e}")
        return False




class EntityRegistry():
    """ A registry for tree entities, is mantains a versioned collection of all entities in the system
    it mantains 
    1) a treeregistry indexed by root_ecs_id UUID --> EntityTree
    2) a lineage registry indexed by lineage_id UUID --> List[root_ecs_id UUID]
    3) a live_id registry indexed by live_id UUID --> Entity [this is used to navigate from live python entity to their root entity when recosntructing a tree from a sub-entity]
    4) a type_registry indexed by entity_type --> List[lineage_id UUID] which is used to get all entities of a given type
    5) a ecs_id_to_root_id registry indexed by ecs_id UUID --> root_ecs_id UUID which is used to get the root_ecs_id for any given ecs_id
    """
    tree_registry: Dict[UUID, EntityTree] = {}
    lineage_registry: Dict[UUID, List[UUID]] = {}
    live_id_registry: Dict[UUID, "Entity"] = {}
    ecs_id_to_root_id: Dict[UUID, UUID] = {}
    type_registry: Dict[Type["Entity"], List[UUID]] = {}
    
    @classmethod
    def register_entity_tree(cls, entity_tree: EntityTree) -> None:
        """ Register an entity tree in the registry when an entity tree is registered in the tree registry its
        1) its root_ecs_id is added to the lineage_history
        2) the entities in the tree are referenced by their live id in the live_id_registry 
        3) the tree is added to the tree_registry with its root_ecs_id as key
        """
        if entity_tree.root_ecs_id in cls.tree_registry:
            raise ValueError("entity tree already registered")
        
        cls.tree_registry[entity_tree.root_ecs_id] = entity_tree
        for sub_entity in entity_tree.nodes.values():
            cls.live_id_registry[sub_entity.live_id] = sub_entity
            cls.ecs_id_to_root_id[sub_entity.ecs_id] = entity_tree.root_ecs_id
        if entity_tree.lineage_id not in cls.lineage_registry:
            cls.lineage_registry[entity_tree.lineage_id] = [entity_tree.root_ecs_id]
        else:
            cls.lineage_registry[entity_tree.lineage_id].append(entity_tree.root_ecs_id)
        root_entity = entity_tree.get_entity(entity_tree.root_ecs_id)
        if root_entity is not None:
            if root_entity.__class__ not in cls.type_registry:
                cls.type_registry[root_entity.__class__] = [entity_tree.lineage_id]
            else:
                cls.type_registry[root_entity.__class__].append(entity_tree.lineage_id)
        else:
            raise ValueError("root entity not found in entity tree")


    @classmethod
    @emit_events(
        creating_factory=lambda cls, entity: EntityRegistrationEvent(
            subject_type=type(entity),
            subject_id=entity.ecs_id,
            process_name="entity_registration",
            entity_type=type(entity).__name__,
            entity_id=entity.ecs_id,
            is_root_entity=entity.is_root_entity(),
            has_existing_tree=False,
            registration_type="new_entity",
            expected_tree_nodes=None,
            expected_tree_edges=None
        ),
        created_factory=lambda result, cls, entity: EntityRegisteredEvent(
            subject_type=type(entity),
            subject_id=entity.ecs_id,
            process_name="entity_registration",
            entity_type=type(entity).__name__,
            entity_id=entity.ecs_id,
            registration_successful=True,
            tree_node_count=0,  # Will be populated by future enhancement
            tree_edge_count=0,  # Will be populated by future enhancement
            tree_max_depth=0,   # Will be populated by future enhancement
            new_lineage_created=True,
            type_registry_updated=True
        )
    )
    def register_entity(cls, entity: "Entity") -> None:
        """ Register an entity in the registry when an entity is registered in the tree registry its
         1) its tree is constructed and indexed by the root_ecs_id
         2) the entiteis in the tree are referenced by their live id in the live_id_registry 
         3) the tree is deepcopied and the deepcopy is added to tree_registy with its root_ecs_id as key
         3) the root_ecs_id is added to the lineage_history
          we can only register root entities for now """
        
        if entity.root_ecs_id is  None:
            raise ValueError("can only register root entities with a root_ecs_id for now")
        elif not entity.is_root_entity():
            raise ValueError("can only register root entities for now")
        
        entity_tree = build_entity_tree(entity)
        cls.register_entity_tree(entity_tree)

    @classmethod            
    def get_stored_tree(cls, root_ecs_id: UUID) -> Optional[EntityTree]:
        """ Get the tree for a given root_ecs_id """
        stored_tree= cls.tree_registry.get(root_ecs_id, None)
        if stored_tree is None:
            return None
        else:
            new_tree = stored_tree.model_copy(deep=True)
            new_tree.update_live_ids() #this are new python objects with new live ids
            return new_tree
            
    @classmethod
    def get_stored_entity(cls, root_ecs_id: UUID, ecs_id: UUID) -> Optional["Entity"]:
        """ Get the entity for a given root_ecs_id and ecs_id """
        tree = cls.get_stored_tree(root_ecs_id)
        if tree is None:
            return None
        entity = tree.get_entity(ecs_id)
        if entity is None:
            return None
        else:
            return entity
        
    @classmethod
    def get_stored_tree_from_entity(cls, entity: "Entity") -> Optional[EntityTree]:
        """ Get the tree for a given entity """
        if not entity.root_ecs_id:
            raise ValueError("entity has no root_ecs_id")
        return cls.get_stored_tree(entity.root_ecs_id)
        
    @classmethod
    def get_live_entity(cls, live_id: UUID) -> Optional["Entity"]:
        """ Get the entity for a given live_id """
        return cls.live_id_registry.get(live_id, None)
    
    @classmethod
    def get_live_root_from_entity(cls, entity: "Entity") -> Optional["Entity"]:
        """ Get the root entity for a given entity """
        if not entity.root_live_id:
            raise ValueError("entity has no root_live_id")
        return cls.get_live_entity(entity.root_live_id)
    
    @classmethod
    def get_live_root_from_live_id(cls, live_id: UUID) -> Optional["Entity"]:
        """ Get the root entity for a given live_id """
        entity = cls.get_live_entity(live_id)
        if entity is None:
            return None
        else:
            return cls.get_live_root_from_entity(entity)
        
    @classmethod
    @emit_events(
        creating_factory=lambda cls, entity, force_versioning=False: EntityVersioningEvent(
            subject_type=type(entity),
            subject_id=entity.ecs_id,
            entity_type=type(entity).__name__,
            entity_id=entity.ecs_id,
            force_versioning=force_versioning,
            has_stored_version=cls.get_stored_tree(entity.root_ecs_id) is not None if entity.root_ecs_id else False,
            change_detection_required=not force_versioning,
            expected_changes=None
        ),
        created_factory=lambda result, cls, entity, force_versioning=False: EntityVersionedEvent(
            subject_type=type(entity),
            subject_id=entity.ecs_id,
            entity_type=type(entity).__name__,
            entity_id=entity.ecs_id,
            version_created=result,
            entities_modified=0,  # Will be populated by future enhancement
            new_ids_created=[],   # Will be populated by future enhancement
            tree_mappings_updated=result,
            versioning_duration_ms=None
        )
    )
    def version_entity(cls, entity: "Entity", force_versioning: bool = False) -> bool:
        """ Core function to version an entity, currently working only for root entities, what this function does is:
        1) check if function is registered , if not delegate to reigister()
        2) get the stored tree snapshot for the entity
        3) compute the new tree
        4) compute the diff between the two trees if no diff return False
        5) update the ecs_id for all changed entities in the tree, update their root_ecs_id,
        6) register the new tree in the tree_registry under the new root_ecs_id key mantaining the lineage intact"""
        """ Version an entity """
        
        # Handle None entity gracefully
        if entity is None:
            return False  # No versioning needed for None entity
            
        if not entity.root_ecs_id:
            raise ValueError("entity has no root_ecs_id for versioning we only support versioning of root entities for now")
        
        old_tree = cls.get_stored_tree(entity.root_ecs_id)
        if old_tree is None:
            cls.register_entity(entity)
            return True
        else:
            new_tree = build_entity_tree(entity)
            if force_versioning:
                modified_entities = new_tree.nodes.keys()
            else:
                modified_entities = list(find_modified_entities(new_tree=new_tree, old_tree=old_tree))
        
            typed_entities = [entity for entity in modified_entities if isinstance(entity, UUID)]
            
            if len(typed_entities) > 0:
                if new_tree.root_ecs_id not in typed_entities:
                    raise ValueError("if any entity is modified the root entity must be modified something went wrong")
                # first we fork the root entity
                # forking the root entity will create a new root_ecs_id then we fork all the modified entities with the new root_ecs_id as input
                current_root_ecs_id = new_tree.root_ecs_id
                root_entity = new_tree.get_entity(current_root_ecs_id)
                if root_entity is None:
                    raise ValueError("root entity not found in new tree, something went very wrong")
                root_entity.update_ecs_ids()
                new_root_ecs_id = root_entity.ecs_id
                root_entity_live_id = root_entity.live_id
                assert new_root_ecs_id is not None and new_root_ecs_id != current_root_ecs_id
                
                # Build ID mapping for tracking changes
                id_mapping = {current_root_ecs_id: new_root_ecs_id}
                
                # Update the nodes dictionary to use the new root entity ID
                new_tree.nodes.pop(current_root_ecs_id)
                new_tree.nodes[new_root_ecs_id] = root_entity
                
                # now we fork all the modified entities with the new root_ecs_id as input
                #remove the old root_ecs_id from the typed_entities
                typed_entities.remove(current_root_ecs_id)
                for modified_entity_id in typed_entities:
                    modified_entity = new_tree.get_entity(modified_entity_id)
                    if modified_entity is not None:
                        #here we could have some modified entitiyes being entities that have been removed from the tree so we get nones
                        old_ecs_id = modified_entity.ecs_id
                        modified_entity.update_ecs_ids(new_root_ecs_id, root_entity_live_id)
                        new_ecs_id = modified_entity.ecs_id
                        id_mapping[old_ecs_id] = new_ecs_id
                    else:
                        #later here we will handle the case where the entity has been moved to a different tree or prompoted to it's own tree
                        print(f"modified entity {modified_entity_id} not found in new tree, something went wrong")
                
                # Update tree mappings to be consistent with new ECS IDs
                update_tree_mappings_after_versioning(new_tree, id_mapping)
                
                # Update the tree's lineage_id to match the updated root entity
                new_tree.lineage_id = root_entity.lineage_id
                
                cls.register_entity_tree(new_tree)
            return True            



class Entity(BaseModel):
    ecs_id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    live_id: UUID = Field(default_factory=uuid4, description="Live/warm identifier")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    forked_at: Optional[datetime] = Field(default=None, description="Timestamp of the last fork")
    previous_ecs_id: Optional[UUID] = Field(default=None, description="Previous ecs_id before forking")
    lineage_id: UUID = Field(default_factory=uuid4)
    old_ids: List[UUID] = Field(default_factory=list)
    old_ecs_id: Optional[UUID] = Field(default=None, description="Last ecs_id before forking")  # Added this field
    root_ecs_id: Optional[UUID] = Field(default=None, description="The ecs_id of the root entity of this entity's tree")
    root_live_id: Optional[UUID] = Field(default=None, description="The live_id of the root entity of this entity's tree")
    from_storage: bool = Field(default=False, description="Whether the entity was loaded from storage, used to prevent re-registration")
    untyped_data: str = Field(default="", description="Default data container for untyped data, string diff will be used to detect changes")
    attribute_source: Dict[str, Union[Optional[UUID], List[UUID], List[Optional[UUID]], List[None], Dict[str, Optional[UUID]]]] = Field(
        default_factory=dict, 
        description="Tracks the source entity for each attribute"
    )
    
    # Phase 4 sibling relationship tracking fields
    derived_from_function: Optional[str] = Field(default=None, description="Function that created or modified this entity")
    derived_from_execution_id: Optional[UUID] = Field(default=None, description="Execution ID that created or modified this entity")
    sibling_output_entities: List[UUID] = Field(default_factory=list, description="Other entities created by the same function execution")
    output_index: Optional[int] = Field(default=None, description="Position in tuple output if part of multi-entity return")

    @model_validator(mode='after')
    def validate_attribute_source(self) -> Self:
        """
        Validates that the attribute_source dictionary only contains keys 
        that match fields in the model. Initializes the dictionary if not present,
        and adds missing fields with source=None to indicate initialization from Python.
        
        For container fields (List, Dict), initializes appropriate nested structures:
        - Lists: List[Optional[UUID]] initialized to same length as field value with None
        - Dicts: Dict[str, Optional[UUID]] initialized with None for each key
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
        
        # Initialize missing fields with appropriate structure based on field type
        for field_name in valid_fields:
            field_value = getattr(self, field_name)
            
            # Skip if already initialized
            if field_name in self.attribute_source:
                continue
                
            # Handle different field types
            if isinstance(field_value, list):
                # Initialize list of None values matching length of field_value
                # Create a properly typed list that satisfies type checking
                none_value: Optional[UUID] = None
                self.attribute_source[field_name] = [none_value] * len(field_value)
            elif isinstance(field_value, dict):
                # Initialize dict with None values for each key
                typed_dict: Dict[str, Optional[UUID]] = {str(k): None for k in field_value.keys()}
                self.attribute_source[field_name] = typed_dict
            else:
                # Regular field gets simple None value
                self.attribute_source[field_name] = None
        
        # Validate existing container fields have correct structure
        for field_name, source_value in self.attribute_source.items():
            field_value = getattr(self, field_name)
            
            if isinstance(field_value, list):
                # Ensure source is a list of the same length
                if not isinstance(source_value, list) or len(source_value) != len(field_value):
                    none_value: Optional[UUID] = None 
                    self.attribute_source[field_name] = [none_value] * len(field_value)
            elif isinstance(field_value, dict):
                # Ensure source is a dict with all current keys
                if not isinstance(source_value, dict):
                    self.attribute_source[field_name] = {str(k): None for k in field_value.keys()}
                else:
                    # Add any missing keys
                    source_dict = source_value  # For type clarity
                    if isinstance(source_dict, dict):  # Type guard for type checker
                        for key in field_value.keys():
                            str_key = str(key)  # Convert key to string to ensure dict compatibility
                            if str_key not in source_dict:
                                source_dict[str_key] = None
        
        return self

    def _hash_str(self) -> str:
        """
        Generate a hash string from identity fields.
        
        With the immutability approach, this includes only the persistent identity fields
        (ecs_id and root_ecs_id), not the temporary runtime ones (live_id and root_live_id).
        """
        return f"{self.ecs_id}-{self.root_ecs_id}"
        
    def __hash__(self) -> int:
        """
        Make entity hashable using a string representation of persistent identity fields.
        """
        return hash(self._hash_str())
        
    def __eq__(self, other: object) -> bool:
        """
        Simple equality comparison using persistent identity fields.
        
        This ensures that when comparing entities from different retrievals
        (which will have different live_ids), we still consider them equal
        if they represent the same persistent entity (same ecs_id).
        """
        if not isinstance(other, Entity):
            return False
        return self._hash_str() == other._hash_str()

    
    def is_root_entity(self) -> bool:
        """
        Check if the entity is the root of its tree.
        """
        return self.root_ecs_id == self.ecs_id
    
    def is_orphan(self) -> bool:
        """
        Check if the entity is an orphan.
        """
        return self.root_ecs_id is None or self.root_live_id is None
        
    
    def update_ecs_ids(self, new_root_ecs_id: Optional[UUID] = None, root_entity_live_id: Optional[UUID] = None) -> None:
        """
        Assign new ecs_id 
        Assign a forked_at timestamp
        Updates previous_ecs_id to the previous ecs_id
        Adds the previous ecs_id to old_ids
        If new_root_ecs_id is provided, updates root_ecs_id to the new value
        If root_entity_live_id is provided, updates root_live_id to the new value this requires new_root_ecs_id to be provided
        """
        old_ecs_id = self.ecs_id
        new_ecs_id = uuid4()
        is_root_entity = self.is_root_entity()
        self.ecs_id = new_ecs_id
        self.forked_at = datetime.now(timezone.utc)
        self.old_ecs_id = old_ecs_id
        self.old_ids.append(old_ecs_id)
        if new_root_ecs_id:
            self.root_ecs_id = new_root_ecs_id
        if root_entity_live_id and not new_root_ecs_id:
            raise ValueError("if root_entity_live_id is provided new_root_ecs_id must be provided")
        elif root_entity_live_id:
            self.root_live_id = root_entity_live_id
        if is_root_entity:
            self.root_ecs_id = new_ecs_id
    
    def get_live_root_entity(self) -> Optional["Entity"]: 
        """
        This method will use the registry to get the live python object of the root entity of the tree
        """
        if self.is_root_entity():
            return self
        elif self.root_live_id is None:
            return None
        else:
            return EntityRegistry.get_live_entity(self.root_live_id)
    
    def get_stored_root_entity(self) -> Optional["Entity"]: 
        """
        This method will use the registry to get the stored reference of the root entity of the tree
        """
        if self.is_root_entity():
            return self
        elif self.root_ecs_id is None:
            return None
        else:
            return EntityRegistry.get_stored_entity(self.root_ecs_id,self.root_ecs_id)
        
    def get_stored_version(self) -> Optional["Entity"]:
        """
        This method will use the registry to get the stored reference of the entity using the
        ecs_id and root_ecs_id of the entity, this may differet from the carrent live object
        """
        if not self.root_ecs_id:
            return None
        else:
            return EntityRegistry.get_stored_entity(self.root_ecs_id,self.ecs_id)

    def get_tree(self, recompute: bool = False) -> Optional[EntityTree]: 
        """
        This method will use the registry to get the whole tree of the entity if 
        recompute is True it will recompute the tree from the live root entity, this is different then versioning
        otherwise it will return the cached tree based on the ecs_id of the root entity
        """
        if recompute and self.is_root_entity():
            return build_entity_tree(self)
        elif recompute and not self.is_root_entity() and self.root_live_id is not None:
            live_root_entity = self.get_live_root_entity()
            if live_root_entity is None:
                raise ValueError("live root entity not found")
            return build_entity_tree(live_root_entity)
        elif self.root_ecs_id is not None:
            return EntityRegistry.get_stored_tree(self.root_ecs_id)
        else:
            return None
  

    @emit_events(
        creating_factory=lambda self: EntityPromotionEvent(
            subject_type=type(self),
            subject_id=self.ecs_id,
            from_state="child_entity",
            to_state="root_entity",
            transition_reason="promotion",
            entity_type=type(self).__name__,
            entity_id=self.ecs_id,
            was_orphan=self.is_orphan(),
            had_root_reference=self.root_ecs_id is not None,
            current_root_id=self.root_ecs_id,
            promotion_reason="manual"
        ),
        created_factory=lambda result, self: EntityPromotedEvent(
            subject_type=type(self),
            subject_id=self.ecs_id,
            from_state="child_entity",
            to_state="root_entity",
            transition_reason="promotion",
            entity_type=type(self).__name__,
            entity_id=self.ecs_id,
            promotion_successful=True,
            new_root_id=self.ecs_id,
            registry_updated=True,
            ids_updated=True,
            promotion_duration_ms=None
        )
    )
    def promote_to_root(self) -> None:
        """
        Promote the entity to the root of its tree
        """
        if self.root_ecs_id is None or self.root_live_id is None:
            # Case 2: Entity is not attached to anything, promote to root
            self.root_ecs_id = self.ecs_id
            self.root_live_id = self.live_id
        
        elif self.root_ecs_id != self.ecs_id and self.root_live_id != self.live_id:
            self.root_ecs_id = self.ecs_id
            self.root_live_id = self.live_id
            self.update_ecs_ids()
        EntityRegistry.register_entity(self)
    
    @emit_events(
        creating_factory=lambda self: EntityDetachmentEvent(
            subject_type=type(self),
            subject_id=self.ecs_id,
            from_state="attached_entity",
            to_state="detached_entity",
            transition_reason="detachment",
            entity_type=type(self).__name__,
            entity_id=self.ecs_id,
            current_root_id=self.root_ecs_id,
            detachment_scenario="manual_detach",
            requires_promotion=not self.is_root_entity()
        ),
        created_factory=lambda result, self: EntityDetachedEvent(
            subject_type=type(self),
            subject_id=self.ecs_id,
            from_state="attached_entity",
            to_state="detached_entity",
            transition_reason="detachment",
            entity_type=type(self).__name__,
            entity_id=self.ecs_id,
            detachment_successful=True,
            was_promoted=True,
            new_root_id=self.ecs_id,
            old_tree_versioned=True,
            detachment_duration_ms=None
        )
    )
    def detach(self) -> None:
        """
        This has to be called after the entity has been removed from its parent python object
        the scenarios are that 
        1) entity is already a root entity and nothing has to be done, trigger versioning
        2) the entity is currently already has root_ecs_id and root_live_id  set to None--> promote to root and register 
        3) the tree does not exist or the parent is not in teh registry --> the entity is not attached to anything and we can just update the ecs_id and register
        3) the entity has root_ecs_id and root_live_id but is not present in the tree --> physically is detached from the tree, we only need to update the ecs_id and register
        4) the entity has root_ecs_id and root_live_id and is present in the tree --> do nothing python has to physically remove the entity from the parent object
        We leave out the case where the entity is a sub entity of a new root entity which is not the root_entity of the current entity. In that case the attach method should be used instead. 
        """
        if self.is_root_entity():
            #case 1 is already a root entity we just version it
            EntityRegistry.version_entity(self)
        elif self.root_ecs_id is None or self.root_live_id is None:
            #case 2 the entity is not attached to anything and we can just update the ecs_id and register
            self.promote_to_root()
        else:
            tree = self.get_tree(recompute=True)
            
            if tree is None:
                #case 3 the tree does not exist or the parent is not in teh registry --> the entity is not attached to anything and we can just update the ecs_id and register
                self.promote_to_root()
            else:
                tree_root_entity = tree.get_entity(self.root_ecs_id)
                if self.ecs_id not in tree.nodes:
                    #case 4 the entity is not present in the tree and we can just update the ecs_id and register
                    self.promote_to_root()
                if tree_root_entity is not None:
                    #we version teh tree root entity to ensure that its' lates version is stored
                    EntityRegistry.version_entity(tree_root_entity) 
  
        #thi
        

    def add_to(self, new_entity: "Entity", field_name: str, copy= False, detach_target: bool = False) -> None:
        """
        just a stub for now
        This method will move the entity to a new root entity and update the attribute_source to reflect the new root entity
        1) get the attribute field from the new entity and type check
        2) it if it is the correct entity type or a container of the correct entity type
        3) if it is a container we need plan forr adding to the container
        4) if it is an entity we need to check if there already is an entity in the field we are moving to and detach if detach_target is True
        5) if copy is True we need to version self root entity and get the copy to attach from this versioned entity from the storage
        6) if copy is False we ned to pop the entity from its parent in the tree (or from the container)
        6) we detach our working object (self or the copy) and set the new entity to the field and update its source to the new entity
        7) if copy is False we version the old root entity and the new entity otherwise only the new entity
        """

    @emit_events(
        creating_factory=lambda self, source_entity, target_field, self_field: DataBorrowingEvent(
            subject_type=type(self),
            subject_id=self.ecs_id,
            process_name="data_borrowing",
            borrower_type=type(self).__name__,
            borrower_id=self.ecs_id,
            source_type=type(source_entity).__name__,
            source_id=source_entity.ecs_id,
            source_field=target_field,
            target_field=self_field,
            data_type=type(getattr(source_entity, target_field)).__name__,
            is_container_data=isinstance(getattr(source_entity, target_field), (list, dict, set, tuple)),
            requires_deep_copy=True
        ),
        created_factory=lambda result, self, source_entity, target_field, self_field: DataBorrowedEvent(
            subject_type=type(self),
            subject_id=self.ecs_id,
            process_name="data_borrowing",
            borrower_type=type(self).__name__,
            borrower_id=self.ecs_id,
            source_type=type(source_entity).__name__,
            source_id=source_entity.ecs_id,
            borrowing_successful=True,
            field_name=target_field,
            provenance_tracked=True,
            container_elements=None,  # Will be populated if container
            borrowing_duration_ms=None
        )
    )
    def borrow_attribute_from(self, source_entity: "Entity", target_field: str, self_field: str) -> None:
        """
        Borrow an attribute from another entity and set it to the self field with provenance tracking.
        
        This method implements data composition by copying data from source_entity.target_field 
        to self.self_field, ensuring no in-place modifications and tracking provenance.
        
        Args:
            source_entity: The entity to borrow from  
            target_field: The field name in the source entity to borrow from
            self_field: The field name in this entity to set
            
        Raises:
            ValueError: If fields don't exist or type validation fails
        """
        # Step 1: Basic validation
        if self_field not in self.model_fields:
            raise ValueError(f"Field '{self_field}' does not exist in {self.__class__.__name__}")
        
        if not hasattr(source_entity, target_field):
            raise ValueError(f"Field '{target_field}' does not exist in {source_entity.__class__.__name__}")
        
        # Step 2: Get source value
        source_value = getattr(source_entity, target_field)
        
        # Step 3: Safe copying with container awareness (prevent in-place modification)
        import copy
        if isinstance(source_value, (list, dict, set, tuple)):
            # Deep copy containers to prevent modification of source
            borrowed_value = copy.deepcopy(source_value)
        elif isinstance(source_value, Entity):
            # For entities, reference them directly (don't copy)
            borrowed_value = source_value
        else:
            # For primitives, simple assignment is fine
            borrowed_value = source_value
        
        # Step 4: Set the value on this entity
        setattr(self, self_field, borrowed_value)
        
        # Step 5: Update attribute_source for provenance tracking
        if isinstance(borrowed_value, list):
            # For lists, create a source list pointing to source entity
            self.attribute_source[self_field] = [source_entity.ecs_id] * len(borrowed_value)
        elif isinstance(borrowed_value, dict):
            # For dicts, create a source dict pointing to source entity  
            self.attribute_source[self_field] = {
                str(k): source_entity.ecs_id for k in borrowed_value.keys()
            }
        else:
            # For simple fields and entities, point to source entity
            self.attribute_source[self_field] = source_entity.ecs_id




    @emit_events(
        creating_factory=lambda self, new_root_entity: EntityAttachmentEvent(
            subject_type=type(self),
            subject_id=self.ecs_id,
            from_state="root_entity",
            to_state="attached_entity",
            transition_reason="attachment",
            entity_type=type(self).__name__,
            entity_id=self.ecs_id,
            target_root_type=type(new_root_entity).__name__,
            target_root_id=new_root_entity.ecs_id,
            lineage_change_required=self.lineage_id != new_root_entity.lineage_id,
            same_lineage=self.lineage_id == new_root_entity.lineage_id
        ),
        created_factory=lambda result, self, new_root_entity: EntityAttachedEvent(
            subject_type=type(self),
            subject_id=self.ecs_id,
            from_state="root_entity",
            to_state="attached_entity",
            transition_reason="attachment",
            entity_type=type(self).__name__,
            entity_id=self.ecs_id,
            attachment_successful=True,
            old_root_id=self.ecs_id,
            new_root_id=new_root_entity.ecs_id,
            lineage_updated=True,
            ids_updated=True,
            attachment_duration_ms=None
        )
    )
    def attach(self, new_root_entity: "Entity") -> None:
        """
        This has to be attached when a previously root entity is added as subentity to a new root parent entity
        """
        if not self.is_root_entity():
            raise ValueError("You can only attach a root entity to a new entity")
        if not new_root_entity.is_root_entity():
            live_root_entity = new_root_entity.get_live_root_entity()
            if live_root_entity is None or not live_root_entity.is_root_entity():
                raise ValueError("Cannot attach an orphan entity")
        else:
            live_root_entity = new_root_entity

        tree = live_root_entity.get_tree(recompute=True)
        assert tree is not None
        if self.ecs_id not in tree.nodes:
            raise ValueError("Cannot attach an entity that is not in the tree")
        
        if self.root_ecs_id == live_root_entity.ecs_id and self.root_live_id == live_root_entity.live_id and self.lineage_id == live_root_entity.lineage_id:
            #only versioning is needed
            EntityRegistry.version_entity(self)
        else:
            old_root_entity = self.get_live_root_entity()

            self.root_ecs_id = live_root_entity.ecs_id
            self.root_live_id = live_root_entity.live_id
            self.lineage_id = live_root_entity.lineage_id
            self.update_ecs_ids()
            if old_root_entity is not None:
                EntityRegistry.version_entity(old_root_entity)
            EntityRegistry.version_entity(live_root_entity)
        
   

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

# Hierarchical entities

class HierarchicalEntity(Entity):
    """
    A hierachical entity.
    """
    entity_of_entity_1: EntityinEntity = Field(description="The entity of the entity", default_factory=EntityinEntity)
    entity_of_entity_2: EntityinEntity = Field(description="The entity of the entity", default_factory=EntityinEntity)
    flat_entity: Entity = Field(description="The flat entity", default_factory=Entity)
    entity_of_entity_of_entity: EntityInEntityInEntity = Field(description="The entity of the entity of the entity", default_factory=EntityInEntityInEntity)
    primitive_data: EntityWithPrimitives = Field(description="Entity with primitive data", default_factory=EntityWithPrimitives)


class FunctionExecution(Entity):
    """
    Enhanced entity for tracking function execution relationships.
    
    This tracks the relationship between input entities, executed functions,
    and output entities for complete audit trails and provenance tracking.
    """
    function_name: str = ""
    input_entity_id: Optional[UUID] = None
    output_entity_id: Optional[UUID] = None
    output_entity_ids: List[UUID] = Field(default_factory=list)  # Support multiple outputs
    execution_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    execution_status: str = "completed"  # "completed", "failed", "pending"
    error_message: Optional[str] = None
    
    # Execution semantics detected via object identity analysis
    execution_semantic: str = ""  # "mutation", "creation", "detachment"
    
    # Enhanced metadata for Phase 2
    return_analysis: Dict[str, Any] = Field(default_factory=dict)  # Return type analysis
    unpacking_metadata: Dict[str, Any] = Field(default_factory=dict)  # How return was unpacked
    sibling_groups: List[List[UUID]] = Field(default_factory=list)  # Groups of entities created together
    performance_metrics: Dict[str, Any] = Field(default_factory=dict)  # Execution time, memory usage, etc.
    input_pattern_classification: Dict[str, Any] = Field(default_factory=dict)  # From Phase 1
    
    # Phase 4 integration fields
    execution_duration: Optional[float] = Field(default=None, description="Function execution time in seconds")
    semantic_classifications: List[str] = Field(default_factory=list, description="Semantic results per output entity")
    execution_pattern: str = Field(default="standard", description="Execution strategy used")
    was_unpacked: bool = Field(default=False, description="Whether result was unpacked into multiple entities")
    original_return_type: str = Field(default="", description="Original function return type")
    entity_count_input: int = Field(default=0, description="Number of input entities")
    entity_count_output: int = Field(default=0, description="Number of output entities")
    config_entity_ids: List[UUID] = Field(default_factory=list, description="ConfigEntity parameters used")
    succeeded: bool = Field(default=True, description="Whether execution succeeded")
    
    # Audit trail expansion
    pre_execution_snapshots: Dict[UUID, Dict[str, Any]] = Field(default_factory=dict)  # Entity states before
    post_execution_changes: Dict[UUID, Dict[str, Any]] = Field(default_factory=dict)   # What changed after
    
    # Execution metadata
    execution_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def mark_as_failed(self, error: str) -> None:
        """Mark execution as failed with error message."""
        self.execution_status = "failed"
        self.error_message = error
        self.succeeded = False
        self.execution_timestamp = datetime.now(timezone.utc)
    
    def mark_as_completed(self, semantic: str) -> None:
        """Mark execution as completed with semantic classification."""
        self.execution_status = "completed"
        self.execution_semantic = semantic
        self.succeeded = True
        self.execution_timestamp = datetime.now(timezone.utc)
        if semantic not in self.semantic_classifications:
            self.semantic_classifications.append(semantic)
    

# EntityFactory for class creation consolidation
class EntityFactory:
    """
    Simple factory for consistent entity class creation across the system.
    
    Consolidates duplicate create_model() patterns while keeping it focused
    on CLASS creation only (no instance-level concerns like execution tracking).
    """
    
    @staticmethod
    def create_entity_class(
        class_name: str,
        field_definitions: Dict[str, Any],
        base_class: Optional[Type['Entity']] = None,
        module_name: Optional[str] = None,
        qualname_parent: Optional[str] = None
    ) -> Type[Entity]:
        """
        Create dynamic entity class with consistent behavior.
        
        Args:
            class_name: Name for the dynamic class
            field_definitions: Dict mapping field names to (type, default) tuples or values
            base_class: Base Entity class (defaults to Entity)
            module_name: Module name for the created class (auto-detected if None)
            qualname_parent: For nested qualname construction (e.g., "function_name")
            
        Returns:
            Dynamic Entity subclass with proper metadata
        """
        # Set default base class (Entity is now available)
        if base_class is None:
            base_class = Entity
        
        # Auto-detect module if not provided
        if module_name is None:
            module_name = EntityFactory._detect_caller_module()
        
        # Process field definitions for Pydantic compatibility
        processed_fields = EntityFactory._process_field_definitions(field_definitions)
        
        # Create the dynamic class
        DynamicClass = create_model(
            class_name,
            __base__=base_class,
            __module__=module_name,
            **processed_fields
        )
        
        # Set proper qualname for debugging
        if qualname_parent:
            DynamicClass.__qualname__ = f"{qualname_parent}.{class_name}"
        else:
            DynamicClass.__qualname__ = class_name
        
        return DynamicClass
    
    @staticmethod
    def _detect_caller_module() -> str:
        """Auto-detect the calling module from the call stack."""
        import inspect
        
        frame = inspect.currentframe()
        try:
            # Skip EntityFactory methods to find the actual caller
            while frame and (
                frame.f_code.co_filename.endswith('entity.py') or
                frame.f_code.co_name.startswith('_') or
                frame.f_code.co_name in ('create_entity_class', 'create_dynamic_entity_class')
            ):
                frame = frame.f_back
            
            if frame:
                module = inspect.getmodule(frame)
                if module:
                    return module.__name__
        finally:
            del frame
        
        return "__main__"
    
    @staticmethod  
    def _process_field_definitions(field_defs: Dict[str, Any]) -> Dict[str, Any]:
        """Process field definitions into Pydantic-compatible format."""
        processed = {}
        
        for field_name, field_spec in field_defs.items():
            # Handle different field specification formats
            if isinstance(field_spec, tuple) and len(field_spec) == 2:
                # (type, default) tuple format
                field_type, default_value = field_spec
                processed[field_name] = (field_type, default_value)
            else:
                # Direct value - infer type
                field_type = type(field_spec) if field_spec is not None else Any
                processed[field_name] = (field_type, field_spec)
                
        return processed




class ConfigEntity(Entity):
    """Base class for dynamically created parameter entities.
    
    ConfigEntity is a subclass of Entity that provides full ECS tracking 
    for parameter entities created by the callable registry. It receives
    special handling only when detected at the top-level of function signatures.
    
    Purpose:
    - Track configuration parameters as first-class entities
    - Enable functools.partial execution pattern
    - Maintain complete audit trails for both data and configuration
    - Support entity inheritance pattern without root reassignment
    
    Usage:
        # Manual creation
        config = ProcessingConfig(threshold=4.0, reason="final_update")
        config.promote_to_root()
        
        # Automatic creation by callable registry
        execute("process_data", data=entity, threshold=4.0, reason="update")
        # System creates ProcessingConfig automatically when function expects it
    """
    
    def __init__(self, **data):
        super().__init__(**data)
        # ConfigEntity-specific initialization if needed
    
    @classmethod
    def is_config_entity_type(cls, entity_type: Type) -> bool:
        """Check if a type is a ConfigEntity subclass (not ConfigEntity itself)."""
        return (
            isinstance(entity_type, type) and
            issubclass(entity_type, ConfigEntity) and
            entity_type is not ConfigEntity
        )
    
    @classmethod
    def create_config_entity_class(
        cls,
        class_name: str,
        field_definitions: Dict[str, Any],
        module_name: str = "__main__"
    ) -> Type['ConfigEntity']:
        """Factory method to create ConfigEntity subclasses dynamically.
        
        Args:
            class_name: Name for the new ConfigEntity subclass
            field_definitions: Dict mapping field names to (type, default) tuples
            module_name: Module name for the created class
            
        Returns:
            New ConfigEntity subclass with specified fields
            
        Example:
            ProcessingConfig = ConfigEntity.create_config_entity_class(
                "ProcessingConfig",
                {
                    "threshold": (float, 3.5),
                    "reason": (str, "update"),
                    "active": (bool, True)
                }
            )
        """
        
        # Use EntityFactory for consistent class creation
        from typing import cast
        ConfigEntityClass = EntityFactory.create_entity_class(
            class_name,
            field_definitions,
            base_class=cls,  # Inherit from ConfigEntity
            module_name=module_name,
            qualname_parent=None  # ConfigEntity classes don't need parent qualification
        )
        
        # Cast to correct type (runtime type is correct, just helping type checker)
        return cast(Type['ConfigEntity'], ConfigEntityClass)


def create_dynamic_entity_class(class_name: str, field_definitions: Dict[str, Any]) -> Type[Entity]:
    """
    Create a dynamic Entity subclass with specified fields.
    
    Args:
        class_name: Name for the dynamic class
        field_definitions: Dict mapping field names to values or (type, default) tuples
        
    Returns:
        Dynamic Entity subclass
    """
    
    # Use EntityFactory for consistent class creation
    return EntityFactory.create_entity_class(
        class_name,
        field_definitions,
        base_class=Entity,
        module_name=None,  # Auto-detect
        qualname_parent=None
    )









