"""
ECS Versioning System Validation Examples

This demonstrates comprehensive testing of the entity versioning system across
different hierarchical depths and complexity scenarios to identify and validate
the ancestry path bugs and versioning consistency issues.

Test Categories:
- Basic versioning scenarios (flat entities)
- Hierarchical depth testing (2-5 levels deep)
- Multi-step versioning operations
- Ancestry path validation
- Edge cases and stress scenarios
"""

import sys
sys.path.append('..')

from typing import List, Dict, Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone
from pydantic import Field

# Import our entity system
from abstractions.ecs.entity import (
    Entity, EntityRegistry, build_entity_tree, find_modified_entities, 
    EntityTree, compare_non_entity_attributes
)

print("🔬 ECS Versioning System Validation")
print("=" * 50)

# Define test entities for hierarchical scenarios
class SimpleEntity(Entity):
    """Basic entity for simple versioning tests."""
    name: str = ""
    value: int = 0
    description: str = ""

class ParentEntity(Entity):
    """Parent entity containing child entities."""
    name: str = ""
    metadata: str = ""
    child: Optional['ChildEntity'] = None

class ChildEntity(Entity):
    """Child entity for hierarchy tests."""
    name: str = ""
    data: str = ""
    grandchild: Optional['GrandchildEntity'] = None

class GrandchildEntity(Entity):
    """Third level entity for deep hierarchy tests."""
    name: str = ""
    value: float = 0.0
    great_grandchild: Optional['GreatGrandchildEntity'] = None

class GreatGrandchildEntity(Entity):
    """Fourth level entity for very deep hierarchy tests."""
    name: str = ""
    final_value: str = ""

class ContainerEntity(Entity):
    """Entity with container fields for complex scenarios."""
    name: str = ""
    children_list: List[ChildEntity] = Field(default_factory=list)
    children_dict: Dict[str, ChildEntity] = Field(default_factory=dict)

# === VALIDATION HELPERS ===

def validate_ancestry_paths(tree: EntityTree, test_name: str) -> bool:
    """Validate that all ancestry paths are consistent with current entity IDs."""
    print(f"  🔍 Validating ancestry paths for {test_name}...")
    
    try:
        # Check 1: All entities in ancestry_paths exist in nodes
        for entity_id, path in tree.ancestry_paths.items():
            assert entity_id in tree.nodes, f"Entity {entity_id} in ancestry_paths but not in nodes"
            
            # Check 2: All IDs in each path exist in nodes
            for path_id in path:
                assert path_id in tree.nodes, f"Path entity {path_id} not found in nodes for entity {entity_id}"
        
        # Check 3: All nodes have ancestry paths
        for entity_id in tree.nodes:
            assert entity_id in tree.ancestry_paths, f"Entity {entity_id} in nodes but missing ancestry path"
        
        # Check 4: Root entity path consistency
        root_path = tree.ancestry_paths.get(tree.root_ecs_id, [])
        assert len(root_path) >= 1, f"Root entity {tree.root_ecs_id} has invalid path: {root_path}"
        assert root_path[0] == tree.root_ecs_id, f"Root path should start with root ID: {root_path}"
        
        print(f"  ✅ Ancestry paths valid for {test_name}")
        return True
        
    except AssertionError as e:
        print(f"  ❌ Ancestry path validation failed for {test_name}: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Unexpected error validating {test_name}: {e}")
        return False

def validate_registry_consistency(test_name: str) -> bool:
    """Validate that EntityRegistry mappings are consistent."""
    print(f"  🔍 Validating registry consistency for {test_name}...")
    
    try:
        # Check 1: All live_id_registry entries have valid entities
        for live_id, entity in EntityRegistry.live_id_registry.items():
            assert hasattr(entity, 'ecs_id'), f"Entity missing ecs_id: {entity}"
            assert hasattr(entity, 'live_id'), f"Entity missing live_id: {entity}"
            assert entity.live_id == live_id, f"Live ID mismatch: {entity.live_id} != {live_id}"
        
        # Check 2: All ecs_id_to_root_id mappings point to valid roots
        for ecs_id, root_ecs_id in EntityRegistry.ecs_id_to_root_id.items():
            assert root_ecs_id in EntityRegistry.tree_registry, f"Root {root_ecs_id} not in tree_registry"
            tree = EntityRegistry.tree_registry[root_ecs_id]
            assert ecs_id in tree.nodes, f"Entity {ecs_id} not found in its root tree {root_ecs_id}"
        
        # Check 3: Tree registry consistency
        for root_ecs_id, tree in EntityRegistry.tree_registry.items():
            assert tree.root_ecs_id == root_ecs_id, f"Tree root mismatch: {tree.root_ecs_id} != {root_ecs_id}"
            assert root_ecs_id in tree.nodes, f"Root entity not in its own tree nodes"
        
        print(f"  ✅ Registry consistency valid for {test_name}")
        return True
        
    except AssertionError as e:
        print(f"  ❌ Registry consistency failed for {test_name}: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Unexpected registry error for {test_name}: {e}")
        return False

