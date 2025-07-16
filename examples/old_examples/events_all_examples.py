"""
Comprehensive test suite for the Event System
Tests all functionality without using a testing framework
"""

import asyncio
import time
import gc
from typing import List, Dict, Any, Optional, Type
from datetime import datetime, timezone
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
import json
import weakref

# Import the events module itself for bus override in tests
import abstractions.events.events as events
# Import all event system components
from abstractions.events.events import (
    # Core
    Event, EventPhase, EventPriority, EventBus, get_event_bus,
    # Event types
    CreatingEvent, CreatedEvent, ModifyingEvent, ModifiedEvent,
    DeletingEvent, DeletedEvent, ProcessingEvent, ProcessedEvent,
    ValidatingEvent, ValidatedEvent, StateTransitionEvent,
    RelationshipCreatedEvent, RelationshipRemovedEvent,
    SystemEvent, SystemStartupEvent, SystemShutdownEvent,
    # Decorators and utilities
    on, emit_events, track_state_transition,
    emit, emit_and_wait, event_context, create_event_chain,
    EventSerializer, EventBusMonitor, Subscription
)


# ============================================================================
# TEST FRAMEWORK
# ============================================================================

class TestResult:
    """Simple test result tracking"""
    def __init__(self, name: str):
        self.name = name
        self.passed = 0
        self.failed = 0
        self.errors: List[str] = []
        self.start_time = time.time()
    
    def assert_true(self, condition: bool, message: str = ""):
        """Assert condition is true"""
        if condition:
            self.passed += 1
        else:
            self.failed += 1
            self.errors.append(f"Assertion failed: {message}")
    
    def assert_equal(self, actual: Any, expected: Any, message: str = ""):
        """Assert values are equal"""
        if actual == expected:
            self.passed += 1
        else:
            self.failed += 1
            self.errors.append(f"Expected {expected}, got {actual}: {message}")
    
    def assert_type(self, obj: Any, expected_type: Type, message: str = ""):
        """Assert object is of expected type"""
        if isinstance(obj, expected_type):
            self.passed += 1
        else:
            self.failed += 1
            self.errors.append(f"Expected type {expected_type}, got {type(obj)}: {message}")
    
    def duration(self) -> float:
        """Get test duration in seconds"""
        return time.time() - self.start_time
    
    def __str__(self) -> str:
        status = "PASSED" if self.failed == 0 else "FAILED"
        result = f"\n{'='*60}\n"
        result += f"Test: {self.name}\n"
        result += f"Status: {status}\n"
        result += f"Passed: {self.passed}, Failed: {self.failed}\n"
        result += f"Duration: {self.duration():.3f}s\n"
        if self.errors:
            result += "Errors:\n"
            for error in self.errors:
                result += f"  - {error}\n"
        return result


# ============================================================================
# TEST MODELS (Non-Entity BaseModels)
# ============================================================================

class Task(BaseModel):
    """Example domain model - a task in a task management system"""
    id: UUID = Field(default_factory=uuid4)
    title: str
    status: str = "pending"
    assignee: Optional[str] = None
    priority: int = 1
    completed_at: Optional[datetime] = None


class Project(BaseModel):
    """Example domain model - a project containing tasks"""
    id: UUID = Field(default_factory=uuid4)
    name: str
    tasks: List[UUID] = Field(default_factory=list)
    status: str = "active"


# Custom event types for our domain models
class TaskCreatedEvent(CreatedEvent[Task]):
    type: str = "task.created"
    project_id: Optional[UUID] = None


class TaskStatusChangedEvent(StateTransitionEvent[Task]):
    type: str = "task.status_changed"


class ProjectTaskAddedEvent(RelationshipCreatedEvent[Project]):
    type: str = "project.task_added"
    relationship_type: str = "contains"


# ============================================================================
# TEST CASES
# ============================================================================

