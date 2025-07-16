# Complete Event Decorator Subclassing Analysis

## Overview of All Event Decorators

From the codebase analysis, I found **5 active event decorators** that could benefit from specialized subclassing:

1. **EntityRegistry.version_entity()** - Uses ModifyingEvent/ModifiedEvent
2. **Entity.promote_to_root()** - Uses StateTransitionEvent
3. **Entity.detach()** - Uses StateTransitionEvent
4. **Entity.attach()** - Uses StateTransitionEvent
5. **CallableRegistry.aexecute()** - Uses ProcessingEvent/ProcessedEvent

## 1. EntityRegistry.version_entity() Event Subclassing

### Current Generic Implementation
```python
@emit_events(
    creating_factory=lambda cls, entity, force_versioning=False: ModifyingEvent(
        subject_type=type(entity),
        subject_id=entity.ecs_id,
        fields=["ecs_id", "version"]
    ),
    created_factory=lambda result, cls, entity, force_versioning=False: ModifiedEvent(
        subject_type=type(entity),
        subject_id=entity.ecs_id,
        fields=["ecs_id", "version"]
    )
)
```

### Proposed Specialized Events
```python
class EntityVersioningEvent(ModifyingEvent):
    """Event for entity versioning operations."""
    versioning_type: str  # "normal", "forced", "initial_registration"
    force_versioning: bool
    has_modifications: bool
    modified_entity_count: int
    tree_root_id: UUID
    lineage_id: UUID
    
class EntityVersionedEvent(ModifiedEvent):
    """Event for completed entity versioning."""
    versioning_type: str
    force_versioning: bool
    version_created: bool
    new_root_id: UUID
    modified_entity_ids: List[UUID]
    id_mapping: Dict[UUID, UUID]  # old_id -> new_id
    versioning_duration: float
    tree_consistency_validated: bool
```

## 2. Entity.promote_to_root() Event Subclassing

### Current Generic Implementation
```python
@emit_events(
    creating_factory=lambda self: StateTransitionEvent(
        subject_type=type(self),
        subject_id=self.ecs_id,
        from_state="child_entity",
        to_state="root_entity",
        transition_reason="promotion"
    )
)
```

### Proposed Specialized Events
```python
class EntityPromotionEvent(StateTransitionEvent):
    """Event for entity promotion to root."""
    promotion_type: str  # "orphan_promotion", "detachment_promotion", "manual_promotion"
    previous_parent_id: Optional[UUID]
    previous_tree_root_id: Optional[UUID]
    previous_lineage_id: Optional[UUID]
    entity_type: Type[Entity]
    had_parent_tree: bool
    
class EntityPromotedEvent(StateTransitionEvent):
    """Event for completed entity promotion."""
    promotion_type: str
    new_root_id: UUID
    new_lineage_id: UUID
    registry_registration_success: bool
    previous_tree_versioned: bool
    promotion_duration: float
```

## 3. Entity.detach() Event Subclassing

### Current Generic Implementation
```python
@emit_events(
    creating_factory=lambda self: StateTransitionEvent(
        subject_type=type(self),
        subject_id=self.ecs_id,
        from_state="attached_entity",
        to_state="detached_entity",
        transition_reason="detachment"
    )
)
```

### Proposed Specialized Events
```python
class EntityDetachmentEvent(StateTransitionEvent):
    """Event for entity detachment operations."""
    detachment_type: str  # "already_root", "orphan_detach", "tree_detach", "missing_tree"
    current_root_id: Optional[UUID]
    current_parent_id: Optional[UUID]
    tree_exists: bool
    entity_in_tree: bool
    
class EntityDetachedEvent(StateTransitionEvent):
    """Event for completed entity detachment."""
    detachment_type: str
    was_promoted_to_root: bool
    parent_tree_versioned: bool
    new_root_id: UUID
    detachment_duration: float
    registry_updated: bool
```

## 4. Entity.attach() Event Subclassing

