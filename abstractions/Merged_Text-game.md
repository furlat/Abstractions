# Combined Text Dir from game

- Full filepath to the merged directory: `C:\Users\Tommaso\Documents\Dev\Abstractions\abstractions\goap\game`

- Created: `2024-03-30T20:26:52.125328`

## init

# This is the __init__.py file for the package.


---

## gui widgets

import pygame
import pygame_gui
from typing import List
from pydantic import BaseModel
from abstractions.goap.interactions import GameEntity
from abstractions.goap.game.payloadgen import SpriteMapping

class InventoryItemVisual(BaseModel):
    sprite_path: str
    name: str
    entity_id: str

class InventoryVisualState(BaseModel):
    items: List[InventoryItemVisual]
class InventoryWidget(pygame_gui.elements.UIWindow):
    def __init__(self, pos, manager, sprite_mappings: List[SpriteMapping], input_handler):
        super().__init__(pygame.Rect(pos, (200, 150)), manager, window_display_title="Inventory", object_id="#inventory_window")
       
        self.inventory_container = pygame_gui.core.UIContainer(pygame.Rect(0, 0, 200, 150), manager=manager, container=self, object_id="#inventory_container")
       
        self.sprite_mappings = sprite_mappings
        self.visual_state = InventoryVisualState(items=[])
        self.input_handler = input_handler
        self.inventory_changed = False


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
        if event.type == pygame.USEREVENT:
            if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.inventory_container:
                    mouse_pos = pygame.mouse.get_pos()
                    for i, item_visual in enumerate(self.visual_state.items):
                        item_rect = pygame.Rect((self.rect.x + 10, self.rect.y + 10 + i * 30), (190, 20))
                        if item_rect.collidepoint(mouse_pos):
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
    def __init__(self, grid_map: GridMap, sprite_mappings: List[SpriteMapping], ui_manager: pygame_gui.UIManager, grid_map_widget_size: Tuple[int, int]):
        self.grid_map = grid_map
        self.active_entities = ActiveEntities()
        self.mouse_highlighted_node: Optional[Node] = None
        self.camera_control = CameraControl()
        self.actions_payload = ActionsPayload(actions=[])
        self.available_actions: List[str] = []
        self.sprite_mappings = sprite_mappings
        self.active_widget: Optional[str] = None
        self.grid_map_widget_size = grid_map_widget_size  
        self.inventory_widget = InventoryWidget((self.grid_map_widget_size[0] + 5, 10), ui_manager, sprite_mappings, self)

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
        if button == 1:  # Left mouse button
            if self.inventory_widget.rect.collidepoint(pos):
                # Handle clicks on the inventory widget
                self.inventory_widget.process_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))
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


---

## main

import pygame
from abstractions.goap.spatial import GridMap, GameEntity, Node, Attribute, BlocksMovement, BlocksLight
import os
from abstractions.goap.interactions import Character, Door, Key, Treasure, Floor, InanimateEntity, IsPickupable, TestItem
from abstractions.goap.game.payloadgen import PayloadGenerator, SpriteMapping
from abstractions.goap.game.renderer import Renderer, GridMapVisual, NodeVisual, EntityVisual, CameraControl
from abstractions.goap.game.input_handler import InputHandler
from pydantic import ValidationError
from abstractions.goap.game.manager import GameManager