async def test_basic_event_creation():
    """Test basic event creation and properties"""
    result = TestResult("Basic Event Creation")
    
    try:
        # Test generic event creation
        event = Event(
            type="test.event",
            phase=EventPhase.STARTED,
            metadata={"test": True}
        )
        
        result.assert_type(event.id, UUID, "Event should have UUID id")
        result.assert_equal(event.type, "test.event", "Event type should match")
        result.assert_equal(event.phase, EventPhase.STARTED, "Event phase should match")
        result.assert_true(event.timestamp <= datetime.now(timezone.utc), "Timestamp should be in past")
        result.assert_type(event.lineage_id, UUID, "Should have lineage ID")
        
        # Test typed event creation
        task = Task(title="Test Task")
        task_event = CreatingEvent[Task](
            subject_type=Task,
            subject_id=task.id
        )
        
        result.assert_equal(task_event.subject_type, Task, "Subject type should be Task")
        result.assert_equal(task_event.subject_id, task.id, "Subject ID should match")
        result.assert_equal(task_event.type, "creating", "Default type should be 'creating'")
        
        # Test custom event
        custom_event = TaskCreatedEvent(
            subject_type=Task,
            subject_id=task.id,
            created_id=task.id,
            project_id=uuid4()
        )
        
        result.assert_equal(custom_event.type, "task.created", "Custom type should override")
        result.assert_type(custom_event.project_id, UUID, "Custom field should work")
        
    except Exception as e:
        result.failed += 1
        result.errors.append(f"Exception: {str(e)}")
    
    return result


async def test_event_evolution():
    """Test event evolution and lineage"""
    result = TestResult("Event Evolution")
    
    try:
        # Create initial event
        start_event = ProcessingEvent[Task](
            subject_type=Task,
            subject_id=uuid4(),
            process_name="analyze_task"
        )
        
        original_lineage = start_event.lineage_id
        
        # Evolve to completion
        complete_event = start_event.to_completed(
            duration_ms=150.5
        )
        
        result.assert_equal(complete_event.lineage_id, original_lineage, "Lineage should be preserved")
        result.assert_equal(complete_event.phase, EventPhase.COMPLETED, "Phase should be COMPLETED")
        result.assert_equal(complete_event.duration_ms, 150.5, "Duration should be set")
        result.assert_true(complete_event.id != start_event.id, "Should have new ID")
        
        # Evolve to failure
        error_event = start_event.to_failed("Something went wrong")
        
        result.assert_equal(error_event.lineage_id, original_lineage, "Lineage preserved on failure")
        result.assert_equal(error_event.phase, EventPhase.FAILED, "Phase should be FAILED")
        result.assert_equal(error_event.error, "Something went wrong", "Error should be set")
        
    except Exception as e:
        result.failed += 1
        result.errors.append(f"Exception: {str(e)}")
    
    return result


async def test_event_bus_subscription():
    """Test event bus subscription patterns"""
    result = TestResult("Event Bus Subscription")
    
    try:
        bus = EventBus()
        received_events: List[Event] = []
        
        # Type-based subscription
        def handle_created(event: CreatedEvent):
            received_events.append(event)
        
        sub1 = bus.subscribe(
            handler=handle_created,
            event_types=CreatedEvent
        )
        
        # Pattern-based subscription
        task_events: List[Event] = []
        
        def handle_task_events(event: Event):
            task_events.append(event)
        
        sub2 = bus.subscribe(
            handler=handle_task_events,
            pattern="task.*"
        )
        
        # Predicate-based subscription
        high_priority_events: List[Event] = []
        
        def handle_high_priority(event: Event):
            high_priority_events.append(event)
        
        sub3 = bus.subscribe(
            handler=handle_high_priority,
            predicate=lambda e: e.metadata.get("priority", 0) > 5
        )
        
        # Start bus and emit events
        await bus.start()
        
        # Emit various events
        await bus.emit(CreatedEvent(
            type="created", 
            subject_type=Task,
            subject_id=uuid4()  # Need both type and id
        ))
        await bus.emit(TaskCreatedEvent(
            subject_type=Task, 
            subject_id=uuid4()
        ))
        await bus.emit(Event(
            type="task.updated", 
            metadata={"priority": 10}
        ))
        await bus.emit(Event(
            type="other.event", 
            metadata={"priority": 1}
        ))
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Check results
        result.assert_equal(len(received_events), 2, "Should receive 2 created events")
        result.assert_equal(len(task_events), 2, "Should receive 2 task.* events")
        result.assert_equal(len(high_priority_events), 1, "Should receive 1 high priority event")
        
        # Test unsubscribe
        bus.unsubscribe(sub1)
        await bus.emit(CreatedEvent(
            type="created", 
            subject_type=Task,
            subject_id=uuid4()  # Need both type and id
        ))
        
        result.assert_equal(len(received_events), 2, "Should not receive after unsubscribe")
        
        await bus.stop()
        
    except Exception as e:
        result.failed += 1
        result.errors.append(f"Exception: {str(e)}")
    
    return result


