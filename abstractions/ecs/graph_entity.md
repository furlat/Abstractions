# Hierarchical Entity System with Graph-Based Versioning

## Core Concepts

### Entity Identity

Each entity in the system maintains multiple identifiers that serve different purposes:

1. **`ecs_id` (Version Identifier)**:
   - Unique identifier that changes when the entity is modified
   - Used to track different versions of the same logical entity
   - Referenced by other entities via `parent_id` to establish version lineage

2. **`live_id` (Object Identity)**:
   - Identifies a specific in-memory Python object instance
   - Changes whenever a new Python object is created (including when retrieved from storage)
   - Used to track and navigate between runtime objects

3. **`root_ecs_id` (Graph Context)**:
   - The `ecs_id` of the root entity of this entity's graph
   - Provides context for which version of the graph this entity belongs to
   - Essential for precise entity identification across different graph versions

4. **`root_live_id` (Runtime Context)**:
   - The `live_id` of the root entity of this entity's graph
   - Allows navigation from any entity to its current root Python object
   - Enables efficient traversal of in-memory entity structures

5. **`lineage_id` (Entity Lineage)**:
   - Shared identifier across all versions of the same logical entity
   - Persists even as the entity is modified and its `ecs_id` changes
   - Changes only when an entity is detached or changes ownership

### Graph-Based Versioning

Instead of versioning individual entities, the system versions entire graphs:

1. **Graphs as Versioning Units**:
   - A graph represents a complete, self-contained entity hierarchy
   - Each graph has a root entity that defines the graph's identity
   - Graphs are stored and retrieved as atomic units

2. **Change Propagation**:
   - Changes to any entity in a graph propagate upward to its root
   - When a sub-entity changes, its parent also gets a new version
   - This ensures all paths to modified entities are properly versioned

3. **Graph Storage**:
   - Graphs are stored indexed by the root entity's `ecs_id`
   - Each stored graph contains the complete entity tree
   - Cold storage maintains the exact structure of entity relationships

## Key Operations

### Entity Creation and Registration

When a new entity is created:

1. It receives a new `ecs_id` and `live_id`
2. If it's a root entity, a new graph is initialized
3. All related entities are discovered and added to the graph
4. Each entity's `root_ecs_id` and `root_live_id` are set to the root entity
5. The complete graph is registered in storage

### Entity Modification and Forking

When entities in a graph are modified:

1. The modified entity's graph is reconstructed from its current state
2. The graph is compared to the stored version to detect changes
3. For each modified entity:
   - A new `ecs_id` is generated
   - The old `ecs_id` is stored in `parent_id` and `old_ids` list
   - All parent entities also receive new `ecs_id` values
4. Once the root entity has its new `ecs_id`, all entities in the graph have their `root_ecs_id` updated
5. The new graph is stored with the new root `ecs_id`

### Detaching Entities

When an entity is detached from its graph:

1. The Python code breaks the reference to the entity
2. The detached entity becomes a root with its own graph
3. It receives a new `ecs_id` and a new `lineage_id`
4. Its `root_ecs_id` is updated to its own `ecs_id`
5. Its `root_live_id` is updated to its own `live_id`
6. Both the modified original graph and the new graph are registered

### Attaching Entities

When an entity is attached to a new parent:

1. The Python code creates the reference from the parent to the entity
2. The entity's `root_ecs_id` is updated to the parent's root `ecs_id` 
3. The entity's `root_live_id` is updated to the parent's root `live_id`
4. The entity's `lineage_id` may be updated to reflect the new ownership
5. The parent's graph is rebuilt and registered with the attached entity

### Cold Storage Retrieval

When an entity is retrieved from cold storage:

1. The complete graph is retrieved based on the root `ecs_id`
2. All entities get new `live_id` values while keeping their `ecs_id` values
3. All entities have their `root_live_id` updated to the new root's `live_id`
4. The entity relationships are preserved exactly as stored
5. Entities are marked as `from_storage = True`

## Entity Registry

The EntityRegistry provides several core services:

1. **Storage Management**:
   - Maps root `ecs_id` values to complete entity graphs
   - Tracks lineage history for version traversal
   - Handles versioning and forking

2. **Warm Entity Tracking**:
   - Maps `live_id` values to entity objects
   - Enables navigation between in-memory Python objects
   - Maintains the connection between warm and cold entities

3. **Operations and Validation**:
   - Provides methods for comparing entities and graphs
   - Validates graph consistency and entity relationships
   - Supports batched operations for efficiency

