# spatial.py
from typing import List, Tuple, Dict, Optional
from pydantic import BaseModel
import math
import heapq
from abstractions.goap.entity import RegistryHolder
from abstractions.goap.nodes import Node, Position
from abstractions.goap.shapes import BaseShape, Radius, Path, Shadow

class VisibilityGraph(BaseModel):
    visibility_matrix: List[List[bool]]

    @classmethod
    def from_nodes(cls, nodes: List[Node]) -> 'VisibilityGraph':
        width = max(node.position.x for node in nodes) + 1
        height = max(node.position.y for node in nodes) + 1
        visibility_matrix = [[False] * width for _ in range(height)]
        for node in nodes:
            x, y = node.position.x, node.position.y
            visibility_matrix[y][x] = not node.blocks_light.value
        return cls(visibility_matrix=visibility_matrix)

class WalkableGraph(BaseModel):
    walkable_matrix: List[List[bool]]

    @classmethod
    def from_nodes(cls, nodes: List[List[Node]]) -> 'WalkableGraph':
        width = max(node.position.x for row in nodes for node in row if node is not None) + 1
        height = max(node.position.y for row in nodes for node in row if node is not None) + 1
        walkable_matrix = [[False] * width for _ in range(height)]
        for row in nodes:
            for node in row:
                if node is not None:
                    x, y = node.position.x, node.position.y
                    walkable_matrix[y][x] = not node.blocks_movement.value
        return cls(walkable_matrix=walkable_matrix)

class PathDistanceResult(BaseModel):
    distances: Dict[Tuple[int, int], int]
    paths: Dict[Tuple[int, int], Path]

def get_neighbors(position: Tuple[int, int], walkable_graph: WalkableGraph, allow_diagonal: bool = True) -> List[Tuple[int, int]]:
    x, y = position
    neighbors = []
    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
        new_x, new_y = x + dx, y + dy
        if 0 <= new_x < len(walkable_graph.walkable_matrix[0]) and 0 <= new_y < len(walkable_graph.walkable_matrix):
            if walkable_graph.walkable_matrix[new_y][new_x]:
                neighbors.append((new_x, new_y))
    if allow_diagonal:
        for dx, dy in [(1, 1), (-1, 1), (1, -1), (-1, -1)]:
            new_x, new_y = x + dx, y + dy
            if 0 <= new_x < len(walkable_graph.walkable_matrix[0]) and 0 <= new_y < len(walkable_graph.walkable_matrix):
                if walkable_graph.walkable_matrix[new_y][new_x]:
                    neighbors.append((new_x, new_y))
    return neighbors

def dijkstra(start: Tuple[int, int], walkable_graph: WalkableGraph, max_distance: int, allow_diagonal: bool = True) -> PathDistanceResult:
    distances: Dict[Tuple[int, int], int] = {start: 0}
    paths: Dict[Tuple[int, int], Path] = {start: Path(nodes=[start])}
    unvisited = [(0, start)]
    while unvisited:
        current_distance, current_position = heapq.heappop(unvisited)
        if current_distance > max_distance:
            break
        for neighbor in get_neighbors(current_position, walkable_graph, allow_diagonal):
            new_distance = current_distance + 1
            if neighbor not in distances or new_distance < distances[neighbor]:
                distances[neighbor] = new_distance
                paths[neighbor] = Path(nodes=paths[current_position].nodes + [neighbor])
                heapq.heappush(unvisited, (new_distance, neighbor))
    return PathDistanceResult(distances=distances, paths=paths)

def a_star(start: Tuple[int, int], goal: Tuple[int, int], walkable_graph: WalkableGraph, allow_diagonal: bool = True) -> Optional[List[Tuple[int, int]]]:
    if start == goal:
        return [start]
    if not walkable_graph.walkable_matrix[goal[1]][goal[0]]:
        return None

    def heuristic(position: Tuple[int, int]) -> int:
        return abs(position[0] - goal[0]) + abs(position[1] - goal[1])

    open_set = [(0, start)]
    came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
    g_score: Dict[Tuple[int, int], int] = {start: 0}
    f_score: Dict[Tuple[int, int], int] = {start: heuristic(start)}

    while open_set:
        current_position = heapq.heappop(open_set)[1]
        if current_position == goal:
            path_positions = []
            while current_position in came_from:
                path_positions.append(current_position)
                current_position = came_from[current_position]
            path_positions.append(start)
            path_positions.reverse()
            return path_positions

        for neighbor in get_neighbors(current_position, walkable_graph, allow_diagonal):
            tentative_g_score = g_score[current_position] + 1
            if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                came_from[neighbor] = current_position
                g_score[neighbor] = tentative_g_score
                f_score[neighbor] = tentative_g_score + heuristic(neighbor)
                if (f_score[neighbor], neighbor) not in open_set:
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))

    return None

def shadow_casting(origin: Tuple[int, int], visibility_graph: VisibilityGraph, max_radius: int = None) -> List[Tuple[int, int]]:
    max_radius = max_radius or max(len(visibility_graph.visibility_matrix), len(visibility_graph.visibility_matrix[0]))
    visible_cells = [origin]
    for angle in range(0, 360, 1):
        visible_cells.extend(cast_light(origin, visibility_graph, max_radius, math.radians(angle)))
    visible_cells = list(set(visible_cells))
    return visible_cells

def cast_light(origin: Tuple[int, int], visibility_graph: VisibilityGraph, max_radius: int, angle: float) -> List[Tuple[int, int]]:
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
    for _ in range(n):
        if is_within_bounds((x, y), visibility_graph):
            line_points.append((x, y))
            if not visibility_graph.visibility_matrix[y][x]:
                break
        if error > 0:
            x += x_inc
            error -= dy
        else:
            y += y_inc
            error += dx
    return line_points

def is_within_bounds(position: Tuple[int, int], visibility_graph: VisibilityGraph) -> bool:
    x, y = position
    return 0 <= x < len(visibility_graph.visibility_matrix[0]) and 0 <= y < len(visibility_graph.visibility_matrix)

def line(start: Tuple[int, int], end: Tuple[int, int], visibility_graph: VisibilityGraph) -> List[Tuple[int, int]]:
    dx, dy = end[0] - start[0], end[1] - start[1]
    distance = math.sqrt(dx * dx + dy * dy)
    angle = math.atan2(dy, dx)
    return cast_light(start, visibility_graph, math.ceil(distance), angle)

def line_of_sight(start: Tuple[int, int], end: Tuple[int, int], visibility_graph: VisibilityGraph) -> Tuple[bool, List[Tuple[int, int]]]:
    line_points = line(start, end, visibility_graph)
    visible_points = []
    for point in line_points[1:]:
        x, y = point
        if not visibility_graph.visibility_matrix[y][x]:
            return False, visible_points
        else:
            visible_points.append(point)
    return True, visible_points