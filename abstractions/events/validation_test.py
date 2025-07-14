#!/usr/bin/env python3
"""
Event System Validation Test Script

Comprehensive testing of the event system using fake entities to validate
that events work correctly before integrating with the real ECS system.

Run with: python -m abstractions.events.validation_test
"""

import asyncio
import time
from typing import List, Dict, Any
from datetime import datetime, timezone

# Import event system components
from abstractions.events.events import (
    Event, EventPhase, EventPriority, get_event_bus, on,
    CreatingEvent, CreatedEvent, ModifyingEvent, ModifiedEvent,
    ProcessingEvent, ProcessedEvent, StateTransitionEvent
)

# Import bridge functions
from abstractions.events.bridge import (
    emit_creation_events, emit_modification_events, emit_processing_events,
    emit_deletion_events, emit_validation_events, emit_simple_event,
    emit_timed_operation, emit_state_transition_events
)

# Import test entities
from abstractions.events.test_entities import (
    FakeEntity, FakeDocument, FakeUser, FakeProcessingTask, FakeProject,
    EntityStatus, create_test_entity, create_test_document, create_test_user,
    create_test_task, create_document_workflow_scenario, create_collaboration_scenario
)


class EventCollector:
    """Utility class to collect and analyze events during testing"""
    
    def __init__(self):
        self.events: List[Event] = []
        self.event_counts: Dict[str, int] = {}
        self.parent_child_pairs: List[tuple] = []
        
    def reset(self):
        """Reset the collector for a new test"""
        self.events.clear()
        self.event_counts.clear()
        self.parent_child_pairs.clear()
    
    async def collect_event(self, event: Event):
        """Collect an event for analysis"""
        self.events.append(event)
        self.event_counts[event.type] = self.event_counts.get(event.type, 0) + 1
        
        # Track parent-child relationships
        if event.parent_id:
            self.parent_child_pairs.append((event.parent_id, event.id))
        
        # Print real-time event info
        phase_icon = {
            EventPhase.PENDING: "⏳",
            EventPhase.STARTED: "🔄", 
            EventPhase.PROGRESS: "⚡",
            EventPhase.COMPLETED: "✅",
            EventPhase.FAILED: "❌",
            EventPhase.CANCELLED: "🚫"
        }.get(event.phase, "📡")
        
        subject_info = ""
        if event.subject_type:
            subject_info = f" | {event.subject_type.__name__}"
            if event.subject_id:
                subject_info += f" ({str(event.subject_id)[:8]})"
        
        print(f"{phase_icon} {event.type}{subject_info}")
    
    def print_summary(self, test_name: str):
        """Print a summary of collected events"""
        print(f"\n📊 {test_name} Summary:")
        print(f"   Total events: {len(self.events)}")
        print(f"   Event types: {len(self.event_counts)}")
        print(f"   Parent-child pairs: {len(self.parent_child_pairs)}")
        
        if self.event_counts:
            print("   Event breakdown:")
            for event_type, count in sorted(self.event_counts.items()):
                print(f"     {event_type}: {count}")
        
        if self.parent_child_pairs:
            print("   Parent-child relationships found: ✅")
        else:
            print("   No parent-child relationships: ⚠️")


# Global event collector
collector = EventCollector()


async def test_basic_event_flow():
    """Test 1: Basic event emission and collection"""
    print("🧪 Test 1: Basic Event Flow")
    collector.reset()
    
    # Subscribe to all events
    bus = get_event_bus()
    subscription = bus.subscribe(
        handler=collector.collect_event,
        predicate=lambda e: True,  # Catch all events
        priority=EventPriority.HIGH
    )
    
    # Test entities
    entity = create_test_entity("basic_test_entity")
    document = create_test_document("Basic Test Doc")
    
    # Emit various events
    await emit_creation_events(entity, "basic_entity_creation")
    await emit_creation_events(document, "basic_document_creation")
    
    # Modify the entity
    old_status = entity.status
    entity.status = EntityStatus.PROCESSING
    await emit_modification_events(
        entity, 
        fields=["status"],
        old_values={"status": old_status.value},
        operation_name="status_change"
    )
    
    # Wait for all events to process
    await asyncio.sleep(0.1)
    
    # Cleanup
    bus.unsubscribe(subscription)
    collector.print_summary("Basic Event Flow")
    
    # Validate
    assert len(collector.events) > 0, "No events were collected"
    assert "creating" in collector.event_counts, "No creation events found"
    assert "created" in collector.event_counts, "No completion events found"
    print("✅ Basic event flow test passed\n")


