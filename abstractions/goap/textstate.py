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