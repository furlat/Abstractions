# Callable Registry: Next Implementation Phases

## Executive Summary

This document outlines the detailed implementation plan for completing the callable registry system. Based on current progress analysis, we prioritize **Enhanced Input Pattern Support** before **Output Unpacking** to build a solid foundation.

**Current Status**: Core semantic detection and basic patterns are fully working. Ready to implement advanced input patterns and output handling.

## Phase 1: Enhanced Input Pattern Support (HIGH PRIORITY)

### Overview
Complete support for all 7 input patterns defined in the design document. This is foundational work that will make output unpacking much more robust.

### Current Gaps
- ❌ **Pattern A3**: Sub-entity direct reference: `execute("func", grade=student.record.grades[0])`
- ❌ **Pattern A4**: Entity reference via address: `execute("func", student="@uuid")`  
- ❌ **Pattern A5**: Sub-entity via address: `execute("func", grade="@uuid.record.grades.0")`
- ❌ **Pattern A7**: Complex mixed everything patterns

### Implementation Tasks

#### Task 1.1: Enhanced ECS Address Parser
**File**: `abstractions/ecs/ecs_address_parser.py`
**Goal**: Add support for entity-only addresses and sub-entity extraction

**Current Limitation**: 
```python
# Currently works:
"@uuid.field.subfield" → Resolves to field value

# Needs to work:
"@uuid" → Resolves to entire entity
"@uuid.record.grades.0" → Resolves to specific list item
"@uuid.courses.math_101" → Resolves to specific dict value
```

**Implementation**:
```python
class ECSAddressParser:
    @classmethod
    def resolve_address_advanced(cls, address: str) -> Tuple[Any, str]:
        """
        Enhanced address resolution supporting entity and sub-entity references.
        
        Returns:
            Tuple of (resolved_value, resolution_type)
            resolution_type: "entity" | "field_value" | "sub_entity"
        """
        entity_id, field_path = cls.parse_address(address)
        
        # Get root entity
        root_ecs_id = EntityRegistry.ecs_id_to_root_id.get(entity_id)
        if not root_ecs_id:
            raise ValueError(f"Entity {entity_id} not found in registry")
        
        entity = EntityRegistry.get_stored_entity(root_ecs_id, entity_id)
        if not entity:
            raise ValueError(f"Could not retrieve entity {entity_id}")
        
        # Case 1: No field path - return entire entity
        if not field_path:
            return entity, "entity"
        
        # Case 2: Navigate field path
        current_value = entity
        for field_part in field_path:
            if hasattr(current_value, field_part):
                current_value = getattr(current_value, field_part)
            else:
                # Try container navigation
                current_value = cls._navigate_container(current_value, field_part)
                if current_value is None:
                    raise ValueError(f"Cannot navigate to {field_part}")
        
        # Determine resolution type
        if isinstance(current_value, Entity):
            return current_value, "sub_entity"
        else:
            return current_value, "field_value"
    
    @classmethod
    def _navigate_container(cls, container, key_or_index: str) -> Any:
        """Navigate into containers using key or index."""
        # Handle list/tuple indices
        if key_or_index.isdigit() and isinstance(container, (list, tuple)):
            index = int(key_or_index)
            return container[index] if 0 <= index < len(container) else None
        
        # Handle dict keys
        elif isinstance(container, dict):
            return container.get(key_or_index)
        
        return None
    
    @classmethod
    def parse_address_flexible(cls, address: str) -> Tuple[UUID, List[str]]:
        """
        Parse address supporting entity-only format.
        
        Examples:
            "@uuid" → (uuid, [])
            "@uuid.field" → (uuid, ["field"])
            "@uuid.field.subfield" → (uuid, ["field", "subfield"])
        """
        if not isinstance(address, str) or not address.startswith('@'):
            raise ValueError(f"Invalid ECS address format: {address}")
        
        address_content = address[1:]  # Remove @
        
        # Split on first dot to separate UUID from field path
        parts = address_content.split('.', 1)
        
        try:
            entity_id = UUID(parts[0])
        except ValueError as e:
            raise ValueError(f"Invalid UUID in address {address}: {e}")
        
        # Field path (empty if no dots)
        field_path = parts[1].split('.') if len(parts) > 1 else []
        
        return entity_id, field_path
```

#### Task 1.2: Enhanced Input Pattern Classification
**File**: `abstractions/ecs/ecs_address_parser.py`
**Goal**: Extend `InputPatternClassifier` to handle all patterns

