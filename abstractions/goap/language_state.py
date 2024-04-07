from typing import Optional, Tuple, List, Dict, Any, Union
from abstractions.goap.entity import Entity, Statement, Attribute
from abstractions.goap.shapes import Shadow, Path, Radius,Rectangle, RayCast, BlockedRaycast
from abstractions.goap.gridmap import GridMap
from abstractions.goap.nodes import Node, GameEntity, BlocksMovement, BlocksLight
from abstractions.goap.spatial import WalkableGraph
from abstractions.goap.interactions import Character, Door, Key, Treasure, Floor, Wall, InanimateEntity, IsPickupable, TestItem, OpenAction, CloseAction, UnlockAction, LockAction, PickupAction, DropAction, MoveStep
from abstractions.goap.game.main import generate_dungeon
from abstractions.goap.payloads import ActionsPayload, ActionInstance, ActionResult
from pydantic import BaseModel
from abstractions.goap.actions import Prerequisites, Consequences, Goal

class GoalState:
    def __init__(self, character_id: str):
        self.character_id = character_id
        self.goals: List[Goal] = []

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
    def __init__(self, action_result: ActionResult):
        self.action_result = action_result

    def generate_analysis(self) -> str:
        if self.action_result.success:
            return self._generate_success_analysis()
        else:
            return self._generate_failure_analysis()

    def _generate_success_analysis(self) -> str:
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