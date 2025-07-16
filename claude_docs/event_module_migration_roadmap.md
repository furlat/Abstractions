# Event Module Migration Roadmap

## Overview

This document provides a step-by-step roadmap for migrating from the current `typed_events.py` approach to specialized event modules: `entity_events.py` and `callable_events.py`.

## Current State

### Files to Migrate From
- `abstractions/events/typed_events.py` - Contains mixed entity and callable events
- Current entity.py imports - Basic events only
- Current callable_registry.py imports - Basic events only

### Files to Create
- `abstractions/events/entity_events.py` - Entity-specific events
- `abstractions/events/callable_events.py` - Callable registry-specific events

### Files to Update
- `abstractions/ecs/entity.py` - Update imports and decorators
- `abstractions/ecs/callable_registry.py` - Update imports and decorators
- `abstractions/events/__init__.py` - Update exports

### Files to Delete
- `abstractions/events/typed_events.py` - Remove after migration complete

## Migration Steps

### Phase 1: Create Entity Events Module

#### Step 1.1: Create entity_events.py
```bash
# Create the new module
touch abstractions/events/entity_events.py
```

#### Step 1.2: Implement Entity Events
Based on `docs/entity_events_module_specification.md`:

```python
# Copy this exact structure to entity_events.py
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import Field

from abstractions.events.events import (
    ProcessingEvent, ProcessedEvent, 
    StateTransitionEvent, ModifyingEvent, ModifiedEvent
)

# Entity Lifecycle Events
class EntityRegistrationEvent(ProcessingEvent):
    entity_type: str
    entity_id: UUID
    is_root_entity: bool
    has_existing_tree: bool
    registration_type: str
    expected_tree_nodes: Optional[int] = None
    expected_tree_edges: Optional[int] = None

class EntityRegisteredEvent(ProcessedEvent):
    entity_type: str
    entity_id: UUID
    registration_successful: bool
    tree_node_count: int
    tree_edge_count: int
    tree_max_depth: int
    new_lineage_created: bool
    type_registry_updated: bool

# ... (implement all events from specification)
```

#### Step 1.3: Test Entity Events Module
```bash
# Test imports work
python -c "from abstractions.events.entity_events import EntityRegistrationEvent; print('✅ Entity events import successful')"
```

### Phase 2: Update entity.py Integration

#### Step 2.1: Update entity.py Imports
```python
# Replace in entity.py line ~18
# OLD:
from abstractions.events.events import emit_events, StateTransitionEvent, ModifyingEvent, ModifiedEvent

# NEW:
from abstractions.events.events import emit_events
from abstractions.events.entity_events import (
    EntityRegistrationEvent, EntityRegisteredEvent,
    EntityVersioningEvent, EntityVersionedEvent,
    EntityPromotionEvent, EntityPromotedEvent,
    EntityDetachmentEvent, EntityDetachedEvent,
    EntityAttachmentEvent, EntityAttachedEvent,
    DataBorrowingEvent, DataBorrowedEvent,
    IDUpdateEvent, IDUpdatedEvent,
    TreeBuildingEvent, TreeBuiltEvent,
    ChangeDetectionEvent, ChangesDetectedEvent
)
```

#### Step 2.2: Update EntityRegistry.version_entity (Line ~1415)
```python
# Replace existing decorator with:
@emit_events(
    creating_factory=lambda cls, entity, force_versioning=False: EntityVersioningEvent(
        subject_type=type(entity),
        subject_id=entity.ecs_id,
        process_name="entity_versioning",
        entity_type=type(entity).__name__,
        entity_id=entity.ecs_id,
        force_versioning=force_versioning,
        has_stored_version=True,  # Will be determined
        change_detection_required=not force_versioning,
        expected_changes=None
    ),
    created_factory=lambda result, cls, entity, force_versioning=False: EntityVersionedEvent(
        subject_type=type(entity),
        subject_id=entity.ecs_id,
        process_name="entity_versioning",
        entity_type=type(entity).__name__,
        entity_id=entity.ecs_id,
        version_created=result,
        entities_modified=0,  # Will be populated
        new_ids_created=[],   # Will be populated
        tree_mappings_updated=result,
        versioning_duration_ms=None
    )
)
def version_entity(cls, entity: "Entity", force_versioning: bool = False) -> bool:
```

