# Correct `create_model` Approach for Dynamic Goal Classes

Based on the Pydantic documentation and existing usage in the abstractions codebase, here's the proper way to create dynamic Goal classes with real type annotations:

## The Problem
We tried using runtime variables in type annotations:
```python
# ❌ WRONG - Variable not allowed in type expression
typed_result: Optional[result_class] = None
```

## The Solution: Use `create_model` with Field Tuples

From the Pydantic docs, `create_model` accepts field definitions as tuples of `(type, default)`:

```python
from typing import Optional, Any
from pydantic import create_model, BaseModel, Field, model_validator
from abstractions.ecs.ecs_address_parser import get

class GoalError(BaseModel):
    """Clean error model for goal failures."""
    error_type: str
    error_message: str
    suggestions: List[str] = Field(default_factory=list)
    debug_info: Dict[str, Any] = Field(default_factory=dict)

class BaseGoal(BaseModel):
    """Base goal with ECS address-based typed result loading."""
    
    model_config = {"validate_assignment": True, "revalidate_instances": "always"}
    
    goal_type: str
    goal_completed: bool = False
    summary: str
    
    # Agent sets this ECS address string
    typed_result_ecs_address: Optional[str] = None
    
    # Gets overridden in dynamic subclasses - this is just base
    typed_result: Optional[Any] = None
    
    # Optional separate error model
    error: Optional[GoalError] = None
    
    @model_validator(mode='after')
    def load_and_validate_typed_result(self):
        """Load typed result and validate required fields."""
        if self.typed_result_ecs_address and not self.typed_result:
            # Load from ECS address
            self.typed_result = get(self.typed_result_ecs_address)
        
        # Validation: Must have (string OR entity) OR error
        has_string = bool(self.typed_result_ecs_address)
        has_entity = bool(self.typed_result)
        has_error = bool(self.error)
        
        if not (has_string or has_entity or has_error):
            raise ValueError("Must provide typed_result_ecs_address, typed_result, or error")
        
        return self

class GoalFactory:
    """Create Goal subclasses with proper typed result fields using create_model."""
    
    _registry = {
        "order_processing": OrderProcessingResult,
        "entity_retrieval": EntityRetrievalResult,
        "function_execution": FunctionExecutionResult,
    }
    
    @classmethod
    def create_goal_class(cls, goal_type: str):
        """Create Goal subclass with properly typed result field."""
        
        result_class = cls._registry.get(goal_type)
        if not result_class:
            raise ValueError(f"Unknown goal type: {goal_type}")
        
        # Use create_model with proper field definition tuple
        dynamic_class_name = f"{goal_type.title().replace('_', '')}Goal"
        
        # Create the dynamic goal class using create_model
        DynamicGoal = create_model(
            dynamic_class_name,
            __base__=BaseGoal,
            __module__=__name__,
            # This is the key - typed_result field with proper type
            typed_result=(Optional[result_class], None),
        )
        
        # Add custom validator for the specific type
        def validate_result_type(self):
            """Ensure typed_result matches expected type for this goal."""
            if self.typed_result and not isinstance(self.typed_result, result_class):
                raise ValueError(f"Expected {result_class.__name__}, got {type(self.typed_result).__name__}")
            return self
        
        # Add the validator to the class
        DynamicGoal.model_validate = model_validator(mode='after')(validate_result_type)
        
        return DynamicGoal
```

## Key Points

1. **Field Definition Tuple**: Use `(Optional[result_class], None)` to specify both type and default
2. **Proper Type Annotations**: The type `Optional[OrderProcessingResult]` becomes real in the generated class
3. **create_model Parameters**: 
   - `__base__=BaseGoal` for inheritance
   - `__module__=__name__` for proper module assignment
4. **Additional Validation**: Add custom validators after class creation
5. **Revalidation**: The `revalidate_instances="always"` config ensures automatic validation

## Expected Result

The generated dynamic class will have:
```python
# Generated dynamically - equivalent to:
class OrderProcessingGoal(BaseGoal):
    typed_result: Optional[OrderProcessingResult] = None
    # ... inherits all other fields from BaseGoal
```

This gives us:
- ✅ Real static typing with `Optional[OrderProcessingResult]`
- ✅ Pydantic revalidation handles type checking automatically  
- ✅ Agent can set `typed_result_ecs_address` or `typed_result` or `error`
- ✅ Clean error handling with separate `GoalError` model
- ✅ No manual type validation needed

The agent gets proper polymorphic types while we leverage Pydantic's own mechanisms for dynamic class creation.