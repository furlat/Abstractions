"""
Typed Events for Entity Operations

This module provides specialized event types for entity operations that inherit
from the base event classes. These are pure type definitions without complex
factory methods that create dependencies.

Like TypeScript types - clean, simple, functional. No over-engineering.
"""

from typing import TypeVar, Generic, Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field

# Import base events (no circular dependency)
from abstractions.events.events import (
    ModifyingEvent, ModifiedEvent, StateTransitionEvent,
    ProcessingEvent, ProcessedEvent
)

# Generic type variable bound to BaseModel
T = TypeVar('T', bound=BaseModel)

# =============================================================================
# VERSIONING EVENTS
# =============================================================================

class VersioningEvent(ModifyingEvent):
    """
    Event for versioning operations.
    
    Usage: VersioningEvent[Entity] for entity versioning.
    Adds versioning-specific fields to the base ModifyingEvent.
    Never redefines existing fields like subject_type, subject_id.
    """
    versioning_type: str = Field(
        description="Type of versioning: normal, forced, initial_registration"
    )
    force_versioning: bool = Field(
        description="Whether versioning was forced"
    )
    has_modifications: bool = Field(
        description="Whether entity has modifications"
    )


class VersionedEvent(ModifiedEvent):
    """
    Event for completed versioning.
    
    Usage: VersionedEvent[Entity] for completed entity versioning.
    Adds versioning completion fields to the base ModifiedEvent.
    """
    versioning_type: str = Field(
        description="Type of versioning that was performed"
    )
    force_versioning: bool = Field(
        description="Whether versioning was forced"
    )
    version_created: bool = Field(
        description="Whether a new version was created"
    )


# =============================================================================
# STATE TRANSITION EVENTS
# =============================================================================

class PromotionEvent(StateTransitionEvent):
    """
    Event for promotion to root.
    
    Usage: PromotionEvent[Entity] for entity promotion.
    Adds promotion-specific fields to the base StateTransitionEvent.
    """
    promotion_type: str = Field(
        description="Type of promotion: orphan_promotion, detachment_promotion, manual_promotion"
    )
    previous_parent_id: Optional[UUID] = Field(
        default=None,
        description="Previous parent entity ID"
    )
    had_parent_tree: bool = Field(
        description="Whether entity had a parent tree"
    )


class PromotedEvent(StateTransitionEvent):
    """
    Event for completed promotion.
    
    Usage: PromotedEvent[Entity] for completed entity promotion.
    Adds promotion completion fields to the base StateTransitionEvent.
    """
    promotion_type: str = Field(
        description="Type of promotion that was performed"
    )
    new_root_id: UUID = Field(
        description="New root entity ID"
    )
    registry_registration_success: bool = Field(
        description="Whether registry registration succeeded"
    )


class DetachmentEvent(StateTransitionEvent):
    """
    Event for detachment operations.
    
    Usage: DetachmentEvent[Entity] for entity detachment.
    Adds detachment-specific fields to the base StateTransitionEvent.
    """
    detachment_type: str = Field(
        description="Type of detachment: already_root, orphan_detach, tree_detach"
    )
    current_root_id: Optional[UUID] = Field(
        default=None,
        description="Current root entity ID"
    )
    requires_promotion: bool = Field(
        description="Whether entity requires promotion"
    )


class DetachedEvent(StateTransitionEvent):
    """
    Event for completed detachment.
    
    Usage: DetachedEvent[Entity] for completed entity detachment.
    Adds detachment completion fields to the base StateTransitionEvent.
    """
    detachment_type: str = Field(
        description="Type of detachment that was performed"
    )
    was_promoted_to_root: bool = Field(
        description="Whether entity was promoted to root"
    )
    new_root_id: UUID = Field(
        description="New root entity ID"
    )


class AttachmentEvent(StateTransitionEvent):
    """
    Event for attachment operations.
    
    Usage: AttachmentEvent[Entity] for entity attachment.
    Adds attachment-specific fields to the base StateTransitionEvent.
    """
    attachment_type: str = Field(
        description="Type of attachment: new_attachment, re_attachment, version_only"
    )
    target_root_id: UUID = Field(
        description="Target root entity ID"
    )
    same_lineage: bool = Field(
        description="Whether attachment is within same lineage"
    )


class AttachedEvent(StateTransitionEvent):
    """
    Event for completed attachment.
    
    Usage: AttachedEvent[Entity] for completed entity attachment.
    Adds attachment completion fields to the base StateTransitionEvent.
    """
    attachment_type: str = Field(
        description="Type of attachment that was performed"
    )
    old_root_id: UUID = Field(
        description="Old root entity ID"
    )
    new_root_id: UUID = Field(
        description="New root entity ID"
    )
    lineage_changed: bool = Field(
        description="Whether lineage changed"
    )


# =============================================================================
# ENTITY LIFECYCLE EVENTS
# =============================================================================

