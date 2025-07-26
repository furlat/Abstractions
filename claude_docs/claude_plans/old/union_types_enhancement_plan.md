# Union Types Enhancement Plan

## Goal: Support Multiple Result Entity Types in a Single Goal

The enhancement will allow the polymorphic goal factory to accept a union of result entity classes, enabling:

1. **Multi-path Goals**: Single goal that can produce different result types
2. **Agent Choice**: Let the agent decide which result type fits best
3. **A/B Testing**: Use examples to bias toward different paths for experimentation

## Current vs Enhanced API

### Current (Single Type)
```python
agent = TypedAgentFactory.create_agent(FunctionExecutionResult)
```

### Enhanced (Union Types)
```python
# Multiple result types - agent chooses based on context
agent = TypedAgentFactory.create_agent([
    FunctionExecutionResult,
    DataProcessingResult,
    NotificationResult
])

# With bias examples toward specific path
bias_examples = """
PREFERRED PATH - Use FunctionExecutionResult when:
- Single function execution is the primary goal
- Simple success/failure tracking is sufficient

Alternative paths available but prefer FunctionExecutionResult unless:
- Multiple functions need coordination (use DataProcessingResult)
- Notification delivery is the focus (use NotificationResult)
"""

agent = TypedAgentFactory.create_agent(
    [FunctionExecutionResult, DataProcessingResult, NotificationResult],
    custom_examples=bias_examples
)
```

## Implementation Plan

### 1. Update Type Signatures

```python
# Support both single type and union types
ResultEntityInput = Union[type[Entity], List[type[Entity]]]

class GoalFactory:
    @classmethod
    def create_goal_class(cls, result_entity_classes: ResultEntityInput):
        """Create Goal subclass supporting single or union result types."""
        
class TypedAgentFactory:
    @classmethod  
    def create_agent(cls, result_entity_classes: ResultEntityInput, custom_examples: Optional[str] = None):
        """Create agent supporting single or union result types."""
```

### 2. Enhanced Goal Class Creation

```python
@classmethod
def create_goal_class(cls, result_entity_classes: ResultEntityInput):
    """Create Goal subclass with single or union typed result field."""
    
    # Normalize input to list
    if not isinstance(result_entity_classes, list):
        result_entity_classes = [result_entity_classes]
    
    # Validate all are Entity subclasses
    for result_class in result_entity_classes:
        if not (isinstance(result_class, type) and issubclass(result_class, Entity)):
            raise ValueError(f"All classes must be Entity subclasses, got {result_class}")
    
    # Derive goal type from first class or create composite name
    if len(result_entity_classes) == 1:
        goal_type = cls._derive_goal_type_from_class(result_entity_classes[0])
        dynamic_class_name = f"{result_entity_classes[0].__name__.replace('Result', '')}Goal"
    else:
        # Composite goal type
        class_names = [cls._derive_goal_type_from_class(c) for c in result_entity_classes]
        goal_type = "_or_".join(class_names)
        dynamic_class_name = f"Multi{len(result_entity_classes)}PathGoal"
    
    # Create union type for typed_result field
    if len(result_entity_classes) == 1:
        result_type_annotation = Optional[result_entity_classes[0]]
    else:
        from typing import Union
        result_type_annotation = Optional[Union[tuple(result_entity_classes)]]
    
    # Create dynamic goal class
    DynamicGoal = create_model(
        dynamic_class_name,
        __base__=BaseGoal,
        __module__=__name__,
        typed_result=(result_type_annotation, None),
    )
    
    return DynamicGoal
```

### 3. Enhanced Prompt Generation

