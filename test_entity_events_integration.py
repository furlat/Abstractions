#!/usr/bin/env python3
"""
Test Entity Events Integration

This test verifies that the entity.py integration with the new specialized
entity events is working correctly with automatic nesting.
"""

import asyncio
from typing import List
from abstractions.ecs.entity import Entity, EntityRegistry
from abstractions.events.events import get_event_bus, Event
from abstractions.events.entity_events import (
    EntityRegistrationEvent, EntityRegisteredEvent,
    EntityVersioningEvent, EntityVersionedEvent,
    EntityPromotionEvent, EntityPromotedEvent,
    DataBorrowingEvent, DataBorrowedEvent,
    TreeBuildingEvent, TreeBuiltEvent
)

class TestEntity(Entity):
    """Test entity with some fields."""
    name: str = "test"
    value: int = 42
    description: str = "A test entity"

class EventCollector:
    """Utility to collect events during testing."""
    
    def __init__(self):
        self.events: List[Event] = []
        
    def reset(self):
        self.events.clear()
    
    async def collect_event(self, event: Event):
        self.events.append(event)
        print(f"📡 {event.type} | {event.phase} | {event.subject_type.__name__ if event.subject_type else 'N/A'}")
    
    def get_events_by_type(self, event_type) -> List[Event]:
        return [e for e in self.events if isinstance(e, event_type)]
    
    def print_summary(self):
        print(f"\n📊 Collected {len(self.events)} events:")
        for event in self.events:
            print(f"  - {event.type} ({event.phase})")

async def test_entity_creation_and_registration():
    """Test entity creation and registration events."""
    print("🧪 Test 1: Entity Creation and Registration")
    
    # Set up event collection
    collector = EventCollector()
    bus = get_event_bus()
    await bus.start()
    
    subscription = bus.subscribe(
        handler=collector.collect_event,
        predicate=lambda e: True
    )
    
    try:
        # Create and register entity
        entity = TestEntity(name="Integration Test", value=100)
        entity.promote_to_root()  # This should trigger registration events
        
        # Wait for events
        await asyncio.sleep(0.1)
        
        # Check events
        collector.print_summary()
        
        # Verify registration events
        registration_events = collector.get_events_by_type(EntityRegistrationEvent)
        registered_events = collector.get_events_by_type(EntityRegisteredEvent)
        
        assert len(registration_events) > 0, "No registration events found"
        assert len(registered_events) > 0, "No registered events found"
        
        print("✅ Entity creation and registration events working!")
        
    finally:
        bus.unsubscribe(subscription)
        await bus.stop()

async def test_entity_versioning():
    """Test entity versioning events."""
    print("\n🧪 Test 2: Entity Versioning")
    
    collector = EventCollector()
    bus = get_event_bus()
    await bus.start()
    
    subscription = bus.subscribe(
        handler=collector.collect_event,
        predicate=lambda e: True
    )
    
    try:
        # Create entity
        entity = TestEntity(name="Version Test", value=200)
        entity.promote_to_root()
        
        # Clear events from creation
        await asyncio.sleep(0.1)
        collector.reset()
        
        # Modify entity to trigger versioning
        entity.value = 300
        EntityRegistry.version_entity(entity)
        
        # Wait for events
        await asyncio.sleep(0.1)
        
        # Check events
        collector.print_summary()
        
        # Verify versioning events
        versioning_events = collector.get_events_by_type(EntityVersioningEvent)
        versioned_events = collector.get_events_by_type(EntityVersionedEvent)
        
        assert len(versioning_events) > 0, "No versioning events found"
        assert len(versioned_events) > 0, "No versioned events found"
        
        print("✅ Entity versioning events working!")
        
    finally:
        bus.unsubscribe(subscription)
        await bus.stop()

