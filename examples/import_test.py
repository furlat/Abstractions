#!/usr/bin/env python3
"""
Test script to verify circular dependencies are resolved.
This should import all modules without circular import errors.
"""

import sys
sys.path.append('.')

print("Testing imports...")

# Test base entity module
try:
    from abstractions.ecs.entity import Entity, EntityRegistry, FunctionExecution, ConfigEntity
    print("✅ entity.py imports successfully")
except ImportError as e:
    print(f"❌ entity.py import failed: {e}")

# Test return type analyzer
try:
    from abstractions.ecs.return_type_analyzer import ReturnTypeAnalyzer, QuickPatternDetector
    print("✅ return_type_analyzer.py imports successfully")
except ImportError as e:
    print(f"❌ return_type_analyzer.py import failed: {e}")

# Test entity unpacker
try:
    from abstractions.ecs.entity_unpacker import EntityUnpacker, ContainerReconstructor
    print("✅ entity_unpacker.py imports successfully")
except ImportError as e:
    print(f"❌ entity_unpacker.py import failed: {e}")

# Test address parser
try:
    from abstractions.ecs.ecs_address_parser import ECSAddressParser, EntityReferenceResolver
    print("✅ ecs_address_parser.py imports successfully")
except ImportError as e:
    print(f"❌ ecs_address_parser.py import failed: {e}")

# Test functional API
try:
    from abstractions.ecs.functional_api import get, create_composite_entity, get_function_execution_siblings
    print("✅ functional_api.py imports successfully")
except ImportError as e:
    print(f"❌ functional_api.py import failed: {e}")

# Test the big one - callable registry (top level coordinator)
try:
    from abstractions.ecs.callable_registry import CallableRegistry
    print("✅ callable_registry.py imports successfully")
except ImportError as e:
    print(f"❌ callable_registry.py import failed: {e}")

# Test that QuickPatternDetector.analyze_type_signature is accessible
try:
    from abstractions.ecs.return_type_analyzer import QuickPatternDetector
    method = getattr(QuickPatternDetector, 'analyze_type_signature', None)
    if method:
        print("✅ QuickPatternDetector.analyze_type_signature is accessible")
    else:
        print("❌ QuickPatternDetector.analyze_type_signature is not accessible")
except Exception as e:
    print(f"❌ QuickPatternDetector method test failed: {e}")

# Test that the moved function is accessible
try:
    from abstractions.ecs.functional_api import get_function_execution_siblings
    print("✅ get_function_execution_siblings is accessible in functional_api")
except ImportError as e:
    print(f"❌ get_function_execution_siblings import failed: {e}")

print("\n🎉 Import test complete!")
print("If all imports show ✅, circular dependencies are resolved!")