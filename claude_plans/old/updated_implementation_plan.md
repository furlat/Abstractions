# Updated Implementation Plan: Clean Architecture Callable Registry

## **Executive Summary**

This updated implementation plan integrates the circular dependency cleanup analysis with the callable registry design to create a clean, hierarchical implementation that respects proper architectural boundaries while delivering the complete enhanced functionality.

## **Clean Architecture Foundation**

### **Fixed Dependency Hierarchy**
```
Level 1: entity.py (PURE CORE - No ECS imports)
Level 2: ecs_address_parser.py (UTILITIES - Uses entity only)  
Level 3: functional_api.py (SERVICES - Uses entity + parser)
Level 4: callable_registry.py (APPLICATION - Uses everything)
```

### **Key Architectural Fixes**
1. **Remove `borrow_from_address()` from Entity class** - Move to functional_api.py
2. **Remove ECSAddressParser import from entity.py** - Break circular dependency
3. **Add InputPatternClassifier to ecs_address_parser.py** - Utility layer
4. **Add FunctionExecution entity to entity.py** - Core domain

## **Implementation Phases**

### **Phase 1: Circular Dependency Cleanup** 
*Priority: CRITICAL - Must be done first*

#### **Step 1.1: Remove Circular Import**
```python
# File: entity.py 
# REMOVE line 16:
# from abstractions.ecs.ecs_address_parser import ECSAddressParser

# REMOVE method from Entity class (lines 1569-1598):
# def borrow_from_address(self, address: str, target_field: str) -> None:
```

#### **Step 1.2: Move borrow_from_address to functional_api.py**
```python
# File: functional_api.py
# ADD new function:
def borrow_from_address(target_entity: Entity, address: str, target_field: str) -> None:
    """
    Borrow an attribute using ECS address string syntax.
    
    Args:
        target_entity: Entity to borrow into
        address: ECS address like "@uuid.field.subfield"
        target_field: The field name in target entity to set
    """
    entity_id, field_path = ECSAddressParser.parse_address(address)
    
    # Get source entity using registry
    root_ecs_id = EntityRegistry.ecs_id_to_root_id.get(entity_id)
    if not root_ecs_id:
        raise ValueError(f"Entity {entity_id} not found in registry")
    
    source_entity = EntityRegistry.get_stored_entity(root_ecs_id, entity_id)
    if not source_entity:
        raise ValueError(f"Could not retrieve entity {entity_id}")
    
    # For now, support only single-field borrowing (first field in path)
    source_field = field_path[0]
    
    # Use existing borrow_attribute_from method from entity
    target_entity.borrow_attribute_from(source_entity, source_field, target_field)
```

#### **Step 1.3: Update Existing Usage**
```python
# File: functional_api.py
# UPDATE create_entity_from_mapping() function:
# OLD: instance.borrow_from_address(value, field_name)
# NEW: borrow_from_address(instance, value, field_name)
```

#### **Step 1.4: Add FunctionExecution to entity.py**
```python
# File: entity.py
# ADD at end of file (after existing example entities):
class FunctionExecution(Entity):
    """
    Minimal entity for tracking function execution relationships.
    
    This tracks the relationship between input entities, executed functions,
    and output entities for complete audit trails and provenance tracking.
    """
    function_name: str = ""
    input_entity_id: Optional[UUID] = None
    output_entity_id: Optional[UUID] = None
    execution_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    execution_status: str = "completed"  # "completed", "failed", "pending"
    error_message: Optional[str] = None
    
    # Execution semantics detected via live_id analysis
    execution_semantic: str = ""  # "mutation", "creation", "detachment"
    
    # For future enhancement - execution metadata
    execution_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def mark_as_failed(self, error: str) -> None:
        """Mark execution as failed with error message."""
        self.execution_status = "failed"
        self.error_message = error
    
    def mark_as_completed(self, semantic: str) -> None:
        """Mark execution as completed with detected semantic."""
        self.execution_status = "completed"
        self.execution_semantic = semantic
```

### **Phase 2: Enhanced Utilities Layer**
*Priority: HIGH - Enables advanced features*

