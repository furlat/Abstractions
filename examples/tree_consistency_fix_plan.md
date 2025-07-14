# Tree Consistency Fix Plan

## Problem Statement

After ECS ID updates during versioning, the EntityTree structure becomes desynchronized:
- `tree.nodes` maps `old_ecs_id -> entity_with_new_ecs_id`
- `tree.edges` maps `(old_source_id, old_target_id) -> edge`
- `tree.ancestry_paths` maps `old_ecs_id -> [old_root_id, old_parent_id, old_ecs_id]`
- All other tree mappings use stale ECS IDs

This causes registry consistency failures and breaks the versioning system.

## Proposed Solution: `update_tree_mappings_after_versioning()`

Add a principled method to update all tree mappings to be consistent with entities' current ECS IDs.

### Method Signature
```python
def update_tree_mappings_after_versioning(
    self, 
    id_mapping: Dict[UUID, UUID]
) -> None:
    """
    Update all tree mappings to use new ECS IDs after versioning.
    
    Args:
        id_mapping: Maps old_ecs_id -> new_ecs_id for all updated entities
    """
```

### Implementation Plan

#### Step 1: Update `nodes` Mapping
```python
# Rebuild nodes dictionary with new ECS IDs as keys
updated_nodes = {}
for old_ecs_id, entity in self.nodes.items():
    new_ecs_id = id_mapping.get(old_ecs_id, old_ecs_id)  # Use new ID if mapped, else keep old
    updated_nodes[new_ecs_id] = entity
self.nodes = updated_nodes
```

**Conflict Check**: ✅ No conflicts - we're creating a fresh dictionary
**Efficiency Check**: ✅ O(n) iteration over existing data, no recomputation

#### Step 2: Update `edges` Mapping
```python
# Rebuild edges dictionary with new ECS IDs in keys and edge objects
updated_edges = {}
for (old_source_id, old_target_id), edge in self.edges.items():
    new_source_id = id_mapping.get(old_source_id, old_source_id)
    new_target_id = id_mapping.get(old_target_id, old_target_id)
    
    # Update edge object's IDs
    edge.source_id = new_source_id
    edge.target_id = new_target_id
    
    updated_edges[(new_source_id, new_target_id)] = edge
self.edges = updated_edges
```

**Conflict Check**: ✅ No conflicts - fresh dictionary with updated edge objects
**Efficiency Check**: ✅ O(e) iteration over existing edges, no recomputation

#### Step 3: Update `outgoing_edges` Mapping
```python
# Rebuild outgoing edges with new ECS IDs
updated_outgoing = defaultdict(list)
for old_source_id, target_list in self.outgoing_edges.items():
    new_source_id = id_mapping.get(old_source_id, old_source_id)
    new_target_list = [id_mapping.get(tid, tid) for tid in target_list]
    updated_outgoing[new_source_id] = new_target_list
self.outgoing_edges = updated_outgoing
```

**Conflict Check**: ✅ No conflicts - fresh defaultdict
**Efficiency Check**: ✅ O(e) iteration over existing data, no recomputation

#### Step 4: Update `incoming_edges` Mapping
```python
# Rebuild incoming edges with new ECS IDs
updated_incoming = defaultdict(list)
for old_target_id, source_list in self.incoming_edges.items():
    new_target_id = id_mapping.get(old_target_id, old_target_id)
    new_source_list = [id_mapping.get(sid, sid) for sid in source_list]
    updated_incoming[new_target_id] = new_source_list
self.incoming_edges = updated_incoming
```

**Conflict Check**: ✅ No conflicts - fresh defaultdict
**Efficiency Check**: ✅ O(e) iteration over existing data, no recomputation

#### Step 5: Update `ancestry_paths` Mapping
```python
# Rebuild ancestry paths with new ECS IDs
updated_ancestry_paths = {}
for old_entity_id, path in self.ancestry_paths.items():
    new_entity_id = id_mapping.get(old_entity_id, old_entity_id)
    new_path = [id_mapping.get(pid, pid) for pid in path]
    updated_ancestry_paths[new_entity_id] = new_path
self.ancestry_paths = updated_ancestry_paths
```

**Conflict Check**: ✅ No conflicts - fresh dictionary
**Efficiency Check**: ✅ O(n*d) where d=average path depth, no recomputation

