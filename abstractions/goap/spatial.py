from __future__ import annotations
from abstractions.goap.entity import Entity, Attribute
from typing import List, Tuple, TYPE_CHECKING
from pydantic import Field

if TYPE_CHECKING:
    from abstractions.goap.spatial import Node

class Position(Attribute):
    value: Tuple[int, int] = Field(default=(0, 0), description="The (x, y) coordinates of the entity")

    @property
    def x(self):
        return self.value[0]

    @property
    def y(self):
        return self.value[1]

class BlocksMovement(Attribute):
    value: bool = Field(default=False, description="Indicates if the entity blocks movement")

class BlocksLight(Attribute):
    value: bool = Field(default=False, description="Indicates if the entity blocks light")

class GameEntity(Entity):
    blocks_movement: BlocksMovement = Field(default_factory=BlocksMovement, description="Attribute indicating if the entity blocks movement")
    blocks_light: BlocksLight = Field(default_factory=BlocksLight, description="Attribute indicating if the entity blocks light")
    node: Node = Field(default=None, description="The node the entity is currently in")

    @property
    def position(self) -> Position:
        if self.node:
            return self.node.position
        return Position()

    def set_node(self, node: Node):
        self.node = node
        node.add_entity(self)

    def remove_from_node(self):
        if self.node:
            self.node.remove_entity(self)
            self.node = None

class Node(Entity):
    position: Position = Field(default_factory=Position, description="The position of the node")
    entities: List[GameEntity] = Field(default_factory=list, description="The game entities contained within the node")

    def add_entity(self, entity: GameEntity):
        self.entities.append(entity)
        entity.node = self

    def remove_entity(self, entity: GameEntity):
        self.entities.remove(entity)
        entity.node = None

    @property
    def blocks_movement(self) -> bool:
        return any(entity.blocks_movement.value for entity in self.entities)

    @property
    def blocks_light(self) -> bool:
        return any(entity.blocks_light.value for entity in self.entities)
    

class GridMap:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.grid: List[List[Node]] = [[Node(position=Position(value=(x, y))) for y in range(height)] for x in range(width)]

    def get_node(self, position: Tuple[int, int]) -> Node:
        x, y = position
        return self.grid[x][y]

    def set_node(self, position: Tuple[int, int], node: Node):
        x, y = position
        self.grid[x][y] = node

    def get_neighbors(self, position: Tuple[int, int]) -> List[Node]:
        x, y = position
        neighbors = []
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            new_x, new_y = x + dx, y + dy
            if 0 <= new_x < self.width and 0 <= new_y < self.height:
                neighbors.append(self.grid[new_x][new_y])
        return neighbors

    def get_movement_array(self) -> List[List[bool]]:
        return [[not node.blocks_movement for node in row] for row in self.grid]

    def get_vision_array(self) -> List[List[bool]]:
        return [[not node.blocks_light for node in row] for row in self.grid]

    def print_grid(self):
        for row in self.grid:
            row_str = ""
            for node in row:
                if node.blocks_movement:
                    row_str += "# "
                elif node.entities:
                    row_str += "E "
                else:
                    row_str += ". "
            print(row_str)

    def get_nodes_in_radius(self, position: Tuple[int, int], radius: int) -> List[Node]:
        x, y = position
        nodes = []
        for i in range(x - radius, x + radius + 1):
            for j in range(y - radius, y + radius + 1):
                if 0 <= i < self.width and 0 <= j < self.height:
                    nodes.append(self.grid[i][j])
        return nodes