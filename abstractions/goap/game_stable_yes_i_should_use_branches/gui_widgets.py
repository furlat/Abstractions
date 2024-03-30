import pygame
import pygame_gui
from typing import List
from pydantic import BaseModel
from abstractions.goap.interactions import GameEntity
from abstractions.goap.game.payloadgen import SpriteMapping

class InventoryItemVisual(BaseModel):
    sprite_path: str
    name: str

class InventoryVisualState(BaseModel):
    items: List[InventoryItemVisual]

class InventoryWidget(pygame_gui.elements.UIWindow):
    def __init__(self, pos, manager, sprite_mappings: List[SpriteMapping]):
        super().__init__(pygame.Rect(pos, (200, 150)), manager, window_display_title="Inventory", object_id="#inventory_window")
        
        self.inventory_panel = pygame_gui.elements.UIPanel(pygame.Rect(0, 0, 200, 150), starting_layer_height=1, manager=manager, container=self, object_id="#inventory_panel")
        
        self.sprite_mappings = sprite_mappings
        self.visual_state = InventoryVisualState(items=[])
        
    def update(self, time_delta, inventory: List[GameEntity]):
        super().update(time_delta)
        
        # Update the visual state based on the current inventory
        self.update_visual_state(inventory)
        
        # Clear existing item images and names
        self.inventory_panel.clear()
        
        # Add item images and names based on the visual state
        for i, item_visual in enumerate(self.visual_state.items):
            item_image = pygame_gui.elements.UIImage(pygame.Rect((10, 10 + i * 30), (20, 20)), item_visual.sprite_path, manager=self.ui_manager, container=self.inventory_panel)
            item_name = pygame_gui.elements.UILabel(pygame.Rect((40, 10 + i * 30), (150, 20)), item_visual.name, manager=self.ui_manager, container=self.inventory_panel)
    
    def update_visual_state(self, inventory: List[GameEntity]):
        item_visuals = []
        for item in inventory:
            sprite_path = self.get_sprite_path(item)
            if sprite_path:
                item_visual = InventoryItemVisual(sprite_path=sprite_path, name=item.name)
                item_visuals.append(item_visual)
        self.visual_state = InventoryVisualState(items=item_visuals)
    
    def get_sprite_path(self, item: GameEntity) -> str:
        for mapping in self.sprite_mappings:
            if isinstance(item, mapping.entity_type):
                return mapping.sprite_path
        return ""