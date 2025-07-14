#!/usr/bin/env python3
"""
Pure ConfigEntity + Multi-Output Bug Demonstration

This script demonstrates the edge case where Pure ConfigEntity functions 
that return multiple entities are not properly handled by the CallableRegistry.

EXPECTED BEHAVIOR:
- Function should return multiple entities with sibling relationships
- Multi-entity unpacking should work properly
- All entities should be properly registered

ACTUAL BEHAVIOR (BUG):
- Only single entity is returned
- Multi-entity processing is completely bypassed  
- Sibling relationships are never established
- Function result is treated as single entity only

Run with: python pure_config_multi_output_bug_demo.py
"""

import sys
import os
from typing import Tuple, List
from uuid import uuid4

# Add the abstractions directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from abstractions.ecs.entity import Entity, EntityRegistry, ConfigEntity
from abstractions.ecs.callable_registry import CallableRegistry

def log_section(title: str):
    """Clean section logging."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")

# Define entities for our test case
class AnalysisReport(Entity):
    """Analysis report entity."""
    title: str
    content: str
    report_type: str = "analysis"

class DataSummary(Entity):
    """Data summary entity."""
    total_records: int
    summary_text: str
    confidence_score: float

class VisualizationChart(Entity):
    """Visualization chart entity.""" 
    chart_type: str
    data_points: List[float]
    chart_title: str

# Define ConfigEntity for the function
class AnalysisConfig(ConfigEntity):
    """Configuration for analysis generation."""
    analysis_depth: str = "standard"
    include_charts: bool = True
    confidence_threshold: float = 0.8
    report_format: str = "detailed"

# PURE CONFIGENTITY FUNCTION THAT RETURNS MULTIPLE ENTITIES
@CallableRegistry.register("generate_analysis_suite")
def generate_analysis_suite(config: AnalysisConfig) -> Tuple[AnalysisReport, DataSummary, VisualizationChart]:
    """
    Pure ConfigEntity function that should return 3 entities with sibling relationships.
    
    This is the exact pattern that triggers the bug:
    - Only ConfigEntity parameters (no regular entities)
    - Returns multiple entities (Tuple[Entity, Entity, Entity])
    - Should trigger multi-entity processing but doesn't
    """
    print(f"🔬 Generating analysis suite with config: {config.analysis_depth}")
    
    # Create the three entities that should be siblings
    report = AnalysisReport(
        title=f"{config.analysis_depth.title()} Analysis Report",
        content=f"Comprehensive {config.analysis_depth} analysis completed with {config.report_format} format.",
        report_type=config.analysis_depth
    )
    
    summary = DataSummary(
        total_records=1500,
        summary_text=f"Analysis processed 1500 records with {config.confidence_threshold} confidence threshold.",
        confidence_score=config.confidence_threshold
    )
    
    chart = None
    if config.include_charts:
        chart = VisualizationChart(
            chart_type="line",
            data_points=[1.2, 2.3, 3.1, 4.7, 5.2],
            chart_title=f"{config.analysis_depth.title()} Trend Analysis"
        )
    else:
        chart = VisualizationChart(
            chart_type="placeholder",
            data_points=[],
            chart_title="No Chart Requested"
        )
    
    print(f"✅ Created 3 entities: Report, Summary, Chart")
    print(f"   Report ID: {report.ecs_id}")
    print(f"   Summary ID: {summary.ecs_id}")  
    print(f"   Chart ID: {chart.ecs_id}")
    
    # Return tuple of 3 entities - should trigger multi-entity processing
    return report, summary, chart

def test_pure_config_multi_output_bug():
    """Test that demonstrates the Pure ConfigEntity + Multi-Output bug."""
    
    log_section("Pure ConfigEntity + Multi-Output Bug Demonstration")
    
    print("🎯 Testing Pure ConfigEntity function with multi-entity return...")
    print("Function: generate_analysis_suite(config: AnalysisConfig) -> Tuple[Report, Summary, Chart]")
    
    # Create configuration entity
    config = AnalysisConfig(
        analysis_depth="comprehensive",
        include_charts=True,
        confidence_threshold=0.9,
        report_format="detailed"
    )
    config.promote_to_root()
    print(f"✅ Created config: {config.ecs_id}")
    
    # Get function metadata to inspect expected behavior
    metadata = CallableRegistry.get_metadata("generate_analysis_suite")
    print(f"\n📊 Function Metadata Analysis:")
    
    if metadata:
        print(f"   supports_unpacking: {metadata.supports_unpacking}")
        print(f"   expected_output_count: {metadata.expected_output_count}")
        print(f"   output_pattern: {metadata.output_pattern}")
        print(f"   input_entity_class: {metadata.input_entity_class}")
        print(f"   uses_config_entity: {metadata.uses_config_entity}")
        
        if metadata.supports_unpacking:
            print("✅ Function SHOULD support multi-entity unpacking")
        else:
            print("❌ Function does NOT support multi-entity unpacking (unexpected)")
    else:
        print("❌ ERROR: Function metadata not found!")
        return
    
    # Execute the function
    print(f"\n🚀 Executing function...")
    result = CallableRegistry.execute("generate_analysis_suite", config=config)
    
    # Analyze the result
    print(f"\n🔍 Result Analysis:")
    print(f"   Result type: {type(result)}")
    
    if isinstance(result, list):
        print(f"✅ CORRECT: Got list of {len(result)} entities")
        if len(result) == 3:
            print("✅ CORRECT: All 3 entities returned")
            
            # Check sibling relationships
            first_entity = result[0]
            if hasattr(first_entity, 'sibling_output_entities'):
                if first_entity.sibling_output_entities:
                    print("✅ CORRECT: Sibling relationships established")
                    print(f"   First entity siblings: {len(first_entity.sibling_output_entities)}")
                else:
                    print("❌ BUG: No sibling relationships found")
            else:
                print("❌ BUG: No sibling_output_entities attribute")
                
            # Check execution tracking
            if hasattr(first_entity, 'derived_from_execution_id'):
                if first_entity.derived_from_execution_id:
                    print("✅ CORRECT: Execution tracking present")
                    execution_id = first_entity.derived_from_execution_id
                    
                    # Check if all entities share same execution ID
                    all_same_execution = all(
                        hasattr(entity, 'derived_from_execution_id') and 
                        entity.derived_from_execution_id == execution_id 
                        for entity in result
                    )
                    if all_same_execution:
                        print("✅ CORRECT: All entities share same execution ID")
                    else:
                        print("❌ BUG: Entities have different execution IDs")
                else:
                    print("❌ BUG: No execution ID tracking")
            else:
                print("❌ BUG: No derived_from_execution_id attribute")
        else:
            print(f"❌ BUG: Expected 3 entities, got {len(result)}")
    else:
        # Single entity returned - this is the bug
        print(f"❌ BUG: Got single entity instead of list")
        print(f"   Entity type: {result.__class__.__name__}")
        print(f"   Entity ID: {result.ecs_id}")
        
        # Check if it's wrapping all the data in a single entity
        print(f"\n🔍 Analyzing single entity content:")
        entity_fields = [f for f in result.model_fields.keys() 
                        if f not in {'ecs_id', 'live_id', 'created_at', 'forked_at',
                                   'previous_ecs_id', 'lineage_id', 'old_ids', 'old_ecs_id',
                                   'root_ecs_id', 'root_live_id', 'from_storage',
                                   'untyped_data', 'attribute_source'}]
        for field in entity_fields:
            value = getattr(result, field, None)
            print(f"   {field}: {type(value)} = {value}")
    
    # Check registry state
    print(f"\n📚 Registry State:")
    print(f"   Trees registered: {len(EntityRegistry.tree_registry)}")
    print(f"   Live entities: {len(EntityRegistry.live_id_registry)}")
    
    # Look for function execution records
    execution_entities = []
    for tree_id in EntityRegistry.tree_registry:
        tree = EntityRegistry.get_stored_tree(tree_id)
        if tree:
            for node_id in tree.nodes:
                entity = EntityRegistry.get_stored_entity(tree_id, node_id)
                if entity and hasattr(entity, 'function_name'):
                    if getattr(entity, 'function_name', None) == "generate_analysis_suite":
                        execution_entities.append(entity)
    
    print(f"   Function execution records: {len(execution_entities)}")
    for exec_entity in execution_entities:
        if hasattr(exec_entity, 'was_unpacked'):
            print(f"   Execution was_unpacked: {getattr(exec_entity, 'was_unpacked', 'N/A')}")
        if hasattr(exec_entity, 'entity_count_output'):
            print(f"   Execution output count: {getattr(exec_entity, 'entity_count_output', 'N/A')}")

def test_comparison_with_normal_multi_output():
    """Test comparison with a normal multi-entity function to show the difference."""
    
    log_section("Comparison: Normal Multi-Entity Function")
    
    # Define a function that takes entities and returns multiple entities
    @CallableRegistry.register("process_entities")
    def process_entities(report: AnalysisReport) -> Tuple[DataSummary, VisualizationChart]:
        """Normal function that takes entity input and returns multiple entities."""
        print("🔄 Processing entity into multiple outputs...")
        
        summary = DataSummary(
            total_records=100,
            summary_text=f"Processed report: {report.title}",
            confidence_score=0.95
        )
        
        chart = VisualizationChart(
            chart_type="bar",
            data_points=[1.0, 2.0, 3.0],
            chart_title=f"Chart for {report.title}"
        )
        
        return summary, chart
    
    # Create input entity
    input_report = AnalysisReport(
        title="Test Report",
        content="Test content for multi-entity processing",
        report_type="test"
    )
    input_report.promote_to_root()
    
    print(f"✅ Created input entity: {input_report.ecs_id}")
    
    # Execute normal function
    print(f"\n🚀 Executing normal multi-entity function...")
    normal_result = CallableRegistry.execute("process_entities", report=input_report)
    
    print(f"\n🔍 Normal Function Result Analysis:")
    print(f"   Result type: {type(normal_result)}")
    
    if isinstance(normal_result, list):
        print(f"✅ Got list of {len(normal_result)} entities (expected)")
        if len(normal_result) > 0 and hasattr(normal_result[0], 'sibling_output_entities'):
            if normal_result[0].sibling_output_entities:
                print("✅ Normal function HAS sibling relationships")
            else:
                print("❌ Normal function missing sibling relationships")
    else:
        print(f"❌ Normal function also broken: {type(normal_result)}")

def main():
    """Main test runner."""
    print("🧪 Pure ConfigEntity + Multi-Output Bug Demonstration")
    print("=" * 80)
    
    try:
        # Test the bug
        test_pure_config_multi_output_bug()
        
        # Compare with normal behavior
        test_comparison_with_normal_multi_output()
        
        log_section("Bug Summary")
        print("🎯 EXPECTED: Pure ConfigEntity functions with multi-entity returns")
        print("   should work the same as normal multi-entity functions")
        print("")
        print("❌ ACTUAL BUG: Pure ConfigEntity multi-entity returns are broken")
        print("   - Only single entity returned instead of list")
        print("   - No sibling relationships established")
        print("   - Multi-entity processing completely bypassed")
        print("")
        print("📍 ROOT CAUSE: _execute_with_partial() lines 593-628")
        print("   Pure ConfigEntity path ignores supports_unpacking metadata")
        print("   Never routes to _finalize_multi_entity_result()")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()