BASE_PATH = r"C:\Users\Tommaso\Documents\Dev\Abstractions\abstractions\goap"
def generate_dungeon(grid_map: GridMap, room_width: int, room_height: int):
    room_x = (grid_map.width - room_width) // 2
    room_y = (grid_map.height - room_height) // 2

    for x in range(room_x, room_x + room_width):
        for y in range(room_y, room_y + room_height):
            if x == room_x or x == room_x + room_width - 1 or y == room_y or y == room_y + room_height - 1:
                if (x, y) != (room_x + room_width // 2, room_y):
                    wall = InanimateEntity(name=f"Wall_{x}_{y}", blocks_movement=BlocksMovement(value=True), blocks_light=BlocksLight(value=True))
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


def main():
    # Initialize Pygame
    pygame.init()
    screen_width, screen_height = 1200, 900
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Dungeon Experiment")
   
    # Create the grid map and generate the dungeon
    grid_map = GridMap(width=100, height=100)
    room_width, room_height = 6, 6
    character, door, key, treasure = generate_dungeon(grid_map, room_width, room_height)
   
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
   
    # Create the game manager
    game_manager = GameManager(screen, grid_map, sprite_mappings, widget_size=(800, 600), controlled_entity_id=character.id)
    
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

from typing import List, Tuple, Set
from abstractions.goap.spatial import GridMap, Path, Shadow, RayCast, Radius, Node, GameEntity
from abstractions.goap.game.renderer import Renderer, GridMapVisual, NodeVisual, EntityVisual
from abstractions.goap.game.input_handler import InputHandler
from abstractions.goap.game.payloadgen import PayloadGenerator, SpriteMapping
from abstractions.goap.interactions import Character
from pydantic import ValidationError

class GameManager:
    def __init__(self, screen: pygame.Surface, grid_map: GridMap, sprite_mappings: List[SpriteMapping],
                 widget_size: Tuple[int, int], controlled_entity_id: str):
        self.screen = screen
        self.grid_map = grid_map
        self.sprite_mappings = sprite_mappings
        self.widget_size = widget_size
        self.controlled_entity_id = controlled_entity_id

        self.renderer = Renderer(self.screen, GridMapVisual(width=grid_map.width, height=grid_map.height, node_visuals={}), self.widget_size)
        self.ui_manager = pygame_gui.UIManager((screen.get_width(), screen.get_height()))
        self.input_handler = InputHandler(self.grid_map, self.sprite_mappings, self.ui_manager, (self.renderer.widget_size[0], self.renderer.widget_size[1]))
        self.payload_generator = PayloadGenerator(self.sprite_mappings, (self.grid_map.width, self.grid_map.height))

        self.bind_controlled_entity(self.controlled_entity_id)
        self.prev_visible_positions: Set[Tuple[int, int]] = set()
        
       
    def bind_controlled_entity(self, controlled_entity_id: str):
        self.controlled_entity_id = controlled_entity_id
        self.input_handler.active_entities.controlled_entity_id = controlled_entity_id
       
    def run(self):
        running = True
        clock = pygame.time.Clock()
        controlled_entity = GameEntity.get_instance(self.input_handler.active_entities.controlled_entity_id)
        target_node = Node.get_instance(self.input_handler.active_entities.targeted_node_id) if self.input_handler.active_entities.targeted_node_id else None
        inventory = Character.get_instance(self.controlled_entity_id).inventory
        self.input_handler.inventory_widget.update_inventory(inventory)
        time_delta = clock.tick(60) / 1000.0
        self.ui_manager.update(time_delta)
        self.ui_manager.draw_ui(self.screen)


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
                    radius = self.grid_map.get_radius(controlled_entity.node, max_radius=10)
                    shadow = self.grid_map.get_shadow(controlled_entity.node, max_radius=20)
                    try:
                        raycast = self.grid_map.get_raycast(controlled_entity.node, target_node) if target_node else None
                    except ValidationError as e:
                        print(f"Error: {e}")
                        raycast = None
                    path = self.grid_map.a_star(controlled_entity.node, target_node) if target_node else None
            if self.input_handler.inventory_widget.inventory_changed:
                self.input_handler.update_available_actions()
                self.input_handler.inventory_widget.inventory_changed = False
            # Update the camera control based on input
            self.renderer.handle_camera_control(self.input_handler.camera_control)

            # Get the controlled entity and target node
            controlled_entity = GameEntity.get_instance(self.input_handler.active_entities.controlled_entity_id)
            target_node = Node.get_instance(self.input_handler.active_entities.targeted_node_id) if self.input_handler.active_entities.targeted_node_id else None

            time_delta = clock.tick(60) / 1000.0
            
            

            # Get the nodes affected by the action payload
            affected_nodes = self.get_affected_nodes()

            # Apply the action payload to the grid map
            actions_results = self.grid_map.apply_actions_payload(self.input_handler.actions_payload)

            # Check if there are any successful actions
            successful_actions = any(result.success for result in actions_results.results)

            

            # Recalculate the available actions after applying the action payload
            self.update_available_actions()

            # Get the nodes affected by the action results
            affected_nodes.update(self.get_affected_nodes_from_results(actions_results))

            # Generate the payload based on the camera position and FOV
            camera_pos = self.renderer.grid_map_widget.camera_pos
            fov = shadow if self.renderer.grid_map_widget.show_fov else None
            visible_nodes = [node for node in fov.nodes] if fov else self.grid_map.get_nodes_in_rect(camera_pos, self.renderer.grid_map_widget.rect.size)
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
                self.ui_manager.update(time_delta)
                self.ui_manager.draw_ui(self.screen)

            # Reset the camera control and actions payload
            self.input_handler.reset_camera_control()
            self.input_handler.reset_actions_payload()

            # Limit the frame rate to 144 FPS
            clock.tick(144)

            # Display FPS and other text
            self.display_text(clock)

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
        self.renderer.screen.blit(fps_text, (10, 10))
       
        # Display active node and entity
        active_node_pos = self.input_handler.active_entities.targeted_node_id
        if active_node_pos:
            active_node_pos = Node.get_instance(active_node_pos).position.value
        active_node_text = self.renderer.grid_map_widget.font.render(f"Active Node: {active_node_pos}", True, (255, 255, 255))
        self.renderer.screen.blit(active_node_text, (10, 30))
       
        active_entity_id = self.input_handler.active_entities.targeted_entity_id
        if active_entity_id:
            active_entity_name = GameEntity.get_instance(active_entity_id).name
            active_entity_text = self.renderer.grid_map_widget.font.render(f"Active Entity: {active_entity_name}", True, (255, 255, 255))
            self.renderer.screen.blit(active_entity_text, (10, 50))
       
        # Display inventory
        controlled_entity = GameEntity.get_instance(self.controlled_entity_id)
        if isinstance(controlled_entity, Character):
            inventory_names = [item.name for item in controlled_entity.inventory]
            inventory_text = self.renderer.grid_map_widget.font.render(f"Inventory: {inventory_names}", True, (255, 255, 255))
            self.renderer.screen.blit(inventory_text, (10, 70))
       
        # Display available actions
        available_actions_text = self.renderer.grid_map_widget.font.render(f"Available Actions: {', '.join(self.input_handler.available_actions)}", True, (255, 255, 255))
        self.renderer.screen.blit(available_actions_text, (10, 90))

        #display targeted_inventory entity
        targeted_inventory_entity_id = self.input_handler.active_entities.targeted_inventory_entity_id
        if targeted_inventory_entity_id:
            targeted_inventory_entity_name = GameEntity.get_instance(targeted_inventory_entity_id).name
            targeted_inventory_entity_text = self.renderer.grid_map_widget.font.render(f"Targeted Inventory Entity: {targeted_inventory_entity_name}", True, (255, 255, 255))
        else:
            targeted_inventory_entity_text = self.renderer.grid_map_widget.font.render(f"Targeted Inventory Entity: None", True, (255, 255, 255))
        self.renderer.screen.blit(targeted_inventory_entity_text, (10, 110))

---

## payloadgen

from functools import lru_cache
from typing import Dict, Type, Callable, Any, List, Tuple, Optional
from pydantic import BaseModel
import re
from abstractions.goap.spatial import GameEntity, Node, Shadow

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
            sorted_entities = sorted(node.entities, key=lambda e: self.get_sprite_mapping(e).draw_order)
            for entity in sorted_entities:
                sprite_mapping = self.get_sprite_mapping(entity)
                entity_visual = {
                    "sprite_path": sprite_mapping.sprite_path,
                    "ascii_char": sprite_mapping.ascii_char,
                    "draw_order": sprite_mapping.draw_order
                }
                entity_visuals.append(entity_visual)
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
                    entity_visuals = []
                    if node.entities:
                        sorted_entities = sorted(node.entities, key=lambda e: self.get_sprite_mapping(e).draw_order)
                        for entity in sorted_entities:
                            sprite_mapping = self.get_sprite_mapping(entity)
                            entity_visual = {
                                "sprite_path": sprite_mapping.sprite_path,
                                "ascii_char": sprite_mapping.ascii_char,
                                "draw_order": sprite_mapping.draw_order
                            }
                            entity_visuals.append(entity_visual)
                    payload[position] = entity_visuals
                    self.payload_cache[position] = entity_visuals
        return payload
    @lru_cache(maxsize=None)
    def is_node_unchanged(self, node: Node) -> bool:
        position = node.position.value
        if position not in self.payload_cache:
            return False
        cached_entity_visuals = self.payload_cache[position]
        current_entity_visuals = []
        if node.entities:
            sorted_entities = sorted(node.entities, key=lambda e: self.get_sprite_mapping(e).draw_order)
            for entity in sorted_entities:
                sprite_mapping = self.get_sprite_mapping(entity)
                entity_visual = {
                    "sprite_path": sprite_mapping.sprite_path,
                    "ascii_char": sprite_mapping.ascii_char,
                    "draw_order": sprite_mapping.draw_order,
                    "attribute_conditions": sprite_mapping.attribute_conditions
                }
                current_entity_visuals.append(entity_visual)
        return cached_entity_visuals == current_entity_visuals

---

## renderer

import pygame
from pygame.sprite import Group, RenderUpdates
from typing import Dict, List, Type, Tuple, Optional
from pydantic import BaseModel
from abstractions.goap.spatial import Node, Path, Shadow, RayCast, Radius

class CameraControl(BaseModel):
    move: Tuple[int, int] = (0, 0)
    zoom: int = 0
    recenter: bool = False
    toggle_path: bool = False
    toggle_shadow: bool = False
    toggle_raycast: bool = False
    toggle_radius: bool = False
    toggle_fov: bool = False
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

    def draw(self, surface: pygame.Surface, path: Optional[Path] = None, shadow: Optional[Shadow] = None,
             raycast: Optional[RayCast] = None, radius: Optional[Radius] = None, fog_of_war: Optional[Shadow] = None):
        # Clear the widget surface
        self.image.fill((0, 0, 0))

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

        # Draw effects (in the following order: shadow, radius, raycast, path)
        if self.show_shadow and shadow:
            self.draw_effect(self.image, shadow.nodes, (255, 255, 0))
        if self.show_radius and radius:
            self.draw_effect(self.image, radius.nodes, (0, 0, 255))
        if self.show_raycast and raycast:
            self.draw_effect(self.image, raycast.nodes, (255, 0, 0))
        if self.show_path and path:
            self.draw_effect(self.image, path.nodes, (0, 255, 0))

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