**Implementation**:
```python
class InputPatternClassifier:
    @classmethod
    def classify_kwargs_advanced(cls, kwargs: Dict[str, Any]) -> Tuple[str, Dict[str, Dict[str, Any]]]:
        """
        Advanced classification with detailed metadata.
        
        Returns:
            Tuple of (pattern_type, field_classifications)
            
        field_classifications format:
        {
            "field_name": {
                "type": "entity" | "entity_address" | "sub_entity" | "sub_entity_address" | "direct",
                "resolution_metadata": {...}
            }
        }
        """
        entity_count = 0
        address_count = 0
        sub_entity_count = 0
        direct_count = 0
        
        classification = {}
        
        for key, value in kwargs.items():
            if hasattr(value, 'ecs_id'):  # Duck typing for Entity
                if cls._is_sub_entity(value):
                    sub_entity_count += 1
                    classification[key] = {
                        "type": "sub_entity",
                        "resolution_metadata": {"root_ecs_id": value.root_ecs_id}
                    }
                else:
                    entity_count += 1
                    classification[key] = {
                        "type": "entity", 
                        "resolution_metadata": {"ecs_id": value.ecs_id}
                    }
            elif isinstance(value, str) and cls.is_ecs_address(value):
                try:
                    resolved_value, resolution_type = ECSAddressParser.resolve_address_advanced(value)
                    address_count += 1
                    
                    if resolution_type == "entity":
                        classification[key] = {
                            "type": "entity_address",
                            "resolution_metadata": {"address": value, "resolves_to": "entity"}
                        }
                    elif resolution_type == "sub_entity":
                        classification[key] = {
                            "type": "sub_entity_address", 
                            "resolution_metadata": {"address": value, "resolves_to": "sub_entity"}
                        }
                    else:
                        classification[key] = {
                            "type": "field_address",
                            "resolution_metadata": {"address": value, "resolves_to": "field_value"}
                        }
                except Exception as e:
                    # Fallback to basic address classification
                    classification[key] = {
                        "type": "address",
                        "resolution_metadata": {"address": value, "error": str(e)}
                    }
            else:
                direct_count += 1
                classification[key] = {
                    "type": "direct",
                    "resolution_metadata": {"value": value}
                }
        
        # Determine overall pattern type
        if entity_count > 0 and address_count == 0:
            pattern_type = "pure_transactional"
        elif address_count > 0 and entity_count == 0:
            pattern_type = "pure_borrowing"
        elif entity_count > 0 and address_count > 0:
            pattern_type = "mixed"
        elif sub_entity_count > 0:
            pattern_type = "sub_entity_transactional" 
        else:
            pattern_type = "direct"
        
        return pattern_type, classification
    
    @classmethod
    def _is_sub_entity(cls, entity: Any) -> bool:
        """Check if entity is a sub-entity (has root_ecs_id != ecs_id)."""
        if not hasattr(entity, 'ecs_id') or not hasattr(entity, 'root_ecs_id'):
            return False
        return entity.root_ecs_id is not None and entity.root_ecs_id != entity.ecs_id
```

#### Task 1.3: Enhanced Composite Input Creation
**File**: `abstractions/ecs/functional_api.py`
**Goal**: Update `create_composite_entity_with_pattern_detection` to handle all patterns

