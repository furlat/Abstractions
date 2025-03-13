"""
Tests for the basic building blocks of the entity graph system.
Tests EntityEdge and basic EntityGraph functionality.
"""
import unittest
from uuid import UUID, uuid4

from abstractions.ecs.entity import EntityEdge, EdgeType, EntityGraph, Entity


class TestEntityEdge(unittest.TestCase):
    """Test the EntityEdge class."""

    def test_entity_edge_creation(self):
        """Test creating an EntityEdge with required and optional attributes."""
        # Create source and target UUIDs
        source_id = uuid4()
        target_id = uuid4()
        
        # Create a basic edge
        edge = EntityEdge(
            source_id=source_id,
            target_id=target_id,
            edge_type=EdgeType.DIRECT,
            field_name="test_field"
        )
        
        # Check required attributes
        self.assertEqual(edge.source_id, source_id)
        self.assertEqual(edge.target_id, target_id)
        self.assertEqual(edge.edge_type, EdgeType.DIRECT)
        self.assertEqual(edge.field_name, "test_field")
        
        # Optional attributes should be None
        self.assertIsNone(edge.container_index)
        self.assertIsNone(edge.container_key)
        
        # Create edge with container index
        list_edge = EntityEdge(
            source_id=source_id,
            target_id=target_id,
            edge_type=EdgeType.LIST,
            field_name="items",
            container_index=5
        )
        self.assertEqual(list_edge.container_index, 5)
        self.assertIsNone(list_edge.container_key)
        
        # Create edge with container key
        dict_edge = EntityEdge(
            source_id=source_id,
            target_id=target_id,
            edge_type=EdgeType.DICT,
            field_name="entries",
            container_key="test_key"
        )
        self.assertEqual(dict_edge.container_key, "test_key")
        self.assertIsNone(dict_edge.container_index)

    def test_entity_edge_hash(self):
        """Test that EntityEdge objects can be hashed."""
        source_id = uuid4()
        target_id = uuid4()
        
        # Create edges
        edge1 = EntityEdge(
            source_id=source_id,
            target_id=target_id,
            edge_type=EdgeType.DIRECT,
            field_name="test_field"
        )
        
        # Create identical edge
        edge2 = EntityEdge(
            source_id=source_id,
            target_id=target_id,
            edge_type=EdgeType.DIRECT,
            field_name="test_field"
        )
        
        # Create edge with different field name
        edge3 = EntityEdge(
            source_id=source_id,
            target_id=target_id,
            edge_type=EdgeType.DIRECT,
            field_name="different_field"
        )
        
        # Test hashing
        self.assertEqual(hash(edge1), hash(edge2))
        self.assertNotEqual(hash(edge1), hash(edge3))
        
        # Test in set
        edge_set = {edge1, edge2, edge3}
        # edge1 and edge2 should be considered the same by hash
        self.assertEqual(len(edge_set), 2)
        self.assertIn(edge1, edge_set)
        self.assertIn(edge3, edge_set)


