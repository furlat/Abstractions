"""
Tests for the ownership field metadata functionality.
"""
import unittest
from typing import Optional, List, Dict, Set, Tuple, Union
from uuid import UUID

from pydantic import BaseModel, Field

from abstractions.ecs.entity import (
    Entity, 
    EntityGraph, 
    build_entity_graph, 
    EdgeType,
    get_pydantic_field_type_entities
)


class ReferenceEntity(Entity):
    """An entity that is referenced by others but not owned."""
    name: str = "Reference"


class OwnerEntity(Entity):
    """An entity that owns other entities."""
    # Owned entity (hierarchical relationship)
    owned_entity: Entity = Field(
        default_factory=Entity,
        description="Entity owned by this entity",
        ownership=True
    )
    
    # Referenced entity (non-hierarchical relationship)
    referenced_entity: Entity = Field(
        default_factory=ReferenceEntity,
        description="Entity referenced but not owned by this entity",
        ownership=False
    )


class ContainerOwnerEntity(Entity):
    """An entity that owns entities in containers."""
    # Owned entities in a list
    owned_list: List[Entity] = Field(
        default_factory=list,
        description="List of owned entities",
        ownership=True
    )
    
    # Referenced entities in a dict
    referenced_dict: Dict[str, Entity] = Field(
        default_factory=dict,
        description="Dictionary of referenced entities",
        ownership=False
    )


class NestedOwnerEntity(Entity):
    """An entity with nested ownership relationships."""
    # A container where some elements are owned and others are referenced
    container: ContainerOwnerEntity = Field(
        default_factory=ContainerOwnerEntity,
        description="Container with mixed ownership",
        ownership=True
    )
    
    # An entity that owns other entities
    owner: OwnerEntity = Field(
        default_factory=OwnerEntity,
        description="Entity that owns other entities",
        ownership=True
    )


class TestOwnershipFieldMetadata(unittest.TestCase):
    """Test the ownership field metadata functionality."""

    def test_field_ownership_metadata(self):
        """Test that the ownership metadata is stored in the field."""
        owner = OwnerEntity()
        
        # Check owned entity field
        self.assertTrue(owner.model_fields["owned_entity"].json_schema_extra["ownership"])
        
        # Check referenced entity field
        self.assertFalse(owner.model_fields["referenced_entity"].json_schema_extra["ownership"])

    def test_get_field_ownership(self):
        """Test the function to get field ownership information."""
        owner = OwnerEntity()
        
        # Check owned entity field
        owned_field_ownership = owner.model_fields["owned_entity"].json_schema_extra.get("ownership", True)
        self.assertTrue(owned_field_ownership)
        
        # Check referenced entity field
        referenced_field_ownership = owner.model_fields["referenced_entity"].json_schema_extra.get("ownership", True)
        self.assertFalse(referenced_field_ownership)

    def test_graph_edge_classification(self):
        """Test that edges are correctly classified based on ownership."""
        # Create a hierarchy with mixed ownership
        nested = NestedOwnerEntity()
        
        # Add some entities to containers
        container = nested.container
        container.owned_list.append(Entity())
        container.referenced_dict["ref1"] = Entity()
        
        # Build the graph
        graph = build_entity_graph(nested)
        
        # Check edge from NestedOwnerEntity to ContainerOwnerEntity (owned -> hierarchical)
        container_edge = graph.get_edges(nested.ecs_id, container.ecs_id)
        self.assertTrue(container_edge.is_hierarchical)
        self.assertEqual(container_edge.edge_type, EdgeType.DIRECT)
        
        # Check edge from NestedOwnerEntity to OwnerEntity (owned -> hierarchical)
        owner_edge = graph.get_edges(nested.ecs_id, nested.owner.ecs_id)
        self.assertTrue(owner_edge.is_hierarchical)
        self.assertEqual(owner_edge.edge_type, EdgeType.DIRECT)
        
        # Check edge from OwnerEntity to owned_entity (owned -> hierarchical)
        owned_edge = graph.get_edges(nested.owner.ecs_id, nested.owner.owned_entity.ecs_id)
        self.assertTrue(owned_edge.is_hierarchical)
        self.assertEqual(owned_edge.edge_type, EdgeType.DIRECT)
        
        # Check edge from OwnerEntity to referenced_entity (referenced -> reference)
        ref_edge = graph.get_edges(nested.owner.ecs_id, nested.owner.referenced_entity.ecs_id)
        self.assertFalse(ref_edge.is_hierarchical)
        self.assertEqual(ref_edge.edge_type, EdgeType.DIRECT)
        
        # Check edge from ContainerOwnerEntity to list item (owned -> hierarchical)
        list_item = container.owned_list[0]
        list_edge = graph.get_edges(container.ecs_id, list_item.ecs_id)
        self.assertTrue(list_edge.is_hierarchical)
        self.assertEqual(list_edge.edge_type, EdgeType.LIST)
        
        # Check edge from ContainerOwnerEntity to dict item (referenced -> reference)
        dict_item = container.referenced_dict["ref1"]
        dict_edge = graph.get_edges(container.ecs_id, dict_item.ecs_id)
        self.assertFalse(dict_edge.is_hierarchical)
        self.assertEqual(dict_edge.edge_type, EdgeType.DICT)


if __name__ == '__main__':
    unittest.main()