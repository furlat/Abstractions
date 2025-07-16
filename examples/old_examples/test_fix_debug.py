#!/usr/bin/env python3
"""
Quick test to debug empty container fixes
"""

import sys
sys.path.append('.')

from abstractions.ecs.return_type_analyzer import ReturnTypeAnalyzer, ReturnPattern
from abstractions.ecs.entity_unpacker import EntityUnpacker

def test_empty_containers():
    print("=== Testing Empty Container Fixes ===")
    
    # Test empty list
    print("\n--- Empty List ---")
    result = []
    analysis = ReturnTypeAnalyzer.analyze_return(result)
    print(f"Pattern: {analysis.pattern}")
    print(f"Strategy: {analysis.unpacking_strategy}")
    print(f"Entity count: {analysis.entity_count}")
    
    unpacking = EntityUnpacker.unpack_return(result, analysis)
    print(f"Primary entities: {len(unpacking.primary_entities)}")
    print(f"Metadata: {unpacking.metadata}")
    
    # Test empty dict
    print("\n--- Empty Dict ---")
    result = {}
    analysis = ReturnTypeAnalyzer.analyze_return(result)
    print(f"Pattern: {analysis.pattern}")
    print(f"Strategy: {analysis.unpacking_strategy}")
    print(f"Entity count: {analysis.entity_count}")
    
    unpacking = EntityUnpacker.unpack_return(result, analysis)
    print(f"Primary entities: {len(unpacking.primary_entities)}")
    print(f"Metadata: {unpacking.metadata}")

if __name__ == "__main__":
    test_empty_containers()