# Entity Event Integration Implementation Plan

## Overview

This document provides a step-by-step implementation plan for integrating typed events with automatic nesting into `entity.py`. This must be completed before the callable registry integration.

## Phase 1: Create Entity-Specific Typed Events

### 1.1 Extend typed_events.py with Entity Events

Add these new event types to `abstractions/events/typed_events.py`:

```python
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
    force_versioning: bool

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
```

## Phase 2: Update Existing Entity Events

### 2.1 Replace EntityRegistry.version_entity

**Current (Lines 1415-1426):**
```python
@emit_events(
    creating_factory=lambda cls, entity, force_versioning=False: ModifyingEvent(...),
    created_factory=lambda result, cls, entity, force_versioning=False: ModifiedEvent(...)
)
def version_entity(cls, entity: "Entity", force_versioning: bool = False) -> bool:
```

**Enhanced:**
```python
@emit_events(
    creating_factory=lambda cls, entity, force_versioning=False: EntityVersioningEvent(
        subject_type=type(entity),
        subject_id=entity.ecs_id,
        process_name="entity_versioning",
        versioning_type="normal" if not force_versioning else "forced",
        force_versioning=force_versioning,
        has_modifications=True,  # Will be determined
        entity_type=type(entity).__name__,
        has_changes=False,  # Will be determined
        change_count=0  # Will be determined
    ),
    created_factory=lambda result, cls, entity, force_versioning=False: EntityVersionedEvent(
        subject_type=type(entity),
        subject_id=entity.ecs_id,
        process_name="entity_versioning",
        versioning_type="normal" if not force_versioning else "forced",
        force_versioning=force_versioning,
        version_created=result,
        entity_type=type(entity).__name__,
        new_version_created=result,
        id_mappings_count=0  # Will be populated
    )
)
def version_entity(cls, entity: "Entity", force_versioning: bool = False) -> bool:
```

### 2.2 Replace Entity.promote_to_root

**Current (Lines 1717-1725):**
```python
@emit_events(
    creating_factory=lambda self: StateTransitionEvent(...)
)
def promote_to_root(self) -> None:
```

**Enhanced:**
```python
@emit_events(
    creating_factory=lambda self: EntityPromotionEvent(
        subject_type=type(self),
        subject_id=self.ecs_id,
        process_name="entity_promotion",
        from_state="child_entity",
        to_state="root_entity",
        transition_reason="promotion",
        promotion_type="manual_promotion",
        previous_parent_id=self.root_ecs_id,
        had_parent_tree=self.root_ecs_id is not None,
        entity_type=type(self).__name__,
        was_orphan=self.is_orphan(),
        had_root_reference=self.root_ecs_id is not None
    ),
    created_factory=lambda result, self: EntityPromotedEvent(
        subject_type=type(self),
        subject_id=self.ecs_id,
        process_name="entity_promotion",
        from_state="child_entity",
        to_state="root_entity",
        transition_reason="promotion",
        promotion_type="manual_promotion",
        new_root_id=self.ecs_id,
        registry_registration_success=True,
        entity_type=type(self).__name__,
        new_root_registration=True
    )
)
def promote_to_root(self) -> None:
```

### 2.3 Replace Entity.detach

**Current (Lines 1735-1743):**
```python
@emit_events(
    creating_factory=lambda self: StateTransitionEvent(...)
)
def detach(self) -> None:
```

**Enhanced:**
```python
@emit_events(
    creating_factory=lambda self: EntityDetachmentEvent(
        subject_type=type(self),
        subject_id=self.ecs_id,
        process_name="entity_detachment",
        from_state="attached_entity",
        to_state="detached_entity",
        transition_reason="detachment",
        detachment_type="manual_detach",
        current_root_id=self.root_ecs_id,
        requires_promotion=not self.is_root_entity(),
        entity_type=type(self).__name__,
        detachment_scenario="user_initiated"
    ),
    created_factory=lambda result, self: EntityDetachedEvent(
        subject_type=type(self),
        subject_id=self.ecs_id,
        process_name="entity_detachment",
        from_state="attached_entity",
        to_state="detached_entity",
        transition_reason="detachment",
        detachment_type="manual_detach",
        was_promoted_to_root=True,
        new_root_id=self.ecs_id,
        entity_type=type(self).__name__,
        promotion_occurred=True
    )
)
def detach(self) -> None:
```

