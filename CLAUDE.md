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
- **Graph Construction**: Complete implementation of the build_entity_graph function
- **Entity Operations**: Support for fork, attach, and detach operations
- **Edge Classification**: Ownership-based hierarchical vs. reference edge marking using Pydantic field metadata
- **Circular References**: Error detection for circular entity references

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

3. **Edge Classification**: The edge classification implementation has been enhanced to:
   - Use Pydantic field metadata with an `ownership` parameter to determine hierarchical relationships
   - Preserve original edge types (DIRECT, LIST, DICT, etc.) while adding hierarchical status
   - Separate edge type (container relationship) from hierarchical status (ownership relationship)
   - Calculate ancestry paths using only hierarchical edges
   - Mark all edges created from fields with `ownership=True` as hierarchical
   - Mark all edges created from fields with `ownership=False` as reference edges

4. **Circular References**: The current implementation raises a ValueError when circular references are detected, as they are not supported at this stage.

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

## Next Development Steps
1. **✅ Improved Field Type Detection**: Successfully enhanced to handle container fields and empty containers
2. **✅ Container Entity Processing**: Updated to work with the improved type detection 
3. **✅ Basic Graph Construction Testing**: Added tests for simple entity hierarchies and container relationships
4. **✅ Refined Edge Classification**: Implemented ownership-based edge classification using Pydantic field metadata

Next priorities:
5. **Implement DAG Transformation**: Use the algorithm from the addendum to transform graphs with cycles
6. **Add Circular Reference Tests**: Once DAG transformation is implemented, add specific tests for circular references

## Code Style Guidelines
- **Python Version**: 3.9+ (use type hints extensively)
- **Imports**: Sort imports with isort
- **Type Hints**: Use explicit typing annotations
- **Entity System**: Track lineage_id, live_id, and ecs_id for all entities
- **Hashing**: Entities use `_hash_str()` that combines identity fields
- **Documentation**: Docstrings for all classes and methods

## Graph Construction Algorithm Notes
The current implementation uses a two-phase approach:
1. **Phase 1**: Build nodes and edges with distance tracking
   - Traverses entity structure breadth-first
   - Adds entities to graph and processes their fields
   - Maintains a distance map to track shortest paths

2. **Phase 2**: Construct ancestry paths and classify edges
   - Uses distance information to find shortest paths to root
   - Marks shortest path edges as hierarchical
   - Marks other edges as reference edges
   - Creates ancestry paths for each entity

Future work will need to focus on the addendum's "Single-Pass DAG Transformation" to better handle circular references.