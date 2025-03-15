# CLAUDE.md - Abstractions Project Guide

## Project Files
- Entity implementation path: `/Users/tommasofurlanello/Documents/Dev/Abstractions/abstractions/ecs/entity.py`
- Old entity version: `/Users/tommasofurlanello/Documents/Dev/Abstractions/abstractions/ecs/old_entity.py`
- Graph entity design: `/Users/tommasofurlanello/Documents/Dev/Abstractions/abstractions/ecs/graph_entity.md`
- Test files: `/Users/tommasofurlanello/Documents/Dev/Abstractions/tests/`

## Environment
```bash
# Activate virtual environment
source /Users/tommasofurlanello/Documents/Dev/Abstractions/.venv/bin/activate

# Run all tests
python -m unittest discover

# Run specific test file
python -m unittest tests/test_entity.py
```

## Current Implementation Status
- **Basic Entity**: Fully implemented with hashability support for collections
- **EntityGraph**: Core structure implemented with node and edge management
- **Graph Construction**: Single-pass algorithm for efficient graph and ancestry path building
- **Entity Operations**: Support for update_ecs_ids, attach, and detach operations
- **Edge Classification**: Simple hierarchical edge marking for all edges (reference edges will be added later)
- **Circular References**: Error detection for circular entity references
- **Visualization**: Mermaid diagram generation for entity graphs
- **Ancestry Paths**: On-the-fly construction during graph traversal
- **Entity Registry**: Core EntityRegistry implementation with storage and retrieval
- **Versioning System**: Set-based diffing with hierarchical propagation for efficient versioning
- **Immutability**: Deep copy-based immutability for entities retrieved from registry

## Implementation Status
1. **Field Type Detection**: The `get_pydantic_field_type_entities` function has been enhanced to:
   - Work reliably for direct Entity fields and Optional[Entity]
   - Handle container types (List, Dict, etc.) even when they're empty
   - Leverage Pydantic's rich field metadata through direct access to `field_info.annotation`
   - Use a multi-layered approach that tries, in order:
     1. Pydantic field annotations (most reliable)
     2. Default factory inspection
     3. Runtime field value checking
     4. Python's type hint system (fallback)

2. **Container Entity Processing**: The graph building algorithm:
   - Uses the improved field type detection to find entities in containers
   - Processes entities in different container types (list, dict, tuple, set)
   - Adds appropriate edge types based on container type

3. **Edge Classification**: The edge classification implementation:
   - Preserves original edge types (DIRECT, LIST, DICT, etc.) for container relationships
   - Marks all edges as hierarchical (simplified approach for now)
   - Uses a single field on the edge to indicate hierarchical status
   - Treats all entity references as hierarchical for ancestry path calculation

4. **Circular References**: The current implementation raises a ValueError when circular references are detected, as they are not supported at this stage.

5. **Graph Visualization**: Added a Mermaid diagram generator with capabilities for:
   - Rendering entity nodes with type and optional attributes
   - Differentiating between hierarchical and reference edges
   - Displaying container relationships (list indices, dict keys)
   - Visual highlighting of the root entity
   - Custom styling for different edge types

6. **Single-Pass Graph Construction**: Implemented a more efficient algorithm that:
   - Builds the graph structure and ancestry paths in a single traversal
   - Classifies edges immediately based on ownership metadata
   - Updates ancestry paths on-the-fly when shorter paths are found
   - Propagates paths from parents to children during traversal
   - Processes each entity's fields only once
   - Maintains proper path information in the queue
   - Matches the approach described in the design document addendum

## Testing Approach
- Start with basic building blocks: EntityEdge, EntityGraph operations, field detection
- Focus on direct entity references first, then add container tests gradually
- Verify each step thoroughly before proceeding to more complex structures
- Adapt tests to match current implementation behavior, adding TODOs for future improvements

## Current Testing Status
- Basic Entity functionality tested (initialization, hash, equality)
- Entity container types (list, dict, tuple, set) tested
- EntityEdge and basic EntityGraph operations tested
- Field type detection tested with full container and type support
- Entity reference processing tested for direct references and containers
- Expanded field tests with non-entity data types
- Ownership-based edge classification tested with hierarchical and reference relationships
- Circular reference detection tested with appropriate error handling
- Mermaid diagram generation tested for various graph structures
- Graph diffing tested for multiple change scenarios:
  - Non-entity attribute changes
  - Entity additions and removals
  - Entity movement within the graph
  - Container modifications (lists, dicts)
  - Optional entity fields (setting to None)
  - Deep and complex entity hierarchies
  - Reassigning children of removed entities
