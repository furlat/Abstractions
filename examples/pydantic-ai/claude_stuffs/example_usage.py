"""
Example Usage: Pydantic-AI + Abstractions Integration

This demonstrates the natural language interface to the Abstractions Entity Framework
with enhanced address debugging capabilities.
"""

import asyncio
from registry_agent import registry_agent


async def demo_basic_functionality():
    """Demonstrate basic agent capabilities."""
    print("=== Abstractions Entity Framework Agent Demo ===\n")
    
    # 1. Function Discovery
    print("1. Discovering available functions:")
    result = registry_agent.run_sync("What functions are available in the registry?")
    print(f"Response: {result.output}")
    print("\n" + "="*60 + "\n")
    
    # 2. Entity Exploration
    print("2. Exploring entity lineages:")
    result = registry_agent.run_sync("Show me all entity lineages and their versions")
    print(f"Response: {result.output}")
    print("\n" + "="*60 + "\n")
    
    # 3. Function Signature Analysis
    print("3. Getting function signature details:")
    result = registry_agent.run_sync("Show me the signature for the first function you found")
    print(f"Response: {result.output}")
    print("\n" + "="*60 + "\n")


async def demo_enhanced_error_handling():
    """Demonstrate the impressive debugging help for address errors."""
    print("=== Enhanced Address Error Debugging Demo ===\n")
    
    # Example 1: Missing @ symbol
    print("1. Testing address without @ symbol:")
    result = registry_agent.run_sync(
        'Execute a function with parameter "invalid-uuid.name" (intentionally wrong address format)'
    )
    print(result.output)
    print("\n" + "="*60 + "\n")
    
    # Example 2: Invalid UUID format
    print("2. Testing invalid UUID format:")
    result = registry_agent.run_sync(
        'Try to execute a function with address "@invalid-uuid-format.field"'
    )
    print(result.output)
    print("\n" + "="*60 + "\n")
    
    # Example 3: Non-existent entity
    print("3. Testing non-existent entity:")
    result = registry_agent.run_sync(
        'Execute function with address "@f65cf3bd-9392-499f-8f57-dba701f50000.name" (fake UUID)'
    )
    print(result.output)
    print("\n" + "="*60 + "\n")


async def demo_conversational_workflow():
    """Demonstrate multi-step conversational workflows."""
    print("=== Conversational Workflow Demo ===\n")
    
    # Step 1: Initial inquiry
    print("Step 1: Initial entity exploration")
    result1 = registry_agent.run_sync("Show me the available entities and their types")
    print(result1.output)
    print("\n" + "-"*40 + "\n")
    
    # Step 2: Follow-up based on first result
    print("Step 2: Follow-up inquiry with conversation history")
    result2 = registry_agent.run_sync(
        "Pick the first entity you showed me and get its detailed information",
        message_history=result1.new_messages()
    )
    print(result2.output)
    print("\n" + "-"*40 + "\n")
    
    # Step 3: Function execution attempt
    print("Step 3: Attempt function execution")
    result3 = registry_agent.run_sync(
        "Now try to execute a function using that entity's ID",
        message_history=result2.new_messages()
    )
    print(result3.output)
    print("\n" + "="*60 + "\n")


async def demo_address_syntax_help():
    """Demonstrate address syntax guidance and suggestions."""
    print("=== Address Syntax Help Demo ===\n")
    
    # Show how the agent helps with correct syntax
    result = registry_agent.run_sync(
        """
        I'm having trouble with address syntax. Can you help me understand:
        1. How to reference entity fields using the @uuid.field format
        2. What happens when I make mistakes in the address format
        3. How the debugging system helps me fix errors
        """
    )
    print(result.output)
    print("\n" + "="*60 + "\n")


async def demo_pattern_classification():
    """Demonstrate input pattern classification."""
    print("=== Input Pattern Classification Demo ===\n")
    
    result = registry_agent.run_sync(
        """
        I want to understand how the system classifies different types of function parameters.
        Can you execute a function with various parameter types and show me how they're classified?
        For example, what's the difference between:
        - Direct entity objects
        - @uuid.field address strings  
        - Regular primitive values
        """
    )
    print(result.output)
    print("\n" + "="*60 + "\n")


def main():
    """Run all demonstration scenarios."""
    print("🤖 Pydantic-AI + Abstractions Integration Demo")
    print("=" * 50)
    
    try:
        # Run basic functionality demo
        asyncio.run(demo_basic_functionality())
        
        # Run enhanced error handling demo
        asyncio.run(demo_enhanced_error_handling())
        
        # Run conversational workflow demo
        asyncio.run(demo_conversational_workflow())
        
        # Run address syntax help demo
        asyncio.run(demo_address_syntax_help())
        
        # Run pattern classification demo
        asyncio.run(demo_pattern_classification())
        
        print("✅ Demo completed successfully!")
        
    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        print("This is expected if no entities are registered in the system yet.")
        print("The enhanced error handling will provide helpful guidance!")


if __name__ == "__main__":
    main()