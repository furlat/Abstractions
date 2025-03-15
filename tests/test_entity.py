"""
Tests for the Entity class in the ECS system.
"""
import unittest
from uuid import UUID, uuid4
from datetime import datetime, timezone

from abstractions.ecs.entity import Entity


class TestEntityBasics(unittest.TestCase):
    """Test basic Entity functionality excluding graph operations."""

    def test_entity_initialization(self):
        """Test that Entity initializes with correct default values."""
        entity = Entity()
        
        # Check that IDs are generated
        self.assertIsInstance(entity.ecs_id, UUID)
        self.assertIsInstance(entity.live_id, UUID)
        self.assertIsInstance(entity.lineage_id, UUID)
        
        # Check default values
        self.assertIsNone(entity.previous_ecs_id)
        self.assertEqual(entity.old_ids, [])
        self.assertFalse(entity.from_storage)
        self.assertEqual(entity.untyped_data, "")
        self.assertIsNone(entity.forked_at)
        
        # Check that created_at is a recent timestamp
        self.assertIsInstance(entity.created_at, datetime)
        time_diff = datetime.now(timezone.utc) - entity.created_at
        self.assertLess(time_diff.total_seconds(), 2)  # Should be within 2 seconds
        
        # Root references should be None by default
        self.assertIsNone(entity.root_ecs_id)
        self.assertIsNone(entity.root_live_id)

    def test_entity_custom_initialization(self):
        """Test Entity initialization with custom values."""
        custom_ecs_id = uuid4()
        custom_live_id = uuid4()
        custom_lineage_id = uuid4()
        custom_previous_id = uuid4()
        
        entity = Entity(
            ecs_id=custom_ecs_id,
            live_id=custom_live_id,
            lineage_id=custom_lineage_id,
            previous_ecs_id=custom_previous_id,
            old_ids=[custom_previous_id],
            from_storage=True,
            untyped_data="test data"
        )
        
        # Check custom values were set correctly
        self.assertEqual(entity.ecs_id, custom_ecs_id)
        self.assertEqual(entity.live_id, custom_live_id)
        self.assertEqual(entity.lineage_id, custom_lineage_id)
        self.assertEqual(entity.previous_ecs_id, custom_previous_id)
        self.assertEqual(entity.old_ids, [custom_previous_id])
        self.assertTrue(entity.from_storage)
        self.assertEqual(entity.untyped_data, "test data")

    def test_is_root_entity(self):
        """Test is_root_entity method."""
        # Entity with matching root_ecs_id should be a root
        entity = Entity()
        entity.root_ecs_id = entity.ecs_id
        self.assertTrue(entity.is_root_entity())
        
        # Entity with different root_ecs_id should not be a root
        entity.root_ecs_id = uuid4()
        self.assertFalse(entity.is_root_entity())
        
        # Entity with None root_ecs_id should not be a root
        entity.root_ecs_id = None
        self.assertFalse(entity.is_root_entity())

    def test_is_orphan(self):
        """Test is_orphan method."""
        entity = Entity()
        
        # Entity with both root IDs as None should be an orphan
        entity.root_ecs_id = None
        entity.root_live_id = None
        self.assertTrue(entity.is_orphan())
        
        # Entity with only root_ecs_id set should still be an orphan
        entity.root_ecs_id = uuid4()
        entity.root_live_id = None
        self.assertTrue(entity.is_orphan())
        
        # Entity with only root_live_id set should still be an orphan
        entity.root_ecs_id = None
        entity.root_live_id = uuid4()
        self.assertTrue(entity.is_orphan())
        
        # Entity with both root IDs set should not be an orphan
        entity.root_ecs_id = uuid4()
        entity.root_live_id = uuid4()
        self.assertFalse(entity.is_orphan())

    def test_update_ecs_ids(self):
        """Test the update_ecs_ids method."""
        entity = Entity()
        old_ecs_id = entity.ecs_id
        
        # Update IDs without specifying new root
        entity.update_ecs_ids()
        
        # Check that ecs_id changed
        self.assertNotEqual(entity.ecs_id, old_ecs_id)
        
        # Check that old_ecs_id is set to old ecs_id
        self.assertEqual(entity.old_ecs_id, old_ecs_id)
        
        # Check that old_ids contains the old ecs_id
        self.assertIn(old_ecs_id, entity.old_ids)
        
        # Check that forked_at is set
        self.assertIsNotNone(entity.forked_at)
        
        # Update IDs with new root
        second_ecs_id = entity.ecs_id
        new_root_id = uuid4()
        entity.update_ecs_ids(new_root_ecs_id=new_root_id)
        
        # Check that ecs_id changed again
        self.assertNotEqual(entity.ecs_id, second_ecs_id)
        
        # Check that old_ecs_id is updated
        self.assertEqual(entity.old_ecs_id, second_ecs_id)
        
        # Check that old_ids contains both old ecs_ids
        self.assertIn(old_ecs_id, entity.old_ids)
        self.assertIn(second_ecs_id, entity.old_ids)
        
        # Check that root_ecs_id is updated
        self.assertEqual(entity.root_ecs_id, new_root_id)

    def test_detach(self):
        """Test detach method."""
        # Create an entity that's not a root
        entity = Entity()
        root_id = uuid4()
        entity.root_ecs_id = root_id
        entity.root_live_id = uuid4()
        old_ecs_id = entity.ecs_id
        
        # Detach without promoting
        entity.detach()
        
        # Check that root references are cleared
        self.assertIsNone(entity.root_ecs_id)
        self.assertIsNone(entity.root_live_id)
        
        # Check that ecs_id changed
        self.assertNotEqual(entity.ecs_id, old_ecs_id)
        
        # Check that old_ecs_id is set to old ecs_id
        self.assertEqual(entity.old_ecs_id, old_ecs_id)
        
        # Detach with promoting to root
        entity = Entity()
        entity.root_ecs_id = root_id
        entity.root_live_id = uuid4()
        old_ecs_id = entity.ecs_id
        
        entity.detach(promote_to_root=True)
        
        # Check that ecs_id changed
        self.assertNotEqual(entity.ecs_id, old_ecs_id)
        
        # Check that root references are set to self
        self.assertEqual(entity.root_ecs_id, entity.ecs_id)
        self.assertEqual(entity.root_live_id, entity.live_id)
        
        # Test detaching a root entity (should do nothing)
        root_entity = Entity()
        root_entity.root_ecs_id = root_entity.ecs_id
        original_ecs_id = root_entity.ecs_id
        
        root_entity.detach()
        
        # Check that ecs_id didn't change (no detach occurred)
        self.assertEqual(root_entity.ecs_id, original_ecs_id)

    def test_attach(self):
        """Test attach method."""
        # Create an orphan entity
        orphan = Entity()
        
        # Create a non-orphan entity to attach to
        host = Entity()
        host.root_ecs_id = host.ecs_id
        host.root_live_id = host.live_id
        
        # Remember original IDs
        original_orphan_ecs_id = orphan.ecs_id
        original_orphan_lineage_id = orphan.lineage_id
        
        # Attach the orphan
        orphan.attach(host)
        
        # Check that root references are updated
        self.assertEqual(orphan.root_ecs_id, host.root_ecs_id)
        self.assertEqual(orphan.root_live_id, host.root_live_id)
        
        # Check that lineage_id is updated
        self.assertEqual(orphan.lineage_id, host.lineage_id)
        self.assertNotEqual(orphan.lineage_id, original_orphan_lineage_id)
        
        # Check that ecs_id changed
        self.assertNotEqual(orphan.ecs_id, original_orphan_ecs_id)
        
        # Check that old_ecs_id is set to old ecs_id
        self.assertEqual(orphan.old_ecs_id, original_orphan_ecs_id)
        
        # Test attaching to an orphan (should raise ValueError)
        orphan2 = Entity()
        with self.assertRaises(ValueError):
            orphan2.attach(orphan2)  # Can't attach to an orphan

    def test_attach_detach_workflow(self):
        """Test a complete attach/detach workflow."""
        # Create a root entity
        root = Entity()
        root.root_ecs_id = root.ecs_id
        root.root_live_id = root.live_id
        
        # Create an entity that's already attached to some root
        entity = Entity()
        other_root_id = uuid4()
        entity.root_ecs_id = other_root_id
        entity.root_live_id = uuid4()
        original_ecs_id = entity.ecs_id
        
        # Attach to the new root
        entity.attach(root)
        
        # Verify it's correctly attached
        self.assertEqual(entity.root_ecs_id, root.ecs_id)
        self.assertEqual(entity.root_live_id, root.live_id)
        self.assertNotEqual(entity.ecs_id, original_ecs_id)
        
        # Now detach and promote to root
        second_ecs_id = entity.ecs_id
        entity.detach(promote_to_root=True)
        
        # Verify it's correctly detached and promoted
        self.assertEqual(entity.root_ecs_id, entity.ecs_id)
        self.assertEqual(entity.root_live_id, entity.live_id)
        self.assertNotEqual(entity.ecs_id, second_ecs_id)


if __name__ == '__main__':
    unittest.main()