**Implementation**:
```python
def create_composite_entity_with_pattern_detection_advanced(
    entity_class: Type[Entity], 
    field_mappings: Dict[str, Union[str, Any, Entity]], 
    register: bool = False
) -> Tuple[Entity, Dict[str, Dict[str, Any]], List[Entity]]:
    """
    Advanced composite entity creation supporting all 7 input patterns.
    
    Returns:
        Tuple of (created_entity, classification_metadata, dependency_entities)
    """
    # Step 1: Advanced pattern classification
    pattern_type, classification = InputPatternClassifier.classify_kwargs_advanced(field_mappings)
    
    # Step 2: Resolve all references and collect dependencies
    resolved_mappings = {}
    dependency_entities = []
    
    for field_name, value in field_mappings.items():
        field_info = classification[field_name]
        field_type = field_info["type"]
        
        if field_type == "entity":
            # Direct entity reference
            resolved_mappings[field_name] = value
            dependency_entities.append(value)
            
        elif field_type == "entity_address":
            # Address that resolves to entire entity
            resolved_entity, _ = ECSAddressParser.resolve_address_advanced(value)
            resolved_mappings[field_name] = resolved_entity
            dependency_entities.append(resolved_entity)
            
        elif field_type == "sub_entity":
            # Direct sub-entity reference
            resolved_mappings[field_name] = value
            # Find root entity for dependency tracking
            if value.root_ecs_id:
                root_entity = EntityRegistry.get_live_entity_by_ecs_id(value.root_ecs_id)
                if root_entity:
                    dependency_entities.append(root_entity)
                    
        elif field_type == "sub_entity_address":
            # Address that resolves to sub-entity
            resolved_sub_entity, _ = ECSAddressParser.resolve_address_advanced(value)
            resolved_mappings[field_name] = resolved_sub_entity
            # Track root entity dependency
            if resolved_sub_entity.root_ecs_id:
                root_entity = EntityRegistry.get_live_entity_by_ecs_id(resolved_sub_entity.root_ecs_id)
                if root_entity:
                    dependency_entities.append(root_entity)
                    
        elif field_type == "field_address":
            # Address that resolves to field value
            resolved_value, _ = ECSAddressParser.resolve_address_advanced(value)
            resolved_mappings[field_name] = resolved_value
            # Track source entity
            entity_id, _ = ECSAddressParser.parse_address_flexible(value)
            root_ecs_id = EntityRegistry.ecs_id_to_root_id.get(entity_id)
            if root_ecs_id:
                source_entity = EntityRegistry.get_live_entity_by_ecs_id(root_ecs_id)
                if source_entity:
                    dependency_entities.append(source_entity)
        else:
            # Direct value
            resolved_mappings[field_name] = value
    
    # Step 3: Create entity with resolved data
    entity = entity_class(**resolved_mappings)
    
    # Step 4: Set up proper attribute sources
    for field_name, value in field_mappings.items():
        field_info = classification[field_name]
        if field_info["type"] in ["entity_address", "field_address", "sub_entity_address"]:
            # Parse to get source entity ID
            entity_id, _ = ECSAddressParser.parse_address_flexible(value)
            entity.attribute_source[field_name] = entity_id
        elif field_info["type"] in ["entity", "sub_entity"]:
            # Direct entity reference
            entity.attribute_source[field_name] = value.ecs_id
        else:
            # Direct value
            entity.attribute_source[field_name] = None
    
    # Step 5: Optionally register
    if register:
        entity.promote_to_root()
    
    return entity, classification, dependency_entities
```

#### Task 1.4: Update Callable Registry Integration
**File**: `abstractions/ecs/callable_registry.py`
**Goal**: Update `_create_input_entity_with_borrowing` to use advanced pattern detection

**Implementation**:
```python
@classmethod
async def _create_input_entity_with_borrowing_advanced(
    cls,
    input_entity_class: Type[Entity],
    kwargs: Dict[str, Any],
    classification: Optional[Dict[str, Dict[str, Any]]] = None
) -> Tuple[Entity, List[Entity]]:
    """
    Create input entity using advanced borrowing patterns supporting all 7 patterns.
    
    Returns:
        Tuple of (input_entity, dependency_entities)
    """
    if classification:
        # Use existing classification
        input_entity = create_composite_entity(
            entity_class=input_entity_class,
            field_mappings=kwargs,
            register=False
        )
        # TODO: Extract dependencies from classification
        dependency_entities = []
    else:
        # Use advanced pattern-aware creation
        input_entity, classification_metadata, dependency_entities = create_composite_entity_with_pattern_detection_advanced(
            entity_class=input_entity_class,
            field_mappings=kwargs,
            register=False
        )
    
    return input_entity, dependency_entities
```

### Success Criteria for Phase 1
1. **All 7 input patterns work**: A1-A7 from the design document
2. **Advanced address resolution**: `@uuid`, `@uuid.field.0`, `@uuid.dict.key` 
3. **Sub-entity handling**: Direct and via address sub-entity references
4. **Complete dependency tracking**: All source entities properly tracked
5. **Test coverage**: Comprehensive test suite for all patterns

---

## Phase 2: Output Analysis & Unpacking (MEDIUM PRIORITY)

### Overview
Implement sophisticated output handling including tuple unpacking, return type analysis, and multi-entity semantic detection.

