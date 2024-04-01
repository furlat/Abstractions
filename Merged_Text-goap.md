# Combined Text Dir from goap

- Full filepath to the merged directory: `C:\Users\Tommaso\Documents\Dev\Abstractions\abstractions\goap`

- Created: `2024-04-01T21:26:26.593813`

## init

# This is the __init__.py file for the package.


---

## actions

from typing import List, Optional, Dict, Tuple, Callable, Any
from pydantic import BaseModel, Field
from abstractions.goap.entity import Entity, Statement, Attribute
from abstractions.goap.spatial import GameEntity, ActionInstance, Node

class Prerequisites(BaseModel):
    source_statements: List[Statement] = Field(default_factory=list, description="Statements involving only the source entity")
    target_statements: List[Statement] = Field(default_factory=list, description="Statements involving only the target entity")
    source_target_statements: List[Statement] = Field(default_factory=list, description="Statements involving both source and target entities")

    def is_satisfied(self, source: Entity, target: Entity) -> bool:
        try:
            return all(statement.validate_condition(source) for statement in self.source_statements) and \
                all(statement.validate_condition(target) for statement in self.target_statements) and \
                all(statement.validate_comparisons(source, target) for statement in self.source_target_statements) and \
                all(statement.validate_callables(source, target) for statement in self.source_statements + self.target_statements + self.source_target_statements)
        except Exception as e:
            return False

class Consequences(BaseModel):
    source_transformations: Dict[str, Any] = Field(default_factory=dict, description="Attribute transformations for the source entity")
    target_transformations: Dict[str, Any] = Field(default_factory=dict, description="Attribute transformations for the target entity")
   
    def apply(self, source: Entity, target: Entity) -> Tuple[Entity, Entity]:
        updated_source_attributes = {}
        updated_target_attributes = {}

        for attr_name, value in self.source_transformations.items():
            if callable(value):
                result = value(source=source, target=target)
                if attr_name == "node" and isinstance(result, Node):
                    updated_source_attributes[attr_name] = result.id  # Store the ID of the Node
                elif attr_name == "stored_in" and (isinstance(result, GameEntity) or result is None):
                    updated_source_attributes[attr_name] = result.id if result else None  # Store the ID of the entity or None
                elif attr_name == "inventory":
                    updated_source_attributes[attr_name] = [item.id for item in result]  # Store the IDs of the entities in the inventory
                else:
                    updated_source_attributes[attr_name] = Attribute(name=attr_name, value=result)
            elif attr_name == "node" and isinstance(value, Node):
                updated_source_attributes[attr_name] = value.id  # Store the ID of the Node
            elif attr_name == "stored_in" and (isinstance(value, GameEntity) or value is None):
                updated_source_attributes[attr_name] = value.id if value else None  # Store the ID of the entity or None
            elif attr_name == "inventory":
                updated_source_attributes[attr_name] = [item.id for item in value]  # Store the IDs of the entities in the inventory
            else:
                updated_source_attributes[attr_name] = Attribute(name=attr_name, value=value)

        for attr_name, value in self.target_transformations.items():
            if callable(value):
                result = value(source=source, target=target)
                if attr_name == "node" and isinstance(result, Node):
                    updated_target_attributes[attr_name] = result.id  # Store the ID of the Node
                elif attr_name == "stored_in" and (isinstance(result, GameEntity) or result is None):
                    updated_target_attributes[attr_name] = result.id if result else None  # Store the ID of the entity or None
                elif attr_name == "inventory":
                    updated_target_attributes[attr_name] = [item.id for item in result]  # Store the IDs of the entities in the inventory
                else:
                    updated_target_attributes[attr_name] = Attribute(name=attr_name, value=result)
            elif attr_name == "node" and isinstance(value, Node):
                updated_target_attributes[attr_name] = value.id  # Store the ID of the Node
            elif attr_name == "stored_in" and (isinstance(value, GameEntity) or value is None):
                updated_target_attributes[attr_name] = value.id if value else None  # Store the ID of the entity or None
            elif attr_name == "inventory":
                updated_target_attributes[attr_name] = [item.id for item in value]  # Store the IDs of the entities in the inventory
            else:
                updated_target_attributes[attr_name] = Attribute(name=attr_name, value=value)

        if isinstance(source, GameEntity):
            updated_source = source.update_attributes(updated_source_attributes)
        else:
            updated_source = source

        if isinstance(target, GameEntity):
            updated_target = target.update_attributes(updated_target_attributes)
        else:
            updated_target = target

        return updated_source, updated_target
class Action(BaseModel):
    name: str = Field("", description="The name of the action")
    prerequisites: Prerequisites = Field(default_factory=Prerequisites, description="The prerequisite conditions for the action")
    consequences: Consequences = Field(default_factory=Consequences, description="The consequences of the action")

    def is_applicable(self, source: GameEntity, target: GameEntity) -> bool:
        return self.prerequisites.is_satisfied(source, target)

    def apply(self, source: GameEntity, target: GameEntity) -> Tuple[GameEntity, GameEntity]:
        if not self.is_applicable(source, target):
            raise ValueError("Action prerequisites are not met")

        updated_source, updated_target = self.consequences.apply(source, target)

        if updated_source != source:
            self.propagate_spatial_consequences(updated_source, updated_target)
            self.propagate_inventory_consequences(updated_source, updated_target)
        else:
            updated_source = source

        if updated_target != target:
            self.propagate_spatial_consequences(updated_source, updated_target)
            self.propagate_inventory_consequences(updated_source, updated_target)
        else:
            updated_target = target

        return updated_source, updated_target

    def propagate_spatial_consequences(self, source: Entity, target: Entity) -> None:
        # Implement spatial consequence propagation logic here
        pass

    def propagate_inventory_consequences(self, source: Entity, target: Entity) -> None:
        # Implement inventory consequence propagation logic here
        pass
ActionInstance.model_rebuild()

---

## entity

from pydantic import BaseModel, Field, ValidationError, validator, field_validator, ValidationInfo
from typing import Annotated, Any, Dict, List, Optional, Set, Union, Tuple, Callable
from pydantic.functional_validators import AfterValidator
import uuid


class RegistryHolder:
    _registry: Dict[str, 'RegistryHolder'] = {}
    _types : Set[type] = set()

    @classmethod
    def register(cls, instance: 'RegistryHolder'):
        cls._registry[instance.id] = instance
        cls._types.add(type(instance))

    @classmethod
    def get_instance(cls, instance_id: str):
        return cls._registry.get(instance_id)

    @classmethod
    def all_instances(cls, filter_type=True):
        if filter_type:
            return [instance for instance in cls._registry.values() if isinstance(instance, cls)]
        return list(cls._registry.values())
    @classmethod
    def all_instances_by_type(cls, type: type):
        return [instance for instance in cls._registry.values() if isinstance(instance, type)]
    @classmethod
    def all_types(cls, as_string=True):
        if as_string:
            return [type_name.__name__ for type_name in cls._types]
        return cls._types
        

class Attribute(BaseModel, RegistryHolder):
    name: str = Field("", description="The name of the attribute")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="The unique identifier of the attribute")
    value: Any

    def __init__(self, **data: Any):
        super().__init__(**data)
        if not self.name:
            self.name = self.__class__.__name__
        self.register(self)



class Entity(BaseModel, RegistryHolder):
    name: str = Field("", description="The name of the entity")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="The unique identifier of the entity")

    def __init__(self, **data: Any):
        super().__init__(**data)
        if not self.name:
            self.name = self.__class__.__name__
        self.register(self)
        
    
    @field_validator('*', mode='after')
    def check_attributes_and_entities(cls, v: Any, info: ValidationInfo):
        if info.field_name not in ['id', 'name',"node"] and not isinstance(v, (Attribute, Entity)):
            raise ValueError(f"Attributes must be instances of Attribute or Entity, got {type(v).__name__} for field {info.field_name}")
        return v

    
    def all_attributes(self) -> Dict[str, 'Attribute']:
        attributes = {}
        for attribute_name, attribute_value in self.__dict__.items():
            if isinstance(attribute_value, Attribute):
                attributes[attribute_name] = attribute_value
            elif isinstance(attribute_value, Entity):
                nested_attributes = attribute_value.all_attributes()
                attributes.update(nested_attributes)
        return attributes
    