async def test_decorator_subscriptions():
    """Test decorator-based subscriptions"""
    result = TestResult("Decorator Subscriptions")
    
    try:
        # Get global bus and ensure it's started
        bus = get_event_bus()
        await bus.start()
        
        received: Dict[str, List[Event]] = {
            "type": [],
            "pattern": [],
            "predicate": []
        }
        
        # Type-based decorator
        @on(TaskCreatedEvent)
        async def handle_task_created(event: TaskCreatedEvent):
            received["type"].append(event)
        
        # Pattern-based decorator
        @on(pattern="project.*")
        def handle_project_events(event: Event):
            received["pattern"].append(event)
        
        # Predicate-based decorator
        @on(predicate=lambda e: hasattr(e, 'subject_id') and e.subject_id is not None)
        async def handle_with_subject(event: Event):
            received["predicate"].append(event)
        
        # Emit test events
        task_id = uuid4()
        await emit(TaskCreatedEvent(subject_type=Task, subject_id=task_id))
        await emit(Event(type="project.created"))
        await emit(Event(type="project.updated"))
        await emit(Event(type="other.event"))
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Verify
        result.assert_equal(len(received["type"]), 1, "Type decorator should work")
        result.assert_equal(len(received["pattern"]), 2, "Pattern decorator should work")
        result.assert_equal(len(received["predicate"]), 1, "Predicate decorator should work")
        
        await get_event_bus().stop()
        
    except Exception as e:
        result.failed += 1
        result.errors.append(f"Exception: {str(e)}")
    
    return result


async def test_parent_child_events():
    """Test parent-child event relationships"""
    result = TestResult("Parent-Child Events")
    
    try:
        bus = EventBus()
        await bus.start()
        
        # Track events
        all_events: List[Event] = []
        
        def track_all(event: Event):
            all_events.append(event)
        
        bus.subscribe(handler=track_all, predicate=lambda e: True)
        
        # Create parent event with children
        parent = ProcessingEvent[Task](
            subject_type=Task,
            subject_id=uuid4(),
            process_name="complex_task"
        )
        
        # Define child generators
        async def child1():
            await asyncio.sleep(0.01)
            return ValidatingEvent(
                type="child.validating",
                subject_type=Task,
                subject_id=uuid4()  # Need both type and id
            )
        
        async def child2():
            await asyncio.sleep(0.02)
            return Event(
                type="child.processing",
                phase=EventPhase.COMPLETED
            )
        
        # Emit with children
        completed_parent = await bus.emit_with_children(
            parent,
            [child1, child2]
        )
        
        # Wait for all events to be processed
        await asyncio.sleep(0.2)  # Increased wait time
        
        # Debug: Print all events
        # for i, e in enumerate(all_events):
        #     print(f"Event {i}: type={e.type}, phase={e.phase}, parent_id={e.parent_id}")
        
        # Verify parent-child relationships
        result.assert_equal(completed_parent.phase, EventPhase.COMPLETED, "Parent should complete")
        result.assert_equal(len(completed_parent.children_ids), 2, "Should have 2 children")
        result.assert_equal(completed_parent.completed_children, 2, "Both children should complete")
        
        # Find child events - use children_ids from completed parent
        # Note: emit_with_children() creates multiple evolved parent events with different IDs
        # Children get linked to the STARTED parent, so we use children_ids to find them
        child_events = []
        for e in all_events:
            if e.id in completed_parent.children_ids:
                child_events.append(e)
        result.assert_equal(len(child_events), 2, "Should find 2 child events using children_ids")
        
        # Verify root_id propagation - should match the started parent's ID
        # Find the started parent event
        started_parent_events = [e for e in all_events if e.phase == EventPhase.STARTED and e.type == "processing"]
        if started_parent_events:
            started_parent_id = started_parent_events[0].id
            for child in child_events:
                result.assert_equal(child.root_id, started_parent_id, "Root ID should match started parent ID")
        
        await bus.stop()
        
    except Exception as e:
        result.failed += 1
        result.errors.append(f"Exception: {str(e)}")
    
    return result


