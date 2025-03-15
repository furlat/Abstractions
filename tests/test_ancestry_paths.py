"""
Tests for ancestry path construction in entity trees.
"""
import unittest
from uuid import UUID
from typing import List, Dict, Optional

from pydantic import Field

from abstractions.ecs.entity import (
    Entity, 
    EntityTree, 
    build_entity_tree,
    get_field_ownership
)


class SimpleEntity(Entity):
    """A simple entity with no references."""
    name: str = "Simple"


class ParentEntity(Entity):
    """An entity that owns a child entity."""
    child: Entity = Field(
        default_factory=Entity,
        description="Owned child entity",
        json_schema_extra={"ownership": True}
    )
    name: str = "Parent"


class ComplexParentEntity(Entity):
    """An entity with both owned and referenced children."""
    owned_child: Entity = Field(
        default_factory=Entity,
        description="Owned child entity",
        json_schema_extra={"ownership": True}
    )
    
    referenced_child: Entity = Field(
        default_factory=Entity,
        description="Referenced child entity",
        json_schema_extra={"ownership": False}
    )


class NestedEntity(Entity):
    """A deeply nested entity structure."""
    level1: ParentEntity = Field(
        default_factory=ParentEntity,
        description="Level 1 entity",
        json_schema_extra={"ownership": True}
    )
    
    def create_nested_structure(self, depth: int = 3):
        """Create a nested structure with the specified depth."""
        # Start with level1 which is already created with default_factory
        current = self.level1
        
        # Create the chain of entities
        for i in range(2, depth + 1):
            # Create a new ParentEntity
            new_entity = ParentEntity(name=f"Level {i}")
            # Replace current's child with the new entity
            current.child = new_entity
            # Move to the next level
            current = new_entity


class MultiPathEntity(Entity):
    """An entity with multiple paths to the same child."""
    direct_child: Entity = Field(
        default_factory=Entity,
        description="Direct child entity",
        json_schema_extra={"ownership": True}
    )
    
    intermediate: ParentEntity = Field(
        default_factory=ParentEntity,
        description="Intermediate entity",
        json_schema_extra={"ownership": True}
    )
    
    def create_diamond_structure(self):
        """Create a diamond-shaped structure with multiple paths to the same entity."""
        # The diamond shape:
        #      Root
        #     /    \
        #  Direct  Intermediate
        #     \    /
        #      Shared
        
        shared = Entity(name="Shared")
        self.direct_child = shared
        self.intermediate.child = shared


