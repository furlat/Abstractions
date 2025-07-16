# Entity Events Module Specification

## Overview

This document specifies the exact implementation details for `abstractions/events/entity_events.py` - the specialized module for entity-specific events.

## Module Structure

### Imports
```python
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import Field

# Import base events from events.py
from abstractions.events.events import (
    ProcessingEvent, ProcessedEvent, 
    StateTransitionEvent, ModifyingEvent, ModifiedEvent
)
```

## Event Classes

### 1. Entity Lifecycle Events

#### EntityRegistrationEvent
```python
class EntityRegistrationEvent(ProcessingEvent):
    """Event emitted when entity registration starts."""
    entity_type: str
    entity_id: UUID
    is_root_entity: bool
    has_existing_tree: bool
    registration_type: str  # "new_entity", "tree_update", "re_registration"
    
    # Tree context if available
    expected_tree_nodes: Optional[int] = None
    expected_tree_edges: Optional[int] = None
```

#### EntityRegisteredEvent
```python
class EntityRegisteredEvent(ProcessedEvent):
    """Event emitted when entity registration completes."""
    entity_type: str
    entity_id: UUID
    registration_successful: bool
    
    # Actual tree metrics
    tree_node_count: int
    tree_edge_count: int
    tree_max_depth: int
    
    # Registry updates
    new_lineage_created: bool
    type_registry_updated: bool
```

#### EntityVersioningEvent
```python
class EntityVersioningEvent(ModifyingEvent):
    """Event emitted when entity versioning starts."""
    entity_type: str
    entity_id: UUID
    force_versioning: bool
    
    # Change detection context
    has_stored_version: bool
    change_detection_required: bool
    expected_changes: Optional[int] = None
```

#### EntityVersionedEvent
```python
class EntityVersionedEvent(ModifiedEvent):
    """Event emitted when entity versioning completes."""
    entity_type: str
    entity_id: UUID
    version_created: bool
    
    # Versioning results
    entities_modified: int
    new_ids_created: List[UUID]
    tree_mappings_updated: bool
    
    # Performance metrics
    versioning_duration_ms: Optional[float] = None
```

### 2. Entity Tree Events

#### TreeBuildingEvent
```python
class TreeBuildingEvent(ProcessingEvent):
    """Event emitted when tree building starts."""
    root_entity_type: str
    root_entity_id: UUID
    building_method: str  # "full_build", "incremental_update", "rebuild"
    
    # Build context
    starting_from_storage: bool
    has_existing_tree: bool
```

#### TreeBuiltEvent
```python
class TreeBuiltEvent(ProcessedEvent):
    """Event emitted when tree building completes."""
    root_entity_type: str
    root_entity_id: UUID
    build_successful: bool
    
    # Tree metrics
    node_count: int
    edge_count: int
    max_depth: int
    
    # Build performance
    build_duration_ms: Optional[float] = None
    entities_processed: int
```

#### ChangeDetectionEvent
```python
class ChangeDetectionEvent(ProcessingEvent):
    """Event emitted when change detection starts."""
    detection_method: str  # "greedy", "full_scan", "targeted"
    
    # Tree comparison context
    old_tree_nodes: int
    new_tree_nodes: int
    old_tree_edges: int
    new_tree_edges: int
```

#### ChangesDetectedEvent
```python
class ChangesDetectedEvent(ProcessedEvent):
    """Event emitted when change detection completes."""
    detection_successful: bool
    
    # Change results
    modified_entities_count: int
    added_entities_count: int
    removed_entities_count: int
    moved_entities_count: int
    
    # Performance metrics
    detection_duration_ms: Optional[float] = None
    entities_compared: int
```

### 3. Entity State Transition Events

#### EntityPromotionEvent
```python
class EntityPromotionEvent(StateTransitionEvent):
    """Event emitted when entity promotion starts."""
    entity_type: str
    entity_id: UUID
    
    # Promotion context
    was_orphan: bool
    had_root_reference: bool
    current_root_id: Optional[UUID] = None
    
    # Promotion type
    promotion_reason: str  # "manual", "detachment", "orphan_recovery"
```

#### EntityPromotedEvent
```python
class EntityPromotedEvent(StateTransitionEvent):
    """Event emitted when entity promotion completes."""
    entity_type: str
    entity_id: UUID
    promotion_successful: bool
    
    # Promotion results
    new_root_id: UUID
    registry_updated: bool
    ids_updated: bool
    
    # Performance
    promotion_duration_ms: Optional[float] = None
```

