"""
Container Entity Bug - Debug Version with Print Statements

This adds strategic print statements to track exactly what happens during
the versioning process when a new entity is added to a container.
"""

import sys
sys.path.append('..')

from typing import List, Dict
from uuid import UUID
from pydantic import Field

# Import our entity system
from abstractions.ecs.entity import (
    Entity, EntityRegistry, build_entity_tree, find_modified_entities
)

print("🔬 Container Entity Bug - Debug Version")
print("=" * 50)

# Define test entities
class ChildEntity(Entity):
    """Child entity for container tests."""
    name: str = ""
    data: str = ""

class ContainerEntity(Entity):
    """Entity with properly typed container fields."""
    name: str = ""
    children_list: List[ChildEntity] = Field(default_factory=list)
    children_dict: Dict[str, ChildEntity] = Field(default_factory=dict)

def clear_entity_registry():
    """Clear the EntityRegistry for isolated testing."""
    EntityRegistry.tree_registry.clear()
    EntityRegistry.lineage_registry.clear()
    EntityRegistry.live_id_registry.clear()
    EntityRegistry.ecs_id_to_root_id.clear()
    EntityRegistry.type_registry.clear()

def debug_version_entity_process():
    """Debug the exact versioning process with detailed logging."""
    print("\n🔍 Debug: Versioning Process with New Entity")
    print("-" * 40)
    
    clear_entity_registry()
    
    # Step 1: Create initial container with entities
    print("📝 Step 1: Creating initial container...")
    container = ContainerEntity(name="Container")
    child1 = ChildEntity(name="Child1", data="data1")
    child2 = ChildEntity(name="Child2", data="data2")
    
    container.children_list = [child1, child2]
    container.promote_to_root()
    
    print(f"   Container ECS ID: {container.ecs_id}")
    print(f"   Container Root ECS ID: {container.root_ecs_id}")
    print(f"   Child1 ECS ID: {child1.ecs_id}")
    print(f"   Child2 ECS ID: {child2.ecs_id}")
    
    # Step 2: Add new entity to container (THE CRITICAL STEP)
    print("\n📝 Step 2: Adding new entity to container...")
    new_child = ChildEntity(name="NewChild", data="new_data")
    container.children_list.append(new_child)
    
    print(f"   New Child ECS ID: {new_child.ecs_id}")
    print(f"   Container children_list length: {len(container.children_list)}")
    
    # Step 3: Manual debugging of version_entity() process
    print("\n🔍 Step 3: Manual version_entity() debugging...")
    
    # 3a: Get old tree from storage
    old_tree = EntityRegistry.get_stored_tree(container.root_ecs_id)
    print(f"   Old tree nodes: {len(old_tree.nodes) if old_tree else 'None'}")
    if old_tree:
        print(f"   Old tree entity IDs: {list(old_tree.nodes.keys())}")
    
    # 3b: Build new tree from current state
    new_tree = build_entity_tree(container)
    print(f"   New tree nodes: {len(new_tree.nodes)}")
    print(f"   New tree entity IDs: {list(new_tree.nodes.keys())}")
    print(f"   New tree root ECS ID: {new_tree.root_ecs_id}")
    
    # 3c: Find modified entities
    if old_tree:
        modified_entities = list(find_modified_entities(new_tree=new_tree, old_tree=old_tree))
        print(f"   Modified entities detected: {len(modified_entities)}")
        print(f"   Modified entity IDs: {modified_entities}")
        
        # Check if new entity is in modified list
        new_child_in_modified = new_child.ecs_id in modified_entities
        print(f"   New child in modified entities: {new_child_in_modified}")
        
        # Check tree structure for new entity
        new_child_in_new_tree = new_child.ecs_id in new_tree.nodes
        print(f"   New child in new tree nodes: {new_child_in_new_tree}")
        
        if not new_child_in_modified:
            print("   ❌ BUG IDENTIFIED: New entity not detected as modified!")
            print("   This means it won't get updated ECS IDs or proper registration!")
            
            # Let's check what find_modified_entities is actually detecting
            debug_modified_entities(new_tree, old_tree, new_child.ecs_id)
    
    # Step 4: Call actual version_entity and see what happens
    print("\n🔄 Step 4: Calling EntityRegistry.version_entity()...")
    
    # Add more detailed tracking before versioning
    print(f"   Before versioning - registry entries: {len(EntityRegistry.ecs_id_to_root_id)}")
    print(f"   Before versioning - new child in registry: {new_child.ecs_id in EntityRegistry.ecs_id_to_root_id}")
    
    version_result = EntityRegistry.version_entity(container)
    print(f"   Versioning result: {version_result}")
    
    # Check registry state after versioning
    print(f"   After versioning - registry entries: {len(EntityRegistry.ecs_id_to_root_id)}")
    print(f"   After versioning - new child in registry: {new_child.ecs_id in EntityRegistry.ecs_id_to_root_id}")
    
    if new_child.ecs_id in EntityRegistry.ecs_id_to_root_id:
        assigned_root = EntityRegistry.ecs_id_to_root_id[new_child.ecs_id]
        print(f"   New child's assigned root: {assigned_root}")
        print(f"   Container's current root: {container.root_ecs_id}")
        print(f"   Root IDs match: {assigned_root == container.root_ecs_id}")
        
        # Check if assigned root exists in tree registry
        if assigned_root in EntityRegistry.tree_registry:
            assigned_tree = EntityRegistry.tree_registry[assigned_root]
            new_child_in_assigned_tree = new_child.ecs_id in assigned_tree.nodes
            print(f"   New child in assigned tree nodes: {new_child_in_assigned_tree}")
        else:
            print(f"   ❌ Assigned root {assigned_root} not found in tree registry!")

def debug_modified_entities(new_tree, old_tree, target_entity_id):
    """Debug what find_modified_entities is actually doing."""
    print(f"\n🔍 Debug: find_modified_entities() analysis for {target_entity_id}")
    
    # Compare node sets
    new_entity_ids = set(new_tree.nodes.keys())
    old_entity_ids = set(old_tree.nodes.keys())
    
    added_entities = new_entity_ids - old_entity_ids
    removed_entities = old_entity_ids - new_entity_ids
    common_entities = new_entity_ids & old_entity_ids
    
    print(f"   Added entities: {added_entities}")
    print(f"   Removed entities: {removed_entities}")
    print(f"   Common entities: {len(common_entities)}")
    print(f"   Target entity in added: {target_entity_id in added_entities}")
    print(f"   Target entity in common: {target_entity_id in common_entities}")
    
    if target_entity_id in added_entities:
        print("   ✅ Target should be detected as added entity")
    else:
        print("   ❌ Target not detected as added - this is the bug!")

def main():
    """Run the debug analysis."""
    debug_version_entity_process()

if __name__ == "__main__":
    main()