#### Step 2.3: Update Entity.promote_to_root (Line ~1717)
```python
# Replace existing decorator with:
@emit_events(
    creating_factory=lambda self: EntityPromotionEvent(
        subject_type=type(self),
        subject_id=self.ecs_id,
        process_name="entity_promotion",
        from_state="child_entity",
        to_state="root_entity",
        transition_reason="promotion",
        entity_type=type(self).__name__,
        entity_id=self.ecs_id,
        was_orphan=self.is_orphan(),
        had_root_reference=self.root_ecs_id is not None,
        current_root_id=self.root_ecs_id,
        promotion_reason="manual"
    ),
    created_factory=lambda result, self: EntityPromotedEvent(
        subject_type=type(self),
        subject_id=self.ecs_id,
        process_name="entity_promotion",
        from_state="child_entity",
        to_state="root_entity",
        transition_reason="promotion",
        entity_type=type(self).__name__,
        entity_id=self.ecs_id,
        promotion_successful=True,
        new_root_id=self.ecs_id,
        registry_updated=True,
        ids_updated=True,
        promotion_duration_ms=None
    )
)
def promote_to_root(self) -> None:
```

#### Step 2.4: Update Entity.detach (Line ~1735)
```python
# Replace existing decorator with:
@emit_events(
    creating_factory=lambda self: EntityDetachmentEvent(
        subject_type=type(self),
        subject_id=self.ecs_id,
        process_name="entity_detachment",
        from_state="attached_entity",
        to_state="detached_entity",
        transition_reason="detachment",
        entity_type=type(self).__name__,
        entity_id=self.ecs_id,
        current_root_id=self.root_ecs_id,
        detachment_scenario="manual_detach",
        requires_promotion=not self.is_root_entity()
    ),
    created_factory=lambda result, self: EntityDetachedEvent(
        subject_type=type(self),
        subject_id=self.ecs_id,
        process_name="entity_detachment",
        from_state="attached_entity",
        to_state="detached_entity",
        transition_reason="detachment",
        entity_type=type(self).__name__,
        entity_id=self.ecs_id,
        detachment_successful=True,
        was_promoted=True,
        new_root_id=self.ecs_id,
        old_tree_versioned=True,
        detachment_duration_ms=None
    )
)
def detach(self) -> None:
```

#### Step 2.5: Update Entity.attach (Line ~1849)
```python
# Replace existing decorator with:
@emit_events(
    creating_factory=lambda self, new_root_entity: EntityAttachmentEvent(
        subject_type=type(self),
        subject_id=self.ecs_id,
        process_name="entity_attachment",
        from_state="root_entity",
        to_state="attached_entity",
        transition_reason="attachment",
        entity_type=type(self).__name__,
        entity_id=self.ecs_id,
        target_root_type=type(new_root_entity).__name__,
        target_root_id=new_root_entity.ecs_id,
        lineage_change_required=self.lineage_id != new_root_entity.lineage_id,
        same_lineage=self.lineage_id == new_root_entity.lineage_id
    ),
    created_factory=lambda result, self, new_root_entity: EntityAttachedEvent(
        subject_type=type(self),
        subject_id=self.ecs_id,
        process_name="entity_attachment",
        from_state="root_entity",
        to_state="attached_entity",
        transition_reason="attachment",
        entity_type=type(self).__name__,
        entity_id=self.ecs_id,
        attachment_successful=True,
        old_root_id=self.ecs_id,
        new_root_id=new_root_entity.ecs_id,
        lineage_updated=True,
        ids_updated=True,
        attachment_duration_ms=None
    )
)
def attach(self, new_root_entity: "Entity") -> None:
```

#### Step 2.6: Add Missing Entity Decorators

