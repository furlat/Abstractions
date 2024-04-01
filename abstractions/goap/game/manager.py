import pygame
import pygame_gui

from typing import List, Tuple, Set, Optional
from abstractions.goap.spatial import GridMap, Path, Shadow, RayCast, Radius, Node, GameEntity, ActionsResults,ActionResult,ActionsPayload,SummarizedActionPayload
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
    
    def handle_action_payload_submission(self, action_payload_json:str):
        try:
            summarized_payload = SummarizedActionPayload.model_validate_json(action_payload_json)
            actions_payload = self.grid_map.convert_summarized_payload(summarized_payload)
            if isinstance(actions_payload, ActionsPayload):
                self.input_handler.actions_payload.actions.extend(actions_payload.actions)
            else:
                print(f"Action Conversion Error: {actions_payload}")
        except ValidationError as e:
            print(f"Invalid action payload: {e}")
            
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
                if self.input_handler.llm_action_payload is not None:
                    self.handle_action_payload_submission(self.input_handler.llm_action_payload)
                    self.input_handler.llm_action_payload = None
                

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
                self.update_observation_logs(shadow,mode="groups",use_egoncentric=False)
                

            
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