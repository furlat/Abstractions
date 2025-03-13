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
- **Entity Operations**: Support for fork, attach, and detach operations
- **Edge Classification**: Simple hierarchical edge marking for all edges (reference edges will be added later)
- **Circular References**: Error detection for circular entity references
- **Visualization**: Mermaid diagram generation for entity graphs
- **Ancestry Paths**: On-the-fly construction during graph traversal

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

## Next Development Steps
1. **✅ Improved Field Type Detection**: Successfully enhanced to handle container fields and empty containers
2. **✅ Container Entity Processing**: Updated to work with the improved type detection 
3. **✅ Basic Graph Construction Testing**: Added tests for simple entity hierarchies and container relationships
4. **✅ Refined Edge Classification**: Implemented ownership-based edge classification using Pydantic field metadata
5. **✅ Graph Visualization**: Added Mermaid diagram generation for entity graphs
6. **✅ Single-Pass Graph Construction**: Implemented the algorithm from the addendum for efficient graph building

Next priorities:
7. **Circular Reference Handling**: Implement proper handling of circular references instead of raising errors
8. **Add Circular Reference Tests**: Once circular reference handling is implemented, add specific tests

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