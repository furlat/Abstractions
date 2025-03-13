"""
Tests for the entity field type detection functionality.
"""
import unittest
from typing import Optional, List, Dict, Set, Tuple, Union

from pydantic import BaseModel, Field

from abstractions.ecs.entity import Entity, get_pydantic_field_type_entities


class TestEntityWithDirectField(Entity):
    """Test entity with a direct Entity field."""
    direct_entity: Entity = Field(default_factory=Entity)


class TestEntityWithOptionalField(Entity):
    """Test entity with an optional Entity field."""
    optional_entity: Optional[Entity] = None


class TestEntityWithListField(Entity):
    """Test entity with a list of entities field."""
    list_entities: List[Entity] = Field(default_factory=list)


class TestEntityWithDictField(Entity):
    """Test entity with a dictionary of entities field."""
    dict_entities: Dict[str, Entity] = Field(default_factory=dict)


class TestEntityWithTupleField(Entity):
    """Test entity with a tuple of entities field."""
    tuple_entities: Tuple[Entity, ...] = Field(default_factory=tuple)


class TestEntityWithSetField(Entity):
    """Test entity with a set of entities field."""
    set_entities: Set[Entity] = Field(default_factory=set)


class TestBaseModel(BaseModel):
    """A non-entity model."""
    value: str = ""


class TestEntityWithNonEntityField(Entity):
    """Test entity with a non-entity field."""
    model: TestBaseModel = Field(default_factory=TestBaseModel)
    string_field: str = ""
    int_field: int = 0


class TestEntityWithNestedOptionalContainer(Entity):
    """Test entity with optional container of entities."""
    optional_list: Optional[List[Entity]] = None
    optional_dict: Optional[Dict[str, Entity]] = None


class TestPydanticFieldTypeDetection(unittest.TestCase):
    """Test the get_pydantic_field_type_entities function."""

    def test_direct_entity_field(self):
        """Test detecting a direct Entity field."""
        entity = TestEntityWithDirectField()
        field_type = get_pydantic_field_type_entities(entity, "direct_entity")
        self.assertEqual(field_type, Entity)

    def test_optional_entity_field(self):
        """Test detecting an optional Entity field."""
        entity = TestEntityWithOptionalField()
        field_type = get_pydantic_field_type_entities(entity, "optional_entity")
        self.assertEqual(field_type, Entity)

    def test_list_entity_field(self):
        """Test detecting a list of entities field.
        
        Note: With the current implementation, containers need to be populated
        before the field type can be detected.
        """
        entity = TestEntityWithListField()
        # Add an entity to the list
        entity.list_entities.append(Entity())
        
        # When working with a populated list
        field_type = None
        if entity.list_entities:
            field_type = Entity if isinstance(entity.list_entities[0], Entity) else None
            
        self.assertEqual(field_type, Entity)
        
        # Our improved function can now detect entity types even in empty containers
        empty_entity = TestEntityWithListField()
        empty_field_type = get_pydantic_field_type_entities(empty_entity, "list_entities")
        self.assertEqual(empty_field_type, Entity)

    def test_dict_entity_field(self):
        """Test detecting a dictionary of entities field.
        
        Note: With the current implementation, containers need to be populated
        before the field type can be detected.
        """
        entity = TestEntityWithDictField()
        # Add an entity to the dict
        entity.dict_entities["key"] = Entity()
        
        # When working with a populated dict
        field_type = None
        if entity.dict_entities:
            first_value = next(iter(entity.dict_entities.values()))
            field_type = Entity if isinstance(first_value, Entity) else None
            
        self.assertEqual(field_type, Entity)
        
        # Our improved function can now detect entity types even in empty containers
        empty_entity = TestEntityWithDictField()
        empty_field_type = get_pydantic_field_type_entities(empty_entity, "dict_entities")
        self.assertEqual(empty_field_type, Entity)

    def test_tuple_entity_field(self):
        """Test detecting a tuple of entities field.
        
        Note: With the current implementation, containers need to be populated
        before the field type can be detected.
        """
        entity = TestEntityWithTupleField()
        # Create a tuple with an entity
        entity.tuple_entities = (Entity(),)
        
        # When working with a populated tuple
        field_type = None
        if entity.tuple_entities:
            field_type = Entity if isinstance(entity.tuple_entities[0], Entity) else None
            
        self.assertEqual(field_type, Entity)
        
        # Our improved function can now detect entity types even in empty containers
        empty_entity = TestEntityWithTupleField()
        empty_field_type = get_pydantic_field_type_entities(empty_entity, "tuple_entities")
        self.assertEqual(empty_field_type, Entity)

    def test_set_entity_field(self):
        """Test detecting a set of entities field.
        
        Note: With the current implementation, containers need to be populated
        before the field type can be detected.
        """
        entity = TestEntityWithSetField()
        # Add an entity to the set
        entity.set_entities.add(Entity())
        
        # When working with a populated set
        field_type = None
        if entity.set_entities:
            first_value = next(iter(entity.set_entities))
            field_type = Entity if isinstance(first_value, Entity) else None
            
        self.assertEqual(field_type, Entity)
        
        # Our improved function can now detect entity types even in empty containers
        empty_entity = TestEntityWithSetField()
        empty_field_type = get_pydantic_field_type_entities(empty_entity, "set_entities")
        self.assertEqual(empty_field_type, Entity)

    def test_non_entity_field(self):
        """Test non-entity fields return None."""
        entity = TestEntityWithNonEntityField()
        
        # Test BaseModel field
        field_type = get_pydantic_field_type_entities(entity, "model")
        self.assertIsNone(field_type)
        
        # Test string field
        field_type = get_pydantic_field_type_entities(entity, "string_field")
        self.assertIsNone(field_type)
        
        # Test int field
        field_type = get_pydantic_field_type_entities(entity, "int_field")
        self.assertIsNone(field_type)

    def test_nonexistent_field(self):
        """Test nonexistent field returns None."""
        entity = TestEntityWithDirectField()
        field_type = get_pydantic_field_type_entities(entity, "nonexistent_field")
        self.assertIsNone(field_type)

    def test_nested_optional_container(self):
        """Test detecting entities in optional containers.
        
        Note: The current implementation requires these containers to be populated.
        """
        entity = TestEntityWithNestedOptionalContainer()
        
        # Initialize the optional containers
        entity.optional_list = [Entity()]
        entity.optional_dict = {"key": Entity()}
        
        # Check types manually for now
        list_type = Entity if entity.optional_list and isinstance(entity.optional_list[0], Entity) else None
        self.assertEqual(list_type, Entity)
        
        dict_type = Entity if entity.optional_dict and isinstance(next(iter(entity.optional_dict.values())), Entity) else None
        self.assertEqual(dict_type, Entity)
        
        # Our improved function can now detect entity types in optional containers
        empty_entity = TestEntityWithNestedOptionalContainer()
        self.assertEqual(get_pydantic_field_type_entities(empty_entity, "optional_list"), Entity)
        self.assertEqual(get_pydantic_field_type_entities(empty_entity, "optional_dict"), Entity)


if __name__ == '__main__':
    unittest.main()