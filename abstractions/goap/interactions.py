from abstractions.goap.actions import Action, Prerequisites, Consequences
from abstractions.goap.entity import Attribute, Statement, Entity
from abstractions.goap.nodes import GameEntity, Node, BlocksMovement, BlocksLight
from typing import Callable, Dict, Tuple, Optional, List, Union
from pydantic import Field

class Health(Attribute):
    value: int = Field(100, description="The current health points of the entity")

class MaxHealth(Attribute):
    value: int = Field(100, description="The maximum health points of the entity")

class AttackPower(Attribute):
    value: int = Field(10, description="The amount of damage the entity inflicts in combat")

class CanAct(Attribute):
    value: bool = Field(True, description="Indicates whether the entity can perform actions")

class IsPickupable(Attribute):
    value: bool = Field(True, description="Indicates whether the entity can be picked up")

class Material(Attribute):
    value: str = Field("", description="The material composition of the entity")

class Open(Attribute):
    value: bool = Field(False, description="Indicates whether the door is open")



class LivingEntity(GameEntity):
    health: Health = Health()
    max_health: MaxHealth = MaxHealth()
    attack_power: AttackPower = AttackPower()
    can_act: CanAct = CanAct()

    def __init__(self, **data):
        super().__init__(**data)
        self.update_can_act()

    def update_can_act(self):
        self.can_act.value = self.is_alive()

    def is_alive(self) -> bool:
        return self.health.value > 0

    def take_damage(self, amount: int):
        self.health.value = max(0, self.health.value - amount)
        self.update_can_act()

    def heal(self, amount: int):
        self.health.value = min(self.health.value + amount, self.max_health.value)
        self.update_can_act()

class InanimateEntity(GameEntity):
    material: Material = Material()

class Character(LivingEntity):
    pass

class Monster(LivingEntity):
    pass

class Door(InanimateEntity):
    open: Open = Open()
    is_locked: Attribute = Attribute(name="is_locked", value=False)
    required_key: Attribute = Attribute(name="required_key", value="")
    blocks_movement: BlocksMovement = BlocksMovement()
    blocks_light: BlocksLight = BlocksLight()

    def __init__(self, **data):
        super().__init__(**data)
        self.update_block_attributes()

    def update_block_attributes(self):
        print("Updating block attributes... for door")
        if self.open.value:
            self.blocks_movement = BlocksMovement(value=False)
            self.blocks_light = BlocksLight(value=False)
        else:
            self.blocks_movement = BlocksMovement(value=True)
            self.blocks_light = BlocksLight(value=True)
  


class Key(InanimateEntity):
    key_name: Attribute = Attribute(name="key_name", value="")
    is_pickupable: IsPickupable = IsPickupable(value=True)

class Treasure(InanimateEntity):
    monetary_value: Attribute = Attribute(name="monetary_value", value=1000)
    is_pickupable: IsPickupable = IsPickupable(value=True)

class Trap(InanimateEntity):
    damage: Attribute = Attribute(name="damage", value=0)
    is_active: Attribute = Attribute(name="is_active", value=True)

class Floor(InanimateEntity):
    blocks_movement: BlocksMovement = BlocksMovement(value=False)

class Wall(InanimateEntity):
    blocks_movement: BlocksMovement = BlocksMovement(value=True)
    blocks_light: BlocksLight = BlocksLight(value=True)

class TestItem(InanimateEntity):
    is_pickupable: IsPickupable = IsPickupable(value=True)


def set_stored_in(source: GameEntity, target: GameEntity) -> GameEntity:
    return source

def source_node_comparison(source: Node, target: Node) -> bool:
    """Check if the source node is the same as or a neighbor of the target node."""
    return target in source.neighbors() or source.id == target.id

def source_node_comparison_and_walkable(source: Node, target: Node) -> bool:
    """Check if the source node is the same as or a neighbor of the target node and the target node is walkable."""
    if target.blocks_movement.value:
        return False

    return target in source.neighbors() or source.id == target.id

def target_walkable_comparison(source: GameEntity, target: GameEntity) -> bool:
    """Check if the target entity does not block movement."""
    return not target.blocks_movement.value

def move_to_target_node(source: GameEntity, target: GameEntity) -> Node:
    """Move the source entity to the target entity's node."""
    return target.node



MoveToTargetNode: Callable[[GameEntity, GameEntity], Node] = move_to_target_node