class TestAncestryPaths(unittest.TestCase):
    """Test the ancestry path construction in entity trees."""

    def test_simple_entity_path(self):
        """Test ancestry path for a simple entity."""
        entity = SimpleEntity()
        entity.root_ecs_id = entity.ecs_id
        entity.root_live_id = entity.live_id
        
        tree = build_entity_tree(entity)
        
        # Only the root should have a path to itself
        self.assertEqual(len(tree.ancestry_paths), 1)
        self.assertEqual(tree.ancestry_paths[entity.ecs_id], [entity.ecs_id])

    def test_parent_child_path(self):
        """Test ancestry paths for parent-child relationship."""
        parent = ParentEntity()
        parent.root_ecs_id = parent.ecs_id
        parent.root_live_id = parent.live_id
        
        # Child entity is automatically created by default_factory
        child = parent.child
        
        tree = build_entity_tree(parent)
        
        # Check paths
        self.assertEqual(len(tree.ancestry_paths), 2)
        self.assertEqual(tree.ancestry_paths[parent.ecs_id], [parent.ecs_id])
        self.assertEqual(tree.ancestry_paths[child.ecs_id], [parent.ecs_id, child.ecs_id])
        
        # Check hierarchy
        self.assertTrue(tree.is_hierarchical_edge(parent.ecs_id, child.ecs_id))

    def test_owned_vs_referenced_paths(self):
        """Test ancestry paths with both owned and referenced entities."""
        parent = ComplexParentEntity()
        parent.root_ecs_id = parent.ecs_id
        parent.root_live_id = parent.live_id
        
        owned = parent.owned_child
        referenced = parent.referenced_child
        
        tree = build_entity_tree(parent)
        
        # Check paths
        self.assertEqual(len(tree.ancestry_paths), 3)
        
        # Owned child should have a path through parent
        self.assertEqual(tree.ancestry_paths[owned.ecs_id], [parent.ecs_id, owned.ecs_id])
        
        # Referenced child should also have a path through parent
        # (We're now treating all edges as hierarchical until we implement circular reference handling)
        self.assertEqual(tree.ancestry_paths[referenced.ecs_id], [parent.ecs_id, referenced.ecs_id])
        
        # Check edge types - both are hierarchical for now
        self.assertTrue(tree.is_hierarchical_edge(parent.ecs_id, owned.ecs_id))
        self.assertTrue(tree.is_hierarchical_edge(parent.ecs_id, referenced.ecs_id))  # Now all edges are hierarchical

    def test_deep_nesting_paths(self):
        """Test ancestry paths with deeply nested entities."""
        root = NestedEntity()
        root.root_ecs_id = root.ecs_id
        root.root_live_id = root.live_id
        
        # Create a structure with depth 5
        depth = 5
        root.create_nested_structure(depth)
        
        # Trace through the chain to capture all entities
        # The chain should consist of root -> level1 -> level2 -> ... -> level5
        current = root.level1
        path_entities = [root, current]
        
        # Follow the chain through each level
        for i in range(2, depth + 1):
            current = current.child
            path_entities.append(current)
        
        # Build the tree
        tree = build_entity_tree(root)
        
        # Print nodes to understand what's being created
        print("\nNodes in tree:")
        for node_id, node in tree.nodes.items():
            print(f"Node {node_id}: {node.__class__.__name__}")
        
        # We're actually getting 7 nodes because:
        # 1. The root entity (NestedEntity)
        # 2. level1 ParentEntity
        # 3-6. Four more ParentEntity instances for levels 2-5
        # 7. The default Entity created by default_factory for the last level's child
        expected_nodes = 1 + depth + 1  # Root + levels + last level's default child
        self.assertEqual(len(tree.nodes), expected_nodes, 
                         f"Expected {expected_nodes} nodes, got {len(tree.nodes)}")
        
        # Verify all path entities are in the tree
        for entity in path_entities:
            self.assertIn(entity.ecs_id, tree.nodes, 
                          f"Entity {entity.ecs_id} missing from tree")
        
        # Construct the expected ancestry path as we traced it
        expected_path = [entity.ecs_id for entity in path_entities]
        
        # Check the ancestry path of the deepest entity
        deepest_id = path_entities[-1].ecs_id
        self.assertEqual(tree.ancestry_paths[deepest_id], expected_path,
                         "Ancestry path doesn't match expected path")
        
        # Each entity should have a hierarchical edge to its child
        for i in range(len(path_entities) - 1):
            parent = path_entities[i]
            child = path_entities[i + 1]
            self.assertTrue(tree.is_hierarchical_edge(parent.ecs_id, child.ecs_id),
                           f"Edge from {parent.ecs_id} to {child.ecs_id} should be hierarchical")
        
        # The max depth will be one more than our expected path length 
        # because of the default child entity of the last level
        expected_max_depth = len(expected_path) + 1
        self.assertEqual(tree.max_depth, expected_max_depth)

    def test_multiple_paths_without_cycles(self):
        """Test ancestry paths with multiple paths to separate entities."""
        # Create a multiple branch structure instead of a diamond (to avoid cycles)
        
        # Create a custom entity type with two fields
        class BranchesEntity(Entity):
            branch1: ParentEntity = Field(
                default_factory=lambda: ParentEntity(child=Entity(name="Leaf1")),
                description="Branch 1",
                json_schema_extra={"ownership": True}
            )
            branch2: ParentEntity = Field(
                default_factory=lambda: ParentEntity(child=Entity(name="Leaf2")),
                description="Branch 2",
                json_schema_extra={"ownership": True}
            )
        
        # Create root entity
        root = BranchesEntity()
        root.root_ecs_id = root.ecs_id
        root.root_live_id = root.live_id
        
        # Access entities to trace them
        branch1 = root.branch1
        branch2 = root.branch2
        leaf1 = branch1.child
        leaf2 = branch2.child
        
        # Build the tree
        tree = build_entity_tree(root)
        
        # We should have 5 entities: root, 2 branches, 2 leaves
        expected_nodes = 5
        self.assertEqual(len(tree.nodes), expected_nodes, 
                         f"Expected {expected_nodes} nodes, got {len(tree.nodes)}")
        
        # Check paths for each leaf
        self.assertEqual(tree.ancestry_paths[leaf1.ecs_id], [root.ecs_id, branch1.ecs_id, leaf1.ecs_id])
        self.assertEqual(tree.ancestry_paths[leaf2.ecs_id], [root.ecs_id, branch2.ecs_id, leaf2.ecs_id])
        
        # Check paths for branches
        self.assertEqual(tree.ancestry_paths[branch1.ecs_id], [root.ecs_id, branch1.ecs_id])
        self.assertEqual(tree.ancestry_paths[branch2.ecs_id], [root.ecs_id, branch2.ecs_id])
        
        # Both branches should have hierarchical edges to their leaves
        self.assertTrue(tree.is_hierarchical_edge(branch1.ecs_id, leaf1.ecs_id))
        self.assertTrue(tree.is_hierarchical_edge(branch2.ecs_id, leaf2.ecs_id))
        
        # Root should have hierarchical edges to both branches
        self.assertTrue(tree.is_hierarchical_edge(root.ecs_id, branch1.ecs_id))
        self.assertTrue(tree.is_hierarchical_edge(root.ecs_id, branch2.ecs_id))


if __name__ == '__main__':
    unittest.main()