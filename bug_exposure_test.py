#!/usr/bin/env python3
"""
Bug Exposure Test: Field Assumption Problem in CallableRegistry

This script demonstrates the exact conditions that trigger the 'result' field assumption bug.

The bug occurs when:
1. Functions have NO entity inputs (triggers broken execution paths)
2. Functions return specific BaseModel types (not generic results)
3. Output entity class has BaseModel field names, NOT a "result" field

Our existing examples never detected this because they always use entity inputs,
which trigger the CORRECT execution path (_execute_borrowing).
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic import BaseModel
from abstractions.ecs.callable_registry import CallableRegistry

print("🔥 Bug Exposure Test: Field Assumption Problem")
print("=" * 60)

# Define specific return types (not generic "result" field)
class UserStats(BaseModel):
    """Specific return type with named fields."""
    user_count: int
    active_count: int
    total_sessions: int

class SystemInfo(BaseModel):
    """Another specific return type."""
    version: str
    uptime_hours: float
    memory_usage: float

# ❌ BUG TRIGGER #1: No-input function with specific return type
@CallableRegistry.register("get_current_stats")
def get_current_stats() -> UserStats:
    """Function with NO inputs - triggers _execute_no_inputs path."""
    return UserStats(
        user_count=150,
        active_count=89, 
        total_sessions=1247
    )

# ❌ BUG TRIGGER #2: Primitive-only function with specific return type  
@CallableRegistry.register("get_system_info")
def get_system_info(include_memory: bool = True) -> SystemInfo:
    """Function with ONLY primitives - triggers _execute_primitives_only path."""
    return SystemInfo(
        version="2.1.0",
        uptime_hours=72.5,
        memory_usage=0.85 if include_memory else 0.0
    )

# ✅ WORKING EXAMPLE: Function that would work (for comparison)
@CallableRegistry.register("get_simple_count")  
def get_simple_count() -> int:
    """This would work because int gets wrapped as 'result' field."""
    return 42

print("\n🎯 Testing Bug Trigger #1: No-input function with specific return type")
print("Expected: TypeError - 'result' field doesn't exist in UserStats")
try:
    result1 = CallableRegistry.execute("get_current_stats")
    print(f"❌ UNEXPECTED: Bug didn't trigger! Got: {result1}")
except TypeError as e:
    print(f"✅ EXPECTED BUG: {e}")
except Exception as e:
    print(f"🤔 DIFFERENT ERROR: {e}")

print("\n🎯 Testing Bug Trigger #2: Primitive-only function with specific return type")  
print("Expected: TypeError - 'result' field doesn't exist in SystemInfo")
try:
    result2 = CallableRegistry.execute("get_system_info", include_memory=False)
    print(f"❌ UNEXPECTED: Bug didn't trigger! Got: {result2}")
except TypeError as e:
    print(f"✅ EXPECTED BUG: {e}")
except Exception as e:
    print(f"🤔 DIFFERENT ERROR: {e}")

print("\n🎯 Testing Working Example: Simple return type")
print("Expected: Works because int gets wrapped as 'result' field")
try:
    result3 = CallableRegistry.execute("get_simple_count")
    print(f"✅ WORKS: {result3}")
    if hasattr(result3, 'result'):
        print(f"   Value: {getattr(result3, 'result', 'N/A')}")
except Exception as e:
    print(f"❌ UNEXPECTED ERROR: {e}")

print("\n📊 Analysis:")
print("1. ❌ Bug #1: _execute_no_inputs assumes 'result' field")
print("2. ❌ Bug #2: _execute_primitives_only assumes 'result' field") 
print("3. ✅ Simple types work because they fit the 'result' pattern")
print("\n🔧 Root Cause:")
print("- No-input/primitive-only functions use broken field assumption")
print("- Entity-input functions use CORRECT field detection logic")
print("- Inconsistent patterns within same codebase!")

print("\n🏗️ Output Entity Class Analysis:")
print("Let's examine what the output entity classes actually look like...")

# Inspect the generated output entity classes
functions = ["get_current_stats", "get_system_info", "get_simple_count"]
for func_name in functions:
    metadata = CallableRegistry.get_metadata(func_name)
    if metadata:
        print(f"\nFunction: {func_name}")
        print(f"  Output class: {metadata.output_entity_class.__name__}")
        print(f"  Fields: {list(metadata.output_entity_class.model_fields.keys())}")
        
        # Check if 'result' field exists
        has_result_field = 'result' in metadata.output_entity_class.model_fields
        print(f"  Has 'result' field: {has_result_field}")
        
        if not has_result_field:
            print(f"  ❌ PROBLEM: No 'result' field, but broken paths assume it exists!")
        else:
            print(f"  ✅ OK: 'result' field exists, broken paths will work")

print("\n🎉 Bug Exposure Complete!")
print("This demonstrates exactly why the field assumption fails.")