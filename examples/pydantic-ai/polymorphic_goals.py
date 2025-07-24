"""
Polymorphic Goal System for Registry Agent

This module implements a sophisticated goal validation system with:
- Goal-specific subtypes with embedded Pydantic validators
- Union types allowing agent to return success/failure objects
- Polymorphic factory pattern for goal object creation
- Type-safe goal achievement validation
"""

from typing import Union, List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, validator, root_validator
from abc import ABC, abstractmethod
from uuid import UUID

# Base goal classes
class GoalResult(BaseModel, ABC):
    """Abstract base for all goal results."""
    goal_type: str
    goal_completed: bool
    primary_action: str
    summary: str
    entity_ids_referenced: List[str] = Field(default_factory=list)
    functions_used: List[str] = Field(default_factory=list)

class GoalFailure(GoalResult):
    """Generic failure response when goal cannot be achieved."""
    goal_completed: bool = False
    error_type: str
    error_message: str
    debug_info: Optional[Dict[str, Any]] = None
    suggestions: List[str] = Field(default_factory=list)

# Specific goal types with validation

class OrderProcessingGoal(GoalResult):
    """Goal for processing order placement with reactive updates."""
    goal_type: str = "order_processing"
    
    # Required successful outcomes
    order_id: str = Field(description="ID of the processed order")
    order_status: str = Field(description="Final status of the order")
    customer_updates: Dict[str, Any] = Field(description="Customer statistics updates")
    product_updates: Dict[str, Any] = Field(description="Product inventory updates")
    
    # Optional cascade results
    inventory_alert: Optional[Dict[str, Any]] = None
    tier_update: Optional[Dict[str, Any]] = None
    recommendations: Optional[Dict[str, Any]] = None
    
    @validator('order_status')
    def validate_order_status(cls, v):
        valid_statuses = ['confirmed', 'shipped', 'delivered']
        if v not in valid_statuses:
            raise ValueError(f"Order status must be one of {valid_statuses}")
        return v
    
    @validator('customer_updates')
    def validate_customer_updates(cls, v):
        required_fields = ['total_spending', 'order_count']
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Customer updates must include {field}")
        return v
    
    @validator('product_updates')  
    def validate_product_updates(cls, v):
        required_fields = ['stock_quantity', 'total_sold']
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Product updates must include {field}")
        return v
    
    @root_validator
    def validate_goal_completion(cls, values):
        """Ensure goal is actually completed with valid data."""
        if values.get('goal_completed', False):
            if not values.get('order_id'):
                raise ValueError("Completed order processing must have order_id")
            if not values.get('customer_updates'):
                raise ValueError("Completed order processing must have customer_updates")
            if not values.get('product_updates'):
                raise ValueError("Completed order processing must have product_updates")
        return values

class EntityRetrievalGoal(GoalResult):
    """Goal for retrieving and exploring entity data."""
    goal_type: str = "entity_retrieval"
    
    retrieved_entities: List[Dict[str, Any]] = Field(description="List of retrieved entities")
    lineage_info: Optional[Dict[str, Any]] = None
    entity_relationships: Optional[Dict[str, Any]] = None
    
    @validator('retrieved_entities')
    def validate_retrieved_entities(cls, v):
        if not v:
            raise ValueError("Entity retrieval must return at least one entity")
        
        for entity in v:
            required_fields = ['ecs_id', 'entity_type']
            for field in required_fields:
                if field not in entity:
                    raise ValueError(f"Retrieved entity must include {field}")
        return v
    
    @root_validator
    def validate_goal_completion(cls, values):
        if values.get('goal_completed', False):
            if not values.get('retrieved_entities'):
                raise ValueError("Completed entity retrieval must have retrieved_entities")
        return values

