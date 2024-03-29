from functools import lru_cache
from typing import Dict, Type, Callable, Any, List, Tuple, Optional
from pydantic import BaseModel
import re
from abstractions.goap.spatial import GameEntity, Node
class SpriteMapping(BaseModel):
    entity_type: Type[GameEntity]
    name_pattern: Optional[str] = None
    sprite_path: str
    ascii_char: str
    draw_order: int



class PayloadGenerator:
    def __init__(self, sprite_mappings: List[SpriteMapping], grid_size: Tuple[int, int]):
        self.sprite_mappings = sprite_mappings
        self.grid_size = grid_size
        self.cache_size = grid_size[0] * grid_size[1]

    @lru_cache(maxsize=None)
    def get_sprite_mapping(self, entity: GameEntity) -> SpriteMapping:
        for mapping in self.sprite_mappings:
            if isinstance(entity, mapping.entity_type):
                if mapping.name_pattern is None or re.match(mapping.name_pattern, entity.name):
                    return mapping
        raise ValueError(f"No sprite mapping found for entity: {entity}")

    def generate_payload(self, nodes: List[Node]) -> Dict[Tuple[int, int], List[Dict[str, Any]]]:
        payload = {}
        for node in nodes:
            position = node.position.value
            entity_visuals = []
            if node.entities:

                sorted_entities = sorted(node.entities, key=lambda e: self.get_sprite_mapping(e).draw_order)
                for entity in sorted_entities:
                    sprite_mapping = self.get_sprite_mapping(entity)
                    # print(f"Sprite mapping for entity {entity}: {sprite_mapping}")
                    entity_visual = {
                        "sprite_path": sprite_mapping.sprite_path,
                        "ascii_char": sprite_mapping.ascii_char,
                        "draw_order": sprite_mapping.draw_order
                    }
                    entity_visuals.append(entity_visual)
            payload[position] = entity_visuals
        return payload