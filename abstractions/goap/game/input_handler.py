from typing import Optional, Tuple, List
from abstractions.goap.spatial import GameEntity, Node, GridMap, ActionsPayload, ActionInstance, Path
from abstractions.goap.interactions import Character, MoveStep, PickupAction, DropAction, TestItem, Door, LockAction, UnlockAction, OpenAction, CloseAction
from abstractions.goap.actions import Action
from abstractions.goap.game.renderer import CameraControl
from abstractions.goap.game.payloadgen import SpriteMapping
from pydantic import BaseModel, ValidationInfo, field_validator
from abstractions.goap.game.gui_widgets import InventoryWidget
import pygame
import pygame_gui
from pygame_gui import UIManager, UI_TEXT_ENTRY_CHANGED
from pygame_gui.elements import UIWindow, UITextEntryBox, UITextBox


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
    def __init__(self, grid_map: GridMap, sprite_mappings: List[SpriteMapping], ui_manager: pygame_gui.UIManager, grid_map_widget_size: Tuple[int, int],inventory_widget: InventoryWidget, text_entry_box: UITextEntryBox):
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

    def handle_input(self, event):
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
                    player_id = self.active_entities.controlled_entity_id
                    player = GameEntity.get_instance(player_id)
                    target_entity_id = self.active_entities.targeted_entity_id
                    if target_entity_id:
                        target_entity = GameEntity.get_instance(target_entity_id)
                        self.available_actions = self.get_available_actions(player, target_entity)
                        if clicked_node == player.node or clicked_node in player.node.neighbors():
                            if hasattr(target_entity, 'is_pickupable') and target_entity.is_pickupable.value:
                                pickup_action = ActionInstance(source_id=player_id, target_id=target_entity_id, action=PickupAction())
                                self.actions_payload.actions.append(pickup_action)
                                print(f"PickupAction generated: {pickup_action}")  # Debug print statement
                            elif isinstance(target_entity, Door):
                                if target_entity.open.value:
                                    close_action = ActionInstance(source_id=player_id, target_id=target_entity_id, action=CloseAction())
                                    self.actions_payload.actions.append(close_action)
                                else:
                                    open_action = ActionInstance(source_id=player_id, target_id=target_entity_id, action=OpenAction())
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
                drop_action = ActionInstance(source_id=player_id, target_id=target_entity_id, action=DropAction())
                self.actions_payload.actions.append(drop_action)
            
    def generate_lock_unlock_action(self):
        player_id = self.active_entities.controlled_entity_id
        player = GameEntity.get_instance(player_id)
        target_entity_id = self.active_entities.targeted_entity_id
        if target_entity_id:
            target_entity = GameEntity.get_instance(target_entity_id)
            if isinstance(target_entity, Door):
                if target_entity.is_locked.value:
                    unlock_action = ActionInstance(source_id=player_id, target_id=target_entity_id, action=UnlockAction())
                    self.actions_payload.actions.append(unlock_action)
                else:
                    lock_action = ActionInstance(source_id=player_id, target_id=target_entity_id, action=LockAction())
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
