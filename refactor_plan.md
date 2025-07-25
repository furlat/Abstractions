# Polymorphic Goal Factory Refactoring Plan

## Current Problem Analysis

### Current Architecture Issues
1. **Hardcoded Registry**: [`GoalFactory._registry`](abstractions/registry_agent.py:313) contains hardcoded mappings from strings to result entity classes
2. **String-Based API**: [`TypedAgentFactory.create_agent()`](abstractions/registry_agent.py:351) takes string goal types like `"function_execution"`
3. **Examples Coupled to Module**: Example files import result classes from the main module and use string identifiers
4. **Inflexible Design**: Adding new goal types requires modifying the core module registry

### Current Flow
```
examples/pydantic-ai/single_step_function.py:
  TypedAgentFactory.create_agent("function_execution") 
    ↓
  GoalFactory.create_goal_class("function_execution")
    ↓
  GoalFactory._registry["function_execution"] → FunctionExecutionResult
    ↓
  Creates dynamic goal class with typed_result: Optional[FunctionExecutionResult]
```

## Proposed Solution

### New Architecture
1. **Class-Based API**: Pass actual result entity classes instead of strings
2. **Dynamic Goal Type Derivation**: Derive goal type from class name automatically
3. **Decoupled Examples**: Move example result classes to example files
4. **Flexible Registration**: Allow any Entity subclass to be used as a result type

### New Flow
```
examples/pydantic-ai/single_step_function.py:
  TypedAgentFactory.create_agent(FunctionExecutionResult)  # Pass class directly
    ↓
  GoalFactory.create_goal_class(FunctionExecutionResult)
    ↓
  Derive goal_type = "function_execution" from class name
    ↓
  Creates dynamic goal class with typed_result: Optional[FunctionExecutionResult]
```

## Implementation Plan

### Phase 1: Core Factory Refactoring

#### 1.1 Update [`GoalFactory`](abstractions/registry_agent.py:310)
```python
class GoalFactory:
    """Create Goal subclasses with proper typed result fields using create_model."""
    
    @classmethod
    def create_goal_class(cls, result_entity_class: type[Entity]):
        """Create Goal subclass with properly typed result field from entity class."""
        
        # Validate input
        if not (isinstance(result_entity_class, type) and issubclass(result_entity_class, Entity)):
            raise ValueError(f"result_entity_class must be an Entity subclass, got {result_entity_class}")
        
        # Derive goal type from class name
        goal_type = cls._derive_goal_type_from_class(result_entity_class)
        
        # Create dynamic goal class
        dynamic_class_name = f"{result_entity_class.__name__.replace('Result', '')}Goal"
        
        DynamicGoal = create_model(
            dynamic_class_name,
            __base__=BaseGoal,
            __module__=__name__,
            typed_result=(Optional[result_entity_class], None),
        )
        
        # Set the goal_type on the class
        DynamicGoal.model_config = {**BaseGoal.model_config, "goal_type": goal_type}
        
        return DynamicGoal
    
    @classmethod
    def _derive_goal_type_from_class(cls, result_entity_class: type[Entity]) -> str:
        """Derive goal type string from result entity class name."""
        class_name = result_entity_class.__name__
        
        # Remove 'Result' suffix if present
        if class_name.endswith('Result'):
            class_name = class_name[:-6]  # Remove 'Result'
        
        # Convert CamelCase to snake_case
        import re
        goal_type = re.sub('([A-Z]+)', r'_\1', class_name).lower().lstrip('_')
        
        return goal_type
```

#### 1.2 Update [`TypedAgentFactory`](abstractions/registry_agent.py:347)
```python
class TypedAgentFactory:
    """Create agents with specific goal types."""
    
    @classmethod
    def create_agent(cls, result_entity_class: type[Entity]):
        """Create agent for specific result entity class."""
        
        goal_class = GoalFactory.create_goal_class(result_entity_class)
        goal_type = GoalFactory._derive_goal_type_from_class(result_entity_class)
        
        system_prompt = build_goal_system_prompt(goal_type, result_entity_class)
        
        agent = Agent(
            'anthropic:claude-sonnet-4-20250514',
            output_type=goal_class,
            toolsets=[registry_toolset],
            system_prompt=system_prompt
        )
        
        return agent
```