### Current Gaps
- ❌ **Tuple Unpacking**: Multi-entity function returns
- ❌ **Return Type Analysis**: Sophisticated type signature parsing
- ❌ **Sibling Relationships**: Tracking entities created together
- ❌ **Mixed Output Handling**: Tuples with entities + non-entities

### Implementation Tasks

#### Task 2.1: Return Type Analysis System
**File**: `abstractions/ecs/callable_registry.py`
**Goal**: Analyze function return types to determine unpacking strategy

**Implementation**:
```python
from typing import get_type_hints, get_origin, get_args
from dataclasses import dataclass

@dataclass
class ReturnTypeInfo:
    """Analysis of function return type."""
    is_tuple: bool
    element_count: int
    element_types: List[Type]
    has_entities: bool
    has_non_entities: bool
    can_unpack: bool

class ReturnTypeAnalyzer:
    @classmethod
    def analyze_return_type(cls, func: Callable) -> ReturnTypeInfo:
        """Analyze function return type for unpacking strategy."""
        type_hints = get_type_hints(func)
        return_type = type_hints.get('return', Any)
        
        # Handle Tuple types
        if get_origin(return_type) is tuple:
            args = get_args(return_type)
            
            # Check if args contain entities
            has_entities = any(cls._is_entity_type(arg) for arg in args)
            has_non_entities = any(not cls._is_entity_type(arg) for arg in args)
            
            return ReturnTypeInfo(
                is_tuple=True,
                element_count=len(args),
                element_types=list(args),
                has_entities=has_entities,
                has_non_entities=has_non_entities,
                can_unpack=has_entities  # Only unpack if contains entities
            )
        
        # Handle single types
        is_entity = cls._is_entity_type(return_type)
        return ReturnTypeInfo(
            is_tuple=False,
            element_count=1,
            element_types=[return_type],
            has_entities=is_entity,
            has_non_entities=not is_entity,
            can_unpack=False
        )
    
    @classmethod
    def _is_entity_type(cls, type_hint: Type) -> bool:
        """Check if type hint represents an Entity or Entity subclass."""
        try:
            return isinstance(type_hint, type) and issubclass(type_hint, Entity)
        except TypeError:
            return False
```

#### Task 2.2: Output Unpacking Engine
**File**: `abstractions/ecs/callable_registry.py`
**Goal**: Handle tuple unpacking with semantic detection per entity

**Implementation**:
```python
@classmethod
async def _analyze_and_unpack_output(
    cls,
    result: Any,
    metadata: FunctionMetadata,
    object_identity_map: Dict[int, Entity],
    unpack_config: bool = True
) -> Tuple[List[Entity], List[Tuple[str, Optional[Entity]]]]:
    """
    Analyze output and optionally unpack tuples.
    
    Returns:
        Tuple of (output_entities, semantic_results)
        semantic_results: List of (semantic_type, original_entity)
    """
    # Analyze return type
    return_info = ReturnTypeAnalyzer.analyze_return_type(metadata.original_function)
    
    # Determine if we should unpack
    should_unpack = (
        unpack_config and 
        return_info.is_tuple and 
        return_info.can_unpack and
        isinstance(result, tuple)
    )
    
    if should_unpack:
        # Unpack tuple result
        output_entities = []
        semantic_results = []
        
        for i, item in enumerate(result):
            if isinstance(item, Entity):
                # Apply semantic detection to each entity
                semantic, original_entity = cls._detect_execution_semantic(item, object_identity_map)
                output_entities.append(item)
                semantic_results.append((semantic, original_entity))
            else:
                # Wrap non-entity in output entity
                item_entity = metadata.output_entity_class(**{f"item_{i}": item})
                output_entities.append(item_entity)
                semantic_results.append(("creation", None))
    else:
        # Single output handling
        if isinstance(result, Entity):
            semantic, original_entity = cls._detect_execution_semantic(result, object_identity_map)
            output_entities = [result]
            semantic_results = [(semantic, original_entity)]
        else:
            # Wrap non-entity result
            output_entity = metadata.output_entity_class(**{"result": result})
            output_entities = [output_entity]
            semantic_results = [("creation", None)]
    
    return output_entities, semantic_results

@classmethod
async def _finalize_unpacked_results(
    cls,
    output_entities: List[Entity],
    semantic_results: List[Tuple[str, Optional[Entity]]],
    metadata: FunctionMetadata
) -> List[Entity]:
    """
    Finalize unpacked results with proper semantic handling.
    """
    final_outputs = []
    
    for entity, (semantic, original_entity) in zip(output_entities, semantic_results):
        if semantic == "mutation":
            if original_entity:
                entity.update_ecs_ids()
                EntityRegistry.register_entity(entity)
                EntityRegistry.version_entity(original_entity)
            else:
                entity.promote_to_root()
                
        elif semantic == "creation":
            entity.promote_to_root()
            
        elif semantic == "detachment":
            entity.detach()
            if original_entity:
                EntityRegistry.version_entity(original_entity)
        
        final_outputs.append(entity)
    
    # Set up sibling relationships if multiple outputs
    if len(final_outputs) > 1:
        cls._setup_sibling_relationships(final_outputs, metadata.name)
    
    return final_outputs
```

