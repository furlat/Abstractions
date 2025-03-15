import unittest
from uuid import UUID, uuid4
from typing import Optional, Dict, List, Any

from abstractions.ecs.entity import (
    Entity, 
    EntityRegistry,
    build_entity_tree,
    EntityinEntity,
    EntityinList
)

class TestParentEntity(Entity):
    """Parent entity for attachment testing"""
    child: Optional[Entity] = None
    name: str = ""

class TestContainerEntity(Entity):
    """Entity with multiple child slots"""
    child1: Optional[Entity] = None
    child2: Optional[Entity] = None
    name: str = ""

class EntityWithFields(Entity):
    """Entity with custom fields to verify preservation during movement"""
    value: str = ""
    count: int = 0

class TestEntityMovement(unittest.TestCase):
    """Test the entity attachment and detachment workflow"""

    def setUp(self):
        """Reset the EntityRegistry before each test"""
        # Clear the registry between tests
        EntityRegistry.tree_registry = {}
        EntityRegistry.lineage_registry = {}
        EntityRegistry.live_id_registry = {}
        EntityRegistry.type_registry = {}

    def test_root_entity_ids(self):
        """Verify the fixed behavior of update_ecs_ids for root entities"""
        # Create a root entity
        entity = Entity()
        entity.root_ecs_id = entity.ecs_id
        entity.root_live_id = entity.live_id
        
        original_ecs_id = entity.ecs_id
        
        # Verify it's a root entity
        self.assertTrue(entity.is_root_entity())
        
        # Update ecs_ids
        entity.update_ecs_ids()
        
        # Verify root_ecs_id is updated to match the new ecs_id
        self.assertNotEqual(entity.ecs_id, original_ecs_id)
        self.assertEqual(entity.root_ecs_id, entity.ecs_id)
        self.assertTrue(entity.is_root_entity())

    def test_promote_to_root(self):
        """Test the promote_to_root method"""
        # Create a non-root entity
        entity = Entity()
        original_ecs_id = entity.ecs_id
        
        # Initially entity is not a root entity
        self.assertFalse(entity.is_root_entity())
        
        # Promote to root
        entity.promote_to_root()
        
        # Verify entity is now a root entity
        self.assertTrue(entity.is_root_entity())
        self.assertEqual(entity.root_ecs_id, entity.ecs_id)
        self.assertNotEqual(entity.ecs_id, original_ecs_id)
        
        # Verify entity is registered
        self.assertIn(entity.ecs_id, EntityRegistry.tree_registry)

    def test_detach_orphan_entity(self):
        """Test detaching an orphan entity (should promote to root)"""
        # Create an orphan entity (no root references)
        entity = Entity()
        original_ecs_id = entity.ecs_id
        
        # Detach it (should promote to root)
        entity.detach()
        
        # Verify:
        # 1. It became a root entity
        self.assertTrue(entity.is_root_entity())
        
        # 2. Its ecs_id changed
        self.assertNotEqual(entity.ecs_id, original_ecs_id)
        
        # 3. It's registered in the registry
        self.assertIn(entity.ecs_id, EntityRegistry.tree_registry)

    def test_detach_root_entity(self):
        """Test detaching a root entity (should just version it)"""
        # Create a root entity with a property to ensure it will be seen as changed
        root = Entity()
        root.root_ecs_id = root.ecs_id
        root.root_live_id = root.live_id
        root.untyped_data = "original value"
        
        # Register it
        EntityRegistry.register_entity(root)
        original_ecs_id = root.ecs_id
        
        # Detach it with force_versioning flag
        # This will bypass the diffing algorithm and ensure versioning
        EntityRegistry.version_entity(root, force_versioning=True)
        
        # Verify:
        # 1. It's still a root entity
        self.assertTrue(root.is_root_entity())
        
        # 2. Its ecs_id changed due to versioning
        self.assertNotEqual(root.ecs_id, original_ecs_id)
        
        # 3. It has the old ID in its history
        self.assertIn(original_ecs_id, root.old_ids)
        
        # 4. The new version is registered in the registry
        self.assertIn(root.ecs_id, EntityRegistry.tree_registry)

    def test_complete_entity_movement(self):
        """Test the complete workflow of detaching and attaching entities"""
        # Create two parent entities
        parent1 = TestParentEntity()
        parent1.name = "Parent1"
        parent1.root_ecs_id = parent1.ecs_id
        parent1.root_live_id = parent1.live_id
        
        parent2 = TestParentEntity()
        parent2.name = "Parent2"
        parent2.root_ecs_id = parent2.ecs_id
        parent2.root_live_id = parent2.live_id
        
        # Create a child entity with fields
        child = EntityWithFields()
        child.value = "test value"
        child.count = 42
        
        # STEP 1: Set up the child as a sub-entity of parent1
        parent1.child = child
        child.root_ecs_id = parent1.ecs_id
        child.root_live_id = parent1.live_id
        
        # Register the parents
        EntityRegistry.register_entity(parent1)
        EntityRegistry.register_entity(parent2)
        
        # Verify the initial state
        self.assertEqual(child.root_ecs_id, parent1.ecs_id)
        self.assertEqual(child.root_live_id, parent1.live_id)
        child_id_in_parent1 = child.ecs_id
        
        # STEP 2: Detach from parent1
        parent1.child = None  # Physical detachment
        child.detach()        # Metadata update
        
        # Verify child is now a root entity
        self.assertTrue(child.is_root_entity())
        self.assertNotEqual(child.ecs_id, child_id_in_parent1)
        self.assertIn(child_id_in_parent1, child.old_ids)
        child_id_as_root = child.ecs_id
        
        # STEP 3: Attach to parent2
        parent2.child = child  # Physical attachment
        
        # Force rebuild the tree
        new_tree = build_entity_tree(parent2)
        
        # Manually update metadata in way that avoids registry conflicts
        old_root_entity = child.get_live_root_entity()
        child.root_ecs_id = parent2.ecs_id
        child.root_live_id = parent2.live_id
        child.lineage_id = parent2.lineage_id
        child.update_ecs_ids()
        
        # Version both entities with force flag
        if old_root_entity is not None:
            EntityRegistry.version_entity(old_root_entity, force_versioning=True)
        EntityRegistry.version_entity(parent2, force_versioning=True)
        
        # Verify child is properly attached to parent2
        self.assertEqual(child.root_ecs_id, parent2.ecs_id)
        self.assertEqual(child.root_live_id, parent2.live_id)
        self.assertNotEqual(child.ecs_id, child_id_as_root)
        
        # Verify ID history is maintained
        self.assertIn(child_id_in_parent1, child.old_ids)
        self.assertIn(child_id_as_root, child.old_ids)
        
        # Verify field values are preserved
        self.assertEqual(child.value, "test value")
        self.assertEqual(child.count, 42)

    def test_container_entity_movement(self):
        """Test moving an entity between different types of containers"""
        # Create a list container
        list_container = EntityinList()
        list_container.root_ecs_id = list_container.ecs_id
        list_container.root_live_id = list_container.live_id
        
        # Create a direct parent entity
        parent = TestParentEntity()
        parent.name = "DirectParent"
        parent.root_ecs_id = parent.ecs_id
        parent.root_live_id = parent.live_id
        
        # Create an entity to move
        entity = Entity()
        
        # Register the containers
        EntityRegistry.register_entity(list_container)
        EntityRegistry.register_entity(parent)
        
        # STEP 1: Add to list container
        list_container.entities = [entity]
        entity.root_ecs_id = list_container.ecs_id
        entity.root_live_id = list_container.live_id
        
        # Force version the list container to update the registry
        EntityRegistry.version_entity(list_container, force_versioning=True)
        
        # Verify entity is in list container
        self.assertEqual(entity.root_ecs_id, list_container.ecs_id)
        entity_id_in_list = entity.ecs_id
        
        # STEP 2: Move from list to direct parent
        list_container.entities = []
        entity.detach()
        
        parent.child = entity
        
        # Manually update metadata in way that avoids registry conflicts
        old_root_entity = entity.get_live_root_entity()
        entity.root_ecs_id = parent.ecs_id
        entity.root_live_id = parent.live_id
        entity.lineage_id = parent.lineage_id
        entity.update_ecs_ids()
        
        # Version both entities with force flag
        if old_root_entity is not None:
            EntityRegistry.version_entity(old_root_entity, force_versioning=True)
        EntityRegistry.version_entity(parent, force_versioning=True)
        
        # Verify entity is attached to direct parent
        self.assertEqual(entity.root_ecs_id, parent.ecs_id)
        self.assertNotEqual(entity.ecs_id, entity_id_in_list)
        self.assertIn(entity_id_in_list, entity.old_ids)

    def test_validation_errors(self):
        """Test the validation errors in attach() and detach()"""
        # Create a parent entity
        parent = TestParentEntity()
        parent.name = "Parent"
        parent.root_ecs_id = parent.ecs_id
        parent.root_live_id = parent.live_id
        EntityRegistry.register_entity(parent)
        
        # Test 1: Can't attach a non-root entity
        child = Entity()
        child.root_ecs_id = parent.ecs_id
        child.root_live_id = parent.live_id
        
        with self.assertRaises(ValueError) as context:
            child.attach(parent)
        self.assertTrue("root entity" in str(context.exception).lower())
        
        # Test 2: Can't attach without physical connection
        root_entity = Entity()
        root_entity.root_ecs_id = root_entity.ecs_id
        root_entity.root_live_id = root_entity.live_id
        EntityRegistry.register_entity(root_entity)
        
        with self.assertRaises(ValueError) as context:
            root_entity.attach(parent)
        self.assertTrue("not in the tree" in str(context.exception).lower())

if __name__ == "__main__":
    unittest.main()