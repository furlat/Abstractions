from __future__ import annotations
from abstractions.goap.entity import Entity, Attribute, RegistryHolder
from typing import List, Tuple, TYPE_CHECKING, Optional, Any, ForwardRef, Dict, Union, Set, Type
from pydantic import Field, BaseModel, validator, ConfigDict, ValidationInfo, field_validator, conlist
import uuid
import re
import math

if TYPE_CHECKING:
    # from abstractions.goap.spatial import Node
    from abstractions.goap.actions import Action
    from abstractions.goap.game.payloadgen import SpriteMapping
    

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


class Path(BaseModel):
    nodes: List[Node] = Field(default_factory=list, description="The list of nodes in the path")

    @validator('nodes')
    def validate_path(cls, nodes):
        for i in range(len(nodes) - 1):
            if nodes[i + 1] not in nodes[i].neighbors():
                raise ValueError(f"Nodes {nodes[i]} and {nodes[i + 1]} are not adjacent")
            if nodes[i].blocks_movement:
                raise ValueError(f"Node {nodes[i]} is not walkable")
        return nodes

class BaseShapeFromSource(BaseModel):
    source: Node = Field(description="The source node of the shape")
    max_radius: int = Field(description="The maximum radius of the shape")
    nodes: List[Node] = Field(default_factory=list, description="The list of nodes within the shape")

    def _to_egocentric_coordinates(self, x: int, y: int) -> Tuple[int, int]:
        source_x, source_y = self.source.position.value
        return x - source_x, y - source_y
    

    def to_entity_groups(self, use_egocentric: bool = False) -> str:
        groups = {}

        for node in self.nodes:
            entity_types, entity_attributes = node._get_entity_info(node)
            group_key = (tuple(entity_types), tuple(sorted(entity_attributes)))

            if group_key not in groups:
                groups[group_key] = []

            position = self._to_egocentric_coordinates(node.position.x, node.position.y) if use_egocentric else (node.position.x, node.position.y)
            groups[group_key].append(position)

        group_strings_vanilla = []
        group_strings_summarized = []
        for (entity_types, entity_attributes), positions in groups.items():
            vanilla_positions = ", ".join(f"({x}, {y})" for x, y in positions)
            summarized_positions = self._summarize_positions(positions)

            group_strings_vanilla.append(f"Entity Types: {list(entity_types)}, Attributes: {list(entity_attributes)}, Positions: {vanilla_positions}")
            group_strings_summarized.append(f"Entity Types: {list(entity_types)}, Attributes: {list(entity_attributes)}, Positions: {summarized_positions}")

        vanilla_output = '\n'.join(group_strings_vanilla)
        summarized_output = '\n'.join(group_strings_summarized)
        # Add information about blocks_light and blocks_movement nodes
        light_blocking_groups = [group_key for group_key in groups if any(attr[0] == 'BlocksLight' and attr[1] for attr in group_key[1])]
        movement_blocking_groups = [group_key for group_key in groups if any(attr[0] == 'BlocksMovement' and attr[1] for attr in group_key[1])]
        
        if light_blocking_groups:
            light_blocking_info = f"Light Blocking Groups: {', '.join(str(group) for group in light_blocking_groups)}"
            summarized_output += f"\n{light_blocking_info}"
        
        if movement_blocking_groups:
            movement_blocking_info = f"Movement Blocking Groups: {', '.join(str(group) for group in movement_blocking_groups)}"
            summarized_output += f"\n{movement_blocking_info}"
        
        return summarized_output

        # print(f"Vanilla Length: {len(vanilla_output)}")
        # print(f"Summarized Length: {len(summarized_output)}")
        # print(f"Efficiency Gain: {len(vanilla_output) - len(summarized_output)}")
        # print(f"Vanilla Output:\n{vanilla_output}")
        # print(f"Summarized Output:\n{summarized_output}")


    def _summarize_positions(self, positions: List[Tuple[int, int]]) -> str:
        if not positions:
            return ""

        min_x = min(x for x, _ in positions)
        min_y = min(y for _, y in positions)
        max_x = max(x for x, _ in positions)
        max_y = max(y for _, y in positions)

        grid = [[0] * (max_x - min_x + 1) for _ in range(max_y - min_y + 1)]
        for x, y in positions:
            grid[y - min_y][x - min_x] = 1

        def find_largest_rectangle(grid):
            if not grid or not grid[0]:
                return 0, 0, 0, 0

            rows = len(grid)
            cols = len(grid[0])
            max_area = 0
            max_rect = (0, 0, 0, 0)

            for i in range(rows):
                for j in range(cols):
                    if grid[i][j] == 1:
                        width = 1
                        height = 1
                        while j + width < cols and all(grid[i][j + width] == 1 for i in range(i, rows)):
                            width += 1
                        while i + height < rows and all(grid[i + height][j] == 1 for j in range(j, j + width)):
                            height += 1
                        area = width * height
                        if area > max_area:
                            max_area = area
                            max_rect = (j, i, width, height)

            return max_rect

        rectangles = []
        while any(1 in row for row in grid):
            x, y, width, height = find_largest_rectangle(grid)
            rectangles.append((x + min_x, y + min_y, width, height))
            for i in range(y, y + height):
                for j in range(x, x + width):
                    grid[i][j] = 0

        summarized = []
        for x, y, width, height in rectangles:
            if width == 1 and height == 1:
                summarized.append(f"({x}, {y})")
            elif width == 1:
                summarized.append(f"({x}, {y}:{y + height})")
            elif height == 1:
                summarized.append(f"({x}:{x + width}, {y})")
            else:
                summarized.append(f"({x}:{x + width}, {y}:{y + height})")

        remaining_positions = [(x, y) for x, y in positions if not any(x >= rx and x < rx + rw and y >= ry and y < ry + rh for rx, ry, rw, rh in rectangles)]
        if remaining_positions:
            summarized.extend(f"({x}, {y})" for x, y in remaining_positions)

        return ", ".join(summarized)




