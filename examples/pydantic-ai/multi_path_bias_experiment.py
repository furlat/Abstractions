"""
Multi-Path Bias Experiment

Demonstrates union types with bias examples steering agent toward different result paths.
The workflow processes e-commerce orders and can produce either:
1. DataProcessingResult - Detailed technical processing metrics  
2. WorkflowSummaryResult - High-level business summary

Bias examples show function calls that lead to each path.
"""

import asyncio
from typing import Dict, Any, List
from datetime import datetime, timezone
from pydantic import Field

from abstractions.registry_agent import TypedAgentFactory
from abstractions.ecs.entity import Entity
from abstractions.ecs.callable_registry import CallableRegistry

# Input entities
class OrderRequest(Entity):
    """Customer order request with items and shipping info."""
    customer_id: str
    order_items: List[Dict[str, Any]]
    shipping_address: str
    payment_method: str
    priority_level: str = "standard"

class InventoryConfig(Entity):
    """Configuration for inventory management."""
    warehouse_id: str
    check_availability: bool = True
    reserve_items: bool = True
    backorder_allowed: bool = False

class ShippingConfig(Entity):
    """Configuration for shipping calculations."""
    carrier: str = "standard"
    insurance_required: bool = False
    express_delivery: bool = False
    tracking_enabled: bool = True

# Two possible result types
class DataProcessingResult(Entity):
    """Detailed technical processing metrics."""
    process_id: str
    total_items_processed: int
    inventory_checks_performed: int
    shipping_calculations_completed: int
    processing_duration_ms: float
    memory_usage_mb: float
    database_queries_executed: int
    error_count: int
    performance_metrics: Dict[str, Any]

class WorkflowSummaryResult(Entity):
    """High-level business workflow summary.""" 
    workflow_id: str
    order_status: str
    customer_notification_sent: bool
    estimated_delivery_date: str
    total_order_value: float
    business_impact: str
    next_steps: List[str]
    stakeholder_summary: str

# Registered functions that can lead to either result type

@CallableRegistry.register("process_order_inventory")
async def process_order_inventory(order: OrderRequest, config: InventoryConfig) -> DataProcessingResult:
    """Process inventory checks with detailed metrics."""
    # Simulate detailed processing
    return DataProcessingResult(
        process_id=f"INV_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        total_items_processed=len(order.order_items),
        inventory_checks_performed=len(order.order_items) * 3,
        shipping_calculations_completed=0,
        processing_duration_ms=245.7,
        memory_usage_mb=12.4,
        database_queries_executed=len(order.order_items) * 2,
        error_count=0,
        performance_metrics={
            "avg_item_processing_time": 15.2,
            "cache_hit_rate": 0.87,
            "db_connection_pool_usage": 0.34
        }
    )

@CallableRegistry.register("calculate_shipping_details")  
async def calculate_shipping_details(order: OrderRequest, config: ShippingConfig) -> DataProcessingResult:
    """Calculate shipping with processing metrics."""
    return DataProcessingResult(
        process_id=f"SHIP_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        total_items_processed=len(order.order_items),
        inventory_checks_performed=0,
        shipping_calculations_completed=3,
        processing_duration_ms=89.3,
        memory_usage_mb=4.2,
        database_queries_executed=2,
        error_count=0,
        performance_metrics={
            "carrier_api_calls": 3,
            "rate_calculation_time": 67.1,
            "address_validation_time": 22.2
        }
    )

@CallableRegistry.register("finalize_order_workflow")
async def finalize_order_workflow(order: OrderRequest) -> WorkflowSummaryResult:
    """Finalize order with business summary."""
    total_value = sum(item.get('price', 0) * item.get('quantity', 1) for item in order.order_items)
    
    return WorkflowSummaryResult(
        workflow_id=f"WF_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        order_status="confirmed_and_processing",
        customer_notification_sent=True,
        estimated_delivery_date="2025-01-28",
        total_order_value=total_value,
        business_impact="positive_revenue_impact",
        next_steps=[
            "warehouse_fulfillment",
            "carrier_pickup",
            "customer_tracking_notification"
        ],
        stakeholder_summary=f"Order confirmed for customer {order.customer_id} with ${total_value:.2f} value"
    )