def print_tree_state(tree: EntityTree, title: str):
    """Print detailed tree state for debugging."""
    print(f"  📊 {title}")
    print(f"    Root ECS ID: {tree.root_ecs_id}")
    print(f"    Nodes ({len(tree.nodes)}): {list(tree.nodes.keys())}")
    print(f"    Ancestry Paths ({len(tree.ancestry_paths)}):")
    for entity_id, path in tree.ancestry_paths.items():
        print(f"      {entity_id}: {path}")

# === TEST SCENARIO 1: BASIC VERSIONING ===

def test_basic_versioning():
    """Test basic versioning with flat entities."""
    print("\n🧪 Test 1A: Basic Versioning - Single Step (Flat Entities)")
    print("-" * 40)
    
    try:
        # Create simple entity
        entity = SimpleEntity(name="Original", value=100, description="Initial state")
        entity.promote_to_root()
        
        original_ecs_id = entity.ecs_id
        original_tree = build_entity_tree(entity)
        
        print(f"  📝 Created entity: {original_ecs_id}")
        validate_ancestry_paths(original_tree, "initial creation")
        validate_registry_consistency("initial creation")
        
        # Modify entity AGGRESSIVELY to force versioning
        entity.name = "Modified"
        entity.value = 200
        entity.description = "Aggressively modified to force versioning"
        
        # Build new tree and force versioning through diffing
        new_tree = build_entity_tree(entity)
        old_stored_tree = None
        if entity.root_ecs_id is not None:
            old_stored_tree = EntityRegistry.get_stored_tree(entity.root_ecs_id)
        
        if old_stored_tree:
            modified_entities = find_modified_entities(new_tree, old_stored_tree)
            print(f"  🔍 Modified entities detected: {len(modified_entities)}")
        
        # Version the entity
        print("  🔄 Versioning entity after modification...")
        version_success = EntityRegistry.version_entity(entity)
        
        new_ecs_id = entity.ecs_id
        versioned_tree = build_entity_tree(entity)
        
        print(f"  📝 New entity ID: {new_ecs_id}")
        print(f"  ✅ ECS ID changed: {original_ecs_id != new_ecs_id}")
        print(f"  ✅ Versioning triggered: {version_success}")
        
        # Validate ancestry paths after versioning
        ancestry_valid = validate_ancestry_paths(versioned_tree, "after basic versioning")
        registry_valid = validate_registry_consistency("after basic versioning")
        
        print_tree_state(versioned_tree, "Post-versioning tree state")
        
        assert ancestry_valid, "Ancestry paths should be valid after basic versioning"
        assert registry_valid, "Registry should be consistent after basic versioning"
        
        print("  ✅ Basic versioning test PASSED")
        return True
        
    except Exception as e:
        print(f"  ❌ Basic versioning test FAILED: {e}")
        return False

