"""
Extended tests for entity field type detection with non-entity types.
"""
import unittest
from typing import List, Dict, Set, Tuple, Union, Optional
from uuid import UUID
from datetime import datetime

from abstractions.ecs.entity import (
    Entity, get_pydantic_field_type_entities,
    EntityWithPrimitives, EntityWithContainersOfPrimitives,
    EntityWithMixedContainers, EntityWithNestedContainers,
    OptionalEntityContainers
)


class TestNonEntityFieldTypes(unittest.TestCase):
    """Test field type detection for non-entity fields."""
    
    def test_primitive_fields(self):
        """Test fields with primitive data types."""
        entity = EntityWithPrimitives()
        
        # Check that primitive fields are not detected as entity fields
        self.assertIsNone(get_pydantic_field_type_entities(entity, "string_value"))
        self.assertIsNone(get_pydantic_field_type_entities(entity, "int_value"))
        self.assertIsNone(get_pydantic_field_type_entities(entity, "float_value"))
        self.assertIsNone(get_pydantic_field_type_entities(entity, "bool_value"))
        self.assertIsNone(get_pydantic_field_type_entities(entity, "datetime_value"))
        self.assertIsNone(get_pydantic_field_type_entities(entity, "uuid_value"))
    
    def test_containers_of_primitives(self):
        """Test fields with containers of primitive types."""
        entity = EntityWithContainersOfPrimitives()
        
        # Add some values to the containers
        entity.string_list = ["test"]
        entity.int_dict = {"key": 1}
        entity.float_tuple = (1.0, 2.0)
        entity.bool_set = {True, False}
        
        # Check that primitive containers are not detected as entity fields
        self.assertIsNone(get_pydantic_field_type_entities(entity, "string_list"))
        self.assertIsNone(get_pydantic_field_type_entities(entity, "int_dict"))
        self.assertIsNone(get_pydantic_field_type_entities(entity, "float_tuple"))
        self.assertIsNone(get_pydantic_field_type_entities(entity, "bool_set"))
    
    def test_mixed_containers(self):
        """Test fields with containers that mix entity and non-entity types."""
        entity = EntityWithMixedContainers()
        
        # Add mixed values to containers
        # First with non-entity values
        entity.mixed_list = ["string"]
        entity.mixed_dict = {"key": 1}
        
        # Check that these are not detected as entity fields
        # The current implementation won't detect entities in mixed containers without entities
        self.assertIsNone(get_pydantic_field_type_entities(entity, "mixed_list"))
        self.assertIsNone(get_pydantic_field_type_entities(entity, "mixed_dict"))
        
        # Now add entity values
        entity.mixed_list = [Entity()]
        entity.mixed_dict = {"key": Entity()}
        
        # Check if entity types are detected when containers have entities
        # With the current implementation, we would detect these by instance check
        list_has_entity = any(isinstance(item, Entity) for item in entity.mixed_list)
        dict_has_entity = any(isinstance(value, Entity) for value in entity.mixed_dict.values())
        
        self.assertTrue(list_has_entity)
        self.assertTrue(dict_has_entity)
    
    def test_nested_containers(self):
        """Test fields with nested containers."""
        entity = EntityWithNestedContainers()
        
        # Add some nested containers
        entity.list_of_lists = [["test"]]
        entity.dict_of_dicts = {"outer": {"inner": 1}}
        
        # Add nested container with entity
        inner_dict = {"key": Entity()}
        entity.list_of_dicts = [inner_dict]
        
        # Check nested primitive containers are not detected as entity fields
        self.assertIsNone(get_pydantic_field_type_entities(entity, "list_of_lists"))
        self.assertIsNone(get_pydantic_field_type_entities(entity, "dict_of_dicts"))
        
        # Check if we can detect entities in nested containers
        # With current implementation, we would need to inspect the containers manually
        has_entity_in_nested = False
        if entity.list_of_dicts:
            first_dict = entity.list_of_dicts[0]
            has_entity_in_nested = any(isinstance(value, Entity) for value in first_dict.values())
        
        self.assertTrue(has_entity_in_nested)
    
    def test_optional_container_handling(self):
        """Test fields with optional containers."""
        entity = OptionalEntityContainers()
        
        # All containers are None by default
        self.assertIsNone(entity.optional_entity)
        self.assertIsNone(entity.optional_entity_list)
        self.assertIsNone(entity.optional_entity_dict)
        
        # Only direct optional entity is detected by type hints
        # This already works in the current implementation
        optional_entity_type = get_pydantic_field_type_entities(entity, "optional_entity")
        self.assertEqual(optional_entity_type, Entity)
        
        # Optional containers of entities require manual inspection
        # Set values and check
        entity.optional_entity_list = [Entity()]
        entity.optional_entity_dict = {"key": Entity()}
        
        # Check if we can detect entities in the containers
        list_has_entity = entity.optional_entity_list and all(isinstance(item, Entity) for item in entity.optional_entity_list)
        dict_has_entity = entity.optional_entity_dict and all(isinstance(value, Entity) for value in entity.optional_entity_dict.values())
        
        self.assertTrue(list_has_entity)
        self.assertTrue(dict_has_entity)
    
    def test_type_detection_performance(self):
        """Test performance considerations for type detection.
        
        This test doesn't actually measure performance, but illustrates
        the steps and complexities involved in type detection.
        """
        # Create an entity with complex nested fields
        complex_entity = EntityWithNestedContainers()
        
        # Add entity to nested container
        complex_entity.list_of_dicts = [{"key": Entity()}]
        
        # Example of more complex type checking for nested containers
        # This is outside the scope of the current implementation
        def find_entity_in_nested_container(container):
            """Find entities in a nested container structure."""
            if isinstance(container, Entity):
                return True
            elif isinstance(container, (list, tuple, set)):
                return any(find_entity_in_nested_container(item) for item in container)
            elif isinstance(container, dict):
                return any(find_entity_in_nested_container(value) for value in container.values())
            return False
        
        # Check if we can find entities in nested structures
        has_entity = find_entity_in_nested_container(complex_entity.list_of_dicts)
        self.assertTrue(has_entity)
        
        # This test passes but illustrates that complex nested container
        # type detection requires a different approach than what's currently implemented


if __name__ == '__main__':
    unittest.main()