# Combined Text Dir from goap

- Full filepath to the merged directory: `C:\Users\Tommaso\Documents\Dev\Abstractions\abstractions\goap`

- Created: `2024-03-27T15:44:23.000725`

## init

# This is the __init__.py file for the package.


---

## actions

from typing import List, Optional, Dict, Tuple, Callable, Any
from pydantic import BaseModel, Field
from abstractions.goap.entity import Entity, Statement, Attribute
from abstractions.goap.spatial import GameEntity, ActionInstance, Node

class Prerequisites(BaseModel):
    source_statements: List[Statement] = Field(default_factory=list, description="Statements involving only the source entity")
    target_statements: List[Statement] = Field(default_factory=list, description="Statements involving only the target entity")
    source_target_statements: List[Statement] = Field(default_factory=list, description="Statements involving both source and target entities")

    def is_satisfied(self, source: Entity, target: Entity) -> bool:
        return all(statement.validate_condition(source) for statement in self.source_statements) and \
               all(statement.validate_condition(target) for statement in self.target_statements) and \
               all(statement.validate_comparisons(source, target) for statement in self.source_target_statements)

class Consequences(BaseModel):
    source_transformations: Dict[str, Any] = Field(default_factory=dict, description="Attribute transformations for the source entity")
    target_transformations: Dict[str, Any] = Field(default_factory=dict, description="Attribute transformations for the target entity")
   
    def apply(self, source: Entity, target: Entity) -> Tuple[Entity, Entity]:
        updated_source_attributes = {}
        updated_target_attributes = {}
       
        for attr_name, value in self.source_transformations.items():
            if callable(value):
                result = value(source=source, target=target)
                if attr_name == "node" and isinstance(result, Node):
                    updated_source_attributes[attr_name] = result
                else:
                    updated_source_attributes[attr_name] = Attribute(name=attr_name, value=result)
            elif attr_name == "node" and isinstance(value, Node):
                updated_source_attributes[attr_name] = value
            else:
                updated_source_attributes[attr_name] = Attribute(name=attr_name, value=value)
       
        for attr_name, value in self.target_transformations.items():
            if callable(value):
                result = value(source=source, target=target)
                if attr_name == "node" and isinstance(result, Node):
                    updated_target_attributes[attr_name] = result
                else:
                    updated_target_attributes[attr_name] = Attribute(name=attr_name, value=result)
            elif attr_name == "node" and isinstance(value, Node):
                updated_target_attributes[attr_name] = value
            else:
                updated_target_attributes[attr_name] = Attribute(name=attr_name, value=value)
       
        if isinstance(source, GameEntity):
            updated_source = source.update_attributes(updated_source_attributes)
        else:
            updated_source = source
       
        if isinstance(target, GameEntity):
            updated_target = target.update_attributes(updated_target_attributes)
        else:
            updated_target = target
       
        return updated_source, updated_target
    
class Action(BaseModel):
    name: str = Field("", description="The name of the action")
    prerequisites: Prerequisites = Field(default_factory=Prerequisites, description="The prerequisite conditions for the action")
    consequences: Consequences = Field(default_factory=Consequences, description="The consequences of the action")

    def is_applicable(self, source: Entity, target: Entity) -> bool:
        return self.prerequisites.is_satisfied(source, target)

    def apply(self, source: Entity, target: Entity) -> Tuple[Entity, Entity]:
        if not self.is_applicable(source, target):
            raise ValueError("Action prerequisites are not met")

        updated_source, updated_target = self.consequences.apply(source, target)

        if updated_source != source:
            self.propagate_spatial_consequences(updated_source, updated_target)
            self.propagate_inventory_consequences(updated_source, updated_target)
        else:
            updated_source = source

        if updated_target != target:
            self.propagate_spatial_consequences(updated_source, updated_target)
            self.propagate_inventory_consequences(updated_source, updated_target)
        else:
            updated_target = target

        return updated_source, updated_target

    def propagate_spatial_consequences(self, source: Entity, target: Entity) -> None:
        # Implement spatial consequence propagation logic here
        pass

    def propagate_inventory_consequences(self, source: Entity, target: Entity) -> None:
        # Implement inventory consequence propagation logic here
        pass
ActionInstance.model_rebuild()

---

## entity

from pydantic import BaseModel, Field, ValidationError, validator, field_validator, ValidationInfo
from typing import Annotated, Any, Dict, List, Optional, Set, Union, Tuple, Callable
from pydantic.functional_validators import AfterValidator
import uuid