def test_basic_versioning_multi_step():
    """Test basic versioning with MULTI-STEP operations - this should expose ancestry path bugs."""
    print("\n🧪 Test 1B: Basic Versioning - Multi-Step (Ancestry Path Bug Detection)")
    print("-" * 40)
    
    try:
        # Create simple entity
        entity = SimpleEntity(name="MultiStep", value=100, description="Multi-step test")
        entity.promote_to_root()
        
        step1_ecs_id = entity.ecs_id
        print(f"  📝 Initial entity: {step1_ecs_id}")
        
        # === STEP 1: First versioning ===
        print("  🔄 STEP 1: First modification and versioning...")
        entity.name = "Step1_Modified"
        entity.value = 200
        
        EntityRegistry.version_entity(entity)
        step2_ecs_id = entity.ecs_id
        step2_tree = build_entity_tree(entity)
        
        print(f"  📝 After Step 1: {step2_ecs_id}")
        print(f"  ✅ Step 1 ECS ID changed: {step1_ecs_id != step2_ecs_id}")
        
        step1_ancestry_valid = validate_ancestry_paths(step2_tree, "after step 1")
        step1_registry_valid = validate_registry_consistency("after step 1")
        
        print_tree_state(step2_tree, "After Step 1 tree state")
        
        # === STEP 2: Second versioning (THE CRITICAL TEST) ===
        print("  🔄 STEP 2: Second modification and versioning (CRITICAL TEST)...")
        entity.name = "Step2_Modified"
        entity.value = 300
        entity.description = "Second round modification - testing ancestry paths"
        
        # This is where the ancestry path bug should manifest
        try:
            EntityRegistry.version_entity(entity)
            step3_ecs_id = entity.ecs_id
            step3_tree = build_entity_tree(entity)
            
            print(f"  📝 After Step 2: {step3_ecs_id}")
            print(f"  ✅ Step 2 ECS ID changed: {step2_ecs_id != step3_ecs_id}")
            
            # CRITICAL: Validate that ancestry paths reference current IDs
            step2_ancestry_valid = validate_ancestry_paths(step3_tree, "after step 2")
            step2_registry_valid = validate_registry_consistency("after step 2")
            
            print_tree_state(step3_tree, "After Step 2 tree state")
            
            # Test diffing between step 1 and step 2 trees
            print("  🔍 Testing diffing between step 1 and step 2...")
            modified_entities = find_modified_entities(step3_tree, step2_tree)
            print(f"    Modified entities between steps: {len(modified_entities)}")
            
            all_valid = step1_ancestry_valid and step1_registry_valid and step2_ancestry_valid and step2_registry_valid
            
            if all_valid:
                print("  ✅ Multi-step basic versioning test PASSED")
                return True
            else:
                print("  ❌ Multi-step basic versioning test FAILED - validation errors")
                return False
                
        except Exception as step2_error:
            print(f"  ❌ STEP 2 FAILED - This likely indicates the ancestry path bug: {step2_error}")
            return False
        
    except Exception as e:
        print(f"  ❌ Multi-step basic versioning test FAILED: {e}")
        return False

# === TEST SCENARIO 2: HIERARCHICAL DEPTH TESTING ===