class Statement(BaseModel, RegistryHolder):
    name: str = Field("", description="The name of the statement")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="The unique identifier of the entity")
    conditions: Dict[str, Any] = Field(default_factory=dict, description="The desired attribute conditions for the statement")
    comparisons: Dict[str, Tuple[str, str, Callable[[Any, Any], bool]]] = Field(default_factory=dict, description="The attribute comparisons for the statement")
    callables: List[Callable[[Entity, Entity], bool]] = Field(default_factory=list, description="The generic callables for the statement")

    def __init__(self, **data: Any):
        super().__init__(**data)
        if not self.name:
            self.name = self.__class__.__name__
        self.register(self)

    @classmethod
    def from_entity(cls, entity: Entity, name: Optional[str] = None, conditions: Optional[Dict[str, Any]] = None, comparisons: Optional[Dict[str, Tuple[str, str, Callable[[Any, Any], bool]]]] = None, callables: Optional[List[Callable[[Entity, Entity], bool]]] = None):
        attributes = entity.all_attributes()
        return cls(name=name, conditions=conditions or {}, comparisons=comparisons or {}, callables=callables or [], **attributes)

    @classmethod
    def from_entities(cls, source: Entity, target: Entity, name: Optional[str] = None, conditions: Optional[Dict[str, Any]] = None, comparisons: Optional[Dict[str, Tuple[str, str, Callable[[Any, Any], bool]]]] = None, callables: Optional[List[Callable[[Entity, Entity], bool]]] = None):
        source_attributes = source.all_attributes()
        target_attributes = target.all_attributes()
        attributes = {f"source_{k}": v for k, v in source_attributes.items()}
        attributes.update({f"target_{k}": v for k, v in target_attributes.items()})
        return cls(name=name, conditions=conditions or {}, comparisons=comparisons or {}, callables=callables or [], **attributes)

    def validate_condition(self, entity: Entity) -> bool:
        attributes = entity.all_attributes()
        for attr_name, desired_value in self.conditions.items():
            if attr_name not in attributes or attributes[attr_name].value != desired_value:
                return False
        return True

    def validate_comparisons(self, source: Entity, target: Entity) -> bool:
        for comparison_name, (source_attr, target_attr, comparison_func) in self.comparisons.items():
            source_value = getattr(source, source_attr, None)
            target_value = getattr(target, target_attr, None)
            if source_value is None or target_value is None:
                return False
            elif source_attr == "node" and target_attr == "node":
                if not comparison_func(source_value, target_value):
                    return False
                return True
            elif not comparison_func(source_value.value, target_value.value):
                return False
        return True

    def validate_callables(self, source: Entity, target: Entity) -> bool:
        for callable_func in self.callables:
            if not callable_func(source, target):
                return False
        return True


---

## init

# This is the __init__.py file for the package.


---

## gui widgets

import pygame
import pygame_gui
from typing import List, Optional
from pydantic import BaseModel
from abstractions.goap.interactions import GameEntity
from abstractions.goap.game.payloadgen import SpriteMapping
import typing

if typing.TYPE_CHECKING:
    from abstractions.goap.game.input_handler import InputHandler

class InventoryItemVisual(BaseModel):
    sprite_path: str
    name: str
    entity_id: str

class InventoryVisualState(BaseModel):
    items: List[InventoryItemVisual]
    
class InventoryWidget(pygame_gui.elements.UIWindow):
    def __init__(self, pos, manager, sprite_mappings: List[SpriteMapping], input_handler:Optional["InputHandler"] = None):
        super().__init__(pygame.Rect(pos, (200, 150)), manager, window_display_title="Inventory", object_id="#inventory_window")
       
        self.inventory_container = pygame_gui.core.UIContainer(pygame.Rect(0, 0, 200, 150), manager=manager, container=self, object_id="#inventory_container")
       
        self.sprite_mappings = sprite_mappings
        self.visual_state = InventoryVisualState(items=[])
        self.input_handler = input_handler
        self.inventory_changed = False

    def setup_input_handler(self, input_handler: "InputHandler"):
        self.input_handler = input_handler
        
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
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # Left mouse button
            mouse_pos = event.pos
            for i, item_visual in enumerate(self.visual_state.items):
                # item_rect = pygame.Rect((self.rect.x + 10, self.rect.y + 10 + i * 30), (190, 20))
                item_rect = pygame.Rect((10, 50 + i * 30), (190, 20))
                if item_rect.collidepoint(mouse_pos):
                    print(f"Clicked on item {item_visual.name}")
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
                    self.active_entities.targeted_inventory_entity_id = None
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
# BASE_PATH = "/Users/tommasofurlanello/Documents/Dev/Abstractions/abstractions/goap"
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
    screen_width, screen_height = 1400, 800
    screen = pygame.display.set_mode((screen_width, screen_height))
    
    pygame.display.set_caption("Dungeon Experiment")
    
   
    # Create the grid map and generate the dungeon
    grid_map = GridMap(width=50, height=50)
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
    game_manager = GameManager(screen, grid_map, sprite_mappings, widget_size=(400, 300), controlled_entity_id=character.id)
    
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

from typing import List, Tuple, Set, Optional
from abstractions.goap.spatial import GridMap, Path, Shadow, RayCast, Radius, Node, GameEntity, ActionsResults,ActionResult
from abstractions.goap.game.renderer import Renderer, GridMapVisual, NodeVisual, EntityVisual
from abstractions.goap.game.input_handler import InputHandler
from abstractions.goap.game.payloadgen import PayloadGenerator, SpriteMapping
from abstractions.goap.interactions import Character
from pydantic import ValidationError
from abstractions.goap.game.gui_widgets import InventoryWidget
from pygame_gui.elements import UIWindow, UITextEntryBox, UITextBox