class Radius(BaseShapeFromSource):
    source: Node = Field(description="The source node of the radius")
    max_radius: int = Field(description="The maximum radius of the area")
    nodes: List[Node] = Field(default_factory=list, description="The list of nodes within the radius")

    @validator('nodes')
    def validate_radius(cls, nodes, values):
        source = values['source']
        max_radius = values['max_radius']
        grid_map = source.grid_map
        for node in nodes:
            if grid_map._get_distance(source.position.value, node.position.value) > max_radius:
                raise ValueError(f"Node {node} is outside the specified radius")
        return nodes

class Shadow(BaseShapeFromSource):
    source: Node = Field(description="The source node of the shadow")
    max_radius: int = Field(description="The maximum radius of the shadow")
    nodes: List[Node] = Field(default_factory=list, description="The list of nodes within the shadow")

    @validator('nodes')
    def validate_shadow(cls, nodes, values):
        source = values['source']
        max_radius = values['max_radius']
        grid_map = source.grid_map
        for node in nodes:
            if grid_map._get_distance(source.position.value, node.position.value) > max_radius:
                raise ValueError(f"Node {node} is outside the specified shadow radius")
        return nodes
    
   

    

class RayCast(BaseModel):
    source: Node = Field(description="The source node of the raycast")
    target: Node = Field(description="The target node of the raycast")
    has_path: bool = Field(description="Indicates whether there is a clear path from source to target")
    nodes: List[Node] = Field(default_factory=list, description="The list of nodes along the raycast path (excluding source and target)")

    @validator('nodes')
    def validate_raycast(cls, nodes, values):
        source = values['source']
        target = values['target']
        has_path = values['has_path']
        if not has_path and nodes:
            raise ValueError("The raycast path should be empty if there is no clear path")
        if has_path and len(nodes) >0:
            if nodes[0] == source or nodes[-1] == target:
                raise ValueError("The raycast path should not include the source or target nodes")
            for i in range(len(nodes) - 1):
                if nodes[i + 1] not in nodes[i].neighbors():
                    raise ValueError(f"Nodes {nodes[i]} and {nodes[i + 1]} are not adjacent")
            for node in nodes:
                if node.blocks_light:
                    raise ValueError(f"Node {node} blocks vision along the raycast path")
        return nodes
    

class ActionInstance(BaseModel):
    source_id: str
    target_id: str
    action: Action

class ActionsPayload(BaseModel):
    actions: List[ActionInstance]

class SummarizedActionPayload(BaseModel):
    """
    Represents an action payload with absolute positions and dictionary-based attributes.
    """
    action_name: str = Field(description="The name of the action.")
    source_entity_type: str = Field(description="The type of the source entity.")
    source_entity_position: Tuple[int, int] = Field(description="The absolute position of the source entity.")
    source_entity_id: Optional[str] = Field(default=None, description="The unique identifier of the source entity. Use only when necessary to disambiguate between multiple entities at the same location.")
    source_entity_name: Optional[str] = Field(default=None, description="The name of the source entity. Use only when necessary to disambiguate between multiple entities at the same location.")
    source_entity_attributes: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional attributes of the source entity.")
    target_entity_type: str = Field(description="The type of the target entity.")
    target_entity_position: Tuple[int, int] = Field(description="The absolute position of the target entity.")
    target_entity_id: Optional[str] = Field(default=None, description="The unique identifier of the target entity. Use only when necessary to disambiguate between multiple entities at the same location.")
    target_entity_name: Optional[str] = Field(default=None, description="The name of the target entity. Use only when necessary to disambiguate between multiple entities at the same location.")
    target_entity_attributes: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional attributes of the target entity.")
    explanation_of_my_behavior:Optional[str] = Field(description="The explanation of the agent's behavior behind the choice of action.")

    def to_ego_payload(self, character_position: Tuple[int, int]) -> "SummarizedEgoActionPayload":
        """
        Convert the action payload to an egocentric version relative to the character's position.
        """
        source_x, source_y = self.source_entity_position
        target_x, target_y = self.target_entity_position
        char_x, char_y = character_position

        ego_source_position = (source_x - char_x, source_y - char_y)
        ego_target_position = (target_x - char_x, target_y - char_y)

        return SummarizedEgoActionPayload(
            action_name=self.action_name,
            source_entity_type=self.source_entity_type,
            source_entity_position=ego_source_position,
            source_entity_id=self.source_entity_id,
            source_entity_name=self.source_entity_name,
            source_entity_attributes=self.source_entity_attributes,
            target_entity_type=self.target_entity_type,
            target_entity_position=ego_target_position,
            target_entity_id=self.target_entity_id,
            target_entity_name=self.target_entity_name,
            target_entity_attributes=self.target_entity_attributes,
        )


