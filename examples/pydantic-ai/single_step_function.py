"""
Debug Function Execution Goal Test

Focus on the problematic date range function execution example.
"""

import asyncio
from typing import Dict
from datetime import datetime, timezone
from pydantic import Field

from abstractions.ecs.registry_agent import (
    TypedAgentFactory, GoalFactory, FunctionExecutionResult
)
from abstractions.ecs.entity import Entity, ConfigEntity
from abstractions.ecs.callable_registry import CallableRegistry

# Simple config entity for date ranges
class DateRangeConfig(ConfigEntity):
    """Configuration entity for date range operations."""
    start_date: str = Field(description="Start date for analysis")
    end_date: str = Field(description="End date for analysis")

@CallableRegistry.register("calculate_revenue_metrics")
async def calculate_revenue_metrics(start_date: str, end_date: str) -> FunctionExecutionResult:
    """
    Calculate comprehensive revenue metrics for a specified date range.
    """
    # Simplified calculation
    metrics = {
        "total_revenue": 15750.50,
        "average_order_value": 127.85,
        "total_orders": 123,
        "unique_customers": 89,
        "customer_lifetime_value": 176.97
    }
    
    # Return proper FunctionExecutionResult entity
    result = FunctionExecutionResult(
        function_name="calculate_revenue_metrics",
        success=True,
        result_data=metrics
    )
    
    return result

async def test_function_execution_goal():
    """Test the function execution goal with date range config."""
    print("📊 Testing Function Execution Goal...")
    
    # Create date range config entity
    date_config = DateRangeConfig(start_date="2024-10-01", end_date="2024-12-31")
    date_config.promote_to_root()
    
    # Create a function execution agent
    execution_agent = TypedAgentFactory.create_agent("function_execution")
    
    # Test agent with date range from config entity
    request = f"""
    Calculate comprehensive revenue metrics for Q4 2024 business analysis.
    
    Requirements:
    1. Execute calculate_revenue_metrics function with start_date=@{date_config.ecs_id}.start_date and end_date=@{date_config.ecs_id}.end_date
    2. Capture the returned metrics including total revenue and average order value
    3. Verify the function executed successfully
    
    Create a FunctionExecutionResult with the execution outcomes.
    """
    
    try:
        run_result = await execution_agent.run(request)
        result = run_result.output
        print(f"✅ Function execution completed!")
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
        
        print(f"\nall messages: {run_result.all_messages()}")
            
    except Exception as e:
        print(f"❌ Function execution failed: {e}")

async def main():
    """Run the debug test."""
    print("🚀 Debug Function Execution Test")
    print("=" * 50)
    
    # Show available goal types
    available_types = GoalFactory.get_available_goal_types()
    print(f"📋 Available goal types: {', '.join(available_types)}")
    print()
    
    # Run the problematic test
    await test_function_execution_goal()

if __name__ == "__main__":
    asyncio.run(main())