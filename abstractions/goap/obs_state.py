from typing import Optional, Tuple, List, Dict, Any
from abstractions.goap.shapes import Shadow
from abstractions.goap.gridmap import GridMap
from abstractions.goap.nodes import Node, GameEntity, BlocksMovement, BlocksLight
from abstractions.goap.spatial import WalkableGraph
from abstractions.goap.interactions import Character, Door, Key, Treasure, Floor, Wall, InanimateEntity, IsPickupable, TestItem, OpenAction, CloseAction, UnlockAction, LockAction, PickupAction, DropAction, MoveStep
from abstractions.goap.game.main import generate_dungeon

class ObservationState:
    def __init__(self, character_id: str, config: Dict[str, bool]):
        self.character_id = character_id
        self.config = config
        self.paths = {}

    def generate(self, shadow: Shadow) -> str:
        observation_message = self._generate_introduction(self.config)

        if self.config.get("character_summary", True):
            character_summary = self._generate_character_summary(self.character_id)
            observation_message += f"# Character Summary\n{character_summary}\n\n"

        if self.config.get("visibility_matrix", True):
            visibility_matrix, dimensions = self._generate_visibility_matrix(shadow, self.character_id)
            observation_message += f"# Visibility Matrix ({dimensions[0]}x{dimensions[1]} Grid)\n{visibility_matrix}\n\n"

        if self.config.get("movement_matrix", True):
            movement_matrix, dimensions = self._generate_movement_matrix(shadow, self.character_id)
            observation_message += f"# Movement Matrix ({dimensions[0]}x{dimensions[1]} Grid)\n{movement_matrix}\n\n"

        if self.config.get("path_matrix", True):
            path_matrix, dimensions, self.paths = self._generate_path_matrix(shadow, self.character_id)
            observation_message += f"# Path Matrix ({dimensions[0]}x{dimensions[1]} Grid)\n{path_matrix}\n\n"

        if self.config.get("immediate_neighbors", True):
            immediate_neighbors = self._generate_immediate_neighbors(shadow, self.character_id)
            observation_message += f"# Immediate Neighbors (3x3 Grid)\n{immediate_neighbors}\n\n"

        if self.config.get("node_equivalence_classes", True):
            node_equivalence_classes = self._generate_node_equivalence_classes(shadow)
            observation_message += f"# Node Equivalence Classes\n{node_equivalence_classes}\n\n"

        if self.config.get("living_entities", True):
            living_entities = self._generate_living_entities(shadow)
            observation_message += f"# Living Entities\n{living_entities}\n\n"

        if self.config.get("movement_sub_goal", True):
            movement_sub_goal = self._generate_movement_sub_goal()
            observation_message += f"# Movement Sub-Goal\n{movement_sub_goal}\n\n"

        if self.config.get("attribute_summary", True):
            attribute_summary = self._generate_attribute_summary(shadow)
            observation_message += f"# Attribute Summary\n{attribute_summary}\n\n"

        if self.config.get("pathfinding_information", True):
            pathfinding_information = self._generate_pathfinding_information()
            observation_message += f"# Pathfinding Information\n{pathfinding_information}\n\n"

        if self.config.get("cognitive_insights", True):
            cognitive_insights = self._generate_cognitive_insights(shadow)
            observation_message += f"# Cognitive Insights\n{cognitive_insights}\n"

        return observation_message

    @staticmethod
    def _generate_introduction(config: Dict[str, bool]) -> str:
        introduction = "# Introduction\n"
        introduction += "This observation represents the current state of the game world from the character's perspective. It includes the following sections:\n\n"

        for method_name, enabled in config.items():
            if enabled:
                method = getattr(ObservationState, f"_generate_{method_name}")
                description = method.__doc__.strip() if method.__doc__ else "No description available."
                introduction += f"- {method_name.replace('_', ' ').title()}: {description}\n"

        return introduction

    @staticmethod
    def _generate_character_summary(character_id: str) -> str:
        """
        Provides an overview of the character's position and key attributes.
        """
        character = GameEntity.get_instance(character_id)
        if character is None:
            return "Character not found."

        position = character.position.value
        attack_power = character.get_attr("attack_power")
        health = character.get_attr("health")
        max_health = character.get_attr("max_health")
        can_act = character.get_attr("can_act")

        summary = f"Position: {position}\n"
        summary += f"Key Attributes:\n"
        summary += f"  - AttackPower: {attack_power}\n"
        summary += f"  - Health: {health}\n"
        summary += f"  - MaxHealth: {max_health}\n"
        summary += f"  - CanAct: {can_act}\n"

        return summary

    @staticmethod
    def _generate_visibility_matrix(shadow: Shadow, character_id: str) -> str:
        """
        Generates a matrix representing the visibility of the nodes in the shadow.
        """
        character = GameEntity.get_instance(character_id)
        if character is None:
            return "Character not found."

        character_node = character.node
        if character_node is None:
            return "Character is not in a node."

        grid_map = GridMap.get_instance(shadow.nodes[0].gridmap_id)
        if grid_map is None:
            return "Grid map not found."

        min_x = max(0, character_node.position.value[0] - shadow.max_radius)
        max_x = min(grid_map.width - 1, character_node.position.value[0] + shadow.max_radius)
        min_y = max(0, character_node.position.value[1] - shadow.max_radius)
        max_y = min(grid_map.height - 1, character_node.position.value[1] + shadow.max_radius)

        visibility_matrix = [["?" for _ in range(max_x - min_x + 1)] for _ in range(max_y - min_y + 1)]
        character_x, character_y = character_node.position.value
        visibility_matrix[character_y - min_y][character_x - min_x] = "c"

        for node in shadow.nodes:
            x = node.position.value[0] - min_x
            y = node.position.value[1] - min_y
            visibility_matrix[y][x] = "v" if not node.blocks_light.value else "x"
        visibility_matrix[character_y - min_y][character_x - min_x] = "c"
        visibility_matrix_str = "\n".join([" ".join(row) for row in visibility_matrix])
        return visibility_matrix_str, (max_y - min_y + 1, max_x - min_x + 1)

    @staticmethod
    def _generate_movement_matrix(shadow: Shadow, character_id: str) -> str:
        """
        Generates a matrix representing the movement blocking of the nodes in the shadow.
        """
        character = GameEntity.get_instance(character_id)
        if character is None:
            return "Character not found."

        character_node = character.node
        if character_node is None:
            return "Character is not in a node."

        grid_map = GridMap.get_instance(shadow.nodes[0].gridmap_id)
        if grid_map is None:
            return "Grid map not found."

        min_x = max(0, character_node.position.value[0] - shadow.max_radius)
        max_x = min(grid_map.width - 1, character_node.position.value[0] + shadow.max_radius)
        min_y = max(0, character_node.position.value[1] - shadow.max_radius)
        max_y = min(grid_map.height - 1, character_node.position.value[1] + shadow.max_radius)

        movement_matrix = [["?" for _ in range(max_x - min_x + 1)] for _ in range(max_y - min_y + 1)]
        character_x, character_y = character_node.position.value
        movement_matrix[character_y - min_y][character_x - min_x] = "c"

        for node in shadow.nodes:
            x = node.position.value[0] - min_x
            y = node.position.value[1] - min_y
            movement_matrix[y][x] = "v" if not node.blocks_movement.value else "x"
        movement_matrix[character_y - min_y][character_x - min_x] = "c"
        movement_matrix_str = "\n".join([" ".join(row) for row in movement_matrix])
        return movement_matrix_str, (max_y - min_y + 1, max_x - min_x + 1)

    @staticmethod
    def _generate_path_matrix(shadow: Shadow, character_id: str) -> str:
        """
        Generates a matrix indicating the presence and length of paths from the character's position to each node in the shadow.
        """
        character = GameEntity.get_instance(character_id)
        if character is None:
            return "Character not found."

        character_node = character.node
        if character_node is None:
            return "Character is not in a node."

        grid_map = GridMap.get_instance(shadow.nodes[0].gridmap_id)
        if grid_map is None:
            return "Grid map not found."

        min_x = max(0, character_node.position.value[0] - shadow.max_radius)
        max_x = min(grid_map.width - 1, character_node.position.value[0] + shadow.max_radius)
        min_y = max(0, character_node.position.value[1] - shadow.max_radius)
        max_y = min(grid_map.height - 1, character_node.position.value[1] + shadow.max_radius)

        path_matrix = [["?" for _ in range(max_x - min_x + 1)] for _ in range(max_y - min_y + 1)]
        character_x, character_y = character_node.position.value
        path_matrix[character_y - min_y][character_x - min_x] = "c"

        paths = {}
        for node in shadow.nodes:
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
        return path_matrix_str, (max_y - min_y + 1, max_x - min_x + 1), paths



    @staticmethod
    def _generate_immediate_neighbors(shadow: Shadow, character_id: str) -> str:
        """
        Describes the 3x3 grid surrounding the character, including the node status and the entities present in each cell.
        """
        character = GameEntity.get_instance(character_id)
        if character is None:
            return "Character not found."

        character_node = character.node
        if character_node is None:
            return "Character is not in a node."

        neighbors = character_node.neighbors()
        immediate_neighbors_str = ""

        directions = ["NW", "N", "NE", "W", "C", "E", "SW", "S", "SE"]
        for direction in directions:
            if direction == "C":
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

            immediate_neighbors_str += f"- {direction} ({x}, {y}): {node_status}, Entities: {entities}\n"

        return immediate_neighbors_str

    @staticmethod
    def _get_direction_offset(direction: str) -> Tuple[int, int]:
        """
        Returns the offset in x and y coordinates for a given direction.
        """
        offsets = {
            "NW": (-1, -1),
            "N": (0, -1),
            "NE": (1, -1),
            "W": (-1, 0),
            "E": (1, 0),
            "SW": (-1, 1),
            "S": (0, 1),
            "SE": (1, 1)
        }
        return offsets[direction]

    @staticmethod
    def _generate_node_equivalence_classes(shadow: Shadow) -> str:
        """
        Groups similar nodes into equivalence classes based on the combination of entities they contain and their attributes, excluding living entities.
        """
        equivalence_classes = {}
        for node in shadow.nodes:
            entity_types = tuple(sorted(type(entity).__name__ for entity in node.entities if not isinstance(entity, Character)))
            entity_attributes = {}
            for entity in node.entities:
                if not isinstance(entity, Character):
                    entity_attributes[type(entity).__name__] = tuple(sorted((attr.name, attr.value) for attr in entity.all_attributes().values()))
            key = (entity_types, tuple(sorted(entity_attributes.items())))
            if key not in equivalence_classes:
                equivalence_classes[key] = []
            equivalence_classes[key].append(node)

        equivalence_classes_str = ""
        for (entity_types, entity_attributes), nodes in equivalence_classes.items():
            equivalence_classes_str += f"- {', '.join(entity_types)}:\n"
            equivalence_classes_str += f"  - Positions: {[node.position.value for node in nodes]}\n"
            for entity_type, attributes in entity_attributes:
                equivalence_classes_str += f"  - {entity_type} Attributes:\n"
                for attr_name, attr_value in attributes:
                    equivalence_classes_str += f"    - {attr_name}: {attr_value}\n"

        return equivalence_classes_str

    @staticmethod
    def _generate_living_entities(shadow: Shadow) -> str:
        """
        Provides information about the living entities in the visible area, excluding the character.
        """
        living_entities = [entity for node in shadow.nodes for entity in node.entities if isinstance(entity, Character) and entity.id != shadow.source.id]

        if not living_entities:
            return "No living entities in the visible area, excluding the character."

        living_entities_str = ""
        for entity in living_entities:
            living_entities_str += f"- {entity.name} (ID: {entity.id}, Position: {entity.position.value})\n"
            living_entities_str += f"  - Attributes:\n"
            for attr_name, attr_value in entity.all_attributes().items():
                living_entities_str += f"    - {attr_name}: {attr_value.value}\n"

        return living_entities_str

    @staticmethod
    def _generate_movement_sub_goal() -> str:
        """
        Specifies the character's current movement sub-goal, including the target position and a brief description.
        """
        # TODO: Implement movement sub-goal generation based on the character's current goal or objective
        return "Movement Sub-Goal: Not implemented yet."

    @staticmethod
    def _generate_attribute_summary(shadow: Shadow) -> str:
        """
        Summarizes the blocking properties of nodes in the visible area and their corresponding equivalence classes, ignoring living entities.
        """
        attribute_groups = {
            "Walkable and Visible": [],
            "Walkable and Not Visible": [],
            "Not Walkable and Visible": [],
            "Not Walkable and Not Visible": []
        }

        for node in shadow.nodes:
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

        attribute_summary = "# Nodes Spatial Attributes Summary (Ignoring Living Entities)\n"
        for group, equivalence_classes in attribute_groups.items():
            node_count = sum(1 for node in shadow.nodes if node.blocks_movement.value == (group.startswith("Not Walkable")) and node.blocks_light.value == (group.endswith("Not Visible")))
            attribute_summary += f"- {group}: {node_count} nodes\n"
            if equivalence_classes:
                for eq_class in equivalence_classes:
                    entities_str = ", ".join([f"{entity_type} ({', '.join([f'{attr_name}: {attr_value}' for attr_name, attr_value in attributes])})" for entity_type, attributes in eq_class])
                    attribute_summary += f"  - Equivalence Class: [{entities_str}]\n"
            else:
                attribute_summary += f"  - Equivalence Classes: None\n"

        return attribute_summary

    def _generate_pathfinding_information(self) -> str:
        """
        Generates pathfinding information for paths with length greater than 1.
        """
        pathfinding_info = ""
        for position, path in self.paths.items():
            if len(path.nodes) > 2:
                pathfinding_info += f"- Path to {position}: {' -> '.join(str(node.position.value) for node in path.nodes)}\n"
        if not pathfinding_info:
            pathfinding_info = "No paths with length greater than 1 found."
        return pathfinding_info

    @staticmethod
    def _generate_cognitive_insights(shadow: Shadow) -> str:
        """
        Offers high-level observations and insights about the game world and the character's current situation.
        """
        # TODO: Implement cognitive insights generation based on the current game state and character's situation
        return "Cognitive Insights: Not implemented yet."