class GameManager:
    def __init__(self, screen: pygame.Surface, grid_map: GridMap, sprite_mappings: List[SpriteMapping],
                 widget_size: Tuple[int, int], controlled_entity_id: str):
        self.screen = screen
        self.grid_map = grid_map
        self.sprite_mappings = sprite_mappings
        self.widget_size = widget_size
        self.controlled_entity_id = controlled_entity_id
        

        self.renderer = Renderer(self.screen, GridMapVisual(width=grid_map.width, height=grid_map.height, node_visuals={}), self.widget_size)
        self.setup_gui_widgets(screen, sprite_mappings)
        
        self.inventory_widget = InventoryWidget((self.renderer.widget_size[0] + 5, 10), self.ui_manager, sprite_mappings, None)
        self.input_handler = InputHandler(self.grid_map, self.sprite_mappings, self.ui_manager, (self.renderer.widget_size[0], self.renderer.widget_size[1]),self.inventory_widget,self.text_entry_box)
        self.payload_generator = PayloadGenerator(self.sprite_mappings, (self.grid_map.width, self.grid_map.height))
        

        self.bind_controlled_entity(self.controlled_entity_id)
        self.prev_visible_positions: Set[Tuple[int, int]] = set()
        

        
    def setup_gui_widgets(self, screen: pygame.Surface, sprite_mappings: List[SpriteMapping]):
        # Initialize the UI manager
        self.ui_manager = pygame_gui.UIManager((screen.get_width(), screen.get_height()))
        # Initialize the inventory widget
        # Initialize the notepad window
        self.notepad_window = UIWindow(pygame.Rect(805, 160, 300, 400), window_display_title="Adventure Notepad")
        self.text_entry_box = UITextEntryBox(
        relative_rect=pygame.Rect((0, 0),  self.notepad_window.get_container().get_size()),
        initial_text="",
        container= self.notepad_window)
        #Initialize the texstate Window
        # the textstate window can be uptad by calling textstate_box.set_text("text")
        self.actionlog_window = UIWindow(pygame.Rect(400, 20, 600, 790), window_display_title="Action Logger")
        self.actionlog_box = UITextBox(
        relative_rect=pygame.Rect((0, 0), self.actionlog_window.get_container().get_size()),
        html_text="",
        container=self.actionlog_window)
        self.action_logs = []
        #Initialize the ObsLogger Window
        self.observationlog_window = UIWindow(pygame.Rect(400, 20, 600, 500), window_display_title="Observation Logger")
        self.observationlog_box = UITextBox(
        relative_rect=pygame.Rect((0, 0), self.observationlog_window.get_container().get_size()),
        html_text="",
        container=self.observationlog_window)
        self.observation_logs = []
        # Initalize the background
        self.vertical_background = pygame.Surface((1000, 800))
        self.horizontal_background = pygame.Surface((1200, 800))
       
    def bind_controlled_entity(self, controlled_entity_id: str):
        self.controlled_entity_id = controlled_entity_id
        self.input_handler.active_entities.controlled_entity_id = controlled_entity_id
    
    def get_controlled_entity(self,inventory:bool = False):
        if inventory:
            return Character.get_instance(self.input_handler.active_entities.controlled_entity_id).inventory
        return GameEntity.get_instance(self.input_handler.active_entities.controlled_entity_id)
    
    def get_target_node(self):
        return  Node.get_instance(self.input_handler.active_entities.targeted_node_id) if self.input_handler.active_entities.targeted_node_id else None

    def controlled_entity_preprocess(self, clock: pygame.time.Clock, target_node:  Optional[Node] = None):
        controlled_entity = self.get_controlled_entity()
        self.renderer.grid_map_widget.center_camera_on_player(controlled_entity.position.value)
        inventory = self.get_controlled_entity(inventory=True)
        self.input_handler.inventory_widget.update_inventory(inventory)
        time_delta = clock.tick(60) / 1000.0
        self.ui_manager.update(time_delta)
        self.ui_manager.draw_ui(self.screen)
        radius, shadow, raycast, path = self.compute_shapes(controlled_entity.node, target_node)
        return controlled_entity, inventory, radius, shadow, raycast, path
    
    def compute_shapes(self,source_node:Node, target_node: Optional[Node] = None):
        radius = self.grid_map.get_radius(source_node, max_radius=10)
        shadow = self.grid_map.get_shadow(source_node, max_radius=10)
       
        try:
            raycast = self.grid_map.get_raycast(source_node, target_node) if target_node else None
        except ValidationError as e:
            print(f"Error: {e}")
            raycast = None
        path = self.grid_map.a_star(source_node, target_node) if target_node else None
        return radius, shadow, raycast, path

    def update_action_logs(self, action_results: ActionsResults, only_changes: bool = True):
        for result in action_results.results:
            action_name = result.action_instance.action.name
            source_name = GameEntity.get_instance(result.action_instance.source_id).name
            target_name = GameEntity.get_instance(result.action_instance.target_id).name

            log_entry = f"Action: {action_name}\n"
            log_entry += f"Source: {source_name}\n"
            log_entry += f"Target: {target_name}\n"
            log_entry += f"Result: {'Success' if result.success else 'Failure'}\n"

            if not result.success:
                log_entry += f"Reason: {result.error}\n"

            if only_changes:
                state_before = {k: v for k, v in result.state_before.items() if k in result.state_after and v != result.state_after[k]}
                state_after = {k: v for k, v in result.state_after.items() if k in result.state_before and v != result.state_before[k]}
            else:
                state_before = result.state_before
                state_after = result.state_after

            log_entry += "State Before:\n"
            for entity, state in state_before.items():
                log_entry += f"  {entity.capitalize()}:\n"
                for attr, value in state.items():
                    log_entry += f"    {attr}: {value}\n"

            if result.success:
                log_entry += "State After:\n"
                for entity, state in state_after.items():
                    log_entry += f"  {entity.capitalize()}:\n"
                    for attr, value in state.items():
                        log_entry += f"    {attr}: {value}\n"

            self.action_logs.append(log_entry)

        inverted_list_action = self.action_logs[::-1]
        self.actionlog_box.set_text(log_entry)
    
    def update_observation_logs(self,observation:Shadow,mode:str,use_egoncentric:bool =False, only_salient:bool = True,include_attributes:bool=False):
        sprite_mappings=self.sprite_mappings
        if mode == "groups":
            self.observation_logs.append(observation.to_entity_groups(use_egocentric=use_egoncentric))
        
        elif mode == "list":
            obs = observation.to_list( use_egocentric=use_egoncentric,include_attributes=include_attributes)
            self.observation_logs.append(obs)

        
        print("diocane",self.observation_logs[-1])
        self.observationlog_box.set_text(self.observation_logs[-1])
        
    def run(self):
        self.screen.blit(self.vertical_background, (400, 0))
        self.screen.blit(self.horizontal_background, (0, 300))
        running = True
        clock = pygame.time.Clock()
        target_node = self.get_target_node()
        controlled_entity, inventory, radius, shadow, raycast, path = self.controlled_entity_preprocess(clock, target_node)
        

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
                    controlled_entity = self.get_controlled_entity()
                    radius, shadow, raycast, path = self.compute_shapes(controlled_entity.node, target_node)
                self.ui_manager.process_events(event)
            

            # Update the camera control based on input
            self.renderer.handle_camera_control(self.input_handler.camera_control)

            # Get the controlled entity and target node
            controlled_entity = self.get_controlled_entity()
            target_node = self.get_target_node()

            time_delta = clock.tick(60) / 1000.0

            # Get the nodes affected by the action payload
            affected_nodes = self.get_affected_nodes()

            # Apply the action payload to the grid map
            actions_results = self.grid_map.apply_actions_payload(self.input_handler.actions_payload)
            if len(actions_results.results) > 0:
                self.update_action_logs(actions_results, only_changes=True)

            # Check if there are any successful actions
            successful_actions = any(result.success for result in actions_results.results)
            #get the action name, source and entiy as a formatted string that we will add to the textstate_box
            # we will use the action name to get the action description from the action class, then combine it with the source name and target name
            # we will also add the position of the source and target node. 
            if successful_actions:
                self.update_observation_logs(shadow,mode="groups",use_egoncentric=True)
                

            
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
                
                
                # # self.ui_manager.draw_ui(self.screen)

            # Reset the camera control and actions payload
            self.input_handler.reset_camera_control()
            self.input_handler.reset_actions_payload()

            # Limit the frame rate to 144 FPS
            clock.tick(144)

            # Display FPS and other text
            
            self.ui_manager.update(time_delta)
            self.screen.blit(self.vertical_background, (400, 0))
            self.screen.blit(self.horizontal_background, (0, 300))
            self.display_text(clock)
            self.ui_manager.draw_ui(self.screen)
            pygame.display.update()

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
        self.renderer.screen.blit(fps_text, (1000, 10))
       
        # Display active node and entity
        active_node_pos = self.input_handler.active_entities.targeted_node_id
        if active_node_pos:
            active_node_pos = Node.get_instance(active_node_pos).position.value
        active_node_text = self.renderer.grid_map_widget.font.render(f"Active Node: {active_node_pos}", True, (255, 255, 255))
        self.renderer.screen.blit(active_node_text, (1000, 30))
       
        active_entity_id = self.input_handler.active_entities.targeted_entity_id
        if active_entity_id:
            active_entity_name = GameEntity.get_instance(active_entity_id).name
            active_entity_text = self.renderer.grid_map_widget.font.render(f"Active Entity: {active_entity_name}", True, (255, 255, 255))
            self.renderer.screen.blit(active_entity_text, (1000, 50))
       
        # Display inventory
        controlled_entity = GameEntity.get_instance(self.controlled_entity_id)
        if isinstance(controlled_entity, Character):
            inventory_names = [item.name for item in controlled_entity.inventory]
            inventory_text = self.renderer.grid_map_widget.font.render(f"Inventory: {inventory_names}", True, (255, 255, 255))
            self.renderer.screen.blit(inventory_text, (1000, 70))
       
        # Display available actions
        available_actions_text = self.renderer.grid_map_widget.font.render(f"Available Actions: {', '.join(self.input_handler.available_actions)}", True, (255, 255, 255))
        self.renderer.screen.blit(available_actions_text, (1000, 90))

        #display targeted_inventory entity
        targeted_inventory_entity_id = self.input_handler.active_entities.targeted_inventory_entity_id
        if targeted_inventory_entity_id:
            targeted_inventory_entity_name = GameEntity.get_instance(targeted_inventory_entity_id).name
            targeted_inventory_entity_text = self.renderer.grid_map_widget.font.render(f"Targeted Inventory Entity: {targeted_inventory_entity_name}", True, (255, 255, 255))
        else:
            targeted_inventory_entity_text = self.renderer.grid_map_widget.font.render(f"Targeted Inventory Entity: None", True, (255, 255, 255))
        self.renderer.screen.blit(targeted_inventory_entity_text, (1000, 110))

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
    toggle_fov: bool = True
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

    def draw_visible_nodes(self, fog_of_war: Optional[Shadow] = None):
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

    def draw_shape_effect(self,path: Optional[Path] = None, shadow: Optional[Shadow] = None,
             raycast: Optional[RayCast] = None, radius: Optional[Radius] = None, fog_of_war: Optional[Shadow] = None):
        # Draw effects (in the following order: shadow, radius, raycast, path)
        if self.show_shadow and shadow:
            self.draw_effect(self.image, shadow.nodes, (255, 255, 0))
        if self.show_radius and radius:
            self.draw_effect(self.image, radius.nodes, (0, 0, 255))
        if self.show_raycast and raycast:
            self.draw_effect(self.image, raycast.nodes, (255, 0, 0))
        if self.show_path and path:
            self.draw_effect(self.image, path.nodes, (0, 255, 0))


    def draw(self, surface: pygame.Surface, path: Optional[Path] = None, shadow: Optional[Shadow] = None,
             raycast: Optional[RayCast] = None, radius: Optional[Radius] = None, fog_of_war: Optional[Shadow] = None):
        # Clear the widget surface
        self.image.fill((0, 0, 0))

        self.draw_visible_nodes(fog_of_war)

        self.draw_shape_effect(path, shadow, raycast, radius, fog_of_war)

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

## interactions

from abstractions.goap.actions import Action, Prerequisites, Consequences
from abstractions.goap.entity import Attribute, Statement, Entity
from abstractions.goap.spatial import GameEntity, Node, BlocksMovement, BlocksLight
from typing import Callable, Dict, Tuple, Optional, List, Union
from pydantic import Field

