from abstractions.goap.actions import Action, Prerequisites, Consequences
from abstractions.goap.entity import Attribute, Statement
from abstractions.goap.spatial import GameEntity, Node, BlocksMovement
from typing import Callable, Dict, Tuple, Optional, List, Union

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

class TestItem(GameEntity):
    is_pickupable: Attribute = Attribute(name="is_pickupable", value=True)

class Floor(GameEntity):
    blocks_movement: BlocksMovement = BlocksMovement(value=False)

def set_stored_in(source: GameEntity, target: GameEntity) -> GameEntity:
    return source

SetStoredIn: Callable[[GameEntity, GameEntity], GameEntity] = set_stored_in

def set_node(source: GameEntity, target: GameEntity) -> Node:
    target.set_stored_in(None)
    source.node.add_entity(target)
    return source.node

SetNode: Callable[[GameEntity, GameEntity], Node] = set_node

def add_to_inventory(source: GameEntity, target: GameEntity) -> List[GameEntity]:
    source.add_to_inventory(target)
    return source.inventory

def remove_from_inventory(source: GameEntity, target: GameEntity) -> List[GameEntity]:
    source.remove_from_inventory(target)
    return source.inventory

AddToInventory: Callable[[GameEntity, GameEntity], None] = add_to_inventory
RemoveFromInventory: Callable[[GameEntity, GameEntity], None] = remove_from_inventory

class PickupAction(Action):
    name: str = "Pickup"
    prerequisites: Prerequisites = Prerequisites(
        source_statements=[Statement(conditions={"can_act": True})],
        target_statements=[Statement(conditions={"is_pickupable": True})],
        source_target_statements=[]
    )
    consequences: Consequences = Consequences(
        source_transformations={"inventory": AddToInventory},
        target_transformations={"stored_in": SetStoredIn, "node": None}
    )

    def apply(self, source: GameEntity, target: GameEntity) -> Tuple[GameEntity, GameEntity]:
        if not self.is_applicable(source, target):
            raise ValueError("Action prerequisites are not met")
        
        # Remove the target entity from its current node
        if target.node:
            target.node.remove_entity(target)
        
        updated_source, updated_target = self.consequences.apply(source, target)
        if updated_source != source:
            self.propagate_spatial_consequences(updated_source, updated_target)
            self.propagate_inventory_consequences(updated_source, updated_target)
        else:
            updated_source = source
        if updated_target != target:
            self.propagate_spatial_consequences(updated_source, updated_target)
            self.propagate_inventory_consequences(updated_source, updated_target)
        else:
            updated_target = target
        return updated_source, updated_target

def clear_stored_in(source: GameEntity, target: GameEntity) -> None:
    return None

ClearStoredIn: Callable[[GameEntity, GameEntity], None] = clear_stored_in

class DropAction(Action):
    name: str = "Drop"
    prerequisites: Prerequisites = Prerequisites(
        source_statements=[Statement(conditions={"can_act": True})],
        target_statements=[],
        source_target_statements=[]
    )
    consequences: Consequences = Consequences(
        source_transformations={},
        target_transformations={"stored_in": ClearStoredIn, "node": SetNode}
    )