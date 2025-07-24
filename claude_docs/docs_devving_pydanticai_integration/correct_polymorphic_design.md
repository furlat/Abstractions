# Correct Polymorphic Goal Design

## What You Actually Asked For

1. **Keep agent output simple** - agent can return string or goal object
2. **Use Pydantic revalidation** - `revalidate_instances="always"` handles type validation automatically
3. **Separate error model** - optional error field, not polluting the goal
4. **Let the type system work** - dynamic goal classes with proper typed_result fields

## Clean Architecture

### Base Goal (Simple)
```python
class BaseGoal(BaseModel):
    model_config = {"validate_assignment": True, "revalidate_instances": "always"}
    
    goal_type: str
    goal_completed: bool = False
    summary: str
    
    # Agent sets this, validator auto-loads typed_result
    typed_result_ecs_address: Optional[str] = None
    
    # Auto-populated from address, gets proper type in subclasses
    typed_result: Optional[Any] = None
    
    # Optional error - separate clean model
    error: Optional["GoalError"] = None
    
    @model_validator(mode='after')
    def load_typed_result(self):
        if self.typed_result_ecs_address and not self.typed_result:
            self.typed_result = get(self.typed_result_ecs_address)
        return self
```

### Separate Error Model
```python
class GoalError(BaseModel):
    """Clean error model - separate from goal"""
    error_type: str
    error_message: str
    suggestions: List[str] = Field(default_factory=list)
    debug_info: Dict[str, Any] = Field(default_factory=dict)
```

### Dynamic Goal Factory (Clean)
```python
class GoalFactory:
    _registry = {
        "order_processing": OrderProcessingResult,
        "entity_retrieval": EntityRetrievalResult,
    }
    
    @classmethod
    def create_goal_class(cls, goal_type: str):
        result_class = cls._registry.get(goal_type)
        if not result_class:
            raise ValueError(f"Unknown goal type: {goal_type}")
        
        class DynamicGoal(BaseGoal):
            # This gets the proper type - revalidation handles validation
            typed_result: Optional[result_class] = None
        
        DynamicGoal.__name__ = f"{goal_type.title().replace('_', '')}Goal"
        return DynamicGoal
```

### Agent Factory (Simple)
```python
class TypedAgentFactory:
    @classmethod
    def create_agent(cls, goal_type: str):
        goal_class = GoalFactory.create_goal_class(goal_type)
        
        # Agent can return string OR goal object
        agent = Agent(
            'anthropic:claude-sonnet-4-20250514',
            output_type=Union[str, goal_class],  # Allow string fallback
            toolsets=[registry_toolset],
            system_prompt=f"""
            You can return either:
            1. A {goal_class.__name__} object for structured results
            2. A simple string for quick responses
            
            For structured results:
            - Set typed_result_ecs_address pointing to result entity
            - Never set typed_result directly
            - Pydantic revalidation handles type checking automatically
            
            For errors:
            - Set error field with GoalError object
            - Or just return a string explaining the problem
            """
        )
        
        return agent
```

## Key Points

1. **No manual type validation** - Pydantic revalidation does it
2. **Clean error handling** - separate GoalError model 
3. **Agent flexibility** - can return string or structured goal
4. **Type safety** - dynamic classes get proper typed_result types
5. **No pollution** - errors don't clutter the goal model

## What Pydantic Revalidation Handles

- When `typed_result` is assigned, revalidation checks it matches the expected type
- No manual isinstance() checks needed
- Clean validation errors if wrong type assigned
- Automatic field validation on every change

This is the simple, clean approach you asked for.