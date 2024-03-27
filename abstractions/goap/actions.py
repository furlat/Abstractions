from typing import List, Optional, Dict, Tuple, Callable, Any
from pydantic import BaseModel, Field
from abstractions.goap.entity import Entity, Statement, Attribute
from abstractions.goap.spatial import GameEntity, ActionInstance, Node

class Prerequisites(BaseModel):
    source_statements: List[Statement] = Field(default_factory=list, description="Statements involving only the source entity")
    target_statements: List[Statement] = Field(default_factory=list, description="Statements involving only the target entity")
    source_target_statements: List[Statement] = Field(default_factory=list, description="Statements involving both source and target entities")

    def is_satisfied(self, source: Entity, target: Entity) -> bool:
        return all(statement.validate_condition(source) for statement in self.source_statements) and \
               all(statement.validate_condition(target) for statement in self.target_statements) and \
               all(statement.validate_comparisons(source, target) for statement in self.source_target_statements)

class Consequences(BaseModel):
    source_transformations: Dict[str, Any] = Field(default_factory=dict, description="Attribute transformations for the source entity")
    target_transformations: Dict[str, Any] = Field(default_factory=dict, description="Attribute transformations for the target entity")
   
    def apply(self, source: Entity, target: Entity) -> Tuple[Entity, Entity]:
        updated_source_attributes = {}
        updated_target_attributes = {}

        for attr_name, value in self.source_transformations.items():
            if callable(value):
                result = value(source=source, target=target)
                if attr_name == "node" and isinstance(result, Node):
                    updated_source_attributes[attr_name] = result.id  # Store the ID of the Node
                elif attr_name == "stored_in" and (isinstance(result, GameEntity) or result is None):
                    updated_source_attributes[attr_name] = result.id if result else None  # Store the ID of the entity or None
                elif attr_name == "inventory":
                    updated_source_attributes[attr_name] = [item.id for item in result]  # Store the IDs of the entities in the inventory
                else:
                    updated_source_attributes[attr_name] = Attribute(name=attr_name, value=result)
            elif attr_name == "node" and isinstance(value, Node):
                updated_source_attributes[attr_name] = value.id  # Store the ID of the Node
            elif attr_name == "stored_in" and (isinstance(value, GameEntity) or value is None):
                updated_source_attributes[attr_name] = value.id if value else None  # Store the ID of the entity or None
            elif attr_name == "inventory":
                updated_source_attributes[attr_name] = [item.id for item in value]  # Store the IDs of the entities in the inventory
            else:
                updated_source_attributes[attr_name] = Attribute(name=attr_name, value=value)

        for attr_name, value in self.target_transformations.items():
            if callable(value):
                result = value(source=source, target=target)
                if attr_name == "node" and isinstance(result, Node):
                    updated_target_attributes[attr_name] = result.id  # Store the ID of the Node
                elif attr_name == "stored_in" and (isinstance(result, GameEntity) or result is None):
                    updated_target_attributes[attr_name] = result.id if result else None  # Store the ID of the entity or None
                elif attr_name == "inventory":
                    updated_target_attributes[attr_name] = [item.id for item in result]  # Store the IDs of the entities in the inventory
                else:
                    updated_target_attributes[attr_name] = Attribute(name=attr_name, value=result)
            elif attr_name == "node" and isinstance(value, Node):
                updated_target_attributes[attr_name] = value.id  # Store the ID of the Node
            elif attr_name == "stored_in" and (isinstance(value, GameEntity) or value is None):
                updated_target_attributes[attr_name] = value.id if value else None  # Store the ID of the entity or None
            elif attr_name == "inventory":
                updated_target_attributes[attr_name] = [item.id for item in value]  # Store the IDs of the entities in the inventory
            else:
                updated_target_attributes[attr_name] = Attribute(name=attr_name, value=value)

        if isinstance(source, GameEntity):
            updated_source = source.update_attributes(updated_source_attributes)
        else:
            updated_source = source

        if isinstance(target, GameEntity):
            updated_target = target.update_attributes(updated_target_attributes)
        else:
            updated_target = target

        return updated_source, updated_target
class Action(BaseModel):
    name: str = Field("", description="The name of the action")
    prerequisites: Prerequisites = Field(default_factory=Prerequisites, description="The prerequisite conditions for the action")
    consequences: Consequences = Field(default_factory=Consequences, description="The consequences of the action")

    def is_applicable(self, source: GameEntity, target: GameEntity) -> bool:
        return self.prerequisites.is_satisfied(source, target)

    def apply(self, source: GameEntity, target: GameEntity) -> Tuple[GameEntity, GameEntity]:
        if not self.is_applicable(source, target):
            raise ValueError("Action prerequisites are not met")

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

    def propagate_spatial_consequences(self, source: Entity, target: Entity) -> None:
        # Implement spatial consequence propagation logic here
        pass

    def propagate_inventory_consequences(self, source: Entity, target: Entity) -> None:
        # Implement inventory consequence propagation logic here
        pass
ActionInstance.model_rebuild()