#### EntityDetachmentEvent
```python
class EntityDetachmentEvent(StateTransitionEvent):
    """Event emitted when entity detachment starts."""
    entity_type: str
    entity_id: UUID
    
    # Detachment context
    current_root_id: Optional[UUID] = None
    detachment_scenario: str  # "already_root", "orphan_detach", "tree_removal"
    requires_promotion: bool
```

#### EntityDetachedEvent
```python
class EntityDetachedEvent(StateTransitionEvent):
    """Event emitted when entity detachment completes."""
    entity_type: str
    entity_id: UUID
    detachment_successful: bool
    
    # Detachment results
    was_promoted: bool
    new_root_id: UUID
    old_tree_versioned: bool
    
    # Performance
    detachment_duration_ms: Optional[float] = None
```

#### EntityAttachmentEvent
```python
class EntityAttachmentEvent(StateTransitionEvent):
    """Event emitted when entity attachment starts."""
    entity_type: str
    entity_id: UUID
    
    # Attachment context
    target_root_type: str
    target_root_id: UUID
    lineage_change_required: bool
    same_lineage: bool
```

#### EntityAttachedEvent
```python
class EntityAttachedEvent(StateTransitionEvent):
    """Event emitted when entity attachment completes."""
    entity_type: str
    entity_id: UUID
    attachment_successful: bool
    
    # Attachment results
    old_root_id: UUID
    new_root_id: UUID
    lineage_updated: bool
    ids_updated: bool
    
    # Performance
    attachment_duration_ms: Optional[float] = None
```

### 4. Entity Data Events

#### DataBorrowingEvent
```python
class DataBorrowingEvent(ProcessingEvent):
    """Event emitted when data borrowing starts."""
    borrower_type: str
    borrower_id: UUID
    source_type: str
    source_id: UUID
    
    # Borrowing context
    source_field: str
    target_field: str
    data_type: str
    
    # Borrowing metadata
    is_container_data: bool
    requires_deep_copy: bool
```

#### DataBorrowedEvent
```python
class DataBorrowedEvent(ProcessedEvent):
    """Event emitted when data borrowing completes."""
    borrower_type: str
    borrower_id: UUID
    source_type: str
    source_id: UUID
    borrowing_successful: bool
    
    # Borrowing results
    field_name: str
    provenance_tracked: bool
    container_elements: Optional[int] = None
    
    # Performance
    borrowing_duration_ms: Optional[float] = None
```

#### IDUpdateEvent
```python
class IDUpdateEvent(ProcessingEvent):
    """Event emitted when entity ID update starts."""
    entity_type: str
    entity_id: UUID
    
    # Update context
    update_type: str  # "versioning", "root_change", "lineage_change"
    has_root_update: bool
    has_lineage_update: bool
    
    # Update metadata
    is_root_entity: bool
    affects_children: bool
```

#### IDUpdatedEvent
```python
class IDUpdatedEvent(ProcessedEvent):
    """Event emitted when entity ID update completes."""
    entity_type: str
    old_id: UUID
    new_id: UUID
    update_successful: bool
    
    # Update results
    root_id_updated: bool
    lineage_updated: bool
    timestamps_updated: bool
    
    # Performance
    update_duration_ms: Optional[float] = None
```

## Export List

```python
__all__ = [
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
    
    # Entity state transition events
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
```

## Integration Points

### 1. Entity Registry Operations
- `EntityRegistry.register_entity()` → EntityRegistrationEvent/EntityRegisteredEvent
- `EntityRegistry.version_entity()` → EntityVersioningEvent/EntityVersionedEvent

### 2. Tree Operations
- `build_entity_tree()` → TreeBuildingEvent/TreeBuiltEvent
- `find_modified_entities()` → ChangeDetectionEvent/ChangesDetectedEvent

### 3. Entity Methods
- `Entity.promote_to_root()` → EntityPromotionEvent/EntityPromotedEvent
- `Entity.detach()` → EntityDetachmentEvent/EntityDetachedEvent
- `Entity.attach()` → EntityAttachmentEvent/EntityAttachedEvent
- `Entity.update_ecs_ids()` → IDUpdateEvent/IDUpdatedEvent
- `Entity.borrow_attribute_from()` → DataBorrowingEvent/DataBorrowedEvent

## Event Metadata Design Principles

### 1. Rich Context Information
- Always include entity type and ID
- Provide operation-specific context
- Include performance metrics where relevant

### 2. Operation State Tracking
- Clear before/after state information
- Success/failure indicators
- Error context when applicable

### 3. Performance Monitoring
- Duration tracking for significant operations
- Resource usage metrics
- Scalability information

### 4. Debugging Support
- Clear operation identification
- Hierarchical relationship information
- Comprehensive metadata for troubleshooting

This specification provides complete coverage of entity operations while maintaining clean separation from callable registry concerns.