def test_hierarchical_versioning():
    """Test versioning with 2-4 level hierarchies - Single Step."""
    print("\n🧪 Test 2A: Hierarchical Versioning - Single Step (2-4 Levels Deep)")
    print("-" * 40)
    
    results = []
    
    # Test 2-level hierarchy
    try:
        print("  📚 Testing 2-level hierarchy...")
        parent = ParentEntity(name="Parent", metadata="parent data")
        child = ChildEntity(name="Child", data="child data")
        parent.child = child
        parent.promote_to_root()
        
        original_parent_id = parent.ecs_id
        original_child_id = child.ecs_id
        original_tree = build_entity_tree(parent)
        
        validate_ancestry_paths(original_tree, "2-level initial")
        print_tree_state(original_tree, "Initial 2-level tree")
        
        # Modify child
        child.data = "modified child data"
        EntityRegistry.version_entity(parent)
        
        new_tree = build_entity_tree(parent)
        ancestry_valid = validate_ancestry_paths(new_tree, "2-level versioned")
        registry_valid = validate_registry_consistency("2-level versioned")
        
        print_tree_state(new_tree, "Versioned 2-level tree")
        
        assert ancestry_valid, "2-level ancestry paths should be valid"
        assert registry_valid, "2-level registry should be consistent"
        print("  ✅ 2-level hierarchy test PASSED")
        results.append(True)
        
    except Exception as e:
        print(f"  ❌ 2-level hierarchy test FAILED: {e}")
        results.append(False)
    
    # Test 3-level hierarchy
    try:
        print("  📚 Testing 3-level hierarchy...")
        parent = ParentEntity(name="Parent", metadata="parent data")
        child = ChildEntity(name="Child", data="child data")
        grandchild = GrandchildEntity(name="Grandchild", value=42.0)
        
        child.grandchild = grandchild
        parent.child = child
        parent.promote_to_root()
        
        original_tree = build_entity_tree(parent)
        validate_ancestry_paths(original_tree, "3-level initial")
        
        # Modify grandchild
        grandchild.value = 84.0
        EntityRegistry.version_entity(parent)
        
        new_tree = build_entity_tree(parent)
        ancestry_valid = validate_ancestry_paths(new_tree, "3-level versioned")
        registry_valid = validate_registry_consistency("3-level versioned")
        
        assert ancestry_valid, "3-level ancestry paths should be valid"
        assert registry_valid, "3-level registry should be consistent"
        print("  ✅ 3-level hierarchy test PASSED")
        results.append(True)
        
    except Exception as e:
        print(f"  ❌ 3-level hierarchy test FAILED: {e}")
        results.append(False)
    
    # Test 4-level hierarchy  
    try:
        print("  📚 Testing 4-level hierarchy...")
        parent = ParentEntity(name="Parent", metadata="parent data")
        child = ChildEntity(name="Child", data="child data")
        grandchild = GrandchildEntity(name="Grandchild", value=42.0)
        great_grandchild = GreatGrandchildEntity(name="GreatGrandchild", final_value="deep")
        
        grandchild.great_grandchild = great_grandchild
        child.grandchild = grandchild
        parent.child = child
        parent.promote_to_root()
        
        original_tree = build_entity_tree(parent)
        validate_ancestry_paths(original_tree, "4-level initial")
        
        # Modify deep entity
        great_grandchild.final_value = "very deep modified"
        EntityRegistry.version_entity(parent)
        
        new_tree = build_entity_tree(parent)
        ancestry_valid = validate_ancestry_paths(new_tree, "4-level versioned")
        registry_valid = validate_registry_consistency("4-level versioned")
        
        assert ancestry_valid, "4-level ancestry paths should be valid"
        assert registry_valid, "4-level registry should be consistent"
        print("  ✅ 4-level hierarchy test PASSED")
        results.append(True)
        
    except Exception as e:
        print(f"  ❌ 4-level hierarchy test FAILED: {e}")
        results.append(False)
    
    passed = sum(results)
    total = len(results)
    print(f"  📊 Hierarchical single-step tests: {passed}/{total} passed")
    return all(results)

