from __future__ import annotations
from abstractions.goap.entity import Entity, Attribute, RegistryHolder
from typing import List, Tuple, TYPE_CHECKING, Optional, Any, ForwardRef, Dict, Union
from pydantic import Field, BaseModel, validator, ConfigDict, ValidationInfo, field_validator
import uuid
import math

if TYPE_CHECKING:
    # from abstractions.goap.spatial import Node
    from abstractions.goap.actions import Action

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
    
class Radius(BaseModel):
    source: Node = Field(description="The source node of the radius")
    max_radius: int = Field(description="The maximum radius of the area")
    nodes: List[Node] = Field(default_factory=list, description="The list of nodes within the radius")

    @validator('nodes')
    def validate_radius(cls, nodes, values):
        source = values['source']
        max_radius = values['max_radius']
        grid_map = source.grid_map
        for node in nodes:
            if grid_map._get_distance(source.position.value, node.position.value) > max_radius:
                raise ValueError(f"Node {node} is outside the specified radius")
        return nodes

class Shadow(BaseModel):
    source: Node = Field(description="The source node of the shadow")
    max_radius: int = Field(description="The maximum radius of the shadow")
    nodes: List[Node] = Field(default_factory=list, description="The list of nodes within the shadow")

    @validator('nodes')
    def validate_shadow(cls, nodes, values):
        source = values['source']
        max_radius = values['max_radius']
        grid_map = source.grid_map
        for node in nodes:
            if grid_map._get_distance(source.position.value, node.position.value) > max_radius:
                raise ValueError(f"Node {node} is outside the specified shadow radius")
        return nodes

class RayCast(BaseModel):
    source: Node = Field(description="The source node of the raycast")
    target: Node = Field(description="The target node of the raycast")
    has_path: bool = Field(description="Indicates whether there is a clear path from source to target")
    nodes: List[Node] = Field(default_factory=list, description="The list of nodes along the raycast path (excluding source and target)")

    @validator('nodes')
    def validate_raycast(cls, nodes, values):
        source = values['source']
        target = values['target']
        has_path = values['has_path']
        if not has_path and nodes:
            raise ValueError("The raycast path should be empty if there is no clear path")
        if has_path:
            if nodes[0] == source or nodes[-1] == target:
                raise ValueError("The raycast path should not include the source or target nodes")
            for i in range(len(nodes) - 1):
                if nodes[i + 1] not in nodes[i].neighbors():
                    raise ValueError(f"Nodes {nodes[i]} and {nodes[i + 1]} are not adjacent")
            for node in nodes:
                if node.blocks_light:
                    raise ValueError(f"Node {node} blocks vision along the raycast path")
        return nodes
    

class ActionInstance(BaseModel):
    source_id: str
    target_id: str
    action: Action

class ActionsPayload(BaseModel):
    actions: List[ActionInstance]

class ActionResult(BaseModel):
    action_instance: ActionInstance
    success: bool
    error: str = None

class ActionsResults(BaseModel):
    results: List[ActionResult]


class GameEntity(Entity):
    blocks_movement: BlocksMovement = Field(default_factory=BlocksMovement, description="Attribute indicating if the entity blocks movement")
    blocks_light: BlocksLight = Field(default_factory=BlocksLight, description="Attribute indicating if the entity blocks light")
    node: Optional[Node] = Field(default=None, description="The node the entity is currently in")
    inventory: List[GameEntity] = Field(default_factory=list, description="The entities stored inside this entity's inventory")
    stored_in: Optional[GameEntity] = Field(default=None, description="The entity this entity is stored inside, if any")

    @property
    def position(self) -> Position:
        if self.stored_in:
           
            return self.stored_in.position
        elif self.node:
            return self.node.position
        return Position()

    def set_node(self, node: Node):
        if self.stored_in:
            raise ValueError("Cannot set node for an entity stored inside another entity's inventory")
        self.node = node
        node.add_entity(self)

    def remove_from_node(self):
        if self.stored_in:
            raise ValueError("Cannot remove from node an entity stored inside another entity's inventory")
        if self.node:
            self.node.remove_entity(self)
            self.node = None

    def update_attributes(self, attributes: Dict[str, Union[Attribute, Node, str, List[str]]]) -> "GameEntity":
        updated_attributes = {"name": self.name}  # Preserve the name attribute
        new_node = None
        new_stored_in = None
        new_inventory = None
        for attr_name, value in attributes.items():
            if attr_name == "node":
                if isinstance(value, Node):
                    new_node = value
                elif isinstance(value, str):
                    new_node = Node.get_instance(value)  # Retrieve the Node instance using the ID
            elif attr_name == "stored_in":
                if value is not None:
                    new_stored_in = GameEntity.get_instance(value)  # Retrieve the GameEntity instance using the ID
                else:
                    new_stored_in = None  # Set new_stored_in to None if the value is None
            elif attr_name == "inventory" and isinstance(value, list):
                new_inventory = [GameEntity.get_instance(item_id) for item_id in value]  # Retrieve GameEntity instances using their IDs
            elif isinstance(value, Attribute):
                updated_attributes[attr_name] = value
        if new_stored_in is not None:
            if self.node:
                self.node.remove_entity(self)  # Remove the entity from its current node
            self.stored_in = new_stored_in  # Update the stored_in attribute with the retrieved GameEntity instance
        elif new_node:
            if self.stored_in:
                self.stored_in.inventory.remove(self)  # Remove the entity from its current stored_in inventory
            if self.node:
                self.node.remove_entity(self)  # Remove the entity from its current node
            new_node.add_entity(self)  # Add the entity to the new node
            self.node = new_node  # Update the entity's node reference
        if new_inventory is not None:
            self.inventory = new_inventory  # Update the inventory attribute with the retrieved GameEntity instances
        for attr_name, value in updated_attributes.items():
            setattr(self, attr_name, value)  # Update the entity's attributes
        return self
    
    def add_to_inventory(self, entity: GameEntity):
        if entity not in self.inventory:
            self.inventory.append(entity)
            entity.stored_in = self

    def remove_from_inventory(self, entity: GameEntity):
        if entity in self.inventory:
            self.inventory.remove(entity)
            entity.stored_in = None

    def set_stored_in(self, entity: Optional[GameEntity]):
        if entity is None:
            if self.stored_in:
                self.stored_in.remove_from_inventory(self)
        else:
            entity.add_to_inventory(self)

    
    def __repr__(self):
        attrs = {}
        for key, value in self.__dict__.items():
            if key == 'node' and value is not None:
                attrs[key] = value.non_verbose_repr()
            elif key != 'node':
                attrs[key] = value
        attrs_str = ', '.join(f'{k}={v}' for k, v in attrs.items())
        return f"{self.__class__.__name__}({attrs_str})"

