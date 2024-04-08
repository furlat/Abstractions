# nodes.py

from typing import List, Optional, Dict, Any, Union, Type, Tuple
from pydantic import BaseModel, Field, ConfigDict
from abstractions.goap.entity import Entity, Attribute, RegistryHolder
import typing

import uuid

if typing.TYPE_CHECKING:
    from abstractions.goap.gridmap import GridMap

class Position(Attribute):
    value: Tuple[int, int] = Field(default=(0, 0), description="The (x, y) coordinates of the entity")

    @property
    def x(self):
        return self.value[0]

    @property
    def y(self):
        return self.value[1]

class BlocksMovement(Attribute):
    value: bool = Field(default=False, description="Indicates if the entity blocks movement")

class BlocksLight(Attribute):
    value: bool = Field(default=False, description="Indicates if the entity blocks light")




class GameEntity(Entity):
    """
    Represents an entity in the game world.
    Attributes:
        blocks_movement (BlocksMovement): Attribute indicating if the entity blocks movement.
        blocks_light (BlocksLight): Attribute indicating if the entity blocks light.
        node (Optional[Node]): The node the entity is currently in.
        inventory (List[GameEntity]): The entities stored inside this entity's inventory.
        stored_in (Optional[GameEntity]): The entity this entity is stored inside, if any.
        hash_resolution (str): The resolution level for hashing and string representation.
    """
    blocks_movement: BlocksMovement = Field(default_factory=BlocksMovement, description="Attribute indicating if the entity blocks movement")
    blocks_light: BlocksLight = Field(default_factory=BlocksLight, description="Attribute indicating if the entity blocks light")
    node: Optional["Node"] = Field(default=None, description="The node the entity is currently in")
    inventory: List["GameEntity"] = Field(default_factory=list, description="The entities stored inside this entity's inventory")
    stored_in: Optional["GameEntity"] = Field(default=None, description="The entity this entity is stored inside, if any")
    hash_resolution: str = Field(default="default", description="The resolution level for hashing and string representation")

    @classmethod
    def get_instance(cls, instance_id: str) -> Optional["GameEntity"]:
        instance = cls._registry.get(instance_id)
        if instance is not None and not isinstance(instance, cls):
            raise TypeError(f"Instance with ID {instance_id} is not of type {cls.__name__}")
        return instance

    @property
    def position(self) -> Position:
        """
        Returns the position of the entity.

        If the entity is stored inside another entity, it returns the position of the parent entity.
        If the entity is in a node, it returns the position of the node.
        Otherwise, it returns a default position (0, 0).
        """
        if self.stored_in:
            return self.stored_in.position
        elif self.node:
            return self.node.position
        return Position()

    def set_node(self, node: "Node"):
        """
        Sets the node of the entity.

        Args:
            node (Node): The node to set.

        Raises:
            ValueError: If the entity is stored inside another entity's inventory.
        """
        if self.stored_in:
            raise ValueError("Cannot set node for an entity stored inside another entity's inventory")
        self.node = node
        node.add_entity(self)

    def remove_from_node(self):
        """
        Removes the entity from its current node.

        Raises:
            ValueError: If the entity is stored inside another entity's inventory.
        """
        if self.stored_in:
            raise ValueError("Cannot remove from node an entity stored inside another entity's inventory")
        if self.node:
            self.node.remove_entity(self)
            self.node = None

    def update_attributes(self, attributes: Dict[str, Union[Attribute, "Node", str, List[str]]]) -> "GameEntity":
        """
        Updates the attributes of the entity.

        Args:
            attributes (Dict[str, Union[Attribute, Node, str, List[str]]]): The attributes to update.

        Returns:
            GameEntity: The updated entity.
        """
        updated_attributes = {"name": self.name}  # Preserve the name attribute
        new_node = None
        new_stored_in = None
        new_inventory = None
        for attr_name, value in attributes.items():
            if attr_name == "node":
                if isinstance(value, Node):
                    new_node = value
                elif isinstance(value, str):
                    new_node = Node.get_instance(value)  # Retrieve the Node instance using the ID
            elif attr_name == "stored_in":
                if value is not None:
                    new_stored_in = GameEntity.get_instance(value)  # Retrieve the GameEntity instance using the ID
                else:
                    new_stored_in = None  # Set new_stored_in to None if the value is None
            elif attr_name == "inventory" and isinstance(value, list):
                new_inventory = [GameEntity.get_instance(item_id) for item_id in value]  # Retrieve GameEntity instances using their IDs
            elif isinstance(value, Attribute):
                updated_attributes[attr_name] = value
        if new_stored_in is not None:
            if self.node:
                self.node.remove_entity(self)  # Remove the entity from its current node
            self.stored_in = new_stored_in  # Update the stored_in attribute with the retrieved GameEntity instance
        elif new_node:
            if self.stored_in:
                self.stored_in.inventory.remove(self)  # Remove the entity from its current stored_in inventory
            if self.node:
                self.node.remove_entity(self)  # Remove the entity from its current node
            new_node.add_entity(self)  # Add the entity to the new node
            self.node = new_node  # Update the entity's node reference
        if new_inventory is not None:
            self.inventory = new_inventory  # Update the inventory attribute with the retrieved GameEntity instances
        for attr_name, value in updated_attributes.items():
            setattr(self, attr_name, value)  # Update the entity's attributes
        return self

    def add_to_inventory(self, entity: "GameEntity"):
        """
        Adds an entity to the inventory of this entity.

        Args:
            entity (GameEntity): The entity to add to the inventory.
        """
        if entity not in self.inventory:
            self.inventory.append(entity)
            entity.stored_in = self

    def remove_from_inventory(self, entity: "GameEntity"):
        """
        Removes an entity from the inventory of this entity.

        Args:
            entity (GameEntity): The entity to remove from the inventory.
        """
        if entity in self.inventory:
            self.inventory.remove(entity)
            entity.stored_in = None

    def set_stored_in(self, entity: Optional["GameEntity"]):
        """
        Sets the entity this entity is stored inside.

        Args:
            entity (Optional[GameEntity]): The entity to store this entity inside, or None to remove it from storage.
        """
        if entity is None:
            if self.stored_in:
                self.stored_in.remove_from_inventory(self)
        else:
            entity.add_to_inventory(self)

    def get_state(self) -> Dict[str, Any]:
        """
        Returns the state of the entity as a dictionary.

        Returns:
            Dict[str, Any]: The state of the entity.
        """
        state = {}
        for attr_name, attr_value in self.__dict__.items():
            if isinstance(attr_value, Attribute) and attr_name not in ["position", "inventory"]:
                state[attr_name] = attr_value.value
        state["position"] = self.position.value
        state["inventory"] = [item.id for item in self.inventory]
        return state

    def get_attr(self, attr_name: str) -> Any:
        """
        Retrieves the value of an attribute.

        Args:
            attr_name (str): The name of the attribute.

        Returns:
            Any: The value of the attribute.
        """
        attr = getattr(self, attr_name, None)
        if isinstance(attr, Attribute):
            return attr.value
        return attr

    def set_attr(self, attr_name: str, value: Any):
        """
        Sets the value of an attribute.

        Args:
            attr_name (str): The name of the attribute.
            value (Any): The value to set.
        """
        attr = getattr(self, attr_name, None)
        if isinstance(attr, Attribute):
            attr.value = value
        else:
            setattr(self, attr_name, value)

    def set_hash_resolution(self, resolution: str):
        """
        Sets the resolution level for hashing and string representation.

        Args:
            resolution (str): The resolution level. Can be "default", "attributes", or "inventory".
        """
        self.hash_resolution = resolution

    def reset_hash_resolution(self):
        """
        Resets the resolution level for hashing and string representation to the default value.
        """
        self.hash_resolution = "default"
    

    def __repr__(self, resolution: Optional[str] = None) -> str:
        """
        Returns a string representation of the entity.

        Args:
            resolution (Optional[str]): The resolution level for the representation. If not provided, uses the entity's hash_resolution.

        Returns:
            str: The string representation of the entity.
        """
        resolution = resolution or self.hash_resolution
        if resolution == "default":
            attrs = {
                "id": self.id,
                "name": self.name,
                "position": self.position.value
            }
        elif resolution == "attributes":
            attrs = {
                "id": self.id,
                "name": self.name,
                "position": self.position.value,
                "attributes": {attr_name: attr_value.value for attr_name, attr_value in self.__dict__.items() if isinstance(attr_value, Attribute)}
            }
        elif resolution == "inventory":
            attrs = {
                "id": self.id,
                "name": self.name,
                "position": self.position.value,
                "attributes": {attr_name: attr_value.value for attr_name, attr_value in self.__dict__.items() if isinstance(attr_value, Attribute)},
                "inventory": [item.__repr__(resolution="default") for item in self.inventory]
            }
        else:
            raise ValueError(f"Invalid resolution level: {resolution}")
        attrs_str = ', '.join(f'{k}={v}' for k, v in attrs.items())
        return f"{self.__class__.__name__}({attrs_str})"

    def __hash__(self, resolution: Optional[str] = None) -> int:
        """
        Returns the hash value of the entity.

        Args:
            resolution (Optional[str]): The resolution level for hashing. If not provided, uses the entity's hash_resolution.

        Returns:
            int: The hash value of the entity.
        """
        resolution = resolution or self.hash_resolution
        if resolution == "default":
            return hash(self.id)
        elif resolution == "attributes":
            attribute_values = [f"{attr_name}={attr_value.value}" for attr_name, attr_value in self.__dict__.items() if isinstance(attr_value, Attribute)]
            return hash((self.id, tuple(attribute_values)))
        elif resolution == "inventory":
            attribute_values = [f"{attr_name}={attr_value.value}" for attr_name, attr_value in self.__dict__.items() if isinstance(attr_value, Attribute)]
            inventory_hashes = tuple(hash(item) for item in self.inventory)
            return hash((self.id, tuple(attribute_values), inventory_hashes))
        else:
            raise ValueError(f"Invalid resolution level: {resolution}")
        

