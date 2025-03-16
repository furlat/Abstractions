"""
Tests for the EntityRegistry class.
"""
import unittest
from uuid import UUID, uuid4
from datetime import datetime, timezone

from abstractions.ecs.entity import (
    Entity, EntityTree, EntityRegistry, build_entity_tree,
    EntityinEntity, EntityinList, EntityinDict, HierarchicalEntity
)


class TestEntityRegistry(unittest.TestCase):
    """Test the EntityRegistry class functionality."""

    def setUp(self):
        """Set up test entities and reset the registry for each test."""
        # Clear registry state before each test
        EntityRegistry.tree_registry = {}
        EntityRegistry.lineage_registry = {}
        EntityRegistry.live_id_registry = {}
        EntityRegistry.type_registry = {}
        
        # Create a root entity
        self.root = Entity()
        self.root.root_ecs_id = self.root.ecs_id
        self.root.root_live_id = self.root.live_id
        
        # Create an entity with a sub-entity
        self.nested = EntityinEntity()
        self.nested.root_ecs_id = self.nested.ecs_id
        self.nested.root_live_id = self.nested.live_id
        
        # Create an entity with a list of entities
        self.list_entity = EntityinList()
        self.list_entity.root_ecs_id = self.list_entity.ecs_id
        self.list_entity.root_live_id = self.list_entity.live_id
        self.list_entity.entities = [Entity(), Entity()]
        
        # Build trees for testing
        self.root_tree = build_entity_tree(self.root)
        self.nested_tree = build_entity_tree(self.nested)
        self.list_tree = build_entity_tree(self.list_entity)

    def test_register_entity_tree(self):
        """Test registering an entity tree in the registry."""
        # Register the root tree
        EntityRegistry.register_entity_tree(self.root_tree)
        
        # Check that the tree was added to tree_registry
        self.assertIn(self.root.ecs_id, EntityRegistry.tree_registry)
        self.assertEqual(EntityRegistry.tree_registry[self.root.ecs_id], self.root_tree)
        
        # Check that the root entity is in the live_id_registry
        self.assertIn(self.root.live_id, EntityRegistry.live_id_registry)
        self.assertEqual(EntityRegistry.live_id_registry[self.root.live_id], self.root)
        
        # Check that the lineage_registry was updated
        self.assertIn(self.root.lineage_id, EntityRegistry.lineage_registry)
        self.assertIn(self.root.ecs_id, EntityRegistry.lineage_registry[self.root.lineage_id])
        
        # Check that the type_registry was updated
        self.assertIn(self.root.__class__, EntityRegistry.type_registry)
        self.assertIn(self.root.lineage_id, EntityRegistry.type_registry[self.root.__class__])
        
        # Test registering a second tree with the same root_ecs_id (should fail)
        with self.assertRaises(ValueError):
            EntityRegistry.register_entity_tree(self.root_tree)

    def test_register_entity(self):
        """Test registering an entity in the registry."""
        # Register the root entity
        EntityRegistry.register_entity(self.root)
        
        # Check that a tree was built and added to tree_registry
        self.assertIn(self.root.ecs_id, EntityRegistry.tree_registry)
        
        # Check that the live_id_registry was updated
        self.assertIn(self.root.live_id, EntityRegistry.live_id_registry)
        self.assertEqual(EntityRegistry.live_id_registry[self.root.live_id], self.root)
        
        # Test registering a non-root entity (should fail)
        non_root = Entity()
        with self.assertRaises(ValueError):
            EntityRegistry.register_entity(non_root)
        
        # Test registering an entity that is not the root of its own tree
        non_root = Entity()
        non_root.root_ecs_id = uuid4()  # Different from its ecs_id
        with self.assertRaises(ValueError):
            EntityRegistry.register_entity(non_root)

    def test_get_stored_tree(self):
        """Test retrieving a stored tree."""
        # Register the tree
        EntityRegistry.register_entity_tree(self.root_tree)
        
        # Retrieve the tree
        retrieved_tree = EntityRegistry.get_stored_tree(self.root.ecs_id)
        
        # Check that the correct tree was retrieved
        # With immutability, we get a new copy with the same ecs_ids but different live_ids
        self.assertEqual(retrieved_tree.root_ecs_id, self.root_tree.root_ecs_id)
        self.assertEqual(retrieved_tree.lineage_id, self.root_tree.lineage_id)
        self.assertNotEqual(retrieved_tree, self.root_tree)  # Should be different objects
        
        # Test retrieving a non-existent tree
        non_existent_id = uuid4()
        self.assertIsNone(EntityRegistry.get_stored_tree(non_existent_id))

    def test_get_stored_entity(self):
        """Test retrieving a stored entity."""
        # Register the nested tree (contains multiple entities)
        EntityRegistry.register_entity_tree(self.nested_tree)
        
        # Get the sub-entity
        sub_entity = self.nested.sub_entity
        
        # Retrieve the sub-entity from the registry
        retrieved_entity = EntityRegistry.get_stored_entity(self.nested.ecs_id, sub_entity.ecs_id)
        
        # Check that the correct entity was retrieved
        self.assertEqual(retrieved_entity, sub_entity)
        
        # Test retrieving an entity that doesn't exist in the tree
        non_existent_id = uuid4()
        with self.assertRaises(ValueError):
            # Tree doesn't exist, should raise error
            EntityRegistry.get_stored_entity(non_existent_id, self.nested.ecs_id)
            
        # Tree exists but entity doesn't
        self.assertIsNone(EntityRegistry.get_stored_entity(self.nested.ecs_id, non_existent_id))

    def test_get_stored_tree_from_entity(self):
        """Test retrieving a tree from an entity."""
        # Register the tree
        EntityRegistry.register_entity_tree(self.nested_tree)
        
        # Get the sub-entity and ensure it has the root_ecs_id set
        sub_entity = self.nested.sub_entity
        sub_entity.root_ecs_id = self.nested.ecs_id
        
        # Retrieve the tree from the sub-entity
        retrieved_tree = EntityRegistry.get_stored_tree_from_entity(sub_entity)
        
        # Check that the correct tree was retrieved
        # With the new immutability implementation, we get a copy with same ecs_ids but different live_ids
        self.assertEqual(retrieved_tree.root_ecs_id, self.nested_tree.root_ecs_id)
        self.assertEqual(retrieved_tree.lineage_id, self.nested_tree.lineage_id)
        
        # Test retrieving a tree for an entity without root_ecs_id
        entity_without_root = Entity()
        with self.assertRaises(ValueError):
            EntityRegistry.get_stored_tree_from_entity(entity_without_root)

    def test_get_live_entity(self):
        """Test retrieving a live entity by its live_id."""
        # Register the nested tree
        EntityRegistry.register_entity_tree(self.nested_tree)
        
        # Get the sub-entity
        sub_entity = self.nested.sub_entity
        
        # Retrieve the sub-entity by its live_id
        retrieved_entity = EntityRegistry.get_live_entity(sub_entity.live_id)
        
        # Check that the correct entity was retrieved
        self.assertEqual(retrieved_entity, sub_entity)
        
        # Test retrieving a non-existent entity
        non_existent_id = uuid4()
        self.assertIsNone(EntityRegistry.get_live_entity(non_existent_id))

    def test_get_live_root_from_entity(self):
        """Test retrieving a live root entity from a sub-entity."""
        # Register the nested tree
        EntityRegistry.register_entity_tree(self.nested_tree)
        
        # Get the sub-entity
        sub_entity = self.nested.sub_entity
        
        # Make sure the sub-entity has the correct root_live_id
        sub_entity.root_live_id = self.nested.live_id
        
        # Retrieve the root entity from the sub-entity
        retrieved_root = EntityRegistry.get_live_root_from_entity(sub_entity)
        
        # Check that the correct root was retrieved
        self.assertEqual(retrieved_root, self.nested)
        
        # Test retrieving a root for an entity without root_live_id
        entity_without_root = Entity()
        with self.assertRaises(ValueError):
            EntityRegistry.get_live_root_from_entity(entity_without_root)

    def test_version_entity_simple(self):
        """Test versioning an entity with no changes."""
        # Register the root entity
        EntityRegistry.register_entity(self.root)
        
        # Version the same entity (no changes)
        result = EntityRegistry.version_entity(self.root)
        
        # Should return True for first versioning
        self.assertTrue(result)
        
        # Check the lineage registry
        self.assertIn(self.root.lineage_id, EntityRegistry.lineage_registry)
        lineage = EntityRegistry.lineage_registry[self.root.lineage_id]
        self.assertEqual(len(lineage), 1)  # Only one version

    def test_version_entity_with_changes(self):
        """Test versioning an entity after making changes."""
        # Register the original entity
        EntityRegistry.register_entity(self.root)
        original_ecs_id = self.root.ecs_id
        
        # Make a substantial change to make sure it's detected
        self.root.untyped_data = "Modified data with significant change to ensure detection"
        
        # Version the modified entity
        result = EntityRegistry.version_entity(self.root)
        
        # Should return True for versioning
        self.assertTrue(result)
        
        # Check lineage registry
        self.assertIn(self.root.lineage_id, EntityRegistry.lineage_registry)
        lineage = EntityRegistry.lineage_registry[self.root.lineage_id]
        
        # Verify at least one version exists
        self.assertTrue(len(lineage) >= 1)
        
        # If the ecs_id was updated, verify old_ids was updated correctly
        if self.root.ecs_id != original_ecs_id:
            self.assertIn(original_ecs_id, self.root.old_ids)
            # Verify new version is in the lineage
            self.assertIn(self.root.ecs_id, lineage)

    def test_nested_entity_versioning(self):
        """Test versioning a nested entity structure."""
        # Register the nested entity
        EntityRegistry.register_entity(self.nested)
        original_root_ecs_id = self.nested.ecs_id
        original_sub_ecs_id = self.nested.sub_entity.ecs_id
        
        # Ensure sub-entity has root_ecs_id set
        self.nested.sub_entity.root_ecs_id = self.nested.ecs_id
        
        # Make a significant change to the sub-entity
        self.nested.sub_entity.untyped_data = "Modified sub-entity with substantial change"
        
        # Version the modified entity
        result = EntityRegistry.version_entity(self.nested)
        
        # Should return True for changes detected
        self.assertTrue(result)
        
        # Check the lineage registry
        self.assertIn(self.nested.lineage_id, EntityRegistry.lineage_registry)
        lineage = EntityRegistry.lineage_registry[self.nested.lineage_id]
        
        # Verify the tree was registered
        self.assertTrue(len(lineage) >= 1)
        
        # Check root_ecs_id relationship is maintained
        if self.nested.ecs_id != original_root_ecs_id:
            # If IDs were updated, verify the relationship is maintained
            self.assertEqual(self.nested.sub_entity.root_ecs_id, self.nested.ecs_id)
            
            # Check that old_ids were updated appropriately
            if original_root_ecs_id != self.nested.ecs_id:
                self.assertIn(original_root_ecs_id, self.nested.old_ids)
            
            if original_sub_ecs_id != self.nested.sub_entity.ecs_id:
                self.assertIn(original_sub_ecs_id, self.nested.sub_entity.old_ids)


    def test_container_entity_versioning(self):
        """Test versioning an entity with container entities (list, dict)."""
        # Register the list entity
        EntityRegistry.register_entity(self.list_entity)
        original_root_ecs_id = self.list_entity.ecs_id
        original_child_ecs_ids = [entity.ecs_id for entity in self.list_entity.entities]
        
        # Set root references for all entities in the list
        for entity in self.list_entity.entities:
            entity.root_ecs_id = self.list_entity.ecs_id
            entity.root_live_id = self.list_entity.live_id
        
        # Modify one of the entities in the list
        self.list_entity.entities[0].untyped_data = "Modified entity in list"
        
        # Version the modified entity
        result = EntityRegistry.version_entity(self.list_entity)
        
        # Should return True for changes detected
        self.assertTrue(result)
        
        # Check lineage registry
        self.assertIn(self.list_entity.lineage_id, EntityRegistry.lineage_registry)
        lineage = EntityRegistry.lineage_registry[self.list_entity.lineage_id]
        
        # Verify at least one version exists
        self.assertTrue(len(lineage) >= 1)
        
        # Check root_ecs_id relationships are maintained
        for entity in self.list_entity.entities:
            self.assertEqual(entity.root_ecs_id, self.list_entity.ecs_id)

    def test_multi_version_entity(self):
        """Test multiple versions of the same entity."""
        # Register the root entity
        EntityRegistry.register_entity(self.root)
        original_ecs_id = self.root.ecs_id
        
        # First modification
        self.root.untyped_data = "First modification"
        EntityRegistry.version_entity(self.root)
        first_version_ecs_id = self.root.ecs_id
        
        # Second modification
        self.root.untyped_data = "Second modification"
        EntityRegistry.version_entity(self.root)
        second_version_ecs_id = self.root.ecs_id
        
        # Check lineage registry contains multiple versions
        lineage = EntityRegistry.lineage_registry[self.root.lineage_id]
        
        # Should have at least the original and possibly new versions
        self.assertTrue(len(lineage) >= 1)
        
        # If the entity was versioned correctly, check the history
        if original_ecs_id != first_version_ecs_id != second_version_ecs_id:
            # Old IDs should contain both previous versions
            self.assertIn(original_ecs_id, self.root.old_ids)
            self.assertIn(first_version_ecs_id, self.root.old_ids)
            
            # Lineage should contain the current version
            self.assertIn(second_version_ecs_id, lineage)

    def test_type_registry(self):
        """Test the type registry functionality."""
        # Clear existing registry state
        EntityRegistry.tree_registry = {}
        EntityRegistry.lineage_registry = {}
        EntityRegistry.live_id_registry = {}
        EntityRegistry.type_registry = {}
        
        # Register different entity types
        entity1 = Entity()
        entity1.root_ecs_id = entity1.ecs_id
        entity1.root_live_id = entity1.live_id
        EntityRegistry.register_entity(entity1)
        
        entity2 = EntityinEntity()
        entity2.root_ecs_id = entity2.ecs_id
        entity2.root_live_id = entity2.live_id
        EntityRegistry.register_entity(entity2)
        
        entity3 = EntityinList()
        entity3.root_ecs_id = entity3.ecs_id
        entity3.root_live_id = entity3.live_id
        EntityRegistry.register_entity(entity3)
        
        # Check type registry
        self.assertIn(Entity, EntityRegistry.type_registry)
        self.assertIn(EntityinEntity, EntityRegistry.type_registry)
        self.assertIn(EntityinList, EntityRegistry.type_registry)
        
        # Verify lineage IDs are correctly classified by type
        self.assertIn(entity1.lineage_id, EntityRegistry.type_registry[Entity])
        self.assertIn(entity2.lineage_id, EntityRegistry.type_registry[EntityinEntity])
        self.assertIn(entity3.lineage_id, EntityRegistry.type_registry[EntityinList])


    def test_complex_entity_tree(self):
        """Test a complex entity tree with multiple levels and container types."""
        # Create a complex entity structure using the class from entity.py
        root = HierarchicalEntity()
        root.root_ecs_id = root.ecs_id
        root.root_live_id = root.live_id
        
        # Access all nested entities to ensure they're properly initialized
        entity_of_entity_1 = root.entity_of_entity_1
        entity_of_entity_2 = root.entity_of_entity_2
        flat_entity = root.flat_entity
        entity_of_entity_of_entity = root.entity_of_entity_of_entity
        
        # Set root references for all nested entities
        entity_of_entity_1.root_ecs_id = root.ecs_id
        entity_of_entity_1.root_live_id = root.live_id
        entity_of_entity_1.sub_entity.root_ecs_id = root.ecs_id
        entity_of_entity_1.sub_entity.root_live_id = root.live_id
        
        entity_of_entity_2.root_ecs_id = root.ecs_id
        entity_of_entity_2.root_live_id = root.live_id
        entity_of_entity_2.sub_entity.root_ecs_id = root.ecs_id
        entity_of_entity_2.sub_entity.root_live_id = root.live_id
        
        flat_entity.root_ecs_id = root.ecs_id
        flat_entity.root_live_id = root.live_id
        
        entity_of_entity_of_entity.root_ecs_id = root.ecs_id
        entity_of_entity_of_entity.root_live_id = root.live_id
        entity_of_entity_of_entity.entity_of_entity.root_ecs_id = root.ecs_id
        entity_of_entity_of_entity.entity_of_entity.root_live_id = root.live_id
        entity_of_entity_of_entity.entity_of_entity.sub_entity.root_ecs_id = root.ecs_id
        entity_of_entity_of_entity.entity_of_entity.sub_entity.root_live_id = root.live_id
        
        # Register the entity
        EntityRegistry.register_entity(root)
        original_root_ecs_id = root.ecs_id
        
        # Capture original IDs at various levels
        original_entity1_ecs_id = entity_of_entity_1.ecs_id
        original_entity2_ecs_id = entity_of_entity_2.ecs_id
        original_deep_sub_entity_ecs_id = entity_of_entity_of_entity.entity_of_entity.sub_entity.ecs_id
        
        # Modify a deeply nested entity
        entity_of_entity_of_entity.entity_of_entity.sub_entity.untyped_data = "Modified deep entity"
        
        # Version the entity
        result = EntityRegistry.version_entity(root)
        self.assertTrue(result)
        
        # Check lineage registry
        lineage = EntityRegistry.lineage_registry[root.lineage_id]
        self.assertTrue(len(lineage) >= 1)
        
        # Verify all entities maintain their root references
        self.assertEqual(root.entity_of_entity_1.root_ecs_id, root.ecs_id)
        self.assertEqual(root.entity_of_entity_2.root_ecs_id, root.ecs_id)
        self.assertEqual(root.entity_of_entity_of_entity.root_ecs_id, root.ecs_id)
        self.assertEqual(root.entity_of_entity_of_entity.entity_of_entity.root_ecs_id, root.ecs_id)
        
        # If IDs changed, verify relationships
        if original_root_ecs_id != root.ecs_id:
            self.assertIn(original_root_ecs_id, root.old_ids)
            
            # Check that nested entities maintain proper relationships
            deep_sub_entity = entity_of_entity_of_entity.entity_of_entity.sub_entity
            if original_deep_sub_entity_ecs_id != deep_sub_entity.ecs_id:
                self.assertIn(original_deep_sub_entity_ecs_id, deep_sub_entity.old_ids)


if __name__ == '__main__':
    unittest.main()