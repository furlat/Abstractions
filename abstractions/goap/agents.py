from typing import List, Dict, Any, Optional, Union, Type, Tuple
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
import outlines
from outlines import models, generate, samplers
from outlines.generate.api import SequenceGenerator



class Agent:
    def __init__(self, goals: List[Goal], character_id: str, actions: Dict[str, Action], entity_type_map: Dict[str, Type[GameEntity]], llm:Optional[str]=None):
        self.goals = goals
        self.character_id = character_id
        self.actions = actions
        self.entity_type_map = entity_type_map
        self.llm = llm
        self.obs_state = ObservationState(character_id=character_id)
        self.action_state = ActionState()
        self.action_log = []
        self.goal_state = GoalState(character_id=character_id, goals=goals)
        self.history = []
        self.system_prompt = self.setup_system_prompt()
        self.str_action_converter = StrActionConverter(actions=self.actions, entity_type_map=self.entity_type_map)
        self.action_strings = self.generate_action_strings()
        self.allowed_strings_count = {}
        if self.llm is not None:
            
            self.llm = models.llamacpp(llm, model_kwargs={"seed": 1337, "n_ctx": 30000, "n_gpu_layers": -1, "verbose": True})
            self.generator_dict = {Tuple[str,str,str]:SequenceGenerator}
            # self.generator_sampler =  generate.choice(self.llm, self.action_strings)
        

    def setup_system_prompt(self) -> str:
        system_prompt = f"""
        <|im_start|>system
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
        The actions you generate should be in the format of "direction action target_type".
        The action should be a valid combination of direction, action name, and target entity type based on your current state and surroundings.

        Remember to consider your goals and prioritize actions that help you achieve them. Remember that you can only perform actions that are valid based on the current state of the game.
        You can Move to Floor
        You can Pickup Key or Treasure
        You can Open or Unlock Door
        If a entity is not in your 3x3 neighborhood, you can't interact with it. and you will wast an action.
        The allowed directiosn are : North, South, East, West, NorthEast, NorthWest, SouthEast, SouthWest, Center
        Good luck!<|im_end|>system
        """
        return system_prompt

    def generate_text(self, shape: Union[Shadow, Radius, Rectangle],actions_results: Optional[ActionsResults] = None):
        obs_state_text = self.obs_state.generate(shape)
        act_obs = []
        act_state_text = None
        if actions_results:
            for result in actions_results.results:
                act_obs.append(self.action_state.update_state(result))
            act_state_text = "\n".join(act_obs)
        goal_state_text= self.goal_state.generate(shape)
        return obs_state_text, act_state_text, goal_state_text

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

    def generate_action_prompt(self, obs_state_text: str, action_state_text: str, goal_state_text: str) -> str:
        prompt = f"{self.system_prompt}\n<|im_start|>user\nObservation:\n{obs_state_text}\n\nAction(s) before:\n{action_state_text}\n\nGoal:\n{goal_state_text} <|im_end|>\n <|im_start|> After reviewing carefully the observation state, the result of the previous action and the current goal state I decided to take the action:" 
        return prompt

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

    
    def derive_direction_string_from_pos(self,source_pos: Tuple[int,int], target_pos: Tuple[int,int]) -> Optional[str]:
        delta_dict = {
            (0,-1): "North",
            (0,1): "South",
            (1,0): "East",
            (-1,0): "West",
            (1,-1): "NorthEast",
            (-1,-1): "NorthWest",
            (1,1): "SouthEast",
            (-1,1): "SouthWest",
            (0,0): "Center"
        }
        dx = target_pos[0] - source_pos[0]
        dy = target_pos[1] - source_pos[1]
        delta = (dx,dy)
        return delta_dict.get(delta,None)
    
    def derive_allowed_strings(self,grid_map: GridMap, radius: int = 1) -> List[str]:
        """ Derive the allowed strings based on the current state of the grid map and the character's position
        each string is in the format of "direction action target_type. The outputs of get_applicable_actions_in_neighborhood
        are in the format:
        [
            (node, [(entity, [action1, action2, ...]), ...]),
            ...
        ] with type hint:
        List[Tuple[Node, List[Tuple[GameEntity, List[Action]]]]]
        """
        banned_strings = ["Center Move Floor", "Center Move Character"]
        character = GameEntity.get_instance(self.character_id)
        allowed_actions = grid_map.get_applicable_actions_in_neighborhood(source=character,radius=radius)
        character_pos = character.position.value
        allowed_strings = []
        action_fstring_template = "{direction} {action_name} {entity_type}"
        for node, entity_list in allowed_actions:
            target_pos = node.position.value
            for entity, entity_action_list in entity_list:
                entity_type = entity.__class__.__name__
                for actiontype in entity_action_list:
                    action_name = actiontype.__class__.__name__
                    direction = self.derive_direction_string_from_pos(character_pos, target_pos)
                    if direction is not None:
                        str_out = action_fstring_template.format(direction=direction, action_name=action_name, entity_type=entity_type)
                        if str_out not in banned_strings:
                            allowed_strings.append(action_fstring_template.format(direction=direction, action_name=action_name, entity_type=entity_type))

        allowed_strings = sorted(allowed_strings)
        return allowed_strings  
       
    def generator_from_allowed_strings(self,allowed_strings: List[str]) -> str:
        """ return the generator object for the allowed strings, it uses a dictionary as cache to avoid recompiling generators for the same subsets of allowed strings"""
        if self.llm is not None:

            if self.generator_dict.get(tuple(allowed_strings)) is None:
                print(f"Generating generator for {allowed_strings}")
                self.generator_dict[tuple(allowed_strings)] = generate.choice(self.llm, allowed_strings,sampler=samplers.multinomial(top_k=1))
            return self.generator_dict[tuple(allowed_strings)]
    
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
            self.action_log.append(action_state_text)

            allowed_action_strings = self.derive_allowed_strings(grid_map)
            if self.allowed_strings_count.get(tuple(allowed_action_strings)) is None:
                self.allowed_strings_count[tuple(allowed_action_strings)] = 0
            self.allowed_strings_count[tuple(allowed_action_strings)] += 1
            if self.llm:
                generator_from_allowed_strings = self.generator_from_allowed_strings(allowed_action_strings)
                joined_action_log = "\n".join(self.action_log)
                prompt = self.generate_action_prompt(obs_state_text, joined_action_log, goal_state_text)
                action_string = generator_from_allowed_strings(prompt)
            else:
                action_string = random.choice(allowed_action_strings)
    

            # print("Observation State:")
            # print(obs_state_text)
            print("\nAction State:")
            print(action_state_text)
            # print("\nGoal State:")
            # print(goal_state_text)

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
                print(f"\nAll goals reached! in {step} steps.")
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

