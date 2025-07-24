# Dynamic Goal System Design

## Overview

Create a polymorphic goal system where Goal subclasses are dynamically generated with properly typed `typed_result` fields. The system uses modern Pydantic v2 patterns with automatic loading and validation from ECS addresses.

## Architecture Flow

1. **Factory creates Goal subclass** with specific `typed_result` type annotation
2. **Agent configured with Goal subclass** as output type
3. **Agent sets `typed_result_ecs_address`** (never touches `typed_result` directly)
4. **Goal validator automatically loads** entity from address into `typed_result`
5. **Pydantic validates** the loaded entity matches the expected type
6. **Revalidation triggers** polymorphic typing enforcement

## Base Goal Model

```python
from typing import Optional, List, Dict, Any, Type
from pydantic import BaseModel, Field, model_validator
from abstractions.ecs.ecs_address_parser import get, is_address
from abstractions.ecs.entity import Entity

class BaseGoal(BaseModel):
    """Base goal model with ECS address-based typed result loading."""
    
    model_config = {"validate_assignment": True, "revalidate_instances": "always"}
    
    goal_type: str = Field(
        description="Type of goal being achieved (order_processing, entity_retrieval, etc.)"
    )
    goal_completed: bool = Field(
        default=False,
        description="Whether the goal has been successfully completed"
    )
    primary_action: str = Field(
        description="Primary action taken to achieve goal (function_execution, data_retrieval, etc.)"
    )
    summary: str = Field(
        description="Clear summary of what was accomplished"
    )
    entity_ids_referenced: List[str] = Field(
        default_factory=list,
        description="UUIDs of entities that were referenced or modified"
    )
    functions_used: List[str] = Field(
        default_factory=list,
        description="Names of functions that were executed"
    )
    extra_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional untyped data for fallback scenarios"
    )
    
    # ECS address for typed result - agent sets this
    typed_result_ecs_address: Optional[str] = Field(
        default=None,
        description="ECS address (@uuid) pointing to the typed result entity"
    )
    
    # Typed result field - populated by validator from ECS address
    # This gets overridden in dynamic subclasses with specific types
    typed_result: Optional[Entity] = Field(
        default=None,
        description="Typed result entity loaded from ECS address"
    )
    
    @field_validator('typed_result_ecs_address')
    @classmethod
    def validate_ecs_address_format(cls, v: Optional[str]) -> Optional[str]:
        """Ensure ECS address format is valid if provided."""
        if v is not None and not is_address(v):
            raise ValueError(f"Invalid ECS address format: {v}")
        return v
    
    @model_validator(mode='after')
    def load_typed_result_from_address(self) -> 'BaseGoal':
        """Load typed result entity from ECS address if provided."""
        if self.typed_result_ecs_address and not self.typed_result:
            try:
                entity = get(self.typed_result_ecs_address)
                if entity is None:
                    raise ValueError(f"No entity found at address: {self.typed_result_ecs_address}")
                self.typed_result = entity
            except Exception as e:
                raise ValueError(f"Failed to load typed result from {self.typed_result_ecs_address}: {e}")
        return self
```

## Result Entity Classes (Pydantic v2)

