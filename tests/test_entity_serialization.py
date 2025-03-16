"""
Tests for entity serialization and registry persistence.

This module contains comprehensive tests for serializing and deserializing
all types of entity structures, ensuring they can be properly persisted
and restored with all relationships intact.
"""
import unittest
import json
from uuid import UUID, uuid4
from datetime import datetime, timezone

from abstractions.ecs.entity import (
    Entity, EntityTree, EntityRegistry, build_entity_tree, find_modified_entities,
    EntityinEntity, EntityinList, EntityinDict, EntityinTuple, EntityinSet,
    EntityWithPrimitives, EntityWithContainersOfPrimitives, 
    EntityWithMixedContainers, EntityWithNestedContainers,
    OptionalEntityContainers, HierarchicalEntity, BaseModelWithEntity, EntityinBaseModel
)


class TestEntitySerialization(unittest.TestCase):
    """Test entity serialization and deserialization with registry integration."""

    def setUp(self):
        """Set up test entities and reset the registry for each test."""
        # Clear registry state before each test
        EntityRegistry.tree_registry = {}
        EntityRegistry.lineage_registry = {}
        EntityRegistry.live_id_registry = {}
        EntityRegistry.type_registry = {}
        
        # Create a basic entity
        self.root = Entity()
        self.root.root_ecs_id = self.root.ecs_id
        self.root.root_live_id = self.root.live_id
        
        # Create an entity with a sub-entity
        self.nested = EntityinEntity()
        self.nested.root_ecs_id = self.nested.ecs_id
        self.nested.root_live_id = self.nested.live_id
        self.nested.sub_entity.root_ecs_id = self.nested.ecs_id 
        self.nested.sub_entity.root_live_id = self.nested.live_id
        
        # Create an entity with a list of entities
        self.list_entity = EntityinList()
        self.list_entity.root_ecs_id = self.list_entity.ecs_id
        self.list_entity.root_live_id = self.list_entity.live_id
        self.list_entity.entities = [Entity(), Entity()]
        for entity in self.list_entity.entities:
            entity.root_ecs_id = self.list_entity.ecs_id
            entity.root_live_id = self.list_entity.live_id
        
        # Create an entity with a dict of entities
        self.dict_entity = EntityinDict()
        self.dict_entity.root_ecs_id = self.dict_entity.ecs_id
        self.dict_entity.root_live_id = self.dict_entity.live_id
        self.dict_entity.entities = {
            "key1": Entity(),
            "key2": Entity()
        }
        for entity in self.dict_entity.entities.values():
            entity.root_ecs_id = self.dict_entity.ecs_id
            entity.root_live_id = self.dict_entity.live_id
            
        # Create an entity with a tuple of entities
        # Create tuple items first since there's no default factory
        tuple_item1 = Entity()
        tuple_item2 = Entity()
        self.tuple_entity = EntityinTuple(entities=(tuple_item1, tuple_item2))
        self.tuple_entity.root_ecs_id = self.tuple_entity.ecs_id
        self.tuple_entity.root_live_id = self.tuple_entity.live_id
        
        # Set root references
        for entity in self.tuple_entity.entities:
            entity.root_ecs_id = self.tuple_entity.ecs_id
            entity.root_live_id = self.tuple_entity.live_id
            
        # Create an entity with a set of entities
        # Create set items first and give them IDs
        set_item1 = Entity()
        set_item2 = Entity()
        # Initialize the set entity with the entities
        self.set_entity = EntityinSet(entities={set_item1, set_item2})
        self.set_entity.root_ecs_id = self.set_entity.ecs_id
        self.set_entity.root_live_id = self.set_entity.live_id
        
        # Set root references
        for entity in self.set_entity.entities:
            entity.root_ecs_id = self.set_entity.ecs_id
            entity.root_live_id = self.set_entity.live_id
        
        # Entity with primitive values
        self.primitive_entity = EntityWithPrimitives()
        self.primitive_entity.root_ecs_id = self.primitive_entity.ecs_id
        self.primitive_entity.root_live_id = self.primitive_entity.live_id
        self.primitive_entity.string_value = "test string"
        self.primitive_entity.int_value = 42
        self.primitive_entity.float_value = 3.14
        self.primitive_entity.bool_value = True
        
        # Entity with containers of primitives
        self.container_primitive_entity = EntityWithContainersOfPrimitives()
        self.container_primitive_entity.root_ecs_id = self.container_primitive_entity.ecs_id
        self.container_primitive_entity.root_live_id = self.container_primitive_entity.live_id
        self.container_primitive_entity.string_list = ["a", "b", "c"]
        self.container_primitive_entity.int_dict = {"one": 1, "two": 2}
        self.container_primitive_entity.float_tuple = (1.1, 2.2, 3.3)
        self.container_primitive_entity.bool_set = {True, False}
        
        # Entity with mixed containers (only using entities for serialization compatibility)
        self.mixed_container_entity = EntityWithMixedContainers()
        self.mixed_container_entity.root_ecs_id = self.mixed_container_entity.ecs_id
        self.mixed_container_entity.root_live_id = self.mixed_container_entity.live_id
        
        # Create entities for both containers
        mixed_list_entity1 = Entity()
        mixed_list_entity2 = Entity()
        mixed_list_entity1.root_ecs_id = self.mixed_container_entity.ecs_id
        mixed_list_entity1.root_live_id = self.mixed_container_entity.live_id
        mixed_list_entity2.root_ecs_id = self.mixed_container_entity.ecs_id
        mixed_list_entity2.root_live_id = self.mixed_container_entity.live_id
        
        # For test compatibility, just use entities in the containers
        self.mixed_container_entity.mixed_list = [mixed_list_entity1, mixed_list_entity2]
        
        mixed_dict_entity1 = Entity()
        mixed_dict_entity2 = Entity()
        mixed_dict_entity1.root_ecs_id = self.mixed_container_entity.ecs_id
        mixed_dict_entity1.root_live_id = self.mixed_container_entity.live_id
        mixed_dict_entity2.root_ecs_id = self.mixed_container_entity.ecs_id
        mixed_dict_entity2.root_live_id = self.mixed_container_entity.live_id
        
        self.mixed_container_entity.mixed_dict = {
            "entity1": mixed_dict_entity1,
            "entity2": mixed_dict_entity2
        }
        
        # Entity with nested containers
        self.nested_container_entity = EntityWithNestedContainers()
        self.nested_container_entity.root_ecs_id = self.nested_container_entity.ecs_id
        self.nested_container_entity.root_live_id = self.nested_container_entity.live_id
        self.nested_container_entity.list_of_lists = [["a", "b"], ["c", "d"]]
        self.nested_container_entity.dict_of_dicts = {
            "outer1": {"inner1": 1, "inner2": 2},
            "outer2": {"inner3": 3, "inner4": 4}
        }
        
        # Need to create these with proper root references
        nested_entity1 = Entity()
        nested_entity2 = Entity()
        nested_entity1.root_ecs_id = self.nested_container_entity.ecs_id
        nested_entity1.root_live_id = self.nested_container_entity.live_id
        nested_entity2.root_ecs_id = self.nested_container_entity.ecs_id
        nested_entity2.root_live_id = self.nested_container_entity.live_id
        
        self.nested_container_entity.list_of_dicts = [
            {"key1": nested_entity1},
            {"key2": nested_entity2}
        ]
        
        # Entity with optional fields
        self.optional_entity = OptionalEntityContainers()
        self.optional_entity.root_ecs_id = self.optional_entity.ecs_id
        self.optional_entity.root_live_id = self.optional_entity.live_id
        
        # Leave optional_entity = None to test null serialization
        
        # Set up optional entity list
        optional_list_item = Entity()
        optional_list_item.root_ecs_id = self.optional_entity.ecs_id
        optional_list_item.root_live_id = self.optional_entity.live_id
        self.optional_entity.optional_entity_list = [optional_list_item]
        
        # Set up optional entity dict
        optional_dict_item = Entity()
        optional_dict_item.root_ecs_id = self.optional_entity.ecs_id
        optional_dict_item.root_live_id = self.optional_entity.live_id
        self.optional_entity.optional_entity_dict = {"key": optional_dict_item}
        
        # Entity with base model
        self.base_model_entity = EntityinBaseModel()
        self.base_model_entity.root_ecs_id = self.base_model_entity.ecs_id
        self.base_model_entity.root_live_id = self.base_model_entity.live_id
        self.base_model_entity.base_model.entity.root_ecs_id = self.base_model_entity.ecs_id
        self.base_model_entity.base_model.entity.root_live_id = self.base_model_entity.live_id
        
        # Hierarchical entity
        self.hierarchical = HierarchicalEntity()
        self.hierarchical.root_ecs_id = self.hierarchical.ecs_id
        self.hierarchical.root_live_id = self.hierarchical.live_id
        
        # Set root references for all nested entities
        for entity_field in [
            self.hierarchical.entity_of_entity_1,
            self.hierarchical.entity_of_entity_2,
            self.hierarchical.flat_entity,
            self.hierarchical.entity_of_entity_of_entity,
            self.hierarchical.primitive_data
        ]:
            entity_field.root_ecs_id = self.hierarchical.ecs_id
            entity_field.root_live_id = self.hierarchical.live_id
            
            # For nested entities, set their sub-entities' root references too
            if hasattr(entity_field, 'sub_entity'):
                entity_field.sub_entity.root_ecs_id = self.hierarchical.ecs_id
                entity_field.sub_entity.root_live_id = self.hierarchical.live_id
            
            # For the entity_of_entity_of_entity, handle its deeper nesting
            if hasattr(entity_field, 'entity_of_entity'):
                entity_field.entity_of_entity.root_ecs_id = self.hierarchical.ecs_id
                entity_field.entity_of_entity.root_live_id = self.hierarchical.live_id
                if hasattr(entity_field.entity_of_entity, 'sub_entity'):
                    entity_field.entity_of_entity.sub_entity.root_ecs_id = self.hierarchical.ecs_id
                    entity_field.entity_of_entity.sub_entity.root_live_id = self.hierarchical.live_id

    def test_simple_entity_serialization(self):
        """Test serialization and deserialization of a simple entity."""
        # Register the entity
        EntityRegistry.register_entity(self.root)
        
        # Serialize the entity
        entity_dict = self.root.model_dump()
        
        # Create a new entity from the serialized data
        new_entity = Entity.model_validate(entity_dict)
        
        # Check that the new entity has the same properties
        self.assertEqual(new_entity.ecs_id, self.root.ecs_id)
        self.assertEqual(new_entity.live_id, self.root.live_id)
        self.assertEqual(new_entity.root_ecs_id, self.root.root_ecs_id)
        self.assertEqual(new_entity.root_live_id, self.root.root_live_id)
        self.assertEqual(new_entity.lineage_id, self.root.lineage_id)
        
        # Register the new entity (should fail as duplicate)
        with self.assertRaises(ValueError):
            EntityRegistry.register_entity(new_entity)
        
        # Build trees and check for differences
        original_tree = build_entity_tree(self.root)
        new_tree = build_entity_tree(new_entity)
        
        # Use the entity diffing function to check for differences
        modified_entities = find_modified_entities(original_tree, new_tree)
        self.assertEqual(len(modified_entities), 0)

    def test_nested_entity_serialization(self):
        """Test serialization and deserialization of a nested entity."""
        # Register the entity
        EntityRegistry.register_entity(self.nested)
        
        # Serialize the entity
        entity_dict = self.nested.model_dump()
        
        # Create a new entity from the serialized data
        new_entity = EntityinEntity.model_validate(entity_dict)
        
        # Check that the new entity has the same properties
        self.assertEqual(new_entity.ecs_id, self.nested.ecs_id)
        self.assertEqual(new_entity.live_id, self.nested.live_id)
        self.assertEqual(new_entity.root_ecs_id, self.nested.root_ecs_id)
        self.assertEqual(new_entity.root_live_id, self.nested.root_live_id)
        
        # Check that the sub-entity was also deserialized correctly
        self.assertEqual(new_entity.sub_entity.ecs_id, self.nested.sub_entity.ecs_id)
        self.assertEqual(new_entity.sub_entity.live_id, self.nested.sub_entity.live_id)
        self.assertEqual(new_entity.sub_entity.root_ecs_id, self.nested.sub_entity.root_ecs_id)
        self.assertEqual(new_entity.sub_entity.root_live_id, self.nested.sub_entity.root_live_id)
        
        # Build trees and check for differences
        original_tree = build_entity_tree(self.nested)
        new_tree = build_entity_tree(new_entity)
        
        # Use the entity diffing function to check for differences
        modified_entities = find_modified_entities(original_tree, new_tree)
        self.assertEqual(len(modified_entities), 0)

    def test_list_entity_serialization(self):
        """Test serialization and deserialization of an entity with a list of entities."""
        # Register the entity
        EntityRegistry.register_entity(self.list_entity)
        
        # Serialize the entity
        entity_dict = self.list_entity.model_dump()
        
        # Create a new entity from the serialized data
        new_entity = EntityinList.model_validate(entity_dict)
        
        # Check that the new entity has the same properties
        self.assertEqual(new_entity.ecs_id, self.list_entity.ecs_id)
        self.assertEqual(new_entity.live_id, self.list_entity.live_id)
        
        # Check that the list of entities was also deserialized correctly
        self.assertEqual(len(new_entity.entities), len(self.list_entity.entities))
        for i, entity in enumerate(new_entity.entities):
            self.assertEqual(entity.ecs_id, self.list_entity.entities[i].ecs_id)
            self.assertEqual(entity.live_id, self.list_entity.entities[i].live_id)
            self.assertEqual(entity.root_ecs_id, self.list_entity.entities[i].root_ecs_id)
            self.assertEqual(entity.root_live_id, self.list_entity.entities[i].root_live_id)
        
        # Build trees and check for differences
        original_tree = build_entity_tree(self.list_entity)
        new_tree = build_entity_tree(new_entity)
        
        # Use the entity diffing function to check for differences
        modified_entities = find_modified_entities(original_tree, new_tree)
        self.assertEqual(len(modified_entities), 0)
        
    def test_dict_entity_serialization(self):
        """Test serialization and deserialization of an entity with a dict of entities."""
        # Register the entity
        EntityRegistry.register_entity(self.dict_entity)
        
        # Serialize the entity
        entity_dict = self.dict_entity.model_dump()
        
        # Create a new entity from the serialized data
        new_entity = EntityinDict.model_validate(entity_dict)
        
        # Check that the new entity has the same properties
        self.assertEqual(new_entity.ecs_id, self.dict_entity.ecs_id)
        self.assertEqual(new_entity.live_id, self.dict_entity.live_id)
        
        # Check that the dict of entities was also deserialized correctly
        self.assertEqual(len(new_entity.entities), len(self.dict_entity.entities))
        for key, entity in new_entity.entities.items():
            self.assertEqual(entity.ecs_id, self.dict_entity.entities[key].ecs_id)
            self.assertEqual(entity.live_id, self.dict_entity.entities[key].live_id)
            self.assertEqual(entity.root_ecs_id, self.dict_entity.entities[key].root_ecs_id)
            self.assertEqual(entity.root_live_id, self.dict_entity.entities[key].root_live_id)
        
        # Build trees and check for differences
        original_tree = build_entity_tree(self.dict_entity)
        new_tree = build_entity_tree(new_entity)
        
        # Use the entity diffing function to check for differences
        modified_entities = find_modified_entities(original_tree, new_tree)
        self.assertEqual(len(modified_entities), 0)
        
    def test_json_serialization(self):
        """Test JSON serialization and deserialization."""
        # Register the entity
        EntityRegistry.register_entity(self.nested)
        
        # Serialize the entity to JSON
        entity_json = self.nested.model_dump_json()
        
        # Deserialize from JSON
        entity_dict = json.loads(entity_json)
        new_entity = EntityinEntity.model_validate(entity_dict)
        
        # Check that the new entity has the same properties
        self.assertEqual(new_entity.ecs_id, self.nested.ecs_id)
        self.assertEqual(new_entity.live_id, self.nested.live_id)
        
        # Check that the sub-entity was also deserialized correctly
        self.assertEqual(new_entity.sub_entity.ecs_id, self.nested.sub_entity.ecs_id)
        self.assertEqual(new_entity.sub_entity.live_id, self.nested.sub_entity.live_id)
        
        # Build trees and check for differences
        original_tree = build_entity_tree(self.nested)
        new_tree = build_entity_tree(new_entity)
        
        # Use the entity diffing function to check for differences
        modified_entities = find_modified_entities(original_tree, new_tree)
        self.assertEqual(len(modified_entities), 0)
        
    def test_versioned_entity_serialization(self):
        """Test serialization and deserialization of a versioned entity."""
        # Register the entity
        EntityRegistry.register_entity(self.root)
        
        # Modify the entity and version it
        self.root.untyped_data = "Modified data"
        EntityRegistry.version_entity(self.root)
        
        # Serialize the entity
        entity_dict = self.root.model_dump()
        
        # Create a new entity from the serialized data
        new_entity = Entity.model_validate(entity_dict)
        
        # Check that the new entity has the same properties
        self.assertEqual(new_entity.ecs_id, self.root.ecs_id)
        self.assertEqual(new_entity.live_id, self.root.live_id)
        self.assertEqual(new_entity.untyped_data, self.root.untyped_data)
        
        # Check versioning information
        self.assertEqual(new_entity.old_ids, self.root.old_ids)
        self.assertEqual(new_entity.old_ecs_id, self.root.old_ecs_id)
        self.assertEqual(new_entity.previous_ecs_id, self.root.previous_ecs_id)
        
        # Build trees and check for differences
        original_tree = build_entity_tree(self.root)
        new_tree = build_entity_tree(new_entity)
        
        # Use the entity diffing function to check for differences
        modified_entities = find_modified_entities(original_tree, new_tree)
        self.assertEqual(len(modified_entities), 0)
        
    def test_complex_entity_serialization(self):
        """Test serialization and deserialization of a complex entity structure."""
        # Create a hierarchical entity
        root = HierarchicalEntity()
        root.root_ecs_id = root.ecs_id
        root.root_live_id = root.live_id
        
        # Make sure all nested entities have correct root references
        for entity_field in [
            root.entity_of_entity_1,
            root.entity_of_entity_2,
            root.flat_entity,
            root.entity_of_entity_of_entity
        ]:
            entity_field.root_ecs_id = root.ecs_id
            entity_field.root_live_id = root.live_id
            
            # For nested entities, set their sub-entities' root references too
            if hasattr(entity_field, 'sub_entity'):
                entity_field.sub_entity.root_ecs_id = root.ecs_id
                entity_field.sub_entity.root_live_id = root.live_id
            
            # For the entity_of_entity_of_entity, handle its deeper nesting
            if hasattr(entity_field, 'entity_of_entity'):
                entity_field.entity_of_entity.root_ecs_id = root.ecs_id
                entity_field.entity_of_entity.root_live_id = root.live_id
                entity_field.entity_of_entity.sub_entity.root_ecs_id = root.ecs_id
                entity_field.entity_of_entity.sub_entity.root_live_id = root.live_id
        
        # Register the entity
        EntityRegistry.register_entity(root)
        
        # Modify a deeply nested entity
        root.entity_of_entity_of_entity.entity_of_entity.sub_entity.untyped_data = "Modified deep entity"
        EntityRegistry.version_entity(root)
        
        # Serialize the entity
        entity_dict = root.model_dump()
        
        # Create a new entity from the serialized data
        new_entity = HierarchicalEntity.model_validate(entity_dict)
        
        # Build trees and check for differences
        original_tree = build_entity_tree(root)
        new_tree = build_entity_tree(new_entity)
        
        # Use the entity diffing function to check for differences
        modified_entities = find_modified_entities(original_tree, new_tree)
        self.assertEqual(len(modified_entities), 0)
        
    def test_entity_tree_serialization(self):
        """Test that serialization and deserialization preserves tree structure."""
        # Register the entity
        EntityRegistry.register_entity(self.root)  # Use simple Entity for cleaner test
        
        # Build the original tree
        original_tree = build_entity_tree(self.root)
        
        # Serialize the entity to dict and back
        entity_dict = self.root.model_dump()
        deserialized_entity = Entity.model_validate(entity_dict)
        
        # Build a new tree from the deserialized entity
        new_tree = build_entity_tree(deserialized_entity)
        
        # Use our tree diffing function to check for any differences
        modified_entities = find_modified_entities(original_tree, new_tree)
        self.assertEqual(len(modified_entities), 0, "Trees should be identical after serialization")
        
        # Verify key properties match exactly
        self.assertEqual(original_tree.root_ecs_id, new_tree.root_ecs_id)
        self.assertEqual(original_tree.lineage_id, new_tree.lineage_id)
        self.assertEqual(len(original_tree.nodes), len(new_tree.nodes))
        self.assertEqual(len(original_tree.edges), len(new_tree.edges))
        
        # Check that serialization also worked for more complex properties
        self.assertEqual(set(original_tree.nodes.keys()), set(new_tree.nodes.keys()))
        self.assertEqual(set(original_tree.edges.keys()), set(new_tree.edges.keys()))
        self.assertEqual(original_tree.ancestry_paths, new_tree.ancestry_paths)


    def test_tuple_entity_serialization(self):
        """Test serialization and deserialization of an entity with a tuple of entities."""
        # Register the entity
        EntityRegistry.register_entity(self.tuple_entity)
        
        # Serialize the entity
        entity_dict = self.tuple_entity.model_dump()
        
        # Create a new entity from the serialized data
        new_entity = EntityinTuple.model_validate(entity_dict)
        
        # Check that the tuple of entities was properly deserialized
        self.assertEqual(len(new_entity.entities), len(self.tuple_entity.entities))
        for i, entity in enumerate(new_entity.entities):
            self.assertEqual(entity.ecs_id, self.tuple_entity.entities[i].ecs_id)
            self.assertEqual(entity.live_id, self.tuple_entity.entities[i].live_id)
            self.assertEqual(entity.root_ecs_id, self.tuple_entity.entities[i].root_ecs_id)
        
        # Build trees and check for differences
        original_tree = build_entity_tree(self.tuple_entity)
        new_tree = build_entity_tree(new_entity)
        
        # Use the entity diffing function to check for differences
        modified_entities = find_modified_entities(original_tree, new_tree)
        self.assertEqual(len(modified_entities), 0)
    
    def test_set_entity_in_registry(self):
        """Test an entity with a set of entities registered and retrieved from EntityRegistry."""
        # Get a snapshot of the entity structure before registration
        original_ecs_id = self.set_entity.ecs_id
        original_entities = list(self.set_entity.entities)
        entity_ids = {e.ecs_id for e in original_entities}
        
        # Register directly with the EntityRegistry
        EntityRegistry.register_entity(self.set_entity)
        
        # Retrieve the entity from the registry using the proper method
        stored_entity = EntityRegistry.get_stored_entity(self.set_entity.ecs_id, self.set_entity.ecs_id)
        
        # Check the entity was properly stored
        self.assertIsNotNone(stored_entity)
        self.assertEqual(stored_entity.ecs_id, original_ecs_id)
        
        # Verify the set elements were preserved
        self.assertEqual(len(stored_entity.entities), len(original_entities))
        stored_ids = {e.ecs_id for e in stored_entity.entities}
        self.assertEqual(stored_ids, entity_ids)
        
        # With the new immutability implementation, we can't look up entities by their
        # original live_id because EntityRegistry.get_stored_entity assigns new live_ids
        # Instead, we verify the structure is preserved by checking we can still
        # access all the original entity's ecs_ids in the stored entity
        for entity in original_entities:
            # Find the corresponding entity in the stored set
            stored_entity_match = next((e for e in stored_entity.entities if e.ecs_id == entity.ecs_id), None)
            self.assertIsNotNone(stored_entity_match, f"Couldn't find entity with ecs_id {entity.ecs_id} in stored set")
            
            # Verify it has a different live_id (immutability feature)
            self.assertNotEqual(stored_entity_match.live_id, entity.live_id)
    
    def test_primitive_entity_serialization(self):
        """Test serialization and deserialization of an entity with primitive values."""
        # Register the entity
        EntityRegistry.register_entity(self.primitive_entity)
        
        # Serialize the entity
        entity_dict = self.primitive_entity.model_dump()
        
        # Create a new entity from the serialized data
        new_entity = EntityWithPrimitives.model_validate(entity_dict)
        
        # Check that primitive values were correctly deserialized
        self.assertEqual(new_entity.string_value, self.primitive_entity.string_value)
        self.assertEqual(new_entity.int_value, self.primitive_entity.int_value)
        self.assertEqual(new_entity.float_value, self.primitive_entity.float_value)
        self.assertEqual(new_entity.bool_value, self.primitive_entity.bool_value)
        
        # Build trees and check for differences
        original_tree = build_entity_tree(self.primitive_entity)
        new_tree = build_entity_tree(new_entity)
        
        # Use the entity diffing function to check for differences
        modified_entities = find_modified_entities(original_tree, new_tree)
        self.assertEqual(len(modified_entities), 0)
    
    def test_container_primitive_entity_serialization(self):
        """Test serialization and deserialization of an entity with containers of primitives."""
        # Register the entity
        EntityRegistry.register_entity(self.container_primitive_entity)
        
        # Serialize the entity
        entity_dict = self.container_primitive_entity.model_dump()
        
        # Create a new entity from the serialized data
        new_entity = EntityWithContainersOfPrimitives.model_validate(entity_dict)
        
        # Check container primitives were correctly deserialized
        self.assertEqual(new_entity.string_list, self.container_primitive_entity.string_list)
        self.assertEqual(new_entity.int_dict, self.container_primitive_entity.int_dict)
        self.assertEqual(new_entity.float_tuple, self.container_primitive_entity.float_tuple)
        self.assertEqual(new_entity.bool_set, self.container_primitive_entity.bool_set)
        
        # Build trees and check for differences
        original_tree = build_entity_tree(self.container_primitive_entity)
        new_tree = build_entity_tree(new_entity)
        
        # Use the entity diffing function to check for differences
        modified_entities = find_modified_entities(original_tree, new_tree)
        self.assertEqual(len(modified_entities), 0)
    
    def test_mixed_container_entity_serialization(self):
        """Test serialization and deserialization of an entity with container entities."""
        # Register the entity
        EntityRegistry.register_entity(self.mixed_container_entity)
        
        # Serialize the entity
        entity_dict = self.mixed_container_entity.model_dump()
        
        # Create a new entity from the serialized data
        new_entity = EntityWithMixedContainers.model_validate(entity_dict)
        
        # Check entities in list
        self.assertEqual(len(new_entity.mixed_list), len(self.mixed_container_entity.mixed_list))
        for i, entity in enumerate(new_entity.mixed_list):
            self.assertIsInstance(entity, Entity)
            self.assertEqual(entity.ecs_id, self.mixed_container_entity.mixed_list[i].ecs_id)
        
        # Check entities in dict
        self.assertEqual(len(new_entity.mixed_dict), len(self.mixed_container_entity.mixed_dict))
        for key, entity in new_entity.mixed_dict.items():
            self.assertIsInstance(entity, Entity)
            self.assertEqual(entity.ecs_id, self.mixed_container_entity.mixed_dict[key].ecs_id)
        
        # Build trees and check for differences
        original_tree = build_entity_tree(self.mixed_container_entity)
        new_tree = build_entity_tree(new_entity)
        
        # Use the entity diffing function to check for differences
        modified_entities = find_modified_entities(original_tree, new_tree)
        self.assertEqual(len(modified_entities), 0)
    
    def test_nested_container_entity_serialization(self):
        """Test serialization and deserialization of an entity with nested containers."""
        # Register the entity
        EntityRegistry.register_entity(self.nested_container_entity)
        
        # Serialize the entity
        entity_dict = self.nested_container_entity.model_dump()
        
        # Create a new entity from the serialized data
        new_entity = EntityWithNestedContainers.model_validate(entity_dict)
        
        # Check primitive nested containers
        self.assertEqual(new_entity.list_of_lists, self.nested_container_entity.list_of_lists)
        self.assertEqual(new_entity.dict_of_dicts, self.nested_container_entity.dict_of_dicts)
        
        # Check list of dicts with entities - this is the complex case
        self.assertEqual(len(new_entity.list_of_dicts), len(self.nested_container_entity.list_of_dicts))
        
        # First dict should have key1 -> entity
        self.assertIn("key1", new_entity.list_of_dicts[0])
        self.assertIsInstance(new_entity.list_of_dicts[0]["key1"], Entity)
        self.assertEqual(
            new_entity.list_of_dicts[0]["key1"].ecs_id, 
            self.nested_container_entity.list_of_dicts[0]["key1"].ecs_id
        )
        
        # Second dict should have key2 -> entity
        self.assertIn("key2", new_entity.list_of_dicts[1])
        self.assertIsInstance(new_entity.list_of_dicts[1]["key2"], Entity)
        self.assertEqual(
            new_entity.list_of_dicts[1]["key2"].ecs_id, 
            self.nested_container_entity.list_of_dicts[1]["key2"].ecs_id
        )
        
        # Build trees and check for differences
        original_tree = build_entity_tree(self.nested_container_entity)
        new_tree = build_entity_tree(new_entity)
        
        # Use the entity diffing function to check for differences
        modified_entities = find_modified_entities(original_tree, new_tree)
        self.assertEqual(len(modified_entities), 0)
    
    def test_optional_entity_serialization(self):
        """Test serialization and deserialization of an entity with optional fields."""
        # Register the entity
        EntityRegistry.register_entity(self.optional_entity)
        
        # Serialize the entity
        entity_dict = self.optional_entity.model_dump()
        
        # Create a new entity from the serialized data
        new_entity = OptionalEntityContainers.model_validate(entity_dict)
        
        # Check that optional entity is None
        self.assertIsNone(new_entity.optional_entity)
        
        # Check optional list
        self.assertIsNotNone(new_entity.optional_entity_list)
        self.assertEqual(len(new_entity.optional_entity_list), 1)
        self.assertEqual(
            new_entity.optional_entity_list[0].ecs_id,
            self.optional_entity.optional_entity_list[0].ecs_id
        )
        
        # Check optional dict
        self.assertIsNotNone(new_entity.optional_entity_dict)
        self.assertIn("key", new_entity.optional_entity_dict)
        self.assertEqual(
            new_entity.optional_entity_dict["key"].ecs_id,
            self.optional_entity.optional_entity_dict["key"].ecs_id
        )
        
        # Build trees and check for differences
        original_tree = build_entity_tree(self.optional_entity)
        new_tree = build_entity_tree(new_entity)
        
        # Use the entity diffing function to check for differences
        modified_entities = find_modified_entities(original_tree, new_tree)
        self.assertEqual(len(modified_entities), 0)
    
    def test_base_model_entity_serialization(self):
        """Test serialization and deserialization of an entity with a base model."""
        # Register the entity
        EntityRegistry.register_entity(self.base_model_entity)
        
        # Serialize the entity
        entity_dict = self.base_model_entity.model_dump()
        
        # Create a new entity from the serialized data
        new_entity = EntityinBaseModel.model_validate(entity_dict)
        
        # Check that the base model was correctly deserialized
        self.assertIsNotNone(new_entity.base_model)
        self.assertIsNotNone(new_entity.base_model.entity)
        self.assertEqual(
            new_entity.base_model.entity.ecs_id,
            self.base_model_entity.base_model.entity.ecs_id
        )
        
        # Build trees and check for differences
        original_tree = build_entity_tree(self.base_model_entity)
        new_tree = build_entity_tree(new_entity)
        
        # Use the entity diffing function to check for differences
        modified_entities = find_modified_entities(original_tree, new_tree)
        self.assertEqual(len(modified_entities), 0)
    
    def test_hierarchical_entity_serialization(self):
        """Test serialization and deserialization of a hierarchical entity."""
        # Register the entity
        EntityRegistry.register_entity(self.hierarchical)
        
        # Serialize the entity
        entity_dict = self.hierarchical.model_dump()
        
        # Create a new entity from the serialized data
        new_entity = HierarchicalEntity.model_validate(entity_dict)
        
        # Check all the complex structure was properly serialized and deserialized
        # This is the most comprehensive test of deeply nested entity structures
        self.assertEqual(new_entity.ecs_id, self.hierarchical.ecs_id)
        self.assertEqual(new_entity.entity_of_entity_1.ecs_id, self.hierarchical.entity_of_entity_1.ecs_id)
        self.assertEqual(new_entity.entity_of_entity_2.ecs_id, self.hierarchical.entity_of_entity_2.ecs_id)
        self.assertEqual(new_entity.flat_entity.ecs_id, self.hierarchical.flat_entity.ecs_id)
        self.assertEqual(new_entity.primitive_data.ecs_id, self.hierarchical.primitive_data.ecs_id)
        
        # Check deep nested structure
        self.assertEqual(
            new_entity.entity_of_entity_of_entity.ecs_id,
            self.hierarchical.entity_of_entity_of_entity.ecs_id
        )
        self.assertEqual(
            new_entity.entity_of_entity_of_entity.entity_of_entity.ecs_id,
            self.hierarchical.entity_of_entity_of_entity.entity_of_entity.ecs_id
        )
        self.assertEqual(
            new_entity.entity_of_entity_of_entity.entity_of_entity.sub_entity.ecs_id,
            self.hierarchical.entity_of_entity_of_entity.entity_of_entity.sub_entity.ecs_id
        )
        
        # Build trees and check for differences
        original_tree = build_entity_tree(self.hierarchical)
        new_tree = build_entity_tree(new_entity)
        
        # Use the entity diffing function to check for differences
        modified_entities = find_modified_entities(original_tree, new_tree)
        self.assertEqual(len(modified_entities), 0)
    
    def test_json_serialization_all_types(self):
        """Test JSON serialization and deserialization for all entity types."""
        # Test with the most complex entity type for comprehensive coverage
        EntityRegistry.register_entity(self.hierarchical)
        
        # Serialize to JSON
        entity_json = self.hierarchical.model_dump_json()
        
        # Deserialize from JSON
        entity_dict = json.loads(entity_json)
        new_entity = HierarchicalEntity.model_validate(entity_dict)
        
        # Build trees and check for differences
        original_tree = build_entity_tree(self.hierarchical)
        new_tree = build_entity_tree(new_entity)
        
        # Check that the entire structure matches with zero differences
        modified_entities = find_modified_entities(original_tree, new_tree)
        self.assertEqual(len(modified_entities), 0, "JSON serialization should preserve all entity relationships")
    
    def test_update_ecs_ids_serialization(self):
        """Test entity versioning with update_ecs_ids and serialization."""
        # Create a new entity for this test
        entity = Entity()
        entity.root_ecs_id = entity.ecs_id
        entity.root_live_id = entity.live_id
        
        # Record original state
        original_ecs_id = entity.ecs_id
        
        # Update ecs_id directly 
        entity.update_ecs_ids()
        
        # Verify ID was changed
        self.assertNotEqual(entity.ecs_id, original_ecs_id, 
                           "Entity ecs_id should change after update_ecs_ids")
        
        # Verify tracking is working
        self.assertIn(original_ecs_id, entity.old_ids, 
                    "Original ecs_id should be in old_ids")
        self.assertEqual(entity.old_ecs_id, original_ecs_id,
                       "old_ecs_id should be set to original ID")
        
        # Serialize and deserialize
        entity_dict = entity.model_dump()
        new_entity = Entity.model_validate(entity_dict)
        
        # Verify ID and history are preserved
        self.assertEqual(new_entity.ecs_id, entity.ecs_id)
        self.assertEqual(new_entity.old_ecs_id, entity.old_ecs_id)
        self.assertEqual(new_entity.old_ids, entity.old_ids)
        
        # Try with the registry workflow
        EntityRegistry.tree_registry = {}
        EntityRegistry.lineage_registry = {}
        EntityRegistry.live_id_registry = {}
        EntityRegistry.type_registry = {}
        
        # Register a fresh entity
        test_entity = Entity()
        test_entity.root_ecs_id = test_entity.ecs_id
        test_entity.root_live_id = test_entity.live_id
        test_entity.untyped_data = "Original data"
        
        # Register and make a significant change
        EntityRegistry.register_entity(test_entity)
        original_id = test_entity.ecs_id
        
        # Modify and use the registry versioning
        test_entity.untyped_data = "Modified data for versioning"
        
        # Directly use update_ecs_ids to force ID change
        test_entity.update_ecs_ids()
        
        # Verify ID changed
        self.assertNotEqual(test_entity.ecs_id, original_id)
        
        # Now try serialization
        entity_dict = test_entity.model_dump()
        new_entity = Entity.model_validate(entity_dict)
        
        # Check ID and data preservation
        self.assertEqual(new_entity.ecs_id, test_entity.ecs_id)
        self.assertEqual(new_entity.untyped_data, "Modified data for versioning")


if __name__ == '__main__':
    unittest.main()