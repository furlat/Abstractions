import pygame
from pygame.sprite import Group, RenderUpdates
from typing import Dict, List, Type, Tuple, Optional
from pydantic import BaseModel
from abstractions.goap.nodes import Node
from abstractions.goap.shapes import Path, Shadow, RayCast, Radius

class CameraControl(BaseModel):
    move: Tuple[int, int] = (0, 0)
    zoom: int = 0
    recenter: bool = False
    toggle_path: bool = False
    toggle_shadow: bool = False
    toggle_raycast: bool = False
    toggle_radius: bool = False
    toggle_fov: bool = True
    toggle_ascii: bool = False

class EntityVisual(BaseModel):
    sprite_path: str
    ascii_char: str
    draw_order: int

class NodeVisual(BaseModel):
    entity_visuals: List[EntityVisual]

class GridMapVisual(BaseModel):
    width: int
    height: int
    node_visuals: Dict[Tuple[int, int], NodeVisual]

class Widget(pygame.sprite.Sprite):
    def __init__(self, pos: Tuple[int, int], size: Tuple[int, int]):
        super().__init__()
        self.image = pygame.Surface(size)
        self.rect = self.image.get_rect(topleft=pos)

    def update(self, camera_control: CameraControl):
        pass

    def draw(self, surface: pygame.Surface):
        surface.blit(self.image, self.rect)