class TestEntityGraphBasics(unittest.TestCase):
    """Test the basic EntityGraph functionality."""

    def setUp(self):
        """Set up test data."""
        self.root_ecs_id = uuid4()
        self.lineage_id = uuid4()
        self.graph = EntityGraph(root_ecs_id=self.root_ecs_id, lineage_id=self.lineage_id)
        
        # Create some test entities
        self.entity1 = Entity()
        self.entity2 = Entity()
        self.entity3 = Entity()

    def test_graph_initialization(self):
        """Test EntityGraph initialization."""
        self.assertEqual(self.graph.root_ecs_id, self.root_ecs_id)
        self.assertEqual(self.graph.lineage_id, self.lineage_id)
        
        # Collections should be empty
        self.assertEqual(len(self.graph.nodes), 0)
        self.assertEqual(len(self.graph.edges), 0)
        self.assertEqual(len(self.graph.outgoing_edges), 0)
        self.assertEqual(len(self.graph.incoming_edges), 0)
        self.assertEqual(len(self.graph.ancestry_paths), 0)
        self.assertEqual(len(self.graph.live_id_to_ecs_id), 0)
        
        # Counters should be zero
        self.assertEqual(self.graph.node_count, 0)
        self.assertEqual(self.graph.edge_count, 0)
        self.assertEqual(self.graph.max_depth, 0)

    def test_add_entity(self):
        """Test adding entities to the graph."""
        # Add an entity
        self.graph.add_entity(self.entity1)
        
        # Check that entity was added
        self.assertEqual(self.graph.node_count, 1)
        self.assertIn(self.entity1.ecs_id, self.graph.nodes)
        self.assertEqual(self.graph.nodes[self.entity1.ecs_id], self.entity1)
        
        # Check live_id mapping
        self.assertIn(self.entity1.live_id, self.graph.live_id_to_ecs_id)
        self.assertEqual(self.graph.live_id_to_ecs_id[self.entity1.live_id], self.entity1.ecs_id)
        
        # Add more entities
        self.graph.add_entity(self.entity2)
        self.graph.add_entity(self.entity3)
        
        # Check counts
        self.assertEqual(self.graph.node_count, 3)
        self.assertEqual(len(self.graph.nodes), 3)
        self.assertEqual(len(self.graph.live_id_to_ecs_id), 3)
        
        # Check entity retrieval
        self.assertEqual(self.graph.get_entity(self.entity2.ecs_id), self.entity2)
        self.assertEqual(self.graph.get_entity_by_live_id(self.entity3.live_id), self.entity3)
        
        # Add duplicate entity (should not increase count)
        self.graph.add_entity(self.entity1)
        self.assertEqual(self.graph.node_count, 3)

    def test_add_edge(self):
        """Test adding edges to the graph."""
        # Add entities first
        self.graph.add_entity(self.entity1)
        self.graph.add_entity(self.entity2)
        
        # Create an edge
        edge = EntityEdge(
            source_id=self.entity1.ecs_id,
            target_id=self.entity2.ecs_id,
            edge_type=EdgeType.DIRECT,
            field_name="test_field"
        )
        
        # Add the edge
        self.graph.add_edge(edge)
        
        # Check that edge was added
        self.assertEqual(self.graph.edge_count, 1)
        edge_key = (self.entity1.ecs_id, self.entity2.ecs_id)
        self.assertIn(edge_key, self.graph.edges)
        self.assertEqual(self.graph.edges[edge_key], edge)
        
        # Check outgoing/incoming edge mappings
        self.assertIn(self.entity2.ecs_id, self.graph.outgoing_edges[self.entity1.ecs_id])
        self.assertIn(self.entity1.ecs_id, self.graph.incoming_edges[self.entity2.ecs_id])
        
        # Add duplicate edge (should not increase count)
        self.graph.add_edge(edge)
        self.assertEqual(self.graph.edge_count, 1)
        
        # Add edge between different entities
        self.graph.add_entity(self.entity3)
        edge2 = EntityEdge(
            source_id=self.entity2.ecs_id,
            target_id=self.entity3.ecs_id,
            edge_type=EdgeType.DIRECT,
            field_name="another_field"
        )
        self.graph.add_edge(edge2)
        
        # Check counts and relationships
        self.assertEqual(self.graph.edge_count, 2)
        self.assertEqual(len(self.graph.edges), 2)
        self.assertEqual(len(self.graph.outgoing_edges[self.entity2.ecs_id]), 1)
        self.assertEqual(len(self.graph.incoming_edges[self.entity3.ecs_id]), 1)

    def test_edge_type_methods(self):
        """Test methods for adding specific edge types."""
        # Add entities
        self.graph.add_entity(self.entity1)
        self.graph.add_entity(self.entity2)
        
        # Add direct edge
        self.graph.add_direct_edge(self.entity1, self.entity2, "direct_field")
        
        # Check edge was added with correct type
        edge_key = (self.entity1.ecs_id, self.entity2.ecs_id)
        self.assertIn(edge_key, self.graph.edges)
        edge = self.graph.edges[edge_key]
        self.assertEqual(edge.edge_type, EdgeType.DIRECT)
        self.assertEqual(edge.field_name, "direct_field")
        
        # Create a new graph for each edge type
        list_graph = EntityGraph(root_ecs_id=self.root_ecs_id, lineage_id=self.lineage_id)
        list_graph.add_entity(self.entity1)
        list_graph.add_entity(self.entity2)
        
        # Add list edge
        list_graph.add_list_edge(self.entity1, self.entity2, "list_field", 3)
        
        # Check list edge
        list_edge_key = (self.entity1.ecs_id, self.entity2.ecs_id)
        list_edge = list_graph.edges[list_edge_key]
        self.assertEqual(list_edge.edge_type, EdgeType.LIST)
        self.assertEqual(list_edge.field_name, "list_field")
        self.assertEqual(list_edge.container_index, 3)
        
        # Test dict edge
        dict_graph = EntityGraph(root_ecs_id=self.root_ecs_id, lineage_id=self.lineage_id)
        dict_graph.add_entity(self.entity1)
        dict_graph.add_entity(self.entity2)
        
        dict_graph.add_dict_edge(self.entity1, self.entity2, "dict_field", "key1")
        
        dict_edge_key = (self.entity1.ecs_id, self.entity2.ecs_id)
        dict_edge = dict_graph.edges[dict_edge_key]
        self.assertEqual(dict_edge.edge_type, EdgeType.DICT)
        self.assertEqual(dict_edge.field_name, "dict_field")
        self.assertEqual(dict_edge.container_key, "key1")
        
        # Test set edge
        set_graph = EntityGraph(root_ecs_id=self.root_ecs_id, lineage_id=self.lineage_id)
        set_graph.add_entity(self.entity1)
        set_graph.add_entity(self.entity2)
        
        set_graph.add_set_edge(self.entity1, self.entity2, "set_field")
        
        set_edge_key = (self.entity1.ecs_id, self.entity2.ecs_id)
        set_edge = set_graph.edges[set_edge_key]
        self.assertEqual(set_edge.edge_type, EdgeType.SET)
        self.assertEqual(set_edge.field_name, "set_field")
        
        # Test tuple edge
        tuple_graph = EntityGraph(root_ecs_id=self.root_ecs_id, lineage_id=self.lineage_id)
        tuple_graph.add_entity(self.entity1)
        tuple_graph.add_entity(self.entity2)
        
        tuple_graph.add_tuple_edge(self.entity1, self.entity2, "tuple_field", 2)
        
        tuple_edge_key = (self.entity1.ecs_id, self.entity2.ecs_id)
        tuple_edge = tuple_graph.edges[tuple_edge_key]
        self.assertEqual(tuple_edge.edge_type, EdgeType.TUPLE)
        self.assertEqual(tuple_edge.field_name, "tuple_field")
        self.assertEqual(tuple_edge.container_index, 2)
        
    def test_ancestry_methods(self):
        """Test methods for managing ancestry paths and edge classification."""
        # Add entities
        self.graph.add_entity(self.entity1)
        self.graph.add_entity(self.entity2)
        self.graph.add_entity(self.entity3)
        
        # Create edges
        self.graph.add_direct_edge(self.entity1, self.entity2, "field1")
        self.graph.add_direct_edge(self.entity2, self.entity3, "field2")
        
        # Set ancestry paths
        path1 = [self.entity1.ecs_id]
        path2 = [self.entity1.ecs_id, self.entity2.ecs_id]
        path3 = [self.entity1.ecs_id, self.entity2.ecs_id, self.entity3.ecs_id]
        
        self.graph.set_ancestry_path(self.entity1.ecs_id, path1)
        self.graph.set_ancestry_path(self.entity2.ecs_id, path2)
        self.graph.set_ancestry_path(self.entity3.ecs_id, path3)
        
        # Check paths were set
        self.assertEqual(self.graph.get_ancestry_path(self.entity1.ecs_id), path1)
        self.assertEqual(self.graph.get_ancestry_path(self.entity2.ecs_id), path2)
        self.assertEqual(self.graph.get_ancestry_path(self.entity3.ecs_id), path3)
        
        # Check max depth
        self.assertEqual(self.graph.max_depth, 3)
        
        # Check path distances
        self.assertEqual(self.graph.get_path_distance(self.entity1.ecs_id), 1)
        self.assertEqual(self.graph.get_path_distance(self.entity2.ecs_id), 2)
        self.assertEqual(self.graph.get_path_distance(self.entity3.ecs_id), 3)
        
        # Test edge classification
        # Initially edges should not be hierarchical
        self.assertFalse(self.graph.is_hierarchical_edge(self.entity1.ecs_id, self.entity2.ecs_id))
        self.assertFalse(self.graph.is_hierarchical_edge(self.entity2.ecs_id, self.entity3.ecs_id))
        
        # Mark edges as hierarchical
        self.graph.mark_edge_as_hierarchical(self.entity1.ecs_id, self.entity2.ecs_id)
        self.graph.mark_edge_as_hierarchical(self.entity2.ecs_id, self.entity3.ecs_id)
        
        # Check edges are now hierarchical
        self.assertTrue(self.graph.is_hierarchical_edge(self.entity1.ecs_id, self.entity2.ecs_id))
        self.assertTrue(self.graph.is_hierarchical_edge(self.entity2.ecs_id, self.entity3.ecs_id))
        
        # Check hierarchical relationships
        self.assertEqual(self.graph.get_hierarchical_parent(self.entity2.ecs_id), self.entity1.ecs_id)
        self.assertEqual(self.graph.get_hierarchical_parent(self.entity3.ecs_id), self.entity2.ecs_id)
        
        children = self.graph.get_hierarchical_children(self.entity1.ecs_id)
        self.assertEqual(len(children), 1)
        self.assertIn(self.entity2.ecs_id, children)
        
        # Mark an edge as reference
        self.graph.mark_edge_as_reference(self.entity1.ecs_id, self.entity2.ecs_id)
        
        # Check edge is now a reference
        self.assertFalse(self.graph.is_hierarchical_edge(self.entity1.ecs_id, self.entity2.ecs_id))
        

if __name__ == '__main__':
    unittest.main()