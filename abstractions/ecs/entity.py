""" Implementing step by step the entity system from
source docs:  /Users/tommasofurlanello/Documents/Dev/Abstractions/abstractions/ecs/graph_entity.md"""

from pydantic import BaseModel, Field

from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Optional, List, Dict, Tuple, Set


class EntityGraph(BaseModel):
    """
    A graph of entities. just a stub for now.
    """
    root_ecs_id: UUID = Field(description="The ecs_id of the root entity of the graph")
    root_live_id: UUID = Field(description="The live_id of the root entity of the graph")
    lineage_id: UUID = Field(description="The lineage_id of the root entity of the graph")
    old_ids: List[UUID] = Field(description="The old_ids of the root entity of the graph")

  

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





