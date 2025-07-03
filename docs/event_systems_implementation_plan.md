# Event-Driven Coordination Layer: Implementation Plan

## Executive Summary

This document provides a comprehensive implementation plan for an event-driven coordination layer that complements the Entity Component System (ECS). The system features a sophisticated type-safe design with generic events, parent-child relationships, efficient subscription routing, and decorator-based auto-instrumentation. The architecture maintains strict separation between the generic event system (`events.py`) and entity-specific implementations (`entity.py`), enabling reuse while preserving type safety.

## 1. Architecture Overview

### 1.1 Core Design Principles

1. **Entity-Agnostic Core**: Events in `events.py` know only about Pydantic BaseModels and UUIDs
2. **Progressive Type Refinement**: Generic events → Entity events → Specific entity type events
3. **Parent-Child Synchronization**: Events can have sub-events that must complete before parent completes
4. **Immutable Event Objects**: Events are create-once, read-many for thread safety
5. **Efficient Routing**: Three-tier subscription system (type → pattern → predicate)
6. **Decorator-Based Instrumentation**: Methods can be wrapped to emit events automatically

### 1.2 Module Structure

```
events.py (Generic Event System)
├── Type definitions and enums
├── Base Event class with generics
├── EventBus implementation
├── Subscription system
├── Decorator factories
└── Utility functions

entity.py (Entity-Specific Events)
├── Entity event subclasses
├── Integration decorators
└── Entity method wrapping

user_code.py (Downstream Usage)
├── Custom entity types
└── Custom event types
```

## 2. Type System Design

### 2.1 Generic Event Base

```python
from typing import TypeVar, Generic, Type, Optional, List, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum

# Type variable for subject references
T = TypeVar('T', bound=BaseModel)

class EventPhase(str, Enum):
    """Lifecycle phases for events"""
    PENDING = "pending"
    STARTED = "started"
    PROGRESS = "progress"
    COMPLETING = "completing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Event(BaseModel, Generic[T]):
    """Base event class with generic type support"""
    # Identity
    id: UUID = Field(default_factory=uuid4)
    type: str = Field(description="Event type identifier")
    phase: EventPhase = Field(default=EventPhase.PENDING)
    
    # Subject reference (type + id)
    subject_type: Optional[Type[T]] = Field(default=None)
    subject_id: Optional[UUID] = Field(default=None)
    
    # Actor reference (who triggered this)
    actor_type: Optional[Type[BaseModel]] = Field(default=None)
    actor_id: Optional[UUID] = Field(default=None)
    
    # Context (additional involved entities)
    context: Dict[str, UUID] = Field(default_factory=dict)
    
    # Temporal
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Lineage
    lineage_id: UUID = Field(default_factory=uuid4)
    parent_id: Optional[UUID] = Field(default=None)
    
    # Sub-events tracking
    children_ids: List[UUID] = Field(default_factory=list)
    pending_children: int = Field(default=0)
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

### 2.2 Generic Event Types

```python
# Creation events
class CreatingEvent(Event[T], Generic[T]):
    """Emitted when object creation begins"""
    type: str = "creating"
    phase: EventPhase = EventPhase.STARTED

class CreatedEvent(Event[T], Generic[T]):
    """Emitted when object creation completes"""
    type: str = "created"
    phase: EventPhase = EventPhase.COMPLETED

# Modification events
class ModifyingEvent(Event[T], Generic[T]):
    """Emitted when object modification begins"""
    type: str = "modifying"
    phase: EventPhase = EventPhase.STARTED
    
class ModifiedEvent(Event[T], Generic[T]):
    """Emitted when object modification completes"""
    type: str = "modified"
    phase: EventPhase = EventPhase.COMPLETED

# Processing events
class ProcessingEvent(Event[T], Generic[T]):
    """Emitted when processing begins"""
    type: str = "processing"
    phase: EventPhase = EventPhase.STARTED
    process_name: str
    
class ProcessedEvent(Event[T], Generic[T]):
    """Emitted when processing completes"""
    type: str = "processed"
    phase: EventPhase = EventPhase.COMPLETED
    process_name: str
    result_id: Optional[UUID] = None
```

## 3. Event Bus Implementation

### 3.1 Subscription Management

```python
from typing import Callable, Union, Pattern, Set, Awaitable
from collections import defaultdict
import asyncio
import inspect