### 2.4 Replace Entity.attach

**Current (Lines 1849-1857):**
```python
@emit_events(
    creating_factory=lambda self, new_root_entity: StateTransitionEvent(...)
)
def attach(self, new_root_entity: "Entity") -> None:
```

**Enhanced:**
```python
@emit_events(
    creating_factory=lambda self, new_root_entity: EntityAttachmentEvent(
        subject_type=type(self),
        subject_id=self.ecs_id,
        process_name="entity_attachment",
        from_state="root_entity",
        to_state="attached_entity",
        transition_reason="attachment",
        attachment_type="manual_attach",
        target_root_id=new_root_entity.ecs_id,
        same_lineage=self.lineage_id == new_root_entity.lineage_id,
        entity_type=type(self).__name__,
        target_root_type=type(new_root_entity).__name__,
        lineage_change=self.lineage_id != new_root_entity.lineage_id
    ),
    created_factory=lambda result, self, new_root_entity: EntityAttachedEvent(
        subject_type=type(self),
        subject_id=self.ecs_id,
        process_name="entity_attachment",
        from_state="root_entity",
        to_state="attached_entity",
        transition_reason="attachment",
        attachment_type="manual_attach",
        old_root_id=self.ecs_id,
        new_root_id=new_root_entity.ecs_id,
        lineage_changed=self.lineage_id != new_root_entity.lineage_id,
        entity_type=type(self).__name__,
        attachment_successful=True
    )
)
def attach(self, new_root_entity: "Entity") -> None:
```

## Phase 3: Add Missing Event Decorators

### 3.1 EntityRegistry.register_entity

**Add to line ~1347:**
```python
@emit_events(
    creating_factory=lambda cls, entity: EntityRegistrationEvent(
        subject_type=type(entity),
        subject_id=entity.ecs_id,
        process_name="entity_registration",
        entity_type=type(entity).__name__,
        is_root_entity=entity.is_root_entity(),
        has_tree=False,  # Will be determined
        registration_type="new_entity"
    ),
    created_factory=lambda result, cls, entity: EntityRegisteredEvent(
        subject_type=type(entity),
        subject_id=entity.ecs_id,
        process_name="entity_registration",
        entity_type=type(entity).__name__,
        tree_node_count=0,  # Will be populated
        tree_edge_count=0,  # Will be populated
        registration_successful=True
    )
)
def register_entity(cls, entity: "Entity") -> None:
```

### 3.2 build_entity_tree function

**Add to line ~599:**
```python
@emit_events(
    creating_factory=lambda root_entity: TreeBuildingEvent(
        subject_type=type(root_entity),
        subject_id=root_entity.ecs_id,
        process_name="tree_building",
        root_entity_type=type(root_entity).__name__,
        root_entity_id=root_entity.ecs_id,
        building_method="full_build"
    ),
    created_factory=lambda result, root_entity: TreeBuiltEvent(
        subject_type=type(root_entity),
        subject_id=root_entity.ecs_id,
        process_name="tree_building",
        node_count=result.node_count,
        edge_count=result.edge_count,
        max_depth=result.max_depth,
        build_successful=True
    )
)
def build_entity_tree(root_entity: "Entity") -> EntityTree:
```

### 3.3 find_modified_entities function