def test_hierarchical_versioning_multi_step():
    """Test versioning with 2-4 level hierarchies - Multi-Step to expose ancestry path bugs."""
    print("\n🧪 Test 2B: Hierarchical Versioning - Multi-Step (Ancestry Path Bug Detection)")
    print("-" * 40)
    
    try:
        # Create 3-level hierarchy for thorough testing
        print("  📚 Testing 3-level hierarchy with multi-step versioning...")
        parent = ParentEntity(name="MultiStepParent", metadata="initial")
        child = ChildEntity(name="MultiStepChild", data="initial")
        grandchild = GrandchildEntity(name="MultiStepGrandchild", value=1.0)
        
        child.grandchild = grandchild
        parent.child = child
        parent.promote_to_root()
        
        initial_parent_id = parent.ecs_id
        initial_child_id = child.ecs_id
        initial_grandchild_id = grandchild.ecs_id
        
        print(f"  📝 Initial hierarchy: P:{initial_parent_id} -> C:{initial_child_id} -> G:{initial_grandchild_id}")
        
        # === STEP 1: First versioning (modify grandchild) ===
        print("  🔄 STEP 1: Modify grandchild and version hierarchy...")
        grandchild.value = 2.0
        grandchild.name = "Step1_Modified"
        
        EntityRegistry.version_entity(parent)
        
        step1_parent_id = parent.ecs_id
        step1_child_id = child.ecs_id
        step1_grandchild_id = grandchild.ecs_id
        step1_tree = build_entity_tree(parent)
        
        print(f"  📝 After Step 1: P:{step1_parent_id} -> C:{step1_child_id} -> G:{step1_grandchild_id}")
        
        step1_ancestry_valid = validate_ancestry_paths(step1_tree, "hierarchical step 1")
        step1_registry_valid = validate_registry_consistency("hierarchical step 1")
        
        print_tree_state(step1_tree, "Hierarchical Step 1 tree state")
        
        # === STEP 2: Second versioning (modify child) ===
        print("  🔄 STEP 2: Modify child and version hierarchy (CRITICAL TEST)...")
        child.data = "Step2_Modified"
        child.name = "Step2_Child"
        
        try:
            EntityRegistry.version_entity(parent)
            
            step2_parent_id = parent.ecs_id
            step2_child_id = child.ecs_id
            step2_grandchild_id = grandchild.ecs_id
            step2_tree = build_entity_tree(parent)
            
            print(f"  📝 After Step 2: P:{step2_parent_id} -> C:{step2_child_id} -> G:{step2_grandchild_id}")
            
            step2_ancestry_valid = validate_ancestry_paths(step2_tree, "hierarchical step 2")
            step2_registry_valid = validate_registry_consistency("hierarchical step 2")
            
            print_tree_state(step2_tree, "Hierarchical Step 2 tree state")
            
            # === STEP 3: Third versioning (modify parent) ===
            print("  🔄 STEP 3: Modify parent and version hierarchy (TRIPLE ANCESTRY TEST)...")
            parent.metadata = "Step3_Modified"
            parent.name = "Step3_Parent"
            
            EntityRegistry.version_entity(parent)
            
            step3_parent_id = parent.ecs_id
            step3_child_id = child.ecs_id
            step3_grandchild_id = grandchild.ecs_id
            step3_tree = build_entity_tree(parent)
            
            print(f"  📝 After Step 3: P:{step3_parent_id} -> C:{step3_child_id} -> G:{step3_grandchild_id}")
            
            step3_ancestry_valid = validate_ancestry_paths(step3_tree, "hierarchical step 3")
            step3_registry_valid = validate_registry_consistency("hierarchical step 3")
            
            # Test diffing between different steps
            print("  🔍 Testing diffing between hierarchical steps...")
            try:
                modified_1_to_2 = find_modified_entities(step2_tree, step1_tree)
                modified_2_to_3 = find_modified_entities(step3_tree, step2_tree)
                print(f"    Modified entities step 1->2: {len(modified_1_to_2)}")
                print(f"    Modified entities step 2->3: {len(modified_2_to_3)}")
                diffing_valid = True
            except Exception as diff_error:
                print(f"    ❌ Diffing failed: {diff_error}")
                diffing_valid = False
            
            all_valid = (step1_ancestry_valid and step1_registry_valid and 
                        step2_ancestry_valid and step2_registry_valid and 
                        step3_ancestry_valid and step3_registry_valid and 
                        diffing_valid)
            
            if all_valid:
                print("  ✅ Multi-step hierarchical versioning test PASSED")
                return True
            else:
                print("  ❌ Multi-step hierarchical versioning test FAILED - validation errors")
                return False
                
        except Exception as step_error:
            print(f"  ❌ Hierarchical multi-step FAILED: {step_error}")
            return False
        
    except Exception as e:
        print(f"  ❌ Multi-step hierarchical versioning test FAILED: {e}")
        return False

# === TEST SCENARIO 3: MULTI-STEP VERSIONING ===