async def test_parent_child_coordination():
    """Test 2: Parent-child event coordination"""
    print("🧪 Test 2: Parent-Child Event Coordination")
    collector.reset()
    
    # Subscribe to events
    bus = get_event_bus()
    subscription = bus.subscribe(
        handler=collector.collect_event,
        predicate=lambda e: True
    )
    
    # Create processing task
    task = create_test_task("coordination_test", "validation")
    
    # Emit processing events (should create parent-child relationship)
    await emit_processing_events(
        process_name="validation_process",
        inputs=[task],
        subject=task
    )
    
    # Wait for processing
    await asyncio.sleep(0.1)
    
    # Cleanup
    bus.unsubscribe(subscription)
    collector.print_summary("Parent-Child Coordination")
    
    # Validate parent-child relationships
    assert len(collector.parent_child_pairs) > 0, "No parent-child relationships found"
    print("✅ Parent-child coordination test passed\n")


async def test_complex_workflow():
    """Test 3: Complex workflow with multiple entities"""
    print("🧪 Test 3: Complex Workflow Simulation")
    collector.reset()
    
    # Subscribe to events
    bus = get_event_bus()
    subscription = bus.subscribe(
        handler=collector.collect_event,
        predicate=lambda e: True
    )
    
    # Create workflow scenario
    user, document, task, project = create_document_workflow_scenario()
    
    # Simulate workflow steps
    print("   Step 1: Create user account")
    await emit_creation_events(user, "user_registration")
    
    print("   Step 2: Create project")
    await emit_creation_events(project, "project_creation")
    
    print("   Step 3: Create document")
    await emit_creation_events(document, "document_creation")
    
    print("   Step 4: Start document processing")
    task.start_processing()
    await emit_processing_events(
        process_name="document_analysis",
        inputs=[document],
        outputs=[],  # Will be filled when processing completes
        subject=task
    )
    
    print("   Step 5: Update document content")
    changes = document.update_content("Updated content after processing")
    await emit_modification_events(
        document,
        fields=["content", "word_count", "modified_at"],
        old_values={k: v[0] for k, v in changes.items()},
        operation_name="content_update"
    )
    
    print("   Step 6: Complete task")
    task.complete_processing([document.id])
    await emit_modification_events(
        task,
        fields=["status", "completed_at", "progress"],
        operation_name="task_completion"
    )
    
    # Wait for all events
    await asyncio.sleep(0.2)
    
    # Cleanup
    bus.unsubscribe(subscription)
    collector.print_summary("Complex Workflow")
    
    # Validate workflow
    assert len(collector.events) >= 10, f"Expected at least 10 events, got {len(collector.events)}"
    assert "creating" in collector.event_counts, "No creation events"
    assert "modifying" in collector.event_counts, "No modification events"
    assert "processing" in collector.event_counts, "No processing events"
    print("✅ Complex workflow test passed\n")


async def test_state_transitions():
    """Test 4: State transition events"""
    print("🧪 Test 4: State Transition Events")
    collector.reset()
    
    # Subscribe to all state-related events (both parent and child events)
    bus = get_event_bus()
    
    @on(predicate=lambda e: "state" in e.type or isinstance(e, StateTransitionEvent))
    async def handle_state_events(event: Event):
        await collector.collect_event(event)
        # Only print state change details for actual StateTransitionEvent
        if isinstance(event, StateTransitionEvent):
            print(f"   🔄 State change: {event.from_state} → {event.to_state}")
    
    # Create entity and trigger state changes
    entity = create_test_entity("state_test_entity")
    
    # Simulate state transitions
    statuses = [EntityStatus.PROCESSING, EntityStatus.COMPLETED, EntityStatus.INACTIVE]
    
    for new_status in statuses:
        old_status, _ = entity.update_status(new_status, f"transition_to_{new_status.value}")
        
        # Emit state transition event using bridge function
        await emit_state_transition_events(
            entity,
            from_state=old_status.value,
            to_state=new_status.value,
            transition_reason=f"automated_transition_to_{new_status.value}"
        )
    
    # Wait for events
    await asyncio.sleep(0.1)
    
    collector.print_summary("State Transitions")
    
    # Validate state transitions
    state_events = [e for e in collector.events if isinstance(e, StateTransitionEvent)]
    transitioning_events = [e for e in collector.events if e.type == "state.transitioning"]
    
    # We expect 3 StateTransitionEvent (child events)
    # We expect 6 state.transitioning events (3 STARTED + 3 COMPLETED parent events)
    assert len(state_events) == 3, f"Expected 3 state transitions, got {len(state_events)}"
    assert len(transitioning_events) == 6, f"Expected 6 transitioning events (3 STARTED + 3 COMPLETED), got {len(transitioning_events)}"
    assert len(collector.event_counts) == 2, f"Expected 2 event types, got {len(collector.event_counts)}"
    assert len(collector.events) == 9, f"Expected 9 total events (6 parent + 3 child), got {len(collector.events)}"
    
    print("✅ State transition test passed\n")


