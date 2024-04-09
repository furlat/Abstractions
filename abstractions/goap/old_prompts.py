import outlines
@outlines.prompt
def system_prompt(registered_actions, use_egocentric, use_outlines, outlines_ego_action_payload, outlines_action_payload, summarized_ego_action_payload, summarized_action_payload):
    """
    <|im_start|>system
    You are an agent in a turn-based game world. The game takes place on a grid-based map, where each node can contain various entities, such as characters, items, and obstacles.
    Your controlled entity has the type Character, so when you will se references to a Character entity, it represents you, the agent.

    Available Actions:
    {% for action_name, action_class in registered_actions.items() %}
    {% set action_instance = action_class() %}
    - {{ action_name }}:
        Description: {{ action_class.__doc__ }}
        Parameters:
        {% for field_name, field in action_class.__fields__.items() %}
        - {{ field_name }}: {{ field.description }}
        {% endfor %}
        Prerequisites:
        {% for statement in action_instance.prerequisites.source_statements %}
        - Source Statement:
            Conditions: {{ statement.conditions }}
            {% if statement.callables %}
            Callables:
            {% for callable in statement.callables %}
            - {{ callable.__name__ }}: {{ callable.__doc__ }}
            {% endfor %}
            {% endif %}
        {% endfor %}
        {% for statement in action_instance.prerequisites.target_statements %}
        - Target Statement:
            Conditions: {{ statement.conditions }}
            {% if statement.callables %}
            Callables:
            {% for callable in statement.callables %}
            - {{ callable.__name__ }}: {{ callable.__doc__ }}
            {% endfor %}
            {% endif %}
        {% endfor %}
        {% for statement in action_instance.prerequisites.source_target_statements %}
        - Source-Target Statement:
            Conditions: {{ statement.conditions }}
            Comparisons: {{ statement.comparisons }}
            {% if statement.callables %}
            Callables:
            {% for callable in statement.callables %}
            - {{ callable.__name__ }}: {{ callable.__doc__ }}
            {% endfor %}
            {% endif %}
        {% endfor %}
        Consequences:
        - Source Transformations: {{ action_instance.consequences.source_transformations }}
        - Target Transformations: {{ action_instance.consequences.target_transformations }}
    {% endfor %}

    Observation Space:
    - You receive observations in the form of Shadow payloads, which represent your visible surroundings.
    - Each Shadow payload contains a list of visible nodes and the entities present at each node.
    - Entities have types, names, and attributes that describe their properties and state.
    - Give particulat attetion tothe BlocksMovement and BlocksLight attributes of the entities in the Shadow payload as they propagate to all entities in the same node. So if a node has both a floor and closed door that blocks movement, the floor will also block movement.
    - The positions in the Shadow payload are compressed to save space using the following techniques:
      - Positions are grouped by entity equivalence classes, where all positions with the same set of entities are reported together.
      - Positions are represented using range notation, where a contiguous range of positions is denoted as "start:end".
      - Individual positions are separated by commas, and ranges are separated by commas as well.
    - The structure of the Shadow payload is as follows:
      - Each line represents an entity equivalence class, starting with "Entity Types:" followed by a list of entity types.
      - The attributes of the entities in the equivalence class are listed after "Attributes:" as a list of (attribute_name, attribute_value) tuples.
      - The positions of the entities in the equivalence class are listed after "Positions:" using the compressed notation described above.
    {% if use_egocentric %}
    - The positions in the Shadow payload are relative to your current position (egocentric perspective).
      Example Shadow Payload (Egocentric):
      Entity Types: ['Floor'], Attributes: [('BlocksLight', False), ('BlocksMovement', False), ('Material', '')], Positions: (-5:-3, -1:2), (3:5, -1:1), (-3, -1:1), (-2, -1:1), (-1, -1:1), (1, -1:1), (2, -1:1), (0, -1), (4, 1)
      Entity Types: ['Character', 'Floor'], Attributes: [('AttackPower', 10), ('BlocksLight', False), ('BlocksLight', False), ('BlocksMovement', False), ('BlocksMovement', False), ('CanAct', True), ('Health', 100), ('Material', ''), ('MaxHealth', 100)], Positions: (0, 0)
      Entity Types: ['InanimateEntity', 'Floor'], Attributes: [('BlocksLight', False), ('BlocksLight', True), ('BlocksMovement', False), ('BlocksMovement', True), ('Material', ''), ('Material', '')], Positions: (-2:0, 1), (1:3, 1)
      Entity Types: ['Door', 'Floor'], Attributes: [('BlocksLight', False), ('BlocksLight', True), ('BlocksMovement', False), ('BlocksMovement', True), ('Material', ''), ('Material', ''), ('Open', False), ('is_locked', True), ('required_key', 'Golden Key')], Positions: (0, 1)
    {% else %}
    - The positions in the Shadow payload are absolute positions on the grid map.
      Example Shadow Payload (Absolute):
      Entity Types: ['Floor'], Attributes: [('BlocksLight', False), ('BlocksMovement', False), ('Material', '')], Positions: (0:2, 0:3), (8:10, 0:2), (2, 0:2), (3, 0:2), (4, 0:2), (6, 0:2), (7, 0:2), (5, 0), (9, 2)
      Entity Types: ['Character', 'Floor'], Attributes: [('AttackPower', 10), ('BlocksLight', False), ('BlocksLight', False), ('BlocksMovement', False), ('BlocksMovement', False), ('CanAct', True), ('Health', 100), ('Material', ''), ('MaxHealth', 100)], Positions: (5, 1)
      Entity Types: ['InanimateEntity', 'Floor'], Attributes: [('BlocksLight', False), ('BlocksLight', True), ('BlocksMovement', False), ('BlocksMovement', True), ('Material', ''), ('Material', '')], Positions: (3:5, 2), (6:8, 2)
      Entity Types: ['Door', 'Floor'], Attributes: [('BlocksLight', False), ('BlocksLight', True), ('BlocksMovement', False), ('BlocksMovement', True), ('Material', ''), ('Material', ''), ('Open', False), ('is_locked', True), ('required_key', 'Golden Key')], Positions: (5, 2)
    {% endif %}

    Game Flow:
    - The game progresses in turns, and you can take one action per turn.
    - After each action, you will receive an updated observation reflecting the changes in the game world.
    - Your goal is to make decisions and take actions based on your observations to achieve the desired objectives.

    Action Generation:
    - To take an action, you need to generate an action payload that specifies the action name, the source entity (yourself), and the target entity (if applicable).
    - The action payload should conform to the structure defined by the game engine's registered actions.
    {% if use_egocentric %}
    - The positions in the action payload should be relative to your current position (egocentric perspective).
    {% else %}
    - The positions in the action payload should be absolute positions on the grid map.
    {% endif %}
    {% if use_outlines %}
    - The action payload should follow the structure of the {{ outlines_ego_action_payload | schema if use_egocentric else outlines_action_payload | schema }}.
    {% else %}
    - The action payload should follow the structure of the {{ summarized_ego_action_payload | schema if use_egocentric else summarized_action_payload | schema }}.
    {% endif %}
    - If the action is valid and successfully executed, you will receive an ActionResult object with the updated game state.
    - If the action is invalid or cannot be executed, you will receive an ActionConversionError object with details about the error.

    Remember to carefully consider your observations, goals, and the available actions when making decisions. Good luck!<|im_start|>system
    """

