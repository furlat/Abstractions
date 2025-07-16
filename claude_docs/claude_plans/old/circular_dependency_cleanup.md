# Circular Dependency Cleanup Plan

## **Current Problem Analysis**

### **Circular Import Issue**
```
entity.py (line 16) → imports ecs_address_parser
ecs_address_parser.py (line 85) → imports entity 
```

**Root Cause**: `entity.py` has a `borrow_from_address()` method that uses `ECSAddressParser.parse_address()`, but `ECSAddressParser.resolve_address()` uses `EntityRegistry` from `entity.py`.

### **Architecture Violation**
The core entity system should NOT depend on higher-level utilities. This breaks the layered architecture principle.

## **Clean Layered Architecture (Target State)**

```
┌─────────────────────────────────────────────┐
│ Level 4: callable_registry.py              │  ← Application Layer
│ - Uses: entity, ecs_address_parser,        │
│   functional_api                           │
└─────────────────────────────────────────────┘
                        ▲
┌─────────────────────────────────────────────┐
│ Level 3: functional_api.py                 │  ← Service Layer  
│ - Uses: entity, ecs_address_parser         │
│ - Provides: High-level entity operations   │
└─────────────────────────────────────────────┘
                        ▲
┌─────────────────────────────────────────────┐
│ Level 2: ecs_address_parser.py             │  ← Utility Layer
│ - Uses: entity (EntityRegistry only)       │
│ - Provides: Address parsing & resolution   │
└─────────────────────────────────────────────┘
                        ▲
┌─────────────────────────────────────────────┐
│ Level 1: entity.py                         │  ← Core Domain Layer
│ - Uses: NOTHING from other ECS modules     │
│ - Provides: Entity, EntityTree,            │
│   EntityRegistry (pure core)               │
└─────────────────────────────────────────────┘
```

## **Refactoring Steps**

### **Step 1: Remove Circular Dependency**

#### **1.1 Move borrow_from_address() OUT of entity.py**

**Current Location**: `entity.py` line 1569-1594
**Target Location**: `functional_api.py` as a standalone function

**Rationale**: 
- Address parsing is a higher-level operation
- Core entities shouldn't know about address syntax
- Functional API is the appropriate layer for this operation

#### **1.2 Remove ECSAddressParser import from entity.py**

**Change**:
```python
# REMOVE this line from entity.py:
from abstractions.ecs.ecs_address_parser import ECSAddressParser
```

### **Step 2: Move borrow_from_address to functional_api.py**

#### **2.1 Add function to functional_api.py**

```python
def borrow_from_address(target_entity: Entity, address: str, target_field: str) -> None:
    """
    Borrow an attribute using ECS address string syntax.
    
    Args:
        target_entity: Entity to borrow into
        address: ECS address like "@uuid.field.subfield"
        target_field: The field name in target entity to set
        
    Example:
        borrow_from_address(entity, "@f65cf3bd-9392-499f-8f57-dba701f5069c.name", "student_name")
    """
    entity_id, field_path = ECSAddressParser.parse_address(address)
    
    # Get source entity
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

#### **2.2 Update existing code that uses borrow_from_address**

**Files to check and update**:
- `functional_api.py` - `create_entity_from_mapping()` function
- `callable_registry.py` - Any usage of `entity.borrow_from_address()`

**Update pattern**:
```python
# OLD:
entity.borrow_from_address(address, field_name)

# NEW:  
from .functional_api import borrow_from_address
borrow_from_address(entity, address, field_name)
```

### **Step 3: Verify Clean Architecture**

#### **3.1 Import Dependencies After Cleanup**

```python
# entity.py
# NO imports from other ECS modules ✅

# ecs_address_parser.py  
from .entity import EntityRegistry  ✅

# functional_api.py
from .entity import Entity, EntityRegistry  ✅
from .ecs_address_parser import ECSAddressParser, EntityReferenceResolver  ✅

