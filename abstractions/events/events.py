"""
Event-Driven Coordination Layer for Entity Component Systems

This module provides a generic, type-safe event system that enables reactive computation
patterns while maintaining strict separation from the ECS data layer. Events are lightweight
signals that reference entities by UUID and type, supporting parent-child relationships,
efficient routing, and comprehensive observability.
"""

from typing import (
    TypeVar, Generic, Type, Optional, List, Dict, Any, Set, Union, Callable,
    Awaitable, Pattern, Tuple, cast, Protocol, runtime_checkable
)
from pydantic import BaseModel, Field, ConfigDict, model_validator
from uuid import UUID, uuid4
from datetime import datetime, timezone
from enum import Enum
from collections import defaultdict, deque
from dataclasses import dataclass, field
import asyncio
import inspect
import functools
import re
import time
import json
import weakref
from contextlib import asynccontextmanager
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Type variable for subject references - bound to BaseModel for type safety
T = TypeVar('T', bound=BaseModel)
S = TypeVar('S', bound=BaseModel)

# Global event bus instance - initialized at module level
_event_bus: Optional['EventBus'] = None


def get_event_bus() -> 'EventBus':
    """Get or create the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    
    # Auto-start if not running and we're in an async context
    try:
        loop = asyncio.get_running_loop()
        if not _event_bus._processor_task:
            loop.create_task(_event_bus.start())
    except RuntimeError:
        # No event loop running - will be started when called from async context
        pass
    
    return _event_bus


# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================

class EventPhase(str, Enum):
    """Lifecycle phases for events - represents temporal progression."""
    PENDING = "pending"          # Event created but not started
    STARTED = "started"          # Operation has begun
    PROGRESS = "progress"        # Operation in progress (for long operations)
    COMPLETING = "completing"    # Operation finishing up
    COMPLETED = "completed"      # Operation successfully completed
    FAILED = "failed"           # Operation failed with error
    CANCELLED = "cancelled"     # Operation was cancelled
    TIMEOUT = "timeout"         # Operation timed out


class EventPriority(int, Enum):
    """Priority levels for event handling order."""
    CRITICAL = 1000
    HIGH = 100
    NORMAL = 10
    LOW = 1


# ============================================================================
# BASE EVENT CLASS
# ============================================================================

class Event(BaseModel, Generic[T]):
    """
    Base event class with generic type support.
    
    Events are immutable signals that reference entities by type and ID,
    supporting parent-child relationships and rich metadata.
    """
    model_config = ConfigDict(
        validate_assignment=False,  # Immutable after creation
        use_enum_values=True,
        json_encoders={
            UUID: str,
            datetime: lambda v: v.isoformat(),
            type: lambda t: t.__name__ if hasattr(t, '__name__') else str(t)
        }
    )
    
    # Identity
    id: UUID = Field(default_factory=uuid4, description="Unique event identifier")
    type: str = Field(description="Event type identifier for routing")
    phase: EventPhase = Field(default=EventPhase.PENDING, description="Current lifecycle phase")
    
    # Subject reference (what this event is about)
    subject_type: Optional[Type[T]] = Field(default=None, description="Type of subject entity")
    subject_id: Optional[UUID] = Field(default=None, description="ID of subject entity")
    
    # Actor reference (who triggered this event)
    actor_type: Optional[Type[BaseModel]] = Field(default=None, description="Type of actor entity")
    actor_id: Optional[UUID] = Field(default=None, description="ID of actor entity")
    
    # Context (additional involved entities)
    context: Dict[str, UUID] = Field(default_factory=dict, description="Additional entity references")
    
    # Temporal
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Event creation timestamp"
    )
    
    # Lineage (for event evolution and parent-child relationships)
    lineage_id: UUID = Field(
        default_factory=uuid4,
        description="Shared ID across event evolution (e.g., Creating→Created)"
    )
    parent_id: Optional[UUID] = Field(default=None, description="Parent event ID for sub-events")
    root_id: Optional[UUID] = Field(default=None, description="Root event ID in hierarchy")
    
    # Sub-events tracking
    children_ids: List[UUID] = Field(default_factory=list, description="Child event IDs")
    pending_children: int = Field(default=0, description="Number of pending child events")
    completed_children: int = Field(default=0, description="Number of completed child events")
    failed_children: int = Field(default=0, description="Number of failed child events")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary metadata")
    error: Optional[str] = Field(default=None, description="Error message if phase is FAILED")
    
    # Performance tracking
    duration_ms: Optional[float] = Field(default=None, description="Duration in milliseconds")
    
    @model_validator(mode='after')
    def validate_references(self) -> 'Event':
        """Validate that subject and actor references are complete."""
        if (self.subject_type is None) != (self.subject_id is None):
            raise ValueError("subject_type and subject_id must both be set or both be None")
        if (self.actor_type is None) != (self.actor_id is None):
            raise ValueError("actor_type and actor_id must both be set or both be None")
        return self
    
    def evolve(self, **kwargs) -> 'Event':
        """Create a new event with updated fields, preserving lineage."""
        data = self.model_dump()
        data.update(kwargs)
        # Preserve lineage_id unless explicitly overridden
        if 'lineage_id' not in kwargs:
            data['lineage_id'] = self.lineage_id
        # Generate new ID unless explicitly overridden
        if 'id' not in kwargs:
            data['id'] = uuid4()
        return self.__class__(**data)
    
    def to_completed(self, **kwargs) -> 'Event':
        """Convenience method to create completion event."""
        return self.evolve(phase=EventPhase.COMPLETED, **kwargs)
    
    def to_failed(self, error: str, **kwargs) -> 'Event':
        """Convenience method to create failure event."""
        return self.evolve(phase=EventPhase.FAILED, error=error, **kwargs)


# ============================================================================
# COMMON EVENT TYPES
# ============================================================================

# Creation Events
class CreatingEvent(Event[T], Generic[T]):
    """Emitted when object creation begins."""
    type: str = "creating"
    phase: EventPhase = EventPhase.STARTED


class CreatedEvent(Event[T], Generic[T]):
    """Emitted when object creation completes."""
    type: str = "created"
    phase: EventPhase = EventPhase.COMPLETED
    created_id: Optional[UUID] = Field(default=None, description="ID of created object")


# Modification Events
class ModifyingEvent(Event[T], Generic[T]):
    """Emitted when object modification begins."""
    type: str = "modifying"
    phase: EventPhase = EventPhase.STARTED
    fields: List[str] = Field(default_factory=list, description="Fields being modified")


class ModifiedEvent(Event[T], Generic[T]):
    """Emitted when object modification completes."""
    type: str = "modified"
    phase: EventPhase = EventPhase.COMPLETED
    fields: List[str] = Field(default_factory=list, description="Fields that were modified")
    old_values: Dict[str, Any] = Field(default_factory=dict, description="Previous values")
    new_values: Dict[str, Any] = Field(default_factory=dict, description="New values")


# Deletion Events
class DeletingEvent(Event[T], Generic[T]):
    """Emitted when object deletion begins."""
    type: str = "deleting"
    phase: EventPhase = EventPhase.STARTED


class DeletedEvent(Event[T], Generic[T]):
    """Emitted when object deletion completes."""
    type: str = "deleted"
    phase: EventPhase = EventPhase.COMPLETED


# Processing Events
class ProcessingEvent(Event[T], Generic[T]):
    """Emitted when processing begins."""
    type: str = "processing"
    phase: EventPhase = EventPhase.STARTED
    process_name: str = Field(description="Name of process being executed")
    input_ids: List[UUID] = Field(default_factory=list, description="Input entity IDs")


class ProcessedEvent(Event[T], Generic[T]):
    """Emitted when processing completes."""
    type: str = "processed"
    phase: EventPhase = EventPhase.COMPLETED
    process_name: str = Field(description="Name of process that was executed")
    output_ids: List[UUID] = Field(default_factory=list, description="Output entity IDs")
    result_summary: Optional[Dict[str, Any]] = Field(default=None, description="Process results")


# Validation Events
class ValidatingEvent(Event[T], Generic[T]):
    """Emitted when validation begins."""
    type: str = "validating"
    phase: EventPhase = EventPhase.STARTED
    validation_type: str = Field(default="schema", description="Type of validation")


class ValidatedEvent(Event[T], Generic[T]):
    """Emitted when validation completes."""
    type: str = "validated"
    phase: EventPhase = EventPhase.COMPLETED
    validation_type: str = Field(default="schema", description="Type of validation")
    is_valid: bool = Field(description="Whether validation passed")
    validation_errors: List[str] = Field(default_factory=list, description="Validation error messages")


# State Transition Events
class StateTransitionEvent(Event[T], Generic[T]):
    """Emitted when an object transitions between states."""
    type: str = "state_transition"
    from_state: str = Field(description="Previous state")
    to_state: str = Field(description="New state")
    transition_reason: Optional[str] = Field(default=None, description="Why transition occurred")


# Relationship Events
class RelationshipCreatedEvent(Event[T], Generic[T]):
    """Emitted when a relationship is established between entities."""
    type: str = "relationship_created"
    phase: EventPhase = EventPhase.COMPLETED
    relationship_type: str = Field(description="Type of relationship")
    source_type: Type[BaseModel] = Field(description="Type of source entity")
    source_id: UUID = Field(description="ID of source entity")
    target_type: Type[BaseModel] = Field(description="Type of target entity")
    target_id: UUID = Field(description="ID of target entity")


class RelationshipRemovedEvent(Event[T], Generic[T]):
    """Emitted when a relationship is removed between entities."""
    type: str = "relationship_removed"
    phase: EventPhase = EventPhase.COMPLETED
    relationship_type: str = Field(description="Type of relationship")
    source_type: Type[BaseModel] = Field(description="Type of source entity")
    source_id: UUID = Field(description="ID of source entity")
    target_type: Type[BaseModel] = Field(description="Type of target entity")
    target_id: UUID = Field(description="ID of target entity")


# System Events (no subject type needed)
class SystemEvent(Event[BaseModel]):
    """Base class for system events that don't have a specific subject."""
    def __init__(self, **data):
        # System events don't have a subject, but validation requires both or neither
        if 'subject_type' not in data:
            data['subject_type'] = None
        if 'subject_id' not in data:
            data['subject_id'] = None
        super().__init__(**data)


