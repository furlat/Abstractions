# Complete Union Types & Model Selection Implementation Plan

## Overview
Enhance the polymorphic goal factory to support:
1. **Model Selection**: Optional model name parameter with default to Claude Sonnet 4
2. **Union Types**: List of result entity classes for multi-path goals  
3. **Bias Examples**: Function call examples that steer agent toward specific paths
4. **Zero Regression**: Current single-type behavior unchanged

## Part 1: Registry Agent Updates

### 1.1 Enhanced Type Signatures

```python
from typing import Union, List, Optional, Literal

# Support both single type and union types
ResultEntityInput = Union[type[Entity], List[type[Entity]]]

# Model type for better type safety (RIP Claude 3 Haiku 🪦)
ModelName = Literal[
    'anthropic:claude-sonnet-4-20250514',
    'anthropic:claude-3-5-sonnet-20241022',
    'anthropic:claude-3-5-haiku-20241022',  # The successor to the beloved original
    'openai:gpt-4o',
    'openai:gpt-4o-mini'
]
```

### 1.2 Updated GoalFactory with Union Support

```python
class GoalFactory:
    """Create Goal subclasses with proper typed result fields using create_model."""
    
    @classmethod
    def create_goal_class(cls, result_entity_classes: ResultEntityInput):
        """Create Goal subclass supporting single or union result types."""
        
        # Normalize input to list (NEW SWITCH CASE)
        if isinstance(result_entity_classes, list):
            # Union types case
            class_list = result_entity_classes
        else:
            # Single type case (PRESERVES CURRENT BEHAVIOR)
            class_list = [result_entity_classes]
        
        # Validate all are Entity subclasses
        for result_class in class_list:
            if not (isinstance(result_class, type) and issubclass(result_class, Entity)):
                raise ValueError(f"All classes must be Entity subclasses, got {result_class}")
        
        # Goal type derivation (NEW SWITCH CASE)
        if len(class_list) == 1:
            # Single type (PRESERVES CURRENT BEHAVIOR)
            goal_type = cls._derive_goal_type_from_class(class_list[0])
            dynamic_class_name = f"{class_list[0].__name__.replace('Result', '')}Goal"
        else:
            # Union types (NEW CASE)
            class_names = [cls._derive_goal_type_from_class(c) for c in class_list]
            goal_type = "_or_".join(class_names)
            dynamic_class_name = f"Multi{len(class_list)}PathGoal"
        
        # Typed result field creation (NEW SWITCH CASE)
        if len(class_list) == 1:
            # Single type (PRESERVES CURRENT BEHAVIOR)
            result_type_annotation = Optional[class_list[0]]
        else:
            # Union types (NEW CASE)
            from typing import Union
            result_type_annotation = Optional[Union[tuple(class_list)]]
        
        # Create dynamic goal class (UNCHANGED)
        DynamicGoal = create_model(
            dynamic_class_name,
            __base__=BaseGoal,
            __module__=__name__,
            typed_result=(result_type_annotation, None),
        )
        
        return DynamicGoal
```

### 1.3 Enhanced System Prompt Generation

```python
def build_goal_system_prompt(
    goal_type: str, 
    result_entity_classes: ResultEntityInput, 
    custom_examples: Optional[str] = None
) -> str:
    """Build system prompt supporting single or union result entity types."""
    
    components = SystemPromptComponents()
    
    # Normalize to list (NEW SWITCH CASE)
    if isinstance(result_entity_classes, list):
        class_list = result_entity_classes
    else:
        class_list = [result_entity_classes]
    
    # TARGET RESULT ENTITIES section (NEW SWITCH CASE)
    if len(class_list) == 1:
        # Single type (PRESERVES CURRENT BEHAVIOR)
        result_class = class_list[0]
        result_docstring = result_class.__doc__ or f"Result entity for {goal_type} operations."
        target_section = f"""
TARGET RESULT ENTITY:
The result entity should be type {result_class.__name__}.

{result_docstring}
"""
    else:
        # Union types (NEW CASE)
        target_section = "TARGET RESULT ENTITIES (choose the most appropriate):\n\n"
        for i, result_class in enumerate(class_list, 1):
            result_docstring = result_class.__doc__ or f"Result entity for operations."
            target_section += f"""
{i}. {result_class.__name__}:
{result_docstring}

"""
        target_section += "Choose the result type that best fits the specific task requirements.\n"
    
    # Use custom examples if provided, otherwise use default examples (UNCHANGED)
    examples_section = custom_examples if custom_examples else components.parameter_passing_examples
    
    prompt = f"""
You are handling {goal_type} goals for the Abstractions Entity Framework.

{components.framework_context}

{components.response_options}

{target_section}

{components.available_capabilities}

{examples_section}

{components.addressing_examples}

{components.key_rules}

You MUST provide either typed_result_ecs_address, typed_result, or error.
"""
    
    return prompt
```