class Node(BaseModel, RegistryHolder):
    name: str = Field("", description="The name of the node")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="The unique identifier of the node")
    position: Position = Field(default_factory=Position, description="The position of the node")
    entities: List[GameEntity] = Field(default_factory=list, description="The game entities contained within the node")
    grid_map: Optional[GridMap] = Field(default=None, exclude=True, description="The grid map the node belongs to")
    blocks_movement: bool = Field(default=False, description="Indicates if the node blocks movement")
    blocks_light: bool = Field(default=False, description="Indicates if the node blocks light")
    
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
        if entity.stored_in:
            raise ValueError("Cannot add an entity stored inside another entity's inventory directly to a node")
        self.entities.append(entity)
        entity.node = self
        self.update_blocking_properties()

    def remove_entity(self, entity: GameEntity):
        if entity.stored_in:
            raise ValueError("Cannot remove an entity stored inside another entity's inventory directly from a node")
        self.entities.remove(entity)
        entity.node = None
        self.update_blocking_properties()

    def update_blocking_properties(self):
        self.blocks_movement = any(entity.blocks_movement.value for entity in self.entities if not entity.stored_in)
        self.blocks_light = any(entity.blocks_light.value for entity in self.entities if not entity.stored_in)
    
    def reset(self):
        self.entities.clear()
        self.blocks_movement = False
        self.blocks_light = False
    
    def neighbors(self) -> List[Node]:
        if self.grid_map:
            return self.grid_map.get_neighbors(self.position.value)
        return []
    
    def update_entity(self, old_entity: GameEntity, new_entity: GameEntity):
        self.remove_entity(old_entity)
        self.add_entity(new_entity)

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
                if not neighbor.blocks_movement:  # Check if the neighbor is walkable
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

    def get_nodes_in_radius(self, position: Tuple[int, int], radius: int) -> List[Node]:
        x, y = position
        nodes = []
        for i in range(x - radius, x + radius + 1):
            for j in range(y - radius, y + radius + 1):
                if 0 <= i < self.width and 0 <= j < self.height:
                    if self._get_distance(position, (i, j)) <= radius:
                        nodes.append(self.grid[i][j])
        return nodes
    
    def get_radius(self, source: Node, max_radius: int) -> Radius:
        nodes = self.get_nodes_in_radius(source.position.value, max_radius)
        return Radius(source=source, max_radius=max_radius, nodes=nodes)


    def _is_within_bounds(self, position: Tuple[int, int]) -> bool:
        x, y = position
        return 0 <= x < self.width and 0 <= y < self.height

    def _get_distance(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


    def raycast(self, source: Node, target: Node) -> Tuple[bool, List[Node]]:
        start = source.position.value
        end = target.position.value
        line_points = self.line(start, end)
        nodes = []
        for point in line_points:
            node = self.get_node(point)
            if node == source or node == target:
                continue
            if node.blocks_light:
                return False, nodes
            nodes.append(node)
        return True, nodes

    def get_raycast(self, source: Node, target: Node) -> RayCast:
        has_path, nodes = self.raycast(source, target)
        return RayCast(source=source, target=target, has_path=has_path, nodes=nodes)

    def shadow_casting(self, origin: Tuple[int, int], max_radius: int = None) -> List[Tuple[int, int]]:
        max_radius = max_radius or max(self.width, self.height)
        visible_cells = [origin]
        step_size = 0.5  # Decrease the step size for better accuracy
        for angle in range(int(360 / step_size)):  # Adjust the loop range based on the new step size
            visible_cells.extend(self.cast_light(origin, max_radius, math.radians(angle * step_size)))
        visible_cells = list(set(visible_cells))  # Take only unique values of visible cells
        return visible_cells

    def cast_light(self, origin: Tuple[int, int], max_radius: int, angle: float) -> List[Tuple[int, int]]:
        x0, y0 = origin
        x1 = x0 + int(max_radius * math.cos(angle))
        y1 = y0 + int(max_radius * math.sin(angle))
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        x, y = x0, y0
        n = 1 + dx + dy
        x_inc = 1 if x1 > x0 else -1
        y_inc = 1 if y1 > y0 else -1
        error = dx - dy
        dx *= 2
        dy *= 2
        line_points = []
        first_iteration = True
        for _ in range(n):
            if self._is_within_bounds((x, y)):
                line_points.append((x, y))
                if not first_iteration and self.get_node((x, y)).blocks_light:
                    break
            first_iteration = False
            if error > 0:
                x += x_inc
                error -= dy
            else:
                y += y_inc
                error += dx
        return line_points

    def line(self, start: Tuple[int, int], end: Tuple[int, int]) -> List[Tuple[int, int]]:
        dx, dy = end[0] - start[0], end[1] - start[1]
        distance = math.sqrt(dx * dx + dy * dy)
        angle = math.atan2(dy, dx)
        return self.cast_light(start, math.ceil(distance), angle)

    def line_of_sight(self, start: Tuple[int, int], end: Tuple[int, int]) -> Tuple[bool, List[Tuple[int, int]]]:
        line_points = self.line(start, end)
        visible_points = []
        for point in line_points[1:]:  # Skip the starting point and iterate through the rest of the points
            if self.get_node(point).blocks_light:
                return False, visible_points
            else:
                visible_points.append(point)
        return True, visible_points

    def get_shadow(self, source: Node, max_radius: int) -> Shadow:
        visible_cells = self.shadow_casting(source.position.value, max_radius)
        nodes = [self.get_node(cell) for cell in visible_cells]
        return Shadow(source=source, max_radius=max_radius, nodes=nodes)
    
    def apply_actions_payload(self, payload: ActionsPayload) -> ActionsResults:
        results = []
        if len(payload.actions) > 0:
            print(f"Applying {len(payload.actions)} actions")
        for action_instance in payload.actions:
            source = GameEntity.get_instance(action_instance.source_id)
            target = GameEntity.get_instance(action_instance.target_id)
            action = action_instance.action

            if action.is_applicable(source, target):
                try:
                    updated_source, updated_target = action.apply(source, target)

                    # Handle inventory-related updates
                    if updated_source.stored_in != source.stored_in:
                        if source.stored_in and source in source.stored_in.inventory:
                            source.stored_in.inventory.remove(source)
                        if updated_source.stored_in:
                            updated_source.stored_in.inventory.append(updated_source)

                    if updated_target.stored_in != target.stored_in:
                        if target.stored_in and target in target.stored_in.inventory:
                            target.stored_in.inventory.remove(target)
                        if updated_target.stored_in:
                            updated_target.stored_in.inventory.append(updated_target)

                    results.append(ActionResult(action_instance=action_instance, success=True))
                except ValueError as e:
                    results.append(ActionResult(action_instance=action_instance, success=False, error=str(e)))
                    break
            else:
                # Check which prerequisite failed and provide a detailed error message
                failed_prerequisites = []
                for statement in action.prerequisites.source_statements:
                    if not statement.validate_condition(source):
                        failed_prerequisites.append(f"Source prerequisite failed: {statement}")
                for statement in action.prerequisites.target_statements:
                    if not statement.validate_condition(target):
                        failed_prerequisites.append(f"Target prerequisite failed: {statement}")
                for statement in action.prerequisites.source_target_statements:
                    if not statement.validate_comparisons(source, target):
                        failed_prerequisites.append(f"Source-Target prerequisite failed: {statement}")

                error_message = "Prerequisites not met:\n" + "\n".join(failed_prerequisites)
                results.append(ActionResult(action_instance=action_instance, success=False, error=error_message))
                break

        return ActionsResults(results=results)
    
    def print_grid(self, path: Optional[Path] = None, radius: Optional[Radius] = None, shadow: Optional[Shadow] = None, raycast: Optional[RayCast] = None):
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
                elif radius and node in radius.nodes:
                    row += "\033[92mR\033[0m "  # Green color for radius
                elif shadow and node == shadow.source:
                    row += "\033[94mS\033[0m "  # Blue color for shadow source
                elif shadow and node in shadow.nodes:
                    row += "\033[92m+\033[0m "  # Green color for shadow
                elif raycast and node in raycast.nodes:
                    row += "\033[92mR\033[0m "  # Green color for raycast
                # elif node.entities:
                #     row += "E "
                else:
                    row += ". "
            print(row)