class SummarizedEgoActionPayload(BaseModel):
    """
    Represents an action payload with positions relative to the character and dictionary-based attributes.
    """
    action_name: str = Field(description="The name of the action.")
    source_entity_type: str = Field(description="The type of the source entity.")
    source_entity_position: Tuple[int, int] = Field(description="The position of the source entity relative to the character.")
    source_entity_id: Optional[str] = Field(default=None, description="The unique identifier of the source entity. Use only when necessary to disambiguate between multiple entities at the same location.")
    source_entity_name: Optional[str] = Field(default=None, description="The name of the source entity. Use only when necessary to disambiguate between multiple entities at the same location.")
    source_entity_attributes: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional attributes of the source entity.")
    target_entity_type: str = Field(description="The type of the target entity.")
    target_entity_position: Tuple[int, int] = Field(description="The position of the target entity relative to the character.")
    target_entity_id: Optional[str] = Field(default=None, description="The unique identifier of the target entity. Use only when necessary to disambiguate between multiple entities at the same location.")
    target_entity_name: Optional[str] = Field(default=None, description="The name of the target entity. Use only when necessary to disambiguate between multiple entities at the same location.")
    target_entity_attributes: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional attributes of the target entity.")

    def to_absolute_payload(self, character_position: Tuple[int, int]) -> "SummarizedActionPayload":
        """
        Convert the egocentric action payload to an absolute version based on the character's position.
        """
        char_x, char_y = character_position
        source_x, source_y = self.source_entity_position
        target_x, target_y = self.target_entity_position

        abs_source_position = (char_x + source_x, char_y + source_y)
        abs_target_position = (char_x + target_x, char_y + target_y)

        return SummarizedActionPayload(
            action_name=self.action_name,
            source_entity_type=self.source_entity_type,
            source_entity_position=abs_source_position,
            source_entity_id=self.source_entity_id,
            source_entity_name=self.source_entity_name,
            source_entity_attributes=self.source_entity_attributes,
            target_entity_type=self.target_entity_type,
            target_entity_position=abs_target_position,
            target_entity_id=self.target_entity_id,
            target_entity_name=self.target_entity_name,
            target_entity_attributes=self.target_entity_attributes,
        )



    

class ActionResult(BaseModel):
    action_instance: ActionInstance
    success: bool
    error: str = None
    failed_prerequisites: List[str] = Field(default_factory=list)
    state_before: Dict[str, Any] = Field(default_factory=dict)
    state_after: Dict[str, Any] = Field(default_factory=dict)


    def to_text_state(self, use_egocentric: bool = False) -> str:
        action_name = self.action_instance.action.__class__.__name__

        source_before = self.state_before["source"].copy()
        target_before = self.state_before["target"].copy()
        source_before_position = source_before.pop("position")
        target_before_position = target_before.pop("position")

        if use_egocentric:
            source_before_position = self._to_egocentric_coordinates(source_before_position[0], source_before_position[1])
            target_before_position = self._to_egocentric_coordinates(target_before_position[0], target_before_position[1])

        source_before_state = self._format_entity_state(source_before)
        target_before_state = self._format_entity_state(target_before)

        if self.success:
            result = "Success"
            source_after = self.state_after["source"].copy()
            target_after = self.state_after["target"].copy()
            source_after_position = source_after.pop("position")
            target_after_position = target_after.pop("position")

            if use_egocentric:
                source_after_position = self._to_egocentric_coordinates(source_after_position[0], source_after_position[1])
                target_after_position = self._to_egocentric_coordinates(target_after_position[0], target_after_position[1])

            source_after_state = self._format_entity_state(source_after)
            target_after_state = self._format_entity_state(target_after)

            return f"Action: {action_name}\nSource Before: {source_before_state}\nSource Before Position: {source_before_position}\nTarget Before: {target_before_state}\nTarget Before Position: {target_before_position}\nResult: {result}\nSource After: {source_after_state}\nSource After Position: {source_after_position}\nTarget After: {target_after_state}\nTarget After Position: {target_after_position}\n"
        else:
            result = "Failure"
            error = self.error
            failed_prerequisites_text = "\n".join(self.failed_prerequisites)
            return f"Action: {action_name}\nSource Before: {source_before_state}\nSource Before Position: {source_before_position}\nTarget Before: {target_before_state}\nTarget Before Position: {target_before_position}\nResult: {result}\nError: {error}\nFailed Prerequisites:\n{failed_prerequisites_text}\n"

    def _to_egocentric_coordinates(self, x: int, y: int) -> Tuple[int, int]:
        source_x, source_y = self.state_before["source"]["position"]
        return x - source_x, y - source_y

    def _format_entity_state(self, state: Dict[str, Any]) -> str:
        formatted_state = ", ".join(f"{key}: {value}" for key, value in state.items())
        return f"{{{formatted_state}}}"

    

