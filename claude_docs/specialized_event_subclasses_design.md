# Specialized Event Subclasses for Precise Function Execution Tracking

## The Vision: Strategy-Specific Event Classes

Instead of generic `ProcessingEvent` and `ProcessedEvent`, we should create specialized Pydantic event subclasses for each execution strategy. This leverages Pydantic's type safety and provides much more informative events.

## Current Generic Approach (Limited)

```python
# Generic events - not very informative
ProcessingEvent(
    subject_type=type(entity),
    subject_id=entity.ecs_id,
    process_name="function_execution"
)

ProcessedEvent(
    subject_type=type(result),
    subject_id=result.ecs_id,
    process_name="function_execution"
)
```

## New Specialized Event Classes

### 1. Single Entity Direct Execution

```python
class SingleEntityDirectProcessingEvent(ProcessingEvent):
    """Event for single entity direct execution pattern."""
    execution_strategy: str = "single_entity_direct"
    primary_entity_type: Type[Entity]
    primary_entity_id: UUID
    function_name: str
    expected_return_type: str
    
class SingleEntityDirectProcessedEvent(ProcessedEvent):
    """Event for completed single entity direct execution."""
    execution_strategy: str = "single_entity_direct"
    input_entity_type: Type[Entity]
    input_entity_id: UUID
    output_entity_type: Type[Entity]
    output_entity_id: UUID
    function_name: str
    execution_duration: float
    semantic_result: str  # "mutation", "creation", "detachment"
```

### 2. Multi-Entity Composite Execution

```python
class MultiEntityCompositeProcessingEvent(ProcessingEvent):
    """Event for multi-entity composite execution pattern."""
    execution_strategy: str = "multi_entity_composite"
    primary_entity_type: Type[Entity]
    primary_entity_id: UUID
    input_entity_types: List[str]
    input_entity_ids: List[UUID]
    composite_entity_expected: bool
    function_name: str
    entity_count: int
    
class MultiEntityCompositeProcessedEvent(ProcessedEvent):
    """Event for completed multi-entity composite execution."""
    execution_strategy: str = "multi_entity_composite"
    input_entity_types: List[str]
    input_entity_ids: List[UUID]
    output_entity_type: Type[Entity]
    output_entity_id: UUID
    function_name: str
    composite_entity_created: bool
    execution_duration: float
    semantic_result: str
```

### 3. Single Entity With Config Execution

```python
class SingleEntityWithConfigProcessingEvent(ProcessingEvent):
    """Event for single entity with config execution pattern."""
    execution_strategy: str = "single_entity_with_config"
    primary_entity_type: Type[Entity]
    primary_entity_id: UUID
    config_entity_type: Optional[Type[ConfigEntity]]
    config_entity_id: Optional[UUID]
    primitive_params: Dict[str, Any]
    function_name: str
    uses_functools_partial: bool
    
class SingleEntityWithConfigProcessedEvent(ProcessedEvent):
    """Event for completed single entity with config execution."""
    execution_strategy: str = "single_entity_with_config"
    input_entity_type: Type[Entity]
    input_entity_id: UUID
    config_entity_type: Optional[Type[ConfigEntity]]
    config_entity_id: Optional[UUID]
    output_entity_type: Type[Entity]
    output_entity_id: UUID
    function_name: str
    config_created_dynamically: bool
    execution_duration: float
    semantic_result: str
```

### 4. No Inputs Execution

```python
class NoInputsProcessingEvent(ProcessingEvent):
    """Event for no inputs execution pattern."""
    execution_strategy: str = "no_inputs"
    function_name: str
    expected_return_type: str
    
class NoInputsProcessedEvent(ProcessedEvent):
    """Event for completed no inputs execution."""
    execution_strategy: str = "no_inputs"
    function_name: str
    output_entity_type: Type[Entity]
    output_entity_id: UUID
    execution_duration: float
    semantic_result: str = "creation"  # Always creation for no-input functions
```

### 5. Pure Borrowing Execution

```python
class PureBorrowingProcessingEvent(ProcessingEvent):
    """Event for pure borrowing execution pattern."""
    execution_strategy: str = "pure_borrowing"
    primary_entity_type: Type[Entity]
    primary_entity_id: UUID
    address_patterns: List[str]
    borrowed_entity_ids: List[UUID]
    function_name: str
    borrowing_pattern: str  # "address_based", "mixed", etc.
    
class PureBorrowingProcessedEvent(ProcessedEvent):
    """Event for completed pure borrowing execution."""
    execution_strategy: str = "pure_borrowing"
    borrowed_entity_ids: List[UUID]
    output_entity_type: Type[Entity]
    output_entity_id: UUID
    function_name: str
    borrowing_sources: Dict[str, UUID]  # field_name -> source_entity_id
    execution_duration: float
    semantic_result: str
```

## Dynamic Event Factory