- EntityRegistry thoroughly tested with coverage for:
  - Basic registration of entities and graphs
  - Retrieval operations for graphs and entities
  - Versioning with attribute changes
  - Versioning of nested entity structures
  - Complex hierarchical entity versioning
  - Multi-version lineage tracking
  - Container entity versioning
  - Type registry functionality
  - Immutability of retrieved entities and graphs
  - Entity serialization and deserialization with comprehensive coverage:
    - Basic entity serialization/deserialization
    - Nested entity structures serialization
    - Container types (lists, dictionaries, tuples, sets)
    - JSON serialization and persistence
    - Primitive value serialization
    - Complex nested container serialization
    - Optional entity fields
    - Entity versioning serialization
    - Graph structure preservation

## Next Development Steps
1. **✅ Improved Field Type Detection**: Successfully enhanced to handle container fields and empty containers
2. **✅ Container Entity Processing**: Updated to work with the improved type detection 
3. **✅ Basic Graph Construction Testing**: Added tests for simple entity hierarchies and container relationships
4. **✅ Refined Edge Classification**: Implemented ownership-based edge classification using Pydantic field metadata
5. **✅ Graph Visualization**: Added Mermaid diagram generation for entity graphs
6. **✅ Single-Pass Graph Construction**: Implemented the algorithm from the addendum for efficient graph building
7. **✅ Entity Graph Diffing Algorithm**: Implemented efficient set-based approach for detecting entity changes
8. **✅ Graph Diffing Tests**: Added comprehensive tests for detecting various entity change scenarios
9. **✅ Entity Registry Implementation**: Added registry for entity graph storage and retrieval
10. **✅ Entity Versioning System**: Implemented versioning with ecs_id management
11. **✅ Registry Test Coverage**: Added comprehensive tests for registry operations including storage, retrieval, and versioning
12. **✅ Serialization Tests**: Added tests for entity and graph serialization/deserialization with JSON support

Completed features:
13. **✅ Entity Serialization Tests**: Implemented comprehensive tests for entity and graph serialization

Current priorities:
14. **✅ Subentity Attachment/Detachment**: Completed implementation for attaching and detaching subentities
15. **✅ Entity Movement**: Implemented functionality to move subentities between parent entities
16. **✅ Attachment/Detachment Testing**: Added comprehensive tests for entity movement operations

Completed features:
17. **✅ Entity Immutability**: Implemented deep copy-based immutability for entities retrieved from the registry

Current focus:
18. **Performance Optimization**: Improve performance of graph operations and versioning for large entity structures

Future work:
19. **Registry Persistence**: Implement persistent storage for the registry to survive application restarts
20. **Circular Reference Handling**: Implement proper handling of circular references instead of raising errors
21. **Direct Entity References**: Support for direct entity references without requiring root entities

## Code Style Guidelines
- **Python Version**: 3.9+ (use type hints extensively)
- **Imports**: Sort imports with isort
- **Type Hints**: Use explicit typing annotations
- **Entity System**: Track lineage_id, live_id, and ecs_id for all entities
- **Hashing**: Entities use `_hash_str()` that combines identity fields
- **Documentation**: Docstrings for all classes and methods

## Graph Construction Algorithm
The implementation uses a simplified single-pass approach:
1. **Unified Graph Building**: 
   - Builds graph structure and ancestry paths in a single traversal
   - Marks all edges as hierarchical during initial discovery
   - Maintains ancestry paths during traversal
   - Propagates paths from parents to children

2. **Key Optimizations**:
   - Each entity's fields are processed only once
   - Ancestry paths are updated on-the-fly when shorter paths are found
   - All edges contribute to ancestry paths
   - Simple queue structure with entity and parent information

This simplifies the "Single-Pass DAG Transformation" approach described in the design document, creating a foundation that can be extended later to support reference edges and circular references.

## Graph Diffing Algorithm

The implementation uses an efficient set-based approach to identify entities that require versioning:

1. **Set-Based Structural Comparison**:
   - Compares node sets to identify added/removed entities
   - Compares edge sets to identify moved entities (same entity, different parent)
   - Marks entire ancestry paths for versioning when structural changes are detected

2. **Moved Entity Detection**:
   - Specifically identifies entities that exist in both graphs but with different parent sets
   - Ensures both old parent path and new parent path are marked for versioning
   - Provides explicit tracking of moved entities for debugging and analysis

3. **Attribute-Level Comparison**:
   - Only performs attribute comparisons for entities not already marked for versioning
   - Starts with leaf nodes (entities with longest paths to root) and works upward
   - Efficiently propagates changes up ancestor paths when differences are detected

4. **Complete Change Detection**:
   - Detects changes in non-entity attribute values
   - Identifies entity additions and removals
   - Recognizes when entities are moved within the graph
   - Detects when optional entities are set to None

