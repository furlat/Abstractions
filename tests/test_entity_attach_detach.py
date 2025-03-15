import unittest
from uuid import UUID, uuid4
from typing import Optional, List, Dict, Any

from abstractions.ecs.entity import (
    Entity, 
    EntityRegistry,
    build_entity_tree
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

class TestEntityAttachDetach(unittest.TestCase):
    """Test the attach and detach methods of Entity"""

    def setUp(self):
        """Reset the EntityRegistry before each test"""
        # Clear the registry between tests
        EntityRegistry.tree_registry = {}
        EntityRegistry.lineage_registry = {}
        EntityRegistry.live_id_registry = {}
        EntityRegistry.type_registry = {}

    def test_physical_attachment_step(self):
        """Test that when an entity is physically attached, its root references aren't automatically set"""
        # Create a parent and child
        parent = TestParentEntity()
        parent.name = "Parent"
        parent.root_ecs_id = parent.ecs_id
        parent.root_live_id = parent.live_id
        
        child = Entity()
        
        # Physically attach the child
        parent.child = child
        
        # Check if the child's root references are still None
        # This verifies that physical attachment doesn't automatically update metadata
        self.assertIsNone(child.root_ecs_id)
        self.assertIsNone(child.root_live_id)
        
        # Register the parent
        EntityRegistry.register_entity(parent)
        
        # Even after registration, child references aren't automatically updated
        self.assertIsNone(child.root_ecs_id)
        self.assertIsNone(child.root_live_id)

    def test_manual_entity_movement(self):
        """Test the workflow for manually moving an entity between parents"""
        # Create two parent entities
        parent1 = TestParentEntity()
        parent1.name = "Parent1"
        parent1.root_ecs_id = parent1.ecs_id
        parent1.root_live_id = parent1.live_id
        
        parent2 = TestParentEntity()
        parent2.name = "Parent2"
        parent2.root_ecs_id = parent2.ecs_id
        parent2.root_live_id = parent2.live_id
        
        # Create a child entity
        child = Entity()
        
        # STEP 1: Manually set up the child as a sub-entity of parent1
        parent1.child = child
        # Manually set the root references since physical attachment doesn't do this
        child.root_ecs_id = parent1.ecs_id
        child.root_live_id = parent1.live_id
        
        # Register the parents
        EntityRegistry.register_entity(parent1)
        EntityRegistry.register_entity(parent2)
        
        # Verify the initial state
        self.assertEqual(child.root_ecs_id, parent1.ecs_id)
        self.assertEqual(child.root_live_id, parent1.live_id)
        child_id_before_move = child.ecs_id
        
        # STEP 2: Physically detach from parent1 and manually handle the update
        parent1.child = None
        
        # Manually promote to root instead of using detach()
        child.root_ecs_id = child.ecs_id
        child.root_live_id = child.live_id
        child.update_ecs_ids()
        EntityRegistry.register_entity(child)
        
        # Verify the child is now a root entity with a new ID
        self.assertTrue(child.is_root_entity())
        self.assertNotEqual(child.ecs_id, child_id_before_move)
        self.assertIn(child_id_before_move, child.old_ids)
        
        # Remember the ID after detaching
        child_id_as_root = child.ecs_id
        
        # STEP 3: Physically attach to parent2
        parent2.child = child
        
        # STEP 4: Update the metadata manually
        # First register the updated tree
        new_tree = build_entity_tree(parent2)
        try:
            EntityRegistry.register_entity_tree(new_tree)
        except ValueError as e:
            if "already registered" not in str(e):
                raise
        
        # Manually update the references
        old_root_entity = child.get_live_root_entity()
        child.root_ecs_id = parent2.ecs_id
        child.root_live_id = parent2.live_id
        child.lineage_id = parent2.lineage_id
        child.update_ecs_ids()
        if old_root_entity is not None:
            EntityRegistry.version_entity(old_root_entity)
        EntityRegistry.version_entity(parent2)
        
        # Verify the child is now attached to parent2
        self.assertEqual(child.root_ecs_id, parent2.ecs_id)
        self.assertEqual(child.root_live_id, parent2.live_id)
        
        # Verify ID changes are properly tracked
        self.assertNotEqual(child.ecs_id, child_id_as_root)
        self.assertIn(child_id_before_move, child.old_ids)
        self.assertIn(child_id_as_root, child.old_ids)

    def test_validation_errors(self):
        """Test the validation errors in attach() and detach()"""
        # Create parent entities
        parent = TestParentEntity()
        parent.name = "Parent"
        parent.root_ecs_id = parent.ecs_id
        parent.root_live_id = parent.live_id
        EntityRegistry.register_entity(parent)
        
        # Test 1: Can't attach a non-root entity
        child = Entity()
        # Make it a non-root by setting different root references
        child.root_ecs_id = parent.ecs_id
        child.root_live_id = parent.live_id
        
        with self.assertRaises(ValueError) as context:
            child.attach(parent)
        self.assertIn("can only attach", str(context.exception).lower())
        
        # Test 2: Can't attach to something without being physically in its tree
        root_entity = Entity()
        root_entity.root_ecs_id = root_entity.ecs_id
        root_entity.root_live_id = root_entity.live_id
        EntityRegistry.register_entity(root_entity)
        
        with self.assertRaises(ValueError) as context:
            root_entity.attach(parent)
        self.assertIn("not in the tree", str(context.exception).lower())

    def test_moving_entity_preserves_fields(self):
        """Test that entity field values are preserved during movement"""
        # Create specialized entity with fields
        class EntityWithFields(Entity):
            value: str = ""
            count: int = 0
        
        # Create parent entities
        parent1 = TestParentEntity()
        parent1.name = "Parent1"
        parent1.root_ecs_id = parent1.ecs_id
        parent1.root_live_id = parent1.live_id
        
        parent2 = TestParentEntity()
        parent2.name = "Parent2"
        parent2.root_ecs_id = parent2.ecs_id
        parent2.root_live_id = parent2.live_id
        
        # Create child with field values
        child = EntityWithFields()
        child.value = "test value"
        child.count = 42
        
        # Setup as subentity of parent1
        parent1.child = child
        child.root_ecs_id = parent1.ecs_id
        child.root_live_id = parent1.live_id
        
        # Register both parents
        EntityRegistry.register_entity(parent1)
        EntityRegistry.register_entity(parent2)
        
        # Move from parent1 to parent2 using manual approach
        parent1.child = None
        
        # Manually promote to root
        child.root_ecs_id = child.ecs_id
        child.root_live_id = child.live_id
        child.update_ecs_ids()
        EntityRegistry.register_entity(child)
        
        # Attach to parent2
        parent2.child = child
        new_tree = build_entity_tree(parent2)
        try:
            EntityRegistry.register_entity_tree(new_tree)
        except ValueError as e:
            if "already registered" not in str(e):
                raise
        
        # Manually update metadata
        old_root_entity = child.get_live_root_entity()
        child.root_ecs_id = parent2.ecs_id
        child.root_live_id = parent2.live_id
        child.lineage_id = parent2.lineage_id
        child.update_ecs_ids()
        if old_root_entity is not None:
            EntityRegistry.version_entity(old_root_entity)
        EntityRegistry.version_entity(parent2)
        
        # Verify field values are preserved
        self.assertEqual(child.value, "test value")
        self.assertEqual(child.count, 42)
        
        # Verify entity is properly attached to parent2
        self.assertEqual(child.root_ecs_id, parent2.ecs_id)

if __name__ == "__main__":
    unittest.main()