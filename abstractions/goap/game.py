import os
import pygame
import random
from pydantic import BaseModel, Field
from typing import Dict, Tuple, Optional, List, Union
from enum import Enum
from pathlib import Path
from abstractions.goap.spatial import GridMap, GameEntity, BlocksMovement, BlocksLight, Node, Path, Shadow, RayCast, Radius
from abstractions.goap.entity import RegistryHolder



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

    def handle_input(self, event):
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
            elif event.key == pygame.K_s:
                self.camera_control.toggle_shadow = True
            elif event.key == pygame.K_c:
                self.camera_control.toggle_raycast = True
            elif event.key == pygame.K_r:
                self.camera_control.toggle_radius = True
            elif event.key == pygame.K_q:
                self.camera_control.toggle_ascii = True
            elif event.key == pygame.K_f:
                self.camera_control.toggle_fov = True

    def reset(self):
        self.camera_control = CameraControl()

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

    def center_camera_on_player(self):
        player_position = self.find_player_position()
        if player_position:
            self.camera_pos = list(player_position)

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
player = GameEntity(name="Player")
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
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            input_handler.handle_input(event)
        elif event.type == pygame.MOUSEMOTION:
            mouse_pos = pygame.mouse.get_pos()
            target_node = renderer.get_node_at_mouse_position(mouse_pos, grid_map)
            if target_node:
                try:
                    print(f'trying to pathfind to {target_node.position}')
                    path = grid_map.a_star(start_node, target_node)
                except Exception as e:
                    print(f"pathfind failed: {str(e)}")
                    path = None
                try:
                    print('trying to raycast')
                    raycast = grid_map.get_raycast(start_node, target_node)
                except Exception as e:
                    print(f"raycast failed: {str(e)}")
                    raycast = None
    
    renderer.render(input_handler.camera_control, path=path, shadow=shadow, raycast=raycast, radius=radius, fov_vision=fov_vision)
    input_handler.reset()
    clock.tick(60)  # Limit the frame rate to 60 FPS
    
    # Display FPS
    fps = clock.get_fps()
    fps_text = renderer.font.render(f"FPS: {fps:.2f}", True, (255, 255, 255))
    renderer.screen.blit(fps_text, (10, 10))
    pygame.display.flip()

pygame.quit()