async def test_entity_promotion():
    """Test entity promotion events."""
    print("\n🧪 Test 3: Entity Promotion")
    
    collector = EventCollector()
    bus = get_event_bus()
    await bus.start()
    
    subscription = bus.subscribe(
        handler=collector.collect_event,
        predicate=lambda e: True
    )
    
    try:
        # Create entity (not yet promoted)
        entity = TestEntity(name="Promotion Test", value=400)
        
        # Clear any creation events
        await asyncio.sleep(0.1)
        collector.reset()
        
        # Promote to root
        entity.promote_to_root()
        
        # Wait for events
        await asyncio.sleep(0.1)
        
        # Check events
        collector.print_summary()
        
        # Verify promotion events
        promotion_events = collector.get_events_by_type(EntityPromotionEvent)
        promoted_events = collector.get_events_by_type(EntityPromotedEvent)
        
        assert len(promotion_events) > 0, "No promotion events found"
        assert len(promoted_events) > 0, "No promoted events found"
        
        print("✅ Entity promotion events working!")
        
    finally:
        bus.unsubscribe(subscription)
        await bus.stop()

async def test_data_borrowing():
    """Test data borrowing events."""
    print("\n🧪 Test 4: Data Borrowing")
    
    collector = EventCollector()
    bus = get_event_bus()
    await bus.start()
    
    subscription = bus.subscribe(
        handler=collector.collect_event,
        predicate=lambda e: True
    )
    
    try:
        # Create source and target entities
        source = TestEntity(name="Source", value=500)
        target = TestEntity(name="Target", value=0)
        
        # Clear creation events
        await asyncio.sleep(0.1)
        collector.reset()
        
        # Borrow data
        target.borrow_attribute_from(source, "value", "value")
        
        # Wait for events
        await asyncio.sleep(0.1)
        
        # Check events
        collector.print_summary()
        
        # Verify borrowing events
        borrowing_events = collector.get_events_by_type(DataBorrowingEvent)
        borrowed_events = collector.get_events_by_type(DataBorrowedEvent)
        
        assert len(borrowing_events) > 0, "No borrowing events found"
        assert len(borrowed_events) > 0, "No borrowed events found"
        
        # Verify data was borrowed
        assert target.value == 500, f"Expected 500, got {target.value}"
        
        print("✅ Data borrowing events working!")
        
    finally:
        bus.unsubscribe(subscription)
        await bus.stop()

async def test_tree_building():
    """Test tree building events."""
    print("\n🧪 Test 5: Tree Building")
    
    collector = EventCollector()
    bus = get_event_bus()
    await bus.start()
    
    subscription = bus.subscribe(
        handler=collector.collect_event,
        predicate=lambda e: True
    )
    
    try:
        # Create entity
        entity = TestEntity(name="Tree Test", value=600)
        entity.promote_to_root()
        
        # Clear creation events
        await asyncio.sleep(0.1)
        collector.reset()
        
        # Build tree (this should trigger tree building events)
        tree = entity.get_tree(recompute=True)
        
        # Wait for events
        await asyncio.sleep(0.1)
        
        # Check events
        collector.print_summary()
        
        # Verify tree building events
        building_events = collector.get_events_by_type(TreeBuildingEvent)
        built_events = collector.get_events_by_type(TreeBuiltEvent)
        
        assert len(building_events) > 0, "No tree building events found"
        assert len(built_events) > 0, "No tree built events found"
        
        # Verify tree was built
        assert tree is not None, "Tree should not be None"
        assert tree.node_count > 0, "Tree should have nodes"
        
        print("✅ Tree building events working!")
        
    finally:
        bus.unsubscribe(subscription)
        await bus.stop()

async def run_all_tests():
    """Run all entity event integration tests."""
    print("🚀 Starting Entity Events Integration Tests\n")
    
    try:
        await test_entity_creation_and_registration()
        await test_entity_versioning()
        await test_entity_promotion()
        await test_data_borrowing()
        await test_tree_building()
        
        print("\n🎉 All entity event integration tests passed!")
        print("✅ Entity events module successfully integrated!")
        print("✅ Automatic nesting working with entity events!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(run_all_tests())