class ActionsResults(BaseModel):
    results: List[ActionResult]

    def to_text_state(self, use_egocentric: bool = False) -> str:
        timesteps = []
        current_timestep = []

        for result in self.results:
            if result.success:
                current_timestep.append(result)
            else:
                if current_timestep:
                    timestep_text = self._format_timestep(current_timestep, use_egocentric)
                    timesteps.append(timestep_text)
                    current_timestep = []

                failure_text = self._format_failure(result, use_egocentric)
                timesteps.append(failure_text)

        if current_timestep:
            timestep_text = self._format_timestep(current_timestep, use_egocentric)
            timesteps.append(timestep_text)

        return "\n".join(timesteps)

    def _format_timestep(self, timestep: List[ActionResult], use_egocentric: bool) -> str:
        action_states = []
        for i, result in enumerate(timestep, start=1):
            action_state = f"Action {i}:\n{result.to_text_state(use_egocentric)}"
            action_states.append(action_state)

        timestep_text = f"Timestep:\n{''.join(action_states)}"
        return timestep_text

    def _format_failure(self, failure: ActionResult, use_egocentric: bool) -> str:
        failure_text = f"Failure:\n{failure.to_text_state(use_egocentric)}"
        return failure_text

class AmbiguousEntityError(BaseModel):
    entity_type: Type[GameEntity]
    entity_id: Optional[str] = None
    entity_name: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    matching_entities: List[GameEntity]
    missing_attributes: List[str]

    def __str__(self):
        return f"Ambiguous entity: {self.entity_type.__name__}, Matching entities: {len(self.matching_entities)}, Missing attributes: {', '.join(self.missing_attributes)}" 

class ActionConversionError(BaseModel):
    message: str
    source_entity_error: Optional[AmbiguousEntityError] = None
    target_entity_error: Optional[AmbiguousEntityError] = None

    def __str__(self):
        error_message = self.message
        if self.source_entity_error:
            error_message += f"\nSource Entity Error: {self.source_entity_error}"
        if self.target_entity_error:
            error_message += f"\nTarget Entity Error: {self.target_entity_error}"
        return error_message

class GameEntity(Entity):
    blocks_movement: BlocksMovement = Field(default_factory=BlocksMovement, description="Attribute indicating if the entity blocks movement")
    blocks_light: BlocksLight = Field(default_factory=BlocksLight, description="Attribute indicating if the entity blocks light")
    node: Optional[Node] = Field(default=None, description="The node the entity is currently in")
    inventory: List[GameEntity] = Field(default_factory=list, description="The entities stored inside this entity's inventory")
    stored_in: Optional[GameEntity] = Field(default=None, description="The entity this entity is stored inside, if any")

    @property
    def position(self) -> Position:
        if self.stored_in:
           
            return self.stored_in.position
        elif self.node:
            return self.node.position
        return Position()

    def set_node(self, node: Node):
        if self.stored_in:
            raise ValueError("Cannot set node for an entity stored inside another entity's inventory")
        self.node = node
        node.add_entity(self)

    def remove_from_node(self):
        if self.stored_in:
            raise ValueError("Cannot remove from node an entity stored inside another entity's inventory")
        if self.node:
            self.node.remove_entity(self)
            self.node = None

    def update_attributes(self, attributes: Dict[str, Union[Attribute, Node, str, List[str]]]) -> "GameEntity":
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
    
    def add_to_inventory(self, entity: GameEntity):
        if entity not in self.inventory:
            self.inventory.append(entity)
            entity.stored_in = self

    def remove_from_inventory(self, entity: GameEntity):
        if entity in self.inventory:
            self.inventory.remove(entity)
            entity.stored_in = None

    def set_stored_in(self, entity: Optional[GameEntity]):
        if entity is None:
            if self.stored_in:
                self.stored_in.remove_from_inventory(self)
        else:
            entity.add_to_inventory(self)

    def get_state(self) -> Dict[str, Any]:
        state = {}
        for attr_name, attr_value in self.__dict__.items():
            if isinstance(attr_value, Attribute) and attr_name not in ["position", "inventory"]:
                state[attr_name] = attr_value.value
        state["position"] = self.position.value
        state["inventory"] = [item.id for item in self.inventory]
        return state
    
    def __repr__(self):
        attrs = {}
        for key, value in self.__dict__.items():
            if key == 'node' and value is not None:
                attrs[key] = value.non_verbose_repr()
            elif key != 'node':
                attrs[key] = value
        attrs_str = ', '.join(f'{k}={v}' for k, v in attrs.items())
        return f"{self.__class__.__name__}({attrs_str})"
    
    def __hash__(self):
        #hash together idname and attributeslike in Node
        attribute_values = []
        for attribute_name, attribute_value in self.__dict__.items():
            if isinstance(attribute_value, Attribute):
                attribute_values.append(f"{attribute_name}={attribute_value.value}")
        entity_info = f"{self.__class__.__name__}_{self.name}_{self.id}_{'_'.join(attribute_values)}"
        return hash(entity_info)