#### **Step 2.1: Add Pattern Classification to ecs_address_parser.py**
```python
# File: ecs_address_parser.py
# ADD after existing classes:

class InputPatternClassifier:
    """Classify input patterns for callable registry."""
    
    @classmethod
    def classify_kwargs(cls, kwargs: Dict[str, Any]) -> Tuple[str, Dict[str, str]]:
        """
        Classify input pattern types.
        
        Returns:
            Tuple of (pattern_type, field_classifications)
            
        Pattern Types:
            - "pure_borrowing": All @uuid.field strings
            - "pure_transactional": All direct Entity objects  
            - "mixed": Combination of both
            - "direct": Only primitive values
        """
        entity_count = 0
        address_count = 0
        direct_count = 0
        
        classification = {}
        
        for key, value in kwargs.items():
            if hasattr(value, 'ecs_id'):  # Duck typing for Entity
                entity_count += 1
                classification[key] = "entity"
            elif isinstance(value, str) and cls.is_ecs_address(value):
                address_count += 1
                classification[key] = "address"
            else:
                direct_count += 1
                classification[key] = "direct"
        
        # Determine pattern type
        if entity_count > 0 and address_count == 0:
            pattern_type = "pure_transactional"
        elif address_count > 0 and entity_count == 0:
            pattern_type = "pure_borrowing"
        elif entity_count > 0 and address_count > 0:
            pattern_type = "mixed"
        else:
            pattern_type = "direct"
        
        return pattern_type, classification
    
    @classmethod
    def is_ecs_address(cls, value: str) -> bool:
        """Check if string is ECS address format."""
        return ECSAddressParser.is_ecs_address(value)
```

#### **Step 2.2: Enhance ECS Address Parser with Tree Navigation**
```python
# File: ecs_address_parser.py
# ADD method to ECSAddressParser class:

@classmethod
def resolve_with_tree_navigation(cls, address: str, entity_tree=None) -> Any:
    """
    Enhanced resolution using EntityTree navigation when available.
    
    Args:
        address: ECS address string
        entity_tree: Optional EntityTree for efficient navigation
        
    Returns:
        Resolved value with improved performance
    """
    entity_id, field_path = cls.parse_address(address)
    
    if entity_tree and entity_id in entity_tree.nodes:
        # Use tree navigation for better performance
        entity = entity_tree.nodes[entity_id]
        if entity:
            try:
                return functools.reduce(getattr, field_path, entity)
            except AttributeError as e:
                raise ValueError(f"Field path '{'.'.join(field_path)}' not found: {e}")
    
    # Fallback to registry-based resolution
    return cls.resolve_address(address)
```

### **Phase 3: Enhanced Services Layer**
*Priority: HIGH - Pattern-aware operations*

#### **Step 3.1: Add Pattern-Aware Composite Entity Creation**
```python
# File: functional_api.py
# ADD new function:

def create_composite_entity_with_pattern_detection(
    entity_class: Type[Entity], 
    field_mappings: Dict[str, Union[str, Any, Entity]], 
    register: bool = False
) -> Tuple[Entity, Dict[str, str]]:
    """
    Enhanced composite entity creation with pattern detection.
    
    Returns:
        Tuple of (created_entity, pattern_classification)
    """
    from .ecs_address_parser import InputPatternClassifier
    
    # Step 1: Classify input patterns
    pattern_type, classification = InputPatternClassifier.classify_kwargs(field_mappings)
    
    # Step 2: Handle mixed patterns appropriately
    if pattern_type == "mixed":
        # Special handling for mixed entity/address patterns
        resolved_mappings = {}
        for field_name, value in field_mappings.items():
            if classification[field_name] == "entity":
                # Handle direct entity reference
                resolved_mappings[field_name] = value
            elif classification[field_name] == "address":
                # Resolve address to value
                resolved_mappings[field_name] = ECSAddressParser.resolve_address(value)
            else:
                # Direct value
                resolved_mappings[field_name] = value
        
        entity = create_composite_entity(entity_class, resolved_mappings, register)
        return entity, classification
    
    # Step 3: Use existing implementation for pure patterns
    entity = create_composite_entity(entity_class, field_mappings, register)
    return entity, classification
```

### **Phase 4: Enhanced Application Layer**
*Priority: HIGH - Complete callable registry features*