#### 1.3 Remove Hardcoded Registry
- Remove [`GoalFactory._registry`](abstractions/registry_agent.py:313) entirely
- Remove [`GoalFactory.get_available_goal_types()`](abstractions/registry_agent.py:342) (no longer needed)

### Phase 2: Move Example Classes

#### 2.1 Remove Classes from Main Module
Remove these classes from [`abstractions/registry_agent.py`](abstractions/registry_agent.py:152):
- [`OrderProcessingResult`](abstractions/registry_agent.py:152)
- [`EntityRetrievalResult`](abstractions/registry_agent.py:171) 
- [`FunctionExecutionResult`](abstractions/registry_agent.py:186)

#### 2.2 Add Classes to Example Files

**In [`examples/pydantic-ai/single_step_function.py`](examples/pydantic-ai/single_step_function.py:1):**
```python
# Add at top of file
class FunctionExecutionResult(Entity):
    """Result entity for function execution operations."""
    function_name: str
    success: bool
    result_data: Dict[str, Any]
```

**In [`examples/pydantic-ai/multi_step_workflow.py`](examples/pydantic-ai/multi_step_workflow.py:1):**
- Already has its own result entity classes, so minimal changes needed

### Phase 3: Update Example Usage

#### 3.1 Update [`single_step_function.py`](examples/pydantic-ai/single_step_function.py:56)
```python
# OLD:
execution_agent = TypedAgentFactory.create_agent("function_execution")

# NEW:
execution_agent = TypedAgentFactory.create_agent(FunctionExecutionResult)
```

#### 3.2 Update [`multi_step_workflow.py`](examples/pydantic-ai/multi_step_workflow.py:301)
```python
# OLD:
workflow_agent = TypedAgentFactory.create_agent("function_execution")

# NEW: 
workflow_agent = TypedAgentFactory.create_agent(FunctionExecutionResult)
```

### Phase 4: Update Imports

#### 4.1 Remove Imports from Examples
**In [`single_step_function.py`](examples/pydantic-ai/single_step_function.py:12):**
```python
# OLD:
from abstractions.registry_agent import (
    TypedAgentFactory, GoalFactory, FunctionExecutionResult
)

# NEW:
from abstractions.registry_agent import TypedAgentFactory
```

**In [`multi_step_workflow.py`](examples/pydantic-ai/multi_step_workflow.py:18):**
```python
# OLD:
from abstractions.registry_agent import (
    TypedAgentFactory, GoalFactory, FunctionExecutionResult
)

# NEW:
from abstractions.registry_agent import TypedAgentFactory
```

### Phase 5: Add Validation and Error Handling

#### 5.1 Enhanced Input Validation
```python
@classmethod
def create_goal_class(cls, result_entity_class: type[Entity]):
    """Create Goal subclass with comprehensive validation."""
    
    # Type validation
    if not isinstance(result_entity_class, type):
        raise TypeError(f"Expected a class, got {type(result_entity_class).__name__}")
    
    if not issubclass(result_entity_class, Entity):
        raise TypeError(f"Class must inherit from Entity, got {result_entity_class.__bases__}")
    
    # Name validation
    if not result_entity_class.__name__:
        raise ValueError("Entity class must have a valid __name__")
    
    # Documentation validation (warning only)
    if not result_entity_class.__doc__:
        import warnings
        warnings.warn(f"Entity class {result_entity_class.__name__} has no docstring")
    
    # Continue with goal class creation...
```

#### 5.2 Better Error Messages
```python
def _derive_goal_type_from_class(cls, result_entity_class: type[Entity]) -> str:
    """Derive goal type with detailed error context."""
    try:
        class_name = result_entity_class.__name__
        
        # Handle edge cases
        if not class_name or class_name.startswith('_'):
            raise ValueError(f"Invalid class name: {class_name}")
        
        # Conversion logic with error context
        goal_type = cls._convert_to_snake_case(class_name)
        
        if not goal_type:
            raise ValueError(f"Could not derive goal type from class name: {class_name}")
        
        return goal_type
        
    except Exception as e:
        raise ValueError(f"Failed to derive goal type from {result_entity_class}: {e}") from e
```

