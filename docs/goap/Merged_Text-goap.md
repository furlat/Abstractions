# Combined Text Dir from goap

- Full filepath to the merged directory: `C:\Users\Tommaso\Documents\Dev\Abstractions\abstractions\goap`

- Created: `2024-04-08T13:59:44.555527`

## init

# This is the __init__.py file for the package.


---

## actions

from typing import List, Optional, Dict, Tuple, Callable, Any
from pydantic import BaseModel, Field
from abstractions.goap.entity import Entity, Statement, Attribute
from abstractions.goap.nodes import GameEntity, Node

class Prerequisites(BaseModel):
    source_statements: List[Statement] = Field(default_factory=list, description="Statements involving only the source entity")
    target_statements: List[Statement] = Field(default_factory=list, description="Statements involving only the target entity")
    source_target_statements: List[Statement] = Field(default_factory=list, description="Statements involving both source and target entities")

    def is_satisfied(self, source: Entity, target: Entity) -> bool:
        try:
            return all(statement.validate_condition(source) for statement in self.source_statements) and \
                all(statement.validate_condition(target) for statement in self.target_statements) and \
                all(statement.validate_comparisons(source, target) for statement in self.source_target_statements) and \
                all(statement.validate_callables(source, target) for statement in self.source_statements + self.target_statements + self.source_target_statements)
        except Exception as e:
            return False

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
    
class Goal(BaseModel):
    name: str
    source_entity_id: str
    target_entity_id: Optional[str] = None
    prerequisites: Prerequisites

    def is_achieved(self) -> bool:
        source_entity = GameEntity.get_instance(self.source_entity_id)
        target_entity = GameEntity.get_instance(self.target_entity_id) if self.target_entity_id else None
        return self.prerequisites.is_satisfied(source_entity, target_entity)


---

## agents

import random
from typing import List, Dict, Any, Optional, Tuple, Union
from pydantic import BaseModel, Field, conlist
from abstractions.goap.entity import Statement
from abstractions.goap.spatial import GridMap, Node, GameEntity, ActionResult, ActionsPayload, SummarizedActionPayload, SummarizedEgoActionPayload
from abstractions.goap.interactions import Move, Pickup, Drop, Open, Close, Unlock, Lock
from abstractions.goap.game.main import generate_dungeon
import outlines
from outlines import models, generate
from llama_cpp import Llama
import re

from abc import ABC, abstractmethod

class MemoryInstance(BaseModel):
    observation: str
    action: Optional[Union[SummarizedActionPayload, "OutlinesActionPayload", "OutlinesEgoActionPayload"]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    failed_prerequisites: Optional[List[str]] = None
    notes: Optional[str] = None

class MemorySequence(BaseModel):
    entries: List[MemoryInstance] = Field(default_factory=list)
    notes: Optional[str] = None

    def add_entry(self, entry: MemoryInstance):
        self.entries.append(entry)

    def get_recent_entries(self, count: int) -> List[MemoryInstance]:
        return self.entries[-count:]

    def summarize(self, length: Optional[int] = None, character_id: Optional[str] = None) -> str:
        summaries = []
        target = self.entries if length is None else self.entries[-length:]
        for entry in target:
            summary = f"Observation: {self._summarize_observation(entry.observation)}\n"
            if entry.action:
                summary += f"Action: {self._summarize_action(entry.action, character_id)}\n"
            if entry.result:
                summary += f"Result: {self._summarize_result(entry.result)}\n"
            if entry.error:
                summary += f"Error: {entry.error}\n"
            if entry.failed_prerequisites:
                summary += f"Failed Prerequisites:\n{self._summarize_failed_prerequisites(entry.failed_prerequisites)}\n"
            if entry.notes:
                summary += f"Notes: {entry.notes}\n"
            summaries.append(summary)
        if self.notes:
            summaries.append(f"Sequence Notes: {self.notes}")
        return "\n".join(summaries)

    def _summarize_observation(self, observation: str) -> str:
        # Extract key entities, positions, and state changes compared to the previous observation
        lines = observation.split("\n")
        summary = []
        for line in lines:
            if "Entity Types" in line:
                entity_types = re.findall(r"\[.*?\]", line)[0]
                summary.append(f"Entity Types: {entity_types}")
            elif "Positions" in line:
                positions = line.split("Positions:")[1].strip()
                summary.append(f"Positions: {positions}")
            elif "Attributes" in line:
                attributes = re.findall(r"\(.*?\)", line)
                filtered_attributes = [attr for attr in attributes if "BlocksMovement" in attr or "BlocksLight" in attr]
                if filtered_attributes:
                    summary.append(f"Attributes: {', '.join(filtered_attributes)}")
        return "\n".join(summary)

    def _summarize_action(self, action: Union[SummarizedActionPayload, "OutlinesActionPayload", "OutlinesEgoActionPayload"], character_id: str) -> str:
        if isinstance(action, SummarizedActionPayload):
            return action.model_dump()
        elif isinstance(action, (OutlinesActionPayload, OutlinesEgoActionPayload)):
            return action.to_summarized_payload(character_id=character_id).model_dump()

    def _summarize_result(self, result: Dict[str, Any]) -> str:
        # Extract the success status and highlight the main changes in the source and target entities
        success = result["success"]
        source_before = result["state_before"]["source"]
        source_after = result["state_after"]["source"]
        target_before = result["state_before"]["target"]
        target_after = result["state_after"]["target"]

        summary = [f"Success: {success}"]

        source_changes = self._get_entity_changes(source_before, source_after)
        if source_changes:
            summary.append(f"Source Changes: {', '.join(source_changes)}")

        target_changes = self._get_entity_changes(target_before, target_after)
        if target_changes:
            summary.append(f"Target Changes: {', '.join(target_changes)}")

        return "\n".join(summary)

    def _get_entity_changes(self, before: Dict[str, Any], after: Dict[str, Any]) -> List[str]:
        changes = []
        for key in before:
            if key in after and before[key] != after[key]:
                changes.append(f"{key}: {before[key]} -> {after[key]}")
        return changes

    def _summarize_failed_prerequisites(self, failed_prerequisites: List[str]) -> str:
        # Extract the failed prerequisite statements and include the docstrings of any failed callables
        summary = []
        for prerequisite in failed_prerequisites:
            summary.append(prerequisite)
            if "Callable" in prerequisite:
                callable_name = prerequisite.split(":")[1].strip()
                callable_obj = next((c for c in self.entries[-1].action.prerequisites.source_statements + 
                                     self.entries[-1].action.prerequisites.target_statements +
                                     self.entries[-1].action.prerequisites.source_target_statements
                                     if hasattr(c, "callables") and callable_name in [c.__name__ for c in c.callables]), None)
                if callable_obj:
                    docstring = callable_obj.__doc__ or "No docstring available"
                    summary.append(f"  {docstring}")
        return "\n".join(summary)

class AgentGoal(BaseModel):
    statement: Statement
    priority: int

class RunMetadata(BaseModel):
    character_id: str
    run_number: int

class AbcAgent(ABC):
    def __init__(self, grid_map: GridMap, character_id: str, use_egocentric: bool = False, use_outlines: bool = False):
        self.grid_map = grid_map
        self.character_id = character_id
        self.use_egocentric = use_egocentric
        self.use_outlines = use_outlines
        self.goals: List[AgentGoal] = []

    @abstractmethod
    def generate_action(self, shadow_payload: str) -> Optional[SummarizedActionPayload]:
        pass

class FakeLLM(AbcAgent):
    def __init__(self, grid_map: GridMap, character_id: str, use_egocentric: bool = False, use_outlines: bool = False):
        super().__init__(grid_map, character_id, use_egocentric, use_outlines)
        

    def generate_action(self, shadow_payload: str) -> Optional[SummarizedActionPayload]:
        current_position = self.get_current_position()
        if current_position:
            return self.random_walk(current_position)
        return None

    def random_walk(self, current_position: Tuple[int, int]) -> Optional[SummarizedActionPayload]:
        x, y = current_position
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        direction = random.choice(directions)
        dx, dy = direction

        if self.use_egocentric:
            target_position = (dx, dy)
            absolute_target_position = (x + dx, y + dy)
        else:
            target_position = (x + dx, y + dy)
            absolute_target_position = target_position

        target_node = self.grid_map.get_node(absolute_target_position)
        if target_node:
            floor_entities = [entity for entity in target_node.entities if entity.name.startswith("Floor")]
            if floor_entities:
                if self.use_egocentric:
                    if self.use_outlines:
                        move_action = OutlinesEgoActionPayload(
                            action_name="Move",
                            source_entity_type="Character",
                            source_entity_position=[0, 0],
                            target_entity_type="Floor",
                            target_entity_position=list(target_position)
                        )
                    else:
                        move_action = SummarizedEgoActionPayload(
                            action_name="Move",
                            source_entity_type="Character",
                            source_entity_position=(0, 0),
                            target_entity_type="Floor",
                            target_entity_position=target_position
                        )
                else:
                    if self.use_outlines:
                        move_action = OutlinesActionPayload(
                            action_name="Move",
                            source_entity_type="Character",
                            source_entity_position=list(current_position),
                            target_entity_type="Floor",
                            target_entity_position=list(target_position)
                        )
                    else:
                        move_action = SummarizedActionPayload(
                            action_name="Move",
                            source_entity_type="Character",
                            source_entity_position=current_position,
                            target_entity_type="Floor",
                            target_entity_position=target_position
                        )
                return move_action
        return None


    def get_current_position(self) -> Tuple[int, int]:
        character_entity = self.get_character_entity()
        if character_entity and character_entity.node:
            return character_entity.node.position.value
        return None

    def get_character_entity(self) -> Optional[GameEntity]:
        return GameEntity.get_instance(self.character_id)

@outlines.prompt
def system_prompt(registered_actions, use_egocentric, use_outlines, outlines_ego_action_payload, outlines_action_payload, summarized_ego_action_payload, summarized_action_payload):
    """
    <|im_start|>system
    You are an agent in a turn-based game world. The game takes place on a grid-based map, where each node can contain various entities, such as characters, items, and obstacles.
    Your controlled entity has the type Character, so when you will se references to a Character entity, it represents you, the agent.

    Available Actions:
    {% for action_name, action_class in registered_actions.items() %}
    {% set action_instance = action_class() %}
    - {{ action_name }}:
        Description: {{ action_class.__doc__ }}
        Parameters:
        {% for field_name, field in action_class.__fields__.items() %}
        - {{ field_name }}: {{ field.description }}
        {% endfor %}
        Prerequisites:
        {% for statement in action_instance.prerequisites.source_statements %}
        - Source Statement:
            Conditions: {{ statement.conditions }}
            {% if statement.callables %}
            Callables:
            {% for callable in statement.callables %}
            - {{ callable.__name__ }}: {{ callable.__doc__ }}
            {% endfor %}
            {% endif %}
        {% endfor %}
        {% for statement in action_instance.prerequisites.target_statements %}
        - Target Statement:
            Conditions: {{ statement.conditions }}
            {% if statement.callables %}
            Callables:
            {% for callable in statement.callables %}
            - {{ callable.__name__ }}: {{ callable.__doc__ }}
            {% endfor %}
            {% endif %}
        {% endfor %}
        {% for statement in action_instance.prerequisites.source_target_statements %}
        - Source-Target Statement:
            Conditions: {{ statement.conditions }}
            Comparisons: {{ statement.comparisons }}
            {% if statement.callables %}
            Callables:
            {% for callable in statement.callables %}
            - {{ callable.__name__ }}: {{ callable.__doc__ }}
            {% endfor %}
            {% endif %}
        {% endfor %}
        Consequences:
        - Source Transformations: {{ action_instance.consequences.source_transformations }}
        - Target Transformations: {{ action_instance.consequences.target_transformations }}
    {% endfor %}

    Observation Space:
    - You receive observations in the form of Shadow payloads, which represent your visible surroundings.
    - Each Shadow payload contains a list of visible nodes and the entities present at each node.
    - Entities have types, names, and attributes that describe their properties and state.
    - Give particulat attetion tothe BlocksMovement and BlocksLight attributes of the entities in the Shadow payload as they propagate to all entities in the same node. So if a node has both a floor and closed door that blocks movement, the floor will also block movement.
    - The positions in the Shadow payload are compressed to save space using the following techniques:
      - Positions are grouped by entity equivalence classes, where all positions with the same set of entities are reported together.
      - Positions are represented using range notation, where a contiguous range of positions is denoted as "start:end".
      - Individual positions are separated by commas, and ranges are separated by commas as well.
    - The structure of the Shadow payload is as follows:
      - Each line represents an entity equivalence class, starting with "Entity Types:" followed by a list of entity types.
      - The attributes of the entities in the equivalence class are listed after "Attributes:" as a list of (attribute_name, attribute_value) tuples.
      - The positions of the entities in the equivalence class are listed after "Positions:" using the compressed notation described above.
    {% if use_egocentric %}
    - The positions in the Shadow payload are relative to your current position (egocentric perspective).
      Example Shadow Payload (Egocentric):
      Entity Types: ['Floor'], Attributes: [('BlocksLight', False), ('BlocksMovement', False), ('Material', '')], Positions: (-5:-3, -1:2), (3:5, -1:1), (-3, -1:1), (-2, -1:1), (-1, -1:1), (1, -1:1), (2, -1:1), (0, -1), (4, 1)
      Entity Types: ['Character', 'Floor'], Attributes: [('AttackPower', 10), ('BlocksLight', False), ('BlocksLight', False), ('BlocksMovement', False), ('BlocksMovement', False), ('CanAct', True), ('Health', 100), ('Material', ''), ('MaxHealth', 100)], Positions: (0, 0)
      Entity Types: ['InanimateEntity', 'Floor'], Attributes: [('BlocksLight', False), ('BlocksLight', True), ('BlocksMovement', False), ('BlocksMovement', True), ('Material', ''), ('Material', '')], Positions: (-2:0, 1), (1:3, 1)
      Entity Types: ['Door', 'Floor'], Attributes: [('BlocksLight', False), ('BlocksLight', True), ('BlocksMovement', False), ('BlocksMovement', True), ('Material', ''), ('Material', ''), ('Open', False), ('is_locked', True), ('required_key', 'Golden Key')], Positions: (0, 1)
    {% else %}
    - The positions in the Shadow payload are absolute positions on the grid map.
      Example Shadow Payload (Absolute):
      Entity Types: ['Floor'], Attributes: [('BlocksLight', False), ('BlocksMovement', False), ('Material', '')], Positions: (0:2, 0:3), (8:10, 0:2), (2, 0:2), (3, 0:2), (4, 0:2), (6, 0:2), (7, 0:2), (5, 0), (9, 2)
      Entity Types: ['Character', 'Floor'], Attributes: [('AttackPower', 10), ('BlocksLight', False), ('BlocksLight', False), ('BlocksMovement', False), ('BlocksMovement', False), ('CanAct', True), ('Health', 100), ('Material', ''), ('MaxHealth', 100)], Positions: (5, 1)
      Entity Types: ['InanimateEntity', 'Floor'], Attributes: [('BlocksLight', False), ('BlocksLight', True), ('BlocksMovement', False), ('BlocksMovement', True), ('Material', ''), ('Material', '')], Positions: (3:5, 2), (6:8, 2)
      Entity Types: ['Door', 'Floor'], Attributes: [('BlocksLight', False), ('BlocksLight', True), ('BlocksMovement', False), ('BlocksMovement', True), ('Material', ''), ('Material', ''), ('Open', False), ('is_locked', True), ('required_key', 'Golden Key')], Positions: (5, 2)
    {% endif %}

    Game Flow:
    - The game progresses in turns, and you can take one action per turn.
    - After each action, you will receive an updated observation reflecting the changes in the game world.
    - Your goal is to make decisions and take actions based on your observations to achieve the desired objectives.

    Action Generation:
    - To take an action, you need to generate an action payload that specifies the action name, the source entity (yourself), and the target entity (if applicable).
    - The action payload should conform to the structure defined by the game engine's registered actions.
    {% if use_egocentric %}
    - The positions in the action payload should be relative to your current position (egocentric perspective).
    {% else %}
    - The positions in the action payload should be absolute positions on the grid map.
    {% endif %}
    {% if use_outlines %}
    - The action payload should follow the structure of the {{ outlines_ego_action_payload | schema if use_egocentric else outlines_action_payload | schema }}.
    {% else %}
    - The action payload should follow the structure of the {{ summarized_ego_action_payload | schema if use_egocentric else summarized_action_payload | schema }}.
    {% endif %}
    - If the action is valid and successfully executed, you will receive an ActionResult object with the updated game state.
    - If the action is invalid or cannot be executed, you will receive an ActionConversionError object with details about the error.

    Remember to carefully consider your observations, goals, and the available actions when making decisions. Good luck!<|im_end|>
    """

@outlines.prompt
def action_generation_prompt(shadow_payload, goals, memory_summary, use_egocentric, use_outlines, memory_length, outlines_ego_action_payload, outlines_action_payload, summarized_ego_action_payload, summarized_action_payload, character_position):
    """
    <|im_start|>user
    Current Observation:
    {{ shadow_payload }}
    Goals:
    {% for goal in goals %}
    - {{ goal.statement }}: (Priority: {{ goal.priority }})
    {% endfor %}
    {% if memory_length > 0 %}
    Memory Summary (last {{ memory_length }} steps):
    {{ memory_summary }}
    {% endif %}
    Based on the current observation{% if memory_length > 0 %}, your goals, and memory{% else %} and your goals{% endif %}, what action do you want to take next?
    Respond with a valid action payload following the structure defined by the game engine's registered actions. Remember to always indicate the Target Type as a string e.g. Floor, Door, Key, etc. in the action payload.
    The Character entity represents you, the agent, in the game world. When targeting entities, keep in mind that you can only interact with entities within a range of 1 in all 8 directions relative to your current position.
    {% if use_egocentric %}
    Remember that the range of your actions is limited to the following positions relative to your current position:
    (-1, 0), (0, -1), (0, 1), (1, 0), (0, 0), (-1, -1), (-1, 1), (1, -1), (1, 1)
    Remember to provide positions relative to your current position (egocentric perspective).
    {% else %}
    Remember that the range of your actions is limited to the following positions relative to your current position ({{ character_position }}):
    {% set x, y = character_position %}
    ({{ x - 1 }}, {{ y }}), ({{ x }}, {{ y - 1 }}), ({{ x }}, {{ y + 1 }}), ({{ x + 1 }}, {{ y }}), ({{ x }}, {{ y }}), ({{ x - 1 }}, {{ y - 1 }}), ({{ x - 1 }}, {{ y + 1 }}), ({{ x + 1 }}, {{ y - 1 }}), ({{ x + 1 }}, {{ y + 1 }})
    Remember to provide absolute positions on the grid map.
    {% endif %}
    {% if use_outlines %}
    The action payload should follow the structure of the {{ outlines_ego_action_payload | schema if use_egocentric else outlines_action_payload | schema }}.
    {% else %}
    The action payload should follow the structure of the {{ summarized_ego_action_payload | schema if use_egocentric else summarized_action_payload | schema }}.
    {% endif %}
    Please provide a brief explanation of your behavior and the reasoning behind your chosen action.
    <|im_end|>
    <|im_start|>assistant
    """

class OutlinesActionPayload(BaseModel):
    """
    Represents an action payload with absolute positions and list-based attributes for Outlines compatibility.
    """
    action_name: str = Field(description="The name of the action.")
    target_entity_type: str = Field(description="The type of the target entity. The most fundamental field to be filled in.")
    target_entity_position: conlist(str, min_length=2, max_length=2) = Field(description="The absolute position of the target entity.the most fundamental field to be filled in. Should be possibl to convert to Integers.")
    explanation_of_my_behavior:str = Field(description="The explanation of the agent's behavior behind the choice of action.")

    def to_summarized_payload(self, character_id: str) -> "SummarizedActionPayload":
        """
        Convert the OutlinesActionPayload to a SummarizedActionPayload.
        """
        character_entity = GameEntity.get_instance(character_id)
        character_position = character_entity.node.position.value

        return SummarizedActionPayload(
            action_name=self.action_name,
            source_entity_type="Character",
            source_entity_position=character_position,
            target_entity_type=self.target_entity_type,
            target_entity_position=tuple(int(x) for x in self.target_entity_position),
            explanation_of_my_behavior=self.explanation_of_my_behavior
        )

    def to_ego_payload(self, character_id: str) -> "OutlinesEgoActionPayload":
        """
        Convert the OutlinesActionPayload to an OutlinesEgoActionPayload relative to the character's position.
        """
        return OutlinesEgoActionPayload(
            action_name=self.action_name,
            target_entity_type=self.target_entity_type,
            target_entity_position=self.target_entity_position,
            explanation_of_my_behavior=self.explanation_of_my_behavior
        )

class OutlinesEgoActionPayload(BaseModel):
    """
    Represents an action payload with positions relative to the character and list-based attributes for Outlines compatibility.
    """
    action_name: str = Field(description="The name of the action.")
    target_entity_type: str = Field(description="The type of the target entity.")
    target_entity_position: conlist(str, min_length=2, max_length=2) = Field(description="The position of the target entity relative to the character. Can be negative. the most fundamental field to be filled in. Should be possibl to convert to Integers.")
    explanation_of_my_behavior:str = Field(description="The explanation of the agent's behavior behind the choice of action.")

    def to_absolute_payload(self, character_id: str) -> "OutlinesActionPayload":
        """
        Convert the OutlinesEgoActionPayload to an OutlinesActionPayload based on the character's position.
        """
        character_entity = GameEntity.get_instance(character_id)
        if character_entity is None or character_entity.node is None:
            raise ValueError(f"Character entity with ID {character_id} not found or not associated with a node.")

        character_position = character_entity.node.position.value

        abs_target_position = [
            character_position[0] + int(self.target_entity_position[0]),
            character_position[1] + int(self.target_entity_position[1])
        ]

        return OutlinesActionPayload(
            action_name=self.action_name,
            target_entity_type=self.target_entity_type,
            target_entity_position=abs_target_position,
            explanation_of_my_behavior=self.explanation_of_my_behavior
        )

    def to_summarized_payload(self, character_id: str) -> "SummarizedEgoActionPayload":
        """
        Convert the OutlinesEgoActionPayload to a SummarizedEgoActionPayload.
        """
        return SummarizedEgoActionPayload(
            action_name=self.action_name,
            source_entity_type="Character",
            source_entity_position=(0, 0),
            target_entity_type=self.target_entity_type,
            target_entity_position=tuple(int(x) for x in self.target_entity_position),
            explanation_of_my_behavior=self.explanation_of_my_behavior
        )

class LLMAgent(AbcAgent):
    def __init__(self, grid_map: GridMap, character_id: str, model_path: str, use_egocentric: bool = False, memory_length: int = 0):
        super().__init__(grid_map, character_id, use_egocentric, use_outlines=True)
        self.model = models.llamacpp(model_path, model_kwargs={"seed": 1337, "n_ctx": 30000, "n_gpu_layers": -1, "verbose": True})
        self.generator = generate.json(self.model, OutlinesEgoActionPayload if use_egocentric else OutlinesActionPayload)
        self.memory_length = memory_length

    def generate_action(self, shadow_payload: str, memory: MemorySequence) -> Optional[Union[OutlinesActionPayload, OutlinesEgoActionPayload]]:
        system_prompt_text = system_prompt(
            self.grid_map.get_actions(),
            self.use_egocentric,
            self.use_outlines,
            OutlinesEgoActionPayload,
            OutlinesActionPayload,
            SummarizedEgoActionPayload,
            SummarizedActionPayload
        )
        character_position = self.get_current_position()
        memory_summary = memory.summarize(length=self.memory_length, character_id=self.character_id)
        action_prompt_text = action_generation_prompt(
            shadow_payload,
            self.goals,
            memory_summary,
            self.use_egocentric,
            self.use_outlines,
            self.memory_length,
            OutlinesEgoActionPayload,
            OutlinesActionPayload,
            SummarizedEgoActionPayload,
            SummarizedActionPayload,
            character_position
        )
        prompt_text = f"{system_prompt_text}\n\n{action_prompt_text}"
        action_payload = self.generator(prompt_text)
        return action_payload


    def get_current_position(self) -> Tuple[int, int]:
        character_entity = self.get_character_entity()
        if character_entity and character_entity.node:
            return character_entity.node.position.value
        return None

    def get_character_entity(self) -> Optional[GameEntity]:
        return GameEntity.get_instance(self.character_id)

class CharacterAgent:
    def __init__(self, grid_map: GridMap, agent: AbcAgent):
        self.grid_map = grid_map
        self.agent = agent
        self.memory = MemorySequence()
        self.goals: List[AgentGoal] = []
        self.metadata: RunMetadata = None
        self.raw_results_payloads = []
        self.use_egocentric = self.agent.use_egocentric
        self.use_outlines = self.agent.use_outlines

    def set_goals(self, goals: List[AgentGoal]):
        self.goals = goals
        self.agent.goals = goals

    def update_memory_notes(self, notes: str):
        self.memory.notes = notes

    def update_instance_notes(self, notes: str):
        if self.memory.entries:
            self.memory.entries[-1].notes = notes

    def set_metadata(self, metadata: RunMetadata):
        self.metadata = metadata

    def generate_action(self, shadow_payload: str) -> Optional[Union[OutlinesActionPayload, OutlinesEgoActionPayload]]:
        action_payload = self.agent.generate_action(shadow_payload, self.memory)
        print(f"Generated Action: {action_payload}")
        if action_payload:
            if self.use_egocentric:
                return action_payload.to_absolute_payload(self.metadata.character_id)
            else:
                return action_payload
        return None

    def process_action_result(self, shadow_payload: str, action_payload: Optional[Union[OutlinesActionPayload, OutlinesEgoActionPayload]], result: Optional[Dict[str, Any]] = None, error: Optional[str] = None, failed_prerequisites: Optional[List[str]] = None):
        memory_instance = MemoryInstance(
            observation=shadow_payload,
            action=action_payload,
            result=result,
            error=error,
            failed_prerequisites=failed_prerequisites,
            notes=None
        )
        self.memory.add_entry(memory_instance)

    def run(self, initial_observation: str):
        observation = initial_observation
        step_count = 0
        while True:
            print(f"\n--- Step: {step_count} ---")
            action_payload = self.generate_action(observation)
            print(f"Generated Action: {action_payload}")
            result, error, failed_prerequisites = self.execute_action(action_payload)
            self.process_action_result(observation, action_payload, result, error)
            if error:
                print(f"Error: {error}, Failed Prerequisites: {failed_prerequisites}")
            if result:
                print("Action Result:")
                print(f" State Before: {result['state_before']}")
                print(f" State After: {result['state_after']}")
            observation = self.get_current_observation()
            if self.check_goal_achieved():
                print("Goal achieved! in step: ", step_count)
                break
            step_count += 1

    def execute_action(self, action_payload: Optional[Union[OutlinesActionPayload, OutlinesEgoActionPayload]]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        if action_payload:
            print("Payload detected", action_payload)
            if self.use_outlines:
                print("Converting to summarized from outlines")
                character_id = self.metadata.character_id
                action_payload = action_payload.to_summarized_payload(character_id=character_id)
            print("Converting summarized payload", action_payload)
            action_result = self.grid_map.convert_summarized_payload(action_payload)
            print("Conversion results:", action_result)
            if isinstance(action_result, ActionsPayload):
                actions_results = self.grid_map.apply_actions_payload(action_result)
                self.raw_results_payloads.append(actions_results)
                if actions_results.results and all(result.success for result in actions_results.results):
                    action_result = actions_results.results[0]
                    result = {
                        "state_before": action_result.state_before,
                        "state_after": action_result.state_after
                    }
                    return result, None, None
                else:
                    error = "Action execution failed"
                    failed_prerequisites = [prereq for result in actions_results.results for prereq in result.failed_prerequisites]
                    return None, error, failed_prerequisites
            else:
                error = str(action_result)
                return None, error, None
        else:
            print("No valid action payload generated.")
            return None, None, None
    def get_current_observation(self) -> str:
        character_entity = self.get_character_entity()
        if character_entity and character_entity.node:
            shadow = self.grid_map.get_shadow(character_entity.node, max_radius=10)
            observation = shadow.to_entity_groups(use_egocentric=self.use_egocentric)
            return observation
        return None

    def get_character_entity(self) -> Optional[GameEntity]:
        if self.metadata:
            character_id = self.metadata.character_id
            return GameEntity.get_instance(character_id)
        return None

    def check_goal_achieved(self) -> bool:
        character_entity = self.get_character_entity()
        if character_entity:
            for goal in self.goals:
                if goal.statement.validate_all(character_entity):
                    return True
        return False

---

## entity

from pydantic import BaseModel, Field, ValidationError, validator, field_validator, ValidationInfo
from typing import Annotated, Any, Dict, List, Optional, Set, Union, Tuple, Callable
from pydantic.functional_validators import AfterValidator
import uuid


class RegistryHolder:
    _registry: Dict[str, 'RegistryHolder'] = {}
    _types : Set[type] = set()

    @classmethod
    def register(cls, instance: 'RegistryHolder'):
        cls._registry[instance.id] = instance
        cls._types.add(type(instance))

    @classmethod
    def get_instance(cls, instance_id: str):
        return cls._registry.get(instance_id)

    @classmethod
    def all_instances(cls, filter_type=True):
        if filter_type:
            return [instance for instance in cls._registry.values() if isinstance(instance, cls)]
        return list(cls._registry.values())
    @classmethod
    def all_instances_by_type(cls, type: type):
        return [instance for instance in cls._registry.values() if isinstance(instance, type)]
    @classmethod
    def all_types(cls, as_string=True):
        if as_string:
            return [type_name.__name__ for type_name in cls._types]
        return cls._types
        

class Attribute(BaseModel, RegistryHolder):
    name: str = Field("", description="The name of the attribute")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="The unique identifier of the attribute")
    value: Any

    def __init__(self, **data: Any):
        super().__init__(**data)
        if not self.name:
            self.name = self.__class__.__name__
        self.register(self)



class Entity(BaseModel, RegistryHolder):
    name: str = Field("", description="The name of the entity")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="The unique identifier of the entity")

    def __init__(self, **data: Any):
        super().__init__(**data)
        if not self.name:
            self.name = self.__class__.__name__
        self.register(self)
        
    
    @field_validator('*', mode='after')
    def check_attributes_and_entities(cls, v: Any, info: ValidationInfo):
        if info.field_name not in ['id', 'name',"node"] and not isinstance(v, (Attribute, Entity)):
            raise ValueError(f"Attributes must be instances of Attribute or Entity, got {type(v).__name__} for field {info.field_name}")
        return v

    
    def all_attributes(self) -> Dict[str, 'Attribute']:
        attributes = {}
        for attribute_name, attribute_value in self.__dict__.items():
            if isinstance(attribute_value, Attribute):
                attributes[attribute_name] = attribute_value
            elif isinstance(attribute_value, Entity):
                nested_attributes = attribute_value.all_attributes()
                attributes.update(nested_attributes)
        return attributes
    

