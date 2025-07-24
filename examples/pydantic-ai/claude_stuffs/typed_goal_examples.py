"""
Typed Goal Agent Examples

This module demonstrates the polymorphic goal system with clear, single-type goals.
Each example showcases a specific goal type with informative semantics and proper
typed result entities.
"""

import asyncio
from typing import Tuple, List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import Field

# Import the typed goal system
from abstractions.ecs.registry_agent import (
    TypedAgentFactory, GoalFactory, OrderProcessingResult, 
    EntityRetrievalResult, FunctionExecutionResult
)
from abstractions.ecs.entity import Entity, ConfigEntity
from abstractions.ecs.callable_registry import CallableRegistry
from abstractions.ecs.functional_api import get

# Domain entities with clear Field descriptions
class Customer(Entity):
    """Customer entity representing a registered user with purchasing history."""
    customer_id: str = Field(description="Unique business identifier for the customer")
    name: str = Field(description="Full legal name of the customer")
    email: str = Field(description="Primary email address for customer communications")
    tier: str = Field(default="standard", description="Customer loyalty tier: standard, premium, or vip")
    total_spending: float = Field(default=0.0, description="Cumulative amount spent by customer in USD")
    order_count: int = Field(default=0, description="Total number of orders placed by this customer")
    last_order_date: Optional[datetime] = Field(default=None, description="Timestamp of most recent order placement")

class Product(Entity):
    """Product entity representing an item available for purchase."""
    product_id: str = Field(description="Unique business identifier for the product")
    name: str = Field(description="Display name of the product for customer-facing interfaces")
    category: str = Field(description="Product category for organization and filtering")
    price: float = Field(description="Current selling price per unit in USD")
    stock_quantity: int = Field(description="Current number of units available in inventory")
    low_stock_threshold: int = Field(default=10, description="Stock level that triggers low inventory alerts")
    popularity_score: float = Field(default=0.0, description="Calculated popularity metric based on sales and views")
    total_sold: int = Field(default=0, description="Lifetime quantity sold across all orders")

class Order(Entity):
    """Order entity representing a customer's purchase transaction."""
    order_id: str = Field(description="Unique business identifier for the order")
    customer_id: str = Field(description="Reference to the customer who placed this order")
    product_id: str = Field(description="Reference to the product being purchased")
    quantity: int = Field(description="Number of units being purchased")
    unit_price: float = Field(description="Price per unit at time of order in USD")
    total_amount: float = Field(description="Total order value (quantity × unit_price) in USD")
    status: str = Field(default="pending", description="Current order status: pending, confirmed, shipped, delivered, cancelled")
    order_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp when the order was placed")

# Register business functions with clear semantics
@CallableRegistry.register("process_customer_order")
async def process_customer_order(order: Order, customer: Customer, product: Product) -> Tuple[Order, Customer, Product]:
    """
    Process a customer order through the complete fulfillment pipeline.
    
    This function handles order confirmation, customer statistics updates,
    and inventory management in a single atomic operation.
    """
    # Confirm the order and update status
    confirmed_order = Order(
        order_id=order.order_id,
        customer_id=order.customer_id,
        product_id=order.product_id,
        quantity=order.quantity,
        unit_price=order.unit_price,
        total_amount=order.total_amount,
        status="confirmed",
        order_date=order.order_date
    )
    
    # Update customer purchasing statistics
    updated_customer = Customer(
        customer_id=customer.customer_id,
        name=customer.name,
        email=customer.email,
        tier=customer.tier,
        total_spending=customer.total_spending + order.total_amount,
        order_count=customer.order_count + 1,
        last_order_date=datetime.now(timezone.utc)
    )
    
    # Update product inventory and sales metrics
    updated_product = Product(
        product_id=product.product_id,
        name=product.name,
        category=product.category,
        price=product.price,
        stock_quantity=product.stock_quantity - order.quantity,
        low_stock_threshold=product.low_stock_threshold,
        popularity_score=product.popularity_score + 1.0,
        total_sold=product.total_sold + order.quantity
    )
    
    return confirmed_order, updated_customer, updated_product

@CallableRegistry.register("find_customers_by_tier")
async def find_customers_by_tier(search_config: SearchConfig) -> List[Customer]:
    """
    Retrieve all customers belonging to a specific loyalty tier.
    
    This function searches the entity registry for customers matching
    the specified tier level for targeted marketing campaigns.
    """
    # This is a simplified implementation - in practice would query the registry
    customers = [
        Customer(customer_id="CUST001", name="Alice Johnson", email="alice@email.com", tier="standard"),
        Customer(customer_id="CUST002", name="Bob Smith", email="bob@email.com", tier="premium"),
        Customer(customer_id="CUST003", name="Charlie Brown", email="charlie@email.com", tier="vip"),
    ]
    
    # Filter by requested tier from config
    matching_customers = [c for c in customers if c.tier == search_config.tier]
    return matching_customers

