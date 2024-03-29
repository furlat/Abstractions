import pygame
from abstractions.goap.spatial import GridMap, GameEntity, Node, Attribute, BlocksMovement, BlocksLight
import os
from abstractions.goap.interactions import Character, Door, Key, Treasure, Floor, InanimateEntity, IsPickupable, TestItem
from abstractions.goap.game.payloadgen import PayloadGenerator, SpriteMapping
from abstractions.goap.game.renderer import Renderer, GridMapVisual, NodeVisual, EntityVisual, CameraControl
from abstractions.goap.game.input_handler import InputHandler
from pydantic import ValidationError

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
    treasure = Treasure(name="Treasure", monetary_value=Attribute(name="monetary_value", value=1000))

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
    grid_map = GridMap(width=30, height=30)
    room_width, room_height = 6, 6
    character, door, key, treasure = generate_dungeon(grid_map, room_width, room_height)

    # Define the sprite mappings
    sprite_mappings = [
        SpriteMapping(entity_type=Character, sprite_path=os.path.join(BASE_PATH, "sprites", "character_agent.png"), ascii_char="@", draw_order=3),
        SpriteMapping(entity_type=Door, sprite_path=os.path.join(BASE_PATH, "sprites", "closed_door.png"), ascii_char="D", draw_order=2),
        SpriteMapping(entity_type=Key, sprite_path=os.path.join(BASE_PATH, "sprites", "lock.png"), ascii_char="K", draw_order=1),
        SpriteMapping(entity_type=Treasure, sprite_path=os.path.join(BASE_PATH, "sprites", "filled_storage.png"), ascii_char="T", draw_order=1),
        SpriteMapping(entity_type=Floor, sprite_path=os.path.join(BASE_PATH, "sprites", "floor.png"), ascii_char=".", draw_order=0),
        SpriteMapping(entity_type=TestItem, sprite_path=os.path.join(BASE_PATH, "sprites", "filled_storage.png"), ascii_char="$", draw_order=1),
        SpriteMapping(entity_type=GameEntity, name_pattern=r"^Wall", sprite_path=os.path.join(BASE_PATH, "sprites", "wall.png"), ascii_char="#", draw_order=1),
    ]

    # Create the payload generator
    payload_generator = PayloadGenerator(sprite_mappings, grid_size=(grid_map.width, grid_map.height))

    # Generate the payload
    nodes = [node for row in grid_map.grid for node in row]
    payload = payload_generator.generate_payload(nodes)

    # Create the grid map visual
    grid_map_visual = GridMapVisual(
        width=grid_map.width,
        height=grid_map.height,
        node_visuals={pos: NodeVisual(entity_visuals=[EntityVisual(**entity_data) for entity_data in entity_data_list]) for pos, entity_data_list in payload.items()}
    )

    # Create the renderer
    renderer = Renderer(screen, grid_map_visual, widget_size=(800, 600))

    # Create the input handler
    input_handler = InputHandler(grid_map)
    input_handler.active_entities.controlled_entity_id = character.id

    # Game loop
    running = True
    clock = pygame.time.Clock()
    while running:
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEMOTION:
                input_handler.handle_mouse_motion(event.pos, renderer.grid_map_widget.camera_pos, renderer.grid_map_widget.cell_size)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                input_handler.handle_mouse_click(event.button, event.pos, renderer.grid_map_widget.camera_pos, renderer.grid_map_widget.cell_size)
            else:
                input_handler.handle_input(event)

        # Update the camera control based on input
        renderer.handle_camera_control(input_handler.camera_control)

        # Get the controlled entity and target node
        controlled_entity = GameEntity.get_instance(input_handler.active_entities.controlled_entity_id)
        target_node = Node.get_instance(input_handler.active_entities.targeted_node_id) if input_handler.active_entities.targeted_node_id else None

        # Calculate the radius, shadow, and raycast based on the controlled entity's position
        radius = grid_map.get_radius(controlled_entity.node, max_radius=5)
        shadow = grid_map.get_shadow(controlled_entity.node, max_radius=10)
        try:
            raycast = grid_map.get_raycast(controlled_entity.node, target_node) if target_node else None
        except ValidationError as e:
            print(f"Error: {e}")
            raycast = None
        path = grid_map.a_star(controlled_entity.node, target_node) if target_node else None

        # Update the renderer with the necessary data
        inventory = Character.get_instance(character.id).inventory
        target = input_handler.active_entities.targeted_entity_id
        controlled_entity_node = controlled_entity.node
        if controlled_entity_node:
            player_position = controlled_entity_node.position.value
            renderer.update(inventory, target, player_position)
        else:
            renderer.update(inventory, target)

        # Apply the action payload to the grid map
        actions_results = grid_map.apply_actions_payload(input_handler.actions_payload)
        if actions_results.results:
            for result in actions_results.results:
                if result.success:
                    # Update the payload and renderer if the action was successful
                    payload = payload_generator.generate_payload(nodes)
                    renderer.update_grid_map_visual(GridMapVisual(
                        width=grid_map.width,
                        height=grid_map.height,
                        node_visuals={pos: NodeVisual(entity_visuals=[EntityVisual(**entity_data) for entity_data in entity_data_list]) for pos, entity_data_list in payload.items()}
                    ))
                else:
                    print(f"Action failed: {result.error}")

        # Render the game
        renderer.render(path=path, shadow=shadow, raycast=raycast, radius=radius, fog_of_war=shadow)

        # Reset the camera control and actions payload
        input_handler.reset_camera_control()
        input_handler.reset_actions_payload()

        # Limit the frame rate to 60 FPS
        clock.tick(60)

        # Display FPS
        fps = clock.get_fps()
        fps_text = renderer.grid_map_widget.font.render(f"FPS: {fps:.2f}", True, (255, 255, 255))
        renderer.screen.blit(fps_text, (10, 10))
        pygame.display.flip()

    # Quit Pygame
    pygame.quit()
if __name__ == "__main__":
    main()