##### Add to EntityRegistry.register_entity (Line ~1347)
```python
@emit_events(
    creating_factory=lambda cls, entity: EntityRegistrationEvent(
        subject_type=type(entity),
        subject_id=entity.ecs_id,
        process_name="entity_registration",
        entity_type=type(entity).__name__,
        entity_id=entity.ecs_id,
        is_root_entity=entity.is_root_entity(),
        has_existing_tree=False,
        registration_type="new_entity",
        expected_tree_nodes=None,
        expected_tree_edges=None
    ),
    created_factory=lambda result, cls, entity: EntityRegisteredEvent(
        subject_type=type(entity),
        subject_id=entity.ecs_id,
        process_name="entity_registration",
        entity_type=type(entity).__name__,
        entity_id=entity.ecs_id,
        registration_successful=True,
        tree_node_count=0,  # Will be populated
        tree_edge_count=0,  # Will be populated
        tree_max_depth=0,   # Will be populated
        new_lineage_created=True,
        type_registry_updated=True
    )
)
def register_entity(cls, entity: "Entity") -> None:
```

##### Add to build_entity_tree (Line ~599)
```python
@emit_events(
    creating_factory=lambda root_entity: TreeBuildingEvent(
        subject_type=type(root_entity),
        subject_id=root_entity.ecs_id,
        process_name="tree_building",
        root_entity_type=type(root_entity).__name__,
        root_entity_id=root_entity.ecs_id,
        building_method="full_build",
        starting_from_storage=False,
        has_existing_tree=False
    ),
    created_factory=lambda result, root_entity: TreeBuiltEvent(
        subject_type=type(root_entity),
        subject_id=root_entity.ecs_id,
        process_name="tree_building",
        root_entity_type=type(root_entity).__name__,
        root_entity_id=root_entity.ecs_id,
        build_successful=True,
        node_count=result.node_count,
        edge_count=result.edge_count,
        max_depth=result.max_depth,
        build_duration_ms=None,
        entities_processed=result.node_count
    )
)
def build_entity_tree(root_entity: "Entity") -> EntityTree:
```

##### Add to Entity.update_ecs_ids (Line ~1641)
```python
@emit_events(
    creating_factory=lambda self, new_root_ecs_id=None, root_entity_live_id=None: IDUpdateEvent(
        subject_type=type(self),
        subject_id=self.ecs_id,
        process_name="id_update",
        entity_type=type(self).__name__,
        entity_id=self.ecs_id,
        update_type="versioning",
        has_root_update=new_root_ecs_id is not None,
        has_lineage_update=False,
        is_root_entity=self.is_root_entity(),
        affects_children=False
    ),
    created_factory=lambda result, self, new_root_ecs_id=None, root_entity_live_id=None: IDUpdatedEvent(
        subject_type=type(self),
        subject_id=self.ecs_id,
        process_name="id_update",
        entity_type=type(self).__name__,
        old_id=self.old_ecs_id,
        new_id=self.ecs_id,
        update_successful=True,
        root_id_updated=new_root_ecs_id is not None,
        lineage_updated=False,
        timestamps_updated=True,
        update_duration_ms=None
    )
)
def update_ecs_ids(self, new_root_ecs_id: Optional[UUID] = None, root_entity_live_id: Optional[UUID] = None) -> None:
```

##### Add to Entity.borrow_attribute_from (Line ~1793)
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
        source_field=target_field,
        target_field=self_field,
        data_type=type(getattr(source_entity, target_field)).__name__,
        is_container_data=isinstance(getattr(source_entity, target_field), (list, dict, set, tuple)),
        requires_deep_copy=True
    ),
    created_factory=lambda result, self, source_entity, target_field, self_field: DataBorrowedEvent(
        subject_type=type(self),
        subject_id=self.ecs_id,
        process_name="data_borrowing",
        borrower_type=type(self).__name__,
        borrower_id=self.ecs_id,
        source_type=type(source_entity).__name__,
        source_id=source_entity.ecs_id,
        borrowing_successful=True,
        field_name=target_field,
        provenance_tracked=True,
        container_elements=None,  # Will be populated if container
        borrowing_duration_ms=None
    )
)
def borrow_attribute_from(self, source_entity: "Entity", target_field: str, self_field: str) -> None:
```

### Phase 3: Create Callable Events Module

#### Step 3.1: Create callable_events.py
```bash
# Create the new module
touch abstractions/events/callable_events.py
```

#### Step 3.2: Implement Callable Events
Based on `docs/callable_events_module_specification.md`:

```python
# Copy this exact structure to callable_events.py
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import Field

from abstractions.events.events import (
    ProcessingEvent, ProcessedEvent
)