class Subscription:
    """Represents a single event subscription"""
    def __init__(
        self,
        handler: Callable,
        event_types: Optional[Set[Type[Event]]] = None,
        pattern: Optional[Pattern] = None,
        predicate: Optional[Callable[[Event], bool]] = None,
        priority: int = 0
    ):
        self.handler = handler
        self.event_types = event_types or set()
        self.pattern = pattern
        self.predicate = predicate
        self.priority = priority
        self.is_async = inspect.iscoroutinefunction(handler)

class EventBus:
    """Central event routing and distribution system"""
    
    def __init__(self):
        # Type-based index (fastest)
        self._type_subscriptions: Dict[Type[Event], List[Subscription]] = defaultdict(list)
        
        # Pattern-based subscriptions
        self._pattern_subscriptions: List[Subscription] = []
        
        # Predicate-based subscriptions (slowest)
        self._predicate_subscriptions: List[Subscription] = []
        
        # Event history (ring buffer)
        self._history: deque[Event] = deque(maxlen=10000)
        
        # Active parent events awaiting children
        self._pending_parents: Dict[UUID, Event] = {}
        
        # Completion callbacks for parent events
        self._completion_callbacks: Dict[UUID, List[Callable]] = defaultdict(list)
```

### 3.2 Event Emission and Routing

```python
class EventBus:
    async def emit(self, event: Event) -> Event:
        """Emit an event and route to all matching subscribers"""
        
        # Record in history
        self._history.append(event)
        
        # Track parent-child relationships
        if event.parent_id and event.parent_id in self._pending_parents:
            parent = self._pending_parents[event.parent_id]
            parent.children_ids.append(event.id)
            
        # Route to subscribers
        handlers = self._find_matching_handlers(event)
        
        # Execute handlers
        if handlers:
            await self._execute_handlers(event, handlers)
        
        # Handle completion logic
        if event.phase == EventPhase.COMPLETED:
            await self._handle_completion(event)
            
        return event
    
    def _find_matching_handlers(self, event: Event) -> List[Subscription]:
        """Find all subscriptions matching this event"""
        handlers = []
        
        # Type-based matching (O(1))
        event_type = type(event)
        for t in event_type.__mro__:  # Check full inheritance chain
            if t in self._type_subscriptions:
                handlers.extend(self._type_subscriptions[t])
        
        # Pattern-based matching (O(n) but usually small n)
        for sub in self._pattern_subscriptions:
            if sub.pattern.match(event.type):
                handlers.append(sub)
        
        # Predicate-based matching (O(n) and expensive)
        for sub in self._predicate_subscriptions:
            if sub.predicate(event):
                handlers.append(sub)
        
        # Sort by priority
        return sorted(handlers, key=lambda s: s.priority, reverse=True)
```

### 3.3 Parent-Child Synchronization

```python
class EventBus:
    async def emit_with_children(
        self, 
        parent_event: Event,
        child_generators: List[Callable[[], Awaitable[Event]]]
    ) -> Event:
        """Emit parent event and await all children before completion"""
        
        # Emit parent in STARTED phase
        parent_event.phase = EventPhase.STARTED
        parent_event.pending_children = len(child_generators)
        await self.emit(parent_event)
        
        # Track as pending
        self._pending_parents[parent_event.id] = parent_event
        
        # Execute all child generators
        child_tasks = [gen() for gen in child_generators]
        child_events = await asyncio.gather(*child_tasks, return_exceptions=True)
        
        # Handle results
        failed_children = []
        for child in child_events:
            if isinstance(child, Exception):
                failed_children.append(child)
            elif isinstance(child, Event):
                child.parent_id = parent_event.id
                await self.emit(child)
        
        # Complete parent
        if failed_children:
            parent_event.phase = EventPhase.FAILED
            parent_event.metadata['failed_children'] = failed_children
        else:
            parent_event.phase = EventPhase.COMPLETED
            
        # Emit completion
        completion_event = parent_event.model_copy()
        completion_event.id = uuid4()  # New event for completion
        await self.emit(completion_event)
        
        # Clean up
        del self._pending_parents[parent_event.id]
        
        return parent_event
```

## 4. Subscription Patterns

### 4.1 Decorator-Based Subscriptions

```python
# Global event bus instance
event_bus = EventBus()

