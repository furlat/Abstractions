"""
Tests for the process_entity_reference function that handles entity references during tree building.
"""
import unittest
from uuid import uuid4
from collections import deque

from abstractions.ecs.entity import (
    Entity, EntityTree, process_entity_reference, EdgeType
)


class TestEntityReferenceProcessing(unittest.TestCase):
    """Test the process_entity_reference function."""

    def setUp(self):
        """Set up test data."""
        self.root_entity = Entity()
        self.root_entity.root_ecs_id = self.root_entity.ecs_id
        self.root_entity.root_live_id = self.root_entity.live_id
        
        self.source_entity = Entity()
        self.target_entity = Entity()
        
        self.tree = EntityTree(
            root_ecs_id=self.root_entity.ecs_id,
            lineage_id=self.root_entity.lineage_id
        )
        
        # Add source and target to tree
        self.tree.add_entity(self.source_entity)
        self.tree.add_entity(self.target_entity)

    def test_direct_reference(self):
        """Test processing a direct entity reference."""
        # Process a direct reference
        process_entity_reference(
            tree=self.tree,
            source=self.source_entity,
            target=self.target_entity,
            field_name="test_field"
        )
        
        # Check edge creation
        edge_key = (self.source_entity.ecs_id, self.target_entity.ecs_id)
        self.assertIn(edge_key, self.tree.edges)
        
        # Check edge attributes
        edge = self.tree.edges[edge_key]
        self.assertEqual(edge.edge_type, EdgeType.DIRECT)
        self.assertEqual(edge.field_name, "test_field")
        self.assertIsNone(edge.container_index)
        self.assertIsNone(edge.container_key)

    def test_list_reference(self):
        """Test processing a list entity reference."""
        # Process a list reference
        process_entity_reference(
            tree=self.tree,
            source=self.source_entity,
            target=self.target_entity,
            field_name="list_field",
            list_index=3
        )
        
        # Check edge creation
        edge_key = (self.source_entity.ecs_id, self.target_entity.ecs_id)
        self.assertIn(edge_key, self.tree.edges)
        
        # Check edge attributes
        edge = self.tree.edges[edge_key]
        self.assertEqual(edge.edge_type, EdgeType.LIST)
        self.assertEqual(edge.field_name, "list_field")
        self.assertEqual(edge.container_index, 3)
        self.assertIsNone(edge.container_key)

    def test_dict_reference(self):
        """Test processing a dictionary entity reference."""
        # Process a dict reference
        process_entity_reference(
            tree=self.tree,
            source=self.source_entity,
            target=self.target_entity,
            field_name="dict_field",
            dict_key="test_key"
        )
        
        # Check edge creation
        edge_key = (self.source_entity.ecs_id, self.target_entity.ecs_id)
        self.assertIn(edge_key, self.tree.edges)
        
        # Check edge attributes
        edge = self.tree.edges[edge_key]
        self.assertEqual(edge.edge_type, EdgeType.DICT)
        self.assertEqual(edge.field_name, "dict_field")
        self.assertIsNone(edge.container_index)
        self.assertEqual(edge.container_key, "test_key")

    def test_tuple_reference(self):
        """Test processing a tuple entity reference."""
        # Process a tuple reference
        process_entity_reference(
            tree=self.tree,
            source=self.source_entity,
            target=self.target_entity,
            field_name="tuple_field",
            tuple_index=2
        )
        
        # Check edge creation
        edge_key = (self.source_entity.ecs_id, self.target_entity.ecs_id)
        self.assertIn(edge_key, self.tree.edges)
        
        # Check edge attributes
        edge = self.tree.edges[edge_key]
        self.assertEqual(edge.edge_type, EdgeType.TUPLE)
        self.assertEqual(edge.field_name, "tuple_field")
        self.assertEqual(edge.container_index, 2)
        self.assertIsNone(edge.container_key)

    def test_distance_map_update(self):
        """Test that the distance map is updated correctly."""
        # Create a distance map with source at distance 5
        distance_map = {self.source_entity.ecs_id: 5}
        
        # Process reference with distance map
        process_entity_reference(
            tree=self.tree,
            source=self.source_entity,
            target=self.target_entity,
            field_name="test_field",
            distance_map=distance_map
        )
        
        # Check distance map was updated
        self.assertIn(self.target_entity.ecs_id, distance_map)
        self.assertEqual(distance_map[self.target_entity.ecs_id], 6)  # source + 1
        
        # Test finding a shorter path
        source2 = Entity()
        self.tree.add_entity(source2)
        
        # Set source2 to have a shorter distance
        distance_map[source2.ecs_id] = 2
        
        # Process reference from source2
        process_entity_reference(
            tree=self.tree,
            source=source2,
            target=self.target_entity,
            field_name="shorter_path",
            distance_map=distance_map
        )
        
        # Check distance map was updated to shorter distance
        self.assertEqual(distance_map[self.target_entity.ecs_id], 3)  # source2 + 1

    def test_processing_queue(self):
        """Test that the processing queue is updated correctly."""
        # Create a processing queue
        to_process = deque()
        
        # Process reference with queue
        process_entity_reference(
            tree=self.tree,
            source=self.source_entity,
            target=self.target_entity,
            field_name="test_field",
            to_process=to_process
        )
        
        # Check target was added to queue
        # Note: in the current implementation, the target is added to the queue
        # both in the distance map update logic and explicitly at the end
        self.assertEqual(len(to_process), 1)
        self.assertIn(self.target_entity, to_process)
        
        # Test reprocessing when a shorter path is found
        distance_map = {
            self.source_entity.ecs_id: 5,
            self.target_entity.ecs_id: 10  # Initially a long distance
        }
        
        # Clear queue and process again
        to_process.clear()
        process_entity_reference(
            tree=self.tree,
            source=self.source_entity,
            target=self.target_entity,
            field_name="test_field",
            to_process=to_process,
            distance_map=distance_map
        )
        
        # Check target was added to queue since we found a shorter path
        # The target is added both by the reprocessing logic and the explicit add at the end
        self.assertIn(self.target_entity, to_process)
        self.assertEqual(distance_map[self.target_entity.ecs_id], 6)  # Updated to source + 1


if __name__ == '__main__':
    unittest.main()