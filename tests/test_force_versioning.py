import unittest
from uuid import UUID

from abstractions.ecs.entity import (
    Entity,
    EntityRegistry
)

class TestForceVersioning(unittest.TestCase):
    """Test the force_versioning flag in EntityRegistry.version_entity"""
    
    def setUp(self):
        """Reset the registry before each test"""
        EntityRegistry.tree_registry = {}
        EntityRegistry.lineage_registry = {}
        EntityRegistry.live_id_registry = {}
        EntityRegistry.type_registry = {}
    
    def test_basic_force_versioning(self):
        """Test that force_versioning causes entity IDs to change even without changes"""
        # Create and register a simple entity
        entity = Entity()
        entity.root_ecs_id = entity.ecs_id
        entity.root_live_id = entity.live_id
        EntityRegistry.register_entity(entity)
        
        # Save the original ID
        original_ecs_id = entity.ecs_id
        
        # Call version_entity without any changes
        # Normally this wouldn't change the ID
        result = EntityRegistry.version_entity(entity)
        
        # The ID should not have changed without force_versioning
        self.assertEqual(entity.ecs_id, original_ecs_id)
        
        # Inspect the entity and registry before force versioning
        second_ecs_id = entity.ecs_id
        print(f"\nBefore force_versioning:")
        print(f"entity.ecs_id: {entity.ecs_id}")
        print(f"entity.root_ecs_id: {entity.root_ecs_id}")
        print(f"entity in registry: {entity.ecs_id in EntityRegistry.tree_registry}")
        
        # Use a try-except to catch and examine the error
        try:
            result = EntityRegistry.version_entity(entity, force_versioning=True)
            
            # This should only run if no exception is raised
            print(f"\nAfter force_versioning (success):")
            print(f"entity.ecs_id: {entity.ecs_id}")
            print(f"entity.root_ecs_id: {entity.root_ecs_id}")
            print(f"entity in registry: {entity.ecs_id in EntityRegistry.tree_registry}")
            
            # The ID should have changed now
            self.assertNotEqual(entity.ecs_id, second_ecs_id)
            
            # Check that the entity is properly registered with the new ID
            self.assertIn(entity.ecs_id, EntityRegistry.tree_registry)
        except Exception as e:
            # Print detailed debug info if there's an error
            print(f"\nError during force_versioning: {str(e)}")
            print(f"entity.ecs_id: {entity.ecs_id}")
            print(f"entity.root_ecs_id: {entity.root_ecs_id}")
            print(f"Keys in tree_registry: {list(EntityRegistry.tree_registry.keys())}")
            
            # Re-raise the exception to make the test fail as before
            raise

if __name__ == "__main__":
    unittest.main()