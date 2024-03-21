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