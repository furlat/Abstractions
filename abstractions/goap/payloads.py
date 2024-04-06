# payloads.py

from typing import List, Optional, Dict, Any, Tuple, Union
from pydantic import BaseModel, Field
from abstractions.goap.actions import Action
from abstractions.goap.nodes import GameEntity, Node
from abstractions.goap.errors import ActionConversionError, AmbiguousEntityError
import typing
if typing.TYPE_CHECKING:
    from abstractions.goap.gridmap import GridMap

class ActionInstance(BaseModel):
    source_id: str
    target_id: str
    action: Action

class ActionResult(BaseModel):
    action_instance: ActionInstance
    success: bool
    error: Optional[str] = None
    failed_prerequisites: List[str] = Field(default_factory=list)
    state_before: Dict[str, Any] = Field(default_factory=dict)
    state_after: Dict[str, Any] = Field(default_factory=dict)

class ActionsResults(BaseModel):
    results: List[ActionResult]

class ActionsPayload(BaseModel):
    actions: List[ActionInstance]
    results: Optional[ActionsResults] = None

    def add_result(self, result: ActionResult):
        if self.results is None:
            self.results = ActionsResults(results=[])
        self.results.results.append(result)


class SummarizedActionPayload(BaseModel):
    """
    Represents an action payload with absolute positions and dictionary-based attributes.
    """
    action_name: str = Field(description="The name of the action.")
    source_entity_type: str = Field(description="The type of the source entity.")
    source_entity_position: Tuple[int, int] = Field(description="The absolute position of the source entity.")
    source_entity_id: Optional[str] = Field(default=None, description="The unique identifier of the source entity. Use only when necessary to disambiguate between multiple entities at the same location.")
    source_entity_name: Optional[str] = Field(default=None, description="The name of the source entity. Use only when necessary to disambiguate between multiple entities at the same location.")
    source_entity_attributes: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional attributes of the source entity.")
    target_entity_type: str = Field(description="The type of the target entity.")
    target_entity_position: Tuple[int, int] = Field(description="The absolute position of the target entity.")
    target_entity_id: Optional[str] = Field(default=None, description="The unique identifier of the target entity. Use only when necessary to disambiguate between multiple entities at the same location.")
    target_entity_name: Optional[str] = Field(default=None, description="The name of the target entity. Use only when necessary to disambiguate between multiple entities at the same location.")
    target_entity_attributes: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional attributes of the target entity.")
    explanation_of_my_behavior: Optional[str] = Field(description="The explanation of the agent's behavior behind the choice of action.")

    def convert_to_actions_payload(self, grid_map: "GridMap") -> Union[ActionsPayload, ActionConversionError]:
        """
        Convert the summarized action payload to an ActionsPayload using the provided GridMap.
        """
        source_entity_type = grid_map.entity_type_map.get(self.source_entity_type)
        if source_entity_type is None:
            return ActionConversionError(message=f"Invalid source entity type: {self.source_entity_type}")
        target_entity_type = grid_map.entity_type_map.get(self.target_entity_type)
        if target_entity_type is None:
            return ActionConversionError(message=f"Invalid target entity type: {self.target_entity_type}")
        source_entity_result = grid_map.find_entity(source_entity_type, self.source_entity_position,
                                                    self.source_entity_id, self.source_entity_name,
                                                    self.source_entity_attributes)
        target_entity_result = grid_map.find_entity(target_entity_type, self.target_entity_position,
                                                    self.target_entity_id, self.target_entity_name,
                                                    self.target_entity_attributes)
        if isinstance(source_entity_result, AmbiguousEntityError):
            return ActionConversionError(
                message=f"Unable to find source entity: {self.source_entity_type} at position {self.source_entity_position}",
                source_entity_error=source_entity_result
            )
        if isinstance(target_entity_result, AmbiguousEntityError):
            return ActionConversionError(
                message=f"Unable to find target entity: {self.target_entity_type} at position {self.target_entity_position}",
                target_entity_error=target_entity_result
            )
        source_entity = source_entity_result
        target_entity = target_entity_result
        if source_entity is None:
            return ActionConversionError(
                message=f"Unable to find source entity: {self.source_entity_type} at position {self.source_entity_position}"
            )
        if target_entity is None:
            return ActionConversionError(
                message=f"Unable to find target entity: {self.target_entity_type} at position {self.target_entity_position}"
            )
        action_class = grid_map.actions.get(self.action_name)
        if action_class is None:
            return ActionConversionError(message=f"Action '{self.action_name}' not found")
        action_instance = ActionInstance(source_id=source_entity.id, target_id=target_entity.id, action=action_class())
        return ActionsPayload(actions=[action_instance])

class SummarizedEgoActionPayload(SummarizedActionPayload):
    """
    Represents an action payload with positions relative to the character and dictionary-based attributes.
    """
    source_entity_position: Tuple[int, int] = Field(description="The position of the source entity relative to the character.")
    target_entity_position: Tuple[int, int] = Field(description="The position of the target entity relative to the character.")

    def to_absolute_payload(self, character_position: Tuple[int, int]) -> "SummarizedActionPayload":
        """
        Convert the egocentric action payload to an absolute version based on the character's position.
        """
        char_x, char_y = character_position
        source_x, source_y = self.source_entity_position
        target_x, target_y = self.target_entity_position
        abs_source_position = (char_x + source_x, char_y + source_y)
        abs_target_position = (char_x + target_x, char_y + target_y)
        return SummarizedActionPayload(
            action_name=self.action_name,
            source_entity_type=self.source_entity_type,
            source_entity_position=abs_source_position,
            source_entity_id=self.source_entity_id,
            source_entity_name=self.source_entity_name,
            source_entity_attributes=self.source_entity_attributes,
            target_entity_type=self.target_entity_type,
            target_entity_position=abs_target_position,
            target_entity_id=self.target_entity_id,
            target_entity_name=self.target_entity_name,
            target_entity_attributes=self.target_entity_attributes,
            explanation_of_my_behavior=self.explanation_of_my_behavior
        )