The algorithm is optimized to minimize comparisons while ensuring all relevant entities are properly versioned.

## Entity Registry System

The EntityRegistry provides a complete versioning and storage system for entity graphs:

1. **Multi-dimensional Indexing**:
   - Stores graphs by root_ecs_id for direct lookup
   - Maps lineage_id to lists of root_ecs_id to track versions
   - Maps live_id to entities for quick in-memory reference lookup
   - Organizes entities by type for type-based queries

2. **Storage Operations**:
   - `register_entity`: Stores a root entity and its entire graph
   - `register_entity_graph`: Registers a pre-built entity graph
   - `version_entity`: Computes differences and updates entity versions

3. **Retrieval Operations**:
   - `get_stored_graph`: Retrieves a deep copy of a graph by root_ecs_id with new live_ids
   - `get_stored_entity`: Gets an entity from a specific graph with new live_id
   - `get_live_entity`: Retrieves an entity by its live_id
   - `get_live_root_from_entity`: Finds a root entity from any sub-entity
   - `get_stored_graph_from_entity`: Gets the graph containing a specific entity

4. **Versioning Process**:
   - Detects modified entities using graph comparison
   - Updates entity ecs_ids while preserving lineage
   - Maintains history through old_ids tracking
   - Propagates root_ecs_id updates through the entire graph

5. **Entity Movement Operations**:
   - `detach()`: Promotes an entity to a root entity after physical removal from its parent
   - `attach()`: Updates an entity's references after physical attachment to a new parent
   - `promote_to_root()`: Internal method to transform an entity into a root entity

6. **Immutability System**:
   - Creates deep copies with new live_ids when retrieving from registry
   - Maintains persistent identity (ecs_id) while changing runtime identity (live_id)
   - Allows independent modification of different copies of the same entity
   - Supports natural branching through separate modifications to retrieved copies

## Entity Movement Workflow

To move an entity between parent entities, follow these precise steps:

1. **Detaching an Entity**:
   - First, physically remove the entity from its parent's field
   - Call `entity.detach()` to update metadata and promote to root
   - The entity is now an independent root entity registered in the registry

2. **Attaching an Entity**:
   - First, physically add the entity to its new parent's field
   - Re-register the parent's updated graph (or force rebuild with build_entity_graph)
   - Call `entity.attach(new_parent)` to update metadata
   - The entity is now properly linked to its new parent with updated IDs

This two-phase approach (physical modification + metadata update) ensures proper tracking of entity relationships and maintains the versioning integrity of the system.

## Entity Immutability System

The entity system implements a powerful immutability feature that ensures entities retrieved from the registry are always deep copies with new runtime identities:

1. **Deep Copy Retrieval**:
   - When an entity or graph is retrieved from the registry using `get_stored_graph()` or `get_stored_entity()`, a deep copy is created
   - The copies maintain the same ecs_ids (persistent identity) but receive new live_ids (runtime identity)
   - All references within the graph are updated to maintain proper relationships in the copy

2. **Identity-Based Equality**:
   - Entity equality is based only on persistent identity (ecs_id and root_ecs_id)
   - This allows entities with different live_ids to be considered equal if they represent the same logical entity
   - Simplifies diffing and comparison operations across different retrievals

3. **Natural Branching Model**:
   - Different code paths can retrieve the same entity and modify it independently
   - When each copy is versioned, it creates a new branch in the version history
   - All branches trace back to the same lineage, allowing for tracking changes over time
   - Similar to Git's branching model for code versioning

4. **Benefits**:
   - Prevents unexpected side effects when multiple parts of code work with the same entity
   - Creates a natural isolation boundary that simplifies concurrent operations
   - Supports "what-if" scenarios where different modifications can be explored in parallel
   - Reduces the risk of inadvertent modification of shared state

To take advantage of immutability, always use the registry's retrieval methods rather than keeping direct references to entities across different operations.

## Graph Visualization Example

To visualize an entity graph, use the `generate_mermaid_diagram` function:

```python
from abstractions.ecs.entity import Entity, build_entity_graph, generate_mermaid_diagram

# Create an entity structure
root = Entity()
root.root_ecs_id = root.ecs_id
root.root_live_id = root.live_id

# Build the graph
graph = build_entity_graph(root)

# Generate a Mermaid diagram
mermaid_code = generate_mermaid_diagram(graph)
print(mermaid_code)

# For more details, include entity attributes
detailed_diagram = generate_mermaid_diagram(graph, include_attributes=True)
```

The diagram can be rendered in any Markdown viewer that supports Mermaid diagrams, including GitHub and many documentation tools.