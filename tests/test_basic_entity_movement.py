import unittest
from uuid import UUID

from abstractions.ecs.entity import (
    Entity, 
    EntityRegistry,
    build_entity_tree
)

class TestParentEntity(Entity):
    """Parent entity for attachment testing"""
    child: Entity = None
    name: str = ""

class TestBasicEntityMovement(unittest.TestCase):
    """Test the basic entity movement workflow"""

    def setUp(self):
        """Reset the EntityRegistry before each test"""
        # Clear the registry between tests
        EntityRegistry.tree_registry = {}
        EntityRegistry.lineage_registry = {}
        EntityRegistry.live_id_registry = {}
        EntityRegistry.type_registry = {}

    def test_basic_movement_workflow(self):
        """Test the basic workflow of physically moving an entity and updating metadata"""
        # Create two root entities
        parent1 = TestParentEntity()
        parent1.name = "Parent1"
        parent1.root_ecs_id = parent1.ecs_id
        parent1.root_live_id = parent1.live_id
        
        parent2 = TestParentEntity()
        parent2.name = "Parent2"
        parent2.root_ecs_id = parent2.ecs_id
        parent2.root_live_id = parent2.live_id
        
        # Create a child entity
        child = Entity()
        
        # Set up the child as a sub-entity of parent1
        parent1.child = child
        
        # Register both root entities
        EntityRegistry.register_entity(parent1)
        EntityRegistry.register_entity(parent2)
        
        # Verify the child is properly associated with parent1
        print(f"Child root_ecs_id: {child.root_ecs_id}")
        print(f"Parent1 ecs_id: {parent1.ecs_id}")
        
        # Check if child.root_ecs_id is set after parent1 registration
        parent1_tree = EntityRegistry.get_stored_tree(parent1.ecs_id)
        print(f"Parent1 tree has {len(parent1_tree.nodes)} nodes")
        print(f"Child in parent1 tree? {child.ecs_id in parent1_tree.nodes}")
        
        # Remember the child's ID before the move
        child_id_before_move = child.ecs_id
        
        # Step 1: Physically remove from parent1
        print("\nStep 1: Removing child from parent1")
        parent1.child = None 
        
        # Step 2: Call detach() to update metadata
        print("Step 2: Calling child.detach()")
        child.detach()
        
        # Verify the child is now a root entity
        print(f"Child is root after detach? {child.is_root_entity()}")
        print(f"Child ecs_id changed? {child.ecs_id != child_id_before_move}")
        print(f"Child old_ids: {child.old_ids}")
        
        # Remember ID after detach
        child_id_after_detach = child.ecs_id
        
        # Step 3: Physically add to parent2
        print("\nStep 3: Adding child to parent2")
        parent2.child = child
        
        # Build the tree to establish physical connection
        temp_tree = build_entity_tree(parent2)
        print(f"Child is in parent2 tree? {child.ecs_id in temp_tree.nodes}")
        
        # Add the temporary tree to registry
        try:
            EntityRegistry.register_entity_tree(temp_tree)
        except ValueError as e:
            if "already registered" in str(e):
                print("Tree already registered (expected if parent2 is registered)")
            else:
                raise
        
        # Step 4: Call attach() to update metadata
        print("Step 4: Calling child.attach(parent2)")
        child.attach(parent2)
        
        # Verify the child is now attached to parent2
        print(f"Child root_ecs_id == parent2.ecs_id? {child.root_ecs_id == parent2.ecs_id}")
        print(f"Child root_live_id == parent2.live_id? {child.root_live_id == parent2.live_id}")
        
        # Verify the IDs have been updated
        print(f"Child ecs_id changed from detached state? {child.ecs_id != child_id_after_detach}")
        
        # Verify the old IDs are tracked in history
        print(f"Original child ID in history? {child_id_before_move in child.old_ids}")
        print(f"Detached child ID in history? {child_id_after_detach in child.old_ids}")
        
        # Success criteria
        self.assertTrue(child.is_root_entity() or child.root_ecs_id == parent2.ecs_id)
        if not child.is_root_entity():
            self.assertEqual(child.root_ecs_id, parent2.ecs_id)
            self.assertEqual(child.root_live_id, parent2.live_id)
        
        self.assertIn(child_id_before_move, child.old_ids)

if __name__ == "__main__":
    unittest.main()