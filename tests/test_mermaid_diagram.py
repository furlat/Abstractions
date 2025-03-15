"""
Tests for the Mermaid diagram generation functionality.
"""
import unittest
import re
from uuid import UUID

from abstractions.ecs.entity import (
    Entity, 
    EntityTree, 
    build_entity_tree, 
    generate_mermaid_diagram,
    EntityinEntity,
    EntityinList
)

# No need to import ownership-related classes


class TestMermaidDiagram(unittest.TestCase):
    """Test the Mermaid diagram generation functionality."""

    def setUp(self):
        """Set up test data."""
        # Simple entity
        self.simple_entity = Entity()
        self.simple_entity.root_ecs_id = self.simple_entity.ecs_id
        self.simple_entity.root_live_id = self.simple_entity.live_id
        
        # Nested entity
        self.nested_entity = EntityinEntity()
        self.nested_entity.root_ecs_id = self.nested_entity.ecs_id
        self.nested_entity.root_live_id = self.nested_entity.live_id
        
        # List entity
        self.list_entity = EntityinList()
        self.list_entity.root_ecs_id = self.list_entity.ecs_id
        self.list_entity.root_live_id = self.list_entity.live_id
        self.list_entity.entities.append(Entity())
        self.list_entity.entities.append(Entity())

    def test_empty_tree(self):
        """Test generating a diagram for an empty tree."""
        empty_tree = EntityTree(
            root_ecs_id=UUID('00000000-0000-0000-0000-000000000000'),
            lineage_id=UUID('00000000-0000-0000-0000-000000000000')
        )
        
        diagram = generate_mermaid_diagram(empty_tree)
        
        self.assertIn("```mermaid", diagram)
        self.assertIn("Empty Tree", diagram)
        self.assertIn("```", diagram)

    def test_simple_entity_diagram(self):
        """Test generating a diagram for a simple entity."""
        tree = build_entity_tree(self.simple_entity)
        
        diagram = generate_mermaid_diagram(tree)
        
        # Basic structure checks
        self.assertIn("```mermaid", diagram)
        self.assertIn("tree TD", diagram)
        self.assertIn(str(self.simple_entity.ecs_id), diagram)
        self.assertIn("Entity", diagram)
        self.assertIn("rootNode", diagram)
        self.assertIn("```", diagram)
        
        # Should contain the node definition
        node_pattern = rf"  {self.simple_entity.ecs_id}\[\"Entity {str(self.simple_entity.ecs_id)[-8:]}\"\]"
        self.assertRegex(diagram, node_pattern)
        
        # Only one node, no edges
        self.assertEqual(1, tree.node_count)
        self.assertEqual(0, tree.edge_count)

    def test_nested_entity_diagram(self):
        """Test generating a diagram for a nested entity."""
        tree = build_entity_tree(self.nested_entity)
        
        diagram = generate_mermaid_diagram(tree)
        
        # Should have two nodes
        self.assertEqual(2, tree.node_count)
        
        # Should have one edge
        self.assertEqual(1, tree.edge_count)
        
        # Should have hierarchical edge
        self.assertIn("hierarchicalEdge", diagram)
        
        # Should have field name in edge
        self.assertIn("|sub_entity|", diagram)

    def test_list_entity_diagram(self):
        """Test generating a diagram for an entity with a list."""
        tree = build_entity_tree(self.list_entity)
        
        diagram = generate_mermaid_diagram(tree)
        
        # Should have three nodes
        self.assertEqual(3, tree.node_count)
        
        # Should have two edges
        self.assertEqual(2, tree.edge_count)
        
        # Should have indexed list items
        self.assertIn("|entities[0]|", diagram)
        self.assertIn("|entities[1]|", diagram)

    def test_include_attributes(self):
        """Test generating a diagram with entity attributes."""
        tree = build_entity_tree(self.nested_entity)
        
        diagram = generate_mermaid_diagram(tree, include_attributes=True)
        
        # Should include ecs_id
        self.assertIn("ecs_id:", diagram)
        
        # Should include lineage_id
        self.assertIn("lineage_id:", diagram)
        
        # Should include root
        self.assertIn("root:", diagram)

    # Test removed since we're no longer differentiating between ownership relationships


if __name__ == '__main__':
    unittest.main()