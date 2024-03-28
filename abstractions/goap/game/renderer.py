import pygame
from pygame.sprite import Group, RenderUpdates
from typing import Dict, List, Type, Tuple, Optional
from pydantic import BaseModel
from abstractions.goap.spatial import Node, Path, Shadow, RayCast, Radius

class EntityVisual(BaseModel):
    sprite_path: str
    ascii_char: str
    
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

    def update(self):
        pass

    def draw(self, surface: pygame.Surface):
        surface.blit(self.image, self.rect)

class InventoryWidget(Widget):
    def __init__(self, pos: Tuple[int, int], size: Tuple[int, int]):
        super().__init__(pos, size)
        self.image.fill((128, 128, 128))  # Placeholder color

    def update(self, inventory: List[str]):
        # Update the inventory widget based on the current inventory state
        pass

class TargetWidget(Widget):
    def __init__(self, pos: Tuple[int, int], size: Tuple[int, int]):
        super().__init__(pos, size)
        self.image.fill((192, 192, 192))  # Placeholder color

    def update(self, target: str):
        # Update the target widget based on the current target
        pass

class Renderer:
    def __init__(self, screen: pygame.Surface, grid_map_visual: GridMapVisual):
        self.screen = screen
        self.grid_map_visual = grid_map_visual
        self.sprite_cache: Dict[str, pygame.Surface] = {}
        self.sprite_groups: Dict[str, Group] = {}
        self.widgets: Dict[str, Widget] = {}
        self.dirty_rects = []
        self.cell_size = 32
        self.show_path = False
        self.show_shadow = False
        self.show_raycast = False
        self.show_radius = False
        self.show_fog_of_war = False
    
    def draw_effect(self, effect_type: str, nodes: List[Node], color: Tuple[int, int, int]):
        for node in nodes:
            x, y = node.position.value
            screen_x = x * self.cell_size
            screen_y = y * self.cell_size
            pygame.draw.rect(self.screen, color, (screen_x, screen_y, self.cell_size, self.cell_size), 2)

    def create_sprite_group(self, group_name: str):
        self.sprite_groups[group_name] = RenderUpdates()

    def add_sprite_to_group(self, group_name: str, sprite: pygame.sprite.Sprite):
        self.sprite_groups[group_name].add(sprite)

    def load_sprite(self, sprite_path: str, cell_size: int) -> pygame.Surface:
        if sprite_path not in self.sprite_cache:
            sprite_surface = pygame.image.load(sprite_path).convert_alpha()
            scaled_surface = pygame.transform.scale(sprite_surface, (cell_size, cell_size))
            self.sprite_cache[sprite_path] = scaled_surface
        return self.sprite_cache[sprite_path]
    def create_widget(self, widget_type: Type[Widget], pos: Tuple[int, int], size: Tuple[int, int], name: str):
        widget = widget_type(pos, size)
        self.widgets[name] = widget

    def update_widget(self, name: str, *args, **kwargs):
        if name in self.widgets:
            self.widgets[name].update(*args, **kwargs)

    def render_grid_map(self, fog_of_war: Optional[Shadow] = None):
        for pos, node_visual in self.grid_map_visual.node_visuals.items():
            if not self.show_fog_of_war or (fog_of_war and pos in [node.position.value for node in fog_of_war.nodes]):
                for entity_visual in node_visual.entity_visuals:
                    sprite_surface = self.load_sprite(entity_visual.sprite_path, self.cell_size)
                    sprite_rect = sprite_surface.get_rect(topleft=(pos[0] * self.cell_size, pos[1] * self.cell_size))
                    self.screen.blit(sprite_surface, sprite_rect)
                    
    def render_sprites(self):
        for group_name, sprite_group in self.sprite_groups.items():
            dirty_rects = sprite_group.draw(self.screen)
            self.dirty_rects.extend(dirty_rects)

    def render_widgets(self):
        for widget in self.widgets.values():
            widget.draw(self.screen)
    
    def render_effects(self, path: Optional[Path] = None, shadow: Optional[Shadow] = None,
                    raycast: Optional[RayCast] = None, radius: Optional[Radius] = None):
        if self.show_path and path:
            self.draw_effect("path", path.nodes, (0, 255, 0))
        if self.show_shadow and shadow:
            self.draw_effect("shadow", shadow.nodes, (255, 255, 0))
        if self.show_raycast and raycast:
            self.draw_effect("raycast", raycast.nodes, (255, 0, 0))
        if self.show_radius and radius:
            self.draw_effect("radius", radius.nodes, (0, 0, 255))

    def render(self, path: Optional[Path] = None, shadow: Optional[Shadow] = None,
           raycast: Optional[RayCast] = None, radius: Optional[Radius] = None,
           fog_of_war: Optional[Shadow] = None):
        self.dirty_rects.clear()
        self.screen.fill((0, 0, 0))  # Clear the screen
        self.render_grid_map(fog_of_war)
        self.render_sprites()
        self.render_widgets()
        self.render_effects(path, shadow, raycast, radius)
        pygame.display.update(self.dirty_rects)