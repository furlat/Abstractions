import unittest
from uuid import UUID, uuid4
from typing import Dict, List, Optional, Union, Self

from abstractions.ecs.entity import (
    Entity, 
    EntityinEntity,
    EntityinList,
    EntityinDict,
    EntityWithPrimitives
)

def update_attribute_source(entity: Entity) -> Entity:
    """
    Helper method to update attribute_source when fields are modified.
    Called manually after modifying container fields.
    
    Args:
        entity: The entity to update attribute_source for
        
    Returns:
        The same entity for method chaining
    """
    if hasattr(entity, 'attribute_source') and entity.attribute_source is not None:
        # Get all valid field names for this model
        valid_fields = set(entity.model_fields.keys())
        valid_fields.discard('attribute_source')
        
        # Initialize missing fields and update container sizes
        for field_name in valid_fields:
            field_value = getattr(entity, field_name)
            
            # Handle container types that need structure updates
            if isinstance(field_value, list):
                # Check if we need to create or resize the list
                current_value = entity.attribute_source.get(field_name)
                if (current_value is None or 
                    not isinstance(current_value, list) or
                    len(current_value) != len(field_value)):
                    # Initialize with a list of properly typed None values
                    none_value: Optional[UUID] = None
                    entity.attribute_source[field_name] = [none_value] * len(field_value)
            
            elif isinstance(field_value, dict):
                # Check if we need to create or update the dict
                current_value = entity.attribute_source.get(field_name)
                if current_value is None or not isinstance(current_value, dict):
                    # Create new dict with None values for each key
                    entity.attribute_source[field_name] = {k: None for k in field_value.keys()}
                else:
                    # Make sure all keys are present
                    source_dict = entity.attribute_source[field_name]
                    if isinstance(source_dict, dict):  # Type guard for mypy/pylance
                        for key in field_value.keys():
                            if key not in source_dict:
                                source_dict[key] = None
            
            elif field_name not in entity.attribute_source:
                # Regular field gets simple None value if missing
                entity.attribute_source[field_name] = None
                
    return entity


