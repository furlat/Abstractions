# Simple Polymorphic Goal System

## Core Concept

Focus on the type system - if we can retrieve the correct type instance from the registry, that's good enough. The type system and registered functions handle the details.

## Simple Architecture

### Base Goal
```python
from typing import Optional, List, Dict, Any, Type
from pydantic import BaseModel, Field, model_validator
from abstractions.ecs.ecs_address_parser import get

class BaseGoal(BaseModel):
    """Simple base goal with polymorphic typed result loading."""
    
    model_config = {"validate_assignment": True, "revalidate_instances": "always"}
    
    goal_type: str
    goal_completed: bool = False
    summary: str
    
    # Agent sets this, validator loads typed_result
    typed_result_ecs_address: Optional[str] = None
    
    # Gets overridden in dynamic subclasses with specific types
    typed_result: Optional[Any] = None
    
    @model_validator(mode='after')
    def load_typed_result(self) -> 'BaseGoal':
        """Load typed result from ECS address if provided."""
        if self.typed_result_ecs_address and not self.typed_result:
            self.typed_result = get(self.typed_result_ecs_address)
        return self
```

### Result Entity Types (Simple)
```python
# Simple result entities - let the type system handle validation
class OrderProcessingResult(Entity):
    """Result for order processing."""
    order_id: str
    order_status: str
    customer_updates: Dict[str, Any]
    product_updates: Dict[str, Any]

class EntityRetrievalResult(Entity):
    """Result for entity retrieval."""
    entities_found: List[str]  # ECS IDs
    total_count: int

class FunctionExecutionResult(Entity):
    """Result for function execution."""
    function_name: str
    success: bool
    result_data: Dict[str, Any]
```

### Dynamic Goal Factory
```python
class GoalFactory:
    """Create Goal subclasses with typed result fields."""
    
    _registry = {
        "order_processing": OrderProcessingResult,
        "entity_retrieval": EntityRetrievalResult,
        "function_execution": FunctionExecutionResult,
    }
    
    @classmethod
    def create_goal_class(cls, goal_type: str) -> Type[BaseGoal]:
        """Create Goal subclass with specific typed_result type."""
        
        result_class = cls._registry.get(goal_type)
        if not result_class:
            raise ValueError(f"Unknown goal type: {goal_type}")
        
        class DynamicGoal(BaseGoal):
            # This is the key - typed_result gets the specific type
            typed_result: Optional[result_class] = None
            
            @model_validator(mode='after')
            def validate_type(self) -> 'DynamicGoal':
                """Ensure loaded result is correct type."""
                if self.typed_result and not isinstance(self.typed_result, result_class):
                    raise ValueError(f"Expected {result_class.__name__}, got {type(self.typed_result).__name__}")
                return self
        
        DynamicGoal.__name__ = f"{goal_type.title()}Goal"
        return DynamicGoal
```

### Agent Factory
```python
from pydantic_ai import Agent
from typing import Union

class AgentFactory:
    """Create agents with specific goal types."""
    
    @classmethod
    def create_agent(cls, goal_type: str) -> Agent:
        """Create agent for specific goal type."""
        
        goal_class = GoalFactory.create_goal_class(goal_type)
        
        agent = Agent(
            'anthropic:claude-sonnet-4-20250514',
            output_type=goal_class,  # Just the specific goal type
            toolsets=[registry_toolset],
            system_prompt=f"""
            You are handling {goal_type} goals.
            
            Set typed_result_ecs_address to point to your result entity.
            Never set typed_result directly - it loads automatically.
            
            The result entity should be type {GoalFactory._registry[goal_type].__name__}.
            """
        )
        
        return agent
```

## Usage Pattern

```python
# Create order processing agent
order_agent = AgentFactory.create_agent("order_processing")

# Agent creates OrderProcessingResult entity and sets address
result = await order_agent.run_async("Process order with customer and product")

# typed_result is automatically OrderProcessingResult type
if result.goal_completed:
    order_result = result.typed_result  # Type: OrderProcessingResult
    print(f"Order: {order_result.order_id}")
```

## Key Benefits

1. **Type Safety**: `typed_result` has correct static type in each Goal subclass
2. **Simplicity**: Agent just sets address string
3. **Registry Integration**: Uses existing ECS address system
4. **Function Responsibility**: Let registered functions handle validation details
5. **Polymorphic**: Different goal types have different result entity types

## Implementation Focus

- Get the dynamic type generation working
- Ensure `typed_result: Optional[OrderProcessingResult]` annotations work
- Test that type checking and IDE support work correctly
- Let the function system handle business logic validation

The goal is: **if registry returns correct type instance, we're good**. Everything else is the responsibility of the type system and registered functions.