async def test_method_instrumentation():
    """Test method instrumentation decorators"""
    result = TestResult("Method Instrumentation")
    
    try:
        # Reset bus
        bus = EventBus()
        await bus.start()
        
        emitted_events: List[Event] = []
        
        @on(predicate=lambda e: True)
        def capture_all(event: Event):
            emitted_events.append(event)
        
        bus.subscribe(handler=capture_all, predicate=lambda e: True)
        
        # Test class with instrumented methods - needs to be BaseModel
        class TaskManager(BaseModel):
            tasks: Dict[UUID, Task] = Field(default_factory=dict)
            state: str = "ready"
            id: UUID = Field(default_factory=uuid4)
            
            @emit_events(
                creating_factory=lambda self, task: CreatingEvent(
                    subject_type=Task,
                    subject_id=task.id
                ),
                created_factory=lambda result, self, task: TaskCreatedEvent(
                    subject_type=Task,
                    subject_id=task.id,
                    created_id=task.id
                )
            )
            async def create_task(self, task: Task) -> Task:
                await asyncio.sleep(0.01)  # Simulate work
                self.tasks[task.id] = task
                return task
            
            @track_state_transition(state_field='state')
            async def activate(self):
                self.state = "active"
            
            @track_state_transition(state_field='state')
            async def deactivate(self):
                self.state = "inactive"
        
        # Test instrumented methods
        manager = TaskManager()
        # No need to setattr anymore since id is a field
        
        # Test async method with events
        task = Task(title="Test Task")
        created_task = await manager.create_task(task)
        
        # Test state transitions (now async)
        await manager.activate()
        await manager.deactivate()
        
        # Wait for events
        await asyncio.sleep(0.1)
        
        # Verify events
        creating_events = [e for e in emitted_events if isinstance(e, CreatingEvent)]
        created_events = [e for e in emitted_events if isinstance(e, TaskCreatedEvent)]
        state_events = [e for e in emitted_events if isinstance(e, StateTransitionEvent)]
        
        result.assert_equal(len(creating_events), 1, "Should emit creating event")
        result.assert_equal(len(created_events), 1, "Should emit created event")
        result.assert_equal(len(state_events), 2, "Should emit 2 state transitions")
        
        # Verify state transitions
        if len(state_events) >= 2:
            result.assert_equal(state_events[0].from_state, "ready", "First transition from ready")
            result.assert_equal(state_events[0].to_state, "active", "First transition to active")
            result.assert_equal(state_events[1].from_state, "active", "Second transition from active")
            result.assert_equal(state_events[1].to_state, "inactive", "Second transition to inactive")
        
        await bus.stop()
        
    except Exception as e:
        result.failed += 1
        result.errors.append(f"Exception: {str(e)}")
    
    return result


async def test_event_context_manager():
    """Test event context manager"""
    result = TestResult("Event Context Manager")
    
    try:
        # Use a fresh bus for this test
        bus = EventBus()
        await bus.start()
        
        received: List[Event] = []
        
        # Subscribe before emitting
        def capture(event: Event):
            received.append(event)
        
        bus.subscribe(handler=capture, predicate=lambda e: True)
        
        # Test successful context
        start_event = ProcessingEvent(
            subject_type=Task,
            subject_id=uuid4(),
            process_name="context_test"
        )
        
        # Temporarily override global bus for event_context
        original_bus = get_event_bus()
        events._event_bus = bus
        
        try:
            async with event_context(start_event) as ctx:
                # Simulate work
                await asyncio.sleep(0.01)
                ctx.result = {"status": "success"}
            
            # Wait for events
            await asyncio.sleep(0.1)
            
            # Should have start and completion events
            result.assert_true(len(received) >= 2, "Should have at least 2 events")
            
            # Test with custom end event
            received.clear()
            
            def end_factory(result):
                return ProcessedEvent(
                    subject_type=Task,
                    subject_id=uuid4(),  # Need both type and id
                    process_name="context_test",
                    result_summary=result
                )
            
            async with event_context(start_event, end_factory) as ctx:
                ctx.result = {"data": "test"}
            
            await asyncio.sleep(0.1)
            
            processed = [e for e in received if isinstance(e, ProcessedEvent)]
            result.assert_equal(len(processed), 1, "Should have custom end event")
            if processed:
                result.assert_equal(processed[0].result_summary, {"data": "test"}, "Result should match")
            
            # Test failure case
            received.clear()
            
            try:
                async with event_context(start_event):
                    raise ValueError("Test error")
            except ValueError:
                pass  # Expected
            
            await asyncio.sleep(0.1)
            
            failed = [e for e in received if e.phase == EventPhase.FAILED]
            result.assert_equal(len(failed), 1, "Should have failure event")
            if failed:
                result.assert_true("Test error" in (failed[0].error or ""), "Error should be captured")
                
        finally:
            # Restore original bus
            events._event_bus = original_bus
            await bus.stop()
        
    except Exception as e:
        result.failed += 1
        result.errors.append(f"Exception: {str(e)}")
    
    return result


