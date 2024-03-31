import pygame
import pygame_gui
from typing import List, Optional
from pydantic import BaseModel
from abstractions.goap.interactions import GameEntity
from abstractions.goap.game.payloadgen import SpriteMapping
import typing

if typing.TYPE_CHECKING:
    from abstractions.goap.game.input_handler import InputHandler

class InventoryItemVisual(BaseModel):
    sprite_path: str
    name: str
    entity_id: str

class InventoryVisualState(BaseModel):
    items: List[InventoryItemVisual]
    
class InventoryWidget(pygame_gui.elements.UIWindow):
    def __init__(self, pos, manager, sprite_mappings: List[SpriteMapping], input_handler:Optional["InputHandler"] = None):
        super().__init__(pygame.Rect(pos, (200, 150)), manager, window_display_title="Inventory", object_id="#inventory_window")
       
        self.inventory_container = pygame_gui.core.UIContainer(pygame.Rect(0, 0, 200, 150), manager=manager, container=self, object_id="#inventory_container")
       
        self.sprite_mappings = sprite_mappings
        self.visual_state = InventoryVisualState(items=[])
        self.input_handler = input_handler
        self.inventory_changed = False

    def setup_input_handler(self, input_handler: "InputHandler"):
        self.input_handler = input_handler
        
    def update(self, time_delta):
        super().update(time_delta)
   
    def update_inventory(self, inventory: List[GameEntity]):
        if self.visual_state.items != [InventoryItemVisual(sprite_path=self.get_sprite_path(item), name=item.name, entity_id=item.id) for item in inventory]:
            self.inventory_changed = True
            self.update_visual_state(inventory)

            self.inventory_container.kill()
            self.inventory_container = pygame_gui.core.UIContainer(pygame.Rect(0, 0, 200, 150), manager=self.ui_manager, container=self, object_id="#inventory_container")

            if self.visual_state.items:
                for i, item_visual in enumerate(self.visual_state.items):
                    sprite_surface = pygame.image.load(item_visual.sprite_path).convert_alpha()
                    item_image = pygame_gui.elements.UIImage(pygame.Rect((10, 10 + i * 30), (20, 20)), sprite_surface, manager=self.ui_manager, container=self.inventory_container)
                    item_name = pygame_gui.elements.UILabel(pygame.Rect((40, 10 + i * 30), (150, 20)), item_visual.name, manager=self.ui_manager, container=self.inventory_container)

    def process_event(self, event: pygame.event.Event) -> bool:
        handled = super().process_event(event)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # Left mouse button
            mouse_pos = event.pos
            for i, item_visual in enumerate(self.visual_state.items):
                # item_rect = pygame.Rect((self.rect.x + 10, self.rect.y + 10 + i * 30), (190, 20))
                item_rect = pygame.Rect((10, 50 + i * 30), (190, 20))
                if item_rect.collidepoint(mouse_pos):
                    print(f"Clicked on item {item_visual.name}")
                    self.input_handler.active_entities.targeted_inventory_entity_id = item_visual.entity_id
                    self.input_handler.active_entities.targeted_entity_id = None
                    self.input_handler.active_entities.targeted_node_id = None
                    self.input_handler.update_available_actions()
                    handled = True
                    break
        return handled
    
    def update_visual_state(self, inventory: List[GameEntity]):
        item_visuals = []
        for item in inventory:
            sprite_path = self.get_sprite_path(item)
            if sprite_path:
                item_visual = InventoryItemVisual(sprite_path=sprite_path, name=item.name, entity_id=item.id)
                item_visuals.append(item_visual)
        self.visual_state = InventoryVisualState(items=item_visuals)
   
    def get_sprite_path(self, item: GameEntity) -> str:
        for mapping in self.sprite_mappings:
            if isinstance(item, mapping.entity_type):
                return mapping.sprite_path
        return ""