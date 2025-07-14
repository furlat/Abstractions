"""
Container Entity Bug - Isolated Test

This script isolates and demonstrates the exact container entity bug where:
1. New entities are added to properly typed container fields
2. The entity gets registered in ecs_id_to_root_id but NOT in tree nodes
3. Registry consistency validation fails

The bug is in field type detection for typed containers failing to detect entity types.
"""

import sys
sys.path.append('..')

from typing import List, Dict
from uuid import UUID
from pydantic import Field

# Import our entity system
from abstractions.ecs.entity import (
    Entity, EntityRegistry, build_entity_tree, 
    get_pydantic_field_type_entities
)

print("🔬 Container Entity Bug - Isolated Test")
print("=" * 50)

# Define test entities - same as failing test
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

def test_field_type_detection():
    """Test what get_pydantic_field_type_entities returns for our fields."""
    print("\n🔍 Step 1: Field Type Detection Analysis")
    print("-" * 40)
    
    container = ContainerEntity(name="TestContainer")
    
    # Test field type detection for empty containers
    list_field_type = get_pydantic_field_type_entities(container, "children_list")
    dict_field_type = get_pydantic_field_type_entities(container, "children_dict")
    
    print(f"📋 Empty children_list field type: {list_field_type}")
    print(f"📋 Empty children_dict field type: {dict_field_type}")
    
    # Add some entities and test again
    child1 = ChildEntity(name="Child1", data="data1")
    child2 = ChildEntity(name="Child2", data="data2")
    container.children_list = [child1, child2]
    container.children_dict = {"key1": child1, "key2": child2}
    
    list_field_type_populated = get_pydantic_field_type_entities(container, "children_list")
    dict_field_type_populated = get_pydantic_field_type_entities(container, "children_dict")
    
    print(f"📋 Populated children_list field type: {list_field_type_populated}")
    print(f"📋 Populated children_dict field type: {dict_field_type_populated}")
    
    return {
        "empty_list": list_field_type,
        "empty_dict": dict_field_type,
        "populated_list": list_field_type_populated,
        "populated_dict": dict_field_type_populated
    }

def test_tree_building_with_existing_entities():
    """Test tree building with pre-existing entities."""
    print("\n🔍 Step 2: Tree Building with Pre-existing Entities")
    print("-" * 40)
    
    clear_entity_registry()
    
    # Create container with existing entities
    container = ContainerEntity(name="Container")
    child1 = ChildEntity(name="ListChild1", data="data1")
    child2 = ChildEntity(name="ListChild2", data="data2") 
    child3 = ChildEntity(name="DictChild1", data="dict_data1")
    child4 = ChildEntity(name="DictChild2", data="dict_data2")
    
    container.children_list = [child1, child2]
    container.children_dict = {"key1": child3, "key2": child4}
    container.promote_to_root()
    
    tree = build_entity_tree(container)
    print(f"📊 Tree built with {tree.node_count} nodes")
    print(f"📊 Nodes: {list(tree.nodes.keys())}")
    
    # Check registry consistency
    registry_consistent = True
    for ecs_id, root_ecs_id in EntityRegistry.ecs_id_to_root_id.items():
        if ecs_id not in tree.nodes:
            print(f"❌ Entity {ecs_id} in registry but not in tree nodes")
            registry_consistent = False
    
    print(f"✅ Registry consistency: {'PASS' if registry_consistent else 'FAIL'}")
    return tree, registry_consistent

def test_adding_new_entity_to_container():
    """Test the exact failing scenario: adding new entity to existing container."""
    print("\n🔍 Step 3: Adding New Entity to Existing Container (THE BUG)")
    print("-" * 40)
    
    clear_entity_registry()
    
    # Create container with existing entities (same as step 2)
    container = ContainerEntity(name="Container")
    child1 = ChildEntity(name="ListChild1", data="data1")
    child2 = ChildEntity(name="ListChild2", data="data2")
    
    container.children_list = [child1, child2]
    container.promote_to_root()
    
    print("📝 Initial setup complete")
    
    # THIS IS THE CRITICAL STEP - add new entity to list
    new_child = ChildEntity(name="NewListChild", data="new_data")
    container.children_list.append(new_child)
    
    print(f"📝 Added new entity {new_child.ecs_id} to children_list")
    print(f"📝 Container children_list now has {len(container.children_list)} entities")
    
    # Test field type detection AFTER adding new entity
    field_type = get_pydantic_field_type_entities(container, "children_list")
    print(f"📋 Field type detected after adding: {field_type}")
    
    # Build new tree
    print("🔄 Building new tree...")
    new_tree = build_entity_tree(container)
    
    print(f"📊 New tree has {new_tree.node_count} nodes")
    print(f"📊 Nodes: {list(new_tree.nodes.keys())}")
    
    # Version the entity (this should register the new entity)
    print("🔄 Versioning entity...")
    EntityRegistry.version_entity(container)
    
    # Check registry mappings
    print("\n🔍 Registry Analysis:")
    print(f"📊 ecs_id_to_root_id entries: {len(EntityRegistry.ecs_id_to_root_id)}")
    print(f"📊 tree_registry entries: {len(EntityRegistry.tree_registry)}")
    
    # Check if new entity is in registry
    new_entity_in_registry = new_child.ecs_id in EntityRegistry.ecs_id_to_root_id
    print(f"📊 New entity in ecs_id_to_root_id: {new_entity_in_registry}")
    
    if new_entity_in_registry:
        root_id = EntityRegistry.ecs_id_to_root_id[new_child.ecs_id]
        print(f"📊 New entity's root_id: {root_id}")
        
        if root_id in EntityRegistry.tree_registry:
            tree = EntityRegistry.tree_registry[root_id]
            new_entity_in_tree_nodes = new_child.ecs_id in tree.nodes
            print(f"📊 New entity in tree nodes: {new_entity_in_tree_nodes}")
            
            if not new_entity_in_tree_nodes:
                print("❌ BUG CONFIRMED: Entity in registry but NOT in tree nodes!")
                return False
    
    print("✅ No bug detected in this scenario")
    return True

def main():
    """Run all isolated tests to identify the container entity bug."""
    
    # Step 1: Analyze field type detection
    field_types = test_field_type_detection()
    
    # Step 2: Test normal tree building
    tree, registry_ok = test_tree_building_with_existing_entities()
    
    # Step 3: Test the exact failing scenario
    bug_reproduced = not test_adding_new_entity_to_container()
    
    print("\n🎯 ANALYSIS SUMMARY")
    print("=" * 50)
    print(f"Field type detection for empty containers:")
    print(f"  - Empty list: {field_types['empty_list']}")
    print(f"  - Empty dict: {field_types['empty_dict']}")
    print(f"Field type detection for populated containers:")
    print(f"  - Populated list: {field_types['populated_list']}")
    print(f"  - Populated dict: {field_types['populated_dict']}")
    print(f"Registry consistency with pre-existing entities: {'✅ PASS' if registry_ok else '❌ FAIL'}")
    print(f"Container entity bug reproduced: {'✅ YES' if bug_reproduced else '❌ NO'}")
    
    if bug_reproduced:
        print("\n🚨 ROOT CAUSE IDENTIFIED:")
        print("When new entities are added to typed containers, the field type")
        print("detection fails, causing build_entity_tree() to skip container")
        print("processing, but the entity still gets registered in the registry.")
    else:
        print("\n🤔 Bug not reproduced - may need different conditions")

if __name__ == "__main__":
    main()