def on(*event_types: Type[Event], pattern: Optional[str] = None, predicate: Optional[Callable] = None):
    """Decorator for subscribing to events"""
    def decorator(handler: Callable):
        subscription = Subscription(
            handler=handler,
            event_types=set(event_types) if event_types else None,
            pattern=re.compile(pattern) if pattern else None,
            predicate=predicate
        )
        
        # Register subscription
        if event_types:
            for event_type in event_types:
                event_bus._type_subscriptions[event_type].append(subscription)
        elif pattern:
            event_bus._pattern_subscriptions.append(subscription)
        else:
            event_bus._predicate_subscriptions.append(subscription)
            
        return handler
    return decorator

# Usage examples:
@on(CreatedEvent)
async def handle_any_creation(event: CreatedEvent):
    """Handles all creation events"""
    pass

@on(pattern="entity.*")
async def handle_entity_events(event: Event):
    """Handles all entity-related events"""
    pass

@on(predicate=lambda e: e.metadata.get('priority', 0) > 5)
async def handle_high_priority(event: Event):
    """Handles high priority events"""
    pass
```

### 4.2 Method Instrumentation Decorators

```python
def emit_events(
    started_event_factory: Callable[..., Event],
    completed_event_factory: Callable[..., Event],
    failed_event_factory: Optional[Callable[..., Event]] = None
):
    """Decorator that emits events around method execution"""
    
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Create started event
            started_event = started_event_factory(*args, **kwargs)
            
            # Emit with children pattern
            async def execute():
                try:
                    result = await func(*args, **kwargs)
                    
                    # Create completed event
                    completed = completed_event_factory(result, *args, **kwargs)
                    return completed
                    
                except Exception as e:
                    if failed_event_factory:
                        failed = failed_event_factory(e, *args, **kwargs)
                        failed.phase = EventPhase.FAILED
                        return failed
                    raise
            
            return await event_bus.emit_with_children(
                started_event,
                [execute]
            )
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Sync version using asyncio.run
            return asyncio.run(async_wrapper(*args, **kwargs))
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator
```

## 5. Entity-Specific Events (entity.py)

### 5.1 Entity Event Definitions

```python
# In entity.py
from events import CreatingEvent, CreatedEvent, ModifyingEvent, ModifiedEvent, Event
from typing import Optional, List

class EntityCreatingEvent(CreatingEvent[Entity]):
    """Emitted when entity creation begins"""
    type: str = "entity.creating"
    
class EntityCreatedEvent(CreatedEvent[Entity]):
    """Emitted when entity creation completes"""
    type: str = "entity.created"
    root_id: Optional[UUID] = None
    
class EntityVersioningEvent(ModifyingEvent[Entity]):
    """Emitted when entity versioning begins"""
    type: str = "entity.versioning"
    old_version_id: UUID
    
class EntityVersionedEvent(ModifiedEvent[Entity]):
    """Emitted when entity versioning completes"""
    type: str = "entity.versioned"
    old_version_id: UUID
    new_version_id: UUID

class EntityBorrowingEvent(Event[Entity]):
    """Emitted when entity borrows data"""
    type: str = "entity.borrowing"
    source_id: UUID
    field_name: str
    target_field: str
    
class FunctionExecutingEvent(ProcessingEvent[FunctionExecution]):
    """Emitted when function execution begins"""
    type: str = "function.executing"
    function_name: str
    input_ids: List[UUID]
    
class FunctionExecutedEvent(ProcessedEvent[FunctionExecution]):
    """Emitted when function execution completes"""
    type: str = "function.executed"
    function_name: str
    output_ids: List[UUID]
    execution_time: float
```

### 5.2 Entity Method Instrumentation

```python
# Extend Entity class with event emission
class Entity(BaseModel):
    # ... existing entity code ...
    
    @emit_events(
        started_event_factory=lambda self: EntityCreatingEvent(
            subject_type=type(self),
            subject_id=self.ecs_id
        ),
        completed_event_factory=lambda result, self: EntityCreatedEvent(
            subject_type=type(self),
            subject_id=self.ecs_id,
            root_id=self.root_ecs_id
        )
    )
    def promote_to_root(self) -> None:
        """Original promote_to_root with event emission"""
        # ... original implementation ...
    
    @emit_events(
        started_event_factory=lambda self: EntityVersioningEvent(
            subject_type=type(self),
            subject_id=self.ecs_id,
            old_version_id=self.ecs_id
        ),
        completed_event_factory=lambda result, self: EntityVersionedEvent(
            subject_type=type(self),
            subject_id=self.ecs_id,
            old_version_id=self.old_ecs_id,
            new_version_id=self.ecs_id
        )
    )
    def update_ecs_ids(self, new_root_ecs_id: Optional[UUID] = None) -> None:
        """Original update_ecs_ids with event emission"""
        # ... original implementation ...
