from typing import List, Optional, Dict, Tuple, Callable, Any
from pydantic import BaseModel, Field
from abstractions.goap.entity import Entity, Statement, Attribute
from abstractions.goap.spatial import GameEntity

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
        updated_source_attributes = {attr_name: Attribute(name=attr_name, value=value) for attr_name, value in self.source_transformations.items()}
        updated_target_attributes = {attr_name: Attribute(name=attr_name, value=value) for attr_name, value in self.target_transformations.items()}

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

    def is_applicable(self, source: Entity, target: Entity) -> bool:
        return self.prerequisites.is_satisfied(source, target)

    def apply(self, source: Entity, target: Entity) -> Tuple[Entity, Entity]:
        if not self.is_applicable(source, target):
            raise ValueError("Action prerequisites are not met")

        updated_source, updated_target = self.consequences.apply(source, target)

        if updated_source != source:
            self.propagate_spatial_consequences(updated_source, updated_target)
            self.propagate_inventory_consequences(updated_source, updated_target)
        else:
            updated_source = source

        if updated_target != target:
            print("Target is updated")
            self.propagate_spatial_consequences(updated_source, updated_target)
            self.propagate_inventory_consequences(updated_source, updated_target)
        else:
            print("Target is not updated")
            updated_target = target

        return updated_source, updated_target

    def propagate_spatial_consequences(self, source: Entity, target: Entity) -> None:
        # Implement spatial consequence propagation logic here
        pass

    def propagate_inventory_consequences(self, source: Entity, target: Entity) -> None:
        # Implement inventory consequence propagation logic here
        pass