"""
Tests for Entity hashing and equality behavior.
"""
import unittest
from uuid import uuid4

from abstractions.ecs.entity import Entity


class TestEntityHashing(unittest.TestCase):
    """Test Entity hashing and equality behavior."""

    def test_entity_hash(self):
        """Test that Entity objects can be hashed."""
        entity = Entity()
        # Basic hash test
        hash(entity)  # Should not raise an exception
        
        # Create a set of entities
        entity_set = {entity, Entity(), Entity()}
        self.assertEqual(len(entity_set), 3)
        
    def test_entity_in_dictionary(self):
        """Test that Entity objects can be used as dictionary keys."""
        entity1 = Entity()
        entity2 = Entity()
        entity3 = Entity()
        
        # Create a dictionary with entities as keys
        entity_dict = {
            entity1: "value1",
            entity2: "value2",
            entity3: "value3"
        }
        
        # Verify dictionary operations work
        self.assertEqual(len(entity_dict), 3)
        self.assertEqual(entity_dict[entity1], "value1")
        self.assertEqual(entity_dict[entity2], "value2")
        self.assertEqual(entity_dict[entity3], "value3")
        
    def test_entity_equality(self):
        """Test Entity equality behavior."""
        # Same object should be equal to itself
        entity = Entity()
        self.assertEqual(entity, entity)
        
        # Different objects with same IDs should be equal
        entity1 = Entity()
        entity2 = Entity()
        entity2.ecs_id = entity1.ecs_id
        entity2.live_id = entity1.live_id
        entity2.root_ecs_id = entity1.root_ecs_id
        entity2.root_live_id = entity1.root_live_id
        self.assertEqual(entity1, entity2)
        
        # Different ecs_id should make entities not equal
        entity3 = Entity()
        entity3.ecs_id = uuid4()  # Different ecs_id
        entity3.live_id = entity1.live_id
        entity3.root_ecs_id = entity1.root_ecs_id
        entity3.root_live_id = entity1.root_live_id
        self.assertNotEqual(entity1, entity3)
        
        # With the new immutability implementation, entities with same ecs_id
        # and root_ecs_id are considered equal even with different live_ids
        # This test is updated to match the new behavior
        entity4 = Entity()
        entity4.ecs_id = entity1.ecs_id
        entity4.live_id = uuid4()  # Different live_id
        entity4.root_ecs_id = entity1.root_ecs_id
        entity4.root_live_id = uuid4()  # Different root_live_id
        self.assertEqual(entity1, entity4)  # Now they should be equal based on ecs_id
        
        # Different root_ecs_id should make entities not equal
        entity5 = Entity()
        entity5.ecs_id = entity1.ecs_id
        entity5.live_id = entity1.live_id
        entity5.root_ecs_id = uuid4()  # Different root_ecs_id
        entity5.root_live_id = entity1.root_live_id
        self.assertNotEqual(entity1, entity5)
        
        # With the new immutability implementation, root_live_id no longer affects equality
        entity6 = Entity()
        entity6.ecs_id = entity1.ecs_id
        entity6.live_id = entity1.live_id
        entity6.root_ecs_id = entity1.root_ecs_id
        entity6.root_live_id = uuid4()  # Different root_live_id
        self.assertEqual(entity1, entity6)
        
    def test_hash_consistency(self):
        """Test that hash values are consistent with equality."""
        # Create two entities with the same IDs
        entity1 = Entity()
        entity2 = Entity()
        entity2.ecs_id = entity1.ecs_id
        entity2.live_id = entity1.live_id
        entity2.root_ecs_id = entity1.root_ecs_id
        entity2.root_live_id = entity1.root_live_id
        
        # Equal entities should have equal hash values
        self.assertEqual(hash(entity1), hash(entity2))
        
        # Create entity with different IDs
        entity3 = Entity()
        # Different entities should have different hash values
        self.assertNotEqual(hash(entity1), hash(entity3))
        
    def test_entity_hash_set_behavior(self):
        """Test Entity behavior in sets with equality."""
        # Create entities with the same IDs
        entity1 = Entity()
        entity2 = Entity()
        entity2.ecs_id = entity1.ecs_id
        entity2.live_id = entity1.live_id
        entity2.root_ecs_id = entity1.root_ecs_id
        entity2.root_live_id = entity1.root_live_id
        
        # Equal entities should behave as the same item in a set
        entity_set = {entity1, entity2}
        self.assertEqual(len(entity_set), 1)
        
        # Add an entity with different IDs
        entity3 = Entity()
        entity_set.add(entity3)
        self.assertEqual(len(entity_set), 2)
        
        # Test that changing an ID affects set membership
        entity4 = Entity()
        entity4.ecs_id = entity1.ecs_id
        entity4.live_id = entity1.live_id
        entity4.root_ecs_id = entity1.root_ecs_id
        entity4.root_live_id = entity1.root_live_id
        
        entity_set = {entity1, entity4}
        # With the new implementation, entities with same ecs_id and root_ecs_id
        # are considered the same entity
        self.assertEqual(len(entity_set), 1)
        
        # Changing live_id doesn't change the entity identity anymore
        entity4.live_id = uuid4()
        
        # Adding again shouldn't change the set size
        entity_set.add(entity4)
        # Still only one unique entity based on ecs_id
        self.assertEqual(len(entity_set), 1)
        
        # But changing the ecs_id WILL make it a different entity
        entity4.ecs_id = uuid4()
        entity_set.add(entity4)
        self.assertEqual(len(entity_set), 2)


if __name__ == '__main__':
    unittest.main()