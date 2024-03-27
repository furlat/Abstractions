import os
import pygame
import random
from pydantic import BaseModel, Field
from typing import Dict, Tuple, Optional, List, Union
from enum import Enum
from pathlib import Path
from abstractions.goap.spatial import GridMap, GameEntity, BlocksMovement, BlocksLight, Node, Path, Shadow, RayCast, Radius, ActionsPayload, ActionInstance
from abstractions.goap.entity import RegistryHolder
from abstractions.goap.interactions import MoveStep, Character, TestItem, PickupAction, DropAction

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
            elif event.key == pygame.K_x and player_id:
                self.generate_drop_action(player_id)
    
    def generate_drop_action(self, player_id):
        player = GameEntity.get_instance(player_id)
        if player.inventory:
            item_to_drop = player.inventory[-1]  # Drop the last item in the inventory
            drop_action = ActionInstance(source_id=player_id, target_id=item_to_drop.id, action=DropAction())
            self.actions_payload.actions.append(drop_action)

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
        elif event.button == 1:  # Left mouse button
            print("Left mouse button clicked")
            mouse_pos = pygame.mouse.get_pos()
            target_node = renderer.get_node_at_mouse_position(mouse_pos, grid_map)
            if target_node:
                player = GameEntity.get_instance(player_id)
                if target_node == player.node or target_node in player.node.neighbors():
                    for entity in target_node.entities:
                        if isinstance(entity, TestItem):
                            pickup_action = ActionInstance(source_id=player_id, target_id=entity.id, action=PickupAction())
                            return [pickup_action]
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
    ITEM = "item"

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
                # Sort entities based on salience (character > item > wall > floor)
                sorted_entities = sorted(node.entities, key=lambda e: (
                    e.name != "Player",
                    e.name != "TestItem",
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
        elif entity.name == "TestItem":
            return EntityType.ITEM
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
            EntityType.ITEM: os.path.join(base_folder, "sprites", "filled_storage.png")
        }
        return sprite_paths.get(entity_type, "")

    @staticmethod
    def get_ascii_char(entity_type: EntityType) -> str:
        ascii_chars = {
            EntityType.WALL: "#",
            EntityType.FLOOR: ".",
            EntityType.CHARACTER: "@",
            EntityType.ITEM: "$"
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
test_item = TestItem(name="TestItem")
grid_map.get_node(player_pos).add_entity(player)
grid_map.get_node(goal_pos).add_entity(test_item)

start_node = grid_map.get_node(player_pos)
goal_node = grid_map.get_node(goal_pos)
path = grid_map.a_star(start_node, goal_node)
shadow = grid_map.get_shadow(start_node, max_radius=10)
fov_vision = shadow 
# raycast = grid_map.get_raycast(start_node, shadow.nodes[-1])
raycast = None
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
            actions = input_handler.handle_mouse_click(event, player.id, grid_map, renderer)
            if actions:
                if isinstance(actions[0].action, PickupAction):
                    actions_payload = ActionsPayload(actions=actions)
                    actions_results = grid_map.apply_actions_payload(actions_payload)
                    if actions_results.results and actions_results.results[0].success:
                        payload = PayloadGenerator.generate_payload()
                        renderer.update_grid_map_visual(payload)
                else:
                    move_actions = actions
                    action_index = 0

    print(input_handler.actions_payload, Character.get_instance(player.id).inventory)
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