**Add to line ~859:**
```python
@emit_events(
    creating_factory=lambda new_tree, old_tree, greedy=True, debug=False: ChangeDetectionEvent(
        subject_type=None,
        subject_id=None,
        process_name="change_detection",
        old_tree_nodes=old_tree.node_count,
        new_tree_nodes=new_tree.node_count,
        detection_method="greedy" if greedy else "full_scan"
    ),
    created_factory=lambda result, new_tree, old_tree, greedy=True, debug=False: ChangesDetectedEvent(
        subject_type=None,
        subject_id=None,
        process_name="change_detection",
        modified_entities_count=len(result) if not debug else len(result[0]),
        added_entities_count=0,  # Will be populated
        removed_entities_count=0,  # Will be populated
        moved_entities_count=0  # Will be populated
    )
)
def find_modified_entities(
    new_tree: EntityTree,
    old_tree: EntityTree,
    greedy: bool = True,
    debug: bool = False
) -> Union[Set[UUID], Tuple[Set[UUID], Dict[str, Any]]]:
```

### 3.4 Entity.update_ecs_ids

**Add to line ~1641:**
```python
@emit_events(
    creating_factory=lambda self, new_root_ecs_id=None, root_entity_live_id=None: IDUpdateEvent(
        subject_type=type(self),
        subject_id=self.ecs_id,
        process_name="id_update",
        entity_type=type(self).__name__,
        entity_id=self.ecs_id,
        update_type="new_version",
        has_root_update=new_root_ecs_id is not None
    ),
    created_factory=lambda result, self, new_root_ecs_id=None, root_entity_live_id=None: IDUpdatedEvent(
        subject_type=type(self),
        subject_id=self.ecs_id,
        process_name="id_update",
        entity_type=type(self).__name__,
        old_id=self.old_ecs_id,
        new_id=self.ecs_id,
        update_successful=True
    )
)
def update_ecs_ids(self, new_root_ecs_id: Optional[UUID] = None, root_entity_live_id: Optional[UUID] = None) -> None:
```

### 3.5 Entity.borrow_attribute_from

**Add to line ~1793:**
```python
@emit_events(
    creating_factory=lambda self, source_entity, target_field, self_field: DataBorrowingEvent(
        subject_type=type(self),
        subject_id=self.ecs_id,
        process_name="data_borrowing",
        borrower_type=type(self).__name__,
        borrower_id=self.ecs_id,
        source_type=type(source_entity).__name__,
        source_id=source_entity.ecs_id,
        field_name=target_field,
        data_type=type(getattr(source_entity, target_field)).__name__
    ),
    created_factory=lambda result, self, source_entity, target_field, self_field: DataBorrowedEvent(
        subject_type=type(self),
        subject_id=self.ecs_id,
        process_name="data_borrowing",
        borrower_type=type(self).__name__,
        borrower_id=self.ecs_id,
        source_type=type(source_entity).__name__,
        source_id=source_entity.ecs_id,
        field_name=target_field,
        borrowing_successful=True,
        provenance_tracked=True
    )
)
def borrow_attribute_from(self, source_entity: "Entity", target_field: str, self_field: str) -> None:
```

## Phase 4: Implementation Steps

### Step 1: Add Entity Events to typed_events.py
1. Add all entity-specific event types to `abstractions/events/typed_events.py`
2. Ensure proper inheritance from base event classes
3. Add comprehensive field definitions with proper types

### Step 2: Update Existing Decorators
1. Replace basic events with typed events
2. Add automatic nesting context support
3. Update event factories with proper metadata

### Step 3: Add Missing Decorators
1. Add decorators to all key entity operations
2. Ensure proper event nesting
3. Add comprehensive metadata

### Step 4: Test Entity Events
1. Create comprehensive test suite
2. Verify automatic nesting works
3. Test event hierarchy structure

### Step 5: Validate Integration
1. Ensure no circular dependencies
2. Test performance impact
3. Verify backward compatibility

## Expected Benefits

### 1. Complete Entity Observability
- Every entity operation will emit events
- Full audit trail of entity lifecycle
- Comprehensive change tracking

### 2. Automatic Nesting Support
- Entity events will automatically nest under callable registry events
- Proper hierarchical event structure
- No manual parent-child management

### 3. Typed Event Benefits
- Type-safe event handling
- Rich metadata for debugging
- Consistent event structure

### 4. Foundation for Callable Registry
- Entity events will be automatically nested under callable registry events
- No duplication of event logic
- Clean separation of concerns

This implementation provides the foundation for the callable registry event integration while ensuring complete observability of all entity operations.