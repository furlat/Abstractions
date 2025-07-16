# Borrow Feature Implementation Plan: Entity Data Composition

## Overview

The `borrow_attribute_from()` method is the **foundational feature** for the callable registry system. It enables composing function input entities from sub-fields of other entities, providing the core data flow mechanism for entity-based function execution.

Based on the existing stub in `entity.py` (lines 1518-1525), this method follows established entity system patterns.

## Core Concept: Data Composition with Provenance

Instead of passing whole entities to functions, we compose inputs from specific fields across multiple entities:

```python
# Target pattern:
@CallableRegistry.register("analyze_performance")
def analyze_performance(name: str, age: int, grades: List[float]) -> AnalysisResult:
    # Function logic here
    return AnalysisResult(...)

# Usage with existing signature: borrow_attribute_from(source_entity, target_field, self_field)
input_entity = AnalyzePerformanceInputEntity()
input_entity.borrow_attribute_from(student_entity, "name", "name")
input_entity.borrow_attribute_from(student_entity, "age", "age") 
input_entity.borrow_attribute_from(academic_record_entity, "grades", "grades")

# Execute with complete provenance tracking
result = CallableRegistry.execute("analyze_performance", **input_entity.model_dump())
```

## Implementation Strategy

### Phase 1: Implement Core `borrow_attribute_from()` Method

**Location**: `abstractions/ecs/entity.py` - Entity class (replace existing stub lines 1518-1525)

**Existing Signature**: `def borrow_attribute_from(self, new_entity: "Entity", target_field: str, self_field: str) -> None:`

**Implementation following entity.py patterns**:

```python
def borrow_attribute_from(self, source_entity: "Entity", target_field: str, self_field: str) -> None:
    """
    Borrow an attribute from another entity and set it to the self field with provenance tracking.
    
    This method implements data composition by copying data from source_entity.target_field 
    to self.self_field, ensuring no in-place modifications and tracking provenance.
    
    Args:
        source_entity: The entity to borrow from  
        target_field: The field name in the source entity to borrow from
        self_field: The field name in this entity to set
        
    Raises:
        ValueError: If fields don't exist or type validation fails
    """
    # Step 1: Basic validation
    if self_field not in self.model_fields:
        raise ValueError(f"Field '{self_field}' does not exist in {self.__class__.__name__}")
    
    if not hasattr(source_entity, target_field):
        raise ValueError(f"Field '{target_field}' does not exist in {source_entity.__class__.__name__}")
    
    # Step 2: Get source value
    source_value = getattr(source_entity, target_field)
    
    # Step 3: Safe copying with container awareness (prevent in-place modification)
    import copy
    if isinstance(source_value, (list, dict, set, tuple)):
        # Deep copy containers to prevent modification of source
        borrowed_value = copy.deepcopy(source_value)
    elif isinstance(source_value, Entity):
        # For entities, reference them directly (don't copy)
        borrowed_value = source_value
    else:
        # For primitives, simple assignment is fine
        borrowed_value = source_value
    
    # Step 4: Set the value on this entity
    setattr(self, self_field, borrowed_value)
    
    # Step 5: Update attribute_source for provenance tracking
    if isinstance(borrowed_value, list):
        # For lists, create a source list pointing to source entity
        self.attribute_source[self_field] = [source_entity.ecs_id] * len(borrowed_value)
    elif isinstance(borrowed_value, dict):
        # For dicts, create a source dict pointing to source entity  
        self.attribute_source[self_field] = {
            str(k): source_entity.ecs_id for k in borrowed_value.keys()
        }
    else:
        # For simple fields and entities, point to source entity
        self.attribute_source[self_field] = source_entity.ecs_id
```

### Phase 2: String-Based Entity Addressing

**Location**: `abstractions/ecs/ecs_address_parser.py` (new file)

**Goal**: Parse `@uuid.field` syntax for entity references

