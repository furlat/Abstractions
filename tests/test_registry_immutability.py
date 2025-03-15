"""
Test the immutability behavior specifically for entities retrieved from the EntityRegistry.
"""
import unittest
from uuid import UUID, uuid4

from abstractions.ecs.entity import (
    Entity, 
    EntityRegistry, 
    build_entity_tree,
    EntityinList
)

class TestParentEntity(Entity):
    """Test parent entity with a child field"""
    child: Entity = None
    name: str = ""

class TestRegistryImmutability(unittest.TestCase):
    """Test the immutability behavior when retrieving entities from the EntityRegistry."""

    def setUp(self):
        """Reset the EntityRegistry before each test."""
        EntityRegistry.tree_registry = {}
        EntityRegistry.lineage_registry = {}
        EntityRegistry.live_id_registry = {}
        EntityRegistry.type_registry = {}
    
    def test_stored_tree_immutability(self):
        """Test that each call to get_stored_tree returns a new copy with new live_ids."""
        # Create a simple entity hierarchy
        root = TestParentEntity()
        root.name = "Root"
        root.root_ecs_id = root.ecs_id
        root.root_live_id = root.live_id
        
        child = Entity()
        child.untyped_data = "Child data"
        root.child = child
        
        # Register the entity
        EntityRegistry.register_entity(root)
        
        # Store original IDs
        original_root_ecs_id = root.ecs_id
        original_root_live_id = root.live_id
        original_child_ecs_id = child.ecs_id
        original_child_live_id = child.live_id
        
        # Get the tree directly from registry - first copy
        tree1 = EntityRegistry.get_stored_tree(root.ecs_id)
        root1 = tree1.get_entity(root.ecs_id)
        child1 = root1.child
        
        # Get the tree again - second copy
        tree2 = EntityRegistry.get_stored_tree(root.ecs_id)
        root2 = tree2.get_entity(root.ecs_id)
        child2 = root2.child
        
        # Verify persistence IDs (ecs_id) are preserved
        self.assertEqual(root1.ecs_id, original_root_ecs_id)
        self.assertEqual(root2.ecs_id, original_root_ecs_id)
        self.assertEqual(child1.ecs_id, original_child_ecs_id)
        self.assertEqual(child2.ecs_id, original_child_ecs_id)
        
        # Verify runtime IDs (live_id) are different
        self.assertNotEqual(root1.live_id, original_root_live_id)
        self.assertNotEqual(root2.live_id, original_root_live_id)
        self.assertNotEqual(child1.live_id, original_child_live_id)
        self.assertNotEqual(child2.live_id, original_child_live_id)
        
        # Critical: Verify the two copies have DIFFERENT live_ids
        self.assertNotEqual(root1.live_id, root2.live_id)
        self.assertNotEqual(child1.live_id, child2.live_id)
        
        # Verify parent-child relationships are maintained in each copy
        self.assertEqual(child1.root_live_id, root1.live_id)
        self.assertEqual(child2.root_live_id, root2.live_id)
    
    def test_branching_behavior(self):
        """Test that modifying different copies creates different branches in the version history."""
        # Create a root entity
        root = Entity()
        root.untyped_data = "Original data"
        root.root_ecs_id = root.ecs_id
        root.root_live_id = root.live_id
        
        # Register the entity
        EntityRegistry.register_entity(root)
        original_ecs_id = root.ecs_id
        
        # Get two copies from the registry
        tree1 = EntityRegistry.get_stored_tree(root.ecs_id)
        root1 = tree1.get_entity(root.ecs_id)
        
        tree2 = EntityRegistry.get_stored_tree(root.ecs_id)
        root2 = tree2.get_entity(root.ecs_id)
        
        # Verify they have different live_ids
        self.assertNotEqual(root1.live_id, root2.live_id)
        
        # Modify each copy differently
        root1.untyped_data = "Modified by copy 1"
        root2.untyped_data = "Modified by copy 2"
        
        # Version both copies
        # This should create two new branches in the version history
        EntityRegistry.version_entity(root1)
        EntityRegistry.version_entity(root2)
        
        # Get all versions in the lineage
        lineage_id = root.lineage_id
        versions = EntityRegistry.lineage_registry.get(lineage_id, [])
        
        # We should have at least 3 versions (original + 2 branches)
        self.assertGreaterEqual(len(versions), 3, 
                              f"Expected at least 3 versions, got {len(versions)}: {versions}")
        
        # Verify we can retrieve both branches and they have different data
        branch_data = set()
        for version_id in versions:
            if version_id != original_ecs_id:  # Skip the original
                tree = EntityRegistry.get_stored_tree(version_id)
                entity = tree.get_entity(version_id)
                branch_data.add(entity.untyped_data)
        
        # Verify both modifications were preserved
        self.assertIn("Modified by copy 1", branch_data)
        self.assertIn("Modified by copy 2", branch_data)
    
    def test_container_immutability(self):
        """Test immutability with container entity types."""
        # Create an entity with list of entities
        container = EntityinList()
        container.root_ecs_id = container.ecs_id
        container.root_live_id = container.live_id
        
        # Add entities to the list
        for i in range(3):
            e = Entity()
            e.untyped_data = f"Entity {i}"
            container.entities.append(e)
        
        # Register the container
        EntityRegistry.register_entity(container)
        
        # Get two copies from the registry
        tree1 = EntityRegistry.get_stored_tree(container.ecs_id)
        container1 = tree1.get_entity(container.ecs_id)
        
        tree2 = EntityRegistry.get_stored_tree(container.ecs_id)
        container2 = tree2.get_entity(container.ecs_id)
        
        # Verify the containers have different live_ids
        self.assertNotEqual(container1.live_id, container2.live_id)
        
        # Verify each contained entity has different live_ids between copies
        for i in range(3):
            self.assertNotEqual(container1.entities[i].live_id, container2.entities[i].live_id)
        
        # Verify the contained entities point to their respective container's live_id
        for i in range(3):
            self.assertEqual(container1.entities[i].root_live_id, container1.live_id)
            self.assertEqual(container2.entities[i].root_live_id, container2.live_id)

if __name__ == "__main__":
    unittest.main()