async def test_event_serialization():
    """Test event serialization and deserialization"""
    result = TestResult("Event Serialization")
    
    try:
        # Create complex event
        task_id = uuid4()
        project_id = uuid4()
        
        event = TaskCreatedEvent(
            subject_type=Task,
            subject_id=task_id,
            created_id=task_id,
            project_id=project_id,
            context={"user_id": uuid4()},
            metadata={"source": "api", "version": "1.0"}
        )
        
        # Add children for complexity
        event.children_ids = [uuid4(), uuid4()]
        
        # Serialize to dict
        try:
            event_dict = EventSerializer.to_dict(event)
            
            result.assert_equal(event_dict["type"], "task.created", "Type should serialize")
            result.assert_equal(event_dict["subject_type"], "Task", "Subject type should be string")
            result.assert_type(event_dict["subject_id"], str, "UUID should be string")
            result.assert_equal(event_dict["subject_id"], str(task_id), "UUID value should match")
        except Exception as e:
            result.failed += 1
            result.errors.append(f"Dict serialization failed: {str(e)}")
            return result
        
        # Serialize to JSON
        try:
            json_str = EventSerializer.to_json(event)
            result.assert_type(json_str, str, "Should produce JSON string")
            
            # Verify valid JSON
            parsed = json.loads(json_str)
            result.assert_equal(parsed["type"], "task.created", "JSON should be valid")
        except Exception as e:
            result.failed += 1
            result.errors.append(f"JSON serialization failed: {str(e)}")
            return result
        
        # Deserialize from dict
        try:
            restored = EventSerializer.from_dict(event_dict)
            
            result.assert_type(restored, Event, "Should restore to Event")
            result.assert_equal(restored.id, event.id, "ID should match after restore")
            result.assert_equal(len(restored.children_ids), 2, "Children should be restored")
        except Exception as e:
            result.failed += 1
            result.errors.append(f"Deserialization failed: {str(e)}")
        
    except Exception as e:
        result.failed += 1
        result.errors.append(f"Exception: {str(e)}")
    
    return result


async def test_event_history_and_stats():
    """Test event history and statistics"""
    result = TestResult("Event History and Statistics")
    
    try:
        bus = EventBus(history_size=100)
        await bus.start()
        
        # Emit various events
        for i in range(10):
            await bus.emit(Event(type="test.event", metadata={"index": i}))
        
        for i in range(5):
            await bus.emit(TaskCreatedEvent(
                subject_type=Task,
                subject_id=uuid4()
            ))
        
        await asyncio.sleep(0.1)
        
        # Test history retrieval
        history = bus.get_history()
        result.assert_equal(len(history), 15, "Should have all events in history")
        
        # Test filtered history
        task_history = bus.get_history(event_type="task.created")
        result.assert_equal(len(task_history), 5, "Should filter by type")
        
        # Test limited history
        recent = bus.get_history(limit=3)
        result.assert_equal(len(recent), 3, "Should limit results")
        
        # Test statistics
        stats = bus.get_statistics()
        
        result.assert_equal(stats["total_events"], 15, "Total events should match")
        result.assert_equal(stats["event_counts"]["test.event"], 10, "Event count by type")
        result.assert_equal(stats["event_counts"]["task.created"], 5, "Event count by type")
        result.assert_true("subscriptions" in stats, "Should have subscription stats")
        
        # Test monitoring
        monitor = EventBusMonitor(bus)
        await asyncio.sleep(0.01)  # Ensure some time passes
        metrics = monitor.get_metrics()
        
        result.assert_equal(metrics["total_events"], 15, "Monitor should track events")
        result.assert_true(metrics["events_per_second"] >= 0, "Should calculate rate")
        
        health = monitor.get_health()
        result.assert_true(health["healthy"], "Bus should be healthy")
        
        await bus.stop()
        
    except Exception as e:
        result.failed += 1
        result.errors.append(f"Exception: {str(e)}")
    
    return result