```python
class OrderProcessingResult(Entity):
    """Typed result entity for order processing goals."""
    
    order_id: str = Field(
        description="Unique identifier of the processed order"
    )
    order_status: Literal['confirmed', 'shipped', 'delivered'] = Field(
        description="Final status of the order after processing"
    )
    customer_spending_updated: float = Field(
        ge=0,
        description="Updated total customer spending amount"
    )
    customer_order_count: int = Field(
        ge=1,
        description="Updated customer order count"
    )
    product_stock_remaining: int = Field(
        ge=0,
        description="Remaining product stock after order"
    )
    product_total_sold: int = Field(
        ge=1,
        description="Updated total units sold for product"
    )
    inventory_alert_triggered: bool = Field(
        default=False,
        description="Whether low inventory alert was triggered"
    )
    customer_tier_updated: bool = Field(
        default=False,
        description="Whether customer tier was updated"
    )
    
    @field_validator('order_status')
    @classmethod
    def validate_order_status(cls, v: str) -> str:
        """Ensure order status is valid."""
        valid_statuses = ['confirmed', 'shipped', 'delivered']
        if v not in valid_statuses:
            raise ValueError(f"Order status must be one of {valid_statuses}, got: {v}")
        return v
    
    @model_validator(mode='after')
    def validate_processing_completeness(self) -> 'OrderProcessingResult':
        """Ensure order processing has meaningful updates."""
        if self.customer_spending_updated <= 0:
            raise ValueError("Customer spending must be updated with positive amount")
        if self.product_stock_remaining < 0:
            raise ValueError("Product stock cannot be negative")
        return self

class EntityRetrievalResult(Entity):
    """Typed result entity for entity retrieval goals."""
    
    entities_retrieved_count: int = Field(
        ge=1,
        description="Number of entities successfully retrieved"
    )
    lineages_explored_count: int = Field(
        ge=0,
        description="Number of entity lineages explored"
    )
    relationships_discovered: int = Field(
        ge=0,
        description="Number of entity relationships discovered"
    )
    retrieval_strategy: Literal['direct_lookup', 'lineage_traversal', 'relationship_mapping'] = Field(
        description="Strategy used for entity retrieval"
    )
    data_completeness_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Score indicating completeness of retrieved data (0.0-1.0)"
    )
    
    @model_validator(mode='after')
    def validate_retrieval_success(self) -> 'EntityRetrievalResult':
        """Ensure retrieval was successful and meaningful."""
        if self.entities_retrieved_count == 0:
            raise ValueError("Must retrieve at least one entity")
        if self.data_completeness_score < 0.1:
            raise ValueError("Data completeness score too low - retrieval may have failed")
        return self

class FunctionExecutionResult(Entity):
    """Typed result entity for function execution goals."""
    
    function_name: str = Field(
        description="Name of the function that was executed"
    )
    execution_success: bool = Field(
        description="Whether function execution completed successfully"
    )
    entities_created_count: int = Field(
        ge=0,
        description="Number of new entities created by function"
    )
    entities_modified_count: int = Field(
        ge=0,
        description="Number of existing entities modified by function"
    )
    execution_time_ms: float = Field(
        ge=0,
        description="Function execution time in milliseconds"
    )
    validation_errors_count: int = Field(
        ge=0,
        description="Number of validation errors encountered"
    )
    
    @field_validator('function_name')
    @classmethod
    def validate_function_name(cls, v: str) -> str:
        """Ensure function name is valid."""
        if not v or not v.strip():
            raise ValueError("Function name cannot be empty")
        return v.strip()
    
    @model_validator(mode='after')
    def validate_execution_consistency(self) -> 'FunctionExecutionResult':
        """Ensure execution results are consistent."""
        if not self.execution_success and self.entities_created_count > 0:
            raise ValueError("Cannot create entities if execution failed")
        if self.validation_errors_count > 0 and self.execution_success:
            raise ValueError("Cannot have validation errors if execution succeeded")
        return self
```

## Dynamic Goal Class Factory