#### **Step 4.1: Update CallableRegistry with Pattern Classification**
```python
# File: callable_registry.py
# REPLACE existing _execute_async method:

@classmethod
async def _execute_async(cls, func_name: str, **kwargs) -> Entity:
    """Execute function with enhanced pattern detection."""
    from .ecs_address_parser import InputPatternClassifier
    
    # Step 1: Get function metadata
    metadata = cls.get_metadata(func_name)
    if not metadata:
        raise ValueError(f"Function '{func_name}' not registered")
    
    # Step 2: Detect execution pattern using clean architecture
    pattern_type, classification = InputPatternClassifier.classify_kwargs(kwargs)
    
    # Step 3: Route to appropriate execution strategy
    if pattern_type in ["pure_transactional", "mixed"]:
        return await cls._execute_transactional(metadata, kwargs, classification)
    else:
        return await cls._execute_borrowing(metadata, kwargs, classification)
```

#### **Step 4.2: Add Enhanced Input Processing**
```python
# File: callable_registry.py
# REPLACE existing _create_input_entity_with_borrowing method:

@classmethod
async def _create_input_entity_with_borrowing(
    cls,
    input_entity_class: Type[Entity],
    kwargs: Dict[str, Any],
    classification: Optional[Dict[str, str]] = None
) -> Entity:
    """
    Create input entity using enhanced borrowing patterns.
    
    Leverages:
    - create_composite_entity_with_pattern_detection() from functional_api.py
    - Enhanced pattern classification for mixed inputs
    - Automatic dependency tracking
    """
    from .functional_api import create_composite_entity_with_pattern_detection
    
    # Use enhanced composite entity creation
    if classification:
        # Pattern already classified - use existing create_composite_entity
        input_entity = create_composite_entity(
            entity_class=input_entity_class,
            field_mappings=kwargs,
            register=False
        )
    else:
        # Use pattern-aware creation
        input_entity, _ = create_composite_entity_with_pattern_detection(
            entity_class=input_entity_class,
            field_mappings=kwargs,
            register=False
        )
    
    return input_entity
```

#### **Step 4.3: Add Enhanced Function Execution Tracking**
```python
# File: callable_registry.py
# UPDATE _record_function_execution method:

@classmethod
async def _record_function_execution(
    cls,
    input_entity: Entity,
    output_entity: Entity, 
    function_name: str
) -> None:
    """Record function execution with enhanced tracking."""
    from .entity import FunctionExecution
    
    # Create FunctionExecution entity for audit trail
    execution_record = FunctionExecution(
        function_name=function_name,
        input_entity_id=input_entity.ecs_id,
        output_entity_id=output_entity.ecs_id
    )
    execution_record.mark_as_completed("creation")  # Default semantic
    execution_record.promote_to_root()
```

### **Phase 5: Enhanced Examples and Testing**
*Priority: MEDIUM - Validation and demonstration*

#### **Step 5.1: Create Enhanced Base ECS Example**
```python
# File: abstractions/examples/enhanced_ecs_example.py
# NEW FILE demonstrating expanded patterns:

#!/usr/bin/env python3
"""
Enhanced ECS Example: Callable Registry Pattern Showcase

This example demonstrates the enhanced callable registry features including:
- Mixed input patterns (entities + address strings)
- Pattern classification and detection
- Enhanced address parsing with tree navigation
- Function execution tracking
- Clean architectural separation
"""

from typing import List, Optional, Tuple
from pydantic import Field
from uuid import UUID

from abstractions.ecs.entity import (
    Entity, EntityRegistry, build_entity_tree, FunctionExecution
)
from abstractions.ecs.ecs_address_parser import (
    ECSAddressParser, InputPatternClassifier
)
from abstractions.ecs.functional_api import (
    create_composite_entity_with_pattern_detection, borrow_from_address
)
from abstractions.ecs.callable_registry import CallableRegistry

# ... implementation details for expanded examples
```