class TestAttributeSource(unittest.TestCase):
    """Test the attribute_source feature of the Entity class."""

    def test_attribute_source_initialization(self):
        """Test that attribute_source is properly initialized for all fields."""
        entity = Entity()
        
        # Check that attribute_source is initialized
        self.assertIsNotNone(entity.attribute_source)
        self.assertIsInstance(entity.attribute_source, dict)
        
        # Check that all fields except attribute_source itself have an entry
        for field_name in entity.model_fields.keys():
            if field_name != 'attribute_source':
                self.assertIn(field_name, entity.attribute_source)
                
                # Container fields might be empty lists or dicts
                field_value = getattr(entity, field_name)
                if isinstance(field_value, list) or isinstance(field_value, dict):
                    continue
                    
                # Check that the source is None for newly created entity (for non-container fields)
                self.assertIsNone(entity.attribute_source[field_name])
    
    def test_list_attribute_source(self):
        """Test attribute_source for a list field."""
        # Create an entity with a list of sub-entities
        sub1 = Entity()
        sub2 = Entity()
        # Create with pre-populated list
        entity = EntityinList(entities=[sub1, sub2])
        
        # Use the standalone function to update attribute_source
        entity = update_attribute_source(entity)
        
        # Validate that list sources are initialized
        self.assertIn('entities', entity.attribute_source)
        self.assertIsInstance(entity.attribute_source['entities'], list)
        self.assertEqual(len(entity.attribute_source['entities']), 2)
        
        # All sources should be None initially
        for source in entity.attribute_source['entities']:
            self.assertIsNone(source)
        
        # Assign a source entity ID to the first item
        source_id = uuid4()
        entity.attribute_source['entities'][0] = source_id
        
        # Validate that only the intended source was updated
        self.assertEqual(entity.attribute_source['entities'][0], source_id)
        self.assertIsNone(entity.attribute_source['entities'][1])
    
    def test_dict_attribute_source(self):
        """Test attribute_source for a dictionary field."""
        # Create an entity with a dict of sub-entities
        sub1 = Entity()
        sub2 = Entity()
        # Create with pre-populated dict
        entity = EntityinDict(entities={'first': sub1, 'second': sub2})
        
        # Use the standalone function to update attribute_source
        entity = update_attribute_source(entity)
        
        # Validate that dict sources are initialized
        self.assertIn('entities', entity.attribute_source)
        self.assertIsInstance(entity.attribute_source['entities'], dict)
        self.assertEqual(len(entity.attribute_source['entities']), 2)
        
        # All sources should be None initially
        for key, source in entity.attribute_source['entities'].items():
            self.assertIsNone(source)
        
        # Assign a source entity ID to the first item
        source_id = uuid4()
        entity.attribute_source['entities']['first'] = source_id
        
        # Validate that only the intended source was updated
        self.assertEqual(entity.attribute_source['entities']['first'], source_id)
        self.assertIsNone(entity.attribute_source['entities']['second'])
    
    def test_nested_entity_attribute_source(self):
        """Test attribute_source for nested entities."""
        # Create a nested entity structure
        child = Entity()
        parent = EntityinEntity(sub_entity=child)
        
        # Use the standalone function to update attribute_source
        parent = update_attribute_source(parent)
        
        # The sub_entity field should have a None source initially
        self.assertIn('sub_entity', parent.attribute_source)
        self.assertIsNone(parent.attribute_source['sub_entity'])
        
        # Assign a source entity ID
        source_id = uuid4()
        parent.attribute_source['sub_entity'] = source_id
        self.assertEqual(parent.attribute_source['sub_entity'], source_id)
    
    def test_primitive_field_attribute_source(self):
        """Test attribute_source for primitive fields."""
        entity = EntityWithPrimitives()
        entity = update_attribute_source(entity)
        
        # All primitive fields should have entries
        fields = ['string_value', 'int_value', 'float_value', 'bool_value', 
                 'datetime_value', 'uuid_value']
        
        for field in fields:
            self.assertIn(field, entity.attribute_source)
            self.assertIsNone(entity.attribute_source[field])
        
        # Assign source IDs to some fields
        source_id1 = uuid4()
        source_id2 = uuid4()
        entity.attribute_source['string_value'] = source_id1
        entity.attribute_source['int_value'] = source_id2
        
        # Validate correct assignments
        self.assertEqual(entity.attribute_source['string_value'], source_id1)
        self.assertEqual(entity.attribute_source['int_value'], source_id2)
        self.assertIsNone(entity.attribute_source['float_value'])
    
    def test_dynamic_structure_updates(self):
        """Test that attribute_source structure updates when field values change."""
        # Start with an empty list
        entity = EntityinList()
        entity = update_attribute_source(entity)
        self.assertEqual(len(entity.attribute_source['entities']), 0)
        
        # Add entities to the list
        entity.entities = [Entity(), Entity(), Entity()]
        
        # Update attribute_source
        entity = update_attribute_source(entity)
        
        # Structure should have updated
        self.assertEqual(len(entity.attribute_source['entities']), 3)
        
        # Similarly for dict
        entity_dict = EntityinDict()
        entity_dict = update_attribute_source(entity_dict)
        self.assertEqual(len(entity_dict.attribute_source['entities']), 0)
        
        # Add entities to the dict
        entity_dict.entities = {'a': Entity(), 'b': Entity(), 'c': Entity()}
        
        # Update attribute_source
        entity_dict = update_attribute_source(entity_dict)
        
        # Structure should have updated
        self.assertEqual(len(entity_dict.attribute_source['entities']), 3)
        self.assertIn('a', entity_dict.attribute_source['entities'])
        self.assertIn('b', entity_dict.attribute_source['entities'])
        self.assertIn('c', entity_dict.attribute_source['entities'])
    
    def test_invalid_attribute_source_keys(self):
        """Test that validation catches invalid keys in attribute_source."""
        entity = Entity()
        
        # Add an invalid key
        entity.attribute_source['not_a_field'] = uuid4()
        
        # Call the original validator which should fail
        with self.assertRaises(ValueError):
            entity.validate_attribute_source()
            
        # Our update function should not raise errors but silently continue
        # This is a different behavior than the original validator
        try:
            update_attribute_source(entity)
        except Exception as e:
            self.fail(f"update_attribute_source raised exception {e} when it should not")
    
    def test_container_size_mismatch(self):
        """Test that validation fixes container size mismatches."""
        # Create entity with list of sub-entities
        entity = EntityinList(entities=[Entity(), Entity(), Entity()])
        
        # Manually set an incorrect size for the attribute_source list
        entity.attribute_source['entities'] = [None]  # Too short
        
        # Update - should fix the mismatch
        entity = update_attribute_source(entity)
        
        # Check if fixed
        self.assertEqual(len(entity.attribute_source['entities']), 3)
        
        # Try a dict with missing keys
        entity_dict = EntityinDict(entities={'a': Entity(), 'b': Entity(), 'c': Entity()})
        entity_dict.attribute_source['entities'] = {'a': None}  # Missing keys
        
        # Update - should fix the mismatch
        entity_dict = update_attribute_source(entity_dict)
        
        # Check if fixed
        self.assertEqual(len(entity_dict.attribute_source['entities']), 3)
        self.assertIn('b', entity_dict.attribute_source['entities'])
        self.assertIn('c', entity_dict.attribute_source['entities'])
    
    def test_container_type_mismatch(self):
        """Test that validation fixes container type mismatches."""
        # Create entity with list but set attribute_source to wrong type
        entity = EntityinList(entities=[Entity(), Entity()])
        entity.attribute_source['entities'] = None  # Wrong type
        
        # Update - should fix the type mismatch
        entity = update_attribute_source(entity)
        
        # Check if fixed
        self.assertIsInstance(entity.attribute_source['entities'], list)
        self.assertEqual(len(entity.attribute_source['entities']), 2)
        
        # Create entity with dict but set attribute_source to wrong type
        entity_dict = EntityinDict(entities={'a': Entity(), 'b': Entity()})
        entity_dict.attribute_source['entities'] = "not a dict"  # Wrong type
        
        # Update - should fix the type mismatch
        entity_dict = update_attribute_source(entity_dict)
        
        # Check if fixed
        self.assertIsInstance(entity_dict.attribute_source['entities'], dict)
        self.assertEqual(len(entity_dict.attribute_source['entities']), 2)


if __name__ == '__main__':
    unittest.main()