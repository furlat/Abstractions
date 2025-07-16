# Nested Event Architecture: Pre/Post with Specialized Sub-Events

## Problem with Previous Approach

The factory functions were making premature decisions about operation types at decoration time, duplicating logic that exists in the method implementation.

## Correct Architecture: Nested Pre/Post Events with Multiple Decorators

### Event Flow Pattern

```
Generic Pre-Event (outer decorator)
    ↓
Method execution begins
    ↓
Execution path determined (method logic)
    ↓
Specialized Sub-Pre Event (inner decorator with specialized factory)
    ↓
Actual computation/work
    ↓
Specialized Sub-Post Event (inner decorator with specialized factory)
    ↓
Generic Post-Event (outer decorator)
```

### Multiple Decorator Pattern

```python
@emit_events(
    creating_factory=lambda self: StateTransitionEvent(
        subject_type=type(self),
        subject_id=self.ecs_id,
        from_state="child_entity",
        to_state="root_entity",
        transition_reason="promotion"
    ),
    created_factory=lambda self: StateTransitionEvent(
        subject_type=type(self),
        subject_id=self.ecs_id,
        from_state="child_entity",
        to_state="root_entity",
        transition_reason="promotion"
    )
)
@emit_specialized_events(
    creating_factory=lambda self, execution_context: PromotionEvent[Entity](
        subject_type=type(self),
        subject_id=self.ecs_id,
        from_state="child_entity",
        to_state="root_entity",
        transition_reason="promotion",
        promotion_type=execution_context.promotion_type,
        previous_parent_id=self.root_ecs_id,
        had_parent_tree=self.root_ecs_id is not None
    ),
    created_factory=lambda self, execution_context: PromotedEvent[Entity](
        subject_type=type(self),
        subject_id=self.ecs_id,
        from_state="child_entity",
        to_state="root_entity",
        transition_reason="promotion",
        promotion_type=execution_context.promotion_type,
        new_root_id=self.ecs_id,
        registry_registration_success=execution_context.success
    )
)
def promote_to_root(self) -> None:
    # Generic pre-event already emitted by outer decorator
    
    # Method logic determines actual operation type
    if self.is_root_entity():
        promotion_type = "already_root"
        # Maybe just trigger versioning, no actual promotion
    elif self.root_ecs_id is None:
        promotion_type = "orphan_promotion"
        # Create new tree
    else:
        promotion_type = "detachment_promotion"
        # Detach from existing tree
    
    # Set execution context for specialized decorator
    execution_context = ExecutionContext(
        promotion_type=promotion_type,
        success=True  # Will be updated based on actual outcome
    )
    
    # Specialized sub-pre event emitted by inner decorator
    
    # Do actual computation based on determined path
    try:
        if promotion_type == "already_root":
            EntityRegistry.version_entity(self)
        elif promotion_type == "orphan_promotion":
            self.root_ecs_id = self.ecs_id
            self.root_live_id = self.live_id
            self.update_ecs_ids()
            EntityRegistry.register_entity(self)
        else:  # detachment_promotion
            # More complex detachment logic
            pass
        
        execution_context.success = True
    except Exception as e:
        execution_context.success = False
        raise
    
    # Specialized sub-post event emitted by inner decorator
    # Generic post-event will be emitted by outer decorator
```

### Execution Context Pattern

```python
class ExecutionContext:
    """Context object to pass execution state between method and specialized decorators."""
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

@emit_specialized_events
def specialized_decorator(creating_factory, created_factory):
    """Decorator that emits specialized events based on execution context."""
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create execution context
            execution_context = ExecutionContext()
            
            # Emit specialized pre-event
            if creating_factory:
                pre_event = creating_factory(*args, execution_context=execution_context, **kwargs)
                get_event_bus().emit(pre_event)
            
            # Execute method (which can modify execution_context)
            result = func(*args, execution_context=execution_context, **kwargs)
            
            # Emit specialized post-event
            if created_factory:
                post_event = created_factory(*args, execution_context=execution_context, **kwargs)
                get_event_bus().emit(post_event)
            
            return result
        return wrapper
    return decorator
```

## Benefits of This Architecture

1. **Maintains Pre/Post Consistency**: Both generic and specialized events follow the same pattern
2. **No Logic Duplication**: Specialized events use actual method outcomes
3. **Proper Nesting**: Events are properly nested and related
4. **Accurate Information**: All events reflect actual execution paths
5. **Complete Observability**: Both high-level intent and specific implementation details are captured

## Event Relationships

- Generic events capture **intent** and **overall outcome**
- Specialized events capture **specific implementation details** and **actual execution paths**
- All events are properly nested and can be traced through parent-child relationships
- Event handlers can subscribe to either level of detail as needed

## Implementation Pattern

1. Keep existing `@emit_events` decorators for generic pre/post events
2. Add helper functions to emit specialized sub-events from within method bodies
3. Emit specialized pre-event when execution path is determined
4. Emit specialized post-event when specific operation completes
5. Use actual method results to populate specialized event fields

This architecture respects the pre/post event design while providing the specialized event information based on actual execution paths.