class RegistryHolder:
    _registry: Dict[str, 'RegistryHolder'] = {}
    _types : Set[type] = set()

    @classmethod
    def register(cls, instance: 'RegistryHolder'):
        cls._registry[instance.id] = instance
        cls._types.add(type(instance))

    @classmethod
    def get_instance(cls, instance_id: str):
        return cls._registry.get(instance_id)

    @classmethod
    def all_instances(cls, filter_type=True):
        if filter_type:
            return [instance for instance in cls._registry.values() if isinstance(instance, cls)]
        return list(cls._registry.values())
    @classmethod
    def all_instances_by_type(cls, type: type):
        return [instance for instance in cls._registry.values() if isinstance(instance, type)]
    @classmethod
    def all_types(cls, as_string=True):
        if as_string:
            return [type_name.__name__ for type_name in cls._types]
        return cls._types
        

class Attribute(BaseModel, RegistryHolder):
    name: str = Field("", description="The name of the attribute")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="The unique identifier of the attribute")
    value: Any

    def __init__(self, **data: Any):
        super().__init__(**data)
        if not self.name:
            self.name = self.__class__.__name__
        self.register(self)



class Entity(BaseModel, RegistryHolder):
    name: str = Field("", description="The name of the entity")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="The unique identifier of the entity")

    def __init__(self, **data: Any):
        super().__init__(**data)
        if not self.name:
            self.name = self.__class__.__name__
        self.register(self)
        
    
    @field_validator('*', mode='after')
    def check_attributes_and_entities(cls, v: Any, info: ValidationInfo):
        if info.field_name not in ['id', 'name',"node"] and not isinstance(v, (Attribute, Entity)):
            raise ValueError(f"Attributes must be instances of Attribute or Entity, got {type(v).__name__} for field {info.field_name}")
        return v

    
    def all_attributes(self) -> Dict[str, 'Attribute']:
        attributes = {}
        for attribute_name, attribute_value in self.__dict__.items():
            if isinstance(attribute_value, Attribute):
                attributes[attribute_name] = attribute_value
            elif isinstance(attribute_value, Entity):
                nested_attributes = attribute_value.all_attributes()
                attributes.update(nested_attributes)
        return attributes
    

class Statement(BaseModel, RegistryHolder):
    name: str = Field("", description="The name of the statement")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="The unique identifier of the entity")
    conditions: Dict[str, Any] = Field(default_factory=dict, description="The desired attribute conditions for the statement")
    comparisons: Dict[str, Tuple[str, str, Callable[[Any, Any], bool]]] = Field(default_factory=dict, description="The attribute comparisons for the statement")

    def __init__(self, **data: Any):
        super().__init__(**data)
        if not self.name:
            self.name = self.__class__.__name__
        self.register(self)

    @classmethod
    def from_entity(cls, entity: Entity, name: Optional[str] = None, conditions: Optional[Dict[str, Any]] = None, comparisons: Optional[Dict[str, Tuple[str, str, Callable[[Any, Any], bool]]]] = None):
        attributes = entity.all_attributes()
        return cls(name=name, conditions=conditions or {}, comparisons=comparisons or {}, **attributes)

    @classmethod
    def from_entities(cls, source: Entity, target: Entity, name: Optional[str] = None, conditions: Optional[Dict[str, Any]] = None, comparisons: Optional[Dict[str, Tuple[str, str, Callable[[Any, Any], bool]]]] = None):
        source_attributes = source.all_attributes()
        target_attributes = target.all_attributes()
        attributes = {f"source_{k}": v for k, v in source_attributes.items()}
        attributes.update({f"target_{k}": v for k, v in target_attributes.items()})
        return cls(name=name, conditions=conditions or {}, comparisons=comparisons or {}, **attributes)

    def validate_condition(self, entity: Entity) -> bool:
        attributes = entity.all_attributes()
        for attr_name, desired_value in self.conditions.items():
            if attr_name not in attributes or attributes[attr_name].value != desired_value:
                return False
        return True

    def validate_comparisons(self, source: Entity, target: Entity) -> bool:
        for comparison_name, (source_attr, target_attr, comparison_func) in self.comparisons.items():
            source_value = getattr(source, source_attr, None)
            target_value = getattr(target, target_attr, None)
            if source_value is None or target_value is None:
                return False
            elif source_attr == "node" and target_attr == "node":
                if not comparison_func(source_value, target_value):
                    return False
                return True
            elif not comparison_func(source_value.value, target_value.value):
                return False
        return True
    


---

## game

import os
import pygame
import random
from pydantic import BaseModel, Field
from typing import Dict, Tuple, Optional, List, Union
from enum import Enum
from pathlib import Path
from abstractions.goap.spatial import GridMap, GameEntity, BlocksMovement, BlocksLight, Node, Path, Shadow, RayCast, Radius, ActionsPayload, ActionInstance
from abstractions.goap.entity import RegistryHolder
from abstractions.goap.movement import MoveStep, Character