```

## 6. Performance Optimizations

### 6.1 Event Object Optimizations

```python
class Event(BaseModel):
    class Config:
        # Pydantic optimizations
        validate_assignment = False  # Immutable after creation
        use_enum_values = True
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }
```

### 6.2 Subscription Indexing

```python
class EventBusIndex:
    """Efficient indexing for event subscriptions"""
    
    def __init__(self):
        # Type hierarchy index
        self._type_hierarchy: Dict[Type, Set[Type]] = {}
        
        # Pattern trie for efficient matching
        self._pattern_trie: PatternTrie = PatternTrie()
        
        # Cached handler lists
        self._handler_cache: Dict[Type[Event], List[Subscription]] = {}
    
    def build_type_hierarchy(self, event_type: Type[Event]):
        """Pre-compute type hierarchy for O(1) lookups"""
        ancestors = set()
        for base in event_type.__mro__:
            if issubclass(base, Event) and base != Event:
                ancestors.add(base)
        self._type_hierarchy[event_type] = ancestors
    
    def invalidate_cache(self):
        """Clear cached handler lists when subscriptions change"""
        self._handler_cache.clear()
```

### 6.3 Event Batching

```python
class EventBatch:
    """Batch multiple events for efficient processing"""
    
    def __init__(self, max_size: int = 100, max_delay: float = 0.1):
        self._events: List[Event] = []
        self._max_size = max_size
        self._max_delay = max_delay
        self._flush_task: Optional[asyncio.Task] = None
    
    async def add(self, event: Event):
        """Add event to batch"""
        self._events.append(event)
        
        if len(self._events) >= self._max_size:
            await self.flush()
        elif not self._flush_task:
            self._flush_task = asyncio.create_task(self._delayed_flush())
    
    async def flush(self):
        """Process all batched events"""
        if not self._events:
            return
            
        events = self._events
        self._events = []
        
        # Process in parallel where possible
        await asyncio.gather(*[
            event_bus.emit(event) for event in events
        ])
```

## 7. Integration Points

### 7.1 Callable Registry Integration

```python
# In callable_registry.py
class CallableRegistry:
    @classmethod
    async def aexecute(cls, func_name: str, **kwargs) -> Union[Entity, List[Entity]]:
        """Enhanced execution with event emission"""
        
        # Create execution event
        exec_event = FunctionExecutingEvent(
            subject_type=FunctionExecution,
            function_name=func_name,
            input_ids=[v.ecs_id for v in kwargs.values() if hasattr(v, 'ecs_id')]
        )
        
        async def execute_with_tracking():
            start_time = time.time()
            try:
                result = await cls._execute_async(func_name, **kwargs)
                
                # Extract output IDs
                output_ids = []
                if isinstance(result, Entity):
                    output_ids = [result.ecs_id]
                elif isinstance(result, list):
                    output_ids = [r.ecs_id for r in result if hasattr(r, 'ecs_id')]
                
                # Create completion event
                return FunctionExecutedEvent(
                    subject_type=FunctionExecution,
                    function_name=func_name,
                    output_ids=output_ids,
                    execution_time=time.time() - start_time
                )
            except Exception as e:
                # Failure event
                return FunctionFailedEvent(
                    subject_type=FunctionExecution,
                    function_name=func_name,
                    error=str(e)
                )
        
        # Emit with children pattern
        await event_bus.emit_with_children(exec_event, [execute_with_tracking])
        
        return result