def test_multi_step_versioning():
    """Test multiple versioning operations in sequence."""
    print("\n🧪 Test 3: Multi-Step Versioning Operations")
    print("-" * 40)
    
    try:
        # Create complex hierarchy
        parent = ParentEntity(name="MultiStep Parent", metadata="step 0")
        child = ChildEntity(name="MultiStep Child", data="step 0")
        grandchild = GrandchildEntity(name="MultiStep Grandchild", value=0.0)
        
        child.grandchild = grandchild
        parent.child = child
        parent.promote_to_root()
        
        step_results = []
        
        # Step 1: Modify parent
        print("  🔄 Step 1: Modify parent...")
        parent.metadata = "step 1"
        EntityRegistry.version_entity(parent)
        
        tree_1 = build_entity_tree(parent)
        step1_valid = validate_ancestry_paths(tree_1, "step 1") and validate_registry_consistency("step 1")
        step_results.append(step1_valid)
        print(f"  {'✅' if step1_valid else '❌'} Step 1 validation")
        
        # Step 2: Modify child
        print("  🔄 Step 2: Modify child...")
        child.data = "step 2"
        EntityRegistry.version_entity(parent)
        
        tree_2 = build_entity_tree(parent)
        step2_valid = validate_ancestry_paths(tree_2, "step 2") and validate_registry_consistency("step 2")
        step_results.append(step2_valid)
        print(f"  {'✅' if step2_valid else '❌'} Step 2 validation")
        
        # Step 3: Modify grandchild
        print("  🔄 Step 3: Modify grandchild...")
        grandchild.value = 3.0
        EntityRegistry.version_entity(parent)
        
        tree_3 = build_entity_tree(parent)
        step3_valid = validate_ancestry_paths(tree_3, "step 3") and validate_registry_consistency("step 3")
        step_results.append(step3_valid)
        print(f"  {'✅' if step3_valid else '❌'} Step 3 validation")
        
        # Step 4: Modify multiple entities
        print("  🔄 Step 4: Modify multiple entities...")
        parent.metadata = "step 4"
        child.data = "step 4"
        grandchild.value = 4.0
        EntityRegistry.version_entity(parent)
        
        tree_4 = build_entity_tree(parent)
        step4_valid = validate_ancestry_paths(tree_4, "step 4") and validate_registry_consistency("step 4")
        step_results.append(step4_valid)
        print(f"  {'✅' if step4_valid else '❌'} Step 4 validation")
        
        # Step 5: Test diffing between steps
        print("  🔄 Step 5: Test diffing between versions...")
        try:
            # This should expose the ancestry path bug if it exists
            modified_entities = find_modified_entities(tree_4, tree_1)
            print(f"    Modified entities detected: {len(modified_entities)}")
            step5_valid = True
        except Exception as e:
            print(f"    ❌ Diffing failed: {e}")
            step5_valid = False
        
        step_results.append(step5_valid)
        print(f"  {'✅' if step5_valid else '❌'} Step 5 validation")
        
        all_valid = all(step_results)
        print(f"  📊 Multi-step validation: {sum(step_results)}/{len(step_results)} steps passed")
        
        if all_valid:
            print("  ✅ Multi-step versioning test PASSED")
        else:
            print("  ❌ Multi-step versioning test FAILED")
            
        return all_valid
        
    except Exception as e:
        print(f"  ❌ Multi-step versioning test FAILED: {e}")
        return False

# === TEST SCENARIO 4: CONTAINER ENTITY VERSIONING ===

def test_container_versioning():
    """Test versioning with container fields (lists, dicts)."""
    print("\n🧪 Test 4: Container Entity Versioning")
    print("-" * 40)
    
    try:
        # Create container entity
        container = ContainerEntity(name="Container")
        
        # Add entities to list
        child1 = ChildEntity(name="ListChild1", data="data1")
        child2 = ChildEntity(name="ListChild2", data="data2")
        container.children_list = [child1, child2]
        
        # Add entities to dict
        child3 = ChildEntity(name="DictChild1", data="dict_data1")
        child4 = ChildEntity(name="DictChild2", data="dict_data2")
        container.children_dict = {"key1": child3, "key2": child4}
        
        container.promote_to_root()
        
        original_tree = build_entity_tree(container)
        print(f"  📝 Created container with {original_tree.node_count} entities")
        
        initial_valid = validate_ancestry_paths(original_tree, "container initial")
        assert initial_valid, "Initial container tree should be valid"
        
        # Modify list child
        print("  🔄 Modifying list child...")
        child1.data = "modified_data1"
        EntityRegistry.version_entity(container)
        
        tree_after_list = build_entity_tree(container)
        list_valid = validate_ancestry_paths(tree_after_list, "after list modification")
        registry_list_valid = validate_registry_consistency("after list modification")
        
        assert list_valid and registry_list_valid, "Tree should be valid after list modification"
        
        # Modify dict child
        print("  🔄 Modifying dict child...")
        child3.data = "modified_dict_data1"
        EntityRegistry.version_entity(container)
        
        tree_after_dict = build_entity_tree(container)
        dict_valid = validate_ancestry_paths(tree_after_dict, "after dict modification")
        registry_dict_valid = validate_registry_consistency("after dict modification")
        
        assert dict_valid and registry_dict_valid, "Tree should be valid after dict modification"
        
        # Add new child to list
        print("  🔄 Adding new child to list...")
        new_child = ChildEntity(name="NewListChild", data="new_data")
        container.children_list.append(new_child)
        EntityRegistry.version_entity(container)
        
        tree_after_add = build_entity_tree(container)
        add_valid = validate_ancestry_paths(tree_after_add, "after adding child")
        registry_add_valid = validate_registry_consistency("after adding child")
        
        assert add_valid and registry_add_valid, "Tree should be valid after adding child"
        
        print("  ✅ Container versioning test PASSED")
        return True
        
    except Exception as e:
        print(f"  ❌ Container versioning test FAILED: {e}")
        return False