class Node(BaseModel, RegistryHolder):
    name: str = Field("", description="The name of the node")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="The unique identifier of the node")
    position: Position = Field(default_factory=Position, description="The position of the node")
    entities: List[GameEntity] = Field(default_factory=list, description="The game entities contained within the node")
    grid_map: Optional[GridMap] = Field(default=None, exclude=True, description="The grid map the node belongs to")
    blocks_movement: bool = Field(default=False, description="Indicates if the node blocks movement")
    blocks_light: bool = Field(default=False, description="Indicates if the node blocks light")
    
    class Config(ConfigDict):
        arbitrary_types_allowed = True
    
    def __init__(self, **data: Any):
        super().__init__(**data)
        self.register(self)
    
    def __hash__(self):
        return hash(self.id)
    
    def non_verbose_repr(self):
        return f"Node(id={self.id}, position={self.position.value})"
    
    def add_entity(self, entity: GameEntity):
        if entity.stored_in:
            raise ValueError("Cannot add an entity stored inside another entity's inventory directly to a node")
        self.entities.append(entity)
        entity.node = self
        self.update_blocking_properties()

    def remove_entity(self, entity: GameEntity):
        if entity.stored_in:
            raise ValueError("Cannot remove an entity stored inside another entity's inventory directly from a node")
        self.entities.remove(entity)
        entity.node = None
        self.update_blocking_properties()
    
    def update_entity(self, old_entity: GameEntity, new_entity: GameEntity):
        self.remove_entity(old_entity)
        self.add_entity(new_entity)

    def update_blocking_properties(self):
        self.blocks_movement = any(entity.blocks_movement.value for entity in self.entities if not entity.stored_in)
        self.blocks_light = any(entity.blocks_light.value for entity in self.entities if not entity.stored_in)
    
    def reset(self):
        self.entities.clear()
        self.blocks_movement = False
        self.blocks_light = False

    def find_entity(self, entity_type: Type[GameEntity], entity_id: Optional[str] = None,
                entity_name: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None) -> Optional[Union[GameEntity, AmbiguousEntityError]]:
        matching_entities = []
        for entity in self.entities:
            if isinstance(entity, entity_type):
                if entity_id is not None and entity.id != entity_id:
                    continue
                if entity_name is not None and entity.name != entity_name:
                    continue
                if attributes is not None:
                    entity_attributes = {attr_name: getattr(entity, attr_name).value for attr_name in attributes}
                    if any(attr_name not in entity_attributes or entity_attributes[attr_name] != attr_value
                        for attr_name, attr_value in attributes.items()):
                        continue
                matching_entities.append(entity)

        if len(matching_entities) == 1:
            return matching_entities[0]
        elif len(matching_entities) > 1:
            missing_attributes = []
            if entity_id is None:
                missing_attributes.append("entity_id")
            if entity_name is None:
                missing_attributes.append("entity_name")
            if attributes is None:
                missing_attributes.extend(attr.name for attr in matching_entities[0].all_attributes())
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
    
    def neighbors(self) -> List[Node]:
        if self.grid_map:
            return self.grid_map.get_neighbors(self.position.value)
        return []
    
    def _get_entity_info(self, node: Node) -> Tuple[List[str], List[Tuple[str, Any]]]:
        entity_types = []
        entity_attributes = []
        for entity in node.entities:
            entity_types.append(type(entity).__name__)
            attributes = [(attr.name, attr.value) for attr in entity.all_attributes().values()]
            entity_attributes.extend(attributes)
        return entity_types, entity_attributes
    

    def __hash__(self):
        entity_info = []
        for entity in self.entities:
            attribute_values = []
            for attribute_name, attribute_value in entity.__dict__.items():
                if isinstance(attribute_value, Attribute):
                    attribute_values.append(f"{attribute_name}={attribute_value.value}")
            entity_info.append(f"{entity.__class__.__name__}_{entity.name}_{entity.id}_{'_'.join(attribute_values)}")
        return hash(f"{self.id}_{self.position.value}_{'_'.join(entity_info)}")

import heapq