## Implementation Benefits

This graph-based versioning approach offers several advantages:

1. **Consistent Versioning**: Related entities are always versioned together
2. **Precise Identity**: Entities can be identified across different contexts
3. **Efficient Navigation**: Direct access to related entities in both warm and cold states
4. **Structural Integrity**: Graph consistency is maintained during modifications
5. **Flexible Reuse**: Entities can be detached and reattached while maintaining proper versioning

## Design Considerations

1. **Triple Identity System**:
   The combination of `ecs_id`, `root_ecs_id`, and `root_live_id` provides complete entity context, enabling precise navigation between versioned storage and runtime objects.

2. **Entity Reuse**:
   The same `ecs_id` can exist in different graphs, allowing efficient reuse of unchanged sub-entities across different structures.

3. **Batch Operations**:
   For efficiency, operations like detachment and attachment can be batched, rebuilding graphs only once after multiple changes.

4. **Graph Reconstruction**:
   Graphs are rebuilt from scratch when needed rather than being maintained continuously, simplifying the implementation and avoiding stale references.

5. **Self-Contained Identity**:
   By storing `root_ecs_id` directly on entities, their identity is self-contained and doesn't rely solely on external registry mappings.

## Conclusion

This hierarchical entity system with graph-based versioning provides a powerful foundation for managing complex entity relationships with proper versioning. By treating graphs as the primary versioning unit and maintaining multiple levels of identity, the system can efficiently track and manipulate entity relationships while preserving version history.

# Efficient Graph Construction and Diffing for Hierarchical Pydantic Entities

## Overview

Building on our hierarchical entity system with graph-based versioning, this document focuses on optimizing two critical operations:

1. **Graph Construction**: How to efficiently build graphs from hierarchical Pydantic entities
2. **Graph Diffing**: How to quickly identify changes between graphs for targeted versioning

These optimizations are essential for systems with deep hierarchies, complex relationships, and frequent modifications.

## Efficient Graph Construction

### Challenges

When building graphs from hierarchical Pydantic entities, we need to handle:
- Direct entity attributes
- Entities contained in lists/tuples
- Entities contained in dictionaries
- Circular references
- Maintaining proper ancestry information

### Optimized Construction Algorithm

```python
def build_entity_graph(root_entity: Entity) -> EntityGraph:
    """Build a graph from a root entity with optimized ancestry tracking."""
    graph = EntityGraph(root_id=root_entity.ecs_id, lineage_id=root_entity.lineage_id)
    
    # Maps entity live_id to its path to root (list of entities from leaf to root)
    ancestry_paths = {}
    
    # Entities pending processing
    to_process = deque([root_entity])
    # Entities that have been seen (to handle cycles)
    processed_live_ids = set()
    
    while to_process:
        entity = to_process.popleft()
        
        # Skip if already processed
        if entity.live_id in processed_live_ids:
            continue
            
        processed_live_ids.add(entity.live_id)
        
        # Add entity to graph
        graph.add_entity(entity)
        
        # Initialize its ancestry path (just itself for now)
        ancestry_paths[entity.live_id] = [entity]
        
        # Process all fields to find entity references
        for field_name, field_info in entity.model_fields.items():
            value = getattr(entity, field_name)
            if value is None:
                continue
                
            # Direct entity reference
            if isinstance(value, Entity):
                process_entity_reference(
                    graph, entity, value, field_name, None, None,
                    ancestry_paths, to_process
                )
            
            # List/tuple of entities
            elif isinstance(value, (list, tuple)):
                for i, item in enumerate(value):
                    if isinstance(item, Entity):
                        process_entity_reference(
                            graph, entity, item, field_name, i, None,
                            ancestry_paths, to_process
                        )
            
            # Dict of entities
            elif isinstance(value, dict):
                for k, v in value.items():
                    if isinstance(v, Entity):
                        process_entity_reference(
                            graph, entity, v, field_name, None, k,
                            ancestry_paths, to_process
                        )
    
    return graph, ancestry_paths

def process_entity_reference(
    graph: EntityGraph,
    source: Entity,
    target: Entity,
    field_name: str,
    list_index: Optional[int],
    dict_key: Optional[Any],
    ancestry_paths: Dict[UUID, List[Entity]],
    to_process: deque
):
    """Process a single entity reference, updating the graph and ancestry paths."""
    # Add the appropriate edge type
    if list_index is not None:
        graph.add_list_edge(source, target, field_name, list_index)
    elif dict_key is not None:
        graph.add_dict_edge(source, target, field_name, dict_key)
    else:
        graph.add_direct_edge(source, target, field_name)
    
    # Update ancestry path for this entity
    # Its path is its parent's path with itself prepended
    if target.live_id not in ancestry_paths:
        parent_path = ancestry_paths[source.live_id]
        ancestry_paths[target.live_id] = [target] + parent_path
    
    # Add to processing queue
    to_process.append(target)
```