#### Step 6: Update `live_id_to_ecs_id` Mapping
```python
# Update live_id mappings to point to new ECS IDs
for live_id, old_ecs_id in self.live_id_to_ecs_id.items():
    if old_ecs_id in id_mapping:
        self.live_id_to_ecs_id[live_id] = id_mapping[old_ecs_id]
```

**Conflict Check**: ✅ No conflicts - updating existing dictionary in-place
**Efficiency Check**: ✅ O(n) iteration, no recomputation

#### Step 7: Update Tree Root Reference
```python
# Update tree's root_ecs_id if the root was versioned
if self.root_ecs_id in id_mapping:
    self.root_ecs_id = id_mapping[self.root_ecs_id]
```

**Conflict Check**: ✅ No conflicts - simple field update
**Efficiency Check**: ✅ O(1) lookup and update

### Integration with `version_entity()`

#### Current Code (lines 1232-1246):
```python
for modified_entity_id in typed_entities:
    modified_entity = new_tree.get_entity(modified_entity_id)
    if modified_entity is not None:
        modified_entity.update_ecs_ids(new_root_ecs_id, root_entity_live_id)

# Update the tree's root_ecs_id and lineage_id to match the updated root entity
new_tree.root_ecs_id = new_root_ecs_id
new_tree.lineage_id = root_entity.lineage_id

cls.register_entity_tree(new_tree)
```

#### Updated Code:
```python
# Build ID mapping for all entities that got new ECS IDs
id_mapping = {}

# Add root entity mapping
id_mapping[current_root_ecs_id] = new_root_ecs_id

# Update all modified entities and build mapping
for modified_entity_id in typed_entities:
    modified_entity = new_tree.get_entity(modified_entity_id)
    if modified_entity is not None:
        old_ecs_id = modified_entity.ecs_id
        modified_entity.update_ecs_ids(new_root_ecs_id, root_entity_live_id)
        new_ecs_id = modified_entity.ecs_id
        id_mapping[old_ecs_id] = new_ecs_id

# Update tree mappings to be consistent with new ECS IDs
new_tree.update_tree_mappings_after_versioning(id_mapping)

# Update the tree's lineage_id to match the updated root entity
new_tree.lineage_id = root_entity.lineage_id

cls.register_entity_tree(new_tree)
```

### Validation Strategy

After calling `update_tree_mappings_after_versioning()`, validate consistency:

1. **Nodes Consistency**: Every `entity.ecs_id` should be a key in `tree.nodes`
2. **Edges Consistency**: Every edge's `source_id` and `target_id` should exist in `tree.nodes`
3. **Ancestry Paths Consistency**: Every entity ID in paths should exist in `tree.nodes`
4. **Root Consistency**: `tree.root_ecs_id` should exist in `tree.nodes`

### Performance Analysis

- **Time Complexity**: O(n + e + n*d) where n=nodes, e=edges, d=average path depth
- **Space Complexity**: O(n + e) for new dictionaries (old ones are replaced)
- **No Redundant Computation**: All updates use existing data, no graph traversal needed
- **Single Pass**: Each data structure updated exactly once

### Benefits

1. **Fixes Container Entity Bug**: Registry consistency will pass
2. **Fixes Ancestry Path Bug**: All tree mappings use current ECS IDs
3. **Prevents Future Issues**: Any tree operation will use consistent IDs
4. **Efficient**: No unnecessary recomputation or graph rebuilding
5. **Principled**: Single method handles all tree consistency issues

### Alternative Rejected: Full Tree Rebuild

```python
# REJECTED: new_tree = build_entity_tree(root_entity)
```

**Why Rejected**:
- ❌ O(n*d) graph traversal (much slower)
- ❌ Recomputes already-known relationships
- ❌ May change edge ordering or other metadata
- ❌ More complex debugging if issues arise

**Our Approach is Better**:
- ✅ Preserves all existing tree structure and metadata
- ✅ Only updates what changed (ECS IDs)
- ✅ Faster and more predictable
- ✅ Easier to debug and validate

## Implementation Notes

1. **Add to EntityTree class**: The method should be a member of EntityTree
2. **Call after ECS ID updates**: Integrate into `version_entity()` workflow
3. **Test thoroughly**: Ensure all tree operations work after update
4. **Document clearly**: This fixes a critical versioning system bug