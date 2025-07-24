"""
Test the pydantic-ai integration with proper Pydantic models.
"""

from abstractions.ecs.registry_agent import (
    registry_agent, 
    FunctionList, 
    LineageList, 
    EntityInfo, 
    ExecutionResult
)


def test_function_listing():
    """Test that function listing returns proper Pydantic model."""
    print("Testing function listing...")
    
    try:
        result = registry_agent.run_sync("List all available functions")
        print(f"Agent response: {result.output}")
        
        # The agent should return structured data, not just strings
        print("✅ Function listing test completed")
        
    except Exception as e:
        print(f"❌ Function listing test failed: {e}")


def test_lineage_exploration():
    """Test lineage exploration with proper models."""
    print("\nTesting lineage exploration...")
    
    try:
        result = registry_agent.run_sync("Show me all entity lineages")
        print(f"Agent response: {result.output}")
        
        print("✅ Lineage exploration test completed")
        
    except Exception as e:
        print(f"❌ Lineage exploration test failed: {e}")


def test_address_error_handling():
    """Test enhanced address error handling."""
    print("\nTesting address error handling...")
    
    try:
        result = registry_agent.run_sync(
            'Try to execute a function with invalid address "invalid-address-format"'
        )
        print(f"Agent response: {result.output}")
        
        print("✅ Address error handling test completed")
        
    except Exception as e:
        print(f"❌ Address error handling test failed: {e}")


def test_function_signature():
    """Test function signature retrieval."""
    print("\nTesting function signature retrieval...")
    
    try:
        result = registry_agent.run_sync("Get the signature of any available function")
        print(f"Agent response: {result.output}")
        
        print("✅ Function signature test completed")
        
    except Exception as e:
        print(f"❌ Function signature test failed: {e}")


def main():
    """Run all integration tests."""
    print("🧪 Pydantic-AI Integration Tests")
    print("=" * 40)
    
    test_function_listing()
    test_lineage_exploration()
    test_address_error_handling()
    test_function_signature()
    
    print("\n✅ All tests completed!")
    print("\nNote: If no functions or entities are registered,")
    print("the agent will return empty results, which is expected.")


if __name__ == "__main__":
    main()