from abstractions.goap.procedural import generate_dungeon

class CameraControl(BaseModel):
    move: Tuple[int, int] = (0, 0)
    zoom: int = 0
    recenter: bool = False
    toggle_path: bool = False
    toggle_shadow: bool = False
    toggle_raycast: bool = False
    toggle_radius: bool = False
    toggle_ascii: bool = False
    toggle_fov: bool = False

class InputHandler:
    def __init__(self):
        self.camera_control = CameraControl()
        self.actions_payload = ActionsPayload(actions=[])

    def handle_input(self, event, player_id: Optional[str] = None):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                self.camera_control.zoom = 1  # Zoom in
            elif event.key == pygame.K_2:
                self.camera_control.zoom = -1  # Zoom out
            elif event.key == pygame.K_LEFT:
                self.camera_control.move = (-1, 0)  # Move camera left
            elif event.key == pygame.K_RIGHT:
                self.camera_control.move = (1, 0)  # Move camera right
            elif event.key == pygame.K_UP:
                self.camera_control.move = (0, -1)  # Move camera up
            elif event.key == pygame.K_DOWN:
                self.camera_control.move = (0, 1)  # Move camera down
            elif event.key == pygame.K_SPACE:
                self.camera_control.recenter = True  # Recenter the camera on the player
            elif event.key == pygame.K_p:
                self.camera_control.toggle_path = True
            elif event.key == pygame.K_t:
                self.camera_control.toggle_shadow = True
            elif event.key == pygame.K_c:
                self.camera_control.toggle_raycast = True
            elif event.key == pygame.K_r:
                self.camera_control.toggle_radius = True
            elif event.key == pygame.K_q:
                self.camera_control.toggle_ascii = True
            elif event.key == pygame.K_f:
                self.camera_control.toggle_fov = True
            elif event.key == pygame.K_w and player_id: 
                self.generate_move_step(player_id, (0, -1))  # Move up
            elif event.key == pygame.K_s and player_id:
                self.generate_move_step(player_id, (0, 1))  # Move down
            elif event.key == pygame.K_a and player_id:
                self.generate_move_step(player_id, (-1, 0))  # Move left
            elif event.key == pygame.K_d and player_id:
                self.generate_move_step(player_id, (1, 0))  # Move right

    def handle_mouse_click(self, event, player_id, grid_map: GridMap, renderer: 'Renderer'):
        if event.button == 3:  # Right mouse button
            mouse_pos = pygame.mouse.get_pos()
            target_node = renderer.get_node_at_mouse_position(mouse_pos, grid_map)
            if target_node:
                player = GameEntity.get_instance(player_id)
                start_node = player.node
                path = grid_map.a_star(start_node, target_node)
                if path:
                    move_actions = self.generate_move_actions(player_id, path)
                    return move_actions
        return []

    def generate_move_actions(self, player_id, path):
        move_actions = []
        for i in range(len(path.nodes) - 1):
            source_node = path.nodes[i]
            target_node = path.nodes[i + 1]
            floor_entities = [entity for entity in target_node.entities if entity.name.startswith("Floor")]
            if floor_entities:
                target_id = floor_entities[0].id
                move_action = ActionInstance(source_id=player_id, target_id=target_id, action=MoveStep())
                move_actions.append(move_action)
        return move_actions
    
    def generate_move_step(self, player_id, direction):
        player = GameEntity.get_instance(player_id)
        current_node = player.node
        target_position = (current_node.position.x + direction[0], current_node.position.y + direction[1])
        target_node = current_node.grid_map.get_node(target_position)
        if target_node:
            floor_entities = [entity for entity in target_node.entities if entity.name.startswith("Floor")]
            if floor_entities:
                target_id = floor_entities[0].id
                move_action = ActionInstance(source_id=player_id, target_id=target_id, action=MoveStep())
                self.actions_payload.actions.append(move_action)

    def reset_actions_payload(self):
        self.actions_payload = ActionsPayload(actions=[])
    
    def reset_camera_control(self):
        self.camera_control = CameraControl()

    def reset(self):
        self.reset_actions_payload()
        # self.camera_control.recenter = False
        
    

class EntityType(Enum):
    FLOOR = "floor"
    WALL = "wall"
    CHARACTER = "character"
    GOAL = "goal"

class EntityVisual(BaseModel):
    type: EntityType
    sprite_path: Optional[str] = Field(None, description="Path to the sprite image file")
    ascii_char: Optional[str] = Field(None, description="ASCII character representation")