#### Task 2.3: Sibling Relationship Tracking
**File**: `abstractions/ecs/entity.py`
**Goal**: Add fields for tracking entities created together

**Implementation**:
```python
# Add to Entity class:
class Entity(BaseModel):
    # ... existing fields ...
    
    # Function execution tracking (new fields)
    derived_from_function: Optional[str] = None
    derived_from_execution_id: Optional[UUID] = None
    function_input_entities: List[UUID] = Field(default_factory=list)
    execution_timestamp: Optional[datetime] = None
    
    # For unpacked multi-entity outputs
    sibling_output_entities: List[UUID] = Field(default_factory=list)
    output_index: Optional[int] = None

# Add to CallableRegistry:
@classmethod
def _setup_sibling_relationships(cls, outputs: List[Entity], function_name: str):
    """Set up sibling relationships for unpacked outputs."""
    if len(outputs) <= 1:
        return
    
    execution_id = uuid4()  # Generate execution ID
    output_ecs_ids = [e.ecs_id for e in outputs]
    
    for i, entity in enumerate(outputs):
        entity.derived_from_function = function_name
        entity.derived_from_execution_id = execution_id
        entity.output_index = i
        entity.execution_timestamp = datetime.now(timezone.utc)
        entity.sibling_output_entities = [
            ecs_id for j, ecs_id in enumerate(output_ecs_ids) if j != i
        ]
```

### Success Criteria for Phase 2
1. **Tuple unpacking works**: Multi-entity returns properly unpacked
2. **Return type analysis**: Sophisticated parsing of function signatures
3. **Semantic detection per entity**: Each output entity analyzed individually
4. **Sibling tracking**: Entities created together properly linked
5. **Configuration support**: Unpacking can be enabled/disabled per execution

---

## Phase 3: Enhanced Function Tracking (MEDIUM PRIORITY)

### Overview
Expand the `FunctionExecution` entity with complete audit trails, performance metrics, and bidirectional navigation.

### Implementation Tasks

#### Task 3.1: Enhanced FunctionExecution Entity
**File**: `abstractions/ecs/entity.py`

#### Task 3.2: Execution Performance Metrics
#### Task 3.3: Bidirectional Navigation System

---

## Phase 4: Advanced Features (LOWER PRIORITY)

### Overview
Implement advanced features like registry disconnection, parameter entities, and configuration systems.

### Implementation Tasks

#### Task 4.1: Registry Disconnection System
#### Task 4.2: Parameter Entity Pattern  
#### Task 4.3: Configurable Execution Settings

---

## Testing Strategy

### Phase 1 Testing
- **Pattern Coverage**: Test all 7 input patterns (A1-A7)
- **Address Resolution**: Test `@uuid`, `@uuid.field.0`, `@uuid.dict.key`
- **Sub-entity Handling**: Test direct and address-based sub-entity references
- **Error Handling**: Test invalid addresses and missing entities

### Phase 2 Testing
- **Tuple Unpacking**: Test multi-entity tuple returns
- **Mixed Tuples**: Test tuples with entities + non-entities
- **Sibling Relationships**: Test linking of unpacked entities
- **Configuration**: Test unpacking enable/disable

## Implementation Timeline

**Recommended Order**:
1. **Phase 1** (2-3 sessions): Enhanced Input Pattern Support
2. **Phase 2** (2-3 sessions): Output Analysis & Unpacking  
3. **Phase 3** (1-2 sessions): Enhanced Function Tracking
4. **Phase 4** (1-2 sessions): Advanced Features

**Total Estimated Time**: 6-10 development sessions

This prioritization ensures we build solid foundations before adding advanced features, making the system more robust and easier to test.