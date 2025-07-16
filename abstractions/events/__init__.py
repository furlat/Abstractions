"""
Events module for entity system.

This module provides event types and functionality for the entity system.
"""

# Export typed events
from .typed_events import (
    VersioningEvent, VersionedEvent, PromotionEvent, PromotedEvent,
    DetachmentEvent, DetachedEvent, AttachmentEvent, AttachedEvent
)

# Export base events
from .events import (
    Event, EventPhase, EventPriority, EventBus, get_event_bus,
    emit_events, on, CreatingEvent, CreatedEvent, ModifyingEvent, ModifiedEvent,
    ProcessingEvent, ProcessedEvent, StateTransitionEvent
)

# Export bridge functions
from .bridge import (
    emit_creation_events, emit_modification_events, emit_processing_events,
    emit_deletion_events, emit_validation_events, emit_simple_event,
    emit_timed_operation, emit_state_transition_events
)

__all__ = [
    # Typed events
    'VersioningEvent', 'VersionedEvent', 'PromotionEvent', 'PromotedEvent',
    'DetachmentEvent', 'DetachedEvent', 'AttachmentEvent', 'AttachedEvent',
    
    # Base events
    'Event', 'EventPhase', 'EventPriority', 'EventBus', 'get_event_bus',
    'emit_events', 'on', 'CreatingEvent', 'CreatedEvent', 'ModifyingEvent', 'ModifiedEvent',
    'ProcessingEvent', 'ProcessedEvent', 'StateTransitionEvent',
    
    # Bridge functions
    'emit_creation_events', 'emit_modification_events', 'emit_processing_events',
    'emit_deletion_events', 'emit_validation_events', 'emit_simple_event',
    'emit_timed_operation', 'emit_state_transition_events'
]