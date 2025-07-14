# Entity Event Integration Analysis

## Current State in entity.py

Looking at the current `entity.py` file, I can see there are already some `@emit_events` decorators:

### Existing Event Decorators:

1. **Line 1415: `EntityRegistry.version_entity`**
   ```python
   @emit_events(
       creating_factory=lambda cls, entity, force_versioning=False: ModifyingEvent(...),
       created_factory=lambda result, cls, entity, force_versioning=False: ModifiedEvent(...)
   )
   def version_entity(cls, entity: "Entity", force_versioning: bool = False) -> bool:
   ```

2. **Line 1717: `Entity.promote_to_root`**
   ```python
   @emit_events(
       creating_factory=lambda self: StateTransitionEvent(
           from_state="child_entity",
           to_state="root_entity",
           transition_reason="promotion"
       )
   )
   def promote_to_root(self) -> None:
   ```

3. **Line 1735: `Entity.detach`**
   ```python
   @emit_events(
       creating_factory=lambda self: StateTransitionEvent(
           from_state="attached_entity", 
           to_state="detached_entity",
           transition_reason="detachment"
       )
   )
   def detach(self) -> None:
   ```

4. **Line 1849: `Entity.attach`**
   ```python
   @emit_events(
       creating_factory=lambda self, new_root_entity: StateTransitionEvent(
           from_state="root_entity",
           to_state="attached_entity", 
           transition_reason="attachment"
       )
   )
   def attach(self, new_root_entity: "Entity") -> None:
   ```

## Key Entity Operations That Need Events

### 1. EntityRegistry Operations
- `register_entity()` - Entity registration
- `register_entity_tree()` - Tree registration
- `version_entity()` - Already has events, needs enhancement
- `get_stored_entity()` - Entity retrieval
- `get_stored_tree()` - Tree retrieval

### 2. Entity Lifecycle Operations
- `promote_to_root()` - Already has events, needs enhancement
- `detach()` - Already has events, needs enhancement
- `attach()` - Already has events, needs enhancement
- `update_ecs_ids()` - Entity versioning
- `borrow_attribute_from()` - Data borrowing

### 3. EntityTree Operations
- `build_entity_tree()` - Tree construction
- `find_modified_entities()` - Change detection
- `update_tree_mappings_after_versioning()` - Tree updates

## Problems with Current Integration

### 1. **Basic Events Only**
Current decorators use basic `ModifyingEvent`, `ModifiedEvent`, and `StateTransitionEvent` instead of specialized typed events from `typed_events.py`.

### 2. **No Automatic Nesting**
Events are not using the automatic nesting system we just built, so they won't have proper parent-child relationships.

### 3. **Missing Key Operations**
Many important entity operations don't have events at all:
- Entity registration
- Tree building
- Entity borrowing
- ID updates

### 4. **No Comprehensive Observability**
We can't see the full entity operation flow, only isolated operations.

## Integration Strategy

### Phase 1: Enhance Existing Events
1. Replace basic events with typed events from `typed_events.py`
2. Add automatic nesting using our enhanced decorator
3. Ensure proper parent-child relationships

### Phase 2: Add Missing Events
1. Add events to `EntityRegistry` operations
2. Add events to tree operations
3. Add events to entity lifecycle operations

### Phase 3: Create Entity-Specific Typed Events
1. Create specialized events for entity operations
2. Use proper inheritance from base events
3. Add entity-specific metadata

## Expected Event Hierarchy

With automatic nesting, when callable registry calls entity operations:

```
FunctionExecutionEvent (callable_registry)
├── EntityRegistrationEvent
│   ├── TreeBuildingEvent
│   │   └── TreeBuiltEvent
│   └── EntityRegisteredEvent
├── EntityVersioningEvent
│   ├── ChangeDetectionEvent
│   │   └── ChangesDetectedEvent
│   ├── IDUpdateEvent
│   │   └── IDUpdatedEvent
│   └── EntityVersionedEvent
└── FunctionExecutedEvent
```

## Next Steps

1. **Analyze current entity operations** - Identify all operations that need events
2. **Create entity-specific typed events** - Extend `typed_events.py` with entity events
3. **Enhance existing decorators** - Use automatic nesting and typed events
4. **Add missing event decorators** - Cover all entity operations
5. **Test entity event integration** - Verify automatic nesting works
6. **Then integrate callable_registry** - Higher-level events that contain entity events

This approach ensures that:
- Entity operations are completely observable
- Callable registry operations automatically contain entity operation events
- We have full hierarchical event structures
- No information is lost or predicted