### Current Generic Implementation
```python
@emit_events(
    creating_factory=lambda self, new_root_entity: StateTransitionEvent(
        subject_type=type(self),
        subject_id=self.ecs_id,
        from_state="root_entity",
        to_state="attached_entity",
        transition_reason="attachment",
        metadata={"new_root_id": str(new_root_entity.ecs_id)}
    )
)
```

### Proposed Specialized Events
```python
class EntityAttachmentEvent(StateTransitionEvent):
    """Event for entity attachment operations."""
    attachment_type: str  # "new_attachment", "re_attachment", "version_only"
    current_root_id: UUID
    target_root_id: UUID
    target_lineage_id: UUID
    same_lineage: bool
    entity_in_target_tree: bool
    
class EntityAttachedEvent(StateTransitionEvent):
    """Event for completed entity attachment."""
    attachment_type: str
    old_root_id: UUID
    new_root_id: UUID
    old_tree_versioned: bool
    new_tree_versioned: bool
    lineage_changed: bool
    attachment_duration: float
```

## 5. CallableRegistry.aexecute() Event Subclassing

Already analyzed in detail in `docs/specialized_event_subclasses_design.md` - needs 5 strategy-specific event pairs.

## Event Factory Pattern for All Decorators

```python
class EntityEventFactory:
    """Factory for creating specialized entity events."""
    
    @staticmethod
    def create_versioning_event(entity: Entity, force_versioning: bool) -> EntityVersioningEvent:
        """Create appropriate versioning event based on entity state."""
        tree = entity.get_tree()
        versioning_type = "forced" if force_versioning else "normal"
        if not EntityRegistry.get_stored_tree(entity.root_ecs_id):
            versioning_type = "initial_registration"
            
        return EntityVersioningEvent(
            subject_type=type(entity),
            subject_id=entity.ecs_id,
            versioning_type=versioning_type,
            force_versioning=force_versioning,
            has_modifications=True,  # Would be calculated
            tree_root_id=entity.root_ecs_id or entity.ecs_id,
            lineage_id=entity.lineage_id
        )
    
    @staticmethod
    def create_promotion_event(entity: Entity) -> EntityPromotionEvent:
        """Create appropriate promotion event based on entity state."""
        promotion_type = "orphan_promotion"
        if entity.root_ecs_id:
            promotion_type = "detachment_promotion"
            
        return EntityPromotionEvent(
            subject_type=type(entity),
            subject_id=entity.ecs_id,
            promotion_type=promotion_type,
            previous_parent_id=entity.root_ecs_id,
            previous_tree_root_id=entity.root_ecs_id,
            previous_lineage_id=entity.lineage_id,
            entity_type=type(entity),
            had_parent_tree=entity.root_ecs_id is not None
        )
    
    # Similar factory methods for detachment, attachment, etc.
```

## Benefits of Comprehensive Subclassing

1. **Rich Context**: Each event captures operation-specific details
2. **Type Safety**: Pydantic validation for each event type
3. **Debugging**: Much easier to understand what happened
4. **Monitoring**: Different operations can be monitored differently
5. **Analytics**: Precise metrics on entity lifecycle patterns
6. **Extensibility**: Easy to add fields to specific event types

## Implementation Priority

1. **High Priority**: CallableRegistry.aexecute() - most complex, most used
2. **Medium Priority**: EntityRegistry.version_entity() - core versioning
3. **Medium Priority**: Entity lifecycle events (promote/detach/attach) - entity management
4. **Low Priority**: Refinements and additional specialized events

## Integration Strategy

Each decorator would use its own factory method:
```python
@emit_events(
    creating_factory=lambda cls, entity, force_versioning=False: 
        EntityEventFactory.create_versioning_event(entity, force_versioning),
    created_factory=lambda result, cls, entity, force_versioning=False:
        EntityEventFactory.create_versioned_event(result, entity, force_versioning)
)
def version_entity(cls, entity: Entity, force_versioning: bool = False):
```

This creates a comprehensive, type-safe event system that provides precise tracking across all entity operations.