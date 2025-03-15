import unittest
from uuid import UUID

from abstractions.ecs.entity import (
    Entity, 
    EntityRegistry
)

class TestPromoteToRoot(unittest.TestCase):
    """Test the promote_to_root method"""

    def setUp(self):
        """Reset the EntityRegistry before each test"""
        # Clear the registry between tests
        EntityRegistry.tree_registry = {}
        EntityRegistry.lineage_registry = {}
        EntityRegistry.live_id_registry = {}
        EntityRegistry.type_registry = {}

    def test_promote_to_root_basic(self):
        """Test basic functionality of promote_to_root"""
        # Create a non-root entity 
        entity = Entity()
        original_ecs_id = entity.ecs_id
        
        # Initially entity is not a root entity
        self.assertFalse(entity.is_root_entity())
        
        # Print debugging info
        print(f"BEFORE promote_to_root:")
        print(f"entity.ecs_id: {entity.ecs_id}")
        print(f"entity.root_ecs_id: {entity.root_ecs_id}")
        print(f"entity.is_root_entity(): {entity.is_root_entity()}")
        
        # Promote to root
        entity.promote_to_root()
        
        # Print after
        print(f"\nAFTER promote_to_root:")
        print(f"entity.ecs_id: {entity.ecs_id}")
        print(f"entity.root_ecs_id: {entity.root_ecs_id}")
        print(f"entity.is_root_entity(): {entity.is_root_entity()}")
        
        # Verify entity is now a root entity
        self.assertTrue(entity.is_root_entity())
        self.assertEqual(entity.root_ecs_id, entity.ecs_id)
        self.assertNotEqual(entity.ecs_id, original_ecs_id)
        
        # Verify entity is registered
        self.assertIn(entity.ecs_id, EntityRegistry.tree_registry)

    def test_update_ecs_ids_for_root(self):
        """Test that update_ecs_ids updates root_ecs_id for root entities"""
        # Create an entity and make it a root entity
        entity = Entity()
        entity.root_ecs_id = entity.ecs_id
        entity.root_live_id = entity.live_id
        
        original_ecs_id = entity.ecs_id
        
        # Verify it's a root entity
        self.assertTrue(entity.is_root_entity())
        
        # Print debugging info
        print(f"BEFORE update_ecs_ids:")
        print(f"entity.ecs_id: {entity.ecs_id}")
        print(f"entity.root_ecs_id: {entity.root_ecs_id}")
        
        # Update ecs_ids
        entity.update_ecs_ids()
        
        # Print after
        print(f"\nAFTER update_ecs_ids:")
        print(f"entity.ecs_id: {entity.ecs_id}")
        print(f"entity.root_ecs_id: {entity.root_ecs_id}")
        
        # Verify root_ecs_id is updated to match the new ecs_id
        self.assertNotEqual(entity.ecs_id, original_ecs_id)
        self.assertEqual(entity.root_ecs_id, entity.ecs_id)
        self.assertTrue(entity.is_root_entity())

if __name__ == "__main__":
    unittest.main()