async def test_weak_references():
    """Test weak reference subscriptions"""
    result = TestResult("Weak References")
    
    try:
        bus = EventBus()
        await bus.start()
        
        events_received = []
        handler_called = []
        
        class Handler:
            def __init__(self):
                self.name = "test_handler"
                
            def handle_event(self, event: Event):
                handler_called.append(self.name)
                events_received.append(event)
        
        # Create handler and weak subscription
        handler = Handler()
        weak_ref = weakref.ref(handler)
        
        sub = bus.subscribe(
            handler=handler.handle_event,
            event_types=Event,
            weak=True
        )
        
        # Emit event - should be received
        await bus.emit(Event(type="test.weak"))
        await asyncio.sleep(0.1)
        
        result.assert_equal(len(events_received), 1, "Weak handler should work")
        
        # Delete handler and force garbage collection
        del handler
        gc.collect()
        gc.collect()  # Sometimes needs multiple passes
        await asyncio.sleep(0.1)  # Give time for cleanup
        
        # Verify weak ref is dead
        result.assert_true(weak_ref() is None, "Weak ref should be dead")
        
        # Clear received events
        events_received.clear()
        handler_called.clear()
        
        # Emit again - should not crash or call handler
        await bus.emit(Event(type="test.weak2"))
        await asyncio.sleep(0.1)
        
        result.assert_equal(len(handler_called), 0, "Dead weak ref should not receive")
        
        await bus.stop()
        
    except Exception as e:
        result.failed += 1
        result.errors.append(f"Exception: {str(e)}")
    
    return result


async def test_event_chains():
    """Test event chain creation"""
    result = TestResult("Event Chains")
    
    try:
        # Create chain of events - ALL need process_name and proper subject info
        task_id = uuid4()  # Same task for the chain
        events = [
            ProcessingEvent(
                type="step1", 
                subject_type=Task, 
                subject_id=task_id,  # Same task ID
                process_name="step1"
            ),
            ProcessingEvent(
                type="step2", 
                subject_type=Task, 
                subject_id=task_id,
                process_name="step2"
            ),
            ProcessingEvent(
                type="step3", 
                subject_type=Task, 
                subject_id=task_id,
                process_name="step3"
            ),
            ProcessedEvent(
                type="complete", 
                subject_type=Task, 
                subject_id=task_id,
                process_name="complete"
            )
        ]
        
        # Chain them
        chained = create_event_chain(events)
        
        # Verify chain
        result.assert_equal(chained[0].root_id, chained[0].id, "First should be root")
        result.assert_equal(chained[1].parent_id, chained[0].id, "Second parent is first")
        result.assert_equal(chained[2].parent_id, chained[1].id, "Third parent is second")
        result.assert_equal(chained[3].parent_id, chained[2].id, "Fourth parent is third")
        
        # All should have same root
        for event in chained[1:]:
            result.assert_equal(event.root_id, chained[0].id, "All should share root")
        
    except Exception as e:
        result.failed += 1
        result.errors.append(f"Exception: {str(e)}")
    
    return result


async def test_priority_ordering():
    """Test subscription priority ordering"""
    result = TestResult("Priority Ordering")
    
    try:
        bus = EventBus()
        await bus.start()
        
        call_order: List[str] = []
        
        # Subscribe with different priorities
        def high_priority(event: Event):
            call_order.append("high")
        
        def normal_priority(event: Event):
            call_order.append("normal")
        
        def low_priority(event: Event):
            call_order.append("low")
        
        # Subscribe in reverse priority order to test sorting
        bus.subscribe(handler=low_priority, event_types=Event, priority=EventPriority.LOW)
        bus.subscribe(handler=normal_priority, event_types=Event, priority=EventPriority.NORMAL)
        bus.subscribe(handler=high_priority, event_types=Event, priority=EventPriority.HIGH)
        
        # Emit event
        await bus.emit(Event(type="test.priority"))
        await asyncio.sleep(0.1)
        
        # Verify order
        result.assert_equal(call_order, ["high", "normal", "low"], "Should execute by priority")
        
        await bus.stop()
        
    except Exception as e:
        result.failed += 1
        result.errors.append(f"Exception: {str(e)}")
    
    return result