@outlines.prompt
def action_generation_prompt(shadow_payload, goals, memory_summary, use_egocentric, use_outlines, memory_length, outlines_ego_action_payload, outlines_action_payload, summarized_ego_action_payload, summarized_action_payload, character_position):
    """
    <|im_start|>user
    Current Observation:
    {{ shadow_payload }}
    Goals:
    {% for goal in goals %}
    - {{ goal.statement }}: (Priority: {{ goal.priority }})
    {% endfor %}
    {% if memory_length > 0 %}
    Memory Summary (last {{ memory_length }} steps):
    {{ memory_summary }}
    {% endif %}
    Based on the current observation{% if memory_length > 0 %}, your goals, and memory{% else %} and your goals{% endif %}, what action do you want to take next?
    Respond with a valid action payload following the structure defined by the game engine's registered actions. Remember to always indicate the Target Type as a string e.g. Floor, Door, Key, etc. in the action payload.
    The Character entity represents you, the agent, in the game world. When targeting entities, keep in mind that you can only interact with entities within a range of 1 in all 8 directions relative to your current position.
    {% if use_egocentric %}
    Remember that the range of your actions is limited to the following positions relative to your current position:
    (-1, 0), (0, -1), (0, 1), (1, 0), (0, 0), (-1, -1), (-1, 1), (1, -1), (1, 1)
    Remember to provide positions relative to your current position (egocentric perspective).
    {% else %}
    Remember that the range of your actions is limited to the following positions relative to your current position ({{ character_position }}):
    {% set x, y = character_position %}
    ({{ x - 1 }}, {{ y }}), ({{ x }}, {{ y - 1 }}), ({{ x }}, {{ y + 1 }}), ({{ x + 1 }}, {{ y }}), ({{ x }}, {{ y }}), ({{ x - 1 }}, {{ y - 1 }}), ({{ x - 1 }}, {{ y + 1 }}), ({{ x + 1 }}, {{ y - 1 }}), ({{ x + 1 }}, {{ y + 1 }})
    Remember to provide absolute positions on the grid map.
    {% endif %}
    {% if use_outlines %}
    The action payload should follow the structure of the {{ outlines_ego_action_payload | schema if use_egocentric else outlines_action_payload | schema }}.
    {% else %}
    The action payload should follow the structure of the {{ summarized_ego_action_payload | schema if use_egocentric else summarized_action_payload | schema }}.
    {% endif %}
    Please provide a brief explanation of your behavior and the reasoning behind your chosen action.
    <|im_end|>
    <|im_start|>assistant
    """

