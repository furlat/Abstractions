from typing import List, Dict, Any, Optional, Union, Type
from abstractions.goap.actions import Goal, Action
from typing import List, Dict, Any, Optional, Union, Type
from abstractions.goap.actions import Goal, Action
from abstractions.goap.nodes import GameEntity, Node
from abstractions.goap.shapes import Shadow, Radius, Rectangle
from abstractions.goap.language_state import ObservationState, ActionState, GoalState
from abstractions.goap.payloads import ActionsPayload, ActionInstance, ActionsResults, ActionResult
from abstractions.goap.gridmap import GridMap
from abstractions.goap.language_state import StrActionConverter
from abstractions.goap.errors import AmbiguousEntityError
import random
import typing

class Agent:
    def __init__(self, goals: List[Goal], character_id: str, actions: Dict[str, Action], entity_type_map: Dict[str, Type[GameEntity]], llm=None, generator_sampler=None):
        self.goals = goals
        self.character_id = character_id
        self.actions = actions
        self.entity_type_map = entity_type_map
        self.llm = llm
        self.generator_sampler = generator_sampler
        self.obs_state = ObservationState(character_id=character_id)
        self.action_state = ActionState()
        self.goal_state = GoalState(character_id=character_id, goals=goals)
        self.history = []
        self.system_prompt = self.setup_system_prompt()
        self.str_action_converter = StrActionConverter(actions=self.actions, entity_type_map=self.entity_type_map)

        if self.llm is not None and self.generator_sampler is not None:
            from outlines import models, generate
            self.llm = models.llama()  # Replace with the appropriate LLM model
            self.generator_sampler = generate.strings  # Replace with the appropriate generator sampler

    def setup_system_prompt(self) -> str:
        system_prompt = f"""
        You are an agent controlling a character in a grid-based game environment.
        Your goal is to navigate the environment, interact with objects, and achieve the specified goals.

        The game environment is represented by a grid of nodes, where each node can contain various entities such as characters, objects, and obstacles.
        You receive observations about your surroundings and the state of the game through the ObservationState.
        The ActionState keeps track of your previous actions and their results.
        The GoalState represents your current goals and objectives.

        Available actions:
        {', '.join(self.actions.keys())}

        Available entity types:
        {', '.join(self.entity_type_map.keys())}

        You should generate your actions based on the current observation, previous actions, and goals.
        The actions you generate should be in the format of "direction action target_type", for example: "North Move Floor" or "South Pickup Key".
        The action should be a valid combination of direction, action name, and target entity type based on your current state and surroundings.

        Remember to consider your goals and prioritize actions that help you achieve them.
        Good luck!
        """
        return system_prompt

    def receive_results_and_shape(self, actions_results: ActionsResults, shape: Union[Shadow, Radius, Rectangle]):
        self.obs_state.generate(shape)
        for result in actions_results.results:
            self.action_state.update_state(result)
        self.goal_state.generate(shape)
    def generate_action_strings(self) -> List[str]:
        directions = ["North", "South", "East", "West", "NorthEast", "NorthWest", "SouthEast", "SouthWest", "Center"]
        action_strings = []
        
        for direction in directions:
            for action_name in self.actions.keys():
                for type_name in self.entity_type_map.keys():
                    action_string = f"{direction} {action_name} {type_name}"
                    action_strings.append(action_string)
        
        return action_strings

    def update_generator_sampler(self):
        if self.llm is not None and self.generator_sampler is not None:
            if typing.TYPE_CHECKING:
                import outlines
            action_strings = self.generate_action_strings()
            self.generator_sampler = outlines.generate.strings(self.llm, action_strings)

    def generate_action(self, obs_state_text: str, action_state_text: str, goal_state_text: str) -> Optional[str]:
        if self.llm is None or self.generator_sampler is None:
            return self.generate_random_action()

        prompt = f"{self.system_prompt}\n\nObservation:\n{obs_state_text}\n\nAction:\n{action_state_text}\n\nGoal:\n{goal_state_text}\n\nNext Action:"
        
        action_string = self.generator_sampler(prompt)
        
        return action_string

    def generate_random_action(self) -> Optional[str]:
        action_strings = self.generate_action_strings()
        if action_strings:
            return random.choice(action_strings)
        return None

    def update_history(self, action_result: ActionResult, shape: Union[Shadow, Radius, Rectangle], action: str):
        self.history.append({
            "action_result": action_result,
            "shape": shape,
            "action": action
        })

    def convert_action_string(self, action_string: str) -> Union[str, Dict[str, Any]]:
        return self.str_action_converter.convert_action_string(action_string, self.character_id)
    
    def run(self, grid_map: GridMap, max_steps: Optional[int] = None, mdp: bool = True) -> None:
        step = 0
        action_result = None
        actions_results = ActionsResults(results=[])

        while True:
            print(f"\n--- Step {step} ---")

            if mdp:
                shape = grid_map.get_rectangle()
            else:
                character_node = GameEntity.get_instance(self.character_id).node
                shape = grid_map.get_shadow(source=character_node, max_radius=5)

            obs_state_text = self.obs_state.generate(shape)
            action_state_text = self.action_state.generate(action_result) if action_result else ""
            goal_state_text = self.goal_state.generate(shape)

            # print("Observation State:")
            # print(obs_state_text)
            print("\nAction State:")
            print(action_state_text)
            # print("\nGoal State:")
            # print(goal_state_text)

            action_string = self.generate_action(obs_state_text, action_state_text, goal_state_text)
            print("\nGenerated Action:")
            print(action_string)

            action_payload = self.convert_action_string(action_string)
            print("\nAction Payload:")
            print(action_payload)

            if isinstance(action_payload, str):
                print("Error:", action_payload)
                action_result = self.create_failed_action_result(action_string, action_payload)
            else:
                actions_results = grid_map.apply_actions_payload(action_payload)
                print("\nAction Results:")
                print(actions_results)

                if actions_results.results:
                    action_result = actions_results.results[0]
                else:
                    action_result = None

            self.update_history(action_result, shape, action_string)

            if self.check_goals_reached():
                print("\nAll goals reached!")
                break

            step += 1
            if max_steps is not None and step >= max_steps:
                print(f"\nMax steps ({max_steps}) reached.")
                break

    def create_failed_action_result(self, action_string: str, error_message: str) -> Optional[ActionResult]:
        action_parts = action_string.split(" ")
        if len(action_parts) == 3:
            direction, action_name, target_type = action_parts
            action_class = self.actions.get(action_name)
            if action_class:
                source_entity = GameEntity.get_instance(self.character_id)
                target_entity = self.find_target_entity(direction, target_type)

                state_before = {
                    "source": source_entity.get_state() if source_entity else {},
                    "target": target_entity.get_state() if target_entity else {}
                }

                action_instance = ActionInstance(source_id=self.character_id, target_id=target_entity.id if target_entity else "", action=action_class())
                return ActionResult(
                    action_instance=action_instance,
                    success=False,
                    error=error_message,
                    failed_prerequisites=[error_message],
                    state_before=state_before,
                    state_after={}
                )
        return None

    def find_target_entity(self, direction: str, target_type: str) -> Optional[GameEntity]:
        character_node = GameEntity.get_instance(self.character_id).node
        target_node = self.str_action_converter._get_target_node(character_node, direction)
        if target_node:
            target_entity_type = self.entity_type_map.get(target_type)
            if target_entity_type:
                target_entity = target_node.find_entity(entity_type=target_entity_type)
                if isinstance(target_entity, AmbiguousEntityError):
                    return None
                return target_entity
        return None


    def check_goals_reached(self) -> bool:
        for goal in self.goals:
            source_entity = GameEntity.get_instance(goal.source_entity_id)
            target_entity = GameEntity.get_instance(goal.target_entity_id) if goal.target_entity_id else None
            if not goal.prerequisites.is_satisfied(source_entity, target_entity):
                return False
        return True