class FunctionExecutionGoal(GoalResult):
    """Goal for executing registered functions with proper validation."""
    goal_type: str = "function_execution"
    
    function_name: str = Field(description="Name of the executed function")
    execution_result: Dict[str, Any] = Field(description="Result of function execution")
    input_parameters: Dict[str, Any] = Field(description="Parameters used for execution")
    execution_metadata: Optional[Dict[str, Any]] = None
    
    @validator('function_name')
    def validate_function_name(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("Function name must be a non-empty string")
        return v
    
    @validator('execution_result')
    def validate_execution_result(cls, v):
        required_fields = ['success', 'result_type']
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Execution result must include {field}")
        return v
    
    @root_validator
    def validate_goal_completion(cls, values):
        if values.get('goal_completed', False):
            execution_result = values.get('execution_result', {})
            if not execution_result.get('success', False):
                raise ValueError("Completed function execution must have successful result")
        return values

class DataExplorationGoal(GoalResult):
    """Goal for exploring and understanding the entity ecosystem."""
    goal_type: str = "data_exploration"
    
    discovery_summary: Dict[str, Any] = Field(description="Summary of discovered data")
    available_functions: Optional[List[str]] = None
    entity_counts: Optional[Dict[str, int]] = None
    relationship_map: Optional[Dict[str, Any]] = None
    
    @validator('discovery_summary')
    def validate_discovery_summary(cls, v):
        if not v:
            raise ValueError("Data exploration must provide discovery summary")
        return v
    
    @root_validator
    def validate_goal_completion(cls, values):
        if values.get('goal_completed', False):
            if not values.get('discovery_summary'):
                raise ValueError("Completed data exploration must have discovery_summary")
        return values

class MultiStepWorkflowGoal(GoalResult):
    """Goal for complex multi-step workflows with intermediate validation."""
    goal_type: str = "multi_step_workflow"
    
    workflow_steps: List[Dict[str, Any]] = Field(description="Completed workflow steps")
    final_state: Dict[str, Any] = Field(description="Final state after all steps")
    intermediate_results: List[Dict[str, Any]] = Field(default_factory=list)
    cascade_effects: Optional[Dict[str, Any]] = None
    
    @validator('workflow_steps')
    def validate_workflow_steps(cls, v):
        if not v:
            raise ValueError("Multi-step workflow must have at least one step")
        
        for i, step in enumerate(v):
            required_fields = ['step_number', 'action', 'success']
            for field in required_fields:
                if field not in step:
                    raise ValueError(f"Step {i} must include {field}")
            
            if not step['success']:
                raise ValueError(f"Step {i} marked as failed - workflow incomplete")
        return v
    
    @validator('final_state')
    def validate_final_state(cls, v):
        if not v:
            raise ValueError("Multi-step workflow must provide final state")
        return v
    
    @root_validator
    def validate_goal_completion(cls, values):
        if values.get('goal_completed', False):
            workflow_steps = values.get('workflow_steps', [])
            if not workflow_steps:
                raise ValueError("Completed workflow must have workflow_steps")
            
            # Ensure all steps are successful
            for step in workflow_steps:
                if not step.get('success', False):
                    raise ValueError("Completed workflow cannot have failed steps")
        return values

# Union type for agent responses
AgentResponse = Union[
    OrderProcessingGoal,
    EntityRetrievalGoal, 
    FunctionExecutionGoal,
    DataExplorationGoal,
    MultiStepWorkflowGoal,
    GoalFailure
]

# Polymorphic factory pattern
class GoalFactory:
    """Factory for creating appropriate goal objects based on task type."""
    
    _goal_registry = {
        "order_processing": OrderProcessingGoal,
        "entity_retrieval": EntityRetrievalGoal,
        "function_execution": FunctionExecutionGoal,
        "data_exploration": DataExplorationGoal,
        "multi_step_workflow": MultiStepWorkflowGoal
    }
    
    @classmethod
    def create_goal(cls, goal_type: str, **kwargs) -> GoalResult:
        """Create a goal object of the appropriate type."""
        goal_class = cls._goal_registry.get(goal_type)
        if not goal_class:
            return GoalFailure(
                goal_type="unknown",
                error_type="invalid_goal_type",
                error_message=f"Unknown goal type: {goal_type}",
                suggestions=[f"Available goal types: {list(cls._goal_registry.keys())}"],
                primary_action="error_handling",
                summary=f"Failed to create goal of type {goal_type}"
            )
        
        try:
            return goal_class(**kwargs)
        except Exception as e:
            return GoalFailure(
                goal_type=goal_type,
                error_type="goal_creation_error", 
                error_message=str(e),
                debug_info={"provided_kwargs": list(kwargs.keys())},
                primary_action="error_handling",
                summary=f"Failed to create {goal_type} goal due to validation error"
            )
    
    @classmethod
    def create_failure(cls, goal_type: str, error_type: str, error_message: str, **kwargs) -> GoalFailure:
        """Create a failure response for any goal type."""
        return GoalFailure(
            goal_type=goal_type,
            error_type=error_type,
            error_message=error_message,
            primary_action="error_handling",
            summary=f"Failed to achieve {goal_type} goal",
            **kwargs
        )
    
    @classmethod
    def get_available_goal_types(cls) -> List[str]:
        """Get list of available goal types."""
        return list(cls._goal_registry.keys())

# Task classification helpers
class TaskClassifier:
    """Classify user requests to determine appropriate goal type."""
    
    @classmethod
    def classify_task(cls, user_request: str) -> str:
        """Classify user request to determine goal type."""
        request_lower = user_request.lower()
        
        # Order processing keywords
        if any(keyword in request_lower for keyword in ['order', 'process', 'purchase', 'buy', 'cascade']):
            return "order_processing"
        
        # Entity retrieval keywords  
        elif any(keyword in request_lower for keyword in ['get', 'retrieve', 'find', 'show', 'entity', 'lineage']):
            return "entity_retrieval"
        
        # Function execution keywords
        elif any(keyword in request_lower for keyword in ['execute', 'run', 'call', 'function']):
            return "function_execution"
        
        # Data exploration keywords
        elif any(keyword in request_lower for keyword in ['explore', 'list', 'available', 'what', 'discover']):
            return "data_exploration"
        
        # Multi-step workflow keywords
        elif any(keyword in request_lower for keyword in ['workflow', 'steps', 'multi', 'sequence', 'chain']):
            return "multi_step_workflow"
        
        # Default to data exploration for unclear requests
        else:
            return "data_exploration"

# Example usage and testing functions
def example_order_processing_goal():
    """Example of creating a successful order processing goal."""
    return GoalFactory.create_goal(
        goal_type="order_processing",
        goal_completed=True,
        primary_action="function_execution",
        summary="Successfully processed customer order with reactive updates",
        order_id="ORD001",
        order_status="confirmed", 
        customer_updates={
            "total_spending": 800.0,
            "order_count": 1,
            "tier": "standard"
        },
        product_updates={
            "stock_quantity": 14,
            "total_sold": 101,
            "popularity_score": 26.0
        },
        entity_ids_referenced=["uuid1", "uuid2", "uuid3"],
        functions_used=["process_order_placement"]
    )

def example_failure_goal():
    """Example of creating a failure response."""
    return GoalFactory.create_failure(
        goal_type="order_processing",
        error_type="validation_error",
        error_message="Invalid entity address format",
        suggestions=["Check UUID format", "Use @uuid.field syntax"],
        debug_info={"invalid_address": "@malformed-uuid"}
    )

if __name__ == "__main__":
    # Test goal creation and validation
    success_goal = example_order_processing_goal()
    print(f"Success goal: {success_goal}")
    
    failure_goal = example_failure_goal()
    print(f"Failure goal: {failure_goal}")
    
    # Test task classification
    classifier = TaskClassifier()
    print(f"Task classification: {classifier.classify_task('process an order with customer data')}")