```python
from typing import Type, TypeVar

T = TypeVar('T', bound=Entity)

class GoalClassFactory:
    """Factory for creating Goal subclasses with specific typed_result types."""
    
    _goal_registry = {
        "order_processing": {
            "result_entity_class": OrderProcessingResult,
            "description": "Process customer orders with reactive updates and validation"
        },
        "entity_retrieval": {
            "result_entity_class": EntityRetrievalResult,
            "description": "Retrieve and explore entity data with relationship mapping"
        },
        "function_execution": {
            "result_entity_class": FunctionExecutionResult,
            "description": "Execute registered functions with comprehensive result tracking"
        }
    }
    
    @classmethod
    def create_goal_class(cls, goal_type: str) -> Type[BaseGoal]:
        """Dynamically create Goal subclass with properly typed result field."""
        
        goal_config = cls._goal_registry.get(goal_type)
        if not goal_config:
            raise ValueError(f"Unknown goal type: {goal_type}. Available: {list(cls._goal_registry.keys())}")
        
        result_entity_class = goal_config["result_entity_class"]
        
        # Create dynamic goal class with typed result field
        class DynamicGoal(BaseGoal):
            """Dynamically generated goal class with typed result validation."""
            
            # Override typed_result with specific type annotation
            typed_result: Optional[result_entity_class] = Field(
                default=None,
                description=f"Typed result entity of type {result_entity_class.__name__}"
            )
            
            @model_validator(mode='after')
            def validate_typed_result_type(self) -> 'DynamicGoal':
                """Ensure loaded typed_result matches expected type."""
                if self.typed_result is not None:
                    if not isinstance(self.typed_result, result_entity_class):
                        raise ValueError(
                            f"typed_result must be instance of {result_entity_class.__name__}, "
                            f"got {type(self.typed_result).__name__}"
                        )
                return self
            
            @model_validator(mode='after')
            def validate_goal_completion_requirements(self) -> 'DynamicGoal':
                """Ensure completed goals have required typed_result."""
                if self.goal_completed and not self.typed_result:
                    raise ValueError(
                        f"Completed {goal_type} goal must have typed_result of type {result_entity_class.__name__}"
                    )
                return self
        
        # Set class name for better debugging
        DynamicGoal.__name__ = f"{goal_type.title().replace('_', '')}Goal"
        DynamicGoal.__qualname__ = DynamicGoal.__name__
        
        return DynamicGoal
    
    @classmethod
    def get_available_goal_types(cls) -> Dict[str, str]:
        """Get available goal types with descriptions."""
        return {
            goal_type: config["description"] 
            for goal_type, config in cls._goal_registry.items()
        }
    
    @classmethod
    def register_goal_type(
        cls, 
        goal_type: str, 
        result_entity_class: Type[Entity], 
        description: str
    ) -> None:
        """Register a new goal type with its result entity class."""
        cls._goal_registry[goal_type] = {
            "result_entity_class": result_entity_class,
            "description": description
        }
```

## Goal Failure Model

```python
class GoalFailure(BaseModel):
    """Model for failed goal attempts with detailed error information."""
    
    model_config = {"validate_assignment": True}
    
    goal_type: str = Field(
        description="Type of goal that was attempted"
    )
    goal_completed: bool = Field(
        default=False,
        description="Always false for failure cases"
    )
    primary_action: str = Field(
        default="error_handling",
        description="Primary action taken (always error_handling for failures)"
    )
    summary: str = Field(
        description="Summary of what went wrong"
    )
    error_type: str = Field(
        description="Category of error (validation_error, execution_error, address_error, etc.)"
    )
    error_message: str = Field(
        description="Detailed error message explaining the failure"
    )
    validation_errors: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Pydantic validation errors if applicable"
    )
    suggestions: List[str] = Field(
        default_factory=list,
        description="Actionable suggestions for resolving the error"
    )
    debug_info: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional debugging information"
    )
    entity_ids_referenced: List[str] = Field(
        default_factory=list,
        description="UUIDs of entities involved in the failed attempt"
    )
    functions_used: List[str] = Field(
        default_factory=list,
        description="Functions that were attempted before failure"
    )
    
    @field_validator('error_type')
    @classmethod
    def validate_error_type(cls, v: str) -> str:
        """Ensure error type is from known categories."""
        valid_types = [
            'validation_error', 'execution_error', 'address_error', 
            'entity_not_found', 'function_not_found', 'permission_error'
        ]
        if v not in valid_types:
            raise ValueError(f"error_type must be one of {valid_types}, got: {v}")
        return v
```

## Registry Agent Factory

