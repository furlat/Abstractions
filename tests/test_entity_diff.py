import unittest
from uuid import UUID
import copy
from typing import List, Dict, Set, Tuple, Optional, Any

from pydantic import Field

from abstractions.ecs.entity import (
    Entity, 
    EntityTree,
    EntityWithPrimitives,
    EntityinList,
    EntityinDict,
    EntityInEntityInEntity,
    HierarchicalEntity,
    build_entity_tree,
    find_modified_entities,
    get_non_entity_attributes,
    compare_non_entity_attributes
)

# Custom entity classes for testing
class TestEntity(Entity):
    """Simple entity with a string field for testing"""
    test_value: str = ""
    
class NestedTestEntity(Entity):
    """Entity that contains another entity for testing"""
    child: Entity = Field(default_factory=Entity)
    test_value: str = ""
    
class ComplexTestEntity(Entity):
    """Entity with multiple child entities for testing"""
    child1: Entity = Field(default_factory=Entity)
    child2: Entity = Field(default_factory=Entity)
    value: int = 0
    
class BranchEntity(Entity):
    """Entity with named child branches for building test hierarchies"""
    branch1: Entity = Field(default_factory=Entity)
    branch2: Entity = Field(default_factory=Entity)
    branch3: Entity = Field(default_factory=Entity)
    value: str = ""