### Optimizations in Graph Construction

1. **Single-pass Construction**:
   - Builds the graph and ancestry paths in a single traversal
   - Uses a queue to process entities breadth-first

2. **Efficient Cycle Handling**:
   - Detects cycles using a set of processed live IDs
   - Avoids infinite recursion without complex cycle detection

3. **Integrated Path Building**:
   - Constructs ancestry paths during graph traversal
   - Each entity's path is derived from its parent's path

4. **Typed Edge Creation**:
   - Creates the appropriate edge type based on the container
   - Preserves relationship context for accurate diffing

## Fast Graph Diffing

### Path-Based Diffing Algorithm

The core insight is that when an entity changes, all entities in its path to the root must receive new versions. We can use the ancestry paths to optimize this process.

```python
def diff_graphs(
    new_graph: EntityGraph,
    old_graph: EntityGraph,
    ancestry_paths: Dict[UUID, List[Entity]]
) -> Set[UUID]:
    """
    Efficiently identify changed entities using ancestry paths.
    Returns set of entity ecs_ids that need new versions.
    """
    changed_entities = set()
    unchanged_entities = set()
    
    # Step 1: Identify structural changes (added/removed entities)
    new_entity_ids = {e.ecs_id for e in new_graph.nodes.values()}
    old_entity_ids = {e.ecs_id for e in old_graph.nodes.values()}
    
    added_entities = new_entity_ids - old_entity_ids
    removed_entities = old_entity_ids - new_entity_ids
    
    # Mark all paths containing added/removed entities as changed
    for entity in new_graph.nodes.values():
        if entity.ecs_id in added_entities:
            # Mark this entity and all ancestors as changed
            path = ancestry_paths[entity.live_id]
            changed_entities.update(e.ecs_id for e in path)
    
    # Step 2: Create a priority queue of remaining entities sorted by path length
    # (Entities with longest paths to root are processed first - these are the leaves)
    remaining_entities = []
    for entity in new_graph.nodes.values():
        if entity.ecs_id not in changed_entities and entity.ecs_id not in added_entities:
            # Get path length as priority (longer paths = higher priority)
            path_length = len(ancestry_paths[entity.live_id])
            remaining_entities.append((path_length, entity))
    
    # Sort by path length (descending)
    remaining_entities.sort(reverse=True)
    
    # Step 3: Process entities in order of path length
    for _, entity in remaining_entities:
        # Skip if already processed
        if entity.ecs_id in changed_entities or entity.ecs_id in unchanged_entities:
            continue
        
        # Get the corresponding entity from old graph
        old_entity = old_graph.get_entity_by_id(entity.ecs_id)
        
        # Compare the entities
        has_changes = compare_entity_fields(entity, old_entity)
        
        if has_changes:
            # Mark the entire path as changed
            path = ancestry_paths[entity.live_id]
            changed_entities.update(e.ecs_id for e in path)
        else:
            # Mark just this entity as unchanged
            unchanged_entities.add(entity.ecs_id)
    
    return changed_entities
```

### Optimizations in Graph Diffing

1. **Structural Change Fast Path**:
   - Quickly identifies added/removed entities
   - Marks entire paths as changed without detailed comparison

2. **Path-Length Prioritization**:
   - Processes leaf nodes first (those with longest paths to root)
   - Enables efficient bottom-up processing

3. **Path-Based Change Propagation**:
   - When a change is detected, marks the entire path to root
   - Avoids redundant comparisons of ancestors

4. **Pruning Already-Processed Paths**:
   - Once a node is marked changed/unchanged, skips it in future processing
   - Drastically reduces the comparison space

5. **Set-Based Operations**:
   - Uses set operations for efficient structural change detection
   - Enables quick path marking without repeated traversals

## Performance Considerations

### Time Complexity Analysis

- **Graph Construction**: O(n) where n is the number of entities
  - Each entity is processed exactly once
  - Ancestry path construction is constant time per entity