# callable_registry.py
from .entity import Entity, EntityRegistry, build_entity_tree, find_modified_entities  ✅
from .ecs_address_parser import EntityReferenceResolver  ✅
from .functional_api import create_composite_entity, resolve_data_with_tracking  ✅
```

#### **3.2 No Circular Dependencies**
- entity.py → (no ECS imports)
- ecs_address_parser.py → entity.py only
- functional_api.py → entity.py + ecs_address_parser.py  
- callable_registry.py → all others

## **Step 4: Add Enhanced Features (Clean)**

### **4.1 Pattern Classification in ecs_address_parser.py**

```python
class InputPatternClassifier:
    """Classify input patterns for callable registry."""
    
    @classmethod
    def classify_kwargs(cls, kwargs: Dict[str, Any]) -> Tuple[str, Dict[str, str]]:
        """
        Classify input pattern types.
        
        Returns:
            Tuple of (pattern_type, field_classifications)
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
```

### **4.2 Enhanced Functional API**

```python
def create_composite_entity_with_pattern_detection(
    entity_class: Type[Entity], 
    field_mappings: Dict[str, Union[str, Any, Entity]], 
    register: bool = False
) -> Tuple[Entity, Dict[str, str]]:
    """Enhanced composite entity creation with pattern detection."""
    
    pattern_type, classification = InputPatternClassifier.classify_kwargs(field_mappings)
    
    # Handle mixed patterns
    if pattern_type == "mixed":
        # Special processing for mixed entity/address patterns
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
    
    # Use existing implementation for pure patterns
    entity = create_composite_entity(entity_class, field_mappings, register)
    return entity, classification
```

### **4.3 Enhanced Callable Registry**

```python
# In callable_registry.py
class CallableRegistry:
    @classmethod
    async def _execute_async(cls, func_name: str, **kwargs) -> Entity:
        """Execute function with enhanced pattern detection."""
        
        # Get function metadata
        metadata = cls.get_metadata(func_name)
        if not metadata:
            raise ValueError(f"Function '{func_name}' not registered")
        
        # Detect execution pattern using clean architecture
        pattern_type, classification = InputPatternClassifier.classify_kwargs(kwargs)
        
        # Route to appropriate execution strategy
        if pattern_type in ["pure_transactional", "mixed"]:
            return await cls._execute_transactional(metadata, kwargs, classification)
        else:
            return await cls._execute_borrowing(metadata, kwargs, classification)
```

## **Benefits of This Approach**

### **✅ Clean Architecture**
- No circular dependencies 
- Clear layered separation
- Each layer only imports from lower layers

### **✅ Maintainable Code**
- Entity core is pure and focused
- Address parsing isolated in utility layer
- Functional operations in service layer
- Application logic in top layer

### **✅ Enhanced Functionality**
- Pattern classification without circular imports
- Mixed pattern support
- Better error handling and validation
- Performance optimizations

### **✅ Follows Entity Tree Principles**
- Hierarchical, non-circular architecture
- Clear parent-child relationships between modules
- Lower levels don't depend on higher levels

## **Migration Checklist**

- [ ] Remove `ECSAddressParser` import from `entity.py`
- [ ] Remove `borrow_from_address()` method from `Entity` class
- [ ] Add `borrow_from_address()` function to `functional_api.py`
- [ ] Update all calls to use new function signature
- [ ] Add `InputPatternClassifier` to `ecs_address_parser.py`
- [ ] Add enhanced functions to `functional_api.py`
- [ ] Update `callable_registry.py` to use pattern classification
- [ ] Test all existing functionality still works
- [ ] Add tests for new enhanced features

## **Result: Clean, Hierarchical Architecture**

After this refactoring, the architecture will mirror the entity tree structure: clean, hierarchical, and without circular dependencies. Each layer will have a clear purpose and will only depend on layers below it, creating a solid foundation for building advanced features on top.