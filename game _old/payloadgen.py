from functools import lru_cache
from typing import Dict, Type, Callable, Any, List, Tuple, Optional
from pydantic import BaseModel
import re
from abstractions.goap.spatial import GameEntity, Node, Shadow

class SpriteMapping(BaseModel):
    entity_type: Type[GameEntity]
    name_pattern: Optional[str] = None
    sprite_path: str
    ascii_char: str
    draw_order: int
    attribute_conditions: Optional[Dict[str, Any]] = None



class PayloadGenerator:
    def __init__(self, sprite_mappings: List[SpriteMapping], grid_size: Tuple[int, int]):
        self.sprite_mappings = sprite_mappings
        self.grid_size = grid_size
        self.cache_size = grid_size[0] * grid_size[1]
        self.payload_cache: Dict[int, Dict[str, Any]] = {}

    @lru_cache(maxsize=None)
    def get_sprite_mapping(self, entity: GameEntity) -> SpriteMapping:
        for mapping in self.sprite_mappings:
            if isinstance(entity, mapping.entity_type):
                if mapping.name_pattern is None or re.match(mapping.name_pattern, entity.name):
                    if mapping.attribute_conditions is None:
                        return mapping
                    else:
                        if all(hasattr(entity, attr_name) and getattr(entity, attr_name).value == value for attr_name, value in mapping.attribute_conditions.items()):
                            return mapping
        # If no specific mapping is found, return the first matching mapping without attribute conditions
        for mapping in self.sprite_mappings:
            if isinstance(entity, mapping.entity_type):
                if mapping.name_pattern is None or re.match(mapping.name_pattern, entity.name):
                    return mapping
        raise ValueError(f"No sprite mapping found for entity: {entity}")
    
    def generate_payload_for_node(self, node: Node) -> List[Dict[str, Any]]:
        entity_visuals = []
        if node.entities:
            sorted_entities = sorted(node.entities, key=lambda e: self.get_sprite_mapping(e).draw_order)
            for entity in sorted_entities:
                sprite_mapping = self.get_sprite_mapping(entity)
                entity_visual = {
                    "sprite_path": sprite_mapping.sprite_path,
                    "ascii_char": sprite_mapping.ascii_char,
                    "draw_order": sprite_mapping.draw_order
                }
                entity_visuals.append(entity_visual)
        return entity_visuals

    def generate_payload(self, nodes: List[Node], camera_pos: Tuple[int, int], fov: Optional[Shadow] = None) -> Dict[Tuple[int, int], List[Dict[str, Any]]]:
        payload = {}
        start_x, start_y = camera_pos
        end_x, end_y = start_x + self.grid_size[0], start_y + self.grid_size[1]

        for node in nodes:
            position = node.position.value
            if fov and position not in [node.position.value for node in fov.nodes]:
                continue  # Skip nodes outside the FOV
            if start_x <= position[0] < end_x and start_y <= position[1] < end_y:
                if position in self.payload_cache and self.is_node_unchanged(node):
                    payload[position] = self.payload_cache[position]
                else:
                    entity_visuals = []
                    if node.entities:
                        sorted_entities = sorted(node.entities, key=lambda e: self.get_sprite_mapping(e).draw_order)
                        for entity in sorted_entities:
                            sprite_mapping = self.get_sprite_mapping(entity)
                            entity_visual = {
                                "sprite_path": sprite_mapping.sprite_path,
                                "ascii_char": sprite_mapping.ascii_char,
                                "draw_order": sprite_mapping.draw_order
                            }
                            entity_visuals.append(entity_visual)
                    payload[position] = entity_visuals
                    self.payload_cache[position] = entity_visuals
        return payload
    @lru_cache(maxsize=None)
    def is_node_unchanged(self, node: Node) -> bool:
        position = node.position.value
        if position not in self.payload_cache:
            return False
        cached_entity_visuals = self.payload_cache[position]
        current_entity_visuals = []
        if node.entities:
            sorted_entities = sorted(node.entities, key=lambda e: self.get_sprite_mapping(e).draw_order)
            for entity in sorted_entities:
                sprite_mapping = self.get_sprite_mapping(entity)
                entity_visual = {
                    "sprite_path": sprite_mapping.sprite_path,
                    "ascii_char": sprite_mapping.ascii_char,
                    "draw_order": sprite_mapping.draw_order,
                    "attribute_conditions": sprite_mapping.attribute_conditions
                }
                current_entity_visuals.append(entity_visual)
        return cached_entity_visuals == current_entity_visuals