class SystemStartupEvent(SystemEvent):
    """Emitted when system starts up."""
    type: str = "system.startup"
    phase: EventPhase = EventPhase.COMPLETED
    version: str = Field(description="System version")
    configuration: Dict[str, Any] = Field(default_factory=dict, description="System configuration")


class SystemShutdownEvent(SystemEvent):
    """Emitted when system shuts down."""
    type: str = "system.shutdown"
    phase: EventPhase = EventPhase.STARTED
    reason: str = Field(default="normal", description="Shutdown reason")


# ============================================================================
# SUBSCRIPTION SYSTEM
# ============================================================================

@dataclass
class Subscription:
    """Represents a single event subscription."""
    handler: Callable
    event_types: Set[Type[Event]] = field(default_factory=set)
    pattern: Optional[Pattern] = None
    predicate: Optional[Callable[[Event], bool]] = None
    priority: int = EventPriority.NORMAL
    is_async: bool = field(init=False)
    is_weak: bool = False
    handler_ref: Optional[weakref.ref] = field(init=False, default=None)
    
    def __post_init__(self):
        self.is_async = inspect.iscoroutinefunction(self.handler)
        if self.is_weak:
            self.handler_ref = weakref.ref(self.handler)
    
    def get_handler(self) -> Optional[Callable]:
        """Get handler, handling weak references."""
        if self.is_weak and self.handler_ref:
            return self.handler_ref()
        return self.handler
    
    def matches(self, event: Event) -> bool:
        """Check if this subscription matches the given event."""
        # Type matching
        if self.event_types:
            event_type = type(event)
            # Check full inheritance chain
            if not any(isinstance(event, et) for et in self.event_types):
                return False
        
        # Pattern matching
        if self.pattern and not self.pattern.match(event.type):
            return False
        
        # Predicate matching
        if self.predicate and not self.predicate(event):
            return False
        
        return True


