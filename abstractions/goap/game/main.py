import pygame
from abstractions.goap.gridmap import GridMap
from abstractions.goap.nodes import GameEntity, Node, Attribute, BlocksMovement, BlocksLight
import os
from abstractions.goap.actions import Goal, Prerequisites
from abstractions.goap.entity import Statement
from abstractions.goap.interactions import Character, Door, Key, Treasure, Floor, Wall, InanimateEntity, IsPickupable, TestItem, Open, Close, Unlock, Lock, Pickup, Drop, Move
from abstractions.goap.game.payloadgen import PayloadGenerator, SpriteMapping
from abstractions.goap.game.renderer import Renderer, GridMapVisual, NodeVisual, EntityVisual, CameraControl
from abstractions.goap.game.input_handler import InputHandler
from pydantic import ValidationError
from abstractions.goap.game.manager import GameManager
from typing import Optional

BASE_PATH = r"C:\Users\Tommaso\Documents\Dev\Abstractions\abstractions\goap"
# BASE_PATH = "/Users/tommasofurlanello/Documents/Dev/Abstractions/abstractions/goap"

def generate_dungeon(grid_map: GridMap, room_width: int, room_height: int):
    room_x = (grid_map.width - room_width) // 2
    room_y = (grid_map.height - room_height) // 2
    for x in range(room_x, room_x + room_width):
        for y in range(room_y, room_y + room_height):
            if x == room_x or x == room_x + room_width - 1 or y == room_y or y == room_y + room_height - 1:
                if (x, y) != (room_x + room_width // 2, room_y):
                    wall = Wall(name=f"Wall_{x}_{y}", blocks_movement=BlocksMovement(value=True), blocks_light=BlocksLight(value=True))
                    grid_map.get_node((x, y)).add_entity(wall)
            else:
                floor = Floor(name=f"Floor_{x}_{y}")
                grid_map.get_node((x, y)).add_entity(floor)
    door_x, door_y = room_x + room_width // 2, room_y
    character_x, character_y = room_x + room_width // 2, room_y - 1
    key_x, key_y = room_x - 1, room_y + room_height // 2    
    treasure_x, treasure_y = room_x + room_width // 2, room_y + room_height - 2
    door = Door(name="Door", is_locked=Attribute(name="is_locked", value=True), required_key=Attribute(name="required_key", value="Golden Key"))
    character = Character(name="Player")
    key = Key(name="Golden Key", key_name=Attribute(name="key_name", value="Golden Key"), is_pickupable=IsPickupable(value=True))
    treasure = Treasure(name="Treasure", monetary_value=Attribute(name="monetary_value", value=1000), is_pickupable=IsPickupable(value=True))
    grid_map.get_node((door_x, door_y)).add_entity(door)
    grid_map.get_node((character_x, character_y)).add_entity(character)
    grid_map.get_node((key_x, key_y)).add_entity(key)
    grid_map.get_node((treasure_x, treasure_y)).add_entity(treasure)
    for x in range(grid_map.width):
        for y in range(grid_map.height):
            if not any(isinstance(entity, Floor) for entity in grid_map.get_node((x, y)).entities):
                floor = Floor(name=f"Floor_{x}_{y}")
                grid_map.get_node((x, y)).add_entity(floor)
    return character, door, key, treasure


def source_target_position_comparison(source: tuple[int,int], target: tuple[int,int]) -> bool:
    """Check if the source entity's position is the same as the target entity's position."""
    if source and target:
        return source == target
    return False

def treasure_in_neighborhood(source: GameEntity, target: Optional[GameEntity] = None) -> bool:
    """Check if the treasure is in the character's neighborhood."""
    if source.node and target and target.node:
        return source.node in target.node.neighbors()
    return False

def key_in_inventory(source: GameEntity, target: Optional[GameEntity] = None) -> bool:
    """Check if the key is in the character's inventory."""
    if target:
        return target in source.inventory
    return False

def is_treasure(source: GameEntity, target: Optional[GameEntity] = None) -> bool:
    """Check if the target entity is a Treasure."""

    
    return isinstance(target, Treasure)

def is_golden_key(source: GameEntity, target: Optional[GameEntity] = None) -> bool:
    """Check if the entity is a Golden Key."""
    return isinstance(target, Key) and target.key_name.value == "Golden Key"

def is_door(entity: GameEntity, target: Optional[GameEntity] = None) -> bool:
    """Check if the entity is a Door."""
    return isinstance(entity, Door)

def main():
    # Initialize Pygame
    pygame.init()
    screen_width, screen_height = 1400, 800
    screen = pygame.display.set_mode((screen_width, screen_height))
    
    pygame.display.set_caption("Dungeon Experiment")
    
    # Create the grid map and generate the dungeon
    grid_map = GridMap(width=10, height=10)
    grid_map.register_actions([Move, Pickup, Drop, Open, Close, Unlock, Lock])
    room_width, room_height = 6, 6
    character, door, key, treasure = generate_dungeon(grid_map, room_width, room_height)
    
    # Generate the entity type map
    grid_map.generate_entity_type_map()
    
    # Define the sprite mappings
    sprite_mappings = [
        SpriteMapping(entity_type=Character, sprite_path=os.path.join(BASE_PATH, "sprites", "character_agent.png"), ascii_char="@", draw_order=3),
        SpriteMapping(entity_type=Door, sprite_path=os.path.join(BASE_PATH, "sprites", "closed_locked_door.png"), ascii_char="D", draw_order=2, attribute_conditions={"open": False, "is_locked": True}),
        SpriteMapping(entity_type=Door, sprite_path=os.path.join(BASE_PATH, "sprites", "closed_unlocked_door.png"), ascii_char="D", draw_order=2, attribute_conditions={"open": False, "is_locked": False}),
        SpriteMapping(entity_type=Door, sprite_path=os.path.join(BASE_PATH, "sprites", "open_locked_door.png"), ascii_char="D", draw_order=2, attribute_conditions={"open": True, "is_locked": True}),
        SpriteMapping(entity_type=Door, sprite_path=os.path.join(BASE_PATH, "sprites", "open_unlocked_door.png"), ascii_char="D", draw_order=2, attribute_conditions={"open": True, "is_locked": False}),
        SpriteMapping(entity_type=Key, sprite_path=os.path.join(BASE_PATH, "sprites", "lock.png"), ascii_char="K", draw_order=1),
        SpriteMapping(entity_type=Treasure, sprite_path=os.path.join(BASE_PATH, "sprites", "filled_storage.png"), ascii_char="T", draw_order=1),
        SpriteMapping(entity_type=Floor, sprite_path=os.path.join(BASE_PATH, "sprites", "floor.png"), ascii_char=".", draw_order=0),
        SpriteMapping(entity_type=TestItem, sprite_path=os.path.join(BASE_PATH, "sprites", "filled_storage.png"), ascii_char="$", draw_order=1),
        SpriteMapping(entity_type=GameEntity, name_pattern=r"^Wall", sprite_path=os.path.join(BASE_PATH, "sprites", "wall.png"), ascii_char="#", draw_order=1),
    ]
    # add the goals

        # Goal 1: Check if the character's position is the same as the treasure's position
    reach_treasure_goal = Goal(
        name="Reach the treasure",
        source_entity_id=character.id,
        target_entity_id=treasure.id,
        prerequisites=Prerequisites(
            source_statements=[Statement(conditions={"can_act": True})],
            target_statements=[Statement(callables=[is_treasure])],
            source_target_statements=[
                Statement(comparisons={
                    "source_position": ("position", "position", source_target_position_comparison)
                })
            ]
        )
    )

    # Goal 2: Check if the treasure is in the character's neighborhood
    treasure_in_neighborhood_goal = Goal(
        name="Treasure in neighborhood",
        source_entity_id=character.id,
        target_entity_id=treasure.id,
        prerequisites=Prerequisites(
            source_statements=[Statement(conditions={"can_act": True})],
            target_statements=[Statement(callables=[is_treasure])],
            source_target_statements=[
                Statement(callables=[treasure_in_neighborhood])
            ]
        )
    )

    # Goal 3: Check if the key is in the character's inventory
    key_in_inventory_goal = Goal(
        name="Key in inventory",
        source_entity_id=character.id,
        target_entity_id=key.id,
        prerequisites=Prerequisites(
            source_statements=[Statement(conditions={"can_act": True})],
            target_statements=[Statement(callables=[is_golden_key])],
            source_target_statements=[
                Statement(callables=[key_in_inventory])
            ]
        )
    )

    # Goal 4: Check if the door is unlocked
    door_unlocked_goal = Goal(
        name="Door unlocked",
        source_entity_id=door.id,
        prerequisites=Prerequisites(
            source_statements=[
                Statement(callables=[is_door]),
                Statement(conditions={"is_locked": False})
            ],
            target_statements=[],
            source_target_statements=[]
        )
    )
    goals = [reach_treasure_goal, treasure_in_neighborhood_goal, key_in_inventory_goal, door_unlocked_goal]

    # Create the game manager
    game_manager = GameManager(screen, grid_map, sprite_mappings, widget_size=(400, 300), controlled_entity_id=character.id, goals=goals)
    
    # Run the game
    game_manager.run()
    
    # Quit Pygame
    pygame.quit()

if __name__ == "__main__":
    main()