class Statement(BaseModel, RegistryHolder):
    name: str = Field("", description="The name of the statement")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="The unique identifier of the entity")
    conditions: Dict[str, Any] = Field(default_factory=dict, description="The desired attribute conditions for the statement")
    comparisons: Dict[str, Tuple[str, str, Callable[[Any, Any], bool]]] = Field(default_factory=dict, description="The attribute comparisons for the statement")
    callables: List[Callable[[Entity, Entity], bool]] = Field(default_factory=list, description="The generic callables for the statement")

    def __init__(self, **data: Any):
        super().__init__(**data)
        if not self.name:
            self.name = self.__class__.__name__
        self.register(self)

    @classmethod
    def from_entity(cls, entity: Entity, name: Optional[str] = None, conditions: Optional[Dict[str, Any]] = None, comparisons: Optional[Dict[str, Tuple[str, str, Callable[[Any, Any], bool]]]] = None, callables: Optional[List[Callable[[Entity, Entity], bool]]] = None):
        attributes = entity.all_attributes()
        return cls(name=name, conditions=conditions or {}, comparisons=comparisons or {}, callables=callables or [], **attributes)

    @classmethod
    def from_entities(cls, source: Entity, target: Entity, name: Optional[str] = None, conditions: Optional[Dict[str, Any]] = None, comparisons: Optional[Dict[str, Tuple[str, str, Callable[[Any, Any], bool]]]] = None, callables: Optional[List[Callable[[Entity, Entity], bool]]] = None):
        source_attributes = source.all_attributes()
        target_attributes = target.all_attributes()
        attributes = {f"source_{k}": v for k, v in source_attributes.items()}
        attributes.update({f"target_{k}": v for k, v in target_attributes.items()})
        return cls(name=name, conditions=conditions or {}, comparisons=comparisons or {}, callables=callables or [], **attributes)

    def validate_condition(self, entity: Entity) -> bool:
        attributes = entity.all_attributes()
        for attr_name, desired_value in self.conditions.items():
            if attr_name not in attributes or attributes[attr_name].value != desired_value:
                return False
        return True

    def validate_comparisons(self, source: Entity, target: Entity) -> bool:
        for comparison_name, (source_attr, target_attr, comparison_func) in self.comparisons.items():
            source_value = getattr(source, source_attr, None)
            target_value = getattr(target, target_attr, None)
            if source_value is None or target_value is None:
                return False
            elif source_attr == "node" and target_attr == "node":
                if not comparison_func(source_value, target_value):
                    return False
                return True
            elif not comparison_func(source_value.value, target_value.value):
                return False
        return True

    def validate_callables(self, source: Entity, target: Optional[Entity] = None) -> bool:
        for callable_func in self.callables:
            if not callable_func(source, target):
                return False
        return True
    
    def validate_all(self, source: Entity, target: Optional[Entity] = None) -> bool:
        return self.validate_condition(source) and (self.validate_comparisons(source, target) if target else True) and self.validate_callables(source, target)


---

## errors

# error.py

from typing import List, Optional, Dict, Any, Type
from pydantic import BaseModel
from abstractions.goap.nodes import AmbiguousEntityError




class ActionConversionError(BaseModel):
    """
    Represents an error that occurs during the conversion of an action payload.
    Attributes:
        message (str): The error message.
        source_entity_error (Optional[AmbiguousEntityError]): The error related to the source entity, if any.
        target_entity_error (Optional[AmbiguousEntityError]): The error related to the target entity, if any.
    """
    message: str
    source_entity_error: Optional[AmbiguousEntityError] = None
    target_entity_error: Optional[AmbiguousEntityError] = None

    def get_error_message(self) -> str:
        error_message = self.message
        if self.source_entity_error:
            error_message += f"\nSource Entity Error: {self.source_entity_error.get_error_message()}"
        if self.target_entity_error:
            error_message += f"\nTarget Entity Error: {self.target_entity_error.get_error_message()}"
        return error_message

---

## init

# This is the __init__.py file for the package.


---

## gui widgets

import pygame
import pygame_gui
from typing import List, Optional
from pydantic import BaseModel
from abstractions.goap.nodes import GameEntity
from abstractions.goap.game.payloadgen import SpriteMapping
import typing

if typing.TYPE_CHECKING:
    from abstractions.goap.game.input_handler import InputHandler

class InventoryItemVisual(BaseModel):
    sprite_path: str
    name: str
    entity_id: str

class InventoryVisualState(BaseModel):
    items: List[InventoryItemVisual]
    
class InventoryWidget(pygame_gui.elements.UIWindow):
    def __init__(self, pos, manager, sprite_mappings: List[SpriteMapping], input_handler:Optional["InputHandler"] = None):
        super().__init__(pygame.Rect(pos, (200, 150)), manager, window_display_title="Inventory", object_id="#inventory_window")
       
        self.inventory_container = pygame_gui.core.UIContainer(pygame.Rect(0, 0, 200, 150), manager=manager, container=self, object_id="#inventory_container")
       
        self.sprite_mappings = sprite_mappings
        self.visual_state = InventoryVisualState(items=[])
        self.input_handler = input_handler
        self.inventory_changed = False

    def setup_input_handler(self, input_handler: "InputHandler"):
        self.input_handler = input_handler
        
    def update(self, time_delta):
        super().update(time_delta)
   
    def update_inventory(self, inventory: List[GameEntity]):
        if self.visual_state.items != [InventoryItemVisual(sprite_path=self.get_sprite_path(item), name=item.name, entity_id=item.id) for item in inventory]:
            self.inventory_changed = True
            self.update_visual_state(inventory)

            self.inventory_container.kill()
            self.inventory_container = pygame_gui.core.UIContainer(pygame.Rect(0, 0, 200, 150), manager=self.ui_manager, container=self, object_id="#inventory_container")

            if self.visual_state.items:
                for i, item_visual in enumerate(self.visual_state.items):
                    sprite_surface = pygame.image.load(item_visual.sprite_path).convert_alpha()
                    item_image = pygame_gui.elements.UIImage(pygame.Rect((10, 10 + i * 30), (20, 20)), sprite_surface, manager=self.ui_manager, container=self.inventory_container)
                    item_name = pygame_gui.elements.UILabel(pygame.Rect((40, 10 + i * 30), (150, 20)), item_visual.name, manager=self.ui_manager, container=self.inventory_container)

    def process_event(self, event: pygame.event.Event) -> bool:
        handled = super().process_event(event)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # Left mouse button
            mouse_pos = event.pos
            for i, item_visual in enumerate(self.visual_state.items):
                # item_rect = pygame.Rect((self.rect.x + 10, self.rect.y + 10 + i * 30), (190, 20))
                item_rect = pygame.Rect((10, 50 + i * 30), (190, 20))
                if item_rect.collidepoint(mouse_pos):
                    print(f"Clicked on item {item_visual.name}")
                    self.input_handler.active_entities.targeted_inventory_entity_id = item_visual.entity_id
                    self.input_handler.active_entities.targeted_entity_id = None
                    self.input_handler.active_entities.targeted_node_id = None
                    self.input_handler.update_available_actions()
                    handled = True
                    break
        return handled
    
    def update_visual_state(self, inventory: List[GameEntity]):
        item_visuals = []
        for item in inventory:
            sprite_path = self.get_sprite_path(item)
            if sprite_path:
                item_visual = InventoryItemVisual(sprite_path=sprite_path, name=item.name, entity_id=item.id)
                item_visuals.append(item_visual)
        self.visual_state = InventoryVisualState(items=item_visuals)
   
    def get_sprite_path(self, item: GameEntity) -> str:
        for mapping in self.sprite_mappings:
            if isinstance(item, mapping.entity_type):
                return mapping.sprite_path
        return ""

---

## input handler