class MoveStep(Action):
    """Represents a single step movement action."""
    name: str = "Move Step"
    prerequisites: Prerequisites = Prerequisites(
        source_statements=[Statement(conditions={"can_act": True})],
        target_statements=[Statement(conditions={"blocks_movement": False})],
        source_target_statements=[Statement(comparisons={
            "source_position": ("node", "node", source_node_comparison_and_walkable)
        })]
    )
    consequences: Consequences = Consequences(
        source_transformations={"node": MoveToTargetNode}
    )

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
    """Represents the action of picking up an entity."""
    name: str = "Pickup"
    prerequisites: Prerequisites = Prerequisites(
        source_statements=[Statement(conditions={"can_act": True})],
        target_statements=[Statement(conditions={"is_pickupable": True})],
        source_target_statements=[Statement(comparisons={
            "source_position": ("node", "node", source_node_comparison)
        })]
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
    
def is_alive(health: int) -> bool:
    return health > 0

def calculate_damage(source: LivingEntity, target: LivingEntity) -> int:
    return max(0, target.health.value - source.attack_power.value)

class AttackAction(Action):
    """Represents the action of attacking another entity."""
    name: str = "Attack"
    prerequisites: Prerequisites = Prerequisites(
        source_statements=[Statement(conditions={"can_act": True})],
        target_statements=[Statement(conditions={"health": is_alive})],
        source_target_statements=[Statement(comparisons={
            "source_position": ("node", "node", source_node_comparison)
        })]
    )
    consequences: Consequences = Consequences(
        source_transformations={},
        target_transformations={"health": calculate_damage}
    )

def can_be_healed(source: LivingEntity, target: LivingEntity) -> bool:
    return target.health.value < target.max_health.value

def calculate_heal_amount(source: LivingEntity, target: LivingEntity) -> int:
    return min(target.health.value + source.attack_power.value, target.max_health.value)

class HealAction(Action):
    """Represents the action of healing another entity."""
    name: str = "Heal"
    prerequisites: Prerequisites = Prerequisites(
        source_statements=[
            Statement(
                conditions={"can_act": True},
                callables=[]
            )
        ],
        target_statements=[
            Statement(
                conditions={},
                callables=[can_be_healed]
            )
        ],
        source_target_statements=[
            Statement(
                conditions={},
                comparisons={
                    "source_position": ("node", "node", source_node_comparison)
                },
                callables=[]
            )
        ]
    )
    consequences: Consequences = Consequences(
        source_transformations={},
        target_transformations={"health": calculate_heal_amount}
    )
def clear_stored_in(source: GameEntity, target: GameEntity) -> None:
    return None

ClearStoredIn: Callable[[GameEntity, GameEntity], None] = clear_stored_in

class DropAction(Action):
    """Represents the action of dropping an entity."""
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



class OpenAction(Action):
    """Represents the action of opening a Entity."""
    name: str = "Open"
    prerequisites: Prerequisites = Prerequisites(
        source_statements=[Statement(conditions={"can_act": True})],
        target_statements=[Statement(conditions={"is_locked": False, "open": False})],
        source_target_statements=[Statement(comparisons={
            "source_position": ("node", "node", source_node_comparison)
        })]
    )
    consequences: Consequences = Consequences(
        source_transformations={},
        target_transformations={"open": True}
    )

    def apply(self, source: GameEntity, target: Door) -> Tuple[GameEntity, Door]:
        if not self.is_applicable(source, target):
            raise ValueError("Action prerequisites are not met")

        updated_source, updated_target = self.consequences.apply(source, target)
        updated_target.update_block_attributes()
        updated_target.node.update_blocking_properties()

        return updated_source, updated_target
class CloseAction(Action):
    """Represents the action of closing a Entity."""
    name: str = "Close"
    prerequisites: Prerequisites = Prerequisites(
        source_statements=[Statement(conditions={"can_act": True})],
        target_statements=[Statement(conditions={"open": True})],
        source_target_statements=[Statement(comparisons={
            "source_position": ("node", "node", source_node_comparison)
        })]
    )
    consequences: Consequences = Consequences(
        source_transformations={},
        target_transformations={"open": False}
    )
    def apply(self, source: GameEntity, target: Door) -> Tuple[GameEntity, Door]:
        if not self.is_applicable(source, target):
            raise ValueError("Action prerequisites are not met")

        updated_source, updated_target = self.consequences.apply(source, target)
        updated_target.update_block_attributes()
        updated_target.node.update_blocking_properties()

        return updated_source, updated_target



def has_required_key(source: GameEntity, target: Door) -> bool:
    return any(item.key_name.value == target.required_key.value for item in source.inventory)

class UnlockAction(Action):
    """Represents the action of unlocking a Entity."""
    name: str = "Unlock"
    prerequisites: Prerequisites = Prerequisites(
        source_statements=[Statement(conditions={"can_act": True})],
        target_statements=[Statement(conditions={"is_locked": True})],
        source_target_statements=[
            Statement(
                comparisons={"source_position": ("node", "node", source_node_comparison)},
                callables=[has_required_key]
            )
        ]
    )
    consequences: Consequences = Consequences(
        source_transformations={},
        target_transformations={"is_locked": False}
    )

class LockAction(Action):
    """ Represents the action of locking a Entity."""
    name: str = "Lock"
    prerequisites: Prerequisites = Prerequisites(
        source_statements=[Statement(conditions={"can_act": True})],
        target_statements=[Statement(conditions={"is_locked": False, "open": False})],
        source_target_statements=[
            Statement(
                comparisons={"source_position": ("node", "node", source_node_comparison)},
                callables=[has_required_key]
            )
        ]
    )
    consequences: Consequences = Consequences(
        source_transformations={},
        target_transformations={"is_locked": True}
    )