# nodes.py



class Node(BaseModel, RegistryHolder):
    """
    Represents a node in the grid map.

    Attributes:
        name (str): The name of the node.
        id (str): The unique identifier of the node.
        position (Position): The position of the node.
        entities (List[GameEntity]): The game entities contained within the node.
        gridmap_id (str): The ID of the grid map the node belongs to.
        blocks_movement (bool): Indicates if the node blocks movement.
        blocks_light (bool): Indicates if the node blocks light.
        hash_resolution (str): The resolution level for hashing and string representation.
    """
    name: str = Field("", description="The name of the node")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="The unique identifier of the node")
    position: Position = Field(default_factory=Position, description="The position of the node")
    entities: List[GameEntity] = Field(default_factory=list, description="The game entities contained within the node")
    gridmap_id: str = Field(description="The ID of the grid map the node belongs to")
    blocks_movement: BlocksMovement = Field(default_factory=BlocksMovement, description="Indicates if the node blocks movement, True if any entity in the node blocks movement, False otherwise")
    blocks_light: BlocksLight = Field(default_factory=BlocksLight, description="Indicates if the node blocks light, True if any entity in the node blocks light, False otherwise")

    hash_resolution: str = Field(default="default", description="The resolution level for hashing and string representation")

    class Config(ConfigDict):
        arbitrary_types_allowed = True

    def __init__(self, **data: Any):
        super().__init__(**data)
        self.register(self)

    @classmethod
    def get_instance(cls, instance_id: str) -> Optional["Node"]:
        instance = cls._registry.get(instance_id)
        if instance is not None and not isinstance(instance, cls):
            raise TypeError(f"Instance with ID {instance_id} is not of type {cls.__name__}")
        return instance

    def add_entity(self, entity: GameEntity):
        """
        Adds an entity to the node.

        Args:
            entity (GameEntity): The entity to add.

        Raises:
            ValueError: If the entity is stored inside another entity's inventory.
        """
        if entity.stored_in:
            raise ValueError("Cannot add an entity stored inside another entity's inventory directly to a node")
        self.entities.append(entity)
        entity.node = self
        self.update_blocking_properties()

    def remove_entity(self, entity: GameEntity):
        """
        Removes an entity from the node.

        Args:
            entity (GameEntity): The entity to remove.

        Raises:
            ValueError: If the entity is stored inside another entity's inventory.
        """
        if entity.stored_in:
            raise ValueError("Cannot remove an entity stored inside another entity's inventory directly from a node")
        self.entities.remove(entity)
        entity.node = None
        self.update_blocking_properties()

    def update_entity(self, old_entity: GameEntity, new_entity: GameEntity):
        """
        Updates an entity in the node.

        Args:
            old_entity (GameEntity): The old entity to replace.
            new_entity (GameEntity): The new entity to replace with.
        """
        self.remove_entity(old_entity)
        self.add_entity(new_entity)

    def update_blocking_properties(self):
        any_movement_blocks = any(entity.blocks_movement.value for entity in self.entities if not entity.stored_in)
        if any_movement_blocks:
            self.blocks_movement.value = True
        else:
            self.blocks_movement.value = False
        any_light_blocks = any(entity.blocks_light.value for entity in self.entities if not entity.stored_in)
        if any_light_blocks:
            self.blocks_light.value = True
        else:
            self.blocks_light.value = False



    def reset(self):
        """
        Resets the node by clearing its entities and resetting the blocking properties.
        """
        self.entities.clear()
        self.blocks_movement = False
        self.blocks_light = False

    def find_entity(self, entity_type: Type[GameEntity], entity_id: Optional[str] = None,
                    entity_name: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None) -> Optional[Union[GameEntity, "AmbiguousEntityError"]]:
        """
        Finds an entity in the node based on the specified criteria.

        Args:
            entity_type (Type[GameEntity]): The type of the entity to find.
            entity_id (Optional[str]): The ID of the entity to find.
            entity_name (Optional[str]): The name of the entity to find.
            attributes (Optional[Dict[str, Any]]): Additional attributes to match.

        Returns:
            Optional[Union[GameEntity, AmbiguousEntityError]]: The found entity, an AmbiguousEntityError if multiple entities match the criteria, or None if no entity is found.
        """
        print(f"inside trhe find_entity method searchinf gfor {entity_type} with id {entity_id} and name {entity_name} and attributes {attributes}")
        matching_entities = []
        for entity in self.entities:
            if isinstance(entity, entity_type):
                if entity_id is not None and entity.id != entity_id:
                    continue
                if entity_name is not None and entity.name != entity_name:
                    continue
                if attributes is not None:
                    entity_attributes = {attr_name: entity.get_attr(attr_name) for attr_name in attributes}
                    if any(attr_name not in entity_attributes or entity_attributes[attr_name] != attr_value
                           for attr_name, attr_value in attributes.items()):
                        continue
                matching_entities.append(entity)
        if len(matching_entities) == 1:
            return matching_entities[0]
        elif len(matching_entities) > 1:
            types_of_matching_entities = [type(entity) for entity in matching_entities]
            missing_attributes = []
            if entity_id is None:
                missing_attributes.append("entity_id")
            if entity_name is None:
                missing_attributes.append("entity_name")
            if attributes is None:
                missing_attributes.extend(matching_entities[0].name)
            return AmbiguousEntityError(
                entity_type=entity_type,
                entity_id=entity_id,
                entity_name=entity_name,
                attributes=attributes,
                matching_entities=matching_entities,
                missing_attributes=missing_attributes
            )
        else:
            return None

    def neighbors(self) -> List["Node"]:
        """
        Returns the neighboring nodes of the node.

        Returns:
            List[Node]: The neighboring nodes.
        """
        grid_map: Optional[GridMap] = RegistryHolder.get_instance(self.gridmap_id)
        if grid_map:
            return grid_map.get_neighbors(self.position.value)
        return []
    
    
    def _get_entity_info(self) -> Tuple[List[str], List[Tuple[str, Any]]]:
        """
        Retrieves the entity types and attributes of the entities in the node.

        Returns:
            Tuple[List[str], List[Tuple[str, Any]]]: A tuple containing the entity types and attributes.
        """
        entity_types = []
        entity_attributes = []
        for entity in self.entities:
            entity_types.append(type(entity).__name__)
            attributes = [(attr.name, attr.value) for attr in entity.all_attributes().values()]
            entity_attributes.extend(attributes)
        return entity_types, entity_attributes

    def set_hash_resolution(self, resolution: str):
        """
        Sets the resolution level for hashing and string representation.

        Args:
            resolution (str): The resolution level. Can be "default", "entities", or "full".
        """
        self.hash_resolution = resolution

    def reset_hash_resolution(self):
        """
        Resets the resolution level for hashing and string representation to the default value.
        """
        self.hash_resolution = "default"

    def __repr__(self, resolution: Optional[str] = None) -> str:
        """
        Returns a string representation of the node.

        Args:
            resolution (Optional[str]): The resolution level for the representation. If not provided, uses the node's hash_resolution.

        Returns:
            str: The string representation of the node.
        """
        resolution = resolution or self.hash_resolution
        if resolution == "default":
            attrs = {
                "id": self.id,
                "position": self.position.value
            }
        elif resolution == "entities":
            attrs = {
                "id": self.id,
                "position": self.position.value,
                "entities": [entity.__repr__(resolution="default") for entity in self.entities]
            }
        elif resolution == "full":
            attrs = {
                "id": self.id,
                "position": self.position.value,
                "entities": [entity.__repr__(resolution="attributes") for entity in self.entities],
                "blocks_movement": self.blocks_movement,
                "blocks_light": self.blocks_light
            }
        else:
            raise ValueError(f"Invalid resolution level: {resolution}")
        attrs_str = ', '.join(f'{k}={v}' for k, v in attrs.items())
        return f"{self.__class__.__name__}({attrs_str})"

    def __hash__(self, resolution: Optional[str] = None) -> int:
        resolution = resolution or self.hash_resolution
        if resolution == "default":
            return hash(self.id)
        elif resolution == "entities":
            entity_hashes = tuple(hash(entity) for entity in self.entities)
            return hash((self.id, entity_hashes))
        elif resolution == "full":
            entity_hashes = tuple(hash(entity) for entity in self.entities)
            return hash((self.id, entity_hashes, self.blocks_movement.value, self.blocks_light.value))
        else:
            raise ValueError(f"Invalid resolution level: {resolution}")
            

class AmbiguousEntityError(BaseModel):
    """
    Represents an error that occurs when multiple entities match the specified criteria.
    Attributes:
        entity_type (Type[GameEntity]): The type of the entity.
        entity_id (Optional[str]): The ID of the entity, if provided.
        entity_name (Optional[str]): The name of the entity, if provided.
        attributes (Optional[Dict[str, Any]]): Additional attributes used for matching, if provided.
        matching_entities (List[GameEntity]): The list of entities that match the specified criteria.
        missing_attributes (List[str]): The list of attributes that could have been used to disambiguate the entities.
    """
    entity_type: Type[GameEntity]
    entity_id: Optional[str] = None
    entity_name: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    matching_entities: List[GameEntity]
    missing_attributes: List[str]

    def get_error_message(self) -> str:
        return f"Ambiguous entity: {self.entity_type.__name__}, Matching entities: {len(self.matching_entities)}, Missing attributes: {', '.join(self.missing_attributes)}"