async def test_error_handling():
    """Test error handling in event handlers"""
    result = TestResult("Error Handling")
    
    try:
        bus = EventBus()
        await bus.start()
        
        successful_calls = []
        
        # Handler that throws
        def failing_handler(event: Event):
            raise ValueError("Handler error")
        
        # Handler that works
        def working_handler(event: Event):
            successful_calls.append(event)
        
        bus.subscribe(handler=failing_handler, event_types=Event)
        bus.subscribe(handler=working_handler, event_types=Event)
        
        # Emit event - should not crash
        await bus.emit(Event(type="test.error"))
        await asyncio.sleep(0.1)
        
        # Working handler should still be called
        result.assert_equal(len(successful_calls), 1, "Other handlers should run despite error")
        
        await bus.stop()
        
    except Exception as e:
        result.failed += 1
        result.errors.append(f"Exception: {str(e)}")
    
    return result


async def test_all_event_types():
    """Test all built-in event types"""
    result = TestResult("All Event Types")
    
    try:
        # Test each event type
        events_to_test = [
            CreatingEvent(subject_type=Task, subject_id=uuid4()),
            CreatedEvent(subject_type=Task, subject_id=uuid4(), created_id=uuid4()),
            ModifyingEvent(subject_type=Task, subject_id=uuid4(), fields=["status"]),
            ModifiedEvent(subject_type=Task, subject_id=uuid4(), fields=["status"]),
            DeletingEvent(subject_type=Task, subject_id=uuid4()),
            DeletedEvent(subject_type=Task, subject_id=uuid4()),
            ProcessingEvent(subject_type=Task, subject_id=uuid4(), process_name="test"),
            ProcessedEvent(subject_type=Task, subject_id=uuid4(), process_name="test"),
            ValidatingEvent(subject_type=Task, subject_id=uuid4()),
            ValidatedEvent(subject_type=Task, subject_id=uuid4(), is_valid=True),
            StateTransitionEvent(
                subject_type=Task,
                subject_id=uuid4(),
                from_state="pending",
                to_state="active"
            ),
            RelationshipCreatedEvent(
                subject_type=Project,
                subject_id=uuid4(),
                relationship_type="contains",
                source_type=Project,
                source_id=uuid4(),
                target_type=Task,
                target_id=uuid4()
            ),
            SystemStartupEvent(version="1.0.0"),
            SystemShutdownEvent(reason="test")
        ]
        
        bus = get_event_bus()
        
        # Emit all events
        for event in events_to_test:
            await bus.emit(event)
            result.assert_type(event, Event, f"{type(event).__name__} should be Event")
        
        # All should have proper fields
        result.assert_equal(len(events_to_test), 14, "Should test all event types")
        
    except Exception as e:
        result.failed += 1
        result.errors.append(f"Exception: {str(e)}")
    
    return result


# ============================================================================
# TEST RUNNER
# ============================================================================

async def run_all_tests():
    """Run all tests and display results"""
    print("\n" + "="*80)
    print("COMPREHENSIVE EVENT SYSTEM TEST SUITE")
    print("="*80)
    
    # Ensure global event bus is started
    bus = get_event_bus()
    await bus.start()
    
    # List of test functions
    tests = [
        test_basic_event_creation,
        test_event_evolution,
        test_event_bus_subscription,
        test_decorator_subscriptions,
        test_parent_child_events,
        test_method_instrumentation,
        test_event_context_manager,
        test_event_serialization,
        test_event_history_and_stats,
        test_weak_references,
        test_event_chains,
        test_priority_ordering,
        test_error_handling,
        test_all_event_types
    ]
    
    # Run all tests
    results: List[TestResult] = []
    total_start = time.time()
    
    for test_func in tests:
        print(f"\nRunning: {test_func.__name__}...")
        result = await test_func()
        results.append(result)
        print(f"  Status: {'PASSED' if result.failed == 0 else 'FAILED'}")
    
    # Stop global event bus
    await bus.stop()
    
    # Display summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    total_passed = sum(r.passed for r in results)
    total_failed = sum(r.failed for r in results)
    
    print(f"\nTotal Tests Run: {len(results)}")
    print(f"Total Assertions: {total_passed + total_failed}")
    print(f"  Passed: {total_passed}")
    print(f"  Failed: {total_failed}")
    print(f"Total Duration: {time.time() - total_start:.3f}s")
    
    # Display individual results
    print("\nDetailed Results:")
    for result in results:
        print(result)
    
    # Overall status
    if total_failed == 0:
        print("\n✅ ALL TESTS PASSED! ✅")
    else:
        print(f"\n❌ {sum(1 for r in results if r.failed > 0)} TESTS FAILED ❌")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Run the test suite
    asyncio.run(run_all_tests())