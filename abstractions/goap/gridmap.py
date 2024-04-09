# gridmap.py
from typing import List, Tuple, Dict, Optional, Union, Type, Any
from pydantic import BaseModel, Field
from abstractions.goap.entity import RegistryHolder
from abstractions.goap.nodes import Node, GameEntity, Position
from abstractions.goap.actions import Action
from abstractions.goap.payloads import ActionsPayload, ActionInstance, SummarizedActionPayload, ActionResult, ActionsResults
from abstractions.goap.errors import ActionConversionError, AmbiguousEntityError
from abstractions.goap.spatial import VisibilityGraph, WalkableGraph, PathDistanceResult, shadow_casting, dijkstra, a_star, line_of_sight
from abstractions.goap.shapes import Radius, Shadow, RayCast, Path, Rectangle, BlockedRaycast
import uuid

class GridMap(BaseModel, RegistryHolder):
    id: str = Field("", description="The unique identifier of the grid map")
    width: int = Field(description="The width of the grid map")
    height: int = Field(description="The height of the grid map")
    grid: List[List[Node]] = Field(description="The 2D grid of nodes")
    actions: Dict[str, Type[Action]] = Field(default_factory=dict, description="The registered actions")
    entity_type_map: Dict[str, Type[GameEntity]] = Field(default_factory=dict, description="The mapping of entity type names to entity classes")

    def __init__(self, width: int, height: int, **data):
        id = str(uuid.uuid4())
        grid = [[Node(position=Position(value=(x, y)), gridmap_id=id) for y in range(height)] for x in range(width)]
        BaseModel.__init__(self,width=width, height=height, grid=grid,id=id, **data)
        self.register(self)

    def register_action(self, action_class: Type[Action]):
        self.actions[action_class.__name__] = action_class

    def register_actions(self, action_classes: List[Type[Action]]):
        for action_class in action_classes:
            self.register_action(action_class)

    def get_actions(self) -> Dict[str, Type[Action]]:
        return self.actions

    def get_nodes_in_rect(self, rect: Rectangle) -> List[Node]:
        start_x, start_y = rect.top_left
        end_x = start_x + rect.width
        end_y = start_y + rect.height
        nodes = []
        for y in range(max(0, start_y), min(self.height, end_y)):
            for x in range(max(0, start_x), min(self.width, end_x)):
                node = self.get_node((x, y))
                if node:
                    nodes.append(node)
        return nodes

    def get_visibility_graph(self) -> VisibilityGraph:
        flattened_nodes = [node for row in self.grid for node in row]
        return VisibilityGraph.from_nodes(flattened_nodes)

    def get_node(self, position: Tuple[int, int]) -> Optional[Node]:
        x, y = position
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.grid[x][y]
        return None
    
    def positions_to_nodes(self, positions: List[Tuple[int, int]]) -> List[Node]:
        return [self.get_node(position) for position in positions if self.get_node(position) is not None]
    
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

    def get_walkable_graph(self) -> WalkableGraph:
        walkable_matrix = [[False] * self.width for _ in range(self.height)]
        for x in range(self.width):
            for y in range(self.height):
                node = self.get_node((x, y))
                if node is not None:
                    walkable_matrix[y][x] = not node.blocks_movement.value
        return WalkableGraph(walkable_matrix=walkable_matrix)
    
    def get_rectangle(self, top_left: Tuple[int, int] = (0, 0), width: Optional[int] = None, height: Optional[int] = None) -> Rectangle:
        if width is None:
            width = self.width - top_left[0]
        if height is None:
            height = self.height - top_left[1]
        start_x, start_y = top_left
        end_x = min(start_x + width, self.width)
        end_y = min(start_y + height, self.height)
        nodes = []
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                node = self.get_node((x, y))
                if node:
                    nodes.append(node)
        return Rectangle(top_left=top_left, width=end_x - start_x, height=end_y - start_y, nodes=nodes)

    def get_radius(self, source: Node, max_radius: int) -> Radius:
        nodes = []
        for x in range(max(0, source.position.x - max_radius), min(self.width, source.position.x + max_radius + 1)):
            for y in range(max(0, source.position.y - max_radius), min(self.height, source.position.y + max_radius + 1)):
                node = self.get_node((x, y))
                if node and self._get_distance(source.position.value, node.position.value) <= max_radius:
                    nodes.append(node)
        return Radius(source=source, max_radius=max_radius, nodes=nodes)

    def _get_distance(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> int:
        return max(abs(pos1[0] - pos2[0]), abs(pos1[1] - pos2[1]))

    def get_shadow(self, source: Node, max_radius: int) -> Shadow:
        visibility_graph = self.get_visibility_graph()
        visible_cells = shadow_casting(source.position.value, visibility_graph, max_radius)
        nodes = [self.get_node(cell) for cell in visible_cells if self.get_node(cell) is not None]
        return Shadow(source=source, max_radius=max_radius, nodes=nodes)

    def get_raycast(self, source: Node, target: Node) -> Union[RayCast, BlockedRaycast]:
        visibility_graph = self.get_visibility_graph()
        has_path, points, blocking_point = line_of_sight(source.position.value, target.position.value, visibility_graph)
        nodes = [self.get_node(point) for point in points if self.get_node(point) is not None]
        if has_path:
            return RayCast(source=source, target=target, nodes=nodes)
        else:
            blocking_node = self.get_node(blocking_point)
            blocking_entity = self.get_blocking_entity(blocking_node)
            return BlockedRaycast(source=source, target=target, nodes=nodes, blocking_node=blocking_node, blocking_entity=blocking_entity)

    def get_blocking_entity(self, node: Node) -> Optional[GameEntity]:
        for entity in node.entities:
            if entity.blocks_light.value:
                return entity
        return None

    def get_path(self, start: Node, goal: Node, allow_diagonal: bool = True) -> Optional[Path]:
        walkable_graph = self.get_walkable_graph()
        path_positions = a_star(start.position.value, goal.position.value, walkable_graph, allow_diagonal)
        if path_positions:
            path_nodes = self.positions_to_nodes(path_positions)
            return Path(start=start, end=goal, nodes=path_nodes)
        return None

    def get_path_distance(self, start: Node, max_distance: int, allow_diagonal: bool = True) -> PathDistanceResult:
        walkable_graph = self.get_walkable_graph()
        return dijkstra(start.position.value, walkable_graph, max_distance, allow_diagonal)

    def generate_entity_type_map(self):
        self.entity_type_map = {}
        for row in self.grid:
            for node in row:
                for entity in node.entities:
                    entity_type = type(entity)
                    entity_type_name = entity_type.__name__
                    if entity_type_name not in self.entity_type_map:
                        self.entity_type_map[entity_type_name] = entity_type

    def get_applicable_actions_for_entity(self, source:GameEntity, target:GameEntity ,return_payload = False) -> List[Union[Action,ActionsPayload]]:
        available_actions = []
        for action_class in self.actions.values():
            action = action_class()
            if action.is_applicable(source, target):
                if not return_payload:
                    available_actions.append(action)
                else:
                    action_payload = ActionsPayload(actions=[ActionInstance(source_id=source.id, target_id=target.id, action=action)])
                    available_actions.append(action_payload)
        return available_actions
    
    def get_appplicable_actions_entities_for_node(self, source:GameEntity, target_node:Node,return_payload = False) -> List[Tuple[GameEntity,List[Union[Action,ActionsPayload]]]]:
        available_actions = []
        for entity in target_node.entities:
            entiy_actions = self.get_applicable_actions_for_entity(source,entity,return_payload= return_payload)
            if len(entiy_actions) > 0:
                available_actions.append((entity,entiy_actions))
        return available_actions
    
    def get_applicable_actions_in_neighborhood(self, source:GameEntity, radius:int,return_payload = False) -> List[Tuple[Node,List[Tuple[GameEntity,List[Union[Action,ActionsPayload]]]]]]:
        neighborhood = self.get_radius(source.node, radius)
        node_tuples = []
        for node in neighborhood.nodes:
            node_actions = self.get_appplicable_actions_entities_for_node(source,node,return_payload= return_payload)
            if len(node_actions) > 0:
                node_tuples.append((node,node_actions))
            
    def apply_actions_payload(self, payload: ActionsPayload) -> ActionsResults:
        results = []
        if len(payload.actions) > 0:
            print(f"Applying {len(payload.actions)} actions")
        for action_instance in payload.actions:
            source = GameEntity.get_instance(action_instance.source_id)
            target = GameEntity.get_instance(action_instance.target_id)
            action = action_instance.action
            state_before = {
                "source": source.get_state(),
                "target": target.get_state()
            }
            print(f"Attempting to apply action: {action.name}")
            # print(f"Source: {source}")
            # print(f"Target: {target}")
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
                    state_after = {
                        "source": updated_source.get_state(),
                        "target": updated_target.get_state()
                    }
                    results.append(ActionResult(action_instance=action_instance, success=True, state_before=state_before, state_after=state_after))
                    print(f"Action applied successfully: {action.name}")
                except ValueError as e:
                    results.append(ActionResult(action_instance=action_instance, success=False, error=str(e), state_before=state_before))
                    print(f"Error applying action: {action.name}")
                    print(f"Error message: {str(e)}")
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
                    if not statement.validate_callables(source, target):
                        for callable_obj in statement.callables:
                            if not callable_obj(source, target):
                                docstring = callable_obj.__doc__ or "No docstring available"
                                failed_prerequisites.append(f"Callable prerequisite failed: {callable_obj.__name__}\nDocstring: {docstring}")
                error_message = "Prerequisites not met:\n" + "\n".join(failed_prerequisites)
                results.append(ActionResult(action_instance=action_instance, success=False, error=error_message, state_before=state_before, failed_prerequisites=failed_prerequisites))
                print(f"Action prerequisites not met: {action.name}")
                print(f"Failed prerequisites: {failed_prerequisites}")
        return ActionsResults(results=results)