```python
class FunctionExecutionEventFactory:
    """Factory for creating strategy-specific events."""
    
    @staticmethod
    def create_processing_event(
        strategy: str,
        func_name: str,
        kwargs: Dict[str, Any],
        metadata: FunctionMetadata
    ) -> ProcessingEvent:
        """Create appropriate ProcessingEvent subclass based on strategy."""
        
        if strategy == "single_entity_direct":
            entity = next(v for v in kwargs.values() if isinstance(v, Entity))
            return SingleEntityDirectProcessingEvent(
                primary_entity_type=type(entity),
                primary_entity_id=entity.ecs_id,
                function_name=func_name,
                expected_return_type=metadata.return_analysis.get('pattern', 'unknown')
            )
            
        elif strategy == "multi_entity_composite":
            entities = [v for v in kwargs.values() if isinstance(v, Entity)]
            primary_entity = entities[0]
            return MultiEntityCompositeProcessingEvent(
                primary_entity_type=type(primary_entity),
                primary_entity_id=primary_entity.ecs_id,
                input_entity_types=[type(e).__name__ for e in entities],
                input_entity_ids=[e.ecs_id for e in entities],
                composite_entity_expected=True,
                function_name=func_name,
                entity_count=len(entities)
            )
            
        elif strategy == "single_entity_with_config":
            entity = next((v for v in kwargs.values() if isinstance(v, Entity)), None)
            config_entity = next((v for v in kwargs.values() if isinstance(v, ConfigEntity)), None)
            primitives = {k: v for k, v in kwargs.items() 
                         if not isinstance(v, (Entity, ConfigEntity))}
            
            return SingleEntityWithConfigProcessingEvent(
                primary_entity_type=type(entity) if entity else None,
                primary_entity_id=entity.ecs_id if entity else None,
                config_entity_type=type(config_entity) if config_entity else None,
                config_entity_id=config_entity.ecs_id if config_entity else None,
                primitive_params=primitives,
                function_name=func_name,
                uses_functools_partial=True
            )
            
        elif strategy == "no_inputs":
            return NoInputsProcessingEvent(
                function_name=func_name,
                expected_return_type=metadata.return_analysis.get('pattern', 'unknown')
            )
            
        elif strategy == "pure_borrowing":
            # Extract address patterns and resolve entities
            addresses = [v for v in kwargs.values() if isinstance(v, str) and v.startswith('@')]
            # Use EntityReferenceResolver to get primary entity
            resolver = EntityReferenceResolver(kwargs)
            primary_entity = resolver.get_primary_entity()
            
            return PureBorrowingProcessingEvent(
                primary_entity_type=type(primary_entity) if primary_entity else None,
                primary_entity_id=primary_entity.ecs_id if primary_entity else None,
                address_patterns=addresses,
                borrowed_entity_ids=resolver.get_all_referenced_entity_ids(),
                function_name=func_name,
                borrowing_pattern="address_based"
            )
    
    @staticmethod
    def create_processed_event(
        strategy: str,
        result: Any,
        func_name: str,
        original_kwargs: Dict[str, Any],
        execution_duration: float,
        semantic_result: str
    ) -> ProcessedEvent:
        """Create appropriate ProcessedEvent subclass based on strategy."""
        # Similar implementation for processed events...
```

## Updated Decorator Implementation

```python
@emit_events(
    creating_factory=lambda cls, func_name, **kwargs: cls._create_processing_event(func_name, kwargs),
    created_factory=lambda result, cls, func_name, **kwargs: cls._create_processed_event(result, func_name, kwargs)
)
async def aexecute(cls, func_name: str, **kwargs):
    return await cls._execute_async(func_name, **kwargs)

@classmethod
def _create_processing_event(cls, func_name: str, kwargs: Dict[str, Any]) -> ProcessingEvent:
    """Create strategy-specific processing event."""
    metadata = cls.get_metadata(func_name)
    strategy = cls._detect_execution_strategy(kwargs, metadata)
    return FunctionExecutionEventFactory.create_processing_event(strategy, func_name, kwargs, metadata)

@classmethod
def _create_processed_event(cls, result: Any, func_name: str, kwargs: Dict[str, Any]) -> ProcessedEvent:
    """Create strategy-specific processed event."""
    metadata = cls.get_metadata(func_name)
    strategy = cls._detect_execution_strategy(kwargs, metadata)
    # Would need to track execution timing and semantic result
    return FunctionExecutionEventFactory.create_processed_event(strategy, result, func_name, kwargs, 0.0, "creation")
```

## Benefits of This Approach

1. **Type Safety**: Each event class has appropriate fields for its strategy
2. **Rich Information**: Strategy-specific metadata captured precisely
3. **Pydantic Power**: Validation, serialization, and type checking
4. **Debugging**: Much easier to understand what happened from events
5. **Monitoring**: Different strategies can be monitored differently
6. **Extensibility**: Easy to add new fields to specific event types

This creates a much more informative and maintainable event system that leverages Pydantic's strengths while providing precise tracking of the actual execution dynamics.