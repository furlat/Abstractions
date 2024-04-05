import random
from typing import List, Dict, Any, Optional, Tuple, Union
from pydantic import BaseModel, Field, conlist
from abstractions.goap.entity import Statement
from abstractions.goap.spatial import GridMap, Node, GameEntity, ActionResult, ActionsPayload, SummarizedActionPayload, SummarizedEgoActionPayload
from abstractions.goap.interactions import MoveStep, PickupAction, DropAction, OpenAction, CloseAction, UnlockAction, LockAction
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
                            action_name="MoveStep",
                            source_entity_type="Character",
                            source_entity_position=[0, 0],
                            target_entity_type="Floor",
                            target_entity_position=list(target_position)
                        )
                    else:
                        move_action = SummarizedEgoActionPayload(
                            action_name="MoveStep",
                            source_entity_type="Character",
                            source_entity_position=(0, 0),
                            target_entity_type="Floor",
                            target_entity_position=target_position
                        )
                else:
                    if self.use_outlines:
                        move_action = OutlinesActionPayload(
                            action_name="MoveStep",
                            source_entity_type="Character",
                            source_entity_position=list(current_position),
                            target_entity_type="Floor",
                            target_entity_position=list(target_position)
                        )
                    else:
                        move_action = SummarizedActionPayload(
                            action_name="MoveStep",
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