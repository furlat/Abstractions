# Simple Entity Event Types: Clean, Functional Approach

## The Problem with My Previous Approach

I was being an idiot and making this way too complicated:

1. **Redefining existing fields**: I was trying to override `subject_type`, `subject_id` etc. that already exist in base Event class
2. **Complex factory mess**: Creating dependency-heavy factory classes in the types file
3. **Object-oriented madness**: Making it OOP when this is a functional framework
4. **Trying to solve everything**: Instead of focusing on entity.py first

## The Simple Solution

typed_events.py should be like a TypeScript types file - **PURE TYPES ONLY**. No factories, no complex methods, no dependencies.

### Clean typed_events.py (Entity Events Only)

```python
# abstractions/events/typed_events.py
from typing import TypeVar, Generic, Optional, List, Dict, Any
from uuid import UUID
from pydantic import Field

# Import base events (no circular dependency)
from abstractions.events.events import (
    ModifyingEvent, ModifiedEvent, StateTransitionEvent
)

# Generic type variable bound to BaseModel
T = TypeVar('T', bound='BaseModel')  # Forward reference

# Entity versioning events - add ONLY new fields, don't redefine existing ones
class EntityVersioningEvent(ModifyingEvent, Generic[T]):
    """Event for entity versioning operations."""
    versioning_type: str = Field(description="Type of versioning: normal, forced, initial_registration")
    force_versioning: bool = Field(description="Whether versioning was forced")
    has_modifications: bool = Field(description="Whether entity has modifications")
    
class EntityVersionedEvent(ModifiedEvent, Generic[T]):
    """Event for completed entity versioning."""
    versioning_type: str = Field(description="Type of versioning that was performed")
    force_versioning: bool = Field(description="Whether versioning was forced")
    version_created: bool = Field(description="Whether a new version was created")
    
# Entity promotion events - add ONLY new fields
class EntityPromotionEvent(StateTransitionEvent, Generic[T]):
    """Event for entity promotion to root."""
    promotion_type: str = Field(description="Type of promotion: orphan_promotion, detachment_promotion, manual_promotion")
    previous_parent_id: Optional[UUID] = Field(default=None, description="Previous parent entity ID")
    had_parent_tree: bool = Field(description="Whether entity had a parent tree")
    
class EntityPromotedEvent(StateTransitionEvent, Generic[T]):
    """Event for completed entity promotion."""
    promotion_type: str = Field(description="Type of promotion that was performed")
    new_root_id: UUID = Field(description="New root entity ID")
    registry_registration_success: bool = Field(description="Whether registry registration succeeded")
    
# Entity detachment events - add ONLY new fields
class EntityDetachmentEvent(StateTransitionEvent, Generic[T]):
    """Event for entity detachment operations."""
    detachment_type: str = Field(description="Type of detachment: already_root, orphan_detach, tree_detach")
    current_root_id: Optional[UUID] = Field(default=None, description="Current root entity ID")
    requires_promotion: bool = Field(description="Whether entity requires promotion")
    
class EntityDetachedEvent(StateTransitionEvent, Generic[T]):
    """Event for completed entity detachment."""
    detachment_type: str = Field(description="Type of detachment that was performed")
    was_promoted_to_root: bool = Field(description="Whether entity was promoted to root")
    new_root_id: UUID = Field(description="New root entity ID")
    
# Entity attachment events - add ONLY new fields
class EntityAttachmentEvent(StateTransitionEvent, Generic[T]):
    """Event for entity attachment operations."""
    attachment_type: str = Field(description="Type of attachment: new_attachment, re_attachment, version_only")
    target_root_id: UUID = Field(description="Target root entity ID")
    same_lineage: bool = Field(description="Whether attachment is within same lineage")
    
class EntityAttachedEvent(StateTransitionEvent, Generic[T]):
    """Event for completed entity attachment."""
    attachment_type: str = Field(description="Type of attachment that was performed")
    old_root_id: UUID = Field(description="Old root entity ID")
    new_root_id: UUID = Field(description="New root entity ID")
    lineage_changed: bool = Field(description="Whether lineage changed")
```

