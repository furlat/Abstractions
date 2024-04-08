# Observation Representation Design Document

## Introduction
This document provides a detailed explanation of the design ideas and components behind our Observation Representation for the game world. The Observation Representation is a structured textual format that encapsulates the current state of the game world from the character's perspective. It is designed to provide the agent with a comprehensive understanding of its surroundings, including spatial information, entity attributes, and high-level insights.

## Design Principles
The Observation Representation is designed with the following key principles in mind:

1. **Clarity and Readability**: The representation should be easy to understand and parse, both for the agent and for human readers. It uses a structured format with clear sections and indentation to improve readability.

2. **Comprehensive Information**: The representation aims to provide a complete picture of the game world, including the character's state, immediate surroundings, entity attributes, spatial relationships, and high-level insights. It includes both egocentric and absolute spatial information to facilitate the agent's decision-making process.

3. **Modularity and Extensibility**: The representation is divided into distinct sections, each focusing on a specific aspect of the game world. This modular structure allows for easy extension and modification of the representation as the game world evolves.

4. **Efficiency and Compression**: The representation employs techniques like equivalence classes and rectangular regions to compress spatial information and reduce redundancy. This helps in managing the size of the observation and improving processing efficiency.

5. **Cognitive Friendliness**: The representation includes high-level insights and summaries to provide the agent with a more intuitive understanding of the game world. These insights highlight important aspects of the environment and potential objectives or challenges.

## Observation Representation Components
The Observation Representation consists of the following main components:

1. **Introduction**: A brief overview of the observation representation and its structure.

2. **Character Summary**: Provides an overview of the character's position and key attributes.

3. **Immediate Neighbors**: Describes the 3x3 grid surrounding the character, including the node status, the entities present in each cell, and their absolute positions.

4. **Node Equivalence Classes**: Groups similar nodes into equivalence classes based on the combination of entities they contain and their attributes, excluding living entities. Each entity's attributes are listed on a new line, along with a node-level summary of the spatial attributes.

5. **Living Entities**: Provides information about the living entities in the visible area, excluding the character.

6. **Movement Sub-Goal**: Specifies the character's current movement sub-goal, including the target position and a brief description.

7. **Attribute Summary**: Summarizes the blocking properties of nodes in the visible area.

8. **Pathfinding Information**: Provides information about reachable nodes and the shortest path to the movement sub-goal.

9. **Cognitive Insights**: Offers high-level observations and insights about the game world and the character's current situation.

### 1. Introduction
The introduction serves as a brief overview of the observation representation and its structure. It outlines the main sections of the representation and their purpose. This helps the agent (or a human reader) understand the organization and content of the observation.

Example:
```
# Introduction
This observation represents the current state of the game world from the character's perspective. It includes the following sections:

1. Character Summary: Provides an overview of the character's position and key attributes.
2. Immediate Neighbors: Describes the 3x3 grid surrounding the character, including the node status, the entities present in each cell, and their absolute positions.
3. Node Equivalence Classes: Groups similar nodes into equivalence classes based on the combination of entities they contain and their attributes, excluding living entities. Each entity's attributes are listed on a new line, along with a node-level summary of the spatial attributes.
4. Living Entities: Provides information about the living entities in the visible area, excluding the character.
5. Movement Sub-Goal: Specifies the character's current movement sub-goal, including the target position and a brief description.
6. Attribute Summary: Summarizes the blocking properties of nodes in the visible area.
7. Pathfinding Information: Provides information about reachable nodes and the shortest path to the movement sub-goal.
8. Cognitive Insights: Offers high-level observations and insights about the game world and the character's current situation.
```

