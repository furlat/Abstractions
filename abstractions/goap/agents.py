import random
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from abstractions.goap.entity import Statement
from abstractions.goap.spatial import GridMap, Node, GameEntity, ActionResult, ActionsPayload, SummarizedActionPayload
from abstractions.goap.interactions import MoveStep, PickupAction, DropAction, OpenAction, CloseAction, UnlockAction, LockAction
from abstractions.goap.game.main import generate_dungeon
import outlines
from abc import ABC, abstractmethod

class MemoryInstance(BaseModel):
    observation: str
    action: Optional[SummarizedActionPayload] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    notes: Optional[str] = None

class MemorySequence(BaseModel):
    entries: List[MemoryInstance] = Field(default_factory=list)
    notes: Optional[str] = None

    def add_entry(self, entry: MemoryInstance):
        self.entries.append(entry)

    def get_recent_entries(self, count: int) -> List[MemoryInstance]:
        return self.entries[-count:]

    def summarize(self) -> str:
        summaries = []
        for entry in self.entries:
            summary = f"Observation: {entry.observation}\n"
            if entry.action:
                summary += f"Action: {entry.action.model_dump()}\n"
            if entry.result:
                summary += f"Result: {entry.result}\n"
            if entry.error:
                summary += f"Error: {entry.error}\n"
            if entry.notes:
                summary += f"Notes: {entry.notes}\n"
            summaries.append(summary)
        if self.notes:
            summaries.append(f"Sequence Notes: {self.notes}")
        return "\n".join(summaries)

class AgentGoal(BaseModel):
    statement: Statement
    priority: int

class RunMetadata(BaseModel):
    character_id: str
    run_number: int

class AbcAgent(ABC):
    def __init__(self, grid_map: GridMap, character_id: str):
        self.grid_map = grid_map
        self.character_id = character_id

    @abstractmethod
    def generate_action(self, shadow_payload: str) -> Optional[SummarizedActionPayload]:
        pass

class FakeLLM(AbcAgent):
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
        target_position = (x + dx, y + dy)
        target_node = self.grid_map.get_node(target_position)
        if target_node:
            floor_entities = [entity for entity in target_node.entities if entity.name.startswith("Floor")]
            if floor_entities:
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

class LLMAgent(AbcAgent):
    def __init__(self, grid_map: GridMap, character_id: str, model_path: str):
        super().__init__(grid_map, character_id)
        self.model = outlines.models.llamacpp(model_path, device="cuda")
        self.generator = outlines.generate.json(self.model, SummarizedActionPayload)

    @outlines.prompt
    def system_prompt(self, registered_actions):
        """
        You are an agent in a turn-based game world. The game takes place on a grid-based map, where each node can contain various entities, such as characters, items, and obstacles.
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
        - The positions in the Shadow payload are compressed to save space.
        - The positions are grouped by entity equivalence classes, where all positions with the same set of entities are reported together.
        Game Flow:
        - The game progresses in turns, and you can take one action per turn.
        - After each action, you will receive an updated observation reflecting the changes in the game world.
        - Your goal is to make decisions and take actions based on your observations to achieve the desired objectives.
        Action Generation:
        - To take an action, you need to generate an action payload that specifies the action name, the source entity (yourself), and the target entity (if applicable).
        - The action payload should conform to the structure defined by the game engine's registered actions.
        - If the action is valid and successfully executed, you will receive an ActionResult object with the updated game state.
        - If the action is invalid or cannot be executed, you will receive an ActionConversionError object with details about the error.
        Remember to carefully consider your observations, goals, and the available actions when making decisions. Good luck!
        """

    @outlines.prompt
    def action_generation_prompt(self, shadow_payload, goals, memory_summary):
        """
        Current Observation:
        {{ shadow_payload }}
        Goals:
        {% for goal in goals %}
        - {{ goal.statement }}: (Priority: {{ goal.priority }})
        {% endfor %}
        Memory Summary:
        {{ memory_summary }}
        Based on the current observation, your goals, and memory, what action do you want to take next?
        Respond with a valid action payload following the structure defined by the game engine's registered actions.
        """

    def generate_action(self, shadow_payload: str) -> Optional[SummarizedActionPayload]:
        system_prompt_text = self.system_prompt(self.grid_map.get_actions())
        action_prompt_text = self.action_generation_prompt(
            shadow_payload,
            self.goals,
            self.memory.summarize()
        )
        prompt_text = f"{system_prompt_text}\n\n{action_prompt_text}"
        action_payload_json = self.generator(prompt_text)
        action_payload = SummarizedActionPayload.model_validate_json(action_payload_json)
        return action_payload

class CharacterAgent:
    def __init__(self, grid_map: GridMap, agent: AbcAgent):
        self.grid_map = grid_map
        self.agent = agent
        self.memory = MemorySequence()
        self.goals: List[AgentGoal] = []
        self.metadata: RunMetadata = None

    def set_goals(self, goals: List[AgentGoal]):
        self.goals = goals

    def update_memory_notes(self, notes: str):
        self.memory.notes = notes

    def update_instance_notes(self, notes: str):
        if self.memory.entries:
            self.memory.entries[-1].notes = notes

    def set_metadata(self, metadata: RunMetadata):
        self.metadata = metadata

    def generate_action(self, shadow_payload: str) -> Optional[SummarizedActionPayload]:
        return self.agent.generate_action(shadow_payload)

    def process_action_result(self, shadow_payload: str, action_payload: Optional[SummarizedActionPayload], result: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
        memory_instance = MemoryInstance(
            observation=shadow_payload,
            action=action_payload,
            result=result,
            error=error
        )
        self.memory.add_entry(memory_instance)

    def run(self, initial_observation: str):
        observation = initial_observation
        step_count = 0
        while True:
            print(f"\n--- Step: {step_count} ---")
            action_payload = self.generate_action(observation)
            print(f"Generated Action: {action_payload}")
            result, error = self.execute_action(action_payload)
            self.process_action_result(observation, action_payload, result, error)
            if error:
                print(f"Error: {error}")
            if result:
                print("Action Result:")
                print(f"  State Before: {result['state_before']}")
                print(f"  State After: {result['state_after']}")
            observation = self.get_current_observation()
            if self.check_goal_achieved():
                print("Goal achieved! in step: ", step_count)
                break
            step_count += 1

    def execute_action(self, action_payload: Optional[SummarizedActionPayload]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        if action_payload:
            action_result = self.grid_map.convert_summarized_payload(action_payload)
            if isinstance(action_result, ActionsPayload):
                actions_results = self.grid_map.apply_actions_payload(action_result)
                if actions_results.results:
                    action_result = actions_results.results[0]
                    result = {
                        "state_before": action_result.state_before,
                        "state_after": action_result.state_after
                    }
                    return result, None
                else:
                    error = "Action execution failed"
                    return None, error
            else:
                error = str(action_result)
                return None, error
        else:
            return None, None

    def get_current_position(self) -> Tuple[int, int]:
        character_entity = self.get_character_entity()
        if character_entity and character_entity.node:
            return character_entity.node.position.value
        return None

    def get_current_observation(self) -> str:
        character_entity = self.get_character_entity()
        if character_entity and character_entity.node:
            shadow = self.grid_map.get_shadow(character_entity.node, max_radius=10)
            observation = shadow.to_entity_groups(use_egocentric=False)
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