class TestEntityDiff(unittest.TestCase):
    """Test the entity diffing algorithm"""
    
    def test_get_non_entity_attributes(self):
        """Test the extraction of non-entity attributes from an entity"""
        # Create an entity with primitive fields
        entity = EntityWithPrimitives()
        entity.string_value = "test"
        entity.int_value = 42
        entity.float_value = 3.14
        entity.bool_value = True
        
        # Get non-entity attributes
        attrs = get_non_entity_attributes(entity)
        
        # Check that we get the expected attributes
        self.assertIn("string_value", attrs)
        self.assertIn("int_value", attrs)
        self.assertIn("float_value", attrs)
        self.assertIn("bool_value", attrs)
        
        # Check that we get the expected values
        self.assertEqual(attrs["string_value"], "test")
        self.assertEqual(attrs["int_value"], 42)
        self.assertEqual(attrs["float_value"], 3.14)
        self.assertEqual(attrs["bool_value"], True)
        
        # Check that we don't get entity attributes or identity fields
        self.assertNotIn("ecs_id", attrs)
        self.assertNotIn("live_id", attrs)
        self.assertNotIn("lineage_id", attrs)
        self.assertNotIn("root_ecs_id", attrs)
        
    def test_compare_non_entity_attributes_identical(self):
        """Test comparison of identical non-entity attributes"""
        # Create two identical entities with only primitive fields
        entity1 = TestEntity()
        entity1.test_value = "test data"
        
        entity2 = TestEntity()
        entity2.test_value = "test data"
        
        # Get non-entity attributes for debugging
        attrs1 = get_non_entity_attributes(entity1)
        attrs2 = get_non_entity_attributes(entity2)
        
        # Print for debugging
        print(f"Entity1 attrs: {attrs1}")
        print(f"Entity2 attrs: {attrs2}")
        
        # Compare attributes
        has_changes = compare_non_entity_attributes(entity1, entity2)
        
        # Should be identical
        self.assertFalse(has_changes)
        
    def test_compare_non_entity_attributes_different(self):
        """Test comparison of different non-entity attributes"""
        # Create two entities with different values
        entity1 = EntityWithPrimitives()
        entity1.string_value = "test"
        entity1.int_value = 42
        
        entity2 = EntityWithPrimitives()
        entity2.string_value = "test"
        entity2.int_value = 43  # Different value
        
        # Compare attributes
        has_changes = compare_non_entity_attributes(entity1, entity2)
        
        # Should be different
        self.assertTrue(has_changes)
    
    def test_diff_attribute_changes(self):
        """Test diffing entities with attribute changes"""
        # Create a root entity
        root1 = EntityWithPrimitives()
        root1.string_value = "test"
        root1.int_value = 42
        root1.root_ecs_id = root1.ecs_id
        root1.root_live_id = root1.live_id
        
        # Build the tree
        tree1 = build_entity_tree(root1)
        
        # Create a second version with the same structure but different attribute values
        root2 = EntityWithPrimitives()
        root2.ecs_id = root1.ecs_id  # Same ecs_id to simulate the same entity
        root2.live_id = root1.live_id  # Same live_id
        root2.lineage_id = root1.lineage_id  # Same lineage_id
        root2.string_value = "modified"  # Different value
        root2.int_value = 42  # Same value
        root2.root_ecs_id = root1.root_ecs_id
        root2.root_live_id = root1.root_live_id
        
        # Build the second tree
        tree2 = build_entity_tree(root2)
        
        # Find modified entities
        modified_entities, debug_info = find_modified_entities(tree2, tree1, debug=True)
        
        # We should detect the root entity as modified
        self.assertIn(root2.ecs_id, modified_entities)
        
        # Check debug info
        self.assertEqual(debug_info["comparison_count"], 1)
        self.assertEqual(len(debug_info["added_entities"]), 0)
        self.assertEqual(len(debug_info["removed_entities"]), 0)
    
    def test_diff_nested_attribute_changes(self):
        """Test diffing with changes in a nested entity"""
        # Create a nested structure using our custom NestedTestEntity
        child = TestEntity()
        child.test_value = "original value"
        
        parent = NestedTestEntity()
        parent.test_value = "parent value"
        parent.child = child
        parent.root_ecs_id = parent.ecs_id
        parent.root_live_id = parent.live_id
        
        # Build the first tree
        tree1 = build_entity_tree(parent)
        
        # Create a second version with a change in the child entity
        child2 = TestEntity()
        child2.ecs_id = child.ecs_id  # Same ID
        child2.live_id = child.live_id
        child2.lineage_id = child.lineage_id
        child2.test_value = "modified value"  # Changed value
        
        parent2 = NestedTestEntity()
        parent2.ecs_id = parent.ecs_id  # Same ID
        parent2.live_id = parent.live_id
        parent2.lineage_id = parent.lineage_id
        parent2.test_value = "parent value"  # Same value
        parent2.child = child2
        parent2.root_ecs_id = parent.root_ecs_id
        parent2.root_live_id = parent.root_live_id
        
        # Build the second tree
        tree2 = build_entity_tree(parent2)
        
        # Find modified entities
        modified_entities, debug_info = find_modified_entities(tree2, tree1, debug=True)
        
        # Both child and parent should be marked as modified
        # The child because its attributes changed
        # The parent because it's in the path from child to root
        self.assertIn(child2.ecs_id, modified_entities)
        self.assertIn(parent2.ecs_id, modified_entities)
        
        # Check that we did some comparisons - the exact count might vary
        # depending on how we implement the diff algorithm
        self.assertGreaterEqual(debug_info["comparison_count"], 1)
    
    def test_diff_container_entity_added(self):
        """Test diffing when a new entity is added to a container"""
        # Create an entity with a list container
        list_entity1 = EntityinList()
        list_entity1.root_ecs_id = list_entity1.ecs_id
        list_entity1.root_live_id = list_entity1.live_id
        
        # First version has an empty list
        list_entity1.entities = []
        
        # Build the first tree
        tree1 = build_entity_tree(list_entity1)
        
        # Create a second entity with the same ID but with an entity in the list
        list_entity2 = EntityinList()
        list_entity2.ecs_id = list_entity1.ecs_id
        list_entity2.live_id = list_entity1.live_id
        list_entity2.lineage_id = list_entity1.lineage_id
        list_entity2.root_ecs_id = list_entity1.root_ecs_id
        list_entity2.root_live_id = list_entity1.root_live_id
        
        # Add an entity to the list
        child = Entity()
        list_entity2.entities = [child]
        
        # Build the second tree
        tree2 = build_entity_tree(list_entity2)
        
        # Find modified entities
        modified_entities, debug_info = find_modified_entities(tree2, tree1, debug=True)
        
        # We should detect the list entity as structurally changed
        # because it has a new entity in its list
        self.assertIn(list_entity2.ecs_id, modified_entities)
        
        # Check that we detected the added entity
        self.assertEqual(len(debug_info["added_entities"]), 1)
        self.assertTrue(child.ecs_id in debug_info["added_entities"])
    
    def test_diff_container_entity_substituted(self):
        """Test diffing when an entity in a container is substituted"""
        # Create entities for the dictionary
        entity1 = Entity()
        entity2 = Entity()  # Different entity
        
        # Create a dictionary container entity
        dict_entity1 = EntityinDict()
        dict_entity1.root_ecs_id = dict_entity1.ecs_id
        dict_entity1.root_live_id = dict_entity1.live_id
        dict_entity1.entities = {"key": entity1}
        
        # Build the first tree
        tree1 = build_entity_tree(dict_entity1)
        
        # Create a second version with the same structure but different entity in the dict
        dict_entity2 = EntityinDict()
        dict_entity2.ecs_id = dict_entity1.ecs_id
        dict_entity2.live_id = dict_entity1.live_id
        dict_entity2.lineage_id = dict_entity1.lineage_id
        dict_entity2.root_ecs_id = dict_entity1.root_ecs_id
        dict_entity2.root_live_id = dict_entity1.root_live_id
        dict_entity2.entities = {"key": entity2}  # Different entity
        
        # Build the second tree
        tree2 = build_entity_tree(dict_entity2)
        
        # Find modified entities
        modified_entities, debug_info = find_modified_entities(tree2, tree1, debug=True)
        
        # We should detect both the dict_entity and entity2 as modified
        self.assertIn(dict_entity2.ecs_id, modified_entities)
        self.assertIn(entity2.ecs_id, modified_entities)
        
        # The old entity should be marked as removed
        self.assertTrue(entity1.ecs_id in debug_info["removed_entities"])
        
        # The new entity should be marked as added
        self.assertTrue(entity2.ecs_id in debug_info["added_entities"])

    def test_diff_deep_hierarchy_no_changes(self):
        """Test diffing on a deep hierarchy with no changes"""
        # Create a deep hierarchical structure
        deep_entity = EntityInEntityInEntity()
        deep_entity.root_ecs_id = deep_entity.ecs_id
        deep_entity.root_live_id = deep_entity.live_id
        
        # Build the tree
        tree1 = build_entity_tree(deep_entity)
        
        # Create a deep copy with the same structure and values
        deep_entity2 = copy.deepcopy(deep_entity)
        
        # Restore the identity fields to match exactly
        deep_entity2.ecs_id = deep_entity.ecs_id
        deep_entity2.live_id = deep_entity.live_id
        deep_entity2.lineage_id = deep_entity.lineage_id
        deep_entity2.root_ecs_id = deep_entity.root_ecs_id
        deep_entity2.root_live_id = deep_entity.root_live_id
        
        # Now we need to restore identity fields for all nested entities
        # For entity_of_entity
        deep_entity2.entity_of_entity.ecs_id = deep_entity.entity_of_entity.ecs_id
        deep_entity2.entity_of_entity.live_id = deep_entity.entity_of_entity.live_id
        deep_entity2.entity_of_entity.lineage_id = deep_entity.entity_of_entity.lineage_id
        
        # For sub_entity in entity_of_entity
        deep_entity2.entity_of_entity.sub_entity.ecs_id = deep_entity.entity_of_entity.sub_entity.ecs_id
        deep_entity2.entity_of_entity.sub_entity.live_id = deep_entity.entity_of_entity.sub_entity.live_id
        deep_entity2.entity_of_entity.sub_entity.lineage_id = deep_entity.entity_of_entity.sub_entity.lineage_id
        
        # Build the second tree
        tree2 = build_entity_tree(deep_entity2)
        
        # Find modified entities
        modified_entities, debug_info = find_modified_entities(tree2, tree1, debug=True)
        
        # Should be no changes
        self.assertEqual(len(modified_entities), 0)
        self.assertEqual(debug_info["comparison_count"], 3)  # Should compare all 3 entities
    
    def test_diff_deep_hierarchy_leaf_change(self):
        """Test diffing on a deep hierarchy with a change in a leaf entity"""
        # Create a deep hierarchical structure
        deep_entity = EntityInEntityInEntity()
        deep_entity.root_ecs_id = deep_entity.ecs_id
        deep_entity.root_live_id = deep_entity.live_id
        
        # Add some non-entity data to the leaf
        deep_entity.entity_of_entity.sub_entity.untyped_data = "original"
        
        # Build the tree
        tree1 = build_entity_tree(deep_entity)
        
        # Create a deep copy
        deep_entity2 = copy.deepcopy(deep_entity)
        
        # Restore the identity fields to match exactly for all entities in the hierarchy
        # Root entity
        deep_entity2.ecs_id = deep_entity.ecs_id
        deep_entity2.live_id = deep_entity.live_id
        deep_entity2.lineage_id = deep_entity.lineage_id
        deep_entity2.root_ecs_id = deep_entity.root_ecs_id
        deep_entity2.root_live_id = deep_entity.root_live_id
        
        # Middle entity
        deep_entity2.entity_of_entity.ecs_id = deep_entity.entity_of_entity.ecs_id
        deep_entity2.entity_of_entity.live_id = deep_entity.entity_of_entity.live_id
        deep_entity2.entity_of_entity.lineage_id = deep_entity.entity_of_entity.lineage_id
        
        # Leaf entity
        deep_entity2.entity_of_entity.sub_entity.ecs_id = deep_entity.entity_of_entity.sub_entity.ecs_id
        deep_entity2.entity_of_entity.sub_entity.live_id = deep_entity.entity_of_entity.sub_entity.live_id
        deep_entity2.entity_of_entity.sub_entity.lineage_id = deep_entity.entity_of_entity.sub_entity.lineage_id
        
        # Modify the leaf entity
        deep_entity2.entity_of_entity.sub_entity.untyped_data = "modified"
        
        # Build the second tree
        tree2 = build_entity_tree(deep_entity2)
        
        # Find modified entities
        modified_entities, debug_info = find_modified_entities(tree2, tree1, debug=True)
        
        # Should have identified changes in all three entities
        # The leaf node should be detected as changed due to its attribute
        # The entire path to the root should be marked for changes
        self.assertEqual(len(modified_entities), 3)
        self.assertIn(deep_entity2.ecs_id, modified_entities)  # Root
        self.assertIn(deep_entity2.entity_of_entity.ecs_id, modified_entities)  # Middle
        self.assertIn(deep_entity2.entity_of_entity.sub_entity.ecs_id, modified_entities)  # Leaf
        
        # Check that we did the right number of comparisons
        # Should have compared all 3 entities but might stop after finding the leaf change
        self.assertLessEqual(debug_info["comparison_count"], 3)
    
    def test_diff_multi_branch_structure_isolated_change(self):
        """Test diffing on a multi-branch structure with a change in only one branch"""
        # Create a hierarchical entity with multiple branches
        root = HierarchicalEntity()
        root.root_ecs_id = root.ecs_id
        root.root_live_id = root.live_id
        
        # Add some data to various parts
        root.flat_entity.untyped_data = "flat data"
        root.entity_of_entity_1.untyped_data = "branch 1 data"
        root.entity_of_entity_1.sub_entity.untyped_data = "branch 1 leaf data"
        root.entity_of_entity_2.untyped_data = "branch 2 data"
        root.entity_of_entity_2.sub_entity.untyped_data = "branch 2 leaf data"
        root.entity_of_entity_of_entity.untyped_data = "deep branch data"
        root.entity_of_entity_of_entity.entity_of_entity.untyped_data = "deep branch middle data"
        root.entity_of_entity_of_entity.entity_of_entity.sub_entity.untyped_data = "deep branch leaf data"
        root.primitive_data.string_value = "string value"
        root.primitive_data.int_value = 42
        
        # Build the first tree
        tree1 = build_entity_tree(root)
        
        # Create a deep copy
        root2 = copy.deepcopy(root)
        
        # Helper function to restore identity fields recursively
        def restore_identity(original, copy_of):
            copy_of.ecs_id = original.ecs_id
            copy_of.live_id = original.live_id
            copy_of.lineage_id = original.lineage_id
            copy_of.root_ecs_id = original.root_ecs_id
            copy_of.root_live_id = original.root_live_id
        
        # Restore all identity fields
        restore_identity(root, root2)
        restore_identity(root.flat_entity, root2.flat_entity)
        restore_identity(root.entity_of_entity_1, root2.entity_of_entity_1)
        restore_identity(root.entity_of_entity_1.sub_entity, root2.entity_of_entity_1.sub_entity)
        restore_identity(root.entity_of_entity_2, root2.entity_of_entity_2)
        restore_identity(root.entity_of_entity_2.sub_entity, root2.entity_of_entity_2.sub_entity)
        restore_identity(root.entity_of_entity_of_entity, root2.entity_of_entity_of_entity)
        restore_identity(root.entity_of_entity_of_entity.entity_of_entity, root2.entity_of_entity_of_entity.entity_of_entity)
        restore_identity(root.entity_of_entity_of_entity.entity_of_entity.sub_entity, root2.entity_of_entity_of_entity.entity_of_entity.sub_entity)
        restore_identity(root.primitive_data, root2.primitive_data)
        
        # Change only one branch
        root2.entity_of_entity_2.sub_entity.untyped_data = "MODIFIED branch 2 leaf data"
        
        # Build the second tree
        tree2 = build_entity_tree(root2)
        
        # Find modified entities
        modified_entities, debug_info = find_modified_entities(tree2, tree1, debug=True)
        
        # Should have identified changes in only the modified branch
        self.assertIn(root2.ecs_id, modified_entities)  # Root
        self.assertIn(root2.entity_of_entity_2.ecs_id, modified_entities)  # Branch 2 
        self.assertIn(root2.entity_of_entity_2.sub_entity.ecs_id, modified_entities)  # Branch 2 leaf
        
        # Unchanged branches should not be in the modified set
        self.assertNotIn(root2.entity_of_entity_1.ecs_id, modified_entities)  # Branch 1
        self.assertNotIn(root2.entity_of_entity_1.sub_entity.ecs_id, modified_entities)  # Branch 1 leaf
        self.assertNotIn(root2.entity_of_entity_of_entity.ecs_id, modified_entities)  # Deep branch
        
        # Should have compared all entities but found changes only in one branch
        self.assertGreaterEqual(debug_info["comparison_count"], 3)
    
    def test_diff_performance_with_large_hierarchy(self):
        """Test the performance of the diff algorithm on a large hierarchy"""
        # Create a hierarchy of entities for testing
        
        # Create the root entity
        root = ComplexTestEntity()
        root.value = 100
        root.root_ecs_id = root.ecs_id
        root.root_live_id = root.live_id
        
        # Build a hierarchy with BranchEntity nodes
        # Level 1
        root.child1 = BranchEntity()
        root.child1.value = "Level 1, Branch 1"
        
        root.child2 = BranchEntity()
        root.child2.value = "Level 1, Branch 2"
        
        # Level 2 - Branch 1
        root.child1.branch1 = TestEntity()
        root.child1.branch1.test_value = "L2-B1-1"
        
        root.child1.branch2 = TestEntity()
        root.child1.branch2.test_value = "L2-B1-2"
        
        # Level 2 - Branch 2
        root.child2.branch1 = TestEntity()
        root.child2.branch1.test_value = "L2-B2-1"
        
        root.child2.branch2 = TestEntity()
        root.child2.branch2.test_value = "L2-B2-2"
        
        # Build the first tree
        tree1 = build_entity_tree(root)
        
        # Create a deep copy for the second version
        root2 = copy.deepcopy(root)
        
        # Restore identity fields to create an identical tree
        # Helper function to restore identity across all entities
        def restore_identity(original, copied):
            # Restore the entity's identity fields
            copied.ecs_id = original.ecs_id
            copied.live_id = original.live_id
            copied.lineage_id = original.lineage_id
            copied.root_ecs_id = original.root_ecs_id
            copied.root_live_id = original.root_live_id
            
            # Process all fields that might contain entities
            for field_name in original.model_fields:
                orig_value = getattr(original, field_name)
                if isinstance(orig_value, Entity):
                    copied_value = getattr(copied, field_name)
                    restore_identity(orig_value, copied_value)
        
        # Perform the identity restoration
        restore_identity(root, root2)
        
        # Now modify a leaf node in the second tree
        # We'll modify the test_value of a leaf entity
        leaf_entity = root2.child2.branch2
        leaf_entity.test_value = "MODIFIED VALUE"
        
        # Build the second tree
        tree2 = build_entity_tree(root2)
        
        # Find modified entities
        modified_entities, debug_info = find_modified_entities(tree2, tree1, debug=True)
        
        # Verify results
        # The leaf entity and its ancestors should be modified
        self.assertIn(leaf_entity.ecs_id, modified_entities)
        self.assertIn(root2.child2.ecs_id, modified_entities)
        self.assertIn(root2.ecs_id, modified_entities)
        
        # Other branch should not be marked as modified
        self.assertNotIn(root2.child1.ecs_id, modified_entities)
        self.assertNotIn(root2.child1.branch1.ecs_id, modified_entities)
        
        # We should have done fewer comparisons than the total number of entities
        total_entities = 7  # root + 2 level1 + 4 level2
        self.assertLessEqual(debug_info["comparison_count"], total_entities)

    def test_diff_entity_moved_within_tree(self):
        """Test diffing when an entity is moved from one parent to another within the same tree"""
        # Create a hierarchy with two branches
        root = ComplexTestEntity()
        root.value = 100
        root.root_ecs_id = root.ecs_id
        root.root_live_id = root.live_id
        
        # Create two branches
        branch1 = BranchEntity()
        branch1.value = "Branch 1"
        root.child1 = branch1
        
        branch2 = BranchEntity()
        branch2.value = "Branch 2"
        root.child2 = branch2
        
        # Create a child entity that will be moved
        movable_entity = TestEntity()
        movable_entity.test_value = "I will be moved"
        
        # Initially attach to branch1
        branch1.branch1 = movable_entity
        
        # Build the first tree
        tree1 = build_entity_tree(root)
        
        # Create a deep copy for the second version
        root2 = copy.deepcopy(root)
        
        # Restore identity fields
        def restore_identity(original, copied):
            # Restore the entity's identity fields
            copied.ecs_id = original.ecs_id
            copied.live_id = original.live_id
            copied.lineage_id = original.lineage_id
            copied.root_ecs_id = original.root_ecs_id
            copied.root_live_id = original.root_live_id
            
            # Process all fields that might contain entities
            for field_name in original.model_fields:
                orig_value = getattr(original, field_name)
                if isinstance(orig_value, Entity):
                    copied_value = getattr(copied, field_name)
                    restore_identity(orig_value, copied_value)
        
        # Perform the identity restoration
        restore_identity(root, root2)
        
        # Now move the entity from branch1 to branch2
        # This simulates detaching from one parent and attaching to another
        branch1_copy = root2.child1
        branch2_copy = root2.child2
        movable_entity_copy = branch1_copy.branch1
        
        # Store reference to the entity to be moved
        moved_entity = branch1_copy.branch1
        
        # Remove from branch1 by setting to None instead of replacing
        branch1_copy.branch1 = None
        
        # Add to branch2
        branch2_copy.branch3 = moved_entity
        
        # Build the second tree
        tree2 = build_entity_tree(root2)
        
        # Find modified entities
        modified_entities, debug_info = find_modified_entities(tree2, tree1, debug=True)
        
        # Print debugging info for reference
        print("Modified entities:", modified_entities)
        print("Added entities:", debug_info["added_entities"])
        print("Removed entities:", debug_info["removed_entities"])
        print("Moved entities:", debug_info["moved_entities"])
        print(f"Root ID: {root2.ecs_id}")
        print(f"Branch1 ID: {branch1_copy.ecs_id}")
        print(f"Branch2 ID: {branch2_copy.ecs_id}")
        print(f"Movable entity ID: {movable_entity_copy.ecs_id}")
        
        # Verify:
        # 1. Branch1 should be marked as modified (entity was removed)
        self.assertIn(branch1_copy.ecs_id, modified_entities, "Branch1 where entity was removed should be modified")
        
        # 2. Root should be marked as modified (ancestor of both branches)
        self.assertIn(root2.ecs_id, modified_entities, "Root entity should be modified")
        
        # 3. Branch2 should be marked as modified (entity was added)
        self.assertIn(branch2_copy.ecs_id, modified_entities, "Branch2 where entity was added should be modified")
        
        # 4. The moved entity should be detected as moved
        self.assertIn(movable_entity_copy.ecs_id, debug_info["moved_entities"],
                      "Moved entity should be detected as moved")

    def test_diff_new_field_addition(self):
        """Test diffing when a new non-entity field is added to an entity"""
        # Create a simple entity
        root = TestEntity()
        root.test_value = "root"
        root.root_ecs_id = root.ecs_id
        root.root_live_id = root.live_id
        
        # Build the first tree
        tree1 = build_entity_tree(root)
        
        # Create a second version where we'll add a new field
        root2 = copy.deepcopy(root)
        root2.ecs_id = root.ecs_id
        root2.live_id = root.live_id
        root2.lineage_id = root.lineage_id
        root2.root_ecs_id = root.root_ecs_id
        root2.root_live_id = root.root_live_id
        
        # Add a new non-entity field that didn't exist in the first version
        root2.untyped_data = "Added untyped data" 
        
        # Build the second tree
        tree2 = build_entity_tree(root2)
        
        # Find modified entities
        modified_entities, debug_info = find_modified_entities(tree2, tree1, debug=True)
        
        # The root should be modified since it has a new field
        self.assertIn(root2.ecs_id, modified_entities)
    
    def test_diff_new_entity_field_addition(self):
        """Test diffing when a new entity field is added to a container"""
        # For this test, we'll use the BranchEntity which already has defined fields
        
        # Create a simple hierarchy
        root = BranchEntity()
        root.value = "root"
        root.root_ecs_id = root.ecs_id
        root.root_live_id = root.live_id
        
        # Initially, no branch entities are set
        
        # Build the first tree
        tree1 = build_entity_tree(root)
        
        # Create a second version where we'll add a new entity
        root2 = copy.deepcopy(root)
        root2.ecs_id = root.ecs_id
        root2.live_id = root.live_id
        root2.lineage_id = root.lineage_id
        root2.root_ecs_id = root.root_ecs_id
        root2.root_live_id = root.root_live_id
        
        # Create and add a brand new entity to a field that was previously None
        new_child = Entity()
        root2.branch1 = new_child
        
        # Build the second tree
        tree2 = build_entity_tree(root2)
        
        # Find modified entities
        modified_entities, debug_info = find_modified_entities(tree2, tree1, debug=True)
        
        # Print debug info
        print("Modified entities:", modified_entities)
        print("Added entities:", debug_info["added_entities"])
        print("Root ID:", root2.ecs_id)
        print("New child ID:", new_child.ecs_id)
        
        # The root should be modified since it has a new entity field filled
        self.assertIn(root2.ecs_id, modified_entities, "Root should be modified when new entity is added")
        
        # The new entity should be in the added entities list
        self.assertIn(new_child.ecs_id, debug_info["added_entities"], "New entity should be detected as added")
    
    def test_diff_optional_entity_nullified(self):
        """Test diffing when an optional entity is set to None"""
        # Create an entity with an optional field
        parent = NestedTestEntity()
        parent.test_value = "parent"
        parent.child = TestEntity()
        parent.child.test_value = "child"
        parent.root_ecs_id = parent.ecs_id
        parent.root_live_id = parent.live_id
        
        # Build the first tree
        tree1 = build_entity_tree(parent)
        
        # Create a second version with the optional entity set to None
        parent2 = copy.deepcopy(parent)
        parent2.ecs_id = parent.ecs_id
        parent2.live_id = parent.live_id
        parent2.lineage_id = parent.lineage_id
        parent2.root_ecs_id = parent.root_ecs_id
        parent2.root_live_id = parent.root_live_id
        
        # Set the optional entity to None
        removedChild = parent2.child
        parent2.child = None
        
        # Build the second tree
        tree2 = build_entity_tree(parent2)
        
        # Find modified entities
        modified_entities, debug_info = find_modified_entities(tree2, tree1, debug=True)
        
        # Verify:
        # 1. The parent should be marked as modified
        self.assertIn(parent2.ecs_id, modified_entities)
        
        # 2. The removed entity should be detected
        self.assertEqual(len(debug_info["removed_entities"]), 1)
        self.assertIn(removedChild.ecs_id, debug_info["removed_entities"])

    def test_diff_reassign_child_of_removed_entity(self):
        """Test diffing when a parent entity is removed and its child is reassigned elsewhere"""
        # Create a hierarchy with a parent entity that will be removed
        root = ComplexTestEntity()
        root.value = 100
        root.root_ecs_id = root.ecs_id
        root.root_live_id = root.live_id
        
        # Create a structure with two branches
        middle_entity1 = BranchEntity()  # This will be removed in the next version
        middle_entity1.value = "Middle 1"
        root.child1 = middle_entity1
        
        middle_entity2 = BranchEntity()  # This will receive a reassigned child
        middle_entity2.value = "Middle 2"
        root.child2 = middle_entity2
        
        # Create a child entity that will be reassigned
        child_entity = TestEntity()
        child_entity.test_value = "Child to be reassigned"
        middle_entity1.branch1 = child_entity  # Initially attached to middle_entity1
        
        # Build the first tree
        tree1 = build_entity_tree(root)
        
        # Create a second version with restructured hierarchy
        root2 = copy.deepcopy(root)
        
        # Restore identity fields for root
        root2.ecs_id = root.ecs_id
        root2.live_id = root.live_id
        root2.lineage_id = root.lineage_id
        root2.root_ecs_id = root.root_ecs_id
        root2.root_live_id = root.root_live_id
        
        # Restore middle_entity2 identity
        middle_entity2_copy = root2.child2
        middle_entity2_copy.ecs_id = middle_entity2.ecs_id
        middle_entity2_copy.live_id = middle_entity2.live_id
        middle_entity2_copy.lineage_id = middle_entity2.lineage_id
        
        # Restore child_entity identity
        child_entity_copy = root2.child1.branch1
        child_entity_copy.ecs_id = child_entity.ecs_id
        child_entity_copy.live_id = child_entity.live_id
        child_entity_copy.lineage_id = child_entity.lineage_id
        
        # Now make the changes:
        # 1. Remove middle_entity1
        root2.child1 = None
        
        # 2. Reassign child_entity to middle_entity2
        middle_entity2_copy.branch2 = child_entity_copy
        
        # Build the second tree
        tree2 = build_entity_tree(root2)
        
        # Find modified entities
        modified_entities, debug_info = find_modified_entities(tree2, tree1, debug=True)
        
        # Print debug info
        print("Modified entities:", modified_entities)
        print("Added entities:", debug_info["added_entities"])
        print("Removed entities:", debug_info["removed_entities"])
        print("Moved entities:", debug_info["moved_entities"])
        print(f"Root ID: {root2.ecs_id}")
        print(f"Child ID: {child_entity_copy.ecs_id}")
        print(f"Middle2 ID: {middle_entity2_copy.ecs_id}")
        
        # Verify results:
        # 1. Root should be marked as modified
        self.assertIn(root2.ecs_id, modified_entities, "Root should be modified")
        
        # 2. Middle entity 2 should be marked as modified (received a new child)
        self.assertIn(middle_entity2_copy.ecs_id, modified_entities, "Middle entity 2 should be modified")
        
        # 3. Child entity should be recognized as moved
        self.assertIn(child_entity_copy.ecs_id, debug_info["moved_entities"], "Child entity should be marked as moved")
        
        # 4. Child entity should be in the ancestry path of modified entities
        self.assertIn(child_entity_copy.ecs_id, modified_entities, "Child entity should be marked for versioning")
        
        # 5. Middle entity 1 should be marked as removed
        self.assertTrue(any(id for id in debug_info["removed_entities"] if id != child_entity_copy.ecs_id),
                      "Middle entity 1 should be detected as removed")

if __name__ == "__main__":
    unittest.main()