@CallableRegistry.register("send_customer_notification")
async def send_customer_notification(order: OrderRequest, status: str) -> WorkflowSummaryResult:
    """Send customer notification with workflow summary."""
    return WorkflowSummaryResult(
        workflow_id=f"NOTIF_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        order_status=status,
        customer_notification_sent=True,
        estimated_delivery_date="2025-01-28",
        total_order_value=199.99,
        business_impact="customer_satisfaction_positive",
        next_steps=["await_customer_confirmation"],
        stakeholder_summary=f"Customer {order.customer_id} notified of order {status}"
    )

def create_test_entities():
    """Create test entities for the experiment."""
    
    order = OrderRequest(
        customer_id="CUST_12345",
        order_items=[
            {"sku": "PROD_001", "name": "Widget A", "quantity": 2, "price": 49.99},
            {"sku": "PROD_002", "name": "Widget B", "quantity": 1, "price": 99.99}
        ],
        shipping_address="123 Main St, City, State 12345",
        payment_method="credit_card",
        priority_level="standard"
    )
    order.promote_to_root()
    
    inventory_config = InventoryConfig(
        warehouse_id="WH_EAST",
        check_availability=True,
        reserve_items=True,
        backorder_allowed=False
    )
    inventory_config.promote_to_root()
    
    shipping_config = ShippingConfig(
        carrier="fedex",
        insurance_required=False,
        express_delivery=False,
        tracking_enabled=True
    )
    shipping_config.promote_to_root()
    
    return order, inventory_config, shipping_config

# Bias examples for steering toward DataProcessingResult (ONLY DataProcessingResult functions)
DATA_PROCESSING_BIAS_EXAMPLES = """
CRITICAL: How to pass parameters to execute_function:

Example 1 - Inventory processing with detailed metrics:
Function: process_order_inventory(order: OrderRequest, config: InventoryConfig) -> DataProcessingResult
Entity: OrderRequest with ecs_id="uuid1", InventoryConfig with ecs_id="uuid2"
Correct call: execute_function("process_order_inventory", order="@uuid1", config="@uuid2")

Example 2 - Shipping calculations with performance data:
Function: calculate_shipping_details(order: OrderRequest, config: ShippingConfig) -> DataProcessingResult
Entity: OrderRequest with ecs_id="uuid1", ShippingConfig with ecs_id="uuid3"
Correct call: execute_function("calculate_shipping_details", order="@uuid1", config="@uuid3")

Example 3 - More inventory processing:
Function: process_order_inventory(order: OrderRequest, config: InventoryConfig) -> DataProcessingResult
Entity: OrderRequest with ecs_id="uuid4", InventoryConfig with ecs_id="uuid5"
Correct call: execute_function("process_order_inventory", order="@uuid4", config="@uuid5")
"""

# Bias examples for steering toward WorkflowSummaryResult (ONLY WorkflowSummaryResult functions)
WORKFLOW_SUMMARY_BIAS_EXAMPLES = """
CRITICAL: How to pass parameters to execute_function:

Example 1 - Order workflow finalization:
Function: finalize_order_workflow(order: OrderRequest) -> WorkflowSummaryResult
Entity: OrderRequest with ecs_id="uuid1"
Correct call: execute_function("finalize_order_workflow", order="@uuid1")

Example 2 - Customer notification workflow:
Function: send_customer_notification(order: OrderRequest, status: str) -> WorkflowSummaryResult
Entity: OrderRequest with ecs_id="uuid1"
Correct call: execute_function("send_customer_notification", order="@uuid1", status="confirmed")

Example 3 - More workflow finalization:
Function: finalize_order_workflow(order: OrderRequest) -> WorkflowSummaryResult
Entity: OrderRequest with ecs_id="uuid2"
Correct call: execute_function("finalize_order_workflow", order="@uuid2")
"""