# Function Execution Events
class FunctionExecutionEvent(ProcessingEvent):
    function_name: str
    execution_strategy: Optional[str] = None
    input_parameter_count: int
    input_entity_count: int
    input_primitive_count: int
    is_async: bool
    uses_config_entity: bool
    expected_output_count: int
    execution_pattern: str

class FunctionExecutedEvent(ProcessedEvent):
    function_name: str
    execution_successful: bool
    execution_strategy: str
    output_entity_count: int
    semantic_results: List[str]
    execution_duration_ms: float
    total_events_generated: int
    error_message: Optional[str] = None

# ... (implement all events from specification)
```

### Phase 4: Update callable_registry.py Integration

#### Step 4.1: Update callable_registry.py Imports
```python
# Add to callable_registry.py imports
from abstractions.events.callable_events import (
    FunctionExecutionEvent, FunctionExecutedEvent,
    StrategyDetectionEvent, StrategyDetectedEvent,
    InputPreparationEvent, InputPreparedEvent,
    SemanticAnalysisEvent, SemanticAnalyzedEvent,
    UnpackingEvent, UnpackedEvent,
    # ... (all callable events)
)
```

#### Step 4.2: Update CallableRegistry.aexecute (Line ~361)
```python
# Replace existing decorator with:
@emit_events(
    creating_factory=lambda cls, func_name, **kwargs: FunctionExecutionEvent(
        subject_type=None,
        subject_id=None,
        process_name="function_execution",
        function_name=func_name,
        execution_strategy=None,
        input_parameter_count=len(kwargs),
        input_entity_count=sum(1 for v in kwargs.values() if isinstance(v, Entity)),
        input_primitive_count=sum(1 for v in kwargs.values() if not isinstance(v, Entity)),
        is_async=True,
        uses_config_entity=False,  # Will be determined
        expected_output_count=1,   # Will be determined
        execution_pattern="determining"
    ),
    created_factory=lambda result, cls, func_name, **kwargs: FunctionExecutedEvent(
        subject_type=type(result[0]) if isinstance(result, list) else type(result),
        subject_id=result[0].ecs_id if isinstance(result, list) else result.ecs_id,
        process_name="function_execution",
        function_name=func_name,
        execution_successful=True,
        execution_strategy="completed",
        output_entity_count=len(result) if isinstance(result, list) else 1,
        semantic_results=[],  # Will be populated
        execution_duration_ms=0.0,  # Will be calculated
        total_events_generated=0,   # Will be populated
        error_message=None
    )
)
async def aexecute(cls, func_name: str, **kwargs) -> Union[Entity, List[Entity]]:
```

### Phase 5: Update Exports and Clean Up

#### Step 5.1: Update __init__.py
```python
# Add to abstractions/events/__init__.py
from .entity_events import *
from .callable_events import *
```

#### Step 5.2: Test Complete Integration
```bash
# Test entity events
python -c "from abstractions.events.entity_events import EntityRegistrationEvent; print('✅ Entity events work')"

# Test callable events
python -c "from abstractions.events.callable_events import FunctionExecutionEvent; print('✅ Callable events work')"

# Test automatic nesting
python -c "from abstractions.events.events import get_event_bus; print('✅ Event bus works')"
```

#### Step 5.3: Remove typed_events.py
```bash
# Only after confirming everything works
rm abstractions/events/typed_events.py
```

## Testing Strategy

### Phase 1 Testing: Entity Events
1. Test entity event imports
2. Test entity.py decorator updates
3. Test automatic nesting with entity operations
4. Verify no circular dependencies

### Phase 2 Testing: Callable Events
1. Test callable event imports
2. Test callable_registry.py decorator updates
3. Test hierarchical structure (callable → entity events)
4. Verify complete observability

### Phase 3 Testing: Integration
1. Test complete callable registry execution with nested entity events
2. Verify event hierarchy structure
3. Test performance impact
4. Verify backward compatibility

## Success Criteria

- [ ] Entity events module created and working
- [ ] Callable events module created and working
- [ ] All entity operations emit proper events
- [ ] All callable registry operations emit proper events
- [ ] Automatic nesting works correctly
- [ ] Hierarchical event structure (callable → entity)
- [ ] No circular dependencies
- [ ] Performance impact < 5%
- [ ] typed_events.py successfully removed

This roadmap provides a clear path to achieving complete event observability with proper domain separation.