async def test_event_timing():
    """Test 5: Event timing and performance"""
    print("🧪 Test 5: Event Timing and Performance")
    collector.reset()
    
    # Subscribe to events
    bus = get_event_bus()
    subscription = bus.subscribe(
        handler=collector.collect_event,
        predicate=lambda e: True
    )
    
    # Test timed operations
    def slow_operation(delay: float = 0.1):
        """Simulate a slow operation"""
        time.sleep(delay)
        return f"operation_completed_after_{delay}s"
    
    entity = create_test_entity("timing_test_entity")
    
    # Measure event overhead
    start_time = time.time()
    
    # Run timed operation
    result = await emit_timed_operation(
        "slow_processing",
        slow_operation,
        entity,
        delay=0.05  # 50ms operation
    )
    
    end_time = time.time()
    total_time = (end_time - start_time) * 1000  # Convert to ms
    
    # Wait for events
    await asyncio.sleep(0.1)
    
    # Cleanup
    bus.unsubscribe(subscription)
    
    # Find timing events
    timing_events = [e for e in collector.events if e.duration_ms is not None]
    
    collector.print_summary("Event Timing")
    print(f"   Total operation time: {total_time:.2f}ms")
    print(f"   Events with timing: {len(timing_events)}")
    
    if timing_events:
        for event in timing_events:
            print(f"   Event duration: {event.duration_ms:.2f}ms ({event.type})")
    
    # Validate timing
    assert len(timing_events) > 0, "No timing information captured"
    assert result is not None, "Operation result not returned"
    print("✅ Event timing test passed\n")


async def test_error_handling():
    """Test 6: Error handling and failure events"""
    print("🧪 Test 6: Error Handling")
    collector.reset()
    
    # Subscribe to events
    bus = get_event_bus()
    subscription = bus.subscribe(
        handler=collector.collect_event,
        predicate=lambda e: True
    )
    
    # Test validation failure
    document = create_test_document("Invalid Document")
    
    # Simulate validation failure
    await emit_validation_events(
        document,
        validation_type="content_validation",
        is_valid=False,
        errors=["Content too short", "Missing required fields"]
    )
    
    # Test processing failure
    def failing_operation():
        raise ValueError("Simulated processing failure")
    
    try:
        await emit_timed_operation(
            "failing_process",
            failing_operation,
            document
        )
    except ValueError:
        pass  # Expected to fail
    
    # Wait for events
    await asyncio.sleep(0.1)
    
    # Cleanup
    bus.unsubscribe(subscription)
    
    # Find error events
    error_events = [e for e in collector.events if e.phase == EventPhase.FAILED]
    validation_events = [e for e in collector.events if "validat" in e.type]
    
    collector.print_summary("Error Handling")
    print(f"   Failed events: {len(error_events)}")
    print(f"   Validation events: {len(validation_events)}")
    
    # Validate error handling
    assert len(error_events) > 0, "No error events captured"
    assert len(validation_events) > 0, "No validation events captured"
    print("✅ Error handling test passed\n")


async def test_event_bus_health():
    """Test 7: Event bus health and statistics"""
    print("🧪 Test 7: Event Bus Health Check")
    
    bus = get_event_bus()
    
    # Get initial statistics
    initial_stats = bus.get_statistics()
    print(f"   Initial event count: {initial_stats['total_events']}")
    print(f"   Queue size: {initial_stats.get('queue_size', 'unknown')}")
    print(f"   Subscriptions: {initial_stats['subscriptions']}")
    
    # Generate some load
    entities = [create_test_entity(f"load_test_{i}") for i in range(10)]
    
    for entity in entities:
        await emit_simple_event("load_test", entity, {"batch": "health_check"})
    
    # Wait for processing
    await asyncio.sleep(0.1)
    
    # Get final statistics
    final_stats = bus.get_statistics()
    print(f"   Final event count: {final_stats['total_events']}")
    
    # Validate health
    events_processed = final_stats['total_events'] - initial_stats['total_events']
    assert events_processed >= 10, f"Expected at least 10 events processed, got {events_processed}"
    
    print("✅ Event bus health check passed\n")


async def run_all_tests():
    """Run all validation tests"""
    print("🚀 Starting Event System Validation Tests\n")
    
    # Start the event bus
    bus = get_event_bus()
    await bus.start()
    
    try:
        # Run all tests
        await test_basic_event_flow()
        await test_parent_child_coordination()
        await test_complex_workflow()
        await test_state_transitions()
        await test_event_timing()
        await test_error_handling()
        await test_event_bus_health()
        
        print("🎉 All tests passed!")
        
        # Final statistics
        final_stats = bus.get_statistics()
        print(f"\n📈 Final Event Bus Statistics:")
        print(f"   Total events processed: {final_stats['total_events']}")
        print(f"   Event types seen: {len(final_stats['event_counts'])}")
        print(f"   Handler performance: {len(final_stats['handler_stats'])} handlers tracked")
        
        # Show event history
        history = bus.get_history(limit=10)
        print(f"\n📜 Recent Event History (last {len(history)} events):")
        for event in history[-5:]:  # Show last 5
            print(f"   {event.timestamp.strftime('%H:%M:%S.%f')[:-3]} | {event.type} | {event.phase}")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        raise
    finally:
        # Stop the event bus
        await bus.stop()
        print("\n🛑 Event bus stopped")


if __name__ == "__main__":
    # Run the tests
    asyncio.run(run_all_tests())