from typing import Optional, Tuple, List, Union
from abstractions.goap.nodes import GameEntity, Node
from abstractions.goap.gridmap import GridMap
from abstractions.goap.payloads import ActionsPayload, ActionInstance
from abstractions.goap.shapes import Path
from abstractions.goap.interactions import Character, Move, Pickup, Drop, TestItem, Door, Lock, Unlock, Open, Close
from abstractions.goap.actions import Action
from abstractions.goap.game.renderer import CameraControl
from abstractions.goap.game.payloadgen import SpriteMapping
from pydantic import BaseModel, ValidationInfo, field_validator
from abstractions.goap.game.gui_widgets import InventoryWidget
import pygame
import pygame_gui
from pygame_gui import UIManager, UI_TEXT_ENTRY_CHANGED
from pygame_gui.elements import UIWindow, UITextEntryBox


class ActiveEntities(BaseModel):
    controlled_entity_id: Optional[str] = None
    targeted_entity_id: Optional[str] = None
    targeted_inventory_entity_id: Optional[str] = None
    targeted_node_id: Optional[str] = None
    active_widget: Optional[str] = None

    @field_validator('controlled_entity_id')
    def validate_controlled_entity(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        if v is not None:
            controlled_entity = GameEntity.get_instance(v)
            if not isinstance(controlled_entity, Character) or not controlled_entity.can_act.value:
                raise ValueError("Invalid controlled entity")
        return v

    @field_validator('targeted_entity_id')
    def validate_targeted_entity(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        if v is not None:
            GameEntity.get_instance(v)  # Validate if the entity exists
        return v

    @field_validator('targeted_node_id')
    def validate_targeted_node(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        if v is not None:
            Node.get_instance(v)  # Validate if the node exists
        return v

class InputHandler:
    def __init__(self, grid_map: GridMap, sprite_mappings: List[SpriteMapping], ui_manager: pygame_gui.UIManager,
                 grid_map_widget_size: Tuple[int, int], inventory_widget: InventoryWidget, text_entry_box: UITextEntryBox):
        self.grid_map = grid_map
        self.active_entities = ActiveEntities()
        self.mouse_highlighted_node: Optional[Node] = None
        self.camera_control = CameraControl()
        self.actions_payload = ActionsPayload(actions=[])
        self.available_actions: List[str] = []
        self.sprite_mappings = sprite_mappings
        self.active_widget: Optional[str] = None
        self.grid_map_widget_size = grid_map_widget_size
        self.ui_manager = ui_manager
        self.inventory_widget = inventory_widget
        self.inventory_widget.setup_input_handler(self)
        self.text_entry_box = text_entry_box
        self.latest_mouse_click = (0, 0)
        self.llm_action_payload = None

    def handle_input(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN: 
            self.handle_keypress_on_gridmap(event.key)
        elif event.type == pygame.MOUSEMOTION:
            self.handle_mouse_motion(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self.handle_mouse_click(event.button, event.pos)
 
    def handle_keypress_on_gridmap(self, key):
        if self.text_entry_box.rect.collidepoint(self.latest_mouse_click):
            print("trying keywriting but latest was a notepad window clicked")
            
        else:
            
            if key == pygame.K_w:
                self.generate_move_step((0, -1))
            elif key == pygame.K_s:
                self.generate_move_step((0, 1))
            elif key == pygame.K_a:
                self.generate_move_step((-1, 0))
            elif key == pygame.K_d:
                self.generate_move_step((1, 0))
            elif key == pygame.K_1:
                self.camera_control.zoom = 1
            elif key == pygame.K_2:
                self.camera_control.zoom = -1
            elif key == pygame.K_SPACE:
                self.camera_control.recenter = True
            elif key == pygame.K_q:
                self.camera_control.toggle_ascii = not self.camera_control.toggle_ascii
            elif key == pygame.K_p:
                self.camera_control.toggle_path = not self.camera_control.toggle_path
                print(f"Path: {self.camera_control.toggle_path}")
            elif key == pygame.K_t:
                self.camera_control.toggle_shadow = not self.camera_control.toggle_shadow
                print(f"Shadow: {self.camera_control.toggle_shadow}")
            elif key == pygame.K_c:
                self.camera_control.toggle_raycast = not self.camera_control.toggle_raycast
                print(f"Raycast: {self.camera_control.toggle_raycast}")
            elif key == pygame.K_r:
                self.camera_control.toggle_radius = not self.camera_control.toggle_radius
                print(f"Radius: {self.camera_control.toggle_radius}")
            elif key == pygame.K_f:
                self.camera_control.toggle_fov = not self.camera_control.toggle_fov
                print(f"FOV: {self.camera_control.toggle_fov}")
            elif key == pygame.K_v:
                self.generate_lock_unlock_action()
            elif key == pygame.K_x:
                self.generate_drop_action()
            elif key == pygame.K_LEFT:
                self.camera_control.move = (-1, 0)
            elif key == pygame.K_RIGHT:
                self.camera_control.move = (1, 0)
            elif key == pygame.K_UP:
                self.camera_control.move = (0, -1)
            elif key == pygame.K_DOWN:
                self.camera_control.move = (0, 1)
            elif key == pygame.K_F1:
                self.llm_action_payload = self.text_entry_box.get_text()
                


    def handle_mouse_click(self, button, pos, camera_pos, cell_size):
        self.latest_mouse_click = pos
        print("latest mouse click", self.latest_mouse_click)

        if button == 1:  # Left mouse button
            if self.inventory_widget.rect.collidepoint(pos):
                # Handle clicks on the inventory widget
                print("Handling click on inventory widget")  # Debug print statement
                mouse_pos_in_inventory = (pos[0] - self.inventory_widget.rect.x,
                                        pos[1] - self.inventory_widget.rect.y)
                self.inventory_widget.process_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                                                    button=1,
                                                                    pos=mouse_pos_in_inventory))
                
            else:
                # Handle clicks on the grid map widget
                clicked_node = self.get_node_at_pos(pos, camera_pos, cell_size)
                if clicked_node and self.is_position_visible(clicked_node.position.x, clicked_node.position.y, camera_pos, cell_size):
                    self.active_entities.targeted_node_id = clicked_node.id
                    self.active_entities.targeted_entity_id = self.get_next_entity_at_node(clicked_node).id if self.get_next_entity_at_node(clicked_node) else None
                    self.active_entities.targeted_inventory_entity_id = None
                    player_id = self.active_entities.controlled_entity_id
                    player = GameEntity.get_instance(player_id)
                    target_entity_id = self.active_entities.targeted_entity_id
                    if target_entity_id:
                        target_entity = GameEntity.get_instance(target_entity_id)
                        self.available_actions = self.get_available_actions(player, target_entity)
                        if clicked_node == player.node or clicked_node in player.node.neighbors():
                            if hasattr(target_entity, 'is_pickupable') and target_entity.is_pickupable.value:
                                pickup_action = ActionInstance(source_id=player_id, target_id=target_entity_id, action=Pickup())
                                self.actions_payload.actions.append(pickup_action)
                                print(f"Pickup generated: {pickup_action}")  # Debug print statement
                            elif isinstance(target_entity, Door):
                                if target_entity.open.value:
                                    close_action = ActionInstance(source_id=player_id, target_id=target_entity_id, action=Close())
                                    self.actions_payload.actions.append(close_action)
                                else:
                                    open_action = ActionInstance(source_id=player_id, target_id=target_entity_id, action=Open())
                                    self.actions_payload.actions.append(open_action)
                    else:
                        self.available_actions = []
        elif button == 3:  # Right mouse button
            clicked_node = self.get_node_at_pos(pos, camera_pos, cell_size)
            if clicked_node and self.is_position_visible(clicked_node.position.x, clicked_node.position.y, camera_pos, cell_size):
                self.generate_move_to_target(clicked_node)

    def is_position_visible(self, x: int, y: int, camera_pos, cell_size) -> bool:
        return (camera_pos[0] <= x < camera_pos[0] + self.grid_map_widget_size[0] // cell_size and
                camera_pos[1] <= y < camera_pos[1] + self.grid_map_widget_size[1] // cell_size)

    def handle_mouse_motion(self, pos, camera_pos, cell_size):  
        self.mouse_highlighted_node = self.get_node_at_pos(pos, camera_pos, cell_size)
        
    def get_available_actions(self, source: GameEntity, target: GameEntity) -> List[str]:
        available_actions = []
        for action_class in Action.__subclasses__():
            action = action_class()
            if action.is_applicable(source, target):
                available_actions.append(action.name)
        return available_actions
    
    
    def update_available_actions(self):
        player_id = self.active_entities.controlled_entity_id
        player = GameEntity.get_instance(player_id)
        target_entity_id = self.active_entities.targeted_inventory_entity_id or self.active_entities.targeted_entity_id
        if target_entity_id:
            target_entity = GameEntity.get_instance(target_entity_id)
            self.available_actions = self.get_available_actions(player, target_entity)
            if target_entity in player.inventory:
                self.available_actions.append("Drop")
            else:
                if "Drop" in self.available_actions:
                    self.available_actions.remove("Drop")
        else:
            self.available_actions = []


        
    def get_node_at_pos(self, pos, camera_pos, cell_size) -> Optional[Node]:
        # Convert screen coordinates to grid coordinates
        grid_x = camera_pos[0] + pos[0] // cell_size
        grid_y = camera_pos[1] + pos[1] // cell_size
        # Check if the grid coordinates are within the grid map bounds
        if 0 <= grid_x < self.grid_map.width and 0 <= grid_y < self.grid_map.height:
            return self.grid_map.get_node((grid_x, grid_y))
        return None

    def get_next_entity_at_node(self, node: Node) -> Optional[GameEntity]:
        if node.entities:
            # Sort entities based on their draw order using the sprite mappings
            sorted_entities = sorted(node.entities, key=lambda e: self.get_draw_order(e), reverse=True)
            return sorted_entities[0]
        return None

    def get_draw_order(self, entity: GameEntity) -> int:
        for mapping in self.sprite_mappings:
            if isinstance(entity, mapping.entity_type):
                return mapping.draw_order
        return 0  # Default draw order if no mapping is found
    
    def generate_drop_action(self):
        player_id = self.active_entities.controlled_entity_id
        player = GameEntity.get_instance(player_id)
        target_entity_id = self.active_entities.targeted_inventory_entity_id
        if target_entity_id:
            target_entity = GameEntity.get_instance(target_entity_id)
            if target_entity in player.inventory:
                drop_action = ActionInstance(source_id=player_id, target_id=target_entity_id, action=Drop())
                self.actions_payload.actions.append(drop_action)
            
    def generate_lock_unlock_action(self):
        player_id = self.active_entities.controlled_entity_id
        player = GameEntity.get_instance(player_id)
        target_entity_id = self.active_entities.targeted_entity_id
        if target_entity_id:
            target_entity = GameEntity.get_instance(target_entity_id)
            if isinstance(target_entity, Door):
                if target_entity.is_locked.value:
                    unlock_action = ActionInstance(source_id=player_id, target_id=target_entity_id, action=Unlock())
                    self.actions_payload.actions.append(unlock_action)
                else:
                    lock_action = ActionInstance(source_id=player_id, target_id=target_entity_id, action=Lock())
                    self.actions_payload.actions.append(lock_action)

    def generate_move_step(self, direction):
        # Delegate the move step generation to the ActionPayloadGenerator
        move_payload = ActionPayloadGenerator.generate_move_step(self.active_entities.controlled_entity_id, direction, self.grid_map)
        if move_payload:
            self.actions_payload.actions.extend(move_payload.actions)

    def generate_move_to_target(self, target_node: Node):
        # Delegate the move-to-target generation to the ActionPayloadGenerator
        move_payload = ActionPayloadGenerator.generate_move_to_target(self.active_entities.controlled_entity_id, target_node, self.grid_map)
        if move_payload:
            self.actions_payload.actions.extend(move_payload.actions)

    def reset_camera_control(self):
        self.camera_control.move = (0, 0)
        self.camera_control.recenter = False
        self.camera_control.zoom = 0

    def reset_actions_payload(self):
        self.actions_payload = ActionsPayload(actions=[])

class ActionPayloadGenerator:
    @staticmethod
    def generate_move_step(controlled_entity_id: str, direction: Tuple[int, int], grid_map: GridMap) -> Optional[ActionsPayload]:
        if controlled_entity_id:
            controlled_entity = GameEntity.get_instance(controlled_entity_id)
            current_node = controlled_entity.node
            target_position = (current_node.position.x + direction[0], current_node.position.y + direction[1])
            if 0 <= target_position[0] < grid_map.width and 0 <= target_position[1] < grid_map.height:
                target_node = grid_map.get_node(target_position)
                if target_node:
                    floor_entities = [entity for entity in target_node.entities if entity.name.startswith("Floor")]
                    if floor_entities:
                        target_id = floor_entities[0].id
                        move_action = ActionInstance(source_id=controlled_entity_id, target_id=target_id, action=Move())
                        return ActionsPayload(actions=[move_action])
        return None

    @staticmethod
    def generate_move_to_target(controlled_entity_id: str, target_node: Node, grid_map: GridMap) -> Optional[ActionsPayload]:
        if controlled_entity_id:
            controlled_entity = GameEntity.get_instance(controlled_entity_id)
            start_node = controlled_entity.node
            path = grid_map.get_path(start_node, target_node)
            if path:
                move_actions = ActionPayloadGenerator.generate_move_actions(controlled_entity_id, path)
                return ActionsPayload(actions=move_actions)
        return None

    @staticmethod
    def generate_move_actions(controlled_entity_id: str, path: Path) -> List[ActionInstance]:
        move_actions = []
        for i in range(len(path.nodes) - 1):
            source_node = path.nodes[i]
            target_node = path.nodes[i + 1]
            floor_entities = [entity for entity in target_node.entities if entity.name.startswith("Floor")]
            if floor_entities:
                target_id = floor_entities[0].id
                move_action = ActionInstance(source_id=controlled_entity_id, target_id=target_id, action=Move())
                move_actions.append(move_action)
        return move_actions


---

## main

import pygame
from abstractions.goap.gridmap import GridMap
from abstractions.goap.nodes import GameEntity, Node, Attribute, BlocksMovement, BlocksLight
import os
from abstractions.goap.actions import Goal, Prerequisites
from abstractions.goap.entity import Statement
from abstractions.goap.interactions import Character, Door, Key, Treasure, Floor, Wall, InanimateEntity, IsPickupable, TestItem, Open, Close, Unlock, Lock, Pickup, Drop, Move
from abstractions.goap.game.payloadgen import PayloadGenerator, SpriteMapping
from abstractions.goap.game.renderer import Renderer, GridMapVisual, NodeVisual, EntityVisual, CameraControl
from abstractions.goap.game.input_handler import InputHandler
from pydantic import ValidationError
from abstractions.goap.game.manager import GameManager
from typing import Optional

BASE_PATH = r"C:\Users\Tommaso\Documents\Dev\Abstractions\abstractions\goap"
# BASE_PATH = "/Users/tommasofurlanello/Documents/Dev/Abstractions/abstractions/goap"

def generate_dungeon(grid_map: GridMap, room_width: int, room_height: int):
    room_x = (grid_map.width - room_width) // 2
    room_y = (grid_map.height - room_height) // 2
    for x in range(room_x, room_x + room_width):
        for y in range(room_y, room_y + room_height):
            if x == room_x or x == room_x + room_width - 1 or y == room_y or y == room_y + room_height - 1:
                if (x, y) != (room_x + room_width // 2, room_y):
                    wall = Wall(name=f"Wall_{x}_{y}", blocks_movement=BlocksMovement(value=True), blocks_light=BlocksLight(value=True))
                    grid_map.get_node((x, y)).add_entity(wall)
            else:
                floor = Floor(name=f"Floor_{x}_{y}")
                grid_map.get_node((x, y)).add_entity(floor)
    door_x, door_y = room_x + room_width // 2, room_y
    character_x, character_y = room_x + room_width // 2, room_y - 1
    key_x, key_y = room_x - 1, room_y + room_height // 2    
    treasure_x, treasure_y = room_x + room_width // 2, room_y + room_height - 2
    door = Door(name="Door", is_locked=Attribute(name="is_locked", value=True), required_key=Attribute(name="required_key", value="Golden Key"))
    character = Character(name="Player")
    key = Key(name="Golden Key", key_name=Attribute(name="key_name", value="Golden Key"), is_pickupable=IsPickupable(value=True))
    treasure = Treasure(name="Treasure", monetary_value=Attribute(name="monetary_value", value=1000), is_pickupable=IsPickupable(value=True))
    grid_map.get_node((door_x, door_y)).add_entity(door)
    grid_map.get_node((character_x, character_y)).add_entity(character)
    grid_map.get_node((key_x, key_y)).add_entity(key)
    grid_map.get_node((treasure_x, treasure_y)).add_entity(treasure)
    for x in range(grid_map.width):
        for y in range(grid_map.height):
            if not any(isinstance(entity, Floor) for entity in grid_map.get_node((x, y)).entities):
                floor = Floor(name=f"Floor_{x}_{y}")
                grid_map.get_node((x, y)).add_entity(floor)
    return character, door, key, treasure


def source_target_position_comparison(source: tuple[int,int], target: tuple[int,int]) -> bool:
    """Check if the source entity's position is the same as the target entity's position."""
    if source and target:
        return source == target
    return False

def treasure_in_neighborhood(source: GameEntity, target: Optional[GameEntity] = None) -> bool:
    """Check if the treasure is in the character's neighborhood."""
    if source.node and target and target.node:
        return source.node in target.node.neighbors()
    return False

def key_in_inventory(source: GameEntity, target: Optional[GameEntity] = None) -> bool:
    """Check if the key is in the character's inventory."""
    if target:
        return target in source.inventory
    return False

def is_treasure(source: GameEntity, target: Optional[GameEntity] = None) -> bool:
    """Check if the target entity is a Treasure."""

    
    return isinstance(target, Treasure)

def is_golden_key(source: GameEntity, target: Optional[GameEntity] = None) -> bool:
    """Check if the entity is a Golden Key."""
    return isinstance(target, Key) and target.key_name.value == "Golden Key"

def is_door(entity: GameEntity, target: Optional[GameEntity] = None) -> bool:
    """Check if the entity is a Door."""
    return isinstance(entity, Door)

def main():
    # Initialize Pygame
    pygame.init()
    screen_width, screen_height = 2400, 1400
    screen = pygame.display.set_mode((screen_width, screen_height))
    
    pygame.display.set_caption("Dungeon Experiment")
    
    # Create the grid map and generate the dungeon
    grid_map = GridMap(width=10, height=10)
    grid_map.register_actions([Move, Pickup, Drop, Open, Close, Unlock, Lock])
    room_width, room_height = 6, 6
    character, door, key, treasure = generate_dungeon(grid_map, room_width, room_height)
    
    # Generate the entity type map
    grid_map.generate_entity_type_map()
    
    # Define the sprite mappings
    sprite_mappings = [
        SpriteMapping(entity_type=Character, sprite_path=os.path.join(BASE_PATH, "sprites", "character_agent.png"), ascii_char="@", draw_order=3),
        SpriteMapping(entity_type=Door, sprite_path=os.path.join(BASE_PATH, "sprites", "closed_locked_door.png"), ascii_char="D", draw_order=2, attribute_conditions={"open": False, "is_locked": True}),
        SpriteMapping(entity_type=Door, sprite_path=os.path.join(BASE_PATH, "sprites", "closed_unlocked_door.png"), ascii_char="D", draw_order=2, attribute_conditions={"open": False, "is_locked": False}),
        SpriteMapping(entity_type=Door, sprite_path=os.path.join(BASE_PATH, "sprites", "open_locked_door.png"), ascii_char="D", draw_order=2, attribute_conditions={"open": True, "is_locked": True}),
        SpriteMapping(entity_type=Door, sprite_path=os.path.join(BASE_PATH, "sprites", "open_unlocked_door.png"), ascii_char="D", draw_order=2, attribute_conditions={"open": True, "is_locked": False}),
        SpriteMapping(entity_type=Key, sprite_path=os.path.join(BASE_PATH, "sprites", "lock.png"), ascii_char="K", draw_order=1),
        SpriteMapping(entity_type=Treasure, sprite_path=os.path.join(BASE_PATH, "sprites", "filled_storage.png"), ascii_char="T", draw_order=1),
        SpriteMapping(entity_type=Floor, sprite_path=os.path.join(BASE_PATH, "sprites", "floor.png"), ascii_char=".", draw_order=0),
        SpriteMapping(entity_type=TestItem, sprite_path=os.path.join(BASE_PATH, "sprites", "filled_storage.png"), ascii_char="$", draw_order=1),
        SpriteMapping(entity_type=GameEntity, name_pattern=r"^Wall", sprite_path=os.path.join(BASE_PATH, "sprites", "wall.png"), ascii_char="#", draw_order=1),
    ]
    # add the goals

        # Goal 1: Check if the character's position is the same as the treasure's position
    reach_treasure_goal = Goal(
        name="Reach the treasure",
        source_entity_id=character.id,
        target_entity_id=treasure.id,
        prerequisites=Prerequisites(
            source_statements=[Statement(conditions={"can_act": True})],
            target_statements=[Statement(callables=[is_treasure])],
            source_target_statements=[
                Statement(comparisons={
                    "source_position": ("position", "position", source_target_position_comparison)
                })
            ]
        )
    )

    # Goal 2: Check if the treasure is in the character's neighborhood
    treasure_in_neighborhood_goal = Goal(
        name="Treasure in neighborhood",
        source_entity_id=character.id,
        target_entity_id=treasure.id,
        prerequisites=Prerequisites(
            source_statements=[Statement(conditions={"can_act": True})],
            target_statements=[Statement(callables=[is_treasure])],
            source_target_statements=[
                Statement(callables=[treasure_in_neighborhood])
            ]
        )
    )

    # Goal 3: Check if the key is in the character's inventory
    key_in_inventory_goal = Goal(
        name="Key in inventory",
        source_entity_id=character.id,
        target_entity_id=key.id,
        prerequisites=Prerequisites(
            source_statements=[Statement(conditions={"can_act": True})],
            target_statements=[Statement(callables=[is_golden_key])],
            source_target_statements=[
                Statement(callables=[key_in_inventory])
            ]
        )
    )

    # Goal 4: Check if the door is unlocked
    door_unlocked_goal = Goal(
        name="Door unlocked",
        source_entity_id=door.id,
        prerequisites=Prerequisites(
            source_statements=[
                Statement(callables=[is_door]),
                Statement(conditions={"is_locked": False})
            ],
            target_statements=[],
            source_target_statements=[]
        )
    )
    goals = [reach_treasure_goal, treasure_in_neighborhood_goal, key_in_inventory_goal, door_unlocked_goal]

    # Create the game manager
    game_manager = GameManager(screen, grid_map, sprite_mappings, widget_size=(420, 420), controlled_entity_id=character.id, goals=goals)
    
    # Run the game
    game_manager.run()
    
    # Quit Pygame
    pygame.quit()

if __name__ == "__main__":
    main()

---

## manager

import pygame
import pygame_gui
from typing import List, Tuple, Set, Optional, Union
from abstractions.goap.gridmap import GridMap
from abstractions.goap.shapes import Path, Shadow, RayCast, Radius, Rectangle
from abstractions.goap.nodes import Node, GameEntity
from abstractions.goap.payloads import ActionsResults, ActionResult, ActionsPayload, SummarizedActionPayload
from abstractions.goap.game.renderer import Renderer, GridMapVisual, NodeVisual, EntityVisual
from abstractions.goap.game.input_handler import InputHandler
from abstractions.goap.game.payloadgen import PayloadGenerator, SpriteMapping
from abstractions.goap.interactions import Character
from pydantic import ValidationError
from abstractions.goap.game.gui_widgets import InventoryWidget
from pygame_gui.elements import UIWindow, UITextEntryBox, UITextBox
from abstractions.goap.language_state import ObservationState,ActionState,GoalState, StrActionConverter
from abstractions.goap.actions import Goal

class GameManager:
    def __init__(self, screen: pygame.Surface, grid_map: GridMap, sprite_mappings: List[SpriteMapping],
                 widget_size: Tuple[int, int], controlled_entity_id: str, goals: List[Goal] = [], split_goals:bool=True):
        self.screen = screen
        self.grid_map = grid_map
        self.sprite_mappings = sprite_mappings
        self.widget_size = widget_size
        self.controlled_entity_id = controlled_entity_id
        

        self.renderer = Renderer(self.screen, GridMapVisual(width=grid_map.width, height=grid_map.height, node_visuals={}), self.widget_size)
        self.setup_gui_widgets(screen, sprite_mappings)
        
        self.inventory_widget = InventoryWidget((self.renderer.widget_size[0] + 5, 10), self.ui_manager, sprite_mappings, None)
        self.input_handler = InputHandler(self.grid_map, self.sprite_mappings, self.ui_manager, (self.renderer.widget_size[0], self.renderer.widget_size[1]),self.inventory_widget,self.text_entry_box)
        self.payload_generator = PayloadGenerator(self.sprite_mappings, (self.grid_map.width, self.grid_map.height))
        

        self.bind_controlled_entity(self.controlled_entity_id)
        self.prev_visible_positions: Set[Tuple[int, int]] = set()

        self.obs_state = ObservationState(character_id=self.controlled_entity_id)
        self.action_state = ActionState()
        self.split_goals = split_goals
        if not split_goals:
            self.goal_state = GoalState(character_id=self.controlled_entity_id,goals=goals)
        else:
            goal_states = [GoalState(character_id=self.controlled_entity_id,goals=[goal]) for goal in goals]
            self.goal_states = goal_states
        self.setup_goal_widgets(screen)
        self.str_action_converter = StrActionConverter(grid_map=self.grid_map)
        

        
    def setup_gui_widgets(self, screen: pygame.Surface, sprite_mappings: List[SpriteMapping]):
        # Initialize the UI manager
        self.ui_manager = pygame_gui.UIManager((screen.get_width(), screen.get_height()))
        # Initialize the inventory widget
        # Initialize the notepad window
        self.notepad_window = UIWindow(pygame.Rect(805, 160, 300, 400), window_display_title="Adventure Notepad")
        self.text_entry_box = UITextEntryBox(
        relative_rect=pygame.Rect((0, 0),  self.notepad_window.get_container().get_size()),
        initial_text="",
        container= self.notepad_window)
        #Initialize the texstate Window
        # the textstate window can be uptad by calling textstate_box.set_text("text")
        self.actionlog_window = UIWindow(pygame.Rect(self.widget_size[0], 20, 600, 790), window_display_title="Action Logger")
        self.actionlog_box = UITextBox(
        relative_rect=pygame.Rect((0, 0), self.actionlog_window.get_container().get_size()),
        html_text="",
        container=self.actionlog_window)
        self.action_logs = []
        #Initialize the ObsLogger Window
        self.observationlog_window = UIWindow(pygame.Rect(self.widget_size[0], 20, 600, screen.get_height()), window_display_title="Observation Logger")
        self.observationlog_box = UITextBox(
        relative_rect=pygame.Rect((0, 0), self.observationlog_window.get_container().get_size()),
        html_text="",
        container=self.observationlog_window)
        self.observation_logs = []
        #initalize the goalLogger window
        # Initalize the background
        self.vertical_background = pygame.Surface((screen.get_width()-self.widget_size[0], screen.get_height()))
        self.horizontal_background = pygame.Surface((screen.get_width(), screen.get_height()))
    
    def setup_goal_widgets(self,screen: pygame.Surface):
        if not self.split_goals:
            self.goallog_window = UIWindow(pygame.Rect(self.widget_size[0], 20, 600, 500), window_display_title="Goal Logger")
            self.goallog_box = UITextBox(
            relative_rect=pygame.Rect((0, 0), self.goallog_window.get_container().get_size()),
            html_text="",
            container=self.goallog_window)
            self.goal_logs = []
        else:
            self.goallog_windows = [UIWindow(pygame.Rect(self.widget_size[0], 20, 600, 500), window_display_title=f"Goal Logger {i}") for i in range(len(self.goal_states))]
            self.goallog_boxes = [UITextBox(
            relative_rect=pygame.Rect((0, 0), self.goallog_windows[i].get_container().get_size()),
            html_text="",
            container=self.goallog_windows[i]) for i in range(len(self.goal_states))]
            self.goal_logs = {i:[] for i in range(len(self.goal_states))}


       
    def bind_controlled_entity(self, controlled_entity_id: str):
        self.controlled_entity_id = controlled_entity_id
        self.input_handler.active_entities.controlled_entity_id = controlled_entity_id
    
    def get_controlled_entity(self,inventory:bool = False):
        if inventory:
            return Character.get_instance(self.input_handler.active_entities.controlled_entity_id).inventory
        return GameEntity.get_instance(self.input_handler.active_entities.controlled_entity_id)
    
    def get_target_node(self):
        return  Node.get_instance(self.input_handler.active_entities.targeted_node_id) if self.input_handler.active_entities.targeted_node_id else None

    def controlled_entity_preprocess(self, clock: pygame.time.Clock, target_node:  Optional[Node] = None):
        controlled_entity = self.get_controlled_entity()
        self.renderer.grid_map_widget.center_camera_on_player(controlled_entity.position.value)
        inventory = self.get_controlled_entity(inventory=True)
        self.input_handler.inventory_widget.update_inventory(inventory)
        time_delta = clock.tick(60) / 1000.0
        self.ui_manager.update(time_delta)
        self.ui_manager.draw_ui(self.screen)
        radius, shadow, raycast, path = self.compute_shapes(controlled_entity.node, target_node)
        return controlled_entity, inventory, radius, shadow, raycast, path
    
    def compute_shapes(self, source_node: Node, target_node: Optional[Node] = None):
        radius = self.grid_map.get_radius(source_node, max_radius=10)
        shadow = self.grid_map.get_shadow(source_node, max_radius=10)

        try:
            raycast = self.grid_map.get_raycast(source_node, target_node) if target_node else None
        except ValidationError as e:
            print(f"Error: {e}")
            raycast = None
        path = self.grid_map.get_path(source_node, target_node) if target_node else None
        return radius, shadow, raycast, path

    def update_action_logs(self, action_results: ActionsResults):
        for result in action_results.results:
            log_entry = self.action_state.generate(result)
            self.action_logs.append(log_entry)
        if log_entry:
            self.actionlog_box.set_text(log_entry)
    
    def update_observation_logs(self, observation: Union[Shadow,Rectangle,Radius]):
        log_entry = self.obs_state.generate(observation)
        self.observation_logs.append(log_entry)
        self.observationlog_box.set_text(self.observation_logs[-1])
        
    def update_goal_logs(self, observation: Union[Shadow,Rectangle,Radius]):
        if not self.split_goals:
            log_entry = self.goal_state.generate(observation)
            self.goal_logs.append(log_entry)
            self.goallog_box.set_text(self.goal_logs[-1])
        else:
            for i,goal_state in enumerate(self.goal_states):
                log_entry = goal_state.generate(observation)
                self.goal_logs[i].append(log_entry)
                self.goallog_boxes[i].set_text(self.goal_logs[i][-1])
            
    def handle_action_payload_submission(self, action_payload_json:str):
        try:
            # summarized_payload = SummarizedActionPayload.model_validate_json(action_payload_json)
            actions_payload = self.str_action_converter.convert_action_string(action_payload_json,self.controlled_entity_id)
            if isinstance(actions_payload, ActionsPayload):
                self.input_handler.actions_payload.actions.extend(actions_payload.actions)
            else:
                print(f"Action Conversion Error: {actions_payload}")
        except ValidationError as e:
            print(f"Invalid action payload: {e}")
            
    def run(self):
        self.screen.blit(self.vertical_background, (self.widget_size[0], 0))
        self.screen.blit(self.horizontal_background, (0, self.widget_size[1]))
        running = True
        clock = pygame.time.Clock()
        target_node = self.get_target_node()
        controlled_entity, inventory, radius, shadow, raycast, path = self.controlled_entity_preprocess(clock, target_node)
        self.update_observation_logs(shadow)
        self.update_goal_logs(shadow)

        while running:
            # Handle events
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEMOTION:
                    self.input_handler.handle_mouse_motion(event.pos, self.renderer.grid_map_widget.camera_pos, self.renderer.grid_map_widget.cell_size)

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.input_handler.handle_mouse_click(event.button, event.pos, self.renderer.grid_map_widget.camera_pos, self.renderer.grid_map_widget.cell_size)
                else:
                    self.input_handler.handle_input(event)

                if not event.type == pygame.MOUSEMOTION:
                    controlled_entity = self.get_controlled_entity()
                    radius, shadow, raycast, path = self.compute_shapes(controlled_entity.node, target_node)
                self.ui_manager.process_events(event)
                if self.input_handler.llm_action_payload is not None:
                    self.handle_action_payload_submission(self.input_handler.llm_action_payload)
                    self.input_handler.llm_action_payload = None
                

            # Update the camera control based on input
            self.renderer.handle_camera_control(self.input_handler.camera_control)

            # Get the controlled entity and target node
            controlled_entity = self.get_controlled_entity()
            target_node = self.get_target_node()

            time_delta = clock.tick(60) / 1000.0

            # Get the nodes affected by the action payload
            affected_nodes = self.get_affected_nodes()

            # Apply the action payload to the grid map
            actions_results = self.grid_map.apply_actions_payload(self.input_handler.actions_payload)
            if len(actions_results.results) > 0:
                self.update_action_logs(actions_results)

            # Check if there are any successful actions
            successful_actions = any(result.success for result in actions_results.results)
            #get the action name, source and entiy as a formatted string that we will add to the textstate_box
            # we will use the action name to get the action description from the action class, then combine it with the source name and target name
            # we will also add the position of the source and target node. 
            if successful_actions:
                self.update_observation_logs(shadow)
                self.update_goal_logs(shadow)
                

            
            # Recalculate the available actions after applying the action payload
            self.update_available_actions()

            # Get the nodes affected by the action results
            affected_nodes.update(self.get_affected_nodes_from_results(actions_results))

            # Generate the payload based on the camera position and FOV
            camera_pos = self.renderer.grid_map_widget.camera_pos
            fov = shadow if self.renderer.grid_map_widget.show_fov else None

            if fov:
                visible_nodes = [node for node in fov.nodes]
            else:
                rect_top_left = camera_pos
                rect_width = self.renderer.grid_map_widget.rect.width // self.renderer.grid_map_widget.cell_size
                rect_height = self.renderer.grid_map_widget.rect.height // self.renderer.grid_map_widget.cell_size
                rect = Rectangle(top_left=rect_top_left, width=rect_width, height=rect_height, nodes=[])
                visible_nodes = self.grid_map.get_nodes_in_rect(rect)

            visible_positions = {node.position.value for node in visible_nodes}

            # Update the grid map visual with the new payload
            self.update_grid_map_visual(visible_positions, affected_nodes)

            # Remove node visuals that are no longer visible
            self.remove_invisible_node_visuals(visible_positions)

            # Update the renderer with the necessary data
            player_position = controlled_entity.node.position.value
            self.renderer.update(player_position)

            # Render the game using dirty rect rendering
            dirty_rects = self.renderer.render(path=path, shadow=shadow, raycast=raycast, radius=radius, fog_of_war=shadow)
            pygame.display.update(dirty_rects)

            # Draw the UI elements
            if successful_actions:
                inventory = Character.get_instance(self.controlled_entity_id).inventory
                self.input_handler.inventory_widget.update_inventory(inventory)
                
                
                # # self.ui_manager.draw_ui(self.screen)

            # Reset the camera control and actions payload
            self.input_handler.reset_camera_control()
            self.input_handler.reset_actions_payload()

            # Limit the frame rate to 144 FPS
            clock.tick(144)

            # Display FPS and other text
            
            self.ui_manager.update(time_delta)
            self.screen.blit(self.vertical_background, (self.widget_size[0], 0))
            self.screen.blit(self.horizontal_background, (0, self.widget_size[1]))
            self.display_text(clock)
            self.ui_manager.draw_ui(self.screen)
            pygame.display.update()

            pygame.display.flip()
           
    def get_affected_nodes(self) -> Set[Node]:
        affected_nodes = set()
        for action_instance in self.input_handler.actions_payload.actions:
            source_entity = GameEntity.get_instance(action_instance.source_id)
            target_entity = GameEntity.get_instance(action_instance.target_id)
            affected_nodes.add(source_entity.node)
            affected_nodes.add(target_entity.node)
        return affected_nodes
   
    def update_available_actions(self):
        player_id = self.input_handler.active_entities.controlled_entity_id
        player = GameEntity.get_instance(player_id)
        target_entity_id = self.input_handler.active_entities.targeted_entity_id
        if target_entity_id:
            target_entity = GameEntity.get_instance(target_entity_id)
            self.input_handler.available_actions = self.input_handler.get_available_actions(player, target_entity)
        else:
            self.input_handler.available_actions = []
   
    def get_affected_nodes_from_results(self, actions_results) -> Set[Node]:
        affected_nodes = set()
        if actions_results.results:
            for result in actions_results.results:
                if result.success:
                    source_entity = GameEntity.get_instance(result.action_instance.source_id)
                    target_entity = GameEntity.get_instance(result.action_instance.target_id)
                    affected_nodes.add(source_entity.node)
                    affected_nodes.add(target_entity.node)
        return affected_nodes
   
    def update_grid_map_visual(self, visible_positions: Set[Tuple[int, int]], affected_nodes: Set[Node]):
        new_visible_positions = visible_positions - self.prev_visible_positions
        affected_positions = {node.position.value for node in affected_nodes if node is not None}
        
        positions_to_update = new_visible_positions | affected_positions
        
        for pos in positions_to_update:
            node = self.grid_map.get_node(pos)
            entity_data_list = self.payload_generator.generate_payload_for_node(node)
            
            if pos in self.renderer.grid_map_widget.grid_map_visual.node_visuals:
                node_visual = self.renderer.grid_map_widget.grid_map_visual.node_visuals[pos]
                node_visual.entity_visuals = [EntityVisual(**entity_data) for entity_data in entity_data_list]
            else:
                node_visual = NodeVisual(entity_visuals=[EntityVisual(**entity_data) for entity_data in entity_data_list])
                self.renderer.grid_map_widget.grid_map_visual.node_visuals[pos] = node_visual
        
        self.prev_visible_positions = visible_positions
   
    def remove_invisible_node_visuals(self, visible_positions: Set[Tuple[int, int]]):
        for pos in self.prev_visible_positions - visible_positions:
            if pos in self.renderer.grid_map_widget.grid_map_visual.node_visuals:
                del self.renderer.grid_map_widget.grid_map_visual.node_visuals[pos]
   
    def display_text(self, clock):
        # Display FPS
        fps = clock.get_fps()
        fps_text = self.renderer.grid_map_widget.font.render(f"FPS: {fps:.2f}", True, (255, 255, 255))
        self.renderer.screen.blit(fps_text, (1000, 10))
       
        # Display active node and entity
        active_node_pos = self.input_handler.active_entities.targeted_node_id
        if active_node_pos:
            active_node_pos = Node.get_instance(active_node_pos).position.value
        active_node_text = self.renderer.grid_map_widget.font.render(f"Active Node: {active_node_pos}", True, (255, 255, 255))
        self.renderer.screen.blit(active_node_text, (1000, 30))
       
        active_entity_id = self.input_handler.active_entities.targeted_entity_id
        if active_entity_id:
            active_entity_name = GameEntity.get_instance(active_entity_id).name
            active_entity_text = self.renderer.grid_map_widget.font.render(f"Active Entity: {active_entity_name}", True, (255, 255, 255))
            self.renderer.screen.blit(active_entity_text, (1000, 50))
       
        # Display inventory
        controlled_entity = GameEntity.get_instance(self.controlled_entity_id)
        if isinstance(controlled_entity, Character):
            inventory_names = [item.name for item in controlled_entity.inventory]
            inventory_text = self.renderer.grid_map_widget.font.render(f"Inventory: {inventory_names}", True, (255, 255, 255))
            self.renderer.screen.blit(inventory_text, (1000, 70))
       
        # Display available actions
        available_actions_text = self.renderer.grid_map_widget.font.render(f"Available Actions: {', '.join(self.input_handler.available_actions)}", True, (255, 255, 255))
        self.renderer.screen.blit(available_actions_text, (1000, 90))

        #display targeted_inventory entity
        targeted_inventory_entity_id = self.input_handler.active_entities.targeted_inventory_entity_id
        if targeted_inventory_entity_id:
            targeted_inventory_entity_name = GameEntity.get_instance(targeted_inventory_entity_id).name
            targeted_inventory_entity_text = self.renderer.grid_map_widget.font.render(f"Targeted Inventory Entity: {targeted_inventory_entity_name}", True, (255, 255, 255))
        else:
            targeted_inventory_entity_text = self.renderer.grid_map_widget.font.render(f"Targeted Inventory Entity: None", True, (255, 255, 255))
        self.renderer.screen.blit(targeted_inventory_entity_text, (1000, 110))

---

## payloadgen

from functools import lru_cache
from typing import Dict, Type, Callable, Any, List, Tuple, Optional
from pydantic import BaseModel
import re
from abstractions.goap.nodes import GameEntity, Node
from abstractions.goap.shapes import Shadow

class SpriteMapping(BaseModel):
    entity_type: Type[GameEntity]
    name_pattern: Optional[str] = None
    sprite_path: str
    ascii_char: str
    draw_order: int
    attribute_conditions: Optional[Dict[str, Any]] = None



class PayloadGenerator:
    def __init__(self, sprite_mappings: List[SpriteMapping], grid_size: Tuple[int, int]):
        self.sprite_mappings = sprite_mappings
        self.grid_size = grid_size
        self.cache_size = grid_size[0] * grid_size[1]
        self.payload_cache: Dict[int, Dict[str, Any]] = {}

    @lru_cache(maxsize=None)
    def get_sprite_mapping(self, entity: GameEntity) -> SpriteMapping:
        for mapping in self.sprite_mappings:
            if isinstance(entity, mapping.entity_type):
                if mapping.name_pattern is None or re.match(mapping.name_pattern, entity.name):
                    if mapping.attribute_conditions is None:
                        return mapping
                    else:
                        if all(hasattr(entity, attr_name) and getattr(entity, attr_name).value == value for attr_name, value in mapping.attribute_conditions.items()):
                            return mapping
        # If no specific mapping is found, return the first matching mapping without attribute conditions
        for mapping in self.sprite_mappings:
            if isinstance(entity, mapping.entity_type):
                if mapping.name_pattern is None or re.match(mapping.name_pattern, entity.name):
                    return mapping
        raise ValueError(f"No sprite mapping found for entity: {entity}")

    def generate_payload_for_node(self, node: Node) -> List[Dict[str, Any]]:
        entity_visuals = []
        if node.entities:
            # Set the hash resolution of the entities to "attributes"
            for entity in node.entities:
                entity.set_hash_resolution("attributes")
            sorted_entities = sorted(node.entities, key=lambda e: self.get_sprite_mapping(e).draw_order)
            for entity in sorted_entities:
                sprite_mapping = self.get_sprite_mapping(entity)
                entity_visual = {
                    "sprite_path": sprite_mapping.sprite_path,
                    "ascii_char": sprite_mapping.ascii_char,
                    "draw_order": sprite_mapping.draw_order
                }
                entity_visuals.append(entity_visual)
            # Reset the hash resolution of the entities to the default value
            for entity in node.entities:
                entity.reset_hash_resolution()
        return entity_visuals

    def generate_payload(self, nodes: List[Node], camera_pos: Tuple[int, int], fov: Optional[Shadow] = None) -> Dict[Tuple[int, int], List[Dict[str, Any]]]:
        payload = {}
        start_x, start_y = camera_pos
        end_x, end_y = start_x + self.grid_size[0], start_y + self.grid_size[1]
        for node in nodes:
            position = node.position.value
            if fov and position not in [node.position.value for node in fov.nodes]:
                continue  # Skip nodes outside the FOV
            if start_x <= position[0] < end_x and start_y <= position[1] < end_y:
                if position in self.payload_cache and self.is_node_unchanged(node):
                    payload[position] = self.payload_cache[position]
                else:
                    entity_visuals = self.generate_payload_for_node(node)
                    payload[position] = entity_visuals
                    self.payload_cache[position] = entity_visuals
        return payload

    @lru_cache(maxsize=None)
    def is_node_unchanged(self, node: Node) -> bool:
        position = node.position.value
        if position not in self.payload_cache:
            return False
        cached_entity_visuals = self.payload_cache[position]
        current_entity_visuals = self.generate_payload_for_node(node)
        return cached_entity_visuals == current_entity_visuals

---

## renderer

import pygame
from pygame.sprite import Group, RenderUpdates
from typing import Dict, List, Type, Tuple, Optional
from pydantic import BaseModel
from abstractions.goap.nodes import Node
from abstractions.goap.shapes import Path, Shadow, RayCast, Radius

class CameraControl(BaseModel):
    move: Tuple[int, int] = (0, 0)
    zoom: int = 0
    recenter: bool = False
    toggle_path: bool = False
    toggle_shadow: bool = False
    toggle_raycast: bool = False
    toggle_radius: bool = False
    toggle_fov: bool = True
    toggle_ascii: bool = False

class EntityVisual(BaseModel):
    sprite_path: str
    ascii_char: str
    draw_order: int

class NodeVisual(BaseModel):
    entity_visuals: List[EntityVisual]

class GridMapVisual(BaseModel):
    width: int
    height: int
    node_visuals: Dict[Tuple[int, int], NodeVisual]

class Widget(pygame.sprite.Sprite):
    def __init__(self, pos: Tuple[int, int], size: Tuple[int, int]):
        super().__init__()
        self.image = pygame.Surface(size)
        self.rect = self.image.get_rect(topleft=pos)

    def update(self, camera_control: CameraControl):
        pass

    def draw(self, surface: pygame.Surface):
        surface.blit(self.image, self.rect)

class GridMapWidget(Widget):
    def __init__(self, pos: Tuple[int, int], size: Tuple[int, int], grid_map_visual: GridMapVisual):
        super().__init__(pos, size)
        self.grid_map_visual = grid_map_visual
        self.cell_size = 32
        self.camera_pos = [0, 0]  # Camera position in grid coordinates
        self.show_path = False
        self.show_shadow = False
        self.show_raycast = False
        self.show_radius = False
        self.show_fov = False
        self.sprite_cache: Dict[str, pygame.Surface] = {}
        self.font = pygame.font.Font(None, self.cell_size)
    

    def grid_to_screen(self, grid_x: int, grid_y: int) -> Tuple[int, int]:
        screen_x = (grid_x - self.camera_pos[0]) * self.cell_size
        screen_y = (grid_y - self.camera_pos[1]) * self.cell_size
        return screen_x, screen_y

    def update(self, camera_control: CameraControl, player_position: Tuple[int, int]):
        # Update camera position based on camera control
        self.camera_pos[0] += camera_control.move[0]
        self.camera_pos[1] += camera_control.move[1]
        self.camera_pos[0] = max(0, min(self.grid_map_visual.width - self.rect.width // self.cell_size, self.camera_pos[0]))
        self.camera_pos[1] = max(0, min(self.grid_map_visual.height - self.rect.height // self.cell_size, self.camera_pos[1]))

        # Update cell size based on camera control
        if camera_control.zoom != 0:
            self.cell_size = max(16, min(64, self.cell_size + camera_control.zoom * 8))
            self.font = pygame.font.Font(None, self.cell_size)

        # Recenter camera on player if requested
        if camera_control.recenter:
            self.center_camera_on_player(player_position)
            camera_control.recenter = False  # Reset the recenter flag

        # Update effect visibility based on camera control
        self.show_path = camera_control.toggle_path
        self.show_shadow = camera_control.toggle_shadow
        self.show_raycast = camera_control.toggle_raycast
        self.show_radius = camera_control.toggle_radius
        self.show_fov = camera_control.toggle_fov
        self.ascii_mode = camera_control.toggle_ascii

    def draw_visible_nodes(self, fog_of_war: Optional[Shadow] = None):
        if self.show_fov and fog_of_war:
            # Draw only the nodes within the FOV
            for node in fog_of_war.nodes:
                position = node.position.value
                if position in self.grid_map_visual.node_visuals:
                    self.draw_node(position, self.grid_map_visual.node_visuals[position])
        else:
            # Draw nodes within the visible range
            start_x = max(0, self.camera_pos[0])
            start_y = max(0, self.camera_pos[1])
            end_x = min(self.grid_map_visual.width, start_x + self.rect.width // self.cell_size)
            end_y = min(self.grid_map_visual.height, start_y + self.rect.height // self.cell_size)
            for x in range(start_x, end_x):
                for y in range(start_y, end_y):
                    position = (x, y)
                    if position in self.grid_map_visual.node_visuals:
                        self.draw_node(position, self.grid_map_visual.node_visuals[position])

    def draw_shape_effect(self, path: Optional[Path] = None, shadow: Optional[Shadow] = None,
                          raycast: Optional[RayCast] = None, radius: Optional[Radius] = None,
                          fog_of_war: Optional[Shadow] = None):
        # Draw effects (in the following order: shadow, radius, raycast, path)
        if self.show_shadow and shadow:
            self.draw_effect(self.image, shadow.nodes, (255, 255, 0))
        if self.show_radius and radius:
            self.draw_effect(self.image, radius.nodes, (0, 0, 255))
        if self.show_raycast and raycast:
            self.draw_effect(self.image, raycast.nodes, (255, 0, 0))
        if self.show_path and path:
            self.draw_effect(self.image, path.nodes, (0, 255, 0))

    def draw_shape_effect(self,path: Optional[Path] = None, shadow: Optional[Shadow] = None,
             raycast: Optional[RayCast] = None, radius: Optional[Radius] = None, fog_of_war: Optional[Shadow] = None):
        # Draw effects (in the following order: shadow, radius, raycast, path)
        if self.show_shadow and shadow:
            self.draw_effect(self.image, shadow.nodes, (255, 255, 0))
        if self.show_radius and radius:
            self.draw_effect(self.image, radius.nodes, (0, 0, 255))
        if self.show_raycast and raycast:
            self.draw_effect(self.image, raycast.nodes, (255, 0, 0))
        if self.show_path and path:
            self.draw_effect(self.image, path.nodes, (0, 255, 0))


    def draw(self, surface: pygame.Surface, path: Optional[Path] = None, shadow: Optional[Shadow] = None,
             raycast: Optional[RayCast] = None, radius: Optional[Radius] = None, fog_of_war: Optional[Shadow] = None):
        # Clear the widget surface
        self.image.fill((0, 0, 0))

        self.draw_visible_nodes(fog_of_war)

        self.draw_shape_effect(path, shadow, raycast, radius, fog_of_war)

        # Blit the widget surface onto the main surface
        surface.blit(self.image, self.rect)

    def draw_node(self, position: Tuple[int, int], node_visual: NodeVisual):
        screen_x, screen_y = self.grid_to_screen(*position)
        if self.ascii_mode:
            # Draw the entity with the highest draw order in ASCII mode
            sorted_entity_visuals = sorted(node_visual.entity_visuals, key=lambda ev: ev.draw_order, reverse=True)
            ascii_char = sorted_entity_visuals[0].ascii_char
            ascii_surface = self.font.render(ascii_char, True, (255, 255, 255))
            ascii_rect = ascii_surface.get_rect(center=(screen_x + self.cell_size // 2, screen_y + self.cell_size // 2))
            self.image.blit(ascii_surface, ascii_rect)
        else:
            # Draw all entities in sprite mode (in draw order)
            sorted_entity_visuals = sorted(node_visual.entity_visuals, key=lambda ev: ev.draw_order)
            for entity_visual in sorted_entity_visuals:
                sprite_surface = self.load_sprite(entity_visual.sprite_path)
                scaled_sprite_surface = pygame.transform.scale(sprite_surface, (self.cell_size, self.cell_size))
                self.image.blit(scaled_sprite_surface, (screen_x, screen_y))

    def draw_effect(self, surface: pygame.Surface, nodes: List[Node], color: Tuple[int, int, int]):
        for node in nodes:
            x, y = node.position.value
            if self.is_position_visible(x, y):
                screen_x, screen_y = self.grid_to_screen(x, y)
                pygame.draw.rect(surface, color, (screen_x, screen_y, self.cell_size, self.cell_size), 2)

    def is_position_visible(self, x: int, y: int) -> bool:
        return (self.camera_pos[0] <= x < self.camera_pos[0] + self.rect.width // self.cell_size and
                self.camera_pos[1] <= y < self.camera_pos[1] + self.rect.height // self.cell_size)

    def load_sprite(self, sprite_path: str) -> pygame.Surface:
        if sprite_path not in self.sprite_cache:
            sprite_surface = pygame.image.load(sprite_path).convert_alpha()
            self.sprite_cache[sprite_path] = sprite_surface
        return self.sprite_cache[sprite_path]

    def center_camera_on_player(self, player_position: Tuple[int, int]):
        self.camera_pos[0] = player_position[0] - self.rect.width // (2 * self.cell_size)
        self.camera_pos[1] = player_position[1] - self.rect.height // (2 * self.cell_size)
        self.camera_pos[0] = max(0, min(self.grid_map_visual.width - self.rect.width // self.cell_size, self.camera_pos[0]))
        self.camera_pos[1] = max(0, min(self.grid_map_visual.height - self.rect.height // self.cell_size, self.camera_pos[1]))


class Renderer:
    def __init__(self, screen: pygame.Surface, grid_map_visual: GridMapVisual, widget_size: Tuple[int, int]):
        self.screen = screen
        self.widget_size = widget_size
        self.grid_map_widget = GridMapWidget((0, 0), widget_size, grid_map_visual)
        self.widgets: Dict[str, Widget] = {
            "grid_map": self.grid_map_widget
        }
        self.camera_control = CameraControl()

    def update(self, player_position: Tuple[int, int] = (0, 0)):
        self.grid_map_widget.update(self.camera_control, player_position)

    def render(self, path: Optional[Path] = None, shadow: Optional[Shadow] = None,
               raycast: Optional[RayCast] = None, radius: Optional[Radius] = None,
               fog_of_war: Optional[Shadow] = None):
        # Clear the area occupied by each widget
        for widget in self.widgets.values():
            self.screen.fill((0, 0, 0), widget.rect)
        # Draw the grid map widget
        self.grid_map_widget.draw(self.screen, path, shadow, raycast, radius, fog_of_war)
        # Draw other widgets
        for widget in self.widgets.values():
            if widget != self.grid_map_widget:
                widget.draw(self.screen)
        pygame.display.flip()

    def handle_camera_control(self, camera_control: CameraControl):
        self.camera_control = camera_control

    def update_grid_map_visual(self, grid_map_visual: GridMapVisual):
        self.grid_map_widget.grid_map_visual = grid_map_visual

---

## goals



---

## gridmap

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

---

## interactions

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

class Move(Action):
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


class Pickup(Action):
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

class Drop(Action):
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



class Open(Action):
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
class Close(Action):
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

class Unlock(Action):
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

class Lock(Action):
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

---

## language state

from typing import Optional, Tuple, List, Dict, Any, Union
from abstractions.goap.entity import Entity, Statement, Attribute
from abstractions.goap.shapes import Shadow, Path, Radius,Rectangle, RayCast, BlockedRaycast
from abstractions.goap.gridmap import GridMap
from abstractions.goap.nodes import Node, GameEntity, BlocksMovement, BlocksLight
from abstractions.goap.spatial import WalkableGraph
from abstractions.goap.interactions import Character, Door, Key, Treasure, Floor, Wall, InanimateEntity, IsPickupable, TestItem, Open, Close, Unlock, Lock, Pickup, Drop, Move
from abstractions.goap.payloads import ActionsPayload, ActionInstance, ActionResult
from pydantic import BaseModel
from abstractions.goap.actions import Prerequisites, Consequences, Goal

class GoalState:
    def __init__(self, character_id: str, goals: Optional[List[Goal]] = []):
        self.character_id = character_id
        self.goals = goals

    def add_goal(self, goal: Goal):
        self.goals.append(goal)

    def remove_goal(self, goal: Goal):
        self.goals.remove(goal)

    def generate(self, shape: Union[Rectangle, Shadow, Radius]) -> str:
        goal_message = "# Agent Goals\n"
        character = GameEntity.get_instance(self.character_id)

        for goal in self.goals:
            goal_message += f"## Goal: {goal.name}\n"
            source_entity = GameEntity.get_instance(goal.source_entity_id)
            target_entity = GameEntity.get_instance(goal.target_entity_id) if goal.target_entity_id else None

            if (source_entity and (source_entity.id != character.id or source_entity not in character.inventory)) or \
            (target_entity and (target_entity.id != character.id or target_entity not in character.inventory)):
                goal_message += self.generate_spatial_info(character, source_entity, target_entity, shape)

            goal_message += self.generate_prerequisites_info(goal.prerequisites, source_entity, target_entity)
            goal_message += "\n"

        return goal_message.strip()

    def generate_spatial_info(self, character: GameEntity, source_entity: GameEntity, target_entity: Optional[GameEntity], shape: Union[Rectangle, Shadow, Radius]) -> str:
        spatial_info = "### Spatial Information:\n"
        character_node = character.node
        source_node = source_entity.node
        target_node = target_entity.node if target_entity else None

        if target_node and character_node != target_node:
            distance = self.calculate_distance(character_node, target_node)
            spatial_info += f"- Distance from Character to {target_entity.__class__.__name__}: {distance}\n"
            if distance == 1:
                direction = self.get_direction(character_node, target_node)
                spatial_info += f"- {target_entity.__class__.__name__} is in the {direction} direction\n"
            else:
                if target_node.blocks_movement.value:
                    neighboring_nodes = [node for node in target_node.neighbors() if not node.blocks_movement.value]
                    if neighboring_nodes:
                        shortest_path_node = min(neighboring_nodes, key=lambda node: len(self.find_path(character_node, node)))
                        path = self.find_path(character_node, shortest_path_node)
                        spatial_info += f"- Path from Character to {target_entity.__class__.__name__}'s neighboring node: {self.format_path(path)}\n"
                        spatial_info += f"- {target_entity.__class__.__name__} is blocked by: {', '.join(entity.__class__.__name__ for entity in target_node.entities if entity.blocks_movement.value)}\n"
                    else:
                        spatial_info += f"- No path found to {target_entity.__class__.__name__} or its neighboring nodes\n"
                else:
                    path = self.find_path(character_node, target_node)
                    spatial_info += f"- Path from Character to {target_entity.__class__.__name__}: {self.format_path(path)}\n"
            raycast = self.calculate_ray(character_node, target_node, shape)
            spatial_info += f"- {raycast}\n"
        elif source_node and character_node != source_node:
            distance = self.calculate_distance(character_node, source_node)
            spatial_info += f"- Distance from Character to {source_entity.__class__.__name__}: {distance}\n"
            if distance == 1:
                direction = self.get_direction(character_node, source_node)
                spatial_info += f"- {source_entity.__class__.__name__} is in the {direction} direction\n"
            else:
                path = self.find_path(character_node, source_node)
                spatial_info += f"- Path from Character to {source_entity.__class__.__name__}: {self.format_path(path)}\n"
            raycast = self.calculate_ray(character_node, source_node, shape)
            spatial_info += f"- {raycast}\n"

        return spatial_info
    
    def get_direction(self, source_node: Node, target_node: Node) -> str:
        dx = target_node.position.x - source_node.position.x
        dy = target_node.position.y - source_node.position.y
        if dx == 0 and dy == -1:
            return "North"
        elif dx == 1 and dy == -1:
            return "NorthEast"
        elif dx == 1 and dy == 0:
            return "East"
        elif dx == 1 and dy == 1:
            return "SouthEast"
        elif dx == 0 and dy == 1:
            return "South"
        elif dx == -1 and dy == 1:
            return "SouthWest"
        elif dx == -1 and dy == 0:
            return "West"
        elif dx == -1 and dy == -1:
            return "NorthWest"
        else:
            raise ValueError("Invalid direction")

    def is_observable(self, node: Node, shape: Union[Rectangle, Shadow, Radius]) -> bool:
        if isinstance(shape, Rectangle):
            return node.position.value in [n.position.value for n in shape.nodes]
        elif isinstance(shape, (Shadow, Radius)):
            return node in shape.nodes
        return False

    def generate_prerequisites_info(self, prerequisites: Prerequisites, source: GameEntity, target: Optional[GameEntity]) -> str:
        info = ""
        for statement_type in ["source_statements", "target_statements", "source_target_statements"]:
            statements = getattr(prerequisites, statement_type)
            if statements:
                info += f"### {statement_type.capitalize().replace('_', ' ')}:\n"
                for statement in statements:
                    if statement.conditions:
                        info += "- Conditions:\n"
                        for attr_name, desired_value in statement.conditions.items():
                            actual_value = getattr(source, attr_name, None) if statement_type == "source_statements" else getattr(target, attr_name, None)
                            is_satisfied = statement.validate_condition(source) if statement_type == "source_statements" else statement.validate_condition(target)
                            info += f"  - {attr_name}: {'Satisfied' if is_satisfied else 'Not Satisfied'} (Desired: {desired_value}, Actual: {actual_value.value if isinstance(actual_value, Attribute) else actual_value})\n"
                    if statement.comparisons:
                        info += "- Comparisons:\n"
                        for comparison_name, (source_attr, target_attr, comparison_func) in statement.comparisons.items():
                            source_value = getattr(source, source_attr, None)
                            target_value = getattr(target, target_attr, None)
                            is_satisfied = statement.validate_comparisons(source, target)
                            info += f"  - {comparison_name}: {'Satisfied' if is_satisfied else 'Not Satisfied'} (Source: {source_value.value if isinstance(source_value, Attribute) else source_value}, Target: {target_value.value if isinstance(target_value, Attribute) else target_value})\n"
                    if statement.callables:
                        info += "- Callables:\n"
                        for callable_func in statement.callables:
                            is_satisfied = statement.validate_callables(source, target)
                            info += f"  - {callable_func.__doc__}: {'Satisfied' if is_satisfied else 'Not Satisfied'}\n"
        return info

    def calculate_distance(self, source_node: Node, target_node: Node) -> int:
        return abs(source_node.position.x - target_node.position.x) + abs(source_node.position.y - target_node.position.y)

    def find_path(self, source_node: Node, target_node: Node) -> Optional[List[Tuple[int, int]]]:
        grid_map = GridMap.get_instance(source_node.gridmap_id)
        if grid_map:
            path = grid_map.get_path(source_node, target_node)
            if path:
                return [node.position.value for node in path.nodes]
        return None

    def format_path(self, path: Optional[List[Tuple[int, int]]]) -> str:
        if path:
            return ' -> '.join(str(node) for node in path)
        return "No path found"

    def calculate_ray(self, source_node: Node, target_node: Node, shape: Union[Rectangle, Shadow, Radius]) -> str:
        grid_map = GridMap.get_instance(source_node.gridmap_id)
        if grid_map:
            raycast = grid_map.get_raycast(source_node, target_node)
            if isinstance(raycast, RayCast):
                ray_path = ' -> '.join(str(node.position.value) for node in raycast.nodes)
                return f"Ray: {ray_path}"
            elif isinstance(raycast, BlockedRaycast):
                ray_path = ' -> '.join(str(node.position.value) for node in raycast.nodes)
                blocking_entity = raycast.blocking_entity
                blocking_entity_name = blocking_entity.__class__.__name__ if blocking_entity else "Unknown"
                blocking_entity_attributes = ", ".join(f"{attr.name}: {attr.value}" for attr in blocking_entity.all_attributes().values()) if blocking_entity else "N/A"
                return f"Blocked Ray: {ray_path} (Blocked by {blocking_entity_name} at {raycast.blocking_node.position.value}, Attributes: {blocking_entity_attributes})"
        return "Ray: Not available"

class ObservationState:
    def __init__(self, character_id: str):
        self.character_id = character_id
        self.paths = {}

    def generate(self, shape: Union[Shadow, Rectangle, Radius]) -> str:
        observation_message = ""
        observation_message += self._generate_character_summary(self.character_id, shape)
        observation_message += self._generate_visibility_matrix(shape, self.character_id)
        observation_message += self._generate_movement_matrix(shape, self.character_id)
        path_matrix_content, paths = self._generate_path_matrix(shape, self.character_id)
        observation_message += path_matrix_content
        observation_message += self._generate_immediate_neighbors(shape, self.character_id)
        observation_message += self._generate_node_equivalence_classes(shape)
        observation_message += self._generate_living_entities(shape, self.character_id)
        observation_message += self._generate_attribute_summary(shape)
        observation_message += self._generate_pathfinding_information(paths)
        return observation_message.strip()

    @staticmethod
    def _generate_character_summary(character_id: str, shape: Union[Shadow, Rectangle, Radius]) -> str:
        character = GameEntity.get_instance(character_id)
        if character is None:
            return "Character not found."
        position = character.position.value
        attack_power = character.get_attr("attack_power")
        health = character.get_attr("health")
        max_health = character.get_attr("max_health")
        can_act = character.get_attr("can_act")
        header = "# Character Summary\n"
        content = f"Position: {position}\n"
        content += f"Key Attributes:\n"
        content += f"  - AttackPower: {attack_power}\n"
        content += f"  - Health: {health}\n"
        content += f"  - MaxHealth: {max_health}\n"
        content += f"  - CanAct: {can_act}\n"
        return f"{header}{content}\n"

    @staticmethod
    def _generate_visibility_matrix(shape: Union[Shadow, Rectangle, Radius], character_id: str) -> str:
        character = GameEntity.get_instance(character_id)
        if character is None:
            return "Character not found."
        character_node = character.node
        if character_node is None:
            return "Character is not in a node."
        grid_map = GridMap.get_instance(character_node.gridmap_id)
        if grid_map is None:
            return "Grid map not found."
        nodes = shape.nodes if isinstance(shape, (Shadow, Radius)) else grid_map.get_nodes_in_rect(shape)
        min_x = min(node.position.value[0] for node in nodes)
        max_x = max(node.position.value[0] for node in nodes)
        min_y = min(node.position.value[1] for node in nodes)
        max_y = max(node.position.value[1] for node in nodes)
        visibility_matrix = [["?" for _ in range(max_x - min_x + 1)] for _ in range(max_y - min_y + 1)]
        character_x, character_y = character_node.position.value
        visibility_matrix[character_y - min_y][character_x - min_x] = "c"
        for node in nodes:
            x = node.position.value[0] - min_x
            y = node.position.value[1] - min_y
            visibility_matrix[y][x] = "v" if not node.blocks_light.value else "x"
        visibility_matrix[character_y - min_y][character_x - min_x] = "c"
        visibility_matrix_str = "\n".join([" ".join(row) for row in visibility_matrix])
        header = f"# Nodes Allowing Light Matrix ({max_y - min_y + 1}x{max_x - min_x + 1} Grid)\n"
        content = visibility_matrix_str
        return f"{header}{content}\n\n"

    @staticmethod
    def _generate_movement_matrix(shape: Union[Shadow, Rectangle, Radius], character_id: str) -> str:
        character = GameEntity.get_instance(character_id)
        if character is None:
            return "Character not found."
        character_node = character.node
        if character_node is None:
            return "Character is not in a node."
        grid_map = GridMap.get_instance(character_node.gridmap_id)
        if grid_map is None:
            return "Grid map not found."
        nodes = shape.nodes if isinstance(shape, (Shadow, Radius)) else grid_map.get_nodes_in_rect(shape)
        min_x = min(node.position.value[0] for node in nodes)
        max_x = max(node.position.value[0] for node in nodes)
        min_y = min(node.position.value[1] for node in nodes)
        max_y = max(node.position.value[1] for node in nodes)
        movement_matrix = [["?" for _ in range(max_x - min_x + 1)] for _ in range(max_y - min_y + 1)]
        character_x, character_y = character_node.position.value
        movement_matrix[character_y - min_y][character_x - min_x] = "c"
        for node in nodes:
            x = node.position.value[0] - min_x
            y = node.position.value[1] - min_y
            movement_matrix[y][x] = "v" if not node.blocks_movement.value else "x"
        movement_matrix[character_y - min_y][character_x - min_x] = "c"
        movement_matrix_str = "\n".join([" ".join(row) for row in movement_matrix])
        header = f"# Nodes Allowing Movement Matrix ({max_y - min_y + 1}x{max_x - min_x + 1} Grid)\n"
        content = movement_matrix_str
        return f"{header}{content}\n\n"

    @staticmethod
    def _generate_path_matrix(shape: Union[Shadow, Rectangle, Radius], character_id: str) -> str:
        character = GameEntity.get_instance(character_id)
        if character is None:
            return "Character not found."
        character_node = character.node
        if character_node is None:
            return "Character is not in a node."
        grid_map = GridMap.get_instance(character_node.gridmap_id)
        if grid_map is None:
            return "Grid map not found."
        nodes = shape.nodes if isinstance(shape, (Shadow, Radius)) else grid_map.get_nodes_in_rect(shape)
        min_x = min(node.position.value[0] for node in nodes)
        max_x = max(node.position.value[0] for node in nodes)
        min_y = min(node.position.value[1] for node in nodes)
        max_y = max(node.position.value[1] for node in nodes)
        path_matrix = [["?" for _ in range(max_x - min_x + 1)] for _ in range(max_y - min_y + 1)]
        character_x, character_y = character_node.position.value
        path_matrix[character_y - min_y][character_x - min_x] = "c"
        paths = {}
        for node in nodes:
            x = node.position.value[0] - min_x
            y = node.position.value[1] - min_y
            path = grid_map.get_path(character_node, node)
            if path:
                path_matrix[y][x] = str(len(path.nodes) - 1)
                paths[node.position.value] = path
            else:
                path_matrix[y][x] = "x"
        path_matrix[character_y - min_y][character_x - min_x] = "c"
        path_matrix_str = "\n".join([" ".join(row) for row in path_matrix])
        header = f"# Path Matrix ({max_y - min_y + 1}x{max_x - min_x + 1} Grid)\n"
        content = path_matrix_str
        return f"{header}{content}\n\n", paths

    def _generate_pathfinding_information(self, paths: Dict[Tuple[int, int], Path]) -> str:
        header = "# Pathfinding Information\n"
        content = ""
        for position, path in paths.items():
            if len(path.nodes) > 2:
                content += f"- Path to {position}: {' -> '.join(str(node.position.value) for node in path.nodes)}\n"
        if not content:
            content = "No paths with length greater than 1 found."
        return f"{header}{content}\n\n"

    @staticmethod
    def _generate_immediate_neighbors(shape: Union[Shadow, Rectangle, Radius], character_id: str) -> str:
        character = GameEntity.get_instance(character_id)
        if character is None:
            return "Character not found."
        character_node = character.node
        if character_node is None:
            return "Character is not in a node."
        neighbors = character_node.neighbors()
        header = "# Immediate Neighbors (3x3 Grid)\n"
        content = ""
        directions = ["NorthWest", "North", "NorthEast", "West", "Center", "East", "SouthWest", "South", "SouthEast"]
        for direction in directions:
            if direction == "Center":
                x, y = character_node.position.value
                node_status = "Node (Passable)"
                entities = [entity.__class__.__name__ for entity in character_node.entities]
            else:
                dx, dy = ObservationState._get_direction_offset(direction)
                neighbor_position = (character_node.position.value[0] + dx, character_node.position.value[1] + dy)
                neighbor_node = next((node for node in neighbors if node.position.value == neighbor_position), None)
                if neighbor_node is None:
                    continue
                x, y = neighbor_node.position.value
                node_status = "Node (Passable)"
                if neighbor_node.blocks_movement.value and neighbor_node.blocks_light.value:
                    node_status = "Node (Blocks Movement, Blocks Light)"
                elif neighbor_node.blocks_movement.value:
                    node_status = "Node (Blocks Movement)"
                elif neighbor_node.blocks_light.value:
                    node_status = "Node (Blocks Light)"
                entities = [entity.__class__.__name__ for entity in neighbor_node.entities]
                if "Door" in entities:
                    door = next((entity for entity in neighbor_node.entities if isinstance(entity, Door)), None)
                    if door is not None:
                        entities.remove("Door")
                        entities.append(f"Door (Open: {door.open.value}, Locked: {door.is_locked.value}, Required Key: {door.required_key.value})")
            content += f"- {direction} ({x}, {y}): {node_status}, Entities: {entities}\n"
        return f"{header}{content}\n"

    @staticmethod
    def _get_direction_offset(direction: str) -> Tuple[int, int]:
        direction_map = {
            "North": (0, -1),
            "South": (0, 1),
            "East": (1, 0),
            "West": (-1, 0),
            "NorthEast": (1, -1),
            "NorthWest": (-1, -1),
            "SouthEast": (1, 1),
            "SouthWest": (-1, 1)
        }

        return direction_map[direction]

    @staticmethod
    def _generate_node_equivalence_classes(shape: Union[Shadow, Rectangle, Radius]) -> str:
        nodes = shape.nodes if isinstance(shape, (Shadow, Radius)) else GridMap.get_instance(shape.nodes[0].gridmap_id).get_nodes_in_rect(shape)
        equivalence_classes = {}
        for node in nodes:
            entity_types = tuple(sorted(type(entity).__name__ for entity in node.entities if not isinstance(entity, Character)))
            entity_attributes = {}
            for entity in node.entities:
                if not isinstance(entity, Character):
                    entity_attributes[type(entity).__name__] = tuple(sorted((attr.name, attr.value) for attr in entity.all_attributes().values()))
            key = (entity_types, tuple(sorted(entity_attributes.items())))
            if key not in equivalence_classes:
                equivalence_classes[key] = []
            equivalence_classes[key].append(node)
        header = "# Node Equivalence Classes\n"
        content = ""
        for (entity_types, entity_attributes), nodes in equivalence_classes.items():
            content += f"- {', '.join(entity_types)}:\n"
            content += f"  - Positions: {[node.position.value for node in nodes]}\n"
            for entity_type, attributes in entity_attributes:
                content += f"  - {entity_type} Attributes:\n"
                for attr_name, attr_value in attributes:
                    content += f"    - {attr_name}: {attr_value}\n"
        return f"{header}{content}\n"

    @staticmethod
    def _generate_living_entities(shape: Union[Shadow, Rectangle, Radius], character_id: str) -> str:
        if isinstance(shape, (Shadow, Radius)):
            nodes = shape.nodes
            source_id = shape.source.id
        else:  # Rectangle
            nodes = shape.nodes
            source_id = GameEntity.get_instance(character_id).id

        living_entities = [entity for node in nodes for entity in node.entities if isinstance(entity, Character) and entity.id != source_id]
        if not living_entities:
            return "No living entities in the visible area, excluding the character."
        header = "# Living Entities\n"
        content = ""
        for entity in living_entities:
            content += f"- {entity.name} (ID: {entity.id}, Position: {entity.position.value})\n"
            content += f"  - Attributes:\n"
            for attr_name, attr_value in entity.all_attributes().items():
                content += f"    - {attr_name}: {attr_value.value}\n"
        return f"{header}{content}\n"

    @staticmethod
    def _generate_movement_sub_goal() -> str:
        header = "# Movement Sub-Goal\n"
        content = "Movement Sub-Goal: Not implemented yet."
        return f"{header}{content}\n\n"
    @staticmethod
    def _generate_attribute_summary(shape: Union[Shadow, Rectangle, Radius]) -> str:
        nodes = shape.nodes if isinstance(shape, (Shadow, Radius)) else GridMap.get_instance(shape.nodes[0].gridmap_id).get_nodes_in_rect(shape)
        attribute_groups = {
            "Walkable and Visible": [],
            "Walkable and Not Visible": [],
            "Not Walkable and Visible": [],
            "Not Walkable and Not Visible": []
        }
        for node in nodes:
            walkable = not node.blocks_movement.value
            visible = not node.blocks_light.value
            if walkable and visible:
                group = "Walkable and Visible"
            elif walkable and not visible:
                group = "Walkable and Not Visible"
            elif not walkable and visible:
                group = "Not Walkable and Visible"
            else:
                group = "Not Walkable and Not Visible"
            entity_types_and_attributes = []
            for entity in node.entities:
                if not isinstance(entity, Character):
                    entity_type = type(entity).__name__
                    entity_attributes = {attr.name: attr.value for attr in entity.all_attributes().values() if not isinstance(attr, (BlocksMovement, BlocksLight))}
                    entity_types_and_attributes.append((entity_type, tuple(sorted(entity_attributes.items()))))
            if tuple(entity_types_and_attributes) not in attribute_groups[group]:
                attribute_groups[group].append(tuple(entity_types_and_attributes))
        header = "# Nodes Spatial Attributes Summary (Ignoring Living Entities)\n"
        content = ""
        for group, equivalence_classes in attribute_groups.items():
            node_count = sum(1 for node in nodes if node.blocks_movement.value == (group.startswith("Not Walkable")) and node.blocks_light.value == (group.endswith("Not Visible")))
            content += f"- {group}: {node_count} nodes\n"
            if equivalence_classes:
                for eq_class in equivalence_classes:
                    entities_str = ", ".join([f"{entity_type} ({', '.join([f'{attr_name}: {attr_value}' for attr_name, attr_value in attributes])})" for entity_type, attributes in eq_class])
                    content += f"  - Equivalence Class: [{entities_str}]\n"
            else:
                content += f"  - Equivalence Classes: None\n"
        return f"{header}{content}\n"



    @staticmethod
    def _generate_cognitive_insights(shape: Union[Shadow, Rectangle, Radius]) -> str:
        header = "# Cognitive Insights\n"
        content = "Cognitive Insights: Not implemented yet."
        return f"{header}{content}\n"

class ActionState:
    def __init__(self, action_result: Optional[ActionResult] = None):
        self.action_result = action_result

    def update_state(self, action_result: ActionResult):
        if not isinstance(action_result, ActionResult):
            raise ValueError("Invalid action result")
        self.action_result = action_result

    def generate(self, action_result: Optional[ActionResult]) -> str:
        if action_result:
            self.update_state(action_result)
        if self.action_result.success:
            return self._generate_success_analysis()
        else:
            return self._generate_failure_analysis()

    def _generate_success_analysis(self,) -> str:
        if not self.action_result:
            raise ValueError("Action result not set")
        action_name = self.action_result.action_instance.action.__class__.__name__
        source_before = self.action_result.state_before["source"]
        source_after = self.action_result.state_after["source"]
        target_before = self.action_result.state_before["target"]
        target_after = self.action_result.state_after["target"]

        source_entity_before = GameEntity.get_instance(self.action_result.action_instance.source_id)
        source_entity_after = GameEntity.get_instance(self.action_result.action_instance.source_id)
        target_entity_before = GameEntity.get_instance(self.action_result.action_instance.target_id)
        target_entity_after = GameEntity.get_instance(self.action_result.action_instance.target_id)

        analysis = "# Action Result Analysis\n"
        analysis += f"## Action: {action_name}\n"
        analysis += "### Result: Success\n"
        analysis += "### Before:\n"
        analysis += f"- Source: {self._format_entity_state(source_before, source_entity_before)}\n"
        analysis += f"- Target: {self._format_entity_state(target_before, target_entity_before)}\n"
        analysis += "### Changes:\n"

        source_changes = []
        target_changes = []

        for attr_name, attr_value_before in source_before.items():
            attr_value_after = source_after.get(attr_name)
            if attr_value_before != attr_value_after:
                source_changes.append(f"{attr_name}: {attr_value_before} -> {attr_value_after}")

        for attr_name, attr_value_before in target_before.items():
            attr_value_after = target_after.get(attr_name)
            if attr_value_before != attr_value_after:
                target_changes.append(f"{attr_name}: {attr_value_before} -> {attr_value_after}")

        if source_changes:
            analysis += f"- Source: {self._format_entity_brief(source_after, source_entity_after)} [{', '.join(source_changes)}]\n"
        if target_changes:
            analysis += f"- Target: {self._format_entity_brief(target_after, target_entity_after)} [{', '.join(target_changes)}]\n"

        if source_changes or target_changes:
            analysis += "### Natural Language Summary:\n"
            if source_changes:
                attr_name, attr_value_change = source_changes[0].split(': ')
                attr_value_before, attr_value_after = attr_value_change.split(' -> ')
                analysis += f"The {attr_name}: {attr_value_before} of {self._format_entity_brief(source_before, source_entity_before)} changed to {attr_value_after} as a result of {action_name}.\n"
            if target_changes:
                attr_name, attr_value_change = target_changes[0].split(': ')
                attr_value_before, attr_value_after = attr_value_change.split(' -> ')
                analysis += f"The {attr_name}: {attr_value_before} of {self._format_entity_brief(target_before, target_entity_before)} changed to {attr_value_after} as a result of {action_name}.\n"

        return analysis

    def _generate_failure_analysis(self) -> str:
        action_name = self.action_result.action_instance.action.__class__.__name__
        source_state = self.action_result.state_before["source"]
        target_state = self.action_result.state_before["target"]
        source_entity = GameEntity.get_instance(self.action_result.action_instance.source_id)
        target_entity = GameEntity.get_instance(self.action_result.action_instance.target_id)

        analysis = "# Action Result Analysis\n"
        analysis += f"## Action: {action_name}\n"
        analysis += "### Result: Failure\n"
        analysis += "### Reason: Prerequisites not met\n"
        analysis += "### Prerequisites:\n"

        prerequisites = self.action_result.action_instance.action.prerequisites
        failed_prerequisites = self.action_result.failed_prerequisites

        for statement_type in ["source_statements", "target_statements", "source_target_statements"]:
            statements = getattr(prerequisites, statement_type)
            for statement in statements:
                is_failed = any(statement.id in prerequisite for prerequisite in failed_prerequisites)
                status = "Failed" if is_failed else "Passed"
                analysis += f"- {statement_type.capitalize().replace('_', ' ')}:\n"
                analysis += f"  - Status: {status}\n"

                if statement.conditions:
                    analysis += "  - Conditions:\n"
                    for attr_name, desired_value in statement.conditions.items():
                        actual_value = source_state[attr_name] if statement_type == "source_statements" else target_state[attr_name]
                        condition_met = actual_value == desired_value
                        analysis += f"    - {attr_name}: {'Met' if condition_met else 'Not Met'} (Desired: {desired_value}, Actual: {actual_value})\n"

                if statement.comparisons:
                    analysis += "  - Comparisons:\n"
                    for comparison_name, (source_attr, target_attr, comparison_func) in statement.comparisons.items():
                        comparison_description = comparison_func.__doc__.strip() if comparison_func.__doc__ else "No description available"
                        source_value = source_state[source_attr] if source_attr in source_state else getattr(source_entity, source_attr)
                        target_value = target_state[target_attr] if target_attr in target_state else getattr(target_entity, target_attr)
                        comparison_met = comparison_func(source_value, target_value)
                        analysis += f"    - {comparison_name.capitalize()}:\n"
                        analysis += f"      - Source Attribute: {source_attr}\n"
                        analysis += f"      - Target Attribute: {target_attr}\n"
                        analysis += f"      - Comparison: {'Met' if comparison_met and status == 'Passed' else 'Not Met'}\n"
                        analysis += f"      - Description: {comparison_description}\n"

                if statement.callables:
                    analysis += "  - Callables:\n"
                    for callable_func in statement.callables:
                        callable_description = callable_func.__doc__.strip() if callable_func.__doc__ else "No description available"
                        callable_met = callable_func(source_entity, target_entity)
                        analysis += f"    - {'Met' if callable_met and status == 'Passed' else 'Not Met'}\n"
                        analysis += f"      - Description: {callable_description}\n"

        return analysis
        
    def _format_entity_state(self, entity_state: Dict[str, Any], entity: GameEntity) -> str:
        entity_type = entity.__class__.__name__
        position = entity_state.get("position", (0, 0))
        attributes = ", ".join(f"{attr_name}: {attr_value}" for attr_name, attr_value in entity_state.items() if attr_name not in ["position"])
        return f"{entity_type} '{entity.name}' ({position[0]}, {position[1]}) [{attributes}]"

    def _format_entity_brief(self, entity_state: Dict[str, Any], entity: GameEntity) -> str:
        entity_type = entity.__class__.__name__
        position = entity_state.get("position", (0, 0))
        return f"{entity_type} '{entity.name}'"
    
   

class StrActionConverter:
    def __init__(self, grid_map: GridMap):
        self.grid_map = grid_map

    def convert_action_string(self, action_string: str, character_id: str) -> Union[ActionsPayload, str]:
        parts = action_string.split(" ")
        if len(parts) != 3:
            return "Invalid action string format. Expected: 'direction action_name target_type'"

        direction, action_name, target_type = parts
        character = GameEntity.get_instance(character_id)
        if character is None:
            return "Character not found"

        character_node = character.node
        if character_node is None:
            return "Character is not in a node"

        target_node = self._get_target_node(character_node, direction)
        if target_node is None:
            return "Invalid direction"

        target_entity = self._find_target_entity(target_node, target_type)
        if target_entity is None:
            return f"Target entity of type '{target_type}' not found in the target node"

        action_class = self.grid_map.actions.get(action_name)
        if action_class is None:
            return f"Action '{action_name}' not found"

        action_instance = ActionInstance(source_id=character_id, target_id=target_entity.id, action=action_class())
        return ActionsPayload(actions=[action_instance])

    def _get_target_node(self, character_node: Node, direction: str) -> Optional[Node]:
        direction_map = {
            "North": (0, -1),
            "South": (0, 1),
            "East": (1, 0),
            "West": (-1, 0),
            "NorthEast": (1, -1),
            "NorthWest": (-1, -1),
            "SouthEast": (1, 1),
            "SouthWest": (-1, 1),
            "Center": (0, 0),
        }

        offset = direction_map.get(direction)
        if offset is None:
            return None

        target_position = (character_node.position.x + offset[0], character_node.position.y + offset[1])
        return self.grid_map.get_node(target_position)

    def _find_target_entity(self, target_node: Node, target_type: str) -> Optional[GameEntity]:
        entity_type = self.grid_map.entity_type_map.get(target_type)
        if entity_type is None:
            return None

        return target_node.find_entity(entity_type)

---

## nodes

# nodes.py

from typing import List, Optional, Dict, Any, Union, Type, Tuple
from pydantic import BaseModel, Field, ConfigDict
from abstractions.goap.entity import Entity, Attribute, RegistryHolder
import typing

import uuid

if typing.TYPE_CHECKING:
    from abstractions.goap.gridmap import GridMap

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




class GameEntity(Entity):
    """
    Represents an entity in the game world.
    Attributes:
        blocks_movement (BlocksMovement): Attribute indicating if the entity blocks movement.
        blocks_light (BlocksLight): Attribute indicating if the entity blocks light.
        node (Optional[Node]): The node the entity is currently in.
        inventory (List[GameEntity]): The entities stored inside this entity's inventory.
        stored_in (Optional[GameEntity]): The entity this entity is stored inside, if any.
        hash_resolution (str): The resolution level for hashing and string representation.
    """
    blocks_movement: BlocksMovement = Field(default_factory=BlocksMovement, description="Attribute indicating if the entity blocks movement")
    blocks_light: BlocksLight = Field(default_factory=BlocksLight, description="Attribute indicating if the entity blocks light")
    node: Optional["Node"] = Field(default=None, description="The node the entity is currently in")
    inventory: List["GameEntity"] = Field(default_factory=list, description="The entities stored inside this entity's inventory")
    stored_in: Optional["GameEntity"] = Field(default=None, description="The entity this entity is stored inside, if any")
    hash_resolution: str = Field(default="default", description="The resolution level for hashing and string representation")

    @classmethod
    def get_instance(cls, instance_id: str) -> Optional["GameEntity"]:
        instance = cls._registry.get(instance_id)
        if instance is not None and not isinstance(instance, cls):
            raise TypeError(f"Instance with ID {instance_id} is not of type {cls.__name__}")
        return instance

    @property
    def position(self) -> Position:
        """
        Returns the position of the entity.

        If the entity is stored inside another entity, it returns the position of the parent entity.
        If the entity is in a node, it returns the position of the node.
        Otherwise, it returns a default position (0, 0).
        """
        if self.stored_in:
            return self.stored_in.position
        elif self.node:
            return self.node.position
        return Position()

    def set_node(self, node: "Node"):
        """
        Sets the node of the entity.

        Args:
            node (Node): The node to set.

        Raises:
            ValueError: If the entity is stored inside another entity's inventory.
        """
        if self.stored_in:
            raise ValueError("Cannot set node for an entity stored inside another entity's inventory")
        self.node = node
        node.add_entity(self)

    def remove_from_node(self):
        """
        Removes the entity from its current node.

        Raises:
            ValueError: If the entity is stored inside another entity's inventory.
        """
        if self.stored_in:
            raise ValueError("Cannot remove from node an entity stored inside another entity's inventory")
        if self.node:
            self.node.remove_entity(self)
            self.node = None

    def update_attributes(self, attributes: Dict[str, Union[Attribute, "Node", str, List[str]]]) -> "GameEntity":
        """
        Updates the attributes of the entity.

        Args:
            attributes (Dict[str, Union[Attribute, Node, str, List[str]]]): The attributes to update.

        Returns:
            GameEntity: The updated entity.
        """
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

    def add_to_inventory(self, entity: "GameEntity"):
        """
        Adds an entity to the inventory of this entity.

        Args:
            entity (GameEntity): The entity to add to the inventory.
        """
        if entity not in self.inventory:
            self.inventory.append(entity)
            entity.stored_in = self

    def remove_from_inventory(self, entity: "GameEntity"):
        """
        Removes an entity from the inventory of this entity.

        Args:
            entity (GameEntity): The entity to remove from the inventory.
        """
        if entity in self.inventory:
            self.inventory.remove(entity)
            entity.stored_in = None

    def set_stored_in(self, entity: Optional["GameEntity"]):
        """
        Sets the entity this entity is stored inside.

        Args:
            entity (Optional[GameEntity]): The entity to store this entity inside, or None to remove it from storage.
        """
        if entity is None:
            if self.stored_in:
                self.stored_in.remove_from_inventory(self)
        else:
            entity.add_to_inventory(self)

    def get_state(self) -> Dict[str, Any]:
        """
        Returns the state of the entity as a dictionary.

        Returns:
            Dict[str, Any]: The state of the entity.
        """
        state = {}
        for attr_name, attr_value in self.__dict__.items():
            if isinstance(attr_value, Attribute) and attr_name not in ["position", "inventory"]:
                state[attr_name] = attr_value.value
        state["position"] = self.position.value
        state["inventory"] = [item.id for item in self.inventory]
        return state

    def get_attr(self, attr_name: str) -> Any:
        """
        Retrieves the value of an attribute.

        Args:
            attr_name (str): The name of the attribute.

        Returns:
            Any: The value of the attribute.
        """
        attr = getattr(self, attr_name, None)
        if isinstance(attr, Attribute):
            return attr.value
        return attr

    def set_attr(self, attr_name: str, value: Any):
        """
        Sets the value of an attribute.

        Args:
            attr_name (str): The name of the attribute.
            value (Any): The value to set.
        """
        attr = getattr(self, attr_name, None)
        if isinstance(attr, Attribute):
            attr.value = value
        else:
            setattr(self, attr_name, value)

    def set_hash_resolution(self, resolution: str):
        """
        Sets the resolution level for hashing and string representation.

        Args:
            resolution (str): The resolution level. Can be "default", "attributes", or "inventory".
        """
        self.hash_resolution = resolution

    def reset_hash_resolution(self):
        """
        Resets the resolution level for hashing and string representation to the default value.
        """
        self.hash_resolution = "default"
    

    def __repr__(self, resolution: Optional[str] = None) -> str:
        """
        Returns a string representation of the entity.

        Args:
            resolution (Optional[str]): The resolution level for the representation. If not provided, uses the entity's hash_resolution.

        Returns:
            str: The string representation of the entity.
        """
        resolution = resolution or self.hash_resolution
        if resolution == "default":
            attrs = {
                "id": self.id,
                "name": self.name,
                "position": self.position.value
            }
        elif resolution == "attributes":
            attrs = {
                "id": self.id,
                "name": self.name,
                "position": self.position.value,
                "attributes": {attr_name: attr_value.value for attr_name, attr_value in self.__dict__.items() if isinstance(attr_value, Attribute)}
            }
        elif resolution == "inventory":
            attrs = {
                "id": self.id,
                "name": self.name,
                "position": self.position.value,
                "attributes": {attr_name: attr_value.value for attr_name, attr_value in self.__dict__.items() if isinstance(attr_value, Attribute)},
                "inventory": [item.__repr__(resolution="default") for item in self.inventory]
            }
        else:
            raise ValueError(f"Invalid resolution level: {resolution}")
        attrs_str = ', '.join(f'{k}={v}' for k, v in attrs.items())
        return f"{self.__class__.__name__}({attrs_str})"

    def __hash__(self, resolution: Optional[str] = None) -> int:
        """
        Returns the hash value of the entity.

        Args:
            resolution (Optional[str]): The resolution level for hashing. If not provided, uses the entity's hash_resolution.

        Returns:
            int: The hash value of the entity.
        """
        resolution = resolution or self.hash_resolution
        if resolution == "default":
            return hash(self.id)
        elif resolution == "attributes":
            attribute_values = [f"{attr_name}={attr_value.value}" for attr_name, attr_value in self.__dict__.items() if isinstance(attr_value, Attribute)]
            return hash((self.id, tuple(attribute_values)))
        elif resolution == "inventory":
            attribute_values = [f"{attr_name}={attr_value.value}" for attr_name, attr_value in self.__dict__.items() if isinstance(attr_value, Attribute)]
            inventory_hashes = tuple(hash(item) for item in self.inventory)
            return hash((self.id, tuple(attribute_values), inventory_hashes))
        else:
            raise ValueError(f"Invalid resolution level: {resolution}")
        

# nodes.py



class Node(BaseModel, RegistryHolder):
    """
    Represents a node in the grid map.

    Attributes:
        name (str): The name of the node.
        id (str): The unique identifier of the node.
        position (Position): The position of the node.
        entities (List[GameEntity]): The game entities contained within the node.
        gridmap_id (str): The ID of the grid map the node belongs to.
        blocks_movement (bool): Indicates if the node blocks movement.
        blocks_light (bool): Indicates if the node blocks light.
        hash_resolution (str): The resolution level for hashing and string representation.
    """
    name: str = Field("", description="The name of the node")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="The unique identifier of the node")
    position: Position = Field(default_factory=Position, description="The position of the node")
    entities: List[GameEntity] = Field(default_factory=list, description="The game entities contained within the node")
    gridmap_id: str = Field(description="The ID of the grid map the node belongs to")
    blocks_movement: BlocksMovement = Field(default_factory=BlocksMovement, description="Indicates if the node blocks movement, True if any entity in the node blocks movement, False otherwise")
    blocks_light: BlocksLight = Field(default_factory=BlocksLight, description="Indicates if the node blocks light, True if any entity in the node blocks light, False otherwise")

    hash_resolution: str = Field(default="default", description="The resolution level for hashing and string representation")

    class Config(ConfigDict):
        arbitrary_types_allowed = True

    def __init__(self, **data: Any):
        super().__init__(**data)
        self.register(self)

    @classmethod
    def get_instance(cls, instance_id: str) -> Optional["Node"]:
        instance = cls._registry.get(instance_id)
        if instance is not None and not isinstance(instance, cls):
            raise TypeError(f"Instance with ID {instance_id} is not of type {cls.__name__}")
        return instance

    def add_entity(self, entity: GameEntity):
        """
        Adds an entity to the node.

        Args:
            entity (GameEntity): The entity to add.

        Raises:
            ValueError: If the entity is stored inside another entity's inventory.
        """
        if entity.stored_in:
            raise ValueError("Cannot add an entity stored inside another entity's inventory directly to a node")
        self.entities.append(entity)
        entity.node = self
        self.update_blocking_properties()

    def remove_entity(self, entity: GameEntity):
        """
        Removes an entity from the node.

        Args:
            entity (GameEntity): The entity to remove.

        Raises:
            ValueError: If the entity is stored inside another entity's inventory.
        """
        if entity.stored_in:
            raise ValueError("Cannot remove an entity stored inside another entity's inventory directly from a node")
        self.entities.remove(entity)
        entity.node = None
        self.update_blocking_properties()

    def update_entity(self, old_entity: GameEntity, new_entity: GameEntity):
        """
        Updates an entity in the node.

        Args:
            old_entity (GameEntity): The old entity to replace.
            new_entity (GameEntity): The new entity to replace with.
        """
        self.remove_entity(old_entity)
        self.add_entity(new_entity)

    def update_blocking_properties(self):
        any_movement_blocks = any(entity.blocks_movement.value for entity in self.entities if not entity.stored_in)
        if any_movement_blocks:
            self.blocks_movement.value = True
        else:
            self.blocks_movement.value = False
        any_light_blocks = any(entity.blocks_light.value for entity in self.entities if not entity.stored_in)
        if any_light_blocks:
            self.blocks_light.value = True
        else:
            self.blocks_light.value = False



    def reset(self):
        """
        Resets the node by clearing its entities and resetting the blocking properties.
        """
        self.entities.clear()
        self.blocks_movement = False
        self.blocks_light = False

    def find_entity(self, entity_type: Type[GameEntity], entity_id: Optional[str] = None,
                    entity_name: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None) -> Optional[Union[GameEntity, "AmbiguousEntityError"]]:
        """
        Finds an entity in the node based on the specified criteria.

        Args:
            entity_type (Type[GameEntity]): The type of the entity to find.
            entity_id (Optional[str]): The ID of the entity to find.
            entity_name (Optional[str]): The name of the entity to find.
            attributes (Optional[Dict[str, Any]]): Additional attributes to match.

        Returns:
            Optional[Union[GameEntity, AmbiguousEntityError]]: The found entity, an AmbiguousEntityError if multiple entities match the criteria, or None if no entity is found.
        """
        matching_entities = []
        for entity in self.entities:
            if isinstance(entity, entity_type):
                if entity_id is not None and entity.id != entity_id:
                    continue
                if entity_name is not None and entity.name != entity_name:
                    continue
                if attributes is not None:
                    entity_attributes = {attr_name: entity.get_attr(attr_name) for attr_name in attributes}
                    if any(attr_name not in entity_attributes or entity_attributes[attr_name] != attr_value
                           for attr_name, attr_value in attributes.items()):
                        continue
                matching_entities.append(entity)
        if len(matching_entities) == 1:
            return matching_entities[0]
        elif len(matching_entities) > 1:
            missing_attributes = []
            if entity_id is None:
                missing_attributes.append("entity_id")
            if entity_name is None:
                missing_attributes.append("entity_name")
            if attributes is None:
                missing_attributes.extend(attr.name for attr in matching_entities[0].all_attributes())
            return AmbiguousEntityError(
                entity_type=entity_type,
                entity_id=entity_id,
                entity_name=entity_name,
                attributes=attributes,
                matching_entities=matching_entities,
                missing_attributes=missing_attributes
            )
        else:
            return None

    def neighbors(self) -> List["Node"]:
        """
        Returns the neighboring nodes of the node.

        Returns:
            List[Node]: The neighboring nodes.
        """
        grid_map: Optional[GridMap] = RegistryHolder.get_instance(self.gridmap_id)
        if grid_map:
            return grid_map.get_neighbors(self.position.value)
        return []
    
    
    def _get_entity_info(self) -> Tuple[List[str], List[Tuple[str, Any]]]:
        """
        Retrieves the entity types and attributes of the entities in the node.

        Returns:
            Tuple[List[str], List[Tuple[str, Any]]]: A tuple containing the entity types and attributes.
        """
        entity_types = []
        entity_attributes = []
        for entity in self.entities:
            entity_types.append(type(entity).__name__)
            attributes = [(attr.name, attr.value) for attr in entity.all_attributes().values()]
            entity_attributes.extend(attributes)
        return entity_types, entity_attributes

    def set_hash_resolution(self, resolution: str):
        """
        Sets the resolution level for hashing and string representation.

        Args:
            resolution (str): The resolution level. Can be "default", "entities", or "full".
        """
        self.hash_resolution = resolution

    def reset_hash_resolution(self):
        """
        Resets the resolution level for hashing and string representation to the default value.
        """
        self.hash_resolution = "default"

    def __repr__(self, resolution: Optional[str] = None) -> str:
        """
        Returns a string representation of the node.

        Args:
            resolution (Optional[str]): The resolution level for the representation. If not provided, uses the node's hash_resolution.

        Returns:
            str: The string representation of the node.
        """
        resolution = resolution or self.hash_resolution
        if resolution == "default":
            attrs = {
                "id": self.id,
                "position": self.position.value
            }
        elif resolution == "entities":
            attrs = {
                "id": self.id,
                "position": self.position.value,
                "entities": [entity.__repr__(resolution="default") for entity in self.entities]
            }
        elif resolution == "full":
            attrs = {
                "id": self.id,
                "position": self.position.value,
                "entities": [entity.__repr__(resolution="attributes") for entity in self.entities],
                "blocks_movement": self.blocks_movement,
                "blocks_light": self.blocks_light
            }
        else:
            raise ValueError(f"Invalid resolution level: {resolution}")
        attrs_str = ', '.join(f'{k}={v}' for k, v in attrs.items())
        return f"{self.__class__.__name__}({attrs_str})"

    def __hash__(self, resolution: Optional[str] = None) -> int:
        resolution = resolution or self.hash_resolution
        if resolution == "default":
            return hash(self.id)
        elif resolution == "entities":
            entity_hashes = tuple(hash(entity) for entity in self.entities)
            return hash((self.id, entity_hashes))
        elif resolution == "full":
            entity_hashes = tuple(hash(entity) for entity in self.entities)
            return hash((self.id, entity_hashes, self.blocks_movement.value, self.blocks_light.value))
        else:
            raise ValueError(f"Invalid resolution level: {resolution}")
            

class AmbiguousEntityError(BaseModel):
    """
    Represents an error that occurs when multiple entities match the specified criteria.
    Attributes:
        entity_type (Type[GameEntity]): The type of the entity.
        entity_id (Optional[str]): The ID of the entity, if provided.
        entity_name (Optional[str]): The name of the entity, if provided.
        attributes (Optional[Dict[str, Any]]): Additional attributes used for matching, if provided.
        matching_entities (List[GameEntity]): The list of entities that match the specified criteria.
        missing_attributes (List[str]): The list of attributes that could have been used to disambiguate the entities.
    """
    entity_type: Type[GameEntity]
    entity_id: Optional[str] = None
    entity_name: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    matching_entities: List[GameEntity]
    missing_attributes: List[str]

    def get_error_message(self) -> str:
        return f"Ambiguous entity: {self.entity_type.__name__}, Matching entities: {len(self.matching_entities)}, Missing attributes: {', '.join(self.missing_attributes)}"

---

## payloads

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

---

## procedural

from abstractions.goap.spatial import GameEntity, Node, Position, GridMap, ActionsPayload, ActionInstance, ActionsResults, Path, BlocksMovement, BlocksLight
from typing import List, Dict, Any, Optional
import random

def create_room(grid_map, top_left, width, height):
    for x in range(top_left[0], top_left[0] + width):
        for y in range(top_left[1], top_left[1] + height):
            grid_map.get_node((x, y)).reset()
            floor = GameEntity(name=f"Floor_{x}_{y}", blocks_movement=BlocksMovement(value=False), blocks_light=BlocksLight(value=False))
            grid_map.get_node((x, y)).add_entity(floor)

def create_h_corridor(grid_map, x1, x2, y):
    for x in range(min(x1, x2), max(x1, x2) + 1):
        grid_map.get_node((x, y)).reset()
        floor = GameEntity(name=f"Floor_{x}_{y}", blocks_movement=BlocksMovement(value=False), blocks_light=BlocksLight(value=False))
        grid_map.get_node((x, y)).add_entity(floor)

def create_v_corridor(grid_map, y1, y2, x):
    for y in range(min(y1, y2), max(y1, y2) + 1):
        grid_map.get_node((x, y)).reset()
        floor = GameEntity(name=f"Floor_{x}_{y}", blocks_movement=BlocksMovement(value=False), blocks_light=BlocksLight(value=False))
        grid_map.get_node((x, y)).add_entity(floor)

def generate_dungeon(grid_map, num_rooms, min_room_size, max_room_size):
    rooms = []
    for _ in range(num_rooms):
        width = random.randint(min_room_size, max_room_size)
        height = random.randint(min_room_size, max_room_size)
        x = random.randint(1, grid_map.width - width - 1)
        y = random.randint(1, grid_map.height - height - 1)
        create_room(grid_map, (x, y), width, height)
        rooms.append((x, y, width, height))
    for i in range(len(rooms) - 1):
        x1, y1, w1, h1 = rooms[i]
        x2, y2, w2, h2 = rooms[i + 1]
        if random.random() < 0.5:
            create_h_corridor(grid_map, x1 + w1, x2, y1 + h1 // 2)
            create_v_corridor(grid_map, y1 + h1 // 2, y2 + h2 // 2, x2)
        else:
            create_v_corridor(grid_map, y1 + h1 // 2, y2, x1 + w1 // 2)
            create_h_corridor(grid_map, x1 + w1 // 2, x2 + w2 // 2, y2)

---

## shapes

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

---

## spatial

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
            blocking_point = point
            return False, visible_points, blocking_point
        else:
            visible_points.append(point)
    return True, visible_points, None

---

## textstate

from typing import List, Dict, Any, Tuple
from pydantic import BaseModel
from abstractions.goap.payloads import ActionResult, ActionsResults
from abstractions.goap.gridmap import GridMap
from abstractions.goap.shapes import Radius, Shadow, RayCast, Path, Rectangle

class TextStateModel(BaseModel):
    def to_text(self, use_egocentric: bool = False, resolution: str = "default") -> str:
        raise NotImplementedError("Subclasses must implement the to_text method")

class ActionResultTextState(TextStateModel):
    action_result: ActionResult

    def to_text(self, use_egocentric: bool = False, resolution: str = "default") -> str:
        action_name = self.action_result.action_instance.action.__class__.__name__
        source_before = self.action_result.state_before["source"].copy()
        target_before = self.action_result.state_before["target"].copy()
        source_before_position = source_before.pop("position")
        target_before_position = target_before.pop("position")
        if use_egocentric:
            source_before_position = self._to_egocentric_coordinates(source_before_position[0], source_before_position[1], self.action_result.state_before["source"]["position"])
            target_before_position = self._to_egocentric_coordinates(target_before_position[0], target_before_position[1], self.action_result.state_before["source"]["position"])
        source_before_state = self._format_entity_state(source_before, resolution)
        target_before_state = self._format_entity_state(target_before, resolution)
        if self.action_result.success:
            result_text = "Success"
            source_after = self.action_result.state_after["source"].copy()
            target_after = self.action_result.state_after["target"].copy()
            source_after_position = source_after.pop("position")
            target_after_position = target_after.pop("position")
            if use_egocentric:
                source_after_position = self._to_egocentric_coordinates(source_after_position[0], source_after_position[1], self.action_result.state_before["source"]["position"])
                target_after_position = self._to_egocentric_coordinates(target_after_position[0], target_after_position[1], self.action_result.state_before["source"]["position"])
            source_after_state = self._format_entity_state(source_after, resolution)
            target_after_state = self._format_entity_state(target_after, resolution)
            return f"Action: {action_name}\nSource Before: {source_before_state}\nSource Before Position: {source_before_position}\nTarget Before: {target_before_state}\nTarget Before Position: {target_before_position}\nResult: {result_text}\nSource After: {source_after_state}\nSource After Position: {source_after_position}\nTarget After: {target_after_state}\nTarget After Position: {target_after_position}\n"
        else:
            result_text = "Failure"
            error = self.action_result.error
            failed_prerequisites_text = "\n".join(self.action_result.failed_prerequisites)
            return f"Action: {action_name}\nSource Before: {source_before_state}\nSource Before Position: {source_before_position}\nTarget Before: {target_before_state}\nTarget Before Position: {target_before_position}\nResult: {result_text}\nError: {error}\nFailed Prerequisites:\n{failed_prerequisites_text}\n"

    def _to_egocentric_coordinates(self, x: int, y: int, source_position: Tuple[int, int]) -> Tuple[int, int]:
        source_x, source_y = source_position
        return x - source_x, y - source_y

    def _format_entity_state(self, state: Dict[str, Any], resolution: str) -> str:
        if resolution == "default":
            formatted_state = ", ".join(f"{key}: {value}" for key, value in state.items() if key != "inventory")
        elif resolution == "attributes":
            formatted_state = ", ".join(f"{key}: {value}" for key, value in state.items() if key != "inventory" and key != "node")
        elif resolution == "inventory":
            formatted_state = ", ".join(f"{key}: {value}" for key, value in state.items())
        else:
            raise ValueError(f"Invalid resolution: {resolution}")
        return f"{{{formatted_state}}}"

class ActionsResultsTextState(TextStateModel):
    actions_results: ActionsResults

    def to_text(self, use_egocentric: bool = False, resolution: str = "default") -> str:
        timesteps = []
        current_timestep = []
        for result in self.actions_results.results:
            if result.success:
                current_timestep.append(result)
            else:
                if current_timestep:
                    timestep_text = self._format_timestep(current_timestep, use_egocentric, resolution)
                    timesteps.append(timestep_text)
                    current_timestep = []
                failure_text = self._format_failure(result, use_egocentric, resolution)
                timesteps.append(failure_text)
        if current_timestep:
            timestep_text = self._format_timestep(current_timestep, use_egocentric, resolution)
            timesteps.append(timestep_text)
        return "\n".join(timesteps)

    def _format_timestep(self, timestep: List[ActionResult], use_egocentric: bool, resolution: str) -> str:
        action_states = []
        for i, result in enumerate(timestep, start=1):
            action_state = f"Action {i}:\n{ActionResultTextState(action_result=result).to_text(use_egocentric, resolution)}"
            action_states.append(action_state)
        timestep_text = f"Timestep:\n{''.join(action_states)}"
        return timestep_text

    def _format_failure(self, failure: ActionResult, use_egocentric: bool, resolution: str) -> str:
        failure_text = f"Failure:\n{ActionResultTextState(action_result=failure).to_text(use_egocentric, resolution)}"
        return failure_text

class ShadowTextState(TextStateModel):
    shadow: Shadow

    def to_text(self, use_egocentric: bool = False, resolution: str = "default") -> str:
        groups = {}
        for node in self.shadow.nodes:
            entity_types, entity_attributes = node._get_entity_info()
            group_key = (tuple(entity_types), tuple(sorted(entity_attributes)))
            if group_key not in groups:
                groups[group_key] = []
            position = self._to_egocentric_coordinates(node.position.x, node.position.y) if use_egocentric else (node.position.x, node.position.y)
            groups[group_key].append(position)
        group_strings_summarized = []
        for (entity_types, entity_attributes), positions in groups.items():
            summarized_positions = self._summarize_positions(positions)
            group_strings_summarized.append(f"Entity Types: {list(entity_types)}, Attributes: {list(entity_attributes)}, Positions: {summarized_positions}")
        summarized_output = '\n'.join(group_strings_summarized)
        light_blocking_groups = [group_key for group_key in groups if any(attr[0] == 'BlocksLight' and attr[1] for attr in group_key[1])]
        movement_blocking_groups = [group_key for group_key in groups if any(attr[0] == 'BlocksMovement' and attr[1] for attr in group_key[1])]
        if light_blocking_groups:
            light_blocking_info = f"Light Blocking Groups: {', '.join(str(group) for group in light_blocking_groups)}"
            summarized_output += f"\n{light_blocking_info}"
        if movement_blocking_groups:
            movement_blocking_info = f"Movement Blocking Groups: {', '.join(str(group) for group in movement_blocking_groups)}"
            summarized_output += f"\n{movement_blocking_info}"
        return summarized_output

    def _to_egocentric_coordinates(self, x: int, y: int) -> Tuple[int, int]:
        source_x, source_y = self.shadow.source.position.value
        return x - source_x, y - source_y

    def _summarize_positions(self, positions: List[Tuple[int, int]]) -> str:
        if not positions:
            return ""

        min_x = min(x for x, _ in positions)
        min_y = min(y for _, y in positions)
        max_x = max(x for x, _ in positions)
        max_y = max(y for _, y in positions)

        grid = [[0] * (max_x - min_x + 1) for _ in range(max_y - min_y + 1)]
        for x, y in positions:
            grid[y - min_y][x - min_x] = 1

        def find_largest_rectangle(grid):
            if not grid or not grid[0]:
                return 0, 0, 0, 0

            rows = len(grid)
            cols = len(grid[0])
            max_area = 0
            max_rect = (0, 0, 0, 0)

            for i in range(rows):
                for j in range(cols):
                    if grid[i][j] == 1:
                        width = 1
                        height = 1
                        while j + width < cols and all(grid[i][j + width] == 1 for i in range(i, rows)):
                            width += 1
                        while i + height < rows and all(grid[i + height][j] == 1 for j in range(j, j + width)):
                            height += 1
                        area = width * height
                        if area > max_area:
                            max_area = area
                            max_rect = (j, i, width, height)

            return max_rect

        rectangles = []
        while any(1 in row for row in grid):
            x, y, width, height = find_largest_rectangle(grid)
            rectangles.append((x + min_x, y + min_y, width, height))
            for i in range(y, y + height):
                for j in range(x, x + width):
                    grid[i][j] = 0

        summarized = []
        for x, y, width, height in rectangles:
            if width == 1 and height == 1:
                summarized.append(f"({x}, {y})")
            elif width == 1:
                summarized.append(f"({x}, {y}:{y + height})")
            elif height == 1:
                summarized.append(f"({x}:{x + width}, {y})")
            else:
                summarized.append(f"({x}:{x + width}, {y}:{y + height})")

        remaining_positions = [(x, y) for x, y in positions if not any(x >= rx and x < rx + rw and y >= ry and y < ry + rh for rx, ry, rw, rh in rectangles)]
        if remaining_positions:
            summarized.extend(f"({x}, {y})" for x, y in remaining_positions)

        return ", ".join(summarized)


class GridMapTextState(TextStateModel):
    rectangle: Rectangle

    def to_text(self, use_egocentric: bool = False, resolution: str = "default") -> str:
        text_state = []
        text_state.append(f"Grid Map (Width: {self.rectangle.width}, Height: {self.rectangle.height})")
        text_state.append(self._format_nodes(use_egocentric, resolution))
        text_state.append(self._format_entities(use_egocentric, resolution))
        text_state.append(self._format_shapes(use_egocentric, resolution))
        return "\n".join(text_state)

    def _format_nodes(self, use_egocentric: bool, resolution: str) -> str:
        nodes_text = []
        for y in range(self.rectangle.height):
            row = []
            for x in range(self.rectangle.width):
                node_position = (self.rectangle.top_left[0] + x, self.rectangle.top_left[1] + y)
                node = next((node for node in self.rectangle.nodes if node.position.value == node_position), None)
                if node:
                    if node.blocks_movement.value:
                        row.append("# ")
                    else:
                        row.append(". ")
                else:
                    row.append("  ")
            nodes_text.append("".join(row))
        return "Nodes:\n" + "\n".join(nodes_text)

    def _format_entities(self, use_egocentric: bool, resolution: str) -> str:
        entities_text = []
        for node in self.rectangle.nodes:
            for entity in node.entities:
                if use_egocentric:
                    entity_position = self._to_egocentric_coordinates(entity.position.value[0], entity.position.value[1], self.rectangle.top_left)
                else:
                    entity_position = entity.position.value
                entity_text = f"{entity.__class__.__name__} (ID: {entity.id}, Position: {entity_position})"
                if resolution != "default":
                    entity_text += f", State: {entity.__repr__(resolution)}"
                entities_text.append(entity_text)
        return "Entities:\n" + "\n".join(entities_text)

    def _format_shapes(self, use_egocentric: bool, resolution: str) -> str:
        shapes_text = []
        for shape in [Radius, Shadow, RayCast, Path]:
            shape_instances = [instance for instance in self.rectangle.nodes if isinstance(instance, shape)]
            if shape_instances:
                shape_text = f"{shape.__name__}:\n"
                for instance in shape_instances:
                    shape_text += f"  {instance.__repr__(resolution)}\n"
                shapes_text.append(shape_text)
        return "Shapes:\n" + "".join(shapes_text)

    def _to_egocentric_coordinates(self, x: int, y: int, top_left: Tuple[int, int]) -> Tuple[int, int]:
        top_left_x, top_left_y = top_left
        return x - top_left_x, y - top_left_y

---