```python
from typing import Union
from pydantic_ai import Agent

class RegistryAgentFactory:
    """Factory for creating registry agents with specific goal types."""
    
    @classmethod
    def create_agent(cls, goal_type: str) -> Agent:
        """Create registry agent configured for specific goal type."""
        
        # Get the dynamically created goal class
        goal_class = GoalClassFactory.create_goal_class(goal_type)
        
        # Union type for agent response
        AgentResponse = Union[goal_class, GoalFailure]
        
        # Create agent with typed output
        agent = Agent(
            'anthropic:claude-sonnet-4-20250514',
            output_type=AgentResponse,
            toolsets=[registry_toolset],  # Existing toolset from registry_agent.py
            system_prompt=f"""
            You are an assistant for the Abstractions Entity Framework that returns structured goal responses.
            
            Your goal type is: {goal_type}
            
            For successful goals, you must:
            1. Set goal_completed=true
            2. Set typed_result_ecs_address to point to a {goal_type} result entity
            3. NEVER set typed_result directly - it will be loaded automatically
            4. Ensure the result entity at the address passes all Pydantic v2 validators
            
            For failed goals, return GoalFailure with:
            - Clear error_type and error_message
            - Actionable suggestions for resolution
            - Debug information when helpful
            
            Available capabilities:
            - execute_function() - Execute registered functions with address support
            - list_functions() - Show available functions
            - get_all_lineages() - Show entity lineages
            - get_entity() - Get specific entity details
            
            The typed_result will be automatically loaded and validated from the ECS address you provide.
            Focus on creating meaningful result entities that pass validation for goal type: {goal_type}
            """
        )
        
        return agent
    
    @classmethod
    def create_multi_goal_agent(cls, goal_types: List[str]) -> Agent:
        """Create agent that can handle multiple goal types."""
        
        # Create union of all goal classes
        goal_classes = [GoalClassFactory.create_goal_class(gt) for gt in goal_types]
        AgentResponse = Union[*goal_classes, GoalFailure]
        
        agent = Agent(
            'anthropic:claude-sonnet-4-20250514',
            output_type=AgentResponse,
            toolsets=[registry_toolset],
            system_prompt=f"""
            You are an assistant that can handle multiple goal types: {', '.join(goal_types)}
            
            Determine the appropriate goal_type from the user request and return the corresponding goal class.
            Always set typed_result_ecs_address to point to the appropriate result entity.
            """
        )
        
        return agent
```

## Usage Examples

```python
# Create agent for order processing
order_agent = RegistryAgentFactory.create_agent("order_processing")

# Agent returns OrderProcessingGoal with typed OrderProcessingResult
result = await order_agent.run_async(
    "Process order ORD001 for customer CUST001 buying product PROD001"
)

# Access typed result (automatically loaded and validated)
if result.goal_completed:
    order_result = result.typed_result  # Type: OrderProcessingResult
    print(f"Order {order_result.order_id} status: {order_result.order_status}")
    print(f"Customer spending: ${order_result.customer_spending_updated}")

# Create multi-goal agent
multi_agent = RegistryAgentFactory.create_multi_goal_agent([
    "order_processing", "entity_retrieval", "function_execution"
])

# Agent automatically chooses appropriate goal type
result = await multi_agent.run_async("Show me all customer entities")
# Returns EntityRetrievalGoal with typed EntityRetrievalResult
```

## Benefits

1. **Type Safety**: Each goal has properly typed `typed_result` field
2. **Automatic Loading**: ECS address automatically resolves to typed entity
3. **Validation**: Pydantic v2 validators ensure result entity correctness
4. **Polymorphism**: Different goal types have different result entity types
5. **Simplicity**: Agent just sets address string, system handles the rest
6. **Revalidation**: `revalidate_instances="always"` ensures consistency
7. **Extensibility**: Easy to add new goal types via registry

## Implementation Steps

1. **Create base models** with Pydantic v2 patterns and informative fields
2. **Implement result entity classes** with comprehensive validators
3. **Build dynamic goal class factory** with proper type annotations
4. **Create registry agent factory** with goal-specific configuration
5. **Test validation patterns** with various goal types and edge cases
6. **Integrate with existing registry_agent.py** toolset