from typing import Optional, Tuple, List
from abstractions.goap.spatial import GameEntity, Node, GridMap, ActionsPayload, ActionInstance, Path
from abstractions.goap.interactions import Character, MoveStep, PickupAction, DropAction, TestItem
import pygame
from abstractions.goap.game.renderer import CameraControl
from pydantic import BaseModel, ValidationInfo, field_validator

class ActiveEntities(BaseModel):
    controlled_entity_id: Optional[str] = None
    targeted_entity_id: Optional[str] = None
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
    def __init__(self, grid_map: GridMap):
        self.grid_map = grid_map
        self.active_entities = ActiveEntities()
        self.mouse_highlighted_node: Optional[Node] = None
        self.camera_control = CameraControl()
        self.actions_payload = ActionsPayload(actions=[])
        

    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            self.handle_keypress(event.key)
        elif event.type == pygame.MOUSEMOTION:
            self.handle_mouse_motion(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self.handle_mouse_click(event.button, event.pos)

    def handle_keypress(self, key):
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

  
    def generate_drop_action(self):
        player_id = self.active_entities.controlled_entity_id
        player = GameEntity.get_instance(player_id)
        if player.inventory:
            item_to_drop = player.inventory[-1]  # Drop the last item in the inventory
            drop_action = ActionInstance(source_id=player_id, target_id=item_to_drop.id, action=DropAction())
            self.actions_payload.actions.append(drop_action)

    def handle_mouse_motion(self, pos, camera_pos, cell_size):
        self.mouse_highlighted_node = self.get_node_at_pos(pos, camera_pos, cell_size)

    def handle_mouse_click(self, button, pos, camera_pos, cell_size):
        if button == 1:  # Left mouse button
            clicked_node = self.get_node_at_pos(pos, camera_pos, cell_size)
            if clicked_node:
                self.active_entities.targeted_node_id = clicked_node.id
                self.active_entities.targeted_entity_id = self.get_next_entity_at_node(clicked_node).id if self.get_next_entity_at_node(clicked_node) else None
                player_id = self.active_entities.controlled_entity_id
                player = GameEntity.get_instance(player_id)
                if clicked_node == player.node or clicked_node in player.node.neighbors():
                    for entity in clicked_node.entities:
                        if isinstance(entity, TestItem):
                            pickup_action = ActionInstance(source_id=player_id, target_id=entity.id, action=PickupAction())
                            self.actions_payload.actions.append(pickup_action)
        elif button == 3:  # Right mouse button
            clicked_node = self.get_node_at_pos(pos, camera_pos, cell_size)
            if clicked_node:
                self.generate_move_to_target(clicked_node)


    def get_node_at_pos(self, pos, camera_pos, cell_size) -> Optional[Node]:
        # Convert screen coordinates to grid coordinates
        grid_x = camera_pos[0] + pos[0] // cell_size
        grid_y = camera_pos[1] + pos[1] // cell_size

        # Check if the grid coordinates are within the grid map bounds
        if 0 <= grid_x < self.grid_map.width and 0 <= grid_y < self.grid_map.height:
            return self.grid_map.get_node((grid_x, grid_y))
        return None

    def get_next_entity_at_node(self, node: Node) -> Optional[GameEntity]:
        for entity in node.entities:
            return entity
        return None

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
                        move_action = ActionInstance(source_id=controlled_entity_id, target_id=target_id, action=MoveStep())
                        return ActionsPayload(actions=[move_action])
        return None

    @staticmethod
    def generate_move_to_target(controlled_entity_id: str, target_node: Node, grid_map: GridMap) -> Optional[ActionsPayload]:
        if controlled_entity_id:
            controlled_entity = GameEntity.get_instance(controlled_entity_id)
            start_node = controlled_entity.node
            path = grid_map.a_star(start_node, target_node)
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
                move_action = ActionInstance(source_id=controlled_entity_id, target_id=target_id, action=MoveStep())
                move_actions.append(move_action)
        return move_actions