## Migration Strategy

### Backward Compatibility Approach
1. **Dual API Support**: Support both string and class-based APIs temporarily
2. **Deprecation Warnings**: Add warnings for string-based usage
3. **Documentation**: Update all examples and docs to use new API
4. **Phased Removal**: Remove string support in next major version

### Implementation Order
1. **Phase 1**: Implement new class-based API alongside existing string API
2. **Phase 2**: Update examples to use new API
3. **Phase 3**: Add deprecation warnings to old API
4. **Phase 4**: Remove old API and hardcoded registry

## Testing Strategy

### Unit Tests Needed
1. **GoalFactory Tests**:
   - Test class validation (valid Entity subclasses)
   - Test invalid inputs (non-classes, non-Entity classes)
   - Test goal type derivation from various class names
   - Test dynamic goal class creation

2. **TypedAgentFactory Tests**:
   - Test agent creation with various result entity classes
   - Test system prompt generation
   - Test integration with pydantic-ai Agent

3. **Integration Tests**:
   - Test complete workflow with example classes
   - Test goal completion and result loading
   - Test error scenarios

### Example Test Cases
```python
def test_goal_factory_with_custom_class():
    """Test GoalFactory with custom result entity class."""
    
    class CustomProcessingResult(Entity):
        process_id: str
        status: str
        data: Dict[str, Any]
    
    goal_class = GoalFactory.create_goal_class(CustomProcessingResult)
    
    assert goal_class.__name__ == "CustomProcessingGoal"
    assert hasattr(goal_class, 'typed_result')
    # Test typed_result field type annotation
    assert goal_class.model_fields['typed_result'].annotation == Optional[CustomProcessingResult]

def test_goal_type_derivation():
    """Test goal type derivation from class names."""
    
    class OrderProcessingResult(Entity):
        pass
    
    class UserAuthResult(Entity):
        pass
        
    class DataTransformationResult(Entity):
        pass
    
    assert GoalFactory._derive_goal_type_from_class(OrderProcessingResult) == "order_processing"
    assert GoalFactory._derive_goal_type_from_class(UserAuthResult) == "user_auth"  
    assert GoalFactory._derive_goal_type_from_class(DataTransformationResult) == "data_transformation"
```

## Benefits of This Refactoring

### 1. **Decoupling**
- Examples no longer depend on hardcoded classes in main module
- Each example can define its own result entity classes
- Core module becomes more focused and reusable

### 2. **Flexibility**
- Any Entity subclass can be used as a result type
- No need to modify core module to add new goal types
- Dynamic goal type derivation from class names

### 3. **Type Safety**
- Better IDE support and autocompletion
- Compile-time type checking for result entity classes
- Clear class-based API is more intuitive

### 4. **Maintainability**
- Eliminates hardcoded registry maintenance
- Clearer separation of concerns
- Easier to extend and customize

### 5. **Discoverability**
- Result entity classes are defined where they're used
- Self-documenting through class names and docstrings
- No hidden string-to-class mappings

## Implementation Files to Modify

1. **Core Module**: [`abstractions/registry_agent.py`](abstractions/registry_agent.py)
   - Remove hardcoded registry and example classes
   - Update GoalFactory and TypedAgentFactory
   - Add validation and error handling

2. **Example Files**:
   - [`examples/pydantic-ai/single_step_function.py`](examples/pydantic-ai/single_step_function.py)
   - [`examples/pydantic-ai/multi_step_workflow.py`](examples/pydantic-ai/multi_step_workflow.py)

3. **New Files** (if needed):
   - Test files for the refactored functionality
   - Migration guide documentation

This refactoring will transform the polymorphic goal system from a rigid, string-based approach to a flexible, class-based design that better aligns with Python's type system and object-oriented principles.