- **Graph Diffing**: O(n log n) in worst case
  - Sorting by path length takes O(n log n)
  - Entity comparison is amortized O(1) for most entities
  - Structural change detection is O(n)

### Space Complexity

- **Graph Structure**: O(n + e) where n is entity count and e is edge count
- **Ancestry Paths**: O(n²) in worst case (deep hierarchies)
  - Each entity stores its path to root
  - Average case is much better in bushy hierarchies

### Memory Optimization Strategies

For very large graphs, we can optimize memory usage:

1. **Compressed Paths**:
   - Store paths as entity IDs instead of entity references
   - Trade computation time for space

2. **Lazy Path Construction**:
   - Compute ancestry paths on-demand during diffing
   - Sacrifice some speed for reduced memory usage

3. **Path Truncation**:
   - For very deep hierarchies, truncate paths after a certain depth
   - Fall back to standard traversal when needed

## Usage Example

```python
# Build a graph with ancestry paths
graph, ancestry_paths = build_entity_graph(root_entity)

# Store the graph
EntityRegistry.register_graph(graph)

# Later, when checking for changes:
# 1. Build a new graph from the current state
new_graph, new_ancestry_paths = build_entity_graph(root_entity)

# 2. Get the stored graph
old_graph = EntityRegistry.get_graph(root_entity.root_ecs_id)

# 3. Diff the graphs
changed_entities = diff_graphs(new_graph, old_graph, new_ancestry_paths)

# 4. Update ecs_ids for changed entities
update_entity_versions(new_graph, changed_entities)

# 5. Register the updated graph
EntityRegistry.register_graph(new_graph)
```

## Conclusion

By optimizing both graph construction and diffing, we can efficiently manage hierarchical entity relationships and versioning at scale. The path-based approach provides a significant performance improvement over naive comparison methods, especially for complex entity hierarchies with localized changes.

The combination of ancestry path tracking during construction and path-based prioritization during diffing creates a powerful system that can quickly identify and version changes while avoiding unnecessary work.


You're right - we can optimize this further by constructing the DAG in a single pass. Let me rewrite the document section focusing on this insight:

# Addendum: Single-Pass DAG Transformation During Entity Graph Construction

## Key Insight: On-the-Fly Path Analysis

The most efficient approach to transforming cyclic entity graphs into DAGs is to perform the canonical path analysis during the initial graph traversal. By maintaining a distance-to-root metric for each entity and making edge classification decisions immediately upon discovery, we eliminate the need for subsequent analysis passes.

## Optimized Single-Pass Algorithm

```python
def build_canonical_dag(root_entity: Entity) -> EntityGraph:
    """
    Build entity graph with automatic DAG transformation in a single pass.
    
    This algorithm:
    1. Traverses the entity graph once
    2. Classifies edges immediately upon discovery
    3. Maintains minimal path information
    """
    graph = EntityGraph(root_id=root_entity.ecs_id)
    
    # Track shortest known distance to root for each entity
    # Map: entity_id -> distance
    shortest_distance = {root_entity.live_id: 0}
    
    # Track canonical parent for each entity
    # Map: entity_id -> (parent_entity, field_info)
    canonical_parent = {}
    
    # Process queue with distance information
    # (entity, distance, source_entity, field_info)
    to_process = deque([(root_entity, 0, None, None)])
    
    while to_process:
        entity, distance, source, field_info = to_process.popleft()
        
        # Always add the entity to the graph (if not already added)
        if entity.live_id not in graph.nodes:
            graph.add_entity(entity)
        
        # Check if we've seen this entity before and compare distances
        if entity.live_id in shortest_distance:
            current_best = shortest_distance[entity.live_id]
            
            if distance < current_best:
                # We found a shorter path - update shortest distance
                shortest_distance[entity.live_id] = distance
                
                # Update canonical parent
                old_parent_info = canonical_parent.get(entity.live_id)
                if old_parent_info:
                    old_parent, old_field_info = old_parent_info
                    # Mark old edge as reference
                    graph.mark_edge_as_reference(old_parent.live_id, entity.live_id, old_field_info)
                
                # Store new canonical parent
                if source:
                    canonical_parent[entity.live_id] = (source, field_info)
                    # Add hierarchical edge
                    add_edge_to_graph(graph, source, entity, field_info, EdgeType.HIERARCHICAL)
                
                # Continue exploration from this entity
                explore_entity_fields(entity, distance, graph, to_process, shortest_distance)
                
            else:
                # Current path is not shorter - mark as reference edge
                if source:
                    # Add reference edge
                    add_edge_to_graph(graph, source, entity, field_info, EdgeType.REFERENCE)
                # Don't explore further from this path
                
        else:
            # First time seeing this entity
            shortest_distance[entity.live_id] = distance
            
            # Store canonical parent
            if source:
                canonical_parent[entity.live_id] = (source, field_info)
                # Add hierarchical edge
                add_edge_to_graph(graph, source, entity, field_info, EdgeType.HIERARCHICAL)
            
            # Explore all fields
            explore_entity_fields(entity, distance, graph, to_process, shortest_distance)
    
    return graph

def explore_entity_fields(entity, current_distance, graph, to_process, shortest_distance):
    """Explore all entity fields and add children to processing queue."""
    next_distance = current_distance + 1
    
    for field_name, field_value in get_entity_fields(entity):
        # Handle direct entity reference
        if isinstance(field_value, Entity):
            to_process.append((field_value, next_distance, entity, (field_name, None, None)))
        
        # Handle list/tuple of entities
        elif isinstance(field_value, (list, tuple)):
            for i, item in enumerate(field_value):
                if isinstance(item, Entity):
                    to_process.append((item, next_distance, entity, (field_name, i, None)))
        
        # Handle dict of entities
        elif isinstance(field_value, dict):
            for k, v in field_value.items():
                if isinstance(v, Entity):
                    to_process.append((v, next_distance, entity, (field_name, None, k)))
```