```python
import re
from typing import Tuple, List, Optional, Any
from uuid import UUID

class ECSAddressParser:
    """Parser for ECS entity address strings in @uuid.field.subfield format."""
    
    # Pattern: @uuid.field.subfield.etc
    ADDRESS_PATTERN = re.compile(r'^@([a-f0-9\-]{36})\.(.+)$')
    
    @classmethod
    def parse_address(cls, address: str) -> Tuple[UUID, List[str]]:
        """
        Parse an ECS address string into entity ID and field path.
        
        Args:
            address: String like "@uuid.field.subfield"
            
        Returns:
            Tuple of (entity_ecs_id, field_path_list)
            
        Raises:
            ValueError: If address format is invalid
        """
        if not isinstance(address, str) or not address.startswith('@'):
            raise ValueError(f"Invalid ECS address format: {address}")
        
        match = cls.ADDRESS_PATTERN.match(address)
        if not match:
            raise ValueError(f"Invalid ECS address format: {address}")
        
        uuid_str, field_path = match.groups()
        
        try:
            entity_id = UUID(uuid_str)
        except ValueError as e:
            raise ValueError(f"Invalid UUID in address {address}: {e}")
        
        # Split field path on dots
        field_parts = field_path.split('.')
        
        return entity_id, field_parts
    
    @classmethod
    def resolve_address(cls, address: str) -> Any:
        """
        Resolve an ECS address to the actual value.
        
        Args:
            address: String like "@uuid.field.subfield"
            
        Returns:
            The resolved value
            
        Raises:
            ValueError: If entity not found or field access fails
        """
        from .entity import EntityRegistry
        import functools
        
        entity_id, field_path = cls.parse_address(address)
        
        # Get entity from registry
        root_ecs_id = EntityRegistry.ecs_id_to_root_id.get(entity_id)
        if not root_ecs_id:
            raise ValueError(f"Entity {entity_id} not found in registry")
        
        entity = EntityRegistry.get_stored_entity(root_ecs_id, entity_id)
        if not entity:
            raise ValueError(f"Could not retrieve entity {entity_id}")
        
        # Navigate field path
        try:
            return functools.reduce(getattr, field_path, entity)
        except AttributeError as e:
            raise ValueError(f"Field path '{'.'.join(field_path)}' not found in entity: {e}")
    
    @classmethod
    def is_ecs_address(cls, value: str) -> bool:
        """Check if a string is an ECS address."""
        return isinstance(value, str) and value.startswith('@') and bool(cls.ADDRESS_PATTERN.match(value))
```

### Phase 3: Enhanced Entity Reference Resolver

**Location**: `abstractions/ecs/entity.py` - Enhanced methods

**Goal**: Integrate borrowing with string address resolution

```python
def borrow_from_address(self, address: str, target_field: str) -> None:
    """
    Borrow an attribute using ECS address string syntax.
    
    Args:
        address: ECS address like "@uuid.field.subfield"
        target_field: The field name in this entity to set
    """
    from .ecs_address_parser import ECSAddressParser
    
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
    
    # Use existing borrow_attribute_from method
    self.borrow_attribute_from(source_entity, source_field, target_field)
    
    # TODO: Support nested field paths like "record.gpa"

@classmethod
def create_from_address_dict(cls, address_mapping: Dict[str, str]) -> "Entity":
    """
    Factory method to create entity by borrowing from multiple addresses.
    
    Args:
        address_mapping: Dict mapping target fields to ECS addresses
        
    Example:
        Student.create_from_address_dict({
            "name": "@student_uuid.name",
            "age": "@student_uuid.age", 
            "gpa": "@record_uuid.gpa"
        })
    """
    instance = cls()
    
    for target_field, address in address_mapping.items():
        instance.borrow_from_address(address, target_field)
    
    return instance
```

### Phase 4: Functional get/put Methods

**Location**: `abstractions/ecs/functional_api.py` (new file)

**Goal**: High-level functional API for entity data access