class Health(Attribute):
    value: int = Field(100, description="The current health points of the entity")

class MaxHealth(Attribute):
    value: int = Field(100, description="The maximum health points of the entity")

class AttackPower(Attribute):
    value: int = Field(10, description="The amount of damage the entity inflicts in combat")

class CanAct(Attribute):
    value: bool = Field(True, description="Indicates whether the entity can perform actions")

class IsPickupable(Attribute):
    value: bool = Field(True, description="Indicates whether the entity can be picked up")

class Material(Attribute):
    value: str = Field("", description="The material composition of the entity")

class Open(Attribute):
    value: bool = Field(False, description="Indicates whether the door is open")



class LivingEntity(GameEntity):
    health: Health = Health()
    max_health: MaxHealth = MaxHealth()
    attack_power: AttackPower = AttackPower()
    can_act: CanAct = CanAct()

    def __init__(self, **data):
        super().__init__(**data)
        self.update_can_act()

    def update_can_act(self):
        self.can_act.value = self.is_alive()

    def is_alive(self) -> bool:
        return self.health.value > 0

    def take_damage(self, amount: int):
        self.health.value = max(0, self.health.value - amount)
        self.update_can_act()

    def heal(self, amount: int):
        self.health.value = min(self.health.value + amount, self.max_health.value)
        self.update_can_act()

class InanimateEntity(GameEntity):
    material: Material = Material()

class Character(LivingEntity):
    pass

class Monster(LivingEntity):
    pass

class Door(InanimateEntity):
    open: Open = Open()
    is_locked: Attribute = Attribute(name="is_locked", value=False)
    required_key: Attribute = Attribute(name="required_key", value="")
    blocks_movement: BlocksMovement = BlocksMovement()
    blocks_light: BlocksLight = BlocksLight()

    def __init__(self, **data):
        super().__init__(**data)
        self.update_block_attributes()

    def update_block_attributes(self):
        print("Updating block attributes... for door")
        if self.open.value:
            self.blocks_movement = BlocksMovement(value=False)
            self.blocks_light = BlocksLight(value=False)
        else:
            self.blocks_movement = BlocksMovement(value=True)
            self.blocks_light = BlocksLight(value=True)
  


class Key(InanimateEntity):
    key_name: Attribute = Attribute(name="key_name", value="")
    is_pickupable: IsPickupable = IsPickupable(value=True)

class Treasure(InanimateEntity):
    monetary_value: Attribute = Attribute(name="monetary_value", value=1000)
    is_pickupable: IsPickupable = IsPickupable(value=True)

class Trap(InanimateEntity):
    damage: Attribute = Attribute(name="damage", value=0)
    is_active: Attribute = Attribute(name="is_active", value=True)

class Floor(InanimateEntity):
    blocks_movement: BlocksMovement = BlocksMovement(value=False)

class TestItem(InanimateEntity):
    is_pickupable: IsPickupable = IsPickupable(value=True)


def set_stored_in(source: GameEntity, target: GameEntity) -> GameEntity:
    return source

def source_node_comparison(source: Node, target: Node) -> bool:
    return source in target.neighbors() or source.id == target.id

def source_node_comparison_and_walkable(source: Node, target: Node) -> bool:
    if target.blocks_movement:
        return False
    return source in target.neighbors() or source.id == target.id

def target_walkable_comparison(source: GameEntity, target: GameEntity) -> bool:
    return not target.blocks_movement.value

def move_to_target_node(source: GameEntity, target: GameEntity) -> Node:
    return target.node

MoveToTargetNode: Callable[[GameEntity, GameEntity], Node] = move_to_target_node

class MoveStep(Action):
    name: str = "Move Step"
    prerequisites: Prerequisites = Prerequisites(
        source_statements=[Statement(conditions={"can_act": True})],
        target_statements=[Statement(conditions={"blocks_movement": False})],
        source_target_statements=[Statement(comparisons={
            "source_position": ("node", "node", source_node_comparison_and_walkable)
        })]
    )
    consequences: Consequences = Consequences(
        source_transformations={"node": MoveToTargetNode}
    )

SetStoredIn: Callable[[GameEntity, GameEntity], GameEntity] = set_stored_in

def set_node(source: GameEntity, target: GameEntity) -> Node:
    target.set_stored_in(None)
    source.node.add_entity(target)
    return source.node

SetNode: Callable[[GameEntity, GameEntity], Node] = set_node

def add_to_inventory(source: GameEntity, target: GameEntity) -> List[GameEntity]:
    source.add_to_inventory(target)
    return source.inventory

def remove_from_inventory(source: GameEntity, target: GameEntity) -> List[GameEntity]:
    source.remove_from_inventory(target)
    return source.inventory

AddToInventory: Callable[[GameEntity, GameEntity], None] = add_to_inventory
RemoveFromInventory: Callable[[GameEntity, GameEntity], None] = remove_from_inventory


class PickupAction(Action):
    name: str = "Pickup"
    prerequisites: Prerequisites = Prerequisites(
        source_statements=[Statement(conditions={"can_act": True})],
        target_statements=[Statement(conditions={"is_pickupable": True})],
        source_target_statements=[Statement(comparisons={
            "source_position": ("node", "node", source_node_comparison)
        })]
    )
    consequences: Consequences = Consequences(
        source_transformations={"inventory": AddToInventory},
        target_transformations={"stored_in": SetStoredIn, "node": None}
    )

    def apply(self, source: GameEntity, target: GameEntity) -> Tuple[GameEntity, GameEntity]:
        if not self.is_applicable(source, target):
            raise ValueError("Action prerequisites are not met")
        # Remove the target entity from its current node
        if target.node:
            target.node.remove_entity(target)
        updated_source, updated_target = self.consequences.apply(source, target)
        if updated_source != source:
            self.propagate_spatial_consequences(updated_source, updated_target)
            self.propagate_inventory_consequences(updated_source, updated_target)
        else:
            updated_source = source
        if updated_target != target:
            self.propagate_spatial_consequences(updated_source, updated_target)
            self.propagate_inventory_consequences(updated_source, updated_target)
        else:
            updated_target = target
        return updated_source, updated_target
    
def is_alive(health: int) -> bool:
    return health > 0

def calculate_damage(source: LivingEntity, target: LivingEntity) -> int:
    return max(0, target.health.value - source.attack_power.value)

class AttackAction(Action):
    name: str = "Attack"
    prerequisites: Prerequisites = Prerequisites(
        source_statements=[Statement(conditions={"can_act": True})],
        target_statements=[Statement(conditions={"health": is_alive})],
        source_target_statements=[Statement(comparisons={
            "source_position": ("node", "node", source_node_comparison)
        })]
    )
    consequences: Consequences = Consequences(
        source_transformations={},
        target_transformations={"health": calculate_damage}
    )

def can_be_healed(source: LivingEntity, target: LivingEntity) -> bool:
    return target.health.value < target.max_health.value

def calculate_heal_amount(source: LivingEntity, target: LivingEntity) -> int:
    return min(target.health.value + source.attack_power.value, target.max_health.value)

class HealAction(Action):
    name: str = "Heal"
    prerequisites: Prerequisites = Prerequisites(
        source_statements=[
            Statement(
                conditions={"can_act": True},
                callables=[]
            )
        ],
        target_statements=[
            Statement(
                conditions={},
                callables=[can_be_healed]
            )
        ],
        source_target_statements=[
            Statement(
                conditions={},
                comparisons={
                    "source_position": ("node", "node", source_node_comparison)
                },
                callables=[]
            )
        ]
    )
    consequences: Consequences = Consequences(
        source_transformations={},
        target_transformations={"health": calculate_heal_amount}
    )
def clear_stored_in(source: GameEntity, target: GameEntity) -> None:
    return None

ClearStoredIn: Callable[[GameEntity, GameEntity], None] = clear_stored_in

class DropAction(Action):
    name: str = "Drop"
    prerequisites: Prerequisites = Prerequisites(
        source_statements=[Statement(conditions={"can_act": True})],
        target_statements=[],
        source_target_statements=[]
    )
    consequences: Consequences = Consequences(
        source_transformations={},
        target_transformations={"stored_in": ClearStoredIn, "node": SetNode}
    )



class OpenAction(Action):
    name: str = "Open"
    prerequisites: Prerequisites = Prerequisites(
        source_statements=[Statement(conditions={"can_act": True})],
        target_statements=[Statement(conditions={"is_locked": False, "open": False})],
        source_target_statements=[Statement(comparisons={
            "source_position": ("node", "node", source_node_comparison)
        })]
    )
    consequences: Consequences = Consequences(
        source_transformations={},
        target_transformations={"open": True}
    )

    def apply(self, source: GameEntity, target: Door) -> Tuple[GameEntity, Door]:
        if not self.is_applicable(source, target):
            raise ValueError("Action prerequisites are not met")

        updated_source, updated_target = self.consequences.apply(source, target)
        updated_target.update_block_attributes()
        updated_target.node.update_blocking_properties()

        return updated_source, updated_target