@CallableRegistry.register("calculate_revenue_metrics")
async def calculate_revenue_metrics(start_date: str, end_date: str) -> Dict[str, float]:
    """
    Calculate comprehensive revenue metrics for a specified date range.
    
    This function aggregates sales data to provide business intelligence
    metrics including total revenue, average order value, and customer lifetime value.
    """
    # Simplified calculation - in practice would aggregate from order history
    metrics = {
        "total_revenue": 15750.50,
        "average_order_value": 127.85,
        "total_orders": 123,
        "unique_customers": 89,
        "customer_lifetime_value": 176.97
    }
    
    return metrics

# Configuration entities for agent to use
class SearchConfig(ConfigEntity):
    """Configuration entity for search operations."""
    tier: str = Field(description="Customer tier to search for")
    
class DateRangeConfig(ConfigEntity):
    """Configuration entity for date range operations."""
    start_date: str = Field(description="Start date for analysis")
    end_date: str = Field(description="End date for analysis")

def create_sample_data() -> Tuple[List[Customer], List[Product], List[Order]]:
    """Create realistic sample data for testing typed goal agents."""
    
    customers = [
        Customer(
            customer_id="CUST001", 
            name="Alice Johnson", 
            email="alice@email.com", 
            tier="standard", 
            total_spending=0.0, 
            order_count=0
        ),
        Customer(
            customer_id="CUST002", 
            name="Bob Smith", 
            email="bob@email.com", 
            tier="premium", 
            total_spending=850.0, 
            order_count=6
        ),
        Customer(
            customer_id="CUST003", 
            name="Charlie Brown", 
            email="charlie@email.com", 
            tier="vip", 
            total_spending=2100.0, 
            order_count=18
        )
    ]
    
    products = [
        Product(
            product_id="PROD001", 
            name="Professional Laptop", 
            category="Electronics", 
            price=1299.99, 
            stock_quantity=25, 
            low_stock_threshold=5, 
            popularity_score=45.0, 
            total_sold=156
        ),
        Product(
            product_id="PROD002", 
            name="Ergonomic Coffee Mug", 
            category="Office Supplies", 
            price=24.99, 
            stock_quantity=8, 
            low_stock_threshold=15, 
            popularity_score=32.0, 
            total_sold=89
        ),
        Product(
            product_id="PROD003", 
            name="Executive Gaming Chair", 
            category="Furniture", 
            price=399.99, 
            stock_quantity=12, 
            low_stock_threshold=3, 
            popularity_score=28.0, 
            total_sold=67
        )
    ]
    
    orders = [
        Order(
            order_id="ORD001", 
            customer_id="CUST001", 
            product_id="PROD001", 
            quantity=1, 
            unit_price=1299.99, 
            total_amount=1299.99
        ),
        Order(
            order_id="ORD002", 
            customer_id="CUST002", 
            product_id="PROD003", 
            quantity=1, 
            unit_price=399.99, 
            total_amount=399.99
        ),
        Order(
            order_id="ORD003", 
            customer_id="CUST003", 
            product_id="PROD002", 
            quantity=3, 
            unit_price=24.99, 
            total_amount=74.97
        )
    ]
    
    return customers, products, orders

def create_config_entities():
    """Create configuration entities for agent to use."""
    # Create search config for finding premium customers
    search_config = SearchConfig(tier="premium")
    search_config.promote_to_root()
    
    # Create date range config for Q4 2024 analysis  
    date_config = DateRangeConfig(start_date="2024-10-01", end_date="2024-12-31")
    date_config.promote_to_root()
    
    return search_config, date_config

async def test_order_processing_goal():
    """Test the order processing goal with clear semantics."""
    print("🛒 Testing Order Processing Goal...")
    
    # Create an order processing agent
    order_agent = TypedAgentFactory.create_agent("order_processing")
    
    # Set up test data
    customers, products, orders = create_sample_data()
    
    # Register entities in the system
    for customer in customers:
        customer.promote_to_root()
    for product in products:
        product.promote_to_root()
    for order in orders:
        order.promote_to_root()
    
    # Test agent with clear, semantic request
    request = f"""
    Process order ORD001 for customer Alice Johnson purchasing a Professional Laptop.
    
    Use these specific entities:
    - Order: @{orders[0].ecs_id}
    - Customer: @{customers[0].ecs_id} 
    - Product: @{products[0].ecs_id}
    
    Execute the complete order fulfillment process including:
    1. Order confirmation and status update
    2. Customer statistics update (spending, order count)
    3. Product inventory reduction and sales metrics update
    
    Create an OrderProcessingResult entity with the processing outcomes.
    """
    
    try:
        run_result = await order_agent.run(request)
        result = run_result.output
        print(f"✅ Order processing completed successfully!")
        print(f"   Goal type: {result.goal_type}")
        print(f"   Completed: {result.goal_completed}")
        print(f"   Summary: {result.summary}")
        
        if result.typed_result and isinstance(result.typed_result, OrderProcessingResult):
            print(f"   Result type: {type(result.typed_result).__name__}")
            print(f"   Order ID: {result.typed_result.order_id}")
            print(f"   Order Status: {result.typed_result.order_status}")
        
        if result.error:
            print(f"   Error: {result.error.error_message}")
            
    except Exception as e:
        print(f"❌ Order processing failed: {e}")