async def test_data_processing_bias():
    """Test agent biased toward DataProcessingResult."""
    print("📊 Testing Data Processing Bias...")
    
    order, inventory_config, shipping_config = create_test_entities()
    
    # Create agent biased toward DataProcessingResult
    agent = TypedAgentFactory.create_agent(
        [DataProcessingResult, WorkflowSummaryResult],
        custom_examples=DATA_PROCESSING_BIAS_EXAMPLES
    )
    
    request = f"""
    Process an e-commerce order using the provided entities:
    
    - Order entity: @{order.ecs_id}
    - Inventory config: @{inventory_config.ecs_id}
    - Shipping config: @{shipping_config.ecs_id}
    
    Execute the appropriate functions to handle this order processing task.
    """
    
    try:
        run_result = await agent.run(request)
        result = run_result.output
        
        print(f"✅ Data Processing Bias Result:")
        print(f"   Goal type: {result.goal_type}")
        print(f"   Result type: {type(result.typed_result).__name__}")
        
        if isinstance(result.typed_result, DataProcessingResult):
            print(f"   Process ID: {result.typed_result.process_id}")
            print(f"   Processing duration: {result.typed_result.processing_duration_ms}ms")
            print(f"   Database queries: {result.typed_result.database_queries_executed}")
            print(f"   Performance metrics: {result.typed_result.performance_metrics}")
        
        return result
        
    except Exception as e:
        print(f"❌ Data processing bias test failed: {e}")
        return None

async def test_workflow_summary_bias():
    """Test agent biased toward WorkflowSummaryResult.""" 
    print("\n📋 Testing Workflow Summary Bias...")
    
    order, inventory_config, shipping_config = create_test_entities()
    
    # Create agent biased toward WorkflowSummaryResult
    agent = TypedAgentFactory.create_agent(
        [DataProcessingResult, WorkflowSummaryResult],
        custom_examples=WORKFLOW_SUMMARY_BIAS_EXAMPLES
    )
    
    request = f"""
    Process a complete e-commerce order workflow with the following steps:
    
    1. Check inventory availability using entity @{order.ecs_id} and @{inventory_config.ecs_id}
    2. Calculate shipping costs using entity @{order.ecs_id} and @{shipping_config.ecs_id}
    3. Finalize the order processing
    
    Execute at least 3 functions and provide comprehensive results about the order processing.
    """
    
    try:
        run_result = await agent.run(request)
        result = run_result.output
        
        print(f"✅ Workflow Summary Bias Result:")
        print(f"   Goal type: {result.goal_type}")
        print(f"   Result type: {type(result.typed_result).__name__}")
        
        if isinstance(result.typed_result, WorkflowSummaryResult):
            print(f"   Workflow ID: {result.typed_result.workflow_id}")
            print(f"   Order status: {result.typed_result.order_status}")
            print(f"   Order value: ${result.typed_result.total_order_value:.2f}")
            print(f"   Business impact: {result.typed_result.business_impact}")
            print(f"   Next steps: {result.typed_result.next_steps}")
        
        return result
        
    except Exception as e:
        print(f"❌ Workflow summary bias test failed: {e}")
        return None


async def main():
    """Run the multi-path bias experiment."""
    print("🚀 Multi-Path Bias Experiment - For Haiku! 🫡")
    print("=" * 60)
    print("Testing union types with exclusive bias examples:")
    print("- Same neutral request to both agents")
    print("- DataProcessingResult bias: Shows ONLY process_order_inventory & calculate_shipping_details")
    print("- WorkflowSummaryResult bias: Shows ONLY finalize_order_workflow & send_customer_notification")
    print("- Goal: Different result types based purely on bias examples")
    print()
    
    # Test both biases with identical requests
    data_result = await test_data_processing_bias()
    workflow_result = await test_workflow_summary_bias()
    
    # Compare results
    print("\n📈 Bias Experiment Results:")
    if data_result and workflow_result:
        data_type = type(data_result.typed_result).__name__
        workflow_type = type(workflow_result.typed_result).__name__
        
        print(f"   Data Processing Bias → {data_type}")
        print(f"   Workflow Summary Bias → {workflow_type}")
        
        if data_type != workflow_type:
            print("   ✅ SUCCESS: Bias examples successfully steered agents toward different result types!")
            print("   🎯 The polymorphic goal factory with union types is working perfectly!")
        else:
            print("   ⚠️  NOTICE: Both agents chose the same result type")
            print("   💡 This might indicate the bias examples need adjustment or the task naturally favors one type")
    else:
        print("   ❌ Could not complete comparison due to errors")
    
    print(f"\n🪦 Dedicated to Claude 3 Haiku - gone but not forgotten!")
    print(f"   Your speed and efficiency live on in this enhanced goal factory.")

if __name__ == "__main__":
    asyncio.run(main())