class CloseAction(Action):
    name: str = "Close"
    prerequisites: Prerequisites = Prerequisites(
        source_statements=[Statement(conditions={"can_act": True})],
        target_statements=[Statement(conditions={"open": True})],
        source_target_statements=[Statement(comparisons={
            "source_position": ("node", "node", source_node_comparison)
        })]
    )
    consequences: Consequences = Consequences(
        source_transformations={},
        target_transformations={"open": False}
    )
    def apply(self, source: GameEntity, target: Door) -> Tuple[GameEntity, Door]:
        if not self.is_applicable(source, target):
            raise ValueError("Action prerequisites are not met")

        updated_source, updated_target = self.consequences.apply(source, target)
        updated_target.update_block_attributes()
        updated_target.node.update_blocking_properties()

        return updated_source, updated_target



def has_required_key(source: GameEntity, target: Door) -> bool:
    return any(item.key_name.value == target.required_key.value for item in source.inventory)

class UnlockAction(Action):
    name: str = "Unlock"
    prerequisites: Prerequisites = Prerequisites(
        source_statements=[Statement(conditions={"can_act": True})],
        target_statements=[Statement(conditions={"is_locked": True})],
        source_target_statements=[
            Statement(
                comparisons={"source_position": ("node", "node", source_node_comparison)},
                callables=[has_required_key]
            )
        ]
    )
    consequences: Consequences = Consequences(
        source_transformations={},
        target_transformations={"is_locked": False}
    )

class LockAction(Action):
    name: str = "Lock"
    prerequisites: Prerequisites = Prerequisites(
        source_statements=[Statement(conditions={"can_act": True})],
        target_statements=[Statement(conditions={"is_locked": False, "open": False})],
        source_target_statements=[
            Statement(
                comparisons={"source_position": ("node", "node", source_node_comparison)},
                callables=[has_required_key]
            )
        ]
    )
    consequences: Consequences = Consequences(
        source_transformations={},
        target_transformations={"is_locked": True}
    )

---

## procedural

from abstractions.goap.spatial import GameEntity, Node, Position, GridMap, ActionsPayload, ActionInstance, ActionsResults, Path, BlocksMovement, BlocksLight
from typing import List, Dict, Any, Optional
import random

def create_room(grid_map, top_left, width, height):
    for x in range(top_left[0], top_left[0] + width):
        for y in range(top_left[1], top_left[1] + height):
            grid_map.get_node((x, y)).reset()
            floor = GameEntity(name=f"Floor_{x}_{y}", blocks_movement=BlocksMovement(value=False), blocks_light=BlocksLight(value=False))
            grid_map.get_node((x, y)).add_entity(floor)

def create_h_corridor(grid_map, x1, x2, y):
    for x in range(min(x1, x2), max(x1, x2) + 1):
        grid_map.get_node((x, y)).reset()
        floor = GameEntity(name=f"Floor_{x}_{y}", blocks_movement=BlocksMovement(value=False), blocks_light=BlocksLight(value=False))
        grid_map.get_node((x, y)).add_entity(floor)

def create_v_corridor(grid_map, y1, y2, x):
    for y in range(min(y1, y2), max(y1, y2) + 1):
        grid_map.get_node((x, y)).reset()
        floor = GameEntity(name=f"Floor_{x}_{y}", blocks_movement=BlocksMovement(value=False), blocks_light=BlocksLight(value=False))
        grid_map.get_node((x, y)).add_entity(floor)

