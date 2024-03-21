from abstractions.goap.actions import Action, Prerequisites, Consequences
from abstractions.goap.entity import Attribute, Statement
from abstractions.goap.spatial import GameEntity, Node
from typing import Callable

def source_node_comparison(source: Node, target: Node) -> bool:

    return source in target.neighbors()

def target_walkable_comparison(source: GameEntity, target: GameEntity) -> bool:
    return not target.blocks_movement.value

def move_to_target_node(source: GameEntity, target: GameEntity) -> Node:
    return target.node

MoveToTargetNode: Callable[[GameEntity, GameEntity], Node] = move_to_target_node

class MoveStep(Action):
    name: str = "Move Step"
    prerequisites: Prerequisites = Prerequisites(
        source_statements=[Statement(conditions={"can_act": True})],
        target_statements=[Statement(conditions={"blocks_movement": False})],
        source_target_statements=[Statement(comparisons={
            "source_position": ("node", "node", source_node_comparison)
        })]
    )
    consequences: Consequences = Consequences(
        source_transformations={"node": MoveToTargetNode}
    )

class Character(GameEntity):
    can_act: Attribute = Attribute(name="can_act", value=True)