```

### 7.2 Hot Process Detection

```python
# Subscription for detecting newly available processes
@on(EntityCreatedEvent)
async def detect_hot_processes(event: EntityCreatedEvent):
    """Detect processes that became available due to new entity"""
    
    # Get entity type that was created
    new_entity = EntityRegistry.get_stored_entity(
        event.root_id, 
        event.subject_id
    )
    
    if not new_entity:
        return
    
    # Check all registered processes
    for func_name, metadata in CallableRegistry._functions.items():
        # Skip if already executable
        if metadata.input_entity_class is None:
            continue
            
        # Check if this new entity satisfies requirements
        required_types = extract_required_types(metadata.input_entity_class)
        available_types = get_available_types()
        
        if required_types.issubset(available_types):
            # Process became hot!
            await event_bus.emit(ProcessBecameHotEvent(
                subject_type=type(metadata),
                process_name=func_name,
                trigger_entity_id=event.subject_id,
                metadata={
                    'newly_satisfied_type': type(new_entity).__name__,
                    'all_required_types': list(required_types)
                }
            ))
```

## 8. Visualization Support

### 8.1 Event Serialization for WebSocket

```python
class EventSerializer:
    """Serialize events for WebSocket transmission"""
    
    @staticmethod
    def to_json(event: Event) -> str:
        """Convert event to JSON for transmission"""
        return event.model_dump_json(
            exclude_none=True,
            by_alias=True
        )
    
    @staticmethod
    def to_visualization_format(event: Event) -> Dict:
        """Convert event to format optimized for React visualization"""
        return {
            'id': str(event.id),
            'type': event.type,
            'phase': event.phase.value,
            'timestamp': event.timestamp.isoformat(),
            'subject': {
                'type': event.subject_type.__name__ if event.subject_type else None,
                'id': str(event.subject_id) if event.subject_id else None
            },
            'parent_id': str(event.parent_id) if event.parent_id else None,
            'children_ids': [str(cid) for cid in event.children_ids],
            'metadata': event.metadata
        }
```

### 8.2 Event Stream API

```python
class EventStreamAPI:
    """API for streaming events to visualization clients"""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.active_streams: Dict[UUID, WebSocket] = {}
    
    async def stream_events(self, websocket: WebSocket, filters: Optional[Dict] = None):
        """Stream filtered events to websocket client"""
        
        stream_id = uuid4()
        self.active_streams[stream_id] = websocket
        
        # Create filtered subscription
        @on(predicate=self._create_filter_predicate(filters))
        async def stream_handler(event: Event):
            if stream_id in self.active_streams:
                await websocket.send_json(
                    EventSerializer.to_visualization_format(event)
                )
        
        try:
            # Keep connection alive
            while True:
                await asyncio.sleep(1)
                if websocket.client_state != WebSocketState.CONNECTED:
                    break
        finally:
            del self.active_streams[stream_id]
```

## 9. Implementation Phases

### Phase 1: Core Event System (events.py)
1. Base Event class with generics
2. Common event types (Creating, Created, etc.)
3. EventBus with basic routing
4. Simple subscription decorators

### Phase 2: Entity Integration (entity.py)
1. Entity-specific event types
2. Method instrumentation decorators
3. Manual event emission in key methods
4. Basic hot process detection

### Phase 3: Advanced Features
1. Parent-child synchronization
2. Event batching and performance optimization
3. Pattern trie for efficient matching
4. Comprehensive error handling

### Phase 4: Visualization Support
1. WebSocket event streaming
2. Event serialization optimizations
3. Hypergraph construction from events
4. React component data formatting

### Phase 5: Production Hardening
1. Distributed event propagation
2. Event persistence and replay
3. Performance monitoring
4. Comprehensive testing suite

## 10. Testing Strategy

### 10.1 Unit Tests
- Event creation and validation
- Subscription matching logic
- Parent-child synchronization
- Serialization correctness

### 10.2 Integration Tests
- Entity method instrumentation
- CallableRegistry integration
- Hot process detection
- End-to-end event flows

### 10.3 Performance Tests
- Event routing performance
- Subscription scaling
- Memory usage under load
- Concurrent event handling

## Conclusion

This event system provides a sophisticated yet elegant solution for coordinating the ECS with complete type safety, efficient routing, and comprehensive observability. The generic design ensures reusability while the progressive type refinement enables domain-specific functionality. The parent-child synchronization model naturally represents complex operations, and the three-tier subscription system balances flexibility with performance.

The implementation maintains clean separation of concerns, with `events.py` remaining entity-agnostic while `entity.py` adds specific functionality. This architecture supports the theoretical goal of creating information-theoretic agents with full execution transparency and reactive computation patterns.