""" Implementing step by step the entity system from
source docs:  /Users/tommasofurlanello/Documents/Dev/Abstractions/abstractions/ecs/graph_entity.md"""

from pydantic import BaseModel, Field

from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Optional, List, Dict, Tuple, Set
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
    edge_type: EdgeType
    field_name: str
    container_index: Optional[int] = None  # For lists and tuples
    container_key: Optional[Any] = None    # For dictionaries

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
    
    def add_direct_edge(self, source: "Entity", target: "Entity", field_name: str) -> None:
        """Add a direct field reference edge"""
        edge = EntityEdge(
            source_id=source.ecs_id,
            target_id=target.ecs_id,
            edge_type=EdgeType.DIRECT,
            field_name=field_name
        )
        self.add_edge(edge)
    
    def add_list_edge(self, source: "Entity", target: "Entity", field_name: str, index: int) -> None:
        """Add a list container edge"""
        edge = EntityEdge(
            source_id=source.ecs_id,
            target_id=target.ecs_id,
            edge_type=EdgeType.LIST,
            field_name=field_name,
            container_index=index
        )
        self.add_edge(edge)
    
    def add_dict_edge(self, source: "Entity", target: "Entity", field_name: str, key: Any) -> None:
        """Add a dictionary container edge"""
        edge = EntityEdge(
            source_id=source.ecs_id,
            target_id=target.ecs_id,
            edge_type=EdgeType.DICT,
            field_name=field_name,
            container_key=key
        )
        self.add_edge(edge)
    
    def add_set_edge(self, source: "Entity", target: "Entity", field_name: str) -> None:
        """Add a set container edge"""
        edge = EntityEdge(
            source_id=source.ecs_id,
            target_id=target.ecs_id,
            edge_type=EdgeType.SET,
            field_name=field_name
        )
        self.add_edge(edge)
    
    def add_tuple_edge(self, source: "Entity", target: "Entity", field_name: str, index: int) -> None:
        """Add a tuple container edge"""
        edge = EntityEdge(
            source_id=source.ecs_id,
            target_id=target.ecs_id,
            edge_type=EdgeType.TUPLE,
            field_name=field_name,
            container_index=index
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
            edge.edge_type = EdgeType.HIERARCHICAL
    
    def mark_edge_as_reference(self, source_id: UUID, target_id: UUID) -> None:
        """Mark an edge as a reference (non-ownership) edge"""
        edge_key = (source_id, target_id)
        if edge_key in self.edges:
            edge = self.edges[edge_key]
            edge.edge_type = EdgeType.REFERENCE
    
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
            return self.edges[edge_key].edge_type == EdgeType.HIERARCHICAL
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

def get_pydantic_field_type_entities(entity: "Entity", field_name: str) -> Optional[Type]:
    """Get the entity type from a Pydantic field type hint"""
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
        
        # Check if field_type is Entity or a subclass
        if field_type and (field_type == Entity or issubclass(field_type, Entity)):
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
    # Add the appropriate edge type
    if list_index is not None:
        graph.add_list_edge(source, target, field_name, list_index)
    elif dict_key is not None:
        graph.add_dict_edge(source, target, field_name, dict_key)
    elif tuple_index is not None:
        graph.add_tuple_edge(source, target, field_name, tuple_index)
    else:
        graph.add_direct_edge(source, target, field_name)
    
    # Update distance map for the single-pass DAG algorithm
    if distance_map is not None:
        source_distance = distance_map.get(source.ecs_id, float('inf'))
        target_distance = distance_map.get(target.ecs_id, float('inf'))
        new_target_distance = source_distance + 1
        
        if new_target_distance < target_distance:
            # Found a shorter path to target
            distance_map[target.ecs_id] = int(new_target_distance)
            
            # Update ancestry path (will be done in a separate phase)
            
            # If we already processed this entity, we need to reprocess it
            # since we found a shorter path
            if target.ecs_id in graph.nodes and to_process is not None:
                to_process.append(target)
    
    # Add to processing queue
    if to_process is not None:
        to_process.append(target)

def build_entity_graph(root_entity: "Entity") -> EntityGraph:
    """
    Build a complete entity graph from a root entity.
    
    This algorithm:
    1. Builds the graph structure in a single pass
    2. Tracks shortest paths for each entity
    3. Creates ancestry paths for path-based diffing
    
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
    
    # Maps entity ecs_id to its shortest known distance from root
    distance_map = {root_entity.ecs_id: 0}
    
    # Queue for breadth-first traversal
    to_process = deque([root_entity])
    
    # Set of processed entities to avoid cycles
    processed = set()
    
    # Process all entities
    while to_process:
        entity = to_process.popleft()
        
        # Skip if already processed
        if entity.ecs_id in processed:
            continue
        
        # Mark as processed
        processed.add(entity.ecs_id)
        
        # Add entity to graph
        graph.add_entity(entity)
        
        # Process all fields
        for field_name in entity.model_fields:
            value = getattr(entity, field_name)
            
            # Skip None values
            if value is None:
                continue
            
            # Get expected type for this field
            field_type = get_pydantic_field_type_entities(entity, field_name)
            
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
    
    # Phase 2: Construct ancestry paths and classify edges
    # For each entity, find the shortest path to root
    for entity_id in graph.nodes:
        if entity_id == root_entity.ecs_id:
            # Root entity has a path of just itself
            graph.set_ancestry_path(entity_id, [entity_id])
            continue
        
        # Start from the entity and follow incoming edges to find the shortest path to root
        current_id = entity_id
        path = [current_id]
        
        while current_id != root_entity.ecs_id:
            # Find parent with minimum distance
            min_distance = float('inf')
            min_parent = None
            
            for parent_id in graph.incoming_edges.get(current_id, []):
                parent_distance = distance_map.get(parent_id, float('inf'))
                if parent_distance < min_distance:
                    min_distance = parent_distance
                    min_parent = parent_id
            
            if min_parent is None:
                # This shouldn't happen in a connected graph
                break
            
            # Mark the edge as hierarchical
            graph.mark_edge_as_hierarchical(min_parent, current_id)
            
            # Mark all other incoming edges as reference
            for parent_id in graph.incoming_edges.get(current_id, []):
                if parent_id != min_parent:
                    graph.mark_edge_as_reference(parent_id, current_id)
            
            # Move up the path
            path.append(min_parent)
            current_id = min_parent
        
        # Reverse the path to go from root to entity
        path.reverse()
        graph.set_ancestry_path(entity_id, path)
    
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



class Entity(BaseModel):
    ecs_id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    live_id: UUID = Field(default_factory=uuid4, description="Live/warm identifier")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    forked_at: Optional[datetime] = Field(default=None, description="Timestamp of the last fork")
    parent_id: Optional[UUID] = None
    lineage_id: UUID = Field(default_factory=uuid4)
    old_ids: List[UUID] = Field(default_factory=list)
    root_ecs_id: Optional[UUID] = Field(default=None, description="The ecs_id of the root entity of this entity's graph")
    root_live_id: Optional[UUID] = Field(default=None, description="The live_id of the root entity of this entity's graph")
    from_storage: bool = Field(default=False, description="Whether the entity was loaded from storage, used to prevent re-registration")
    untyped_data: str = Field(default="", description="Default data container for untyped data, string diff will be used to detect changes")

    
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
        Updates parent_id to the previous ecs_id
        Adds the previous ecs_id to old_ids
        If new_root_ecs_id is provided, updates root_ecs_id to the new value
        """
        old_ecs_id = self.ecs_id
        new_ecs_id = uuid4()
        
        self.ecs_id = new_ecs_id
        self.forked_at = datetime.now(timezone.utc)
        self.parent_id = old_ecs_id
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
        #forks the entity to assign a new ecs_id and update the parent_id to the previous ecs_id and adds the previous ecs_id to old_ids
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
        #fork the entity to assign a new ecs_id and update the parent_id to the previous ecs_id and adds the previous ecs_id to old_ids
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
    entities: List[Entity] = Field(description="The list of entities of the entity")

class EntityinDict(Entity):
    """
    An entity that contains a dictionary of entities.
    """
    entities: Dict[str, Entity] = Field(description="The dictionary of entities of the entity")

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

# Hierachical entities

class HierachicalEntity(Entity):
    """
    A hierachical entity.
    """
    entity_of_entity_1: EntityinEntity = Field(description="The entity of the entity", default_factory=EntityinEntity)
    entity_of_entity_2: EntityinEntity = Field(description="The entity of the entity", default_factory=EntityinEntity)
    flat_entity: Entity = Field(description="The flat entity", default_factory=Entity)
    entity_of_entity_of_entity: EntityInEntityInEntity = Field(description="The entity of the entity of the entity", default_factory=EntityInEntityInEntity)





