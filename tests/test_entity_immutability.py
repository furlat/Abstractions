"""
Test the immutability behavior of entity tree retrieval from EntityRegistry.
"""
import unittest
from uuid import UUID, uuid4

from abstractions.ecs.entity import (
    Entity, 
    EntityRegistry, 
    build_entity_tree,
    EntityinList,
    EntityinDict
)

class TestParentEntity(Entity):
    """Test parent entity with a child field"""
    child: Entity = None
    name: str = ""

class TestImmutability(unittest.TestCase):
    """Test the immutability behavior of entity retrieval from EntityRegistry."""

    def setUp(self):
        """Reset the EntityRegistry before each test."""
        EntityRegistry.tree_registry = {}
        EntityRegistry.lineage_registry = {}
        EntityRegistry.live_id_registry = {}
        EntityRegistry.type_registry = {}
    
    def test_basic_immutability(self):
        """Test that retrieving the same tree twice returns different copies with different live_ids."""
        # Create and register a root entity
        root = Entity()
        root.root_ecs_id = root.ecs_id
        root.root_live_id = root.live_id
        root.untyped_data = "original value"
        EntityRegistry.register_entity(root)
        
        original_root_ecs_id = root.ecs_id
        original_root_live_id = root.live_id
        
        # Get the first copy from the registry
        copy1 = EntityRegistry.get_stored_entity(root.ecs_id, root.ecs_id)
        
        # Get a second copy from the registry
        copy2 = EntityRegistry.get_stored_entity(root.ecs_id, root.ecs_id)
        
        # Verify both copies have the same ecs_id (persistent identity)
        self.assertEqual(copy1.ecs_id, original_root_ecs_id)
        self.assertEqual(copy2.ecs_id, original_root_ecs_id)
        
        # Verify both copies have different live_ids (runtime identity)
        self.assertNotEqual(copy1.live_id, original_root_live_id)
        self.assertNotEqual(copy2.live_id, original_root_live_id)
        self.assertNotEqual(copy1.live_id, copy2.live_id)
        
        # Verify both copies have the same data
        self.assertEqual(copy1.untyped_data, "original value")
        self.assertEqual(copy2.untyped_data, "original value")
    
    def test_hierarchical_immutability(self):
        """Test that retrieving a tree with child entities maintains proper structure with new live_ids."""
        # Create a parent entity with a child
        parent = TestParentEntity()
        parent.root_ecs_id = parent.ecs_id
        parent.root_live_id = parent.live_id
        parent.name = "Parent"
        
        child = Entity()
        child.untyped_data = "child data"
        # Explicitly set the child's root references
        child.root_ecs_id = parent.ecs_id
        child.root_live_id = parent.live_id
        parent.child = child
        
        # Register the parent entity
        EntityRegistry.register_entity(parent)
        
        original_parent_ecs_id = parent.ecs_id
        original_parent_live_id = parent.live_id
        original_child_ecs_id = child.ecs_id
        original_child_live_id = child.live_id
        
        # Get the first copy
        copy1 = EntityRegistry.get_stored_entity(parent.ecs_id, parent.ecs_id)
        copy1_child = copy1.child
        
        # Get a second copy
        copy2 = EntityRegistry.get_stored_entity(parent.ecs_id, parent.ecs_id)
        copy2_child = copy2.child
        
        # Verify the parent's identity
        self.assertEqual(copy1.ecs_id, original_parent_ecs_id)
        self.assertEqual(copy2.ecs_id, original_parent_ecs_id)
        self.assertNotEqual(copy1.live_id, original_parent_live_id)
        self.assertNotEqual(copy2.live_id, original_parent_live_id)
        self.assertNotEqual(copy1.live_id, copy2.live_id)
        
        # Verify the child's identity
        self.assertEqual(copy1_child.ecs_id, original_child_ecs_id)
        self.assertEqual(copy2_child.ecs_id, original_child_ecs_id)
        self.assertNotEqual(copy1_child.live_id, original_child_live_id)
        self.assertNotEqual(copy2_child.live_id, original_child_live_id)
        self.assertNotEqual(copy1_child.live_id, copy2_child.live_id)
        
        # Verify the parent-child relationships in the copies
        self.assertEqual(copy1_child.root_ecs_id, copy1.ecs_id)
        self.assertEqual(copy2_child.root_ecs_id, copy2.ecs_id)
        self.assertEqual(copy1_child.root_live_id, copy1.live_id)
        self.assertEqual(copy2_child.root_live_id, copy2.live_id)
    
    def test_branching_with_immutability(self):
        """Test that modifications to different copies create independent branches."""
        # Create a root entity
        root = Entity()
        root.root_ecs_id = root.ecs_id
        root.root_live_id = root.live_id
        root.untyped_data = "original value"
        EntityRegistry.register_entity(root)
        
        original_lineage_id = root.lineage_id
        
        # Get two copies from the registry
        copy1 = EntityRegistry.get_stored_entity(root.ecs_id, root.ecs_id)
        copy2 = EntityRegistry.get_stored_entity(root.ecs_id, root.ecs_id)
        
        # Modify and version the first copy
        copy1.untyped_data = "modified by copy1"
        EntityRegistry.version_entity(copy1)
        
        # Modify and version the second copy
        copy2.untyped_data = "modified by copy2"
        EntityRegistry.version_entity(copy2)
        
        # Get all versions of this lineage from the registry
        versions = EntityRegistry.lineage_registry.get(original_lineage_id, [])
        
        # We should have at least 3 versions (original + 2 branches)
        self.assertGreaterEqual(len(versions), 3)
        
        # Get the latest versions
        latest_versions = [v for v in versions if v != root.ecs_id]
        
        # Verify we have both branches
        branch1 = None
        branch2 = None
        
        for version_id in latest_versions:
            version = EntityRegistry.get_stored_entity(version_id, version_id)
            if version.untyped_data == "modified by copy1":
                branch1 = version
            elif version.untyped_data == "modified by copy2":
                branch2 = version
        
        self.assertIsNotNone(branch1, "Branch with 'modified by copy1' not found")
        self.assertIsNotNone(branch2, "Branch with 'modified by copy2' not found")
        self.assertNotEqual(branch1.ecs_id, branch2.ecs_id)
    
    def test_immutability_with_containers(self):
        """Test immutability with container entity types (list, dict)."""
        # Create an entity with a list of entities
        list_entity = EntityinList()
        list_entity.root_ecs_id = list_entity.ecs_id
        list_entity.root_live_id = list_entity.live_id
        
        # Add some child entities to the list
        child1 = Entity()
        child1.untyped_data = "child1"
        child2 = Entity()
        child2.untyped_data = "child2"
        list_entity.entities = [child1, child2]
        
        # Register the entity
        EntityRegistry.register_entity(list_entity)
        
        # Retrieve two copies
        copy1 = EntityRegistry.get_stored_entity(list_entity.ecs_id, list_entity.ecs_id)
        copy2 = EntityRegistry.get_stored_entity(list_entity.ecs_id, list_entity.ecs_id)
        
        # Verify the copies have different live_ids
        self.assertNotEqual(copy1.live_id, copy2.live_id)
        
        # Verify the children in the copies have different live_ids
        self.assertNotEqual(copy1.entities[0].live_id, copy2.entities[0].live_id)
        self.assertNotEqual(copy1.entities[1].live_id, copy2.entities[1].live_id)
        
        # Verify the children's root_live_id points to their respective parent's live_id
        self.assertEqual(copy1.entities[0].root_live_id, copy1.live_id)
        self.assertEqual(copy1.entities[1].root_live_id, copy1.live_id)
        self.assertEqual(copy2.entities[0].root_live_id, copy2.live_id)
        self.assertEqual(copy2.entities[1].root_live_id, copy2.live_id)
        
        # Create an entity with a dict of entities
        dict_entity = EntityinDict()
        dict_entity.root_ecs_id = dict_entity.ecs_id
        dict_entity.root_live_id = dict_entity.live_id
        
        # Add some child entities to the dict
        child3 = Entity()
        child3.untyped_data = "child3"
        child4 = Entity()
        child4.untyped_data = "child4"
        dict_entity.entities = {"key1": child3, "key2": child4}
        
        # Register the entity
        EntityRegistry.register_entity(dict_entity)
        
        # Retrieve two copies
        copy3 = EntityRegistry.get_stored_entity(dict_entity.ecs_id, dict_entity.ecs_id)
        copy4 = EntityRegistry.get_stored_entity(dict_entity.ecs_id, dict_entity.ecs_id)
        
        # Verify the copies have different live_ids
        self.assertNotEqual(copy3.live_id, copy4.live_id)
        
        # Verify the children in the copies have different live_ids
        self.assertNotEqual(copy3.entities["key1"].live_id, copy4.entities["key1"].live_id)
        self.assertNotEqual(copy3.entities["key2"].live_id, copy4.entities["key2"].live_id)
        
        # Verify the children's root_live_id points to their respective parent's live_id
        self.assertEqual(copy3.entities["key1"].root_live_id, copy3.live_id)
        self.assertEqual(copy3.entities["key2"].root_live_id, copy3.live_id)
        self.assertEqual(copy4.entities["key1"].root_live_id, copy4.live_id)
        self.assertEqual(copy4.entities["key2"].root_live_id, copy4.live_id)
    
if __name__ == "__main__":
    unittest.main()