### Factory Methods in entity.py (Where they belong)

```python
# abstractions/ecs/entity.py
from abstractions.events.typed_events import (
    EntityVersioningEvent, EntityVersionedEvent,
    EntityPromotionEvent, EntityPromotedEvent,
    EntityDetachmentEvent, EntityDetachedEvent,
    EntityAttachmentEvent, EntityAttachedEvent
)

# Create concrete type aliases
EntityVersioningEvent = EntityVersioningEvent[Entity]
EntityVersionedEvent = EntityVersionedEvent[Entity]
EntityPromotionEvent = EntityPromotionEvent[Entity]
EntityPromotedEvent = EntityPromotedEvent[Entity]
EntityDetachmentEvent = EntityDetachmentEvent[Entity]
EntityDetachedEvent = EntityDetachedEvent[Entity]
EntityAttachmentEvent = EntityAttachmentEvent[Entity]
EntityAttachedEvent = EntityAttachedEvent[Entity]

# Simple factory functions (not classes) in entity.py where they have access to Entity
def create_versioning_event(entity: Entity, force_versioning: bool) -> EntityVersioningEvent:
    """Create versioning event - this goes in entity.py because it needs Entity data."""
    return EntityVersioningEvent(
        subject_type=type(entity),
        subject_id=entity.ecs_id,
        fields=["ecs_id", "version"],
        versioning_type="forced" if force_versioning else "normal",
        force_versioning=force_versioning,
        has_modifications=True
    )

def create_versioned_event(result: bool, entity: Entity, force_versioning: bool) -> EntityVersionedEvent:
    """Create versioned event - this goes in entity.py because it needs Entity data."""
    return EntityVersionedEvent(
        subject_type=type(entity),
        subject_id=entity.ecs_id,
        fields=["ecs_id", "version"],
        versioning_type="forced" if force_versioning else "normal",
        force_versioning=force_versioning,
        version_created=result
    )

def create_promotion_event(entity: Entity) -> EntityPromotionEvent:
    """Create promotion event - this goes in entity.py because it needs Entity data."""
    return EntityPromotionEvent(
        subject_type=type(entity),
        subject_id=entity.ecs_id,
        from_state="child_entity",
        to_state="root_entity",
        transition_reason="promotion",
        promotion_type="orphan_promotion" if not entity.root_ecs_id else "detachment_promotion",
        previous_parent_id=entity.root_ecs_id,
        had_parent_tree=entity.root_ecs_id is not None
    )

# Updated decorators using simple factory functions
@emit_events(
    creating_factory=lambda cls, entity, force_versioning=False:
        create_versioning_event(entity, force_versioning),
    created_factory=lambda result, cls, entity, force_versioning=False:
        create_versioned_event(result, entity, force_versioning)
)
def version_entity(cls, entity: Entity, force_versioning: bool = False) -> bool:
    # ... existing implementation

@emit_events(
    creating_factory=lambda self: create_promotion_event(self)
)
def promote_to_root(self) -> None:
    # ... existing implementation
```

## Why This Approach Works

1. **typed_events.py is pure types**: No imports, no factories, no complexity
2. **Factory functions in entity.py**: Where they have access to Entity data
3. **No field redefinition**: We only add new fields, never override existing ones
4. **Functional**: Simple functions, not complex factory classes
5. **Clean imports**: No circular dependencies
6. **Type safety**: Full generic typing support
7. **Extensible**: Easy to add new event types

## The Pattern

1. **typed_events.py**: Pure event type definitions with only new fields
2. **entity.py**: Factory functions that create events using Entity data
3. **Decorators**: Use simple factory functions, not complex factory classes

This is like TypeScript types - clean, simple, functional. No over-engineering nonsense.