class NodeVisual(BaseModel):
    entity_visuals: List[EntityVisual] = Field(default_factory=list, description="List of entity visuals in the node")

class GridMapVisual(BaseModel):
    width: int = Field(..., description="Width of the grid map")
    height: int = Field(..., description="Height of the grid map")
    node_visuals: Dict[Tuple[int, int], NodeVisual] = Field({}, description="Dictionary mapping node positions to their visuals")

    def update_node_visual(self, position: Tuple[int, int], entity_visuals: List[EntityVisual]):
        self.node_visuals[position] = NodeVisual(entity_visuals=entity_visuals)

class Renderer:
    def __init__(self, grid_map_visual: GridMapVisual, cell_size: int, player_position: Tuple[int, int]):
        self.grid_map_visual = grid_map_visual
        self.cell_size = cell_size
        self.sprite_cache = {}
        self.ascii_mode = False
        self.camera_pos = list(player_position)  # Camera position in grid coordinates

        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))  # Set the screen size
        self.grid_surface = pygame.Surface((grid_map_visual.width * cell_size, grid_map_visual.height * cell_size))
        self.grid_surface.convert()
        self.font = pygame.font.Font(None, cell_size)
        self.fov_mode = False
        self.show_path = False
        self.show_shadow = False
        self.show_raycast = False
        self.show_radius = False

    def update_grid_map_visual(self, grid_map_visual: GridMapVisual):
        self.grid_map_visual = grid_map_visual

    def update_player_position(self, player_position: Tuple[int, int]):
        self.camera_pos = list(player_position)


    def render(self, camera_control: CameraControl, path: Optional[Path] = None, shadow: Optional[Shadow] = None, raycast: Optional[RayCast] = None, radius: Optional[Radius] = None,fov_vision: Optional[Union[Shadow, Radius]] = None):
        # Update camera position based on camera control
        self.camera_pos[0] = max(0, min(self.grid_map_visual.width - 1, self.camera_pos[0] + camera_control.move[0]))
        self.camera_pos[1] = max(0, min(self.grid_map_visual.height - 1, self.camera_pos[1] + camera_control.move[1]))

        # Update cell size based on camera control
        if camera_control.zoom != 0:
            self.cell_size = max(16, min(64, self.cell_size + camera_control.zoom * 8))
            self.font = pygame.font.Font(None, self.cell_size)
            self.sprite_cache.clear()  # Clear the sprite cache when zooming

        # Recenter camera on player if requested
        if camera_control.recenter:
            self.center_camera_on_player()

        if camera_control.toggle_ascii:
            self.ascii_mode = not self.ascii_mode

        self.grid_surface.fill((0, 0, 0))  # Clear the grid surface

        # Calculate the visible range based on the camera position and screen size
        start_x = max(0, self.camera_pos[0] - self.screen.get_width() // (2 * self.cell_size))
        start_y = max(0, self.camera_pos[1] - self.screen.get_height() // (2 * self.cell_size))
        end_x = min(self.grid_map_visual.width, start_x + self.screen.get_width() // self.cell_size + 1)
        end_y = min(self.grid_map_visual.height, start_y + self.screen.get_height() // self.cell_size + 1)

        if camera_control.toggle_fov:
            self.fov_mode = not self.fov_mode

        for x in range(start_x, end_x):
            for y in range(start_y, end_y):
                position = (x, y)
                if position in self.grid_map_visual.node_visuals:
                    node_visual = self.grid_map_visual.node_visuals[position]
                    if not self.fov_mode or (fov_vision and position in [node.position.value for node in fov_vision.nodes]):
                        screen_x = (x - start_x) * self.cell_size
                        screen_y = (y - start_y) * self.cell_size

                        if self.ascii_mode:
                            if node_visual.entity_visuals:
                                # Draw the most salient entity in ASCII mode
                                ascii_char = node_visual.entity_visuals[0].ascii_char
                                ascii_surface = self.font.render(ascii_char, True, (255, 255, 255))
                                ascii_rect = ascii_surface.get_rect(center=(screen_x + self.cell_size // 2, screen_y + self.cell_size // 2))
                                self.grid_surface.blit(ascii_surface, ascii_rect)
                        else:
                            # Draw all entities in sprite mode (in opposite salience order)
                            for entity_visual in reversed(node_visual.entity_visuals):
                                sprite_path = entity_visual.sprite_path
                                sprite_surface = self.load_sprite(sprite_path)
                                scaled_sprite_surface = pygame.transform.scale(sprite_surface, (self.cell_size, self.cell_size))
                                self.grid_surface.blit(scaled_sprite_surface, (screen_x, screen_y))
        if camera_control.toggle_path:
            self.show_path = not self.show_path
        if camera_control.toggle_shadow:
            self.show_shadow = not self.show_shadow
        if camera_control.toggle_raycast:
            self.show_raycast = not self.show_raycast
        if camera_control.toggle_radius:
            self.show_radius = not self.show_radius
        # Draw path
        if self.show_path and path:
            for node in path.nodes:
                x, y = node.position.value
                if start_x <= x < end_x and start_y <= y < end_y:
                    screen_x = (x - start_x) * self.cell_size
                    screen_y = (y - start_y) * self.cell_size
                    pygame.draw.rect(self.grid_surface, (0, 255, 0), (screen_x, screen_y, self.cell_size, self.cell_size), 2)

        # Draw shadow
        if self.show_shadow and shadow:
            for node in shadow.nodes:
                x, y = node.position.value
                if start_x <= x < end_x and start_y <= y < end_y:
                    screen_x = (x - start_x) * self.cell_size
                    screen_y = (y - start_y) * self.cell_size
                    pygame.draw.rect(self.grid_surface, (255, 255, 0), (screen_x, screen_y, self.cell_size, self.cell_size), 2)

        # Draw raycast
        if self.show_raycast and raycast:
            for node in raycast.nodes:
                x, y = node.position.value
                if start_x <= x < end_x and start_y <= y < end_y:
                    screen_x = (x - start_x) * self.cell_size
                    screen_y = (y - start_y) * self.cell_size
                    pygame.draw.rect(self.grid_surface, (255, 0, 0), (screen_x, screen_y, self.cell_size, self.cell_size), 2)

        # Draw radius
        if self.show_radius and radius:
            for node in radius.nodes:
                x, y = node.position.value
                if start_x <= x < end_x and start_y <= y < end_y:
                    screen_x = (x - start_x) * self.cell_size
                    screen_y = (y - start_y) * self.cell_size
                    pygame.draw.rect(self.grid_surface, (0, 0, 255), (screen_x, screen_y, self.cell_size, self.cell_size), 2)

        self.screen.blit(self.grid_surface, (0, 0))
        pygame.display.flip()

    def get_node_at_mouse_position(self, mouse_position: Tuple[int, int], grid_map: GridMap) -> Optional[Node]:
        x, y = mouse_position
        start_x = max(0, self.camera_pos[0] - self.screen.get_width() // (2 * self.cell_size))
        start_y = max(0, self.camera_pos[1] - self.screen.get_height() // (2 * self.cell_size))
        grid_x = start_x + x // self.cell_size
        grid_y = start_y + y // self.cell_size
        if 0 <= grid_x < grid_map.width and 0 <= grid_y < grid_map.height:
            return grid_map.get_node((grid_x, grid_y))
        return None

    def update_camera_position(self, player_position: Tuple[int, int]):
        self.camera_pos = list(player_position)

    def center_camera_on_player(self):
        player_position = self.find_player_position()
        if player_position:
            self.update_camera_position(player_position)
    def find_player_position(self) -> Optional[Tuple[int, int]]:
        for position, node_visual in self.grid_map_visual.node_visuals.items():
            for entity_visual in node_visual.entity_visuals:
                if entity_visual.type == EntityType.CHARACTER:
                    return position
        return None

    def load_sprite(self, sprite_path: str) -> pygame.Surface:
        if sprite_path not in self.sprite_cache:
            sprite_surface = pygame.image.load(sprite_path).convert_alpha()
            self.sprite_cache[sprite_path] = sprite_surface
        return self.sprite_cache[sprite_path]
    

base_folder = r"C:\Users\Tommaso\Documents\Dev\Abstractions\abstractions\goap"

class PayloadGenerator:
    @staticmethod
    def generate_payload() -> GridMapVisual:
        nodes = RegistryHolder.all_instances_by_type(Node)
        node_visuals = {}
        for node in nodes:
            position = node.position.value
            entity_visuals = []
            if node.entities:
                # Sort entities based on salience (character > goal > wall > floor)
                sorted_entities = sorted(node.entities, key=lambda e: (
                    e.name != "Player",
                    e.name != "Goal",
                    not (e.blocks_movement.value and e.blocks_light.value),
                    e.blocks_movement.value or e.blocks_light.value
                ))
                for entity in sorted_entities:
                    entity_type = PayloadGenerator.get_entity_type(entity)
                    entity_visual = EntityVisual(
                        type=entity_type,
                        sprite_path=PayloadGenerator.get_sprite_path(entity_type),
                        ascii_char=PayloadGenerator.get_ascii_char(entity_type)
                    )
                    entity_visuals.append(entity_visual)
            node_visuals[position] = NodeVisual(entity_visuals=entity_visuals)
        width = max(node.position.x for node in nodes) + 1
        height = max(node.position.y for node in nodes) + 1
        payload = GridMapVisual(
            width=width,
            height=height,
            node_visuals=node_visuals
        )
        return payload

    @staticmethod
    def get_entity_type(entity: GameEntity) -> EntityType:
        if entity.name == "Player":
            return EntityType.CHARACTER
        elif entity.name == "Goal":
            return EntityType.GOAL
        elif entity.blocks_movement.value and entity.blocks_light.value:
            return EntityType.WALL
        else:
            return EntityType.FLOOR

    @staticmethod
    def get_sprite_path(entity_type: EntityType) -> str:
        sprite_paths = {
            EntityType.WALL: os.path.join(base_folder, "sprites", "wall.png"),
            EntityType.FLOOR: os.path.join(base_folder, "sprites", "floor.png"),
            EntityType.CHARACTER: os.path.join(base_folder, "sprites", "character_agent.png"),
            EntityType.GOAL: os.path.join(base_folder, "sprites", "full_storage.png")
        }
        return sprite_paths.get(entity_type, "")

    @staticmethod
    def get_ascii_char(entity_type: EntityType) -> str:
        ascii_chars = {
            EntityType.WALL: "#",
            EntityType.FLOOR: ".",
            EntityType.CHARACTER: "@",
            EntityType.GOAL: "$"
        }
        return ascii_chars.get(entity_type, " ")



# Create a larger grid map
grid_map = GridMap(width=50, height=50)

# Fill the grid map with walls
for x in range(grid_map.width):
    for y in range(grid_map.height):
        wall = GameEntity(name=f"Wall_{x}_{y}", blocks_movement=BlocksMovement(value=True), blocks_light=BlocksLight(value=True))
        grid_map.get_node((x, y)).add_entity(wall)

# Generate the dungeon
num_rooms = 10
min_room_size = 5
max_room_size = 10
generate_dungeon(grid_map, num_rooms, min_room_size, max_room_size)

# Find valid floor tiles for player and goal
floor_tiles = [(x, y) for x in range(grid_map.width) for y in range(grid_map.height) if any(isinstance(entity, GameEntity) and entity.name.startswith("Floor") for entity in grid_map.get_node((x, y)).entities)]
player_pos, goal_pos = random.sample(floor_tiles, 2)

# Place the player and goal entities
player = Character(name="Player")
goal = GameEntity(name="Goal")
grid_map.get_node(player_pos).add_entity(player)
grid_map.get_node(goal_pos).add_entity(goal)
# Precompute payloads
start_node = grid_map.get_node(player_pos)
goal_node = grid_map.get_node(goal_pos)
path = grid_map.a_star(start_node, goal_node)
shadow = grid_map.get_shadow(start_node, max_radius=10)
fov_vision = shadow 
raycast = grid_map.get_raycast(start_node, shadow.nodes[-1])
radius = grid_map.get_radius(start_node, max_radius=5)
# Generate the payload
payload = PayloadGenerator.generate_payload()

# Create the renderer
renderer = Renderer(payload, cell_size=32, player_position=player_pos)


input_handler = InputHandler()

clock = pygame.time.Clock()
running = True
move_actions = []
action_index = 0

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            input_handler.handle_input(event, player.id)
        elif event.type == pygame.MOUSEMOTION:
            mouse_pos = pygame.mouse.get_pos()
            target_node = renderer.get_node_at_mouse_position(mouse_pos, grid_map)
            if target_node:
                try:
                    print(f'trying to pathfind to {target_node.position}')
                    start_node = grid_map.get_node(player_pos)
                    path = grid_map.a_star(start_node, target_node)
                except Exception as e:
                    print(f"pathfind failed: {str(e)}")
                    path = None
                try:
                    print('trying to raycast')
                    start_node = grid_map.get_node(player_pos)
                    raycast = grid_map.get_raycast(start_node, target_node)
                except Exception as e:
                    print(f"raycast failed: {str(e)}")
                    raycast = None
        elif event.type == pygame.MOUSEBUTTONDOWN:
            move_actions = input_handler.handle_mouse_click(event, player.id, grid_map, renderer)
            action_index = 0

    print(input_handler.actions_payload)

    if move_actions and action_index < len(move_actions):
        action = move_actions[action_index]
        actions_payload = ActionsPayload(actions=[action])
        actions_results = grid_map.apply_actions_payload(actions_payload)
        if actions_results.results and actions_results.results[0].success:
            updated_player = GameEntity.get_instance(player.id)
            player_pos = updated_player.node.position.value
            radius = grid_map.get_radius(grid_map.get_node(player_pos), max_radius=10)
            shadow = grid_map.get_shadow(grid_map.get_node(player_pos), max_radius=10)
            payload = PayloadGenerator.generate_payload()
            renderer.update_grid_map_visual(payload)
            action_index += 1
    else:
        actions_results = grid_map.apply_actions_payload(input_handler.actions_payload)
        if actions_results.results and actions_results.results[0].success:
            updated_player = GameEntity.get_instance(player.id)
            player_pos = updated_player.node.position.value
            radius = grid_map.get_radius(grid_map.get_node(player_pos), max_radius=10)
            shadow = grid_map.get_shadow(grid_map.get_node(player_pos), max_radius=10)
            payload = PayloadGenerator.generate_payload()
            renderer.update_grid_map_visual(payload)

    renderer.render(input_handler.camera_control, path=path, shadow=shadow, raycast=raycast, radius=radius, fov_vision=shadow)
    input_handler.reset_camera_control()
    input_handler.reset()
    clock.tick(60)  # Limit the frame rate to 60 FPS

    # Display FPS
    fps = clock.get_fps()
    fps_text = renderer.font.render(f"FPS: {fps:.2f}", True, (255, 255, 255))
    renderer.screen.blit(fps_text, (10, 10))
    pygame.display.flip()

pygame.quit()

---

## movement

from abstractions.goap.actions import Action, Prerequisites, Consequences
from abstractions.goap.entity import Attribute, Statement
from abstractions.goap.spatial import GameEntity, Node
from typing import Callable

def source_node_comparison(source: Node, target: Node) -> bool:

    return source in target.neighbors()

def target_walkable_comparison(source: GameEntity, target: GameEntity) -> bool:
    return not target.blocks_movement.value

def move_to_target_node(source: GameEntity, target: GameEntity) -> Node:
    return target.node

MoveToTargetNode: Callable[[GameEntity, GameEntity], Node] = move_to_target_node

class MoveStep(Action):
    name: str = "Move Step"
    prerequisites: Prerequisites = Prerequisites(
        source_statements=[Statement(conditions={"can_act": True})],
        target_statements=[Statement(conditions={"blocks_movement": False})],
        source_target_statements=[Statement(comparisons={
            "source_position": ("node", "node", source_node_comparison)
        })]
    )
    consequences: Consequences = Consequences(
        source_transformations={"node": MoveToTargetNode}
    )

class Character(GameEntity):
    can_act: Attribute = Attribute(name="can_act", value=True)

---

## procedural

from abstractions.goap.spatial import GameEntity, Node, Position, GridMap, ActionsPayload, ActionInstance, ActionsResults, Path, BlocksMovement, BlocksLight
from typing import List, Dict, Any, Optional
import random

def create_room(grid_map, top_left, width, height):
    for x in range(top_left[0], top_left[0] + width):
        for y in range(top_left[1], top_left[1] + height):
            grid_map.get_node((x, y)).reset()
            floor = GameEntity(name=f"Floor_{x}_{y}", blocks_movement=BlocksMovement(value=False), blocks_light=BlocksLight(value=False))
            grid_map.get_node((x, y)).add_entity(floor)

def create_h_corridor(grid_map, x1, x2, y):
    for x in range(min(x1, x2), max(x1, x2) + 1):
        grid_map.get_node((x, y)).reset()
        floor = GameEntity(name=f"Floor_{x}_{y}", blocks_movement=BlocksMovement(value=False), blocks_light=BlocksLight(value=False))
        grid_map.get_node((x, y)).add_entity(floor)

def create_v_corridor(grid_map, y1, y2, x):
    for y in range(min(y1, y2), max(y1, y2) + 1):
        grid_map.get_node((x, y)).reset()
        floor = GameEntity(name=f"Floor_{x}_{y}", blocks_movement=BlocksMovement(value=False), blocks_light=BlocksLight(value=False))
        grid_map.get_node((x, y)).add_entity(floor)

def generate_dungeon(grid_map, num_rooms, min_room_size, max_room_size):
    rooms = []
    for _ in range(num_rooms):
        width = random.randint(min_room_size, max_room_size)
        height = random.randint(min_room_size, max_room_size)
        x = random.randint(1, grid_map.width - width - 1)
        y = random.randint(1, grid_map.height - height - 1)
        create_room(grid_map, (x, y), width, height)
        rooms.append((x, y, width, height))
    for i in range(len(rooms) - 1):
        x1, y1, w1, h1 = rooms[i]
        x2, y2, w2, h2 = rooms[i + 1]
        if random.random() < 0.5:
            create_h_corridor(grid_map, x1 + w1, x2, y1 + h1 // 2)
            create_v_corridor(grid_map, y1 + h1 // 2, y2 + h2 // 2, x2)
        else:
            create_v_corridor(grid_map, y1 + h1 // 2, y2, x1 + w1 // 2)
            create_h_corridor(grid_map, x1 + w1 // 2, x2 + w2 // 2, y2)

---

## spatial

from __future__ import annotations
from abstractions.goap.entity import Entity, Attribute, RegistryHolder
from typing import List, Tuple, TYPE_CHECKING, Optional, Any, ForwardRef, Dict, Union
from pydantic import Field, BaseModel, validator, ConfigDict, ValidationInfo, field_validator
import uuid
import math

if TYPE_CHECKING:
    # from abstractions.goap.spatial import Node
    from abstractions.goap.actions import Action

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
    
class Radius(BaseModel):
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

class Shadow(BaseModel):
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
        if has_path:
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

class ActionResult(BaseModel):
    action_instance: ActionInstance
    success: bool
    error: str = None

class ActionsResults(BaseModel):
    results: List[ActionResult]


class GameEntity(Entity):
    blocks_movement: BlocksMovement = Field(default_factory=BlocksMovement, description="Attribute indicating if the entity blocks movement")
    blocks_light: BlocksLight = Field(default_factory=BlocksLight, description="Attribute indicating if the entity blocks light")
    node: Node = Field(default=None, description="The node the entity is currently in")

    @property
    def position(self) -> Position:
        if self.node:
            return self.node.position
        return Position()

    def set_node(self, node: Node):
        self.node = node
        node.add_entity(self)

    def remove_from_node(self):
        if self.node:
            self.node.remove_entity(self)
            self.node = None

    def update_attributes(self, attributes: Dict[str, Union[Attribute, Node]]) -> "GameEntity":
        updated_attributes = {"name": self.name}  # Preserve the name attribute
        new_node = None
        for attr_name, value in attributes.items():
            if attr_name == "node" and isinstance(value, Node):
                new_node = value
            elif isinstance(value, Attribute):
                updated_attributes[attr_name] = value
        if new_node:
            if self.node:
                self.node.remove_entity(self)  # Remove the entity from its current node
            new_node.add_entity(self)  # Add the entity to the new node
            self.node = new_node  # Update the entity's node reference
        for attr_name, value in updated_attributes.items():
            setattr(self, attr_name, value)  # Update the entity's attributes
        return self

    
    def __repr__(self):
        attrs = {}
        for key, value in self.__dict__.items():
            if key == 'node' and value is not None:
                attrs[key] = value.non_verbose_repr()
            elif key != 'node':
                attrs[key] = value
        attrs_str = ', '.join(f'{k}={v}' for k, v in attrs.items())
        return f"{self.__class__.__name__}({attrs_str})"

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
        self.entities.append(entity)
        entity.node = self
        self.update_blocking_properties()
    
    def remove_entity(self, entity: GameEntity):
        self.entities.remove(entity)
        entity.node = None
        self.update_blocking_properties()
    
    def update_blocking_properties(self):
        self.blocks_movement = any(entity.blocks_movement.value for entity in self.entities)
        self.blocks_light = any(entity.blocks_light.value for entity in self.entities)
    
    def reset(self):
        self.entities.clear()
        self.blocks_movement = False
        self.blocks_light = False
    
    def neighbors(self) -> List[Node]:
        if self.grid_map:
            return self.grid_map.get_neighbors(self.position.value)
        return []
    
    def update_entity(self, old_entity: GameEntity, new_entity: GameEntity):
        self.remove_entity(old_entity)
        self.add_entity(new_entity)

import heapq

class GridMap:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.grid: List[List[Node]] = [[Node(position=Position(value=(x, y)), grid_map=self) for y in range(height)] for x in range(width)]

    def get_node(self, position: Tuple[int, int]) -> Node:
        x, y = position
        return self.grid[x][y]

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
    
    def apply_actions_payload(self, payload: ActionsPayload) -> ActionsResults:
        results = []
        if len(payload.actions) >0:
            print(f"Applying {len(payload.actions)} actions")
        for action_instance in payload.actions:
            source = GameEntity.get_instance(action_instance.source_id)
            target = GameEntity.get_instance(action_instance.target_id)
            action = action_instance.action
            
            if action.is_applicable(source, target):
                try:
                    updated_source, updated_target = action.apply(source, target)
                    results.append(ActionResult(action_instance=action_instance, success=True))
                except ValueError as e:
                    results.append(ActionResult(action_instance=action_instance, success=False, error=str(e)))
                    break
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
                results.append(ActionResult(action_instance=action_instance, success=False, error=error_message))
                break
    
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

---