def generate_dungeon(grid_map, num_rooms, min_room_size, max_room_size):
    rooms = []
    for _ in range(num_rooms):
        width = random.randint(min_room_size, max_room_size)
        height = random.randint(min_room_size, max_room_size)
        x = random.randint(1, grid_map.width - width - 1)
        y = random.randint(1, grid_map.height - height - 1)
        create_room(grid_map, (x, y), width, height)
        rooms.append((x, y, width, height))
    for i in range(len(rooms) - 1):
        x1, y1, w1, h1 = rooms[i]
        x2, y2, w2, h2 = rooms[i + 1]
        if random.random() < 0.5:
            create_h_corridor(grid_map, x1 + w1, x2, y1 + h1 // 2)
            create_v_corridor(grid_map, y1 + h1 // 2, y2 + h2 // 2, x2)
        else:
            create_v_corridor(grid_map, y1 + h1 // 2, y2, x1 + w1 // 2)
            create_h_corridor(grid_map, x1 + w1 // 2, x2 + w2 // 2, y2)

---

## spatial

from __future__ import annotations
from abstractions.goap.entity import Entity, Attribute, RegistryHolder
from typing import List, Tuple, TYPE_CHECKING, Optional, Any, ForwardRef, Dict, Union, Set, Type
from pydantic import Field, BaseModel, validator, ConfigDict, ValidationInfo, field_validator
import uuid
import re
import math

if TYPE_CHECKING:
    # from abstractions.goap.spatial import Node
    from abstractions.goap.actions import Action
    from abstractions.goap.game.payloadgen import SpriteMapping
    

class Position(Attribute):
    value: Tuple[int, int] = Field(default=(0, 0), description="The (x, y) coordinates of the entity")

    @property
    def x(self):
        return self.value[0]

    @property
    def y(self):
        return self.value[1]

class BlocksMovement(Attribute):
    value: bool = Field(default=False, description="Indicates if the entity blocks movement")

class BlocksLight(Attribute):
    value: bool = Field(default=False, description="Indicates if the entity blocks light")


class Path(BaseModel):
    nodes: List[Node] = Field(default_factory=list, description="The list of nodes in the path")

    @validator('nodes')
    def validate_path(cls, nodes):
        for i in range(len(nodes) - 1):
            if nodes[i + 1] not in nodes[i].neighbors():
                raise ValueError(f"Nodes {nodes[i]} and {nodes[i + 1]} are not adjacent")
            if nodes[i].blocks_movement:
                raise ValueError(f"Node {nodes[i]} is not walkable")
        return nodes

class BaseShapeFromSource(BaseModel):
    source: Node = Field(description="The source node of the shape")
    max_radius: int = Field(description="The maximum radius of the shape")
    nodes: List[Node] = Field(default_factory=list, description="The list of nodes within the shape")

    def _to_egocentric_coordinates(self, x: int, y: int) -> Tuple[int, int]:
        source_x, source_y = self.source.position.value
        return x - source_x, y - source_y
    

    def to_entity_groups(self, use_egocentric: bool = False) -> str:
        groups = {}

        for node in self.nodes:
            entity_types, entity_attributes = node._get_entity_info(node)
            group_key = (tuple(entity_types), tuple(sorted(entity_attributes)))

            if group_key not in groups:
                groups[group_key] = []

            position = self._to_egocentric_coordinates(node.position.x, node.position.y) if use_egocentric else (node.position.x, node.position.y)
            groups[group_key].append(position)

        group_strings_vanilla = []
        group_strings_summarized = []
        for (entity_types, entity_attributes), positions in groups.items():
            vanilla_positions = ", ".join(f"({x}, {y})" for x, y in positions)
            summarized_positions = self._summarize_positions(positions)

            group_strings_vanilla.append(f"Entity Types: {list(entity_types)}, Attributes: {list(entity_attributes)}, Positions: {vanilla_positions}")
            group_strings_summarized.append(f"Entity Types: {list(entity_types)}, Attributes: {list(entity_attributes)}, Positions: {summarized_positions}")

        vanilla_output = '\n'.join(group_strings_vanilla)
        summarized_output = '\n'.join(group_strings_summarized)

        print(f"Vanilla Length: {len(vanilla_output)}")
        print(f"Summarized Length: {len(summarized_output)}")
        print(f"Efficiency Gain: {len(vanilla_output) - len(summarized_output)}")
        print(f"Vanilla Output:\n{vanilla_output}")
        print(f"Summarized Output:\n{summarized_output}")

        return summarized_output

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




class Radius(BaseShapeFromSource):
    source: Node = Field(description="The source node of the radius")
    max_radius: int = Field(description="The maximum radius of the area")
    nodes: List[Node] = Field(default_factory=list, description="The list of nodes within the radius")

    @validator('nodes')
    def validate_radius(cls, nodes, values):
        source = values['source']
        max_radius = values['max_radius']
        grid_map = source.grid_map
        for node in nodes:
            if grid_map._get_distance(source.position.value, node.position.value) > max_radius:
                raise ValueError(f"Node {node} is outside the specified radius")
        return nodes

class Shadow(BaseShapeFromSource):
    source: Node = Field(description="The source node of the shadow")
    max_radius: int = Field(description="The maximum radius of the shadow")
    nodes: List[Node] = Field(default_factory=list, description="The list of nodes within the shadow")

    @validator('nodes')
    def validate_shadow(cls, nodes, values):
        source = values['source']
        max_radius = values['max_radius']
        grid_map = source.grid_map
        for node in nodes:
            if grid_map._get_distance(source.position.value, node.position.value) > max_radius:
                raise ValueError(f"Node {node} is outside the specified shadow radius")
        return nodes
    
   

    

class RayCast(BaseModel):
    source: Node = Field(description="The source node of the raycast")
    target: Node = Field(description="The target node of the raycast")
    has_path: bool = Field(description="Indicates whether there is a clear path from source to target")
    nodes: List[Node] = Field(default_factory=list, description="The list of nodes along the raycast path (excluding source and target)")

    @validator('nodes')
    def validate_raycast(cls, nodes, values):
        source = values['source']
        target = values['target']
        has_path = values['has_path']
        if not has_path and nodes:
            raise ValueError("The raycast path should be empty if there is no clear path")
        if has_path and len(nodes) >0:
            if nodes[0] == source or nodes[-1] == target:
                raise ValueError("The raycast path should not include the source or target nodes")
            for i in range(len(nodes) - 1):
                if nodes[i + 1] not in nodes[i].neighbors():
                    raise ValueError(f"Nodes {nodes[i]} and {nodes[i + 1]} are not adjacent")
            for node in nodes:
                if node.blocks_light:
                    raise ValueError(f"Node {node} blocks vision along the raycast path")
        return nodes
    

class ActionInstance(BaseModel):
    source_id: str
    target_id: str
    action: Action

class ActionsPayload(BaseModel):
    actions: List[ActionInstance]

class SummarizedActionPayload(BaseModel):
    action_name: str
    source_entity_type: str
    source_entity_position: Tuple[int, int]
    source_entity_id: Optional[str] = None
    source_entity_name: Optional[str] = None
    source_entity_attributes: Optional[Dict[str, Any]] = Field(default_factory=dict)
    target_entity_type: str
    target_entity_position: Tuple[int, int]
    target_entity_id: Optional[str] = None
    target_entity_name: Optional[str] = None
    target_entity_attributes: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ActionResult(BaseModel):
    action_instance: ActionInstance
    success: bool
    error: str = None
    state_before: Dict[str, Any] = Field(default_factory=dict)
    state_after: Dict[str, Any] = Field(default_factory=dict)

class ActionsResults(BaseModel):
    results: List[ActionResult]

class AmbiguousEntityError(BaseModel):
    entity_type: Type[GameEntity]
    entity_id: Optional[str] = None
    entity_name: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    matching_entities: List[GameEntity]
    missing_attributes: List[str]

    def __str__(self):
        return f"Ambiguous entity: {self.entity_type.__name__}, Matching entities: {len(self.matching_entities)}, Missing attributes: {', '.join(self.missing_attributes)}" 

class ActionConversionError(BaseModel):
    message: str
    source_entity_error: Optional[AmbiguousEntityError] = None
    target_entity_error: Optional[AmbiguousEntityError] = None

    def __str__(self):
        error_message = self.message
        if self.source_entity_error:
            error_message += f"\nSource Entity Error: {self.source_entity_error}"
        if self.target_entity_error:
            error_message += f"\nTarget Entity Error: {self.target_entity_error}"
        return error_message

class GameEntity(Entity):
    blocks_movement: BlocksMovement = Field(default_factory=BlocksMovement, description="Attribute indicating if the entity blocks movement")
    blocks_light: BlocksLight = Field(default_factory=BlocksLight, description="Attribute indicating if the entity blocks light")
    node: Optional[Node] = Field(default=None, description="The node the entity is currently in")
    inventory: List[GameEntity] = Field(default_factory=list, description="The entities stored inside this entity's inventory")
    stored_in: Optional[GameEntity] = Field(default=None, description="The entity this entity is stored inside, if any")

    @property
    def position(self) -> Position:
        if self.stored_in:
           
            return self.stored_in.position
        elif self.node:
            return self.node.position
        return Position()

    def set_node(self, node: Node):
        if self.stored_in:
            raise ValueError("Cannot set node for an entity stored inside another entity's inventory")
        self.node = node
        node.add_entity(self)

    def remove_from_node(self):
        if self.stored_in:
            raise ValueError("Cannot remove from node an entity stored inside another entity's inventory")
        if self.node:
            self.node.remove_entity(self)
            self.node = None

    def update_attributes(self, attributes: Dict[str, Union[Attribute, Node, str, List[str]]]) -> "GameEntity":
        updated_attributes = {"name": self.name}  # Preserve the name attribute
        new_node = None
        new_stored_in = None
        new_inventory = None
        for attr_name, value in attributes.items():
            if attr_name == "node":
                if isinstance(value, Node):
                    new_node = value
                elif isinstance(value, str):
                    new_node = Node.get_instance(value)  # Retrieve the Node instance using the ID
            elif attr_name == "stored_in":
                if value is not None:
                    new_stored_in = GameEntity.get_instance(value)  # Retrieve the GameEntity instance using the ID
                else:
                    new_stored_in = None  # Set new_stored_in to None if the value is None
            elif attr_name == "inventory" and isinstance(value, list):
                new_inventory = [GameEntity.get_instance(item_id) for item_id in value]  # Retrieve GameEntity instances using their IDs
            elif isinstance(value, Attribute):
                updated_attributes[attr_name] = value
        if new_stored_in is not None:
            if self.node:
                self.node.remove_entity(self)  # Remove the entity from its current node
            self.stored_in = new_stored_in  # Update the stored_in attribute with the retrieved GameEntity instance
        elif new_node:
            if self.stored_in:
                self.stored_in.inventory.remove(self)  # Remove the entity from its current stored_in inventory
            if self.node:
                self.node.remove_entity(self)  # Remove the entity from its current node
            new_node.add_entity(self)  # Add the entity to the new node
            self.node = new_node  # Update the entity's node reference
        if new_inventory is not None:
            self.inventory = new_inventory  # Update the inventory attribute with the retrieved GameEntity instances
        for attr_name, value in updated_attributes.items():
            setattr(self, attr_name, value)  # Update the entity's attributes
        return self
    
    def add_to_inventory(self, entity: GameEntity):
        if entity not in self.inventory:
            self.inventory.append(entity)
            entity.stored_in = self

    def remove_from_inventory(self, entity: GameEntity):
        if entity in self.inventory:
            self.inventory.remove(entity)
            entity.stored_in = None

    def set_stored_in(self, entity: Optional[GameEntity]):
        if entity is None:
            if self.stored_in:
                self.stored_in.remove_from_inventory(self)
        else:
            entity.add_to_inventory(self)

    def get_state(self) -> Dict[str, Any]:
        state = {}
        for attr_name, attr_value in self.__dict__.items():
            if isinstance(attr_value, Attribute) and attr_name not in ["position", "inventory"]:
                state[attr_name] = attr_value.value
        state["position"] = self.position.value
        state["inventory"] = [item.id for item in self.inventory]
        return state
    
    def __repr__(self):
        attrs = {}
        for key, value in self.__dict__.items():
            if key == 'node' and value is not None:
                attrs[key] = value.non_verbose_repr()
            elif key != 'node':
                attrs[key] = value
        attrs_str = ', '.join(f'{k}={v}' for k, v in attrs.items())
        return f"{self.__class__.__name__}({attrs_str})"
    
    def __hash__(self):
        #hash together idname and attributeslike in Node
        attribute_values = []
        for attribute_name, attribute_value in self.__dict__.items():
            if isinstance(attribute_value, Attribute):
                attribute_values.append(f"{attribute_name}={attribute_value.value}")
        entity_info = f"{self.__class__.__name__}_{self.name}_{self.id}_{'_'.join(attribute_values)}"
        return hash(entity_info)


class Node(BaseModel, RegistryHolder):
    name: str = Field("", description="The name of the node")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="The unique identifier of the node")
    position: Position = Field(default_factory=Position, description="The position of the node")
    entities: List[GameEntity] = Field(default_factory=list, description="The game entities contained within the node")
    grid_map: Optional[GridMap] = Field(default=None, exclude=True, description="The grid map the node belongs to")
    blocks_movement: bool = Field(default=False, description="Indicates if the node blocks movement")
    blocks_light: bool = Field(default=False, description="Indicates if the node blocks light")
    
    class Config(ConfigDict):
        arbitrary_types_allowed = True
    
    def __init__(self, **data: Any):
        super().__init__(**data)
        self.register(self)
    
    def __hash__(self):
        return hash(self.id)
    
    def non_verbose_repr(self):
        return f"Node(id={self.id}, position={self.position.value})"
    
    def add_entity(self, entity: GameEntity):
        if entity.stored_in:
            raise ValueError("Cannot add an entity stored inside another entity's inventory directly to a node")
        self.entities.append(entity)
        entity.node = self
        self.update_blocking_properties()

    def remove_entity(self, entity: GameEntity):
        if entity.stored_in:
            raise ValueError("Cannot remove an entity stored inside another entity's inventory directly from a node")
        self.entities.remove(entity)
        entity.node = None
        self.update_blocking_properties()
    
    def update_entity(self, old_entity: GameEntity, new_entity: GameEntity):
        self.remove_entity(old_entity)
        self.add_entity(new_entity)

    def update_blocking_properties(self):
        self.blocks_movement = any(entity.blocks_movement.value for entity in self.entities if not entity.stored_in)
        self.blocks_light = any(entity.blocks_light.value for entity in self.entities if not entity.stored_in)
    
    def reset(self):
        self.entities.clear()
        self.blocks_movement = False
        self.blocks_light = False

    def find_entity(self, entity_type: Type[GameEntity], entity_id: Optional[str] = None,
                entity_name: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None) -> Optional[Union[GameEntity, AmbiguousEntityError]]:
        matching_entities = []
        for entity in self.entities:
            if isinstance(entity, entity_type):
                if entity_id is not None and entity.id != entity_id:
                    continue
                if entity_name is not None and entity.name != entity_name:
                    continue
                if attributes is not None:
                    entity_attributes = {attr_name: getattr(entity, attr_name).value for attr_name in attributes}
                    if any(attr_name not in entity_attributes or entity_attributes[attr_name] != attr_value
                        for attr_name, attr_value in attributes.items()):
                        continue
                matching_entities.append(entity)

        if len(matching_entities) == 1:
            return matching_entities[0]
        elif len(matching_entities) > 1:
            missing_attributes = []
            if entity_id is None:
                missing_attributes.append("entity_id")
            if entity_name is None:
                missing_attributes.append("entity_name")
            if attributes is None:
                missing_attributes.extend(attr.name for attr in matching_entities[0].all_attributes())
            return AmbiguousEntityError(
                entity_type=entity_type,
                entity_id=entity_id,
                entity_name=entity_name,
                attributes=attributes,
                matching_entities=matching_entities,
                missing_attributes=missing_attributes
            )
        else:
            return None
    
    def neighbors(self) -> List[Node]:
        if self.grid_map:
            return self.grid_map.get_neighbors(self.position.value)
        return []
    
    def _get_entity_info(self, node: Node) -> Tuple[List[str], List[Tuple[str, Any]]]:
        entity_types = []
        entity_attributes = []
        for entity in node.entities:
            entity_types.append(type(entity).__name__)
            attributes = [(attr.name, attr.value) for attr in entity.all_attributes().values()]
            entity_attributes.extend(attributes)
        return entity_types, entity_attributes
    

    def __hash__(self):
        entity_info = []
        for entity in self.entities:
            attribute_values = []
            for attribute_name, attribute_value in entity.__dict__.items():
                if isinstance(attribute_value, Attribute):
                    attribute_values.append(f"{attribute_name}={attribute_value.value}")
            entity_info.append(f"{entity.__class__.__name__}_{entity.name}_{entity.id}_{'_'.join(attribute_values)}")
        return hash(f"{self.id}_{self.position.value}_{'_'.join(entity_info)}")

import heapq

class GridMap:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.grid: List[List[Node]] = [[Node(position=Position(value=(x, y)), grid_map=self) for y in range(height)] for x in range(width)]
        self.actions: Dict[str, Type[Action]] = {}
    
    def register_action(self, action_class: Type[Action]):
        self.actions[action_class.__name__] = action_class

    def register_actions(self, action_classes: List[Type[Action]]):
        for action_class in action_classes:
            self.register_action(action_class)
    
    def get_actions(self) -> Dict[str, Type[Action]]:
        return self.actions

    def get_node(self, position: Tuple[int, int]) -> Node:
        x, y = position
        return self.grid[x][y] if 0 <= x < self.width and 0 <= y < self.height else None
    
    def get_nodes_in_rect(self, pos: Tuple[int, int], size: Tuple[int, int]) -> List[Node]:
        start_x, start_y = pos
        width, height = size
        end_x = start_x + width
        end_y = start_y + height

        nodes = []
        for y in range(max(0, start_y), min(self.height, end_y)):
            for x in range(max(0, start_x), min(self.width, end_x)):
                node = self.get_node((x, y))
                if node:
                    nodes.append(node)

        return nodes

    def set_node(self, position: Tuple[int, int], node: Node):
        x, y = position
        self.grid[x][y] = node

    def get_neighbors(self, position: Tuple[int, int], allow_diagonal: bool = True) -> List[Node]:
        x, y = position
        neighbors = []
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            new_x, new_y = x + dx, y + dy
            if 0 <= new_x < self.width and 0 <= new_y < self.height:
                neighbors.append(self.grid[new_x][new_y])
        if allow_diagonal:
            for dx, dy in [(1, 1), (-1, 1), (1, -1), (-1, -1)]:
                new_x, new_y = x + dx, y + dy
                if 0 <= new_x < self.width and 0 <= new_y < self.height:
                    neighbors.append(self.grid[new_x][new_y])
        return neighbors
    
    def find_entity(self, entity_type: Type[GameEntity], position: Tuple[int, int], entity_id: Optional[str] = None,
                    entity_name: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None) -> Optional[GameEntity]:
        node = self.get_node(position)
        if node is None:
            return None
        return node.find_entity(entity_type, entity_id, entity_name, attributes)

    def dijkstra(self, start: Node, max_distance: int, allow_diagonal: bool = True) -> Tuple[Dict[Tuple[int, int], int], Dict[Tuple[int, int], Path]]:
        distances: Dict[Tuple[int, int], int] = {start.position.value: 0}
        paths: Dict[Tuple[int, int], Path] = {start.position.value: Path(nodes=[start])}
        unvisited = [(0, start.position.value)]  # The unvisited set is a list of tuples (distance, position)
        while unvisited:
            current_distance, current_position = heapq.heappop(unvisited)
            if current_distance > max_distance:
                break
            current_node = self.get_node(current_position)
            for neighbor in self.get_neighbors(current_position, allow_diagonal):
                if not neighbor.blocks_movement:
                    new_distance = current_distance + 1  # Assuming uniform cost between nodes
                    if neighbor.position.value not in distances or new_distance < distances[neighbor.position.value]:
                        distances[neighbor.position.value] = new_distance
                        paths[neighbor.position.value] = Path(nodes=paths[current_position].nodes + [neighbor])
                        heapq.heappush(unvisited, (new_distance, neighbor.position.value))
        return distances, paths

    def a_star(self, start: Node, goal: Node, allow_diagonal: bool = True) -> Optional[Path]:
        if start == goal:
            return Path(nodes=[start])
        if goal.blocks_movement:
            return None

        def heuristic(position: Tuple[int, int]) -> int:
            return abs(position[0] - goal.position.x) + abs(position[1] - goal.position.y)

        open_set = [(0, start.position.value)]  # The open set is a list of tuples (f_score, position)
        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
        g_score: Dict[Tuple[int, int], int] = {start.position.value: 0}
        f_score: Dict[Tuple[int, int], int] = {start.position.value: heuristic(start.position.value)}

        while open_set:
            current_position = heapq.heappop(open_set)[1]
            current_node = self.get_node(current_position)

            if current_node == goal:
                path_nodes = []
                while current_position in came_from:
                    path_nodes.append(self.get_node(current_position))
                    current_position = came_from[current_position]
                path_nodes.append(start)
                path_nodes.reverse()
                return Path(nodes=path_nodes)

            for neighbor in self.get_neighbors(current_position, allow_diagonal):
                if not neighbor.blocks_movement:  # Check if the neighbor is walkable
                    tentative_g_score = g_score[current_position] + 1  # Assuming uniform cost
                    if neighbor.position.value not in g_score or tentative_g_score < g_score[neighbor.position.value]:
                        came_from[neighbor.position.value] = current_position
                        g_score[neighbor.position.value] = tentative_g_score
                        f_score[neighbor.position.value] = tentative_g_score + heuristic(neighbor.position.value)
                        if (f_score[neighbor.position.value], neighbor.position.value) not in open_set:
                            heapq.heappush(open_set, (f_score[neighbor.position.value], neighbor.position.value))

        return None  # No path found
    def get_movement_array(self) -> List[List[bool]]:
        return [[not node.blocks_movement for node in row] for row in self.grid]

    def get_vision_array(self) -> List[List[bool]]:
        return [[not node.blocks_light for node in row] for row in self.grid]

    def get_nodes_in_radius(self, position: Tuple[int, int], radius: int) -> List[Node]:
        x, y = position
        nodes = []
        for i in range(x - radius, x + radius + 1):
            for j in range(y - radius, y + radius + 1):
                if 0 <= i < self.width and 0 <= j < self.height:
                    if self._get_distance(position, (i, j)) <= radius:
                        nodes.append(self.grid[i][j])
        return nodes
    
    def get_radius(self, source: Node, max_radius: int) -> Radius:
        nodes = self.get_nodes_in_radius(source.position.value, max_radius)
        return Radius(source=source, max_radius=max_radius, nodes=nodes)


    def _is_within_bounds(self, position: Tuple[int, int]) -> bool:
        x, y = position
        return 0 <= x < self.width and 0 <= y < self.height

    def _get_distance(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


    def raycast(self, source: Node, target: Node) -> Tuple[bool, List[Node]]:
        start = source.position.value
        end = target.position.value
        line_points = self.line(start, end)
        nodes = []
        for point in line_points:
            node = self.get_node(point)
            if node == source or node == target:
                continue
            if node.blocks_light:
                return False, nodes
            nodes.append(node)
        return True, nodes

    def get_raycast(self, source: Node, target: Node) -> RayCast:
        has_path, nodes = self.raycast(source, target)
        return RayCast(source=source, target=target, has_path=has_path, nodes=nodes)

    def shadow_casting(self, origin: Tuple[int, int], max_radius: int = None) -> List[Tuple[int, int]]:
        max_radius = max_radius or max(self.width, self.height)
        visible_cells = [origin]
        step_size = 0.5  # Decrease the step size for better accuracy
        for angle in range(int(360 / step_size)):  # Adjust the loop range based on the new step size
            visible_cells.extend(self.cast_light(origin, max_radius, math.radians(angle * step_size)))
        visible_cells = list(set(visible_cells))  # Take only unique values of visible cells
        return visible_cells

    def cast_light(self, origin: Tuple[int, int], max_radius: int, angle: float) -> List[Tuple[int, int]]:
        x0, y0 = origin
        x1 = x0 + int(max_radius * math.cos(angle))
        y1 = y0 + int(max_radius * math.sin(angle))
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        x, y = x0, y0
        n = 1 + dx + dy
        x_inc = 1 if x1 > x0 else -1
        y_inc = 1 if y1 > y0 else -1
        error = dx - dy
        dx *= 2
        dy *= 2
        line_points = []
        first_iteration = True
        for _ in range(n):
            if self._is_within_bounds((x, y)):
                line_points.append((x, y))
                if not first_iteration and self.get_node((x, y)).blocks_light:
                    break
            first_iteration = False
            if error > 0:
                x += x_inc
                error -= dy
            else:
                y += y_inc
                error += dx
        return line_points

    def line(self, start: Tuple[int, int], end: Tuple[int, int]) -> List[Tuple[int, int]]:
        dx, dy = end[0] - start[0], end[1] - start[1]
        distance = math.sqrt(dx * dx + dy * dy)
        angle = math.atan2(dy, dx)
        return self.cast_light(start, math.ceil(distance), angle)

    def line_of_sight(self, start: Tuple[int, int], end: Tuple[int, int]) -> Tuple[bool, List[Tuple[int, int]]]:
        line_points = self.line(start, end)
        visible_points = []
        for point in line_points[1:]:  # Skip the starting point and iterate through the rest of the points
            if self.get_node(point).blocks_light:
                return False, visible_points
            else:
                visible_points.append(point)
        return True, visible_points

    def get_shadow(self, source: Node, max_radius: int) -> Shadow:
        visible_cells = self.shadow_casting(source.position.value, max_radius)
        nodes = [self.get_node(cell) for cell in visible_cells]
        return Shadow(source=source, max_radius=max_radius, nodes=nodes)
    
    def convert_summarized_payload(self, summarized_payload: SummarizedActionPayload) -> ActionsPayload:
        source_entity_result = self.find_entity(summarized_payload.source_entity_type, summarized_payload.source_entity_position,
                                                summarized_payload.source_entity_id, summarized_payload.source_entity_name,
                                                summarized_payload.source_entity_attributes)
        target_entity_result = self.find_entity(summarized_payload.target_entity_type, summarized_payload.target_entity_position,
                                                summarized_payload.target_entity_id, summarized_payload.target_entity_name,
                                                summarized_payload.target_entity_attributes)

        if isinstance(source_entity_result, AmbiguousEntityError):
            raise ActionConversionError(
                message=f"Unable to find source entity: {summarized_payload.source_entity_type} at position {summarized_payload.source_entity_position}",
                source_entity_error=source_entity_result
            )
        if isinstance(target_entity_result, AmbiguousEntityError):
            raise ActionConversionError(
                message=f"Unable to find target entity: {summarized_payload.target_entity_type} at position {summarized_payload.target_entity_position}",
                target_entity_error=target_entity_result
            )

        source_entity = source_entity_result
        target_entity = target_entity_result

        if source_entity is None:
            raise ActionConversionError(
                message=f"Unable to find source entity: {summarized_payload.source_entity_type} at position {summarized_payload.source_entity_position}"
            )
        if target_entity is None:
            raise ActionConversionError(
                message=f"Unable to find target entity: {summarized_payload.target_entity_type} at position {summarized_payload.target_entity_position}"
            )

        action_class = self.actions.get(summarized_payload.action_name)
        if action_class is None:
            raise ActionConversionError(message=f"Action '{summarized_payload.action_name}' not found")

        action_instance = ActionInstance(source_id=source_entity.id, target_id=target_entity.id, action=action_class())
        return ActionsPayload(actions=[action_instance])
    
    def apply_actions_payload(self, payload: ActionsPayload) -> ActionsResults:
        results = []
        if len(payload.actions) > 0:
            print(f"Applying {len(payload.actions)} actions")
        for action_instance in payload.actions:
            source = GameEntity.get_instance(action_instance.source_id)
            target = GameEntity.get_instance(action_instance.target_id)
            action = action_instance.action

            state_before = {
                "source": source.get_state(),
                "target": target.get_state()
            }

            if action.is_applicable(source, target):
                try:
                    updated_source, updated_target = action.apply(source, target)
                    # Handle inventory-related updates
                    if updated_source.stored_in != source.stored_in:
                        if source.stored_in and source in source.stored_in.inventory:
                            source.stored_in.inventory.remove(source)
                        if updated_source.stored_in:
                            updated_source.stored_in.inventory.append(updated_source)
                    if updated_target.stored_in != target.stored_in:
                        if target.stored_in and target in target.stored_in.inventory:
                            target.stored_in.inventory.remove(target)
                        if updated_target.stored_in:
                            updated_target.stored_in.inventory.append(updated_target)

                    state_after = {
                        "source": updated_source.get_state(),
                        "target": updated_target.get_state()
                    }
                    results.append(ActionResult(action_instance=action_instance, success=True, state_before=state_before, state_after=state_after))
                except ValueError as e:
                    results.append(ActionResult(action_instance=action_instance, success=False, error=str(e), state_before=state_before))
            else:
                # Check which prerequisite failed and provide a detailed error message
                failed_prerequisites = []
                for statement in action.prerequisites.source_statements:
                    if not statement.validate_condition(source):
                        failed_prerequisites.append(f"Source prerequisite failed: {statement}")
                for statement in action.prerequisites.target_statements:
                    if not statement.validate_condition(target):
                        failed_prerequisites.append(f"Target prerequisite failed: {statement}")
                for statement in action.prerequisites.source_target_statements:
                    if not statement.validate_comparisons(source, target):
                        failed_prerequisites.append(f"Source-Target prerequisite failed: {statement}")
                error_message = "Prerequisites not met:\n" + "\n".join(failed_prerequisites)
                results.append(ActionResult(action_instance=action_instance, success=False, error=error_message, state_before=state_before))

        return ActionsResults(results=results)
    
    def print_grid(self, path: Optional[Path] = None, radius: Optional[Radius] = None, shadow: Optional[Shadow] = None, raycast: Optional[RayCast] = None):
        for y in range(self.height):
            row = ""
            for x in range(self.width):
                node = self.grid[x][y]
                if node.blocks_movement:
                    row += "# "
                elif path and node == path.nodes[0]:
                    row += "\033[92mS\033[0m "  # Green color for start
                elif path and node == path.nodes[-1]:
                    row += "\033[91mG\033[0m "  # Red color for goal
                elif path and node in path.nodes:
                    row += "\033[93m*\033[0m "  # Orange color for path
                elif radius and node in radius.nodes:
                    row += "\033[92mR\033[0m "  # Green color for radius
                elif shadow and node == shadow.source:
                    row += "\033[94mS\033[0m "  # Blue color for shadow source
                elif shadow and node in shadow.nodes:
                    row += "\033[92m+\033[0m "  # Green color for shadow
                elif raycast and node in raycast.nodes:
                    row += "\033[92mR\033[0m "  # Green color for raycast
                # elif node.entities:
                #     row += "E "
                else:
                    row += ". "
            print(row)

---