class GridMap:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.grid: List[List[Node]] = [[Node(position=Position(value=(x, y)), grid_map=self) for y in range(height)] for x in range(width)]
        self.actions: Dict[str, Type[Action]] = {}
        self.entity_type_map: Dict[str, Type[GameEntity]] = {}
    
    def register_action(self, action_class: Type[Action]):
        self.actions[action_class.__name__] = action_class

    def register_actions(self, action_classes: List[Type[Action]]):
        for action_class in action_classes:
            self.register_action(action_class)
    
    def get_actions(self) -> Dict[str, Type[Action]]:
        return self.actions

    def get_node(self, position: Tuple[int, int]) -> Node:
        x, y = position
        return self.grid[x][y] if 0 <= x < self.width and 0 <= y < self.height else None
    
    def get_nodes_in_rect(self, pos: Tuple[int, int], size: Tuple[int, int]) -> List[Node]:
        start_x, start_y = pos
        width, height = size
        end_x = start_x + width
        end_y = start_y + height

        nodes = []
        for y in range(max(0, start_y), min(self.height, end_y)):
            for x in range(max(0, start_x), min(self.width, end_x)):
                node = self.get_node((x, y))
                if node:
                    nodes.append(node)

        return nodes

    def set_node(self, position: Tuple[int, int], node: Node):
        x, y = position
        self.grid[x][y] = node

    def get_neighbors(self, position: Tuple[int, int], allow_diagonal: bool = True) -> List[Node]:
        x, y = position
        neighbors = []
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            new_x, new_y = x + dx, y + dy
            if 0 <= new_x < self.width and 0 <= new_y < self.height:
                neighbors.append(self.grid[new_x][new_y])
        if allow_diagonal:
            for dx, dy in [(1, 1), (-1, 1), (1, -1), (-1, -1)]:
                new_x, new_y = x + dx, y + dy
                if 0 <= new_x < self.width and 0 <= new_y < self.height:
                    neighbors.append(self.grid[new_x][new_y])
        return neighbors
    
    def find_entity(self, entity_type: Type[GameEntity], position: Tuple[int, int], entity_id: Optional[str] = None,
                    entity_name: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None) -> Optional[GameEntity]:
        node = self.get_node(position)
        if node is None:
            return None
        return node.find_entity(entity_type, entity_id, entity_name, attributes)

    def dijkstra(self, start: Node, max_distance: int, allow_diagonal: bool = True) -> Tuple[Dict[Tuple[int, int], int], Dict[Tuple[int, int], Path]]:
        distances: Dict[Tuple[int, int], int] = {start.position.value: 0}
        paths: Dict[Tuple[int, int], Path] = {start.position.value: Path(nodes=[start])}
        unvisited = [(0, start.position.value)]  # The unvisited set is a list of tuples (distance, position)
        while unvisited:
            current_distance, current_position = heapq.heappop(unvisited)
            if current_distance > max_distance:
                break
            current_node = self.get_node(current_position)
            for neighbor in self.get_neighbors(current_position, allow_diagonal):
                if not neighbor.blocks_movement:
                    new_distance = current_distance + 1  # Assuming uniform cost between nodes
                    if neighbor.position.value not in distances or new_distance < distances[neighbor.position.value]:
                        distances[neighbor.position.value] = new_distance
                        paths[neighbor.position.value] = Path(nodes=paths[current_position].nodes + [neighbor])
                        heapq.heappush(unvisited, (new_distance, neighbor.position.value))
        return distances, paths

    def a_star(self, start: Node, goal: Node, allow_diagonal: bool = True) -> Optional[Path]:
        if start == goal:
            return Path(nodes=[start])
        if goal.blocks_movement:
            return None

        def heuristic(position: Tuple[int, int]) -> int:
            return abs(position[0] - goal.position.x) + abs(position[1] - goal.position.y)

        open_set = [(0, start.position.value)]  # The open set is a list of tuples (f_score, position)
        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
        g_score: Dict[Tuple[int, int], int] = {start.position.value: 0}
        f_score: Dict[Tuple[int, int], int] = {start.position.value: heuristic(start.position.value)}

        while open_set:
            current_position = heapq.heappop(open_set)[1]
            current_node = self.get_node(current_position)

            if current_node == goal:
                path_nodes = []
                while current_position in came_from:
                    path_nodes.append(self.get_node(current_position))
                    current_position = came_from[current_position]
                path_nodes.append(start)
                path_nodes.reverse()
                return Path(nodes=path_nodes)

            for neighbor in self.get_neighbors(current_position, allow_diagonal):
                if not neighbor.blocks_movement:  # Check if the neighbor is walkable
                    tentative_g_score = g_score[current_position] + 1  # Assuming uniform cost
                    if neighbor.position.value not in g_score or tentative_g_score < g_score[neighbor.position.value]:
                        came_from[neighbor.position.value] = current_position
                        g_score[neighbor.position.value] = tentative_g_score
                        f_score[neighbor.position.value] = tentative_g_score + heuristic(neighbor.position.value)
                        if (f_score[neighbor.position.value], neighbor.position.value) not in open_set:
                            heapq.heappush(open_set, (f_score[neighbor.position.value], neighbor.position.value))

        return None  # No path found
    def get_movement_array(self) -> List[List[bool]]:
        return [[not node.blocks_movement for node in row] for row in self.grid]

    def get_vision_array(self) -> List[List[bool]]:
        return [[not node.blocks_light for node in row] for row in self.grid]

    def get_nodes_in_radius(self, position: Tuple[int, int], radius: int) -> List[Node]:
        x, y = position
        nodes = []
        for i in range(x - radius, x + radius + 1):
            for j in range(y - radius, y + radius + 1):
                if 0 <= i < self.width and 0 <= j < self.height:
                    if self._get_distance(position, (i, j)) <= radius:
                        nodes.append(self.grid[i][j])
        return nodes
    
    def get_radius(self, source: Node, max_radius: int) -> Radius:
        nodes = self.get_nodes_in_radius(source.position.value, max_radius)
        return Radius(source=source, max_radius=max_radius, nodes=nodes)


    def _is_within_bounds(self, position: Tuple[int, int]) -> bool:
        x, y = position
        return 0 <= x < self.width and 0 <= y < self.height

    def _get_distance(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


    def raycast(self, source: Node, target: Node) -> Tuple[bool, List[Node]]:
        start = source.position.value
        end = target.position.value
        line_points = self.line(start, end)
        nodes = []
        for point in line_points:
            node = self.get_node(point)
            if node == source or node == target:
                continue
            if node.blocks_light:
                return False, nodes
            nodes.append(node)
        return True, nodes

    def get_raycast(self, source: Node, target: Node) -> RayCast:
        has_path, nodes = self.raycast(source, target)
        return RayCast(source=source, target=target, has_path=has_path, nodes=nodes)

    def shadow_casting(self, origin: Tuple[int, int], max_radius: int = None) -> List[Tuple[int, int]]:
        max_radius = max_radius or max(self.width, self.height)
        visible_cells = [origin]
        step_size = 0.5  # Decrease the step size for better accuracy
        for angle in range(int(360 / step_size)):  # Adjust the loop range based on the new step size
            visible_cells.extend(self.cast_light(origin, max_radius, math.radians(angle * step_size)))
        visible_cells = list(set(visible_cells))  # Take only unique values of visible cells
        return visible_cells

    def cast_light(self, origin: Tuple[int, int], max_radius: int, angle: float) -> List[Tuple[int, int]]:
        x0, y0 = origin
        x1 = x0 + int(max_radius * math.cos(angle))
        y1 = y0 + int(max_radius * math.sin(angle))
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        x, y = x0, y0
        n = 1 + dx + dy
        x_inc = 1 if x1 > x0 else -1
        y_inc = 1 if y1 > y0 else -1
        error = dx - dy
        dx *= 2
        dy *= 2
        line_points = []
        first_iteration = True
        for _ in range(n):
            if self._is_within_bounds((x, y)):
                line_points.append((x, y))
                if not first_iteration and self.get_node((x, y)).blocks_light:
                    break
            first_iteration = False
            if error > 0:
                x += x_inc
                error -= dy
            else:
                y += y_inc
                error += dx
        return line_points

    def line(self, start: Tuple[int, int], end: Tuple[int, int]) -> List[Tuple[int, int]]:
        dx, dy = end[0] - start[0], end[1] - start[1]
        distance = math.sqrt(dx * dx + dy * dy)
        angle = math.atan2(dy, dx)
        return self.cast_light(start, math.ceil(distance), angle)

    def line_of_sight(self, start: Tuple[int, int], end: Tuple[int, int]) -> Tuple[bool, List[Tuple[int, int]]]:
        line_points = self.line(start, end)
        visible_points = []
        for point in line_points[1:]:  # Skip the starting point and iterate through the rest of the points
            if self.get_node(point).blocks_light:
                return False, visible_points
            else:
                visible_points.append(point)
        return True, visible_points

    def get_shadow(self, source: Node, max_radius: int) -> Shadow:
        visible_cells = self.shadow_casting(source.position.value, max_radius)
        nodes = [self.get_node(cell) for cell in visible_cells]
        return Shadow(source=source, max_radius=max_radius, nodes=nodes)
    
    def generate_entity_type_map(self):
        self.entity_type_map = {}
        for row in self.grid:
            for node in row:
                for entity in node.entities:
                    entity_type = type(entity)
                    entity_type_name = entity_type.__name__
                    if entity_type_name not in self.entity_type_map:
                        self.entity_type_map[entity_type_name] = entity_type
    
    def convert_summarized_payload(self, summarized_payload: SummarizedActionPayload) -> Union[ActionsPayload, ActionConversionError]:
        source_entity_type = self.entity_type_map.get(summarized_payload.source_entity_type)
        if source_entity_type is None:
            return ActionConversionError(message=f"Invalid source entity type: {summarized_payload.source_entity_type}")

        target_entity_type = self.entity_type_map.get(summarized_payload.target_entity_type)
        if target_entity_type is None:
            return ActionConversionError(message=f"Invalid target entity type: {summarized_payload.target_entity_type}")

        source_entity_result = self.find_entity(source_entity_type, summarized_payload.source_entity_position,
                                                summarized_payload.source_entity_id, summarized_payload.source_entity_name,
                                                summarized_payload.source_entity_attributes)
        target_entity_result = self.find_entity(target_entity_type, summarized_payload.target_entity_position,
                                                summarized_payload.target_entity_id, summarized_payload.target_entity_name,
                                                summarized_payload.target_entity_attributes)

        if isinstance(source_entity_result, AmbiguousEntityError):
            return ActionConversionError(
                message=f"Unable to find source entity: {summarized_payload.source_entity_type} at position {summarized_payload.source_entity_position}",
                source_entity_error=source_entity_result
            )
        if isinstance(target_entity_result, AmbiguousEntityError):
            return ActionConversionError(
                message=f"Unable to find target entity: {summarized_payload.target_entity_type} at position {summarized_payload.target_entity_position}",
                target_entity_error=target_entity_result
            )

        source_entity = source_entity_result
        target_entity = target_entity_result

        if source_entity is None:
            return ActionConversionError(
                message=f"Unable to find source entity: {summarized_payload.source_entity_type} at position {summarized_payload.source_entity_position}"
            )
        if target_entity is None:
            return ActionConversionError(
                message=f"Unable to find target entity: {summarized_payload.target_entity_type} at position {summarized_payload.target_entity_position}"
            )

        action_class = self.actions.get(summarized_payload.action_name)
        if action_class is None:
            return ActionConversionError(message=f"Action '{summarized_payload.action_name}' not found")

        action_instance = ActionInstance(source_id=source_entity.id, target_id=target_entity.id, action=action_class())
        return ActionsPayload(actions=[action_instance])
    
    def apply_actions_payload(self, payload: ActionsPayload) -> ActionsResults:
        results = []
        if len(payload.actions) > 0:
            print(f"Applying {len(payload.actions)} actions")
        for action_instance in payload.actions:
            source = GameEntity.get_instance(action_instance.source_id)
            target = GameEntity.get_instance(action_instance.target_id)
            action = action_instance.action

            state_before = {
                "source": source.get_state(),
                "target": target.get_state()
            }

            if action.is_applicable(source, target):
                try:
                    updated_source, updated_target = action.apply(source, target)
                    # Handle inventory-related updates
                    if updated_source.stored_in != source.stored_in:
                        if source.stored_in and source in source.stored_in.inventory:
                            source.stored_in.inventory.remove(source)
                        if updated_source.stored_in:
                            updated_source.stored_in.inventory.append(updated_source)
                    if updated_target.stored_in != target.stored_in:
                        if target.stored_in and target in target.stored_in.inventory:
                            target.stored_in.inventory.remove(target)
                        if updated_target.stored_in:
                            updated_target.stored_in.inventory.append(updated_target)

                    state_after = {
                        "source": updated_source.get_state(),
                        "target": updated_target.get_state()
                    }
                    results.append(ActionResult(action_instance=action_instance, success=True, state_before=state_before, state_after=state_after))
                except ValueError as e:
                    results.append(ActionResult(action_instance=action_instance, success=False, error=str(e), state_before=state_before))
            else:
                # Check which prerequisite failed and provide a detailed error message
                failed_prerequisites = []
                for statement in action.prerequisites.source_statements:
                    if not statement.validate_condition(source):
                        failed_prerequisites.append(f"Source prerequisite failed: {statement}")
                for statement in action.prerequisites.target_statements:
                    if not statement.validate_condition(target):
                        failed_prerequisites.append(f"Target prerequisite failed: {statement}")
                for statement in action.prerequisites.source_target_statements:
                    if not statement.validate_comparisons(source, target):
                        failed_prerequisites.append(f"Source-Target prerequisite failed: {statement}")
                error_message = "Prerequisites not met:\n" + "\n".join(failed_prerequisites)
                results.append(ActionResult(action_instance=action_instance, success=False, error=error_message, state_before=state_before))

        return ActionsResults(results=results)
    
    def print_grid(self, path: Optional[Path] = None, radius: Optional[Radius] = None, shadow: Optional[Shadow] = None, raycast: Optional[RayCast] = None):
        for y in range(self.height):
            row = ""
            for x in range(self.width):
                node = self.grid[x][y]
                if node.blocks_movement:
                    row += "# "
                elif path and node == path.nodes[0]:
                    row += "\033[92mS\033[0m "  # Green color for start
                elif path and node == path.nodes[-1]:
                    row += "\033[91mG\033[0m "  # Red color for goal
                elif path and node in path.nodes:
                    row += "\033[93m*\033[0m "  # Orange color for path
                elif radius and node in radius.nodes:
                    row += "\033[92mR\033[0m "  # Green color for radius
                elif shadow and node == shadow.source:
                    row += "\033[94mS\033[0m "  # Blue color for shadow source
                elif shadow and node in shadow.nodes:
                    row += "\033[92m+\033[0m "  # Green color for shadow
                elif raycast and node in raycast.nodes:
                    row += "\033[92mR\033[0m "  # Green color for raycast
                # elif node.entities:
                #     row += "E "
                else:
                    row += ". "
            print(row)