# === TEST SCENARIO 5: EDGE CASES AND STRESS TEST ===

def test_edge_cases():
    """Test edge cases and stress scenarios."""
    print("\n🧪 Test 5: Edge Cases and Stress Scenarios") 
    print("-" * 40)
    
    edge_results = []
    
    # Edge Case 1: Empty entity versioning
    try:
        print("  🧪 Edge Case 1: Empty entity...")
        empty = SimpleEntity()
        empty.promote_to_root()
        EntityRegistry.version_entity(empty)
        
        empty_tree = build_entity_tree(empty)
        empty_valid = validate_ancestry_paths(empty_tree, "empty entity")
        edge_results.append(empty_valid)
        print(f"  {'✅' if empty_valid else '❌'} Empty entity test")
        
    except Exception as e:
        print(f"  ❌ Empty entity test FAILED: {e}")
        edge_results.append(False)
    
    # Edge Case 2: Rapid successive versioning
    try:
        print("  🧪 Edge Case 2: Rapid successive versioning...")
        rapid = SimpleEntity(name="Rapid", value=0)
        rapid.promote_to_root()
        
        for i in range(5):
            rapid.value = i * 10
            EntityRegistry.version_entity(rapid)
            tree = build_entity_tree(rapid)
            if not validate_ancestry_paths(tree, f"rapid step {i}"):
                raise Exception(f"Validation failed at step {i}")
        
        edge_results.append(True)
        print("  ✅ Rapid versioning test PASSED")
        
    except Exception as e:
        print(f"  ❌ Rapid versioning test FAILED: {e}")
        edge_results.append(False)
    
    # Edge Case 3: Complex hierarchy modifications
    try:
        print("  🧪 Edge Case 3: Complex hierarchy modifications...")
        
        # Create complex structure
        root = ParentEntity(name="ComplexRoot")
        level1 = ChildEntity(name="Level1")
        level2 = GrandchildEntity(name="Level2", value=1.0)
        level3 = GreatGrandchildEntity(name="Level3", final_value="initial")
        
        level2.great_grandchild = level3
        level1.grandchild = level2
        root.child = level1
        root.promote_to_root()
        
        # Swap a deep child
        new_level3 = GreatGrandchildEntity(name="NewLevel3", final_value="swapped")
        level2.great_grandchild = new_level3
        EntityRegistry.version_entity(root)
        
        complex_tree = build_entity_tree(root)
        complex_valid = validate_ancestry_paths(complex_tree, "complex hierarchy")
        edge_results.append(complex_valid)
        print(f"  {'✅' if complex_valid else '❌'} Complex hierarchy test")
        
    except Exception as e:
        print(f"  ❌ Complex hierarchy test FAILED: {e}")
        edge_results.append(False)
    
    passed = sum(edge_results)
    total = len(edge_results)
    print(f"  📊 Edge case tests: {passed}/{total} passed")
    
    return all(edge_results)

# === MAIN TEST EXECUTION ===

def clear_entity_registry():
    """Manually clear the EntityRegistry for testing."""
    EntityRegistry.tree_registry.clear()
    EntityRegistry.lineage_registry.clear()
    EntityRegistry.live_id_registry.clear()
    EntityRegistry.ecs_id_to_root_id.clear()
    EntityRegistry.type_registry.clear()

def run_all_tests():
    """Run all versioning validation tests."""
    print("\n🚀 Running All Versioning Validation Tests")
    print("=" * 50)
    
    # Clear registry to start fresh
    clear_entity_registry()
    
    test_results = []
    
    # Run all test scenarios
    test_results.append(test_basic_versioning())
    test_results.append(test_basic_versioning_multi_step())
    test_results.append(test_hierarchical_versioning())
    test_results.append(test_hierarchical_versioning_multi_step())
    test_results.append(test_multi_step_versioning())
    test_results.append(test_container_versioning())
    test_results.append(test_edge_cases())
    
    # Summary
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"\n📊 FINAL RESULTS: {passed}/{total} test scenarios passed")
    
    if all(test_results):
        print("🎉 ALL TESTS PASSED - Versioning system is working correctly!")
    else:
        print("⚠️  SOME TESTS FAILED - Versioning bugs detected!")
        print("🔍 Check the failed test outputs above for specific issues")
    
    return all(test_results)

if __name__ == "__main__":
    run_all_tests()