Explanation:
- The introduction starts with a heading (`# Introduction`) to clearly identify the section.
- It provides a brief description of what the observation represents (the current state of the game world from the character's perspective).
- It lists the main sections of the observation representation, along with a short description of each section's purpose.
- The introduction helps the agent understand the structure and content of the observation, making it easier to navigate and extract relevant information.

### 2. Character Summary
The Character Summary section provides an overview of the character's position and key attributes. It includes the character's current position in the game world and a list of important attributes that define the character's state.

Example:
```
# Character Summary
Position: (4, 1)
Key Attributes:
- AttackPower: 10
- Health: 100
- MaxHealth: 100
- CanAct: True
```

Explanation:
- The section starts with a heading (`# Character Summary`) to identify the section.
- The `Position` field indicates the character's current position in the game world, represented as a tuple of coordinates (x, y).
- The `Key Attributes` field lists the important attributes of the character, such as:
  - `AttackPower`: The character's attack power, which determines the damage it can inflict on other entities.
  - `Health`: The character's current health points.
  - `MaxHealth`: The character's maximum health points.
  - `CanAct`: A boolean value indicating whether the character can perform actions in the current turn.
- The Character Summary provides a quick overview of the character's state, allowing the agent to assess its current situation and make informed decisions based on its attributes.

### 3. Immediate Neighbors
The Immediate Neighbors section describes the 3x3 grid surrounding the character, including the node status, the entities present in each cell, and their absolute positions. It provides a detailed view of the character's immediate surroundings.

Example:
```
# Immediate Neighbors (3x3 Grid)
- NW (3, 0): Node (Blocks Movement, Blocks Light), Entities: [Wall, Floor]
- N (4, 0): Node (Blocks Movement, Blocks Light), Entities: [Wall, Floor]
- NE (5, 0): Node (Blocks Movement, Blocks Light), Entities: [Wall, Floor]
- W (3, 1): Node (Passable), Entities: [Floor]
- C (4, 1): Node (Passable), Entities: [Character, Floor]
- E (5, 1): Node (Passable), Entities: [Floor]
- SW (3, 2): Node (Passable), Entities: [Floor]
- S (4, 2): Node (Blocks Movement, Blocks Light), Entities: [Door (Locked, Requires Golden Key), Floor]
- SE (5, 2): Node (Passable), Entities: [Floor]
```

Explanation:
- The section starts with a heading (`# Immediate Neighbors (3x3 Grid)`) to identify the section and specify the size of the grid.
- Each line represents a cell in the 3x3 grid surrounding the character.
- The cell is identified by its cardinal direction relative to the character (e.g., NW, N, NE, W, C, E, SW, S, SE).
- The absolute position of each cell is provided in parentheses next to the cardinal direction, representing the coordinates (x, y) in the game world.
- Each cell contains information about the node status and the entities present in that cell.
- The node status indicates whether the node blocks movement and/or light, represented as `Node (Blocks Movement, Blocks Light)` or `Node (Passable)`.
- The entities present in each cell are listed after `Entities:`, enclosed in square brackets.
- Entities can include walls, floors, doors, the character itself, and other game objects.
- Special properties of entities, such as a locked door requiring a specific key, are mentioned in parentheses after the entity name.
- The Immediate Neighbors section provides a detailed view of the character's surroundings, allowing the agent to assess the spatial layout, obstacles, and potential interactions in its immediate vicinity.

### 4. Node Equivalence Classes
The Node Equivalence Classes section groups similar nodes into equivalence classes based on the combination of entities they contain and their attributes, excluding living entities. It provides a compressed representation of the spatial information in the game world.

Example:
```
# Node Equivalence Classes
- Floor:
  - Rectangles: [((0, 0), (2, 3)), ((8, 0), (10, 2)), ((2, 0), (2, 2)), ((3, 0), (3, 2)), ((5, 0), (5, 2)), ((6, 0), (6, 2)), ((7, 0), (7, 2))]
  - Points: [(4, 0), (9, 2)]
  - Node Attributes:
    - BlocksLight: False
    - BlocksMovement: False
  - Entity Attributes:
    - Material: ''
- Wall and Floor:
  - Rectangles: [((3, 2), (5, 2)), ((6, 2), (8, 2))]
  - Node Attributes:
    - BlocksLight: True
    - BlocksMovement: True
  - Entity Attributes:
    - Wall:
      - BlocksLight: True
      - BlocksMovement: True
      - Material: ''
    - Floor:
      - BlocksLight: False
      - BlocksMovement: False
      - Material: ''
- Door and Floor:
  - Position: (5, 2)
  - Node Attributes:
    - BlocksLight: True
    - BlocksMovement: True
  - Entity Attributes:
    - Door:
      - BlocksLight: True
      - BlocksMovement: True
      - Material: ''
      - Open: False
      - is_locked: True
      - required_key: 'Golden Key'
    - Floor:
      - BlocksLight: False
      - BlocksMovement: False
      - Material: ''
```

Explanation:
- The section starts with a heading (`# Node Equivalence Classes`) to identify the section.
- Each equivalence class represents a group of nodes that share similar properties and entities.
- The equivalence classes are defined based on the combination of entities present in the nodes, such as Floor, Wall and Floor, Door and Floor, etc.
- For each equivalence class, the spatial information is compressed using rectangles and points.
  - `Rectangles` represent contiguous regions of nodes belonging to the equivalence class, specified as a list of tuples indicating the top-left and bottom-right coordinates of each rectangle.
  - `Points` represent individual nodes that belong to the equivalence class but do not form a contiguous region, specified as a list of tuples indicating the coordinates of each point.
- The `Node Attributes` section within each equivalence class summarizes the blocking properties of the nodes, such as `BlocksLight` and `BlocksMovement`, indicating whether the nodes block light and movement, respectively.
- The `Entity Attributes` section within each equivalence class lists the attributes of each entity type present in the nodes.
  - Each entity type (e.g., Wall, Floor, Door) is listed along with its specific attributes.
  - Attributes can include properties like `BlocksLight`, `BlocksMovement`, `Material`, `Open`, `is_locked`, `required_key`, etc., depending on the entity type.
- The Node Equivalence Classes section provides a compressed representation of the spatial information, reducing redundancy and allowing for efficient processing and reasoning about the game world.

### 5. Living Entities
The Living Entities section provides information about the living entities in the visible area, excluding the character. It includes the position and attributes of each living entity.

Example:
```
# Living Entities
- Character and Floor:
  - Position: (4, 1)
  - Character Attributes:
    - AttackPower: 10
    - BlocksLight: False
    - BlocksMovement: False
    - CanAct: True
    - Health: 100
    - MaxHealth: 100
  - Floor Attributes:
    - BlocksLight: False
    - BlocksMovement: False
    - Material: ''
```

Explanation:
- The section starts with a heading (`# Living Entities`) to identify the section.
- Each living entity is listed along with its position and attributes.
- In this example, there is only one living entity: the character itself, represented as `Character and Floor`.
- The `Position` field indicates the current position of the living entity in the game world, represented as a tuple of coordinates (x, y).
- The `Character Attributes` section lists the specific attributes of the character, such as `AttackPower`, `BlocksLight`, `BlocksMovement`, `CanAct`, `Health`, and `MaxHealth`.
- The `Floor Attributes` section lists the attributes of the floor entity on which the character is standing, such as `BlocksLight`, `BlocksMovement`, and `Material`.
- The Living Entities section provides information about the dynamic and interactive entities in the game world, allowing the agent to track their positions and attributes for decision-making and interaction.

### 6. Movement Sub-Goal
The Movement Sub-Goal section specifies the character's current movement sub-goal, including the target position and a brief description. It provides information about the character's immediate or short-term movement objective.

Example:
```
# Movement Sub-Goal
- Position: (6, 9)
- Description: Reach the end of the corridor
```

Explanation:
- The section starts with a heading (`# Movement Sub-Goal`) to identify the section.
- The `Position` field indicates the target position of the movement sub-goal, represented as a tuple of coordinates (x, y).
- The `Description` field provides a brief textual description of the movement sub-goal, giving context or purpose to the target position.
- The Movement Sub-Goal section helps the agent understand its current movement objective and guides its pathfinding and navigation decisions.

### 7. Attribute Summary
The Attribute Summary section summarizes the blocking properties of nodes in the visible area. It provides a high-level overview of the nodes that block movement and light.

Example:
```
# Attribute Summary
- Blocks Movement: Wall and Floor (8 cells), Door and Floor (1 cell, Locked)
- Blocks Light: Wall and Floor (8 cells), Door and Floor (1 cell, Locked)
```

Explanation:
- The section starts with a heading (`# Attribute Summary`) to identify the section.
- The `Blocks Movement` field lists the equivalence classes of nodes that block movement, along with the number of cells belonging to each class.
- The `Blocks Light` field lists the equivalence classes of nodes that block light, along with the number of cells belonging to each class.
- Additional information, such as the locked state of a door, is mentioned in parentheses after the equivalence class.
- The Attribute Summary section provides a quick overview of the blocking properties of nodes in the visible area, helping the agent assess the navigability and visibility of the environment.

### 8. Pathfinding Information
The Pathfinding Information section provides information about reachable nodes and the shortest path to the movement sub-goal. It helps the agent understand the connectivity and optimal path to its current objective.

Example:
```
# Pathfinding Information
- Reachable Nodes: 25
- Shortest Path to Movement Sub-Goal:
  - Length: 10
  - Path: (4, 1) -> (4, 2) -> (5, 2) -> (6, 2) -> (6, 3) -> (6, 4) -> (6, 5) -> (6, 6) -> (6, 7) -> (6, 8) -> (6, 9)
```

Explanation:
- The section starts with a heading (`# Pathfinding Information`) to identify the section.
- The `Reachable Nodes` field indicates the total number of nodes that are reachable from the character's current position, considering the blocking properties of nodes.
- The `Shortest Path to Movement Sub-Goal` field provides information about the optimal path from the character's current position to the movement sub-goal.
  - The `Length` field indicates the number of steps required to reach the movement sub-goal following the shortest path.
  - The `Path` field lists the sequence of positions (represented as tuples of coordinates) that form the shortest path from the character's current position to the movement sub-goal.
- The Pathfinding Information section helps the agent understand the connectivity of the environment and plan its movements efficiently towards the current objective.

### 9. Cognitive Insights
The Cognitive Insights section offers high-level observations and insights about the game world and the character's current situation. It provides a more intuitive and summarized understanding of the environment, highlighting important aspects and potential challenges or objectives.

Example:
```
# Cognitive Insights
- The character is surrounded by passable floor tiles, except for walls to the north and a locked door to the south.
- The majority of the visible area consists of floor tiles, with walls forming rectangular barriers.
- The locked door requires a specific key (Golden Key) to be opened, indicating a potential objective or challenge.
- The character has a clear path to the movement sub-goal, which can be reached by navigating around the walls and through the locked door once the key is obtained.
```

Explanation:
- The section starts with a heading (`# Cognitive Insights`) to identify the section.
- Each insight is presented as a bullet point, providing a concise and meaningful observation about the game world or the character's situation.
- The insights can cover various aspects, such as:
  - The character's immediate surroundings and the types of tiles or entities present.
  - The presence of obstacles, barriers, or special entities that may impact navigation or interaction.
  - Potential objectives, challenges, or key items required to progress, such as a locked door requiring a specific key.
  - The overall path or strategy to reach the current movement sub-goal, considering the obstacles and requirements.
- The Cognitive Insights section aims to provide the agent with a higher-level understanding of the game world, helping it make more informed decisions and plan its actions based on the key aspects of the environment.

## Prompt Generation
To generate the observation representation prompt, follow these steps:

1. Begin with the Introduction section, providing an overview of the observation representation and its structure.

2. Generate the Character Summary section, including the character's current position and key attributes.

3. Generate the Immediate Neighbors section, describing the 3x3 grid surrounding the character. For each cell, include the cardinal direction, absolute position, node status, and the entities present.

4. Generate the Node Equivalence Classes section, grouping similar nodes based on the combination of entities and their attributes. For each equivalence class, provide the spatial information using rectangles and points, along with the node attributes and entity attributes.

5. Generate the Living Entities section, listing the living entities in the visible area (excluding the character) along with their positions and attributes.

6. Generate the Movement Sub-Goal section, specifying the character's current movement sub-goal with the target position and a brief description.

7. Generate the Attribute Summary section, summarizing the blocking properties of nodes in the visible area, including the equivalence classes that block movement and light.

8. Generate the Pathfinding Information section, providing the number of reachable nodes and the shortest path to the movement sub-goal, including the path length and the sequence of positions.

9. Generate the Cognitive Insights section, offering high-level observations and insights about the game world and the character's current situation, highlighting important aspects and potential challenges or objectives.

10. Combine all the generated sections to form the complete observation representation prompt.

## Conclusion
The Observation Representation design document provides a comprehensive guide to understanding the structure, components, and generation process of the observation prompt. By following the design principles and leveraging the detailed explanations and examples provided for each section, it is possible to implement the prompt generation method accurately and efficiently.

The observation representation is designed to provide the agent with a clear, informative, and cognitively friendly view of the game world, enabling it to make informed decisions and navigate the environment effectively. The modular structure and the use of techniques like equivalence classes and spatial compression contribute to the overall efficiency and extensibility of the representation.

By adhering to this design document, we can ensure a consistent and reliable generation of observation prompts that facilitate the agent's learning and decision-making processes within the game world.

Signed,
GridMapWeaver