class EntityRegistrationEvent(ProcessingEvent):
    """Event for entity registration start."""
    entity_type: str
    is_root_entity: bool
    has_tree: bool
    registration_type: str  # "new_entity", "existing_tree", "tree_update"

class EntityRegisteredEvent(ProcessedEvent):
    """Event for entity registration completion."""
    entity_type: str
    tree_node_count: int
    tree_edge_count: int
    registration_successful: bool

class EntityVersioningEvent(VersioningEvent):
    """Event for entity versioning start (inherits from existing VersioningEvent)."""
    entity_type: str
    has_changes: bool
    change_count: int

class EntityVersionedEvent(VersionedEvent):
    """Event for entity versioning completion (inherits from existing VersionedEvent)."""
    entity_type: str
    new_version_created: bool
    id_mappings_count: int

# =============================================================================
# ENTITY TREE EVENTS
# =============================================================================

class TreeBuildingEvent(ProcessingEvent):
    """Event for tree building start."""
    root_entity_type: str
    root_entity_id: UUID
    building_method: str  # "full_build", "incremental_update"

class TreeBuiltEvent(ProcessedEvent):
    """Event for tree building completion."""
    node_count: int
    edge_count: int
    max_depth: int
    build_successful: bool

class ChangeDetectionEvent(ProcessingEvent):
    """Event for change detection start."""
    old_tree_nodes: int
    new_tree_nodes: int
    detection_method: str  # "greedy", "full_scan"

class ChangesDetectedEvent(ProcessedEvent):
    """Event for change detection completion."""
    modified_entities_count: int
    added_entities_count: int
    removed_entities_count: int
    moved_entities_count: int

# =============================================================================
# ENTITY OPERATION EVENTS
# =============================================================================

class EntityPromotionEvent(PromotionEvent):
    """Event for entity promotion (inherits from existing PromotionEvent)."""
    entity_type: str
    was_orphan: bool
    had_root_reference: bool

class EntityPromotedEvent(PromotedEvent):
    """Event for entity promotion completion (inherits from existing PromotedEvent)."""
    entity_type: str
    new_root_registration: bool

class EntityDetachmentEvent(DetachmentEvent):
    """Event for entity detachment (inherits from existing DetachmentEvent)."""
    entity_type: str
    detachment_scenario: str  # "already_root", "orphan_promotion", "tree_removal"

class EntityDetachedEvent(DetachedEvent):
    """Event for entity detachment completion (inherits from existing DetachedEvent)."""
    entity_type: str
    promotion_occurred: bool

class EntityAttachmentEvent(AttachmentEvent):
    """Event for entity attachment (inherits from existing AttachmentEvent)."""
    entity_type: str
    target_root_type: str
    lineage_change: bool

class EntityAttachedEvent(AttachedEvent):
    """Event for entity attachment completion (inherits from existing AttachedEvent)."""
    entity_type: str
    attachment_successful: bool

# =============================================================================
# ENTITY DATA EVENTS
# =============================================================================

class DataBorrowingEvent(ProcessingEvent):
    """Event for data borrowing start."""
    borrower_type: str
    borrower_id: UUID
    source_type: str
    source_id: UUID
    field_name: str
    data_type: str

class DataBorrowedEvent(ProcessedEvent):
    """Event for data borrowing completion."""
    borrower_type: str
    borrower_id: UUID
    source_type: str
    source_id: UUID
    field_name: str
    borrowing_successful: bool
    provenance_tracked: bool

class IDUpdateEvent(ProcessingEvent):
    """Event for entity ID update start."""
    entity_type: str
    entity_id: UUID
    update_type: str  # "new_version", "root_change", "lineage_change"
    has_root_update: bool

class IDUpdatedEvent(ProcessedEvent):
    """Event for entity ID update completion."""
    entity_type: str
    old_id: UUID
    new_id: UUID
    update_successful: bool

# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Versioning events
    'VersioningEvent',
    'VersionedEvent',
    
    # State transition events
    'PromotionEvent',
    'PromotedEvent',
    'DetachmentEvent',
    'DetachedEvent',
    'AttachmentEvent',
    'AttachedEvent',
    
    # Entity lifecycle events
    'EntityRegistrationEvent',
    'EntityRegisteredEvent',
    'EntityVersioningEvent',
    'EntityVersionedEvent',
    
    # Entity tree events
    'TreeBuildingEvent',
    'TreeBuiltEvent',
    'ChangeDetectionEvent',
    'ChangesDetectedEvent',
    
    # Entity operation events
    'EntityPromotionEvent',
    'EntityPromotedEvent',
    'EntityDetachmentEvent',
    'EntityDetachedEvent',
    'EntityAttachmentEvent',
    'EntityAttachedEvent',
    
    # Entity data events
    'DataBorrowingEvent',
    'DataBorrowedEvent',
    'IDUpdateEvent',
    'IDUpdatedEvent',
]