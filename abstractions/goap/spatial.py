from __future__ import annotations
from abstractions.goap.entity import Entity, Attribute, RegistryHolder
from typing import List, Tuple, TYPE_CHECKING, Optional, Any, ForwardRef, Dict
from pydantic import Field, BaseModel, validator, ConfigDict
import uuid

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

    def __repr__(self):
        attrs = {}
        for key, value in self.__dict__.items():
            if key == 'node' and value is not None:
                attrs[key] = value.non_verbose_repr()
            elif key != 'node':
                attrs[key] = value
        attrs_str = ', '.join(f'{k}={v}' for k, v in attrs.items())
        return f"{self.__class__.__name__}({attrs_str})"

class Path(BaseModel):
    nodes: List[Node] = Field(default_factory=list, description="The list of nodes in the path")

    @validator('nodes')
    def validate_path(cls, nodes):
        for i in range(len(nodes) - 1):
            if nodes[i + 1] not in nodes[i].neighbors():
                raise ValueError(f"Nodes {nodes[i]} and {nodes[i + 1]} are not adjacent")
            if nodes[i].blocks_movement:
                raise ValueError(f"Node {nodes[i]} is not walkable")
        return nodes

class Node(BaseModel, RegistryHolder):
    name: str = Field("", description="The name of the node")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="The unique identifier of the node")
    position: Position = Field(default_factory=Position, description="The position of the node")
    entities: List[GameEntity] = Field(default_factory=list, description="The game entities contained within the node")
    grid_map: Optional[GridMap] = Field(default=None, exclude=True, description="The grid map the node belongs to")

    class Config(ConfigDict):
        arbitrary_types_allowed = True

    def __init__(self, **data: Any):
        super().__init__(**data)
        self.register(self)

    def __hash__(self):
        return hash(self.id)

    def non_verbose_repr(self):
        return f"Node(id={self.id}, position={self.position.value})"

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

    def neighbors(self) -> List[Node]:
        if self.grid_map:
            return self.grid_map.get_neighbors(self.position.value)
        return []
    

import heapq

class GridMap:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.grid: List[List[Node]] = [[Node(position=Position(value=(x, y)), grid_map=self) for y in range(height)] for x in range(width)]

    def get_node(self, position: Tuple[int, int]) -> Node:
        x, y = position
        return self.grid[x][y]

    def set_node(self, position: Tuple[int, int], node: Node):
        x, y = position
        self.grid[x][y] = node

    def get_neighbors(self, position: Tuple[int, int], allow_diagonal: bool = True) -> List[Node]:
        x, y = position
        neighbors = []
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            new_x, new_y = x + dx, y + dy
            if 0 <= new_x < self.width and 0 <= new_y < self.height:
                neighbors.append(self.grid[new_x][new_y])
        if allow_diagonal:
            for dx, dy in [(1, 1), (-1, 1), (1, -1), (-1, -1)]:
                new_x, new_y = x + dx, y + dy
                if 0 <= new_x < self.width and 0 <= new_y < self.height:
                    neighbors.append(self.grid[new_x][new_y])
        return neighbors

    def dijkstra(self, start: Node, max_distance: int, allow_diagonal: bool = True) -> Tuple[Dict[Tuple[int, int], int], Dict[Tuple[int, int], Path]]:
        distances: Dict[Tuple[int, int], int] = {start.position.value: 0}
        paths: Dict[Tuple[int, int], Path] = {start.position.value: Path(nodes=[start])}
        unvisited = [(0, start.position.value)]  # The unvisited set is a list of tuples (distance, position)
        while unvisited:
            current_distance, current_position = heapq.heappop(unvisited)
            if current_distance > max_distance:
                break
            current_node = self.get_node(current_position)
            for neighbor in self.get_neighbors(current_position, allow_diagonal):
                if not neighbor.blocks_movement:
                    new_distance = current_distance + 1  # Assuming uniform cost between nodes
                    if neighbor.position.value not in distances or new_distance < distances[neighbor.position.value]:
                        distances[neighbor.position.value] = new_distance
                        paths[neighbor.position.value] = Path(nodes=paths[current_position].nodes + [neighbor])
                        heapq.heappush(unvisited, (new_distance, neighbor.position.value))
        return distances, paths

    def a_star(self, start: Node, goal: Node, allow_diagonal: bool = True) -> Optional[Path]:
        if start == goal:
            return Path(nodes=[start])
        if goal.blocks_movement:
            return None

        def heuristic(position: Tuple[int, int]) -> int:
            return abs(position[0] - goal.position.x) + abs(position[1] - goal.position.y)

        open_set = [(0, start.position.value)]  # The open set is a list of tuples (f_score, position)
        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
        g_score: Dict[Tuple[int, int], int] = {start.position.value: 0}
        f_score: Dict[Tuple[int, int], int] = {start.position.value: heuristic(start.position.value)}

        while open_set:
            current_position = heapq.heappop(open_set)[1]
            current_node = self.get_node(current_position)
            if current_node == goal:
                path_nodes = []
                while current_position in came_from:
                    path_nodes.append(self.get_node(current_position))
                    current_position = came_from[current_position]
                path_nodes.append(start)
                path_nodes.reverse()
                return Path(nodes=path_nodes)

            for neighbor in self.get_neighbors(current_position, allow_diagonal):
                if not neighbor.blocks_movement:
                    tentative_g_score = g_score[current_position] + 1  # Assuming uniform cost
                    if neighbor.position.value not in g_score or tentative_g_score < g_score[neighbor.position.value]:
                        came_from[neighbor.position.value] = current_position
                        g_score[neighbor.position.value] = tentative_g_score
                        f_score[neighbor.position.value] = tentative_g_score + heuristic(neighbor.position.value)
                        if (f_score[neighbor.position.value], neighbor.position.value) not in open_set:
                            heapq.heappush(open_set, (f_score[neighbor.position.value], neighbor.position.value))

        return None  # No path found
    def get_movement_array(self) -> List[List[bool]]:
        return [[not node.blocks_movement for node in row] for row in self.grid]

    def get_vision_array(self) -> List[List[bool]]:
        return [[not node.blocks_light for node in row] for row in self.grid]

    def print_grid(self, path: Optional[Path] = None):
        for y in range(self.height):
            row = ""
            for x in range(self.width):
                node = self.grid[x][y]
                if node.blocks_movement:
                    row += "# "
                elif path and node == path.nodes[0]:
                    row += "\033[92mS\033[0m "  # Green color for start
                elif path and node == path.nodes[-1]:
                    row += "\033[91mG\033[0m "  # Red color for goal
                elif path and node in path.nodes:
                    row += "\033[93m*\033[0m "  # Orange color for path
                elif node.entities:
                    row += "E "
                else:
                    row += ". "
            print(row)
    def get_nodes_in_radius(self, position: Tuple[int, int], radius: int) -> List[Node]:
        x, y = position
        nodes = []
        for i in range(x - radius, x + radius + 1):
            for j in range(y - radius, y + radius + 1):
                if 0 <= i < self.width and 0 <= j < self.height:
                    nodes.append(self.grid[i][j])
        return nodes