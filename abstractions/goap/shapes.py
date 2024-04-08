# shapes.py
from typing import List, Optional, Set, Dict, Any
from typing_extensions import Annotated
from pydantic import BaseModel, Field, ValidationInfo, field_validator
from abstractions.goap.nodes import Node, GameEntity

class BaseShape(BaseModel):
    """
    Base class for representing a collection of nodes.
    Attributes:
        nodes (list): The list of nodes in the shape.
    """
    nodes: List[Node] = Field(description="The list of nodes in the shape")

    def has_common_nodes(self, other: 'BaseShape') -> bool:
        """
        Checks if the shape has any nodes in common with another shape.
        Args:
            other (BaseShape): The other shape to compare with.
        Returns:
            bool: True if there are common nodes, False otherwise.
        """
        return bool(set(self.nodes) & set(other.nodes))

    def get_different_nodes(self, other: 'BaseShape') -> Set[Node]:
        """
        Returns the set of nodes that are different between the shape and another shape.
        Args:
            other (BaseShape): The other shape to compare with.
        Returns:
            set: The set of nodes that are different.
        """
        return set(self.nodes) ^ set(other.nodes)

    def is_same_as(self, other: 'BaseShape') -> bool:
        """
        Checks if the shape is the same as another shape.
        Args:
            other (BaseShape): The other shape to compare with.
        Returns:
            bool: True if the shapes are the same, False otherwise.
        """
        return set(self.nodes) == set(other.nodes)

def validate_radius(node: Node, values: Dict[str, Any]) -> Node:
    source = values['source']
    max_radius = values['max_radius']
    grid_map = source.grid_map
    if grid_map._get_distance(source.position.value, node.position.value) > max_radius:
        raise ValueError(f"Node {node} is outside the specified radius")
    return node

class Radius(BaseModel):
    source: Node = Field(description="The source node of the radius")
    max_radius: int = Field(description="The maximum radius of the area")
    nodes: Annotated[List[Node], Field(description="The list of nodes within the radius", validator=validate_radius)]

def validate_shadow(node: Node, values: Dict[str, Any]) -> Node:
    source = values['source']
    max_radius = values['max_radius']
    grid_map = source.grid_map
    if grid_map._get_distance(source.position.value, node.position.value) > max_radius:
        raise ValueError(f"Node {node} is outside the specified shadow radius")
    return node

class Shadow(BaseShape):
    """
    Represents the observable area around a source node.
    Attributes:
        source (Node): The source node of the shadow.
        max_radius (int): The maximum radius of the shadow.
    """
    source: Node = Field(description="The source node of the shadow")
    max_radius: int = Field(description="The maximum radius of the shadow")
    nodes: Annotated[List[Node], Field(description="The list of nodes within the shadow", validator=validate_shadow)]

def validate_raycast(node: Node, values: Dict[str, Any]) -> Node:
    source = values['source']
    target = values['target']
    grid_map = source.grid_map
    nodes = values['nodes']
    if node == source or node == target:
        return node
    if node not in grid_map.get_neighbors(nodes[nodes.index(node) - 1].position.value):
        raise ValueError(f"Node {node} is not adjacent to the previous node in the raycast path")
    if node.blocks_light.value:
        raise ValueError(f"Node {node} blocks vision along the raycast path")
    return node

class RayCast(BaseShape):
    """
    Represents a line of sight between a source node and a target node.
    Attributes:
        source (Node): The source node of the raycast.
        target (Node): The target node of the raycast.
    """
    source: Node = Field(description="The source node of the raycast")
    target: Node = Field(description="The target node of the raycast")
    nodes: Annotated[List[Node], Field(description="The list of nodes along the raycast path", validator=validate_raycast)]

def validate_path(node: Node, values: Dict[str, Any]) -> Node:
    start = values['start']
    end = values['end']
    nodes = values['nodes']
    if node == start or node == end:
        return node
    if node not in nodes[nodes.index(node) - 1].neighbors():
        raise ValueError(f"Node {node} is not adjacent to the previous node in the path")
    if node.blocks_movement.value:
        raise ValueError(f"Node {node} is not walkable")
    return node

class BlockedRaycast(BaseShape):
    """
    Represents a blocked line of sight between a source node and a target node.
    Attributes:
        source (Node): The source node of the raycast.
        target (Node): The target node of the raycast.
        nodes (List[Node]): The list of nodes along the raycast path up to the blocking node.
        blocking_node (Node): The node where the raycast is blocked.
        blocking_entity (Optional[GameEntity]): The entity in the blocking node that blocks light.
    """
    source: Node = Field(description="The source node of the raycast")
    target: Node = Field(description="The target node of the raycast")
    nodes: List[Node] = Field(description="The list of nodes along the raycast path up to the blocking node")
    blocking_node: Node = Field(description="The node where the raycast is blocked")
    blocking_entity: GameEntity = Field(description="The entity in the blocking node that blocks light")

class Path(BaseShape):
    """
    Represents a path between a start node and an end node.
    Attributes:
        start (Node): The start node of the path.
        end (Node): The end node of the path.
    """
    start: Node = Field(description="The start node of the path")
    end: Node = Field(description="The end node of the path")
    nodes: Annotated[List[Node], Field(description="The list of nodes along the path", validator=validate_path)]

def validate_rectangle(node: Node, values: Dict[str, Any]) -> Node:
    top_left = values['top_left']
    width = values['width']
    height = values['height']
    x, y = node.position.value
    if not (top_left[0] <= x < top_left[0] + width and top_left[1] <= y < top_left[1] + height):
        raise ValueError(f"Node {node} is outside the specified rectangle")
    return node

class Rectangle(BaseShape):
    """
    Represents a rectangular area of nodes.
    Attributes:
        top_left (tuple): The position of the top-left node of the rectangle.
        width (int): The width of the rectangle.
        height (int): The height of the rectangle.
    """
    top_left: tuple = Field(description="The position of the top-left node of the rectangle")
    width: int = Field(description="The width of the rectangle")
    height: int = Field(description="The height of the rectangle")
    nodes: Annotated[List[Node], Field(description="The list of nodes within the rectangle", validator=validate_rectangle)]