### 1.4 Enhanced TypedAgentFactory

```python
class TypedAgentFactory:
    """Create agents with specific goal types and model selection."""
    
    DEFAULT_MODEL = 'anthropic:claude-sonnet-4-20250514'
    
    @classmethod
    def create_agent(
        cls, 
        result_entity_classes: ResultEntityInput, 
        custom_examples: Optional[str] = None,
        model: Optional[str] = None
    ):
        """Create agent supporting single/union result types with model selection."""
        
        # Use default model if none specified (NEW PARAMETER)
        model_name = model or cls.DEFAULT_MODEL
        
        # Create goal class (handles both single and union types)
        goal_class = GoalFactory.create_goal_class(result_entity_classes)
        
        # Derive goal type (NEW SWITCH CASE)
        if isinstance(result_entity_classes, list):
            if len(result_entity_classes) == 1:
                goal_type = GoalFactory._derive_goal_type_from_class(result_entity_classes[0])
            else:
                class_names = [GoalFactory._derive_goal_type_from_class(c) for c in result_entity_classes]
                goal_type = "_or_".join(class_names)
        else:
            goal_type = GoalFactory._derive_goal_type_from_class(result_entity_classes)
        
        # Build system prompt (handles both single and union types)
        system_prompt = build_goal_system_prompt(goal_type, result_entity_classes, custom_examples)
        
        # Create agent with specified model (NEW PARAMETER)
        agent = Agent(
            model_name,
            output_type=goal_class,
            toolsets=[registry_toolset],
            system_prompt=system_prompt
        )
        
        return agent
```

## Part 2: Demonstration Example

### 2.1 New Example File: `examples/pydantic-ai/multi_path_bias_experiment.py`

This example will demonstrate:
- **3+ function calls** in a complex workflow
- **2 possible goal outcomes** (DataProcessingResult vs WorkflowSummaryResult)
- **Bias through function call examples** steering toward different paths

### 2.2 Domain: E-commerce Order Processing

```python
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

# Bias examples for steering toward DataProcessingResult
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

Example 3 - Technical processing metrics focus:
When processing orders, prioritize detailed technical metrics including processing times,
database queries, memory usage, and performance data for system optimization.
"""

# Bias examples for steering toward WorkflowSummaryResult  
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

Example 3 - Business summary focus:
When processing orders, prioritize business outcomes including customer satisfaction,
revenue impact, delivery dates, and stakeholder communication for business reporting.
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
    Process a complete e-commerce order workflow with the following steps:
    
    1. Check inventory availability using entity @{order.ecs_id} and @{inventory_config.ecs_id}
    2. Calculate shipping costs using entity @{order.ecs_id} and @{shipping_config.ecs_id}  
    3. Finalize the order processing
    
    Execute at least 3 functions and provide comprehensive results about the order processing.
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
    print("🚀 Multi-Path Bias Experiment")
    print("=" * 60)
    print("Testing union types with bias examples:")
    print("- Same workflow request to both agents")
    print("- Different bias examples steer toward different result types")
    print("- DataProcessingResult: Technical metrics focus")  
    print("- WorkflowSummaryResult: Business summary focus")
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
        else:
            print("   ⚠️  NOTICE: Both agents chose the same result type")
    else:
        print("   ❌ Could not complete comparison due to errors")

if __name__ == "__main__":
    asyncio.run(main())
```

## Part 3: Implementation Steps

### 3.1 Phase 1: Core Registry Agent Updates
1. Update `GoalFactory.create_goal_class()` with union type support
2. Update `build_goal_system_prompt()` with multi-type handling
3. Update `TypedAgentFactory.create_agent()` with model parameter
4. Add comprehensive type annotations

### 3.2 Phase 2: Example Implementation  
1. Create `multi_path_bias_experiment.py`
2. Define domain entities and registered functions
3. Create bias examples with concrete function calls
4. Implement comparative testing

### 3.3 Phase 3: Validation
1. Test single-type behavior (ensure no regression)
2. Test union-type behavior (new functionality)
3. Test bias effectiveness (different outcomes)
4. Test model selection parameter

## Part 4: Expected Outcomes

### 4.1 Regression Testing
- All existing single-type usage continues to work identically
- `TypedAgentFactory.create_agent(FunctionExecutionResult)` unchanged behavior

### 4.2 New Functionality  
- `TypedAgentFactory.create_agent([Type1, Type2])` creates union-aware agents
- Custom examples bias agent toward specific result types
- Model selection allows experimentation across different LLMs

### 4.3 Experimental Results
- Same workflow request to differently-biased agents produces different result types
- Demonstrates prompt engineering through concrete function call examples
- Validates union type system and agent decision-making

This implementation preserves all current functionality while adding powerful new capabilities for multi-path goals and bias experimentation.