## Operational Principles

The algorithm operates on a few key principles:

1. **Immediate Edge Classification**: Every edge is classified as hierarchical or reference as soon as it's discovered, eliminating the need for post-processing.

2. **Distance-Based Path Selection**: We maintain a simple integer distance metric for each entity rather than storing complete paths.

3. **Dynamic Path Updating**: When a shorter path is discovered:
   - The previous edge is reclassified as a reference edge
   - The new edge becomes the hierarchical edge
   - Further exploration continues from this shorter path

4. **Exploration Pruning**: When discovering an entity through a longer path, the edge is marked as a reference and exploration from that entity is skipped to avoid redundant processing.

## Set Operations for Path Management

Instead of storing complete ancestry paths, we utilize efficient set operations:

1. **Distance Tracking**: `shortest_distance` mapping uses constant-time lookups to determine if a shorter path exists.

2. **Path Reclassification**: When a shorter path is found, we simply update the canonical parent and reclassify the previous edge without reconstructing complete paths.

3. **Exploration Control**: The algorithm naturally stops exploring branches that would create longer paths to already-discovered entities.

## Performance Characteristics

This approach achieves optimal performance for DAG transformation:

- **Time Complexity**: O(n + e) where n is the number of entities and e is the number of edges
  - Each entity is processed exactly once for its shortest path
  - Each edge is classified exactly once

- **Space Complexity**: O(n) for tracking distance and canonical parent information
  - No need to store complete paths
  - Only minimal metadata per entity

## Versioning with the Transformed DAG

Once the DAG is constructed, versioning operations become straightforward:

```python
def propagate_changes_in_dag(graph, changed_entity_ids):
    """Propagate changes up through hierarchical edges only."""
    entities_to_version = set(changed_entity_ids)
    processed = set()
    
    # Process each changed entity
    for entity_id in changed_entity_ids:
        if entity_id in processed:
            continue
            
        current = graph.get_entity(entity_id)
        processed.add(entity_id)
        
        # Follow hierarchical edges up to the root
        while current:
            entities_to_version.add(current.ecs_id)
            
            # Find the parent through a hierarchical edge
            parent = None
            for edge in graph.get_outgoing_edges(current.ecs_id):
                if edge.type == EdgeType.HIERARCHICAL:
                    parent = graph.get_entity(edge.target_id)
                    break
                    
            # Stop if no hierarchical parent or we've processed this path
            if not parent or parent.ecs_id in processed:
                break
                
            current = parent
            processed.add(current.ecs_id)
    
    return entities_to_version
```

## Conclusion

The single-pass DAG transformation algorithm efficiently converts potentially cyclic entity graphs into directed acyclic graphs for versioning purposes. By making classification decisions immediately upon entity discovery and using simple set operations to track path information, we achieve optimal performance while maintaining the full semantics of the entity relationships.

This approach elegantly handles complex entity structures with circular references, providing clear, deterministic versioning behavior without unnecessary propagation through reference edges.