#!/usr/bin/env python3
"""
Test script for Phase 1: Context Management Infrastructure

This script tests the basic context management functionality before
integrating with the event system.
"""

import sys
from uuid import uuid4
from pydantic import BaseModel
from typing import Optional

# Add the project root to path so we can import our modules
sys.path.append('.')

from abstractions.events.context import (
    get_current_parent_event,
    push_event_context,
    pop_event_context,
    get_context_depth,
    get_context_stack,
    get_root_event,
    clear_context,
    get_context_statistics,
    validate_context_balance,
    EventContextManager
)

# Mock event class for testing
class MockEvent(BaseModel):
    id: str
    type: str
    parent_id: Optional[str] = None
    root_id: Optional[str] = None
    lineage_id: Optional[str] = None

def test_basic_stack_operations():
    """Test basic push/pop operations"""
    print("🧪 Testing basic stack operations...")
    
    # Start with clean context
    clear_context()
    
    # Test empty stack
    assert get_current_parent_event() is None
    assert get_context_depth() == 0
    assert len(get_context_stack()) == 0
    
    # Create test events
    event1 = MockEvent(id="event1", type="test", lineage_id="lineage1")
    event2 = MockEvent(id="event2", type="test", lineage_id="lineage2")
    
    # Push first event
    push_event_context(event1)
    assert get_current_parent_event() == event1
    assert get_context_depth() == 1
    assert get_root_event() == event1
    
    # Push second event
    push_event_context(event2)
    assert get_current_parent_event() == event2
    assert get_context_depth() == 2
    assert get_root_event() == event1  # Root should still be first
    
    # Pop second event
    popped = pop_event_context()
    assert popped == event2
    assert get_current_parent_event() == event1
    assert get_context_depth() == 1
    
    # Pop first event
    popped = pop_event_context()
    assert popped == event1
    assert get_current_parent_event() is None
    assert get_context_depth() == 0
    
    print("✅ Basic stack operations passed!")

def test_context_statistics():
    """Test context statistics and validation"""
    print("🧪 Testing context statistics...")
    
    clear_context()
    
    # Initial stats
    stats = get_context_statistics()
    assert stats['current_depth'] == 0
    assert stats['push_count'] == 0
    assert stats['pop_count'] == 0
    assert stats['balance_check'] == True
    
    # Push some events
    event1 = MockEvent(id="stats1", type="test")
    event2 = MockEvent(id="stats2", type="test")
    
    push_event_context(event1)
    push_event_context(event2)
    
    # Check stats after pushes
    stats = get_context_statistics()
    assert stats['current_depth'] == 2
    assert stats['push_count'] == 2
    assert stats['pop_count'] == 0
    assert stats['balance_check'] == True
    
    # Pop one event
    pop_event_context()
    
    # Check stats after pop
    stats = get_context_statistics()
    assert stats['current_depth'] == 1
    assert stats['push_count'] == 2
    assert stats['pop_count'] == 1
    assert stats['balance_check'] == True
    
    # Validate balance
    assert validate_context_balance() == True
    
    print("✅ Context statistics passed!")

def test_context_manager():
    """Test the EventContextManager"""
    print("🧪 Testing EventContextManager...")
    
    clear_context()
    
    event = MockEvent(id="manager_test", type="test")
    
    # Test context manager
    assert get_current_parent_event() is None
    
    with EventContextManager(event) as ctx_event:
        assert ctx_event == event
        assert get_current_parent_event() == event
        assert get_context_depth() == 1
    
    # Should be cleaned up after context manager
    assert get_current_parent_event() is None
    assert get_context_depth() == 0
    
    print("✅ EventContextManager passed!")

def test_auto_parent_linking():
    """Test automatic parent linking functionality"""
    print("🧪 Testing auto parent linking...")
    
    clear_context()
    
    # Create parent and child events
    parent = MockEvent(id="parent", type="test", lineage_id="lineage_parent")
    child = MockEvent(id="child", type="test")
    
    # Push parent to context
    push_event_context(parent)
    
    # Test the create_child_event_with_context function
    from abstractions.events.context import create_child_event_with_context
    
    def create_child_event():
        return MockEvent(id="auto_child", type="test")
    
    # This should automatically link to parent
    auto_child = create_child_event_with_context(create_child_event)
    
    # Check that parent linking was applied
    assert auto_child.parent_id == parent.id
    assert auto_child.root_id == parent.id  # Parent is root
    assert auto_child.lineage_id == parent.lineage_id
    
    print("✅ Auto parent linking passed!")

def test_error_handling():
    """Test error handling and edge cases"""
    print("🧪 Testing error handling...")
    
    clear_context()
    
    # Test popping from empty stack
    popped = pop_event_context()
    assert popped is None
    
    # Test with events that don't have all attributes
    class MinimalEvent(BaseModel):
        name: str
    
    minimal = MinimalEvent(name="minimal")
    
    # Should work even without id/parent_id attributes
    push_event_context(minimal)
    assert get_current_parent_event() == minimal
    
    popped = pop_event_context()
    assert popped == minimal
    
    print("✅ Error handling passed!")

def run_all_tests():
    """Run all context management tests"""
    print("🚀 Starting Phase 1 Context Management Tests\n")
    
    try:
        test_basic_stack_operations()
        test_context_statistics()
        test_context_manager()
        test_auto_parent_linking()
        test_error_handling()
        
        print("\n🎉 All Phase 1 tests passed!")
        print("✅ Context management infrastructure is working correctly")
        
        # Final stats
        stats = get_context_statistics()
        print(f"\nFinal context stats: {stats}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)