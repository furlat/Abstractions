# Polymorphic Goal Validation System Design

## Overview

Replace the generic `GoalAchieved` model with a sophisticated polymorphic goal system that:
- Uses modern Pydantic v2 validation patterns
- Integrates goals as entities in the system
- Provides type-safe, goal-specific validation
- Allows agent to return typed success/failure responses

## Current Problems

1. **Generic `data` field**: Untyped `Dict[str, Any]` provides no validation
2. **Old Pydantic patterns**: Using v1 `@validator` instead of v2 `@field_validator`
3. **No entity integration**: Goals aren't part of the entity system
4. **No polymorphic validation**: Single generic response type

## Proposed Architecture

### Base Goal Entity

```python
class GoalEntity(Entity):
    """Base entity for all goal types with string reference to result entity."""
    goal_type: str
    goal_completed: bool = False
    primary_action: str
    summary: str
    entity_ids_referenced: List[str] = Field(default_factory=list)
    functions_used: List[str] = Field(default_factory=list)
    
    # Untyped fallback for additional data
    extra_data: Dict[str, Any] = Field(default_factory=dict)
    
    # Simple string reference to result entity - use get() to retrieve
    result_entity_address: Optional[str] = None
    
    def get_result(self) -> Optional[Entity]:
        """Get the typed result entity using ECS address system."""
        if not self.result_entity_address:
            return None
        return get(self.result_entity_address)
    
    @field_validator('result_entity_address')
    @classmethod
    def validate_result_address(cls, v: Optional[str]) -> Optional[str]:
        """Ensure result address is valid ECS format if provided."""
        if v is not None and not is_address(v):
            raise ValueError("result_entity_address must be valid ECS address format")
        return v
```

### Goal-Specific Result Entities (Pydantic v2)

```python
class OrderProcessingResult(Entity):
    """Entity representing successful order processing result."""
    order_id: str
    order_status: Literal['confirmed', 'shipped', 'delivered']
    customer_updates: CustomerUpdates
    product_updates: ProductUpdates
    inventory_alert: Optional[InventoryAlertData] = None
    tier_update: Optional[TierUpdateData] = None
    
    @field_validator('order_status')
    @classmethod
    def validate_order_status(cls, v: str) -> str:
        if v not in ['confirmed', 'shipped', 'delivered']:
            raise ValueError(f"Invalid order status: {v}")
        return v
    
    @model_validator(mode='after')
    def validate_complete_processing(self) -> 'OrderProcessingResult':
        """Ensure all required processing steps completed."""
        if not self.customer_updates.total_spending_updated:
            raise ValueError("Customer spending must be updated")
        return self

class EntityRetrievalResult(Entity):
    """Entity representing successful entity retrieval result."""
    retrieved_entities: List[EntitySummary] = Field(default_factory=list)
    lineage_info: Optional[LineageData] = None
    relationship_count: int = 0
    
    @field_validator('retrieved_entities')
    @classmethod
    def validate_entities_found(cls, v: List[EntitySummary]) -> List[EntitySummary]:
        if not v:
            raise ValueError("Must retrieve at least one entity")
        return v
    
    @model_validator(mode='after')
    def validate_retrieval_completeness(self) -> 'EntityRetrievalResult':
        """Ensure retrieval has meaningful results."""
        if not self.retrieved_entities and not self.lineage_info:
            raise ValueError("Retrieval must return entities or lineage info")
        return self
```

### Simple Factory Pattern

```python
class GoalFactory:
    """Factory for creating goal entities with string references to result entities."""
    
    _goal_types = {
        "order_processing": {
            "result_entity_class": OrderProcessingResult,
            "description": "Process customer orders with reactive updates"
        },
        "entity_retrieval": {
            "result_entity_class": EntityRetrievalResult,
            "description": "Retrieve and explore entity data"
        }
        # ... more goal types
    }
    
    @classmethod
    def create_goal(
        cls, 
        goal_type: str, 
        result_data: Optional[Dict[str, Any]] = None,
        **base_kwargs
    ) -> Union[GoalEntity, GoalFailure]:
        """Create goal entity with string reference to result entity."""
        
        goal_config = cls._goal_types.get(goal_type)
        if not goal_config:
            return GoalFailure(
                goal_type="unknown",
                error_type="invalid_goal_type",
                error_message=f"Unknown goal type: {goal_type}"
            )
        
        # Create result entity if data provided
        result_address = None
        if result_data:
            try:
                result_entity_class = goal_config["result_entity_class"]
                result_entity = result_entity_class(**result_data)
                result_entity.promote_to_root()
                
                # Store simple string reference
                result_address = f"@{result_entity.ecs_id}"
                
            except ValidationError as e:
                return GoalFailure(
                    goal_type=goal_type,
                    error_type="validation_error",
                    validation_errors=e.errors()
                )
        
        # Create goal entity with string reference
        goal = GoalEntity(
            goal_type=goal_type,
            result_entity_address=result_address,
            **base_kwargs
        )
        
        goal.promote_to_root()
        return goal
```