class GridMapWidget(Widget):
    def __init__(self, pos: Tuple[int, int], size: Tuple[int, int], grid_map_visual: GridMapVisual):
        super().__init__(pos, size)
        self.grid_map_visual = grid_map_visual
        self.cell_size = 32
        self.camera_pos = [0, 0]  # Camera position in grid coordinates
        self.show_path = False
        self.show_shadow = False
        self.show_raycast = False
        self.show_radius = False
        self.show_fov = False
        self.sprite_cache: Dict[str, pygame.Surface] = {}
        self.font = pygame.font.Font(None, self.cell_size)
    

    def grid_to_screen(self, grid_x: int, grid_y: int) -> Tuple[int, int]:
        screen_x = (grid_x - self.camera_pos[0]) * self.cell_size
        screen_y = (grid_y - self.camera_pos[1]) * self.cell_size
        return screen_x, screen_y

    def update(self, camera_control: CameraControl, player_position: Tuple[int, int]):
        # Update camera position based on camera control
        self.camera_pos[0] += camera_control.move[0]
        self.camera_pos[1] += camera_control.move[1]
        self.camera_pos[0] = max(0, min(self.grid_map_visual.width - self.rect.width // self.cell_size, self.camera_pos[0]))
        self.camera_pos[1] = max(0, min(self.grid_map_visual.height - self.rect.height // self.cell_size, self.camera_pos[1]))

        # Update cell size based on camera control
        if camera_control.zoom != 0:
            self.cell_size = max(16, min(64, self.cell_size + camera_control.zoom * 8))
            self.font = pygame.font.Font(None, self.cell_size)

        # Recenter camera on player if requested
        if camera_control.recenter:
            self.center_camera_on_player(player_position)
            camera_control.recenter = False  # Reset the recenter flag

        # Update effect visibility based on camera control
        self.show_path = camera_control.toggle_path
        self.show_shadow = camera_control.toggle_shadow
        self.show_raycast = camera_control.toggle_raycast
        self.show_radius = camera_control.toggle_radius
        self.show_fov = camera_control.toggle_fov
        self.ascii_mode = camera_control.toggle_ascii

    def draw_visible_nodes(self, fog_of_war: Optional[Shadow] = None):
        if self.show_fov and fog_of_war:
            # Draw only the nodes within the FOV
            for node in fog_of_war.nodes:
                position = node.position.value
                if position in self.grid_map_visual.node_visuals:
                    self.draw_node(position, self.grid_map_visual.node_visuals[position])
        else:
            # Draw nodes within the visible range
            start_x = max(0, self.camera_pos[0])
            start_y = max(0, self.camera_pos[1])
            end_x = min(self.grid_map_visual.width, start_x + self.rect.width // self.cell_size)
            end_y = min(self.grid_map_visual.height, start_y + self.rect.height // self.cell_size)
            for x in range(start_x, end_x):
                for y in range(start_y, end_y):
                    position = (x, y)
                    if position in self.grid_map_visual.node_visuals:
                        self.draw_node(position, self.grid_map_visual.node_visuals[position])

    def draw_shape_effect(self, path: Optional[Path] = None, shadow: Optional[Shadow] = None,
                          raycast: Optional[RayCast] = None, radius: Optional[Radius] = None,
                          fog_of_war: Optional[Shadow] = None):
        # Draw effects (in the following order: shadow, radius, raycast, path)
        if self.show_shadow and shadow:
            self.draw_effect(self.image, shadow.nodes, (255, 255, 0))
        if self.show_radius and radius:
            self.draw_effect(self.image, radius.nodes, (0, 0, 255))
        if self.show_raycast and raycast:
            self.draw_effect(self.image, raycast.nodes, (255, 0, 0))
        if self.show_path and path:
            self.draw_effect(self.image, path.nodes, (0, 255, 0))

    def draw_shape_effect(self,path: Optional[Path] = None, shadow: Optional[Shadow] = None,
             raycast: Optional[RayCast] = None, radius: Optional[Radius] = None, fog_of_war: Optional[Shadow] = None):
        # Draw effects (in the following order: shadow, radius, raycast, path)
        if self.show_shadow and shadow:
            self.draw_effect(self.image, shadow.nodes, (255, 255, 0))
        if self.show_radius and radius:
            self.draw_effect(self.image, radius.nodes, (0, 0, 255))
        if self.show_raycast and raycast:
            self.draw_effect(self.image, raycast.nodes, (255, 0, 0))
        if self.show_path and path:
            self.draw_effect(self.image, path.nodes, (0, 255, 0))


    def draw(self, surface: pygame.Surface, path: Optional[Path] = None, shadow: Optional[Shadow] = None,
             raycast: Optional[RayCast] = None, radius: Optional[Radius] = None, fog_of_war: Optional[Shadow] = None):
        # Clear the widget surface
        self.image.fill((0, 0, 0))

        self.draw_visible_nodes(fog_of_war)

        self.draw_shape_effect(path, shadow, raycast, radius, fog_of_war)

        # Blit the widget surface onto the main surface
        surface.blit(self.image, self.rect)

    def draw_node(self, position: Tuple[int, int], node_visual: NodeVisual):
        screen_x, screen_y = self.grid_to_screen(*position)
        if self.ascii_mode:
            # Draw the entity with the highest draw order in ASCII mode
            sorted_entity_visuals = sorted(node_visual.entity_visuals, key=lambda ev: ev.draw_order, reverse=True)
            ascii_char = sorted_entity_visuals[0].ascii_char
            ascii_surface = self.font.render(ascii_char, True, (255, 255, 255))
            ascii_rect = ascii_surface.get_rect(center=(screen_x + self.cell_size // 2, screen_y + self.cell_size // 2))
            self.image.blit(ascii_surface, ascii_rect)
        else:
            # Draw all entities in sprite mode (in draw order)
            sorted_entity_visuals = sorted(node_visual.entity_visuals, key=lambda ev: ev.draw_order)
            for entity_visual in sorted_entity_visuals:
                sprite_surface = self.load_sprite(entity_visual.sprite_path)
                scaled_sprite_surface = pygame.transform.scale(sprite_surface, (self.cell_size, self.cell_size))
                self.image.blit(scaled_sprite_surface, (screen_x, screen_y))

    def draw_effect(self, surface: pygame.Surface, nodes: List[Node], color: Tuple[int, int, int]):
        for node in nodes:
            x, y = node.position.value
            if self.is_position_visible(x, y):
                screen_x, screen_y = self.grid_to_screen(x, y)
                pygame.draw.rect(surface, color, (screen_x, screen_y, self.cell_size, self.cell_size), 2)

    def is_position_visible(self, x: int, y: int) -> bool:
        return (self.camera_pos[0] <= x < self.camera_pos[0] + self.rect.width // self.cell_size and
                self.camera_pos[1] <= y < self.camera_pos[1] + self.rect.height // self.cell_size)

    def load_sprite(self, sprite_path: str) -> pygame.Surface:
        if sprite_path not in self.sprite_cache:
            sprite_surface = pygame.image.load(sprite_path).convert_alpha()
            self.sprite_cache[sprite_path] = sprite_surface
        return self.sprite_cache[sprite_path]

    def center_camera_on_player(self, player_position: Tuple[int, int]):
        self.camera_pos[0] = player_position[0] - self.rect.width // (2 * self.cell_size)
        self.camera_pos[1] = player_position[1] - self.rect.height // (2 * self.cell_size)
        self.camera_pos[0] = max(0, min(self.grid_map_visual.width - self.rect.width // self.cell_size, self.camera_pos[0]))
        self.camera_pos[1] = max(0, min(self.grid_map_visual.height - self.rect.height // self.cell_size, self.camera_pos[1]))


class Renderer:
    def __init__(self, screen: pygame.Surface, grid_map_visual: GridMapVisual, widget_size: Tuple[int, int]):
        self.screen = screen
        self.widget_size = widget_size
        self.grid_map_widget = GridMapWidget((0, 0), widget_size, grid_map_visual)
        self.widgets: Dict[str, Widget] = {
            "grid_map": self.grid_map_widget
        }
        self.camera_control = CameraControl()

    def update(self, player_position: Tuple[int, int] = (0, 0)):
        self.grid_map_widget.update(self.camera_control, player_position)

    def render(self, path: Optional[Path] = None, shadow: Optional[Shadow] = None,
               raycast: Optional[RayCast] = None, radius: Optional[Radius] = None,
               fog_of_war: Optional[Shadow] = None):
        # Clear the area occupied by each widget
        for widget in self.widgets.values():
            self.screen.fill((0, 0, 0), widget.rect)
        # Draw the grid map widget
        self.grid_map_widget.draw(self.screen, path, shadow, raycast, radius, fog_of_war)
        # Draw other widgets
        for widget in self.widgets.values():
            if widget != self.grid_map_widget:
                widget.draw(self.screen)
        pygame.display.flip()

    def handle_camera_control(self, camera_control: CameraControl):
        self.camera_control = camera_control

    def update_grid_map_visual(self, grid_map_visual: GridMapVisual):
        self.grid_map_widget.grid_map_visual = grid_map_visual