#### **Step 5.2: Add Pattern Classification Tests**
```python
# File: tests/test_pattern_classification.py
# NEW FILE testing pattern classification:

import unittest
from abstractions.ecs.entity import Entity
from abstractions.ecs.ecs_address_parser import InputPatternClassifier

class TestPatternClassification(unittest.TestCase):
    
    def test_pure_borrowing_pattern(self):
        """Test classification of pure borrowing inputs."""
        kwargs = {
            "name": "@student_uuid.name",
            "age": "@student_uuid.age",
            "gpa": "@record_uuid.gpa"
        }
        pattern_type, classification = InputPatternClassifier.classify_kwargs(kwargs)
        
        self.assertEqual(pattern_type, "pure_borrowing")
        self.assertEqual(classification["name"], "address")
        self.assertEqual(classification["age"], "address")
        self.assertEqual(classification["gpa"], "address")
    
    def test_mixed_pattern(self):
        """Test classification of mixed entity + address inputs."""
        student = Entity()
        kwargs = {
            "student": student,  # Direct entity
            "name": "@student_uuid.name",  # Address
            "threshold": 3.5  # Primitive
        }
        pattern_type, classification = InputPatternClassifier.classify_kwargs(kwargs)
        
        self.assertEqual(pattern_type, "mixed")
        self.assertEqual(classification["student"], "entity")
        self.assertEqual(classification["name"], "address")
        self.assertEqual(classification["threshold"], "direct")
```

## **Implementation Sequence and Dependencies**

### **Critical Path Dependencies**
```
Phase 1 (Cleanup) → Phase 2 (Utilities) → Phase 3 (Services) → Phase 4 (Application)
     ↓                    ↓                     ↓                    ↓
No circular         Pattern           Enhanced composite     Complete registry
dependencies      classification      entity creation       with all patterns
```

### **Validation Checkpoints**
1. **After Phase 1**: All existing tests pass, no circular imports
2. **After Phase 2**: Pattern classification works correctly
3. **After Phase 3**: Mixed pattern composite entities work
4. **After Phase 4**: All 7 input patterns (A1-A7) supported

## **Benefits of Clean Architecture Approach**

### **✅ Dependency Clarity**
- Each layer only imports from layers below it
- No circular dependencies or inline imports
- Clear separation of concerns

### **✅ Maintainable Enhancement**
- New features added to appropriate architectural layer
- Existing functionality preserved and reused
- Clean upgrade path without breaking changes

### **✅ Testing Isolation**
- Each layer can be tested independently
- Mock dependencies flow downward only
- Clear test boundaries and responsibilities

### **✅ Future-Proof Design**
- Easy to add new pattern types to utility layer
- Service layer can be enhanced without touching core
- Application layer features don't pollute lower layers

## **Migration Checklist**

### **Phase 1 Checklist:**
- [ ] Remove ECSAddressParser import from entity.py
- [ ] Remove borrow_from_address method from Entity class
- [ ] Add borrow_from_address function to functional_api.py
- [ ] Update create_entity_from_mapping to use new function
- [ ] Add FunctionExecution entity to entity.py
- [ ] Run all existing tests to ensure no regressions

### **Phase 2 Checklist:**
- [ ] Add InputPatternClassifier to ecs_address_parser.py
- [ ] Add resolve_with_tree_navigation method
- [ ] Test pattern classification with all input types
- [ ] Verify enhanced address resolution performance

### **Phase 3 Checklist:**
- [ ] Add create_composite_entity_with_pattern_detection
- [ ] Test mixed pattern handling
- [ ] Verify backward compatibility with existing patterns
- [ ] Performance test enhanced composite creation

### **Phase 4 Checklist:**
- [ ] Update CallableRegistry with pattern classification
- [ ] Enhanced input processing with mixed patterns
- [ ] Add function execution tracking
- [ ] Test all 7 input patterns (A1-A7)
- [ ] End-to-end integration testing

### **Phase 5 Checklist:**
- [ ] Create enhanced examples
- [ ] Add comprehensive tests
- [ ] Performance benchmarking
- [ ] Documentation updates

## **Result: Production-Ready Callable Registry**

After this implementation, the callable registry will have:

1. **Clean Architecture** - No circular dependencies, proper layer separation
2. **Complete Pattern Support** - All 7 input patterns (A1-A7) working
3. **Enhanced Performance** - Tree navigation, optimized lookups
4. **Full Audit Trails** - Function execution tracking with FunctionExecution entities
5. **Backward Compatibility** - All existing code continues to work
6. **Future Extensibility** - Clean foundation for advanced features

The implementation follows the same hierarchical, non-circular principles as the entity trees it manages, creating a solid architectural foundation for building sophisticated entity-native function execution capabilities.