```python
def build_goal_system_prompt(goal_type: str, result_entity_classes: List[type[Entity]], custom_examples: Optional[str] = None) -> str:
    """Build system prompt supporting multiple result entity types."""
    
    components = SystemPromptComponents()
    
    # Generate TARGET RESULT ENTITIES section
    if len(result_entity_classes) == 1:
        result_class = result_entity_classes[0]
        result_docstring = result_class.__doc__ or f"Result entity for {goal_type} operations."
        target_section = f"""
TARGET RESULT ENTITY:
The result entity should be type {result_class.__name__}.

{result_docstring}
"""
    else:
        target_section = "TARGET RESULT ENTITIES (choose the most appropriate):\n\n"
        for i, result_class in enumerate(result_entity_classes, 1):
            result_docstring = result_class.__doc__ or f"Result entity for operations."
            target_section += f"""
{i}. {result_class.__name__}:
{result_docstring}

"""
        target_section += "Choose the result type that best fits the specific task requirements.\n"
    
    # Use custom examples if provided, otherwise use default examples
    examples_section = custom_examples if custom_examples else components.parameter_passing_examples
    
    prompt = f"""
You are handling {goal_type} goals for the Abstractions Entity Framework.

{components.framework_context}

{components.response_options}

{target_section}

{components.available_capabilities}

{examples_section}

{components.addressing_examples}

{components.key_rules}

You MUST provide either typed_result_ecs_address, typed_result, or error.
"""
    
    return prompt
```

### 4. Experimental A/B Testing Setup

```python
def create_experimental_agents(result_types: List[type[Entity]], bias_examples: Dict[str, str]):
    """Create multiple agents with different biases for A/B testing."""
    
    agents = {}
    for bias_name, examples in bias_examples.items():
        agents[bias_name] = TypedAgentFactory.create_agent(
            result_types,
            custom_examples=examples
        )
    
    return agents

# Usage example:
bias_examples = {
    "function_focused": """
BIAS: Prefer FunctionExecutionResult for simple function execution tracking.
Use DataProcessingResult only when complex data transformation details are needed.
""",
    
    "data_focused": """  
BIAS: Prefer DataProcessingResult for comprehensive processing information.
Use FunctionExecutionResult only for simple success/failure cases.
"""
}

experimental_agents = create_experimental_agents(
    [FunctionExecutionResult, DataProcessingResult],
    bias_examples
)

# Test both paths
result_a = await experimental_agents["function_focused"].run(task)
result_b = await experimental_agents["data_focused"].run(task)
```

## Implementation Benefits

### 1. **Flexible Path Selection**
- Agent can choose the most appropriate result type
- Natural language bias through examples
- Dynamic adaptation to task complexity

### 2. **A/B Testing Framework**
- Compare different result structures
- Test agent decision-making patterns
- Evaluate prompt effectiveness

### 3. **Backward Compatibility**
- Single-type usage remains unchanged
- Existing code continues to work
- Progressive enhancement

### 4. **Experimental Possibilities**

```python
# Experiment 1: Simple vs Complex Results
TypedAgentFactory.create_agent([
    SimpleResult,      # Basic success/failure
    DetailedResult     # Rich context and metrics
])

# Experiment 2: Different Domain Focus
TypedAgentFactory.create_agent([
    TechnicalResult,   # Developer-focused output
    BusinessResult     # Stakeholder-focused output  
])

# Experiment 3: Granularity Testing
TypedAgentFactory.create_agent([
    AtomicResult,      # Single operation result
    WorkflowResult     # Multi-step process result
])
```

## Implementation Steps

1. **Phase 1**: Update type signatures and basic union support
2. **Phase 2**: Enhanced prompt generation for multiple types
3. **Phase 3**: Experimental framework and bias testing
4. **Phase 4**: Real-world validation with complex scenarios

## Testing Strategy

### Unit Tests
- Single type (backward compatibility)
- Multiple types (union functionality)
- Invalid inputs (error handling)
- Goal type derivation (composite names)

### Integration Tests  
- Agent creation with unions
- Prompt generation quality
- Pydantic validation of union results
- A/B testing framework

### Experimental Tests
- Path selection accuracy
- Bias effectiveness
- Decision consistency
- Performance comparison

This enhancement would transform the goal factory into a sophisticated experimentation platform while maintaining the clean architecture we've established.