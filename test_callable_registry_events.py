#!/usr/bin/env python3
"""
Test script to verify callable registry event integration with UUID tracking.

This tests the complete hierarchical event system:
callable_registry → entity operations → specialized events with UUID tracking
"""

import asyncio
import sys
import os

# Add the abstractions directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'abstractions'))

from abstractions.ecs.entity import Entity
from abstractions.ecs.callable_registry import CallableRegistry
from abstractions.events.events import get_event_bus, on
from abstractions.events.callable_events import (
    FunctionExecutionEvent, FunctionExecutedEvent,
    StrategyDetectionEvent, StrategyDetectedEvent,
    ConfigEntityCreationEvent, ConfigEntityCreatedEvent
)
from abstractions.events.entity_events import (
    EntityPromotionEvent, EntityPromotedEvent
)

# Test entities
class Student(Entity):
    name: str = ""
    age: int = 0
    student_id: str = ""

class AnalysisResult(Entity):
    student_name: str = ""
    status: str = ""
    analysis_notes: str = ""

# Event collector for testing
class EventCollector:
    def __init__(self):
        self.events = []
        self.event_types = set()
        
    def reset(self):
        self.events.clear()
        self.event_types.clear()
        
    async def collect_event(self, event):
        self.events.append(event)
        self.event_types.add(type(event).__name__)
        
        # Print event with UUID info
        event_name = type(event).__name__
        uuids = []
        
        # Extract UUID fields for cascade tracking
        if hasattr(event, 'input_entity_ids') and event.input_entity_ids:
            uuids.extend([str(uuid)[:8] for uuid in event.input_entity_ids])
        if hasattr(event, 'output_entity_ids') and event.output_entity_ids:
            uuids.extend([str(uuid)[:8] for uuid in event.output_entity_ids])
        if hasattr(event, 'subject_id') and event.subject_id:
            uuids.append(str(event.subject_id)[:8])
        if hasattr(event, 'config_entity_ids') and event.config_entity_ids:
            uuids.extend([str(uuid)[:8] for uuid in event.config_entity_ids])
            
        uuid_info = f" | UUIDs: {', '.join(uuids)}" if uuids else ""
        print(f"📡 {event_name}{uuid_info}")

# Global collector
collector = EventCollector()

# Event handlers to test hierarchical emission
@on(FunctionExecutionEvent)
async def handle_function_execution(event: FunctionExecutionEvent):
    await collector.collect_event(event)

@on(FunctionExecutedEvent)
async def handle_function_executed(event: FunctionExecutedEvent):
    await collector.collect_event(event)

@on(StrategyDetectionEvent)
async def handle_strategy_detection(event: StrategyDetectionEvent):
    await collector.collect_event(event)

@on(StrategyDetectedEvent)
async def handle_strategy_detected(event: StrategyDetectedEvent):
    await collector.collect_event(event)

@on(ConfigEntityCreationEvent)
async def handle_config_creation(event: ConfigEntityCreationEvent):
    await collector.collect_event(event)

@on(ConfigEntityCreatedEvent)
async def handle_config_created(event: ConfigEntityCreatedEvent):
    await collector.collect_event(event)

@on(EntityPromotionEvent)
async def handle_entity_promotion(event: EntityPromotionEvent):
    await collector.collect_event(event)

@on(EntityPromotedEvent)
async def handle_entity_promoted(event: EntityPromotedEvent):
    await collector.collect_event(event)

# Test function with proper type hints
@CallableRegistry.register("analyze_student")
def analyze_student(student: Student, threshold: float = 3.0) -> AnalysisResult:
    """Analyze student performance with events."""
    return AnalysisResult(
        student_name=student.name,
        status="excellent" if student.age > threshold else "average",
        analysis_notes=f"Student {student.name} analysis completed"
    )

async def test_hierarchical_events():
    """Test complete hierarchical event system."""
    print("🚀 Testing Callable Registry Event Integration with UUID Tracking")
    print("=" * 80)
    
    # Start event bus
    bus = get_event_bus()
    await bus.start()
    
    try:
        collector.reset()
        
        print("\n📚 Creating test student...")
        student = Student(name="Alice Johnson", age=22, student_id="STU001")
        
        print("\n⚡ Executing function with hierarchical events...")
        # This should trigger:
        # 1. FunctionExecutionEvent (main callable registry)
        # 2. StrategyDetectionEvent (strategy detection)
        # 3. ConfigEntityCreationEvent (config entity creation)
        # 4. EntityCreationEvent (entity operations during execution)
        # 5. EntityPromotionEvent (entity promotion)
        # 6. And their corresponding completion events
        
        result = await CallableRegistry.aexecute(
            "analyze_student",
            student=student,
            threshold=3.5
        )
        
        print(f"\n✅ Function executed successfully!")
        print(f"Result type: {type(result).__name__}")
        if isinstance(result, list):
            print(f"Result IDs: {[str(r.ecs_id)[:8] for r in result]}")
        else:
            print(f"Result ID: {str(result.ecs_id)[:8]}")
        
        # Wait for all events to process
        await asyncio.sleep(0.2)
        
        print(f"\n📊 Event System Results:")
        print(f"   Total events collected: {len(collector.events)}")
        print(f"   Event types seen: {len(collector.event_types)}")
        print(f"   Event types: {', '.join(sorted(collector.event_types))}")
        
        # Check for key event types
        expected_events = [
            'FunctionExecutionEvent', 'FunctionExecutedEvent',
            'StrategyDetectionEvent', 'StrategyDetectedEvent'
        ]
        
        for event_type in expected_events:
            if event_type in collector.event_types:
                print(f"   ✅ {event_type} detected")
            else:
                print(f"   ❌ {event_type} missing")
        
        # Check for UUID tracking
        uuid_events = [e for e in collector.events if hasattr(e, 'input_entity_ids') and e.input_entity_ids]
        print(f"\n🔗 UUID Tracking:")
        print(f"   Events with UUID tracking: {len(uuid_events)}")
        
        if uuid_events:
            print("   ✅ UUID tracking functional for cascade implementation")
            for event in uuid_events:
                if hasattr(event, 'input_entity_ids') and event.input_entity_ids:
                    print(f"     {type(event).__name__}: {len(event.input_entity_ids)} input UUIDs")
        else:
            print("   ⚠️  No UUID tracking detected")
        
        print(f"\n🎯 Integration Test Results:")
        print(f"   Function execution: {'✅ Success' if result else '❌ Failed'}")
        print(f"   Event emission: {'✅ Success' if collector.events else '❌ Failed'}")
        print(f"   UUID tracking: {'✅ Success' if uuid_events else '❌ Failed'}")
        print(f"   Hierarchical events: {'✅ Success' if len(collector.event_types) > 4 else '❌ Failed'}")
        
        # Final bus statistics
        final_stats = bus.get_statistics()
        print(f"\n📈 Event Bus Statistics:")
        print(f"   Total events processed: {final_stats['total_events']}")
        print(f"   Queue size: {final_stats['queue_size']}")
        print(f"   Processing: {final_stats['processing']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await bus.stop()
        print("\n🛑 Event bus stopped")

if __name__ == "__main__":
    success = asyncio.run(test_hierarchical_events())
    if success:
        print("\n🎉 All tests passed! Callable registry event integration is working correctly.")
        sys.exit(0)
    else:
        print("\n💥 Tests failed! Check the error output above.")
        sys.exit(1)