# ============================================================================
# EVENT BUS IMPLEMENTATION
# ============================================================================

class EventBus:
    """
    Central event routing and distribution system.
    
    Provides efficient event routing with three-tier subscription system:
    1. Type-based (fastest) - O(1) lookup
    2. Pattern-based (indexed) - O(n) where n is number of patterns
    3. Predicate-based (slowest) - O(n) with predicate evaluation
    """
    
    def __init__(self, history_size: int = 10000):
        # Subscription storage
        self._type_subscriptions: Dict[Type[Event], List[Subscription]] = defaultdict(list)
        self._pattern_subscriptions: List[Subscription] = []
        self._predicate_subscriptions: List[Subscription] = []
        
        # Event history (ring buffer)
        self._history: deque[Event] = deque(maxlen=history_size)
        
        # Parent-child tracking
        self._pending_parents: Dict[UUID, Event] = {}
        self._child_futures: Dict[UUID, List[asyncio.Future]] = defaultdict(list)
        
        # Performance tracking
        self._event_counts: Dict[str, int] = defaultdict(int)
        self._handler_timings: Dict[str, List[float]] = defaultdict(list)
        self._max_handler_timings: int = 1000  # Limit handler timing history
        
        # Bus state
        self._is_processing = False
        self._event_queue: asyncio.Queue[Event] = asyncio.Queue()
        self._processor_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start the event bus processor."""
        if self._processor_task is None:
            self._processor_task = asyncio.create_task(self._process_events())
    
    async def stop(self) -> None:
        """Stop the event bus processor."""
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
            self._processor_task = None
    
    async def _process_events(self) -> None:
        """Process events from the queue."""
        while True:
            try:
                event = await self._event_queue.get()
                await self._emit_internal(event)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing event: {e}", exc_info=True)
    
    def subscribe(
        self,
        handler: Callable,
        event_types: Optional[Union[Type[Event], List[Type[Event]]]] = None,
        pattern: Optional[str] = None,
        predicate: Optional[Callable[[Event], bool]] = None,
        priority: int = EventPriority.NORMAL,
        weak: bool = False
    ) -> Subscription:
        """
        Subscribe to events with various filtering options.
        
        Args:
            handler: Callable to handle matching events
            event_types: Type(s) of events to match
            pattern: Regex pattern to match event.type
            predicate: Custom predicate function
            priority: Handler priority (higher executes first)
            weak: Use weak reference to handler
            
        Returns:
            Subscription object
        """
        # Normalize event types to a set
        event_types_set: Set[Type[Event]] = set()
        if event_types is not None:
            if isinstance(event_types, list):
                event_types_set = set(event_types)
            else:
                # Single type
                event_types_set = {event_types}
        
        # Compile pattern if provided
        compiled_pattern = re.compile(pattern) if pattern else None
        
        # Create subscription
        sub = Subscription(
            handler=handler,
            event_types=event_types_set,
            pattern=compiled_pattern,
            predicate=predicate,
            priority=priority,
            is_weak=weak
        )
        
        # Add to appropriate index
        if event_types_set:
            for event_type in event_types_set:
                self._type_subscriptions[event_type].append(sub)
                # Sort by priority
                self._type_subscriptions[event_type].sort(
                    key=lambda s: s.priority, reverse=True
                )
        elif pattern:
            self._pattern_subscriptions.append(sub)
            self._pattern_subscriptions.sort(key=lambda s: s.priority, reverse=True)
        elif predicate:
            self._predicate_subscriptions.append(sub)
            self._predicate_subscriptions.sort(key=lambda s: s.priority, reverse=True)
        else:
            raise ValueError("Must specify event_types, pattern, or predicate")
        
        return sub
    
    def unsubscribe(self, subscription: Subscription) -> None:
        """Remove a subscription."""
        # Remove from type subscriptions
        for event_type in subscription.event_types:
            if event_type in self._type_subscriptions:
                try:
                    self._type_subscriptions[event_type].remove(subscription)
                    # Clean up empty lists
                    if not self._type_subscriptions[event_type]:
                        del self._type_subscriptions[event_type]
                except ValueError:
                    pass  # Subscription not in list
        
        # Remove from pattern subscriptions
        try:
            self._pattern_subscriptions.remove(subscription)
        except ValueError:
            pass  # Subscription not in list
        
        # Remove from predicate subscriptions
        try:
            self._predicate_subscriptions.remove(subscription)
        except ValueError:
            pass  # Subscription not in list
    
    async def emit(self, event: Event) -> Event:
        """
        Emit an event to all matching subscribers.
        
        Args:
            event: Event to emit
            
        Returns:
            The emitted event
        """
        # Add to queue for processing
        await self._event_queue.put(event)
        return event
    
    async def _emit_internal(self, event: Event) -> None:
        """Internal event emission logic."""
        # Record in history
        self._history.append(event)
        self._event_counts[event.type] += 1
        
        # Track parent-child relationships
        if event.parent_id and event.parent_id in self._pending_parents:
            parent = self._pending_parents[event.parent_id]
            if event.id not in parent.children_ids:
                parent.children_ids.append(event.id)
            
            # Update child completion tracking based on phase
            if event.phase == EventPhase.COMPLETED:
                parent.completed_children = getattr(parent, 'completed_children', 0) + 1
            elif event.phase == EventPhase.FAILED:
                parent.failed_children = getattr(parent, 'failed_children', 0) + 1
            
            # Check if parent should complete
            total_children_done = getattr(parent, 'completed_children', 0) + getattr(parent, 'failed_children', 0)
            if total_children_done >= parent.pending_children:
                # Notify waiters
                for future in self._child_futures.get(parent.id, []):
                    if not future.done():
                        future.set_result(None)
        
        # Find matching handlers
        handlers = self._find_matching_handlers(event)
        
        # Execute handlers
        await self._execute_handlers(event, handlers)
    
    def _find_matching_handlers(self, event: Event) -> List[Subscription]:
        """Find all subscriptions matching this event."""
        handlers = []
        seen = set()  # Avoid duplicates
        
        # Type-based matching (O(1) per type in MRO)
        event_type = type(event)
        for base_type in event_type.__mro__:
            if base_type in self._type_subscriptions:
                for sub in self._type_subscriptions[base_type][:]:  # Copy to avoid modification during iteration
                    # Check if weak reference is still alive
                    if sub.is_weak and sub.get_handler() is None:
                        # Remove dead weak reference
                        self._type_subscriptions[base_type].remove(sub)
                        continue
                    if id(sub) not in seen and sub.matches(event):
                        handlers.append(sub)
                        seen.add(id(sub))
        
        # Pattern-based matching
        for sub in self._pattern_subscriptions:
            # Check if weak reference is still alive
            if sub.is_weak and sub.get_handler() is None:
                continue
            if id(sub) not in seen and sub.matches(event):
                handlers.append(sub)
                seen.add(id(sub))
        
        # Predicate-based matching
        for sub in self._predicate_subscriptions:
            # Check if weak reference is still alive
            if sub.is_weak and sub.get_handler() is None:
                continue
            if id(sub) not in seen and sub.matches(event):
                handlers.append(sub)
                seen.add(id(sub))
        
        # Sort by priority (already sorted in each list, but need global sort)
        handlers.sort(key=lambda s: s.priority, reverse=True)
        
        return handlers
    
    async def _execute_handlers(self, event: Event, handlers: List[Subscription]) -> None:
        """Execute handlers for an event."""
        for sub in handlers:
            handler = sub.get_handler()
            if handler is None:  # Weak reference died
                continue
            
            try:
                start_time = time.time()
                
                if sub.is_async:
                    await handler(event)
                else:
                    # Run sync handler in thread pool
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, handler, event)
                
                # Track timing (with memory limit)
                elapsed = time.time() - start_time
                handler_name = f"{handler.__module__}.{handler.__name__}"
                timing_list = self._handler_timings[handler_name]
                timing_list.append(elapsed)
                
                # Limit memory usage by keeping only recent timings
                if len(timing_list) > self._max_handler_timings:
                    timing_list[:] = timing_list[-self._max_handler_timings//2:]  # Keep last half
                
            except Exception as e:
                logger.error(
                    f"Error in event handler {handler}: {e}",
                    exc_info=True,
                    extra={"event": event}
                )
    
    async def emit_with_children(
        self,
        parent_event: Event,
        child_generators: List[Callable[[], Awaitable[Event]]]
    ) -> Event:
        """
        Emit parent event and await all children before completion.
        
        Args:
            parent_event: Parent event to emit
            child_generators: Functions that generate child events
            
        Returns:
            The completed parent event
        """
        # Set parent to STARTED phase with proper initialization
        parent_event = parent_event.evolve(
            phase=EventPhase.STARTED,
            pending_children=len(child_generators),
            completed_children=0,
            failed_children=0
        )
        
        # Track as pending parent
        self._pending_parents[parent_event.id] = parent_event
        
        # Emit parent start
        await self.emit(parent_event)
        
        # Execute all child generators
        child_tasks = []
        for generator in child_generators:
            task = asyncio.create_task(self._emit_child(parent_event.id, generator))
            child_tasks.append(task)
        
        # Wait for all children
        child_results = await asyncio.gather(*child_tasks, return_exceptions=True)
        
        # Count successful vs failed children
        successful_children = 0
        failed_children = []
        
        for result in child_results:
            if isinstance(result, Exception):
                failed_children.append(result)
            else:
                successful_children += 1
        
        # Update parent tracking
        if parent_event.id in self._pending_parents:
            self._pending_parents[parent_event.id].completed_children = successful_children
            self._pending_parents[parent_event.id].failed_children = len(failed_children)
        
        # Determine final parent phase
        if failed_children:
            final_phase = EventPhase.FAILED
            error_msg = f"Failed with {len(failed_children)} child errors"
        else:
            final_phase = EventPhase.COMPLETED
            error_msg = None
        
        # Get final counts from tracked parent
        tracked_parent = self._pending_parents.get(parent_event.id, parent_event)
        final_completed = getattr(tracked_parent, 'completed_children', successful_children)
        final_failed = getattr(tracked_parent, 'failed_children', len(failed_children))
        
        # Emit parent completion
        completion_event = parent_event.evolve(
            phase=final_phase,
            error=error_msg,
            completed_children=final_completed,
            failed_children=final_failed
        )
        await self.emit(completion_event)
        
        # Cleanup
        if parent_event.id in self._pending_parents:
            del self._pending_parents[parent_event.id]
        if parent_event.id in self._child_futures:
            del self._child_futures[parent_event.id]
        
        return completion_event
    
    async def _emit_child(
        self,
        parent_id: UUID,
        generator: Callable[[], Awaitable[Event]]
    ) -> Optional[Event]:
        """Emit a child event with parent tracking."""
        try:
            child_event = await generator()
            
            # Update child event with parent info
            if not hasattr(child_event, 'parent_id') or child_event.parent_id is None:
                child_event = child_event.evolve(parent_id=parent_id)
            
            # Set root_id if not set
            if child_event.root_id is None:
                if parent_id in self._pending_parents:
                    parent = self._pending_parents[parent_id]
                    child_event = child_event.evolve(
                        root_id=parent.root_id or parent.id
                    )
                else:
                    child_event = child_event.evolve(root_id=parent_id)
            
            await self.emit(child_event)
            return child_event
            
        except Exception as e:
            # Emit failure event
            failure_event = Event(
                type="child_failure",
                phase=EventPhase.FAILED,
                parent_id=parent_id,
                error=str(e)
            )
            await self.emit(failure_event)
            raise
    
    async def wait_for_children(self, parent_id: UUID, timeout: Optional[float] = None) -> None:
        """Wait for all children of a parent event to complete."""
        if parent_id not in self._pending_parents:
            return  # Parent already completed
        
        # Create future for this waiter
        future = asyncio.Future()
        self._child_futures[parent_id].append(future)
        
        try:
            await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            # Emit timeout event
            if parent_id in self._pending_parents:
                parent = self._pending_parents[parent_id]
                timeout_event = parent.evolve(
                    phase=EventPhase.TIMEOUT,
                    error=f"Timeout waiting for children after {timeout}s"
                )
                await self.emit(timeout_event)
            raise
    
    def get_history(
        self,
        limit: Optional[int] = None,
        event_type: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> List[Event]:
        """Get event history with optional filtering."""
        events = list(self._history)
        
        # Filter by type
        if event_type:
            events = [e for e in events if e.type == event_type]
        
        # Filter by time
        if since:
            events = [e for e in events if e.timestamp >= since]
        
        # Apply limit
        if limit:
            events = events[-limit:]
        
        return events
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        handler_stats = {}
        for handler_name, timings in self._handler_timings.items():
            if timings:
                handler_stats[handler_name] = {
                    'count': len(timings),
                    'avg_ms': sum(timings) / len(timings) * 1000,
                    'max_ms': max(timings) * 1000,
                    'min_ms': min(timings) * 1000
                }
        
        return {
            'total_events': sum(self._event_counts.values()),
            'event_counts': dict(self._event_counts),
            'pending_parents': len(self._pending_parents),
            'history_size': len(self._history),
            'queue_size': self._event_queue.qsize(),
            'processing': self._processor_task is not None and not self._processor_task.done(),
            'subscriptions': {
                'type_based': sum(len(subs) for subs in self._type_subscriptions.values()),
                'pattern_based': len(self._pattern_subscriptions),
                'predicate_based': len(self._predicate_subscriptions)
            },
            'handler_stats': handler_stats
        }


# ============================================================================
# DECORATOR-BASED SUBSCRIPTIONS
# ============================================================================

def on(
    *event_types: Type[Event],
    pattern: Optional[str] = None,
    predicate: Optional[Callable[[Event], bool]] = None,
    priority: int = EventPriority.NORMAL,
    weak: bool = False
) -> Callable:
    """
    Decorator for subscribing to events.
    
    Examples:
        @on(CreatedEvent)
        async def handle_creation(event: CreatedEvent):
            print(f"Object created: {event.subject_id}")
        
        @on(pattern="entity.*")
        def handle_entity_events(event: Event):
            print(f"Entity event: {event.type}")
        
        @on(predicate=lambda e: e.metadata.get('important'))
        async def handle_important(event: Event):
            print(f"Important event: {event}")
    """
    def decorator(handler: Callable) -> Callable:
        # Get or create event bus
        bus = get_event_bus()
        
        # Subscribe
        bus.subscribe(
            handler=handler,
            event_types=list(event_types) if event_types else None,
            pattern=pattern,
            predicate=predicate,
            priority=priority,
            weak=weak
        )
        
        return handler
    
    return decorator


# ============================================================================
# METHOD INSTRUMENTATION DECORATORS
# ============================================================================

def emit_events(
    creating_factory: Optional[Callable[..., Event]] = None,
    created_factory: Optional[Callable[..., Event]] = None,
    failed_factory: Optional[Callable[..., Event]] = None,
    include_timing: bool = True,
    include_args: bool = False
) -> Callable:
    """
    Decorator that emits events around method execution.
    
    Args:
        creating_factory: Function to create the 'started' event
        created_factory: Function to create the 'completed' event
        failed_factory: Function to create the 'failed' event
        include_timing: Whether to include execution time
        include_args: Whether to include method arguments in metadata
        
    Example:
        @emit_events(
            creating_factory=lambda self: ProcessingEvent(
                subject_type=type(self),
                subject_id=self.id,
                process_name="analyze"
            ),
            created_factory=lambda result, self: ProcessedEvent(
                subject_type=type(self),
                subject_id=self.id,
                process_name="analyze",
                output_ids=[result.id]
            )
        )
        async def analyze(self, data):
            # ... method implementation ...
            return result
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            bus = get_event_bus()
            start_time = time.time()
            
            # Create starting event
            if creating_factory:
                start_event = creating_factory(*args, **kwargs)
                if include_args:
                    start_event.metadata['args'] = str(args)
                    start_event.metadata['kwargs'] = str(kwargs)
                await bus.emit(start_event)
                lineage_id = start_event.lineage_id
            else:
                lineage_id = uuid4()
            
            try:
                # Execute method
                result = await func(*args, **kwargs)
                
                # Create completion event
                if created_factory:
                    end_event = created_factory(result, *args, **kwargs)
                    end_event.lineage_id = lineage_id
                    if include_timing:
                        end_event.duration_ms = (time.time() - start_time) * 1000
                    await bus.emit(end_event)
                
                return result
                
            except Exception as e:
                # Create failure event
                if failed_factory:
                    error_event = failed_factory(e, *args, **kwargs)
                    error_event.lineage_id = lineage_id
                    if include_timing:
                        error_event.duration_ms = (time.time() - start_time) * 1000
                    await bus.emit(error_event)
                else:
                    # Default failure event
                    error_event = Event(
                        type=f"{func.__name__}.failed",
                        phase=EventPhase.FAILED,
                        lineage_id=lineage_id,
                        error=str(e),
                        metadata={'function': func.__name__}
                    )
                    if include_timing:
                        error_event.duration_ms = (time.time() - start_time) * 1000
                    await bus.emit(error_event)
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync methods, check if we're in an event loop
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context, create a task
                return asyncio.create_task(async_wrapper(*args, **kwargs))
            except RuntimeError:
                # No event loop, create one
                return asyncio.run(async_wrapper(*args, **kwargs))
        
        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def track_state_transition(
    state_field: str = 'state',
    emit_event: bool = True
) -> Callable:
    """
    Decorator that tracks state transitions and emits events.
    
    Args:
        state_field: Name of the state field on the object
        emit_event: Whether to emit state transition events
        
    Example:
        @track_state_transition(state_field='status')
        def approve(self):
            self.status = 'approved'
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(self, *args, **kwargs):
            # Get current state
            old_state = getattr(self, state_field, None)
            
            # Execute method
            result = await func(self, *args, **kwargs) if asyncio.iscoroutinefunction(func) else func(self, *args, **kwargs)
            
            # Get new state
            new_state = getattr(self, state_field, None)
            
            # Emit event if state changed
            if emit_event and old_state != new_state:
                bus = get_event_bus()
                event = StateTransitionEvent(
                    subject_type=type(self),
                    subject_id=getattr(self, 'id', None) or getattr(self, 'ecs_id', None),
                    from_state=str(old_state),
                    to_state=str(new_state),
                    transition_reason=func.__name__
                )
                await bus.emit(event)
            
            return result
        
        @functools.wraps(func)
        def sync_wrapper(self, *args, **kwargs):
            try:
                loop = asyncio.get_running_loop()
                # Already in async context, create task
                return asyncio.create_task(async_wrapper(self, *args, **kwargs))
            except RuntimeError:
                # No event loop running
                return asyncio.run(async_wrapper(self, *args, **kwargs))
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

async def emit(event: Event) -> Event:
    """Convenience function to emit an event to the global bus."""
    return await get_event_bus().emit(event)


async def emit_and_wait(
    event: Event,
    timeout: Optional[float] = None
) -> List[Event]:
    """Emit an event and wait for all resulting events to complete."""
    bus = get_event_bus()
    
    # Track child events
    child_events = []
    
    @on(predicate=lambda e: e.parent_id == event.id or e.lineage_id == event.lineage_id)
    async def collector(e: Event):
        child_events.append(e)
    
    # Emit event
    await bus.emit(event)
    
    # Wait for completion
    if timeout:
        await asyncio.sleep(timeout)
    else:
        # Wait for a short time to collect immediate children
        await asyncio.sleep(0.1)
    
    # Unsubscribe collector
    # (In production, would need proper subscription management)
    
    return child_events


@asynccontextmanager
async def event_context(
    start_event: Event,
    end_event_factory: Optional[Callable[[Any], Event]] = None
):
    """
    Context manager that emits events at start and end.
    
    Example:
        async with event_context(ProcessingEvent(...)) as ctx:
            # Do work
            result = await process()
            ctx.result = result
    """
    bus = get_event_bus()
    
    # Create context object to store data
    class Context:
        result: Any = None
        error: Optional[Exception] = None
    
    ctx = Context()
    
    # Emit start event
    await bus.emit(start_event)
    
    try:
        yield ctx
        
        # Emit success event
        if end_event_factory and ctx.result is not None:
            end_event = end_event_factory(ctx.result)
            end_event.lineage_id = start_event.lineage_id
            await bus.emit(end_event)
        else:
            # Default completion
            await bus.emit(start_event.to_completed())
            
    except Exception as e:
        ctx.error = e
        # Emit failure event
        await bus.emit(start_event.to_failed(str(e)))
        raise


def create_event_chain(events: List[Event]) -> List[Event]:
    """
    Create a chain of events with parent-child relationships.
    
    Args:
        events: List of events to chain
        
    Returns:
        The same events with parent_id and root_id set
    """
    if not events:
        return events
    
    # Set root
    root = events[0]
    root.root_id = root.id
    
    # Chain events
    for i in range(1, len(events)):
        events[i].parent_id = events[i-1].id
        events[i].root_id = root.id
    
    return events


# ============================================================================
# EVENT STREAMING FOR VISUALIZATION
# ============================================================================

class EventSerializer:
    """Serialize events for transmission and visualization."""
    
    @staticmethod
    def to_json(event: Event) -> str:
        """Convert event to JSON string."""
        # First convert to dict with proper handling
        data = EventSerializer.to_dict(event)
        return json.dumps(data)
    
    @staticmethod
    def to_dict(event: Event) -> Dict[str, Any]:
        """Convert event to dictionary."""
        # Create a custom dict that handles Type serialization
        data = {}
        
        # Manually handle each field to control serialization
        for field_name, field_info in event.model_fields.items():
            value = getattr(event, field_name)
            
            if value is None:
                continue
                
            # Special handling for Type fields
            if field_name in ['subject_type', 'actor_type']:
                if value is not None:
                    data[field_name] = value.__name__ if hasattr(value, '__name__') else str(value)
            # Special handling for relationship event types
            elif field_name in ['source_type', 'target_type'] and hasattr(event, field_name):
                if value is not None:
                    data[field_name] = value.__name__ if hasattr(value, '__name__') else str(value)
            # UUID fields
            elif isinstance(value, UUID):
                data[field_name] = str(value)
            # UUID lists
            elif isinstance(value, list) and value and isinstance(value[0], UUID):
                data[field_name] = [str(v) for v in value]
            # UUID dicts
            elif isinstance(value, dict) and any(isinstance(v, UUID) for v in value.values()):
                data[field_name] = {k: str(v) if isinstance(v, UUID) else v for k, v in value.items()}
            # Datetime
            elif isinstance(value, datetime):
                data[field_name] = value.isoformat()
            # Enum
            elif isinstance(value, Enum):
                data[field_name] = value.value
            else:
                data[field_name] = value
        
        return data
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> Event:
        """Create event from dictionary."""
        # Convert string UUIDs back
        for key in ['id', 'subject_id', 'actor_id', 'parent_id', 'root_id', 'lineage_id']:
            if key in data and data[key]:
                data[key] = UUID(data[key])
        
        # Convert context UUIDs
        if 'context' in data:
            data['context'] = {k: UUID(v) for k, v in data['context'].items()}
        
        # Convert children IDs
        if 'children_ids' in data:
            data['children_ids'] = [UUID(cid) for cid in data['children_ids']]
        
        # Determine event class from type
        event_type = data.get('type', '')
        
        # Map common types to classes
        type_map = {
            'creating': CreatingEvent,
            'created': CreatedEvent,
            'modifying': ModifyingEvent,
            'modified': ModifiedEvent,
            'processing': ProcessingEvent,
            'processed': ProcessedEvent,
            'validating': ValidatingEvent,
            'validated': ValidatedEvent,
            'deleting': DeletingEvent,
            'deleted': DeletedEvent,
        }
        
        event_class = type_map.get(event_type, Event)
        return event_class(**data)


# ============================================================================
# PERFORMANCE MONITORING
# ============================================================================

class EventBusMonitor:
    """Monitor event bus performance and health."""
    
    def __init__(self, bus: EventBus):
        self.bus = bus
        self._start_time = time.time()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        stats = self.bus.get_statistics()
        uptime = time.time() - self._start_time
        
        # Calculate rates
        total_events = stats['total_events']
        event_rate = total_events / uptime if uptime > 0 else 0
        
        # Get queue size
        queue_size = self.bus._event_queue.qsize()
        
        return {
            'uptime_seconds': uptime,
            'total_events': total_events,
            'events_per_second': event_rate,
            'queue_size': queue_size,
            'pending_parents': stats['pending_parents'],
            'subscriptions': stats['subscriptions'],
            'event_types': stats['event_counts'],
            'handler_performance': stats['handler_stats']
        }
    
    def get_health(self) -> Dict[str, Any]:
        """Get health status."""
        metrics = self.get_metrics()
        
        # Define health thresholds
        is_healthy = (
            metrics['queue_size'] < 1000 and
            metrics['pending_parents'] < 100
        )
        
        return {
            'healthy': is_healthy,
            'checks': {
                'queue_size': {
                    'value': metrics['queue_size'],
                    'threshold': 1000,
                    'healthy': metrics['queue_size'] < 1000
                },
                'pending_parents': {
                    'value': metrics['pending_parents'],
                    'threshold': 100,
                    'healthy': metrics['pending_parents'] < 100
                }
            }
        }


# ============================================================================
# MODULE INITIALIZATION
# ============================================================================

# Create and start global event bus
_event_bus = EventBus()

# Auto-start event bus if in an async context
try:
    loop = asyncio.get_running_loop()
    if _event_bus and not _event_bus._processor_task:
        loop.create_task(_event_bus.start())
except RuntimeError:
    # No event loop running yet - will be started when get_event_bus() is called
    pass

# Export main components
__all__ = [
    # Core classes
    'Event', 'EventPhase', 'EventPriority', 'EventBus',
    
    # Event types
    'CreatingEvent', 'CreatedEvent',
    'ModifyingEvent', 'ModifiedEvent', 
    'DeletingEvent', 'DeletedEvent',
    'ProcessingEvent', 'ProcessedEvent',
    'ValidatingEvent', 'ValidatedEvent',
    'StateTransitionEvent',
    'RelationshipCreatedEvent', 'RelationshipRemovedEvent',
    'SystemEvent', 'SystemStartupEvent', 'SystemShutdownEvent',
    
    # Decorators
    'on', 'emit_events', 'track_state_transition',
    
    # Functions
    'emit', 'emit_and_wait', 'event_context', 'create_event_chain',
    'get_event_bus',
    
    # Utilities
    'EventSerializer', 'EventBusMonitor',
    'Subscription'
]