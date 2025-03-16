"""
Tests for Entity containers and nested entity relationships.
"""
import unittest
from uuid import UUID

from abstractions.ecs.entity import (
    Entity, EntityinEntity, EntityinList, EntityinDict, 
    EntityinTuple, EntityinSet, EntityinBaseModel, 
    EntityInEntityInEntity, HierarchicalEntity
)


class TestEntityContainers(unittest.TestCase):
    """Test Entity with various container types."""

    def test_entity_in_entity(self):
        """Test EntityinEntity - direct entity reference."""
        container = EntityinEntity()
        
        # Check that sub_entity was created
        self.assertIsNotNone(container.sub_entity)
        self.assertIsInstance(container.sub_entity, Entity)
        
        # Check that IDs are different
        self.assertNotEqual(container.ecs_id, container.sub_entity.ecs_id)
        self.assertNotEqual(container.live_id, container.sub_entity.live_id)

    def test_entity_list(self):
        """Test EntityinList - list of entities."""
        # Test with empty list
        empty_container = EntityinList(entities=[])
        self.assertEqual(len(empty_container.entities), 0)
        
        # Test with populated list
        entities = [Entity() for _ in range(3)]
        container = EntityinList(entities=entities)
        
        # Check that list was set correctly
        self.assertEqual(len(container.entities), 3)
        for e in container.entities:
            self.assertIsInstance(e, Entity)
            
        # Check that each entity has unique IDs
        ecs_ids = [e.ecs_id for e in container.entities]
        live_ids = [e.live_id for e in container.entities]
        self.assertEqual(len(set(ecs_ids)), 3)
        self.assertEqual(len(set(live_ids)), 3)

    def test_entity_dict(self):
        """Test EntityinDict - dictionary of entities."""
        # Test with empty dict
        empty_container = EntityinDict(entities={})
        self.assertEqual(len(empty_container.entities), 0)
        
        # Test with populated dict
        entities = {f"key{i}": Entity() for i in range(3)}
        container = EntityinDict(entities=entities)
        
        # Check that dict was set correctly
        self.assertEqual(len(container.entities), 3)
        for key, value in container.entities.items():
            self.assertTrue(key.startswith("key"))
            self.assertIsInstance(value, Entity)
            
        # Check that each entity has unique IDs
        ecs_ids = [e.ecs_id for e in container.entities.values()]
        live_ids = [e.live_id for e in container.entities.values()]
        self.assertEqual(len(set(ecs_ids)), 3)
        self.assertEqual(len(set(live_ids)), 3)

    def test_entity_tuple(self):
        """Test EntityinTuple - tuple of entities."""
        # Create entities for tuple
        entities = tuple(Entity() for _ in range(3))
        container = EntityinTuple(entities=entities)
        
        # Check that tuple was set correctly
        self.assertEqual(len(container.entities), 3)
        self.assertIsInstance(container.entities, tuple)
        for e in container.entities:
            self.assertIsInstance(e, Entity)
            
        # Check that each entity has unique IDs
        ecs_ids = [e.ecs_id for e in container.entities]
        live_ids = [e.live_id for e in container.entities]
        self.assertEqual(len(set(ecs_ids)), 3)
        self.assertEqual(len(set(live_ids)), 3)

    def test_entity_set(self):
        """Test EntityinSet - set of entities."""
        # Create entities for set - store in list first to verify the count
        entity_list = [Entity() for _ in range(3)]
        entities = set(entity_list)  # Convert to set
        container = EntityinSet(entities=entities)
        
        # Check that set was set correctly
        self.assertEqual(len(container.entities), 3)
        self.assertIsInstance(container.entities, set)
        for e in container.entities:
            self.assertIsInstance(e, Entity)
            
        # Check that each entity is in the set
        for e in entity_list:
            self.assertIn(e, container.entities)
            
        # Check that each entity has unique IDs
        ecs_ids = {e.ecs_id for e in container.entities}
        live_ids = {e.live_id for e in container.entities}
        self.assertEqual(len(ecs_ids), 3)
        self.assertEqual(len(live_ids), 3)

    def test_entity_in_basemodel(self):
        """Test EntityinBaseModel - entity in a Pydantic BaseModel."""
        container = EntityinBaseModel()
        
        # Check that base_model was created
        self.assertIsNotNone(container.base_model)
        
        # Check that base_model contains an entity
        self.assertIsNotNone(container.base_model.entity)
        self.assertIsInstance(container.base_model.entity, Entity)
        
        # Check that all IDs are different
        self.assertNotEqual(container.ecs_id, container.base_model.entity.ecs_id)

    def test_nested_entity_hierarchy(self):
        """Test EntityInEntityInEntity - deeply nested entities."""
        container = EntityInEntityInEntity()
        
        # Check that nested structure was created correctly
        self.assertIsNotNone(container.entity_of_entity)
        self.assertIsInstance(container.entity_of_entity, EntityinEntity)
        
        self.assertIsNotNone(container.entity_of_entity.sub_entity)
        self.assertIsInstance(container.entity_of_entity.sub_entity, Entity)
        
        # Check that all IDs are different
        self.assertNotEqual(container.ecs_id, container.entity_of_entity.ecs_id)
        self.assertNotEqual(container.ecs_id, container.entity_of_entity.sub_entity.ecs_id)
        self.assertNotEqual(container.entity_of_entity.ecs_id, container.entity_of_entity.sub_entity.ecs_id)

    def test_hierarchical_entity(self):
        """Test HierarchicalEntity - multiple entity relationships."""
        container = HierarchicalEntity()
        
        # Check all entities were created
        self.assertIsNotNone(container.entity_of_entity_1)
        self.assertIsNotNone(container.entity_of_entity_2)
        self.assertIsNotNone(container.flat_entity)
        self.assertIsNotNone(container.entity_of_entity_of_entity)
        
        # Check types
        self.assertIsInstance(container.entity_of_entity_1, EntityinEntity)
        self.assertIsInstance(container.entity_of_entity_2, EntityinEntity)
        self.assertIsInstance(container.flat_entity, Entity)
        self.assertIsInstance(container.entity_of_entity_of_entity, EntityInEntityInEntity)
        
        # Check sub-entities
        self.assertIsNotNone(container.entity_of_entity_1.sub_entity)
        self.assertIsNotNone(container.entity_of_entity_2.sub_entity)
        self.assertIsNotNone(container.entity_of_entity_of_entity.entity_of_entity)
        self.assertIsNotNone(container.entity_of_entity_of_entity.entity_of_entity.sub_entity)
        
        # Check all top-level IDs are different
        ecs_ids = [
            container.ecs_id,
            container.entity_of_entity_1.ecs_id,
            container.entity_of_entity_2.ecs_id,
            container.flat_entity.ecs_id,
            container.entity_of_entity_of_entity.ecs_id
        ]
        self.assertEqual(len(set(ecs_ids)), 5)


if __name__ == '__main__':
    unittest.main()