async def test_entity_retrieval_goal():
    """Test the entity retrieval goal with clear semantics."""
    print("\n🔍 Testing Entity Retrieval Goal...")
    
    # Create configuration entities for agent to use
    search_config, _ = create_config_entities()
    
    # Create an entity retrieval agent
    retrieval_agent = TypedAgentFactory.create_agent("entity_retrieval")
    
    # Test agent with clear, semantic request using config entity
    request = f"""
    Find all premium tier customers in the system for a targeted marketing campaign.
    
    Requirements:
    1. Use the find_customers_by_tier function with config entity @{search_config.ecs_id}.tier
    2. Count the total number of premium customers found
    3. Collect their entity IDs for campaign targeting
    
    Create an EntityRetrievalResult with the search outcomes.
    """
    
    try:
        run_result = await retrieval_agent.run(request)
        result = run_result.output
        
        print(f"✅ Entity retrieval completed successfully!")
        print(f"   Goal type: {result.goal_type}")
        print(f"   Completed: {result.goal_completed}")
        print(f"   Summary: {result.summary}")
        
        if result.typed_result and isinstance(result.typed_result, EntityRetrievalResult):
            print(f"   Result type: {type(result.typed_result).__name__}")
            print(f"   Entities found: {result.typed_result.total_count}")
            print(f"   Entity IDs: {result.typed_result.entities_found}")
        
        if result.error:
            print(f"   Error: {result.error.error_message}")
            
    except Exception as e:
        print(f"❌ Entity retrieval failed: {e}")

async def test_function_execution_goal():
    """Test the function execution goal with clear semantics."""
    print("\n📊 Testing Function Execution Goal...")
    
    # Create configuration entities for agent to use
    _, date_config = create_config_entities()
    
    # Create a function execution agent
    execution_agent = TypedAgentFactory.create_agent("function_execution")
    
    # Test agent with clear, semantic request using config entity
    request = f"""
    Calculate comprehensive revenue metrics for Q4 2024 business analysis.
    
    Requirements:
    1. Execute calculate_revenue_metrics function with date range from config @{date_config.ecs_id}.start_date to @{date_config.ecs_id}.end_date
    2. Capture the returned metrics including total revenue and average order value
    3. Verify the function executed successfully
    
    Create a FunctionExecutionResult with the execution outcomes.
    """
    
    try:
        run_result = await execution_agent.run(request)
        result = run_result.output
        print(f"✅ Function execution completed successfully!")
        print(f"   Goal type: {result.goal_type}")
        print(f"   Completed: {result.goal_completed}")
        print(f"   Summary: {result.summary}")
        
        if result.typed_result and isinstance(result.typed_result, FunctionExecutionResult):
            print(f"   Result type: {type(result.typed_result).__name__}")
            print(f"   Function: {result.typed_result.function_name}")
            print(f"   Success: {result.typed_result.success}")
            print(f"   Result data: {result.typed_result.result_data}")
        
        if result.error:
            print(f"   Error: {result.error.error_message}")
        
        print(f"all messages: {run_result.all_messages()}")
            
    except Exception as e:
        print(f"❌ Function execution failed: {e}")

async def test_goal_failure_scenario():
    """Test the goal failure handling with clear semantics."""
    print("\n❌ Testing Goal Failure Scenario...")
    
    # Create an order processing agent
    order_agent = TypedAgentFactory.create_agent("order_processing")
    
    # Test agent with intentionally problematic request
    request = """
    Process an order with invalid entity references that don't exist in the system.
    
    Use these non-existent entities:
    - Order: @00000000-0000-0000-0000-000000000000
    - Customer: @11111111-1111-1111-1111-111111111111
    - Product: @22222222-2222-2222-2222-222222222222
    
    This should demonstrate proper error handling with informative failure messages.
    """
    
    try:
        run_result = await order_agent.run(request)
        result = run_result.output
        print(f"📋 Goal failure handling test:")
        print(f"   Goal type: {result.goal_type}")
        print(f"   Completed: {result.goal_completed}")
        print(f"   Summary: {result.summary}")
        
        if result.error:
            print(f"   ✅ Error properly captured:")
            print(f"      Type: {result.error.error_type}")
            print(f"      Message: {result.error.error_message}")
            print(f"      Suggestions: {result.error.suggestions}")
        else:
            print(f"   ⚠️  Expected error but got success")
            
    except Exception as e:
        print(f"❌ Unexpected exception during failure test: {e}")

async def main():
    """Run all typed goal examples with clear semantic demonstrations."""
    print("🚀 Typed Goal Agent Examples")
    print("=" * 50)
    print("Demonstrating polymorphic goal system with clear semantics")
    print("Each goal type has proper typed results and validation")
    print()
    
    # Show available goal types
    available_types = GoalFactory.get_available_goal_types()
    print(f"📋 Available goal types: {', '.join(available_types)}")
    print()
    
    # Run only the function execution test to debug
    await test_function_execution_goal()
    
    print("\n🎉 All typed goal examples completed!")
    print("Each agent returned properly typed results with validation")

if __name__ == "__main__":
    asyncio.run(main())