### Agent Integration

```python
# Agent response type becomes Union of goal entities
AgentResponse = Union[GoalEntity, GoalFailure]

# Agent configured with polymorphic output
registry_agent = Agent(
    'anthropic:claude-sonnet-4-20250514',
    output_type=AgentResponse,  # Polymorphic union type
    toolsets=[registry_toolset],
    system_prompt="""
    You must return either a GoalEntity with typed_result or a GoalFailure.
    
    For successful goals:
    1. Determine goal_type from user request
    2. Populate typed_result with goal-specific data
    3. Ensure all Pydantic v2 validators pass
    
    Goal types available: {goal_types}
    """
)
```

## Implementation Benefits

### 1. Type Safety
- **Compile-time validation**: Typed result fields catch errors early
- **Runtime validation**: Pydantic v2 validators ensure data integrity
- **IDE support**: Full autocomplete and type checking

### 2. Entity System Integration
- **Lineage tracking**: Goals become part of entity versioning
- **Relationship mapping**: Goals reference processed entities
- **Event system**: Goal creation/completion triggers events

### 3. Validation Patterns

```python
class CustomerUpdates(BaseModel):
    total_spending: float = Field(ge=0, description="Updated customer spending")
    order_count: int = Field(ge=0, description="Updated order count")
    tier_changed: bool = False
    
    @field_validator('total_spending')
    @classmethod
    def validate_spending_increase(cls, v: float, info: ValidationInfo) -> float:
        """Ensure spending only increases."""
        if hasattr(info.context, 'previous_spending'):
            if v < info.context['previous_spending']:
                raise ValueError("Spending cannot decrease")
        return v
    
    @model_validator(mode='after')
    def validate_tier_logic(self) -> 'CustomerUpdates':
        """Validate tier change logic."""
        if self.tier_changed and self.total_spending < 500:
            raise ValueError("Tier upgrade requires minimum spending")
        return self
```

### 4. Failure Handling

```python
class GoalFailure(Entity):
    """Entity for failed goal attempts."""
    goal_type: str
    error_type: str
    error_message: str
    validation_errors: Optional[List[Dict[str, Any]]] = None
    suggestions: List[str] = Field(default_factory=list)
    debug_info: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('error_type')
    @classmethod
    def validate_error_type(cls, v: str) -> str:
        valid_types = ['validation_error', 'execution_error', 'address_error']
        if v not in valid_types:
            raise ValueError(f"Invalid error type: {v}")
        return v
```

## Multi-Step Task Orchestration

### Task Definition
```python
class MultiStepTask(Entity):
    """Entity representing a multi-step workflow."""
    task_name: str
    steps: List[TaskStep] = Field(default_factory=list)
    current_step: int = 0
    completed: bool = False
    
    def add_step(self, step_type: str, **kwargs) -> 'MultiStepTask':
        """Add a step to the workflow."""
        step = TaskStep(
            step_number=len(self.steps),
            step_type=step_type,
            **kwargs
        )
        self.steps.append(step)
        return self
    
    @model_validator(mode='after')
    def validate_step_sequence(self) -> 'MultiStepTask':
        """Ensure steps form valid sequence."""
        # Validation logic
        return self
```

### Agent-Driven Orchestration
```python
async def orchestrate_multi_step_task(task: MultiStepTask) -> GoalEntity:
    """Agent-driven task orchestration instead of @on reactions."""
    
    for step in task.steps:
        # Agent determines how to execute step
        step_goal = await registry_agent.run_async(
            f"Execute step {step.step_number}: {step.description}",
            context={"task": task, "previous_steps": task.completed_steps}
        )
        
        # Validate step completion with typed result
        if isinstance(step_goal, GoalFailure):
            return step_goal
        
        # Continue to next step
        task.current_step += 1
    
    # Create final goal with complete workflow result
    return GoalFactory.create_goal(
        goal_type="multi_step_workflow",
        typed_result_data={
            "completed_steps": len(task.steps),
            "final_state": task.get_final_state(),
            "cascade_effects": task.get_cascade_effects()
        }
    )
```

## Next Steps

1. **Create base GoalEntity class** with polymorphic typed_result field
2. **Define goal-specific result models** using Pydantic v2 patterns
3. **Implement GoalFactory** with validation and entity registration
4. **Update registry_agent.py** to use polymorphic goal system
5. **Create multi-step task orchestration** examples
6. **Test validation patterns** with increasingly complex scenarios

## Questions for Discussion

1. **Field naming**: Should `typed_result` be the field name or something else?
2. **Validation context**: How to pass previous state for comparative validation?
3. **Error aggregation**: How to handle multiple validation errors in complex goals?
4. **Goal persistence**: Should goals be automatically registered or manual?
5. **Task orchestration**: Agent-driven vs declarative workflow definition?