```python
from typing import Any, Dict, List, Optional
from .entity import Entity, EntityRegistry
from .ecs_address_parser import ECSAddressParser

def get(address: str) -> Any:
    """
    Functional API to get a value from an entity using ECS address.
    
    Args:
        address: ECS address like "@uuid.field.subfield"
        
    Returns:
        The resolved value
    """
    return ECSAddressParser.resolve_address(address)

def put(address: str, value: Any, borrow: bool = True) -> None:
    """
    Functional API to set a value in an entity using ECS address.
    
    Args:
        address: ECS address like "@uuid.field"
        value: Value to set
        borrow: If True, create borrowing relationship for entity values
    """
    entity_id, field_path = ECSAddressParser.parse_address(address)
    
    # Get entity from registry  
    root_ecs_id = EntityRegistry.ecs_id_to_root_id.get(entity_id)
    if not root_ecs_id:
        raise ValueError(f"Entity {entity_id} not found in registry")
    
    entity = EntityRegistry.get_live_entity_by_ecs_id(entity_id)  # Get live version for modification
    if not entity:
        raise ValueError(f"Could not retrieve live entity {entity_id}")
    
    # For now, support only single field (first in path)
    field_name = field_path[0]
    
    if borrow and isinstance(value, Entity):
        # Create borrowing relationship
        entity.borrow_attribute_from(value, field_name, field_name)
    else:
        # Direct assignment
        setattr(entity, field_name, value)
        
        # Update attribute_source for provenance
        if isinstance(value, Entity):
            entity.attribute_source[field_name] = value.ecs_id
        else:
            entity.attribute_source[field_name] = None  # New data

def create_entity_from_mapping(entity_class: type, mapping: Dict[str, Any]) -> Entity:
    """
    Factory to create entity from mixed value/address mapping.
    
    Args:
        entity_class: Entity class to create
        mapping: Dict with field names and values/addresses
        
    Example:
        create_entity_from_mapping(AnalysisInputEntity, {
            "name": "@student_uuid.name",
            "age": "@student_uuid.age",
            "threshold": 85.0  # Direct value
        })
    """
    instance = entity_class()
    
    for field_name, value in mapping.items():
        if isinstance(value, str) and ECSAddressParser.is_ecs_address(value):
            # Borrow from address
            instance.borrow_from_address(value, field_name)
        else:
            # Direct assignment
            setattr(instance, field_name, value)
            instance.attribute_source[field_name] = None  # New data
    
    return instance
```

## Integration with Base ECS Example

### Demonstration Scenario

Using the validated academic system from `base_ecs_example.py`:

```python
# After running base_ecs_example.py, we have:
# - university with alice, bob, charlie students
# - academic records with grades

# Create analysis input by borrowing from multiple entities
analysis_input = AnalysisInputEntity()
analysis_input.borrow_attribute_from(alice, "name", "student_name")
analysis_input.borrow_attribute_from(alice, "age", "student_age")
analysis_input.borrow_attribute_from(alice_record, "gpa", "current_gpa")

# String-based approach (Phase 2)
analysis_input_2 = AnalysisInputEntity.create_from_address_dict({
    "student_name": f"@{alice.ecs_id}.name",
    "student_age": f"@{alice.ecs_id}.age", 
    "current_gpa": f"@{alice_record.ecs_id}.gpa"
})

# Functional API approach (Phase 4)
analysis_input_3 = create_entity_from_mapping(AnalysisInputEntity, {
    "student_name": f"@{alice.ecs_id}.name",
    "student_age": f"@{alice.ecs_id}.age",
    "current_gpa": f"@{alice_record.ecs_id}.gpa",
    "threshold": 3.5  # Direct value
})
```

## Testing Strategy

### Phase 1 Tests: Core borrow_attribute_from()
- Type validation (compatible/incompatible types)
- Container copying (lists, dicts, sets, tuples)
- Entity reference handling
- Attribute source tracking
- Error conditions

### Phase 2 Tests: String Address Parsing
- Valid/invalid address formats
- UUID parsing
- Field path handling
- Entity resolution
- Error conditions

### Phase 3 Tests: Integration
- Borrowing via addresses
- Factory methods
- Mixed value/address scenarios
- Provenance preservation

### Phase 4 Tests: Functional API
- get/put operations
- Entity creation from mappings
- Performance characteristics
- Error handling

## Success Metrics

1. **✅ Type Safety**: All borrowed values pass Pydantic validation
2. **✅ Immutability**: Source entities unmodified after borrowing
3. **✅ Provenance**: Complete `attribute_source` tracking
4. **✅ Performance**: Minimal overhead for borrowing operations
5. **✅ Integration**: Seamless callable registry integration

This borrow feature implementation provides the **foundational data composition capability** needed for the callable registry system, enabling flexible and traceable entity-based function execution.