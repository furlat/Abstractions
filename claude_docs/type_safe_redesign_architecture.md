# Type-Safe Redesign Architecture

## Core Design Principle
**Every component in the entity pipeline MUST only deal with Entity objects. No raw data structures allowed.**

## New Architecture Components

### 1. PureEntityExtractor
**Responsibility**: Extract only Entity objects from any data structure
**Contract**: `Any → List[Entity]`

```python
class PureEntityExtractor:
    """Extract only Entity objects, ignore everything else."""
    
    @classmethod
    def extract_entities(cls, result: Any) -> List[Entity]:
        """
        Recursively find all Entity objects in any data structure.
        
        Returns:
            List[Entity]: All entities found, flattened
        """
        entities = []
        cls._recursive_extract(result, entities)
        return entities
    
    @classmethod
    def _recursive_extract(cls, obj: Any, entities: List[Entity]) -> None:
        """Recursively extract entities into the entities list."""
        if isinstance(obj, Entity):
            entities.append(obj)
        elif isinstance(obj, (list, tuple)):
            for item in obj:
                cls._recursive_extract(item, entities)
        elif isinstance(obj, dict):
            for value in obj.values():
                cls._recursive_extract(value, entities)
        # Ignore all non-Entity objects
```

### 2. DataWrapper
**Responsibility**: Wrap complete result structures in WrapperEntity
**Contract**: `Any → Entity`

```python
class DataWrapper:
    """Wrap any data structure in a WrapperEntity."""
    
    @classmethod
    def wrap_complete_result(cls, result: Any, execution_id: UUID) -> Entity:
        """
        Wrap the entire result structure in a WrapperEntity.
        
        This preserves the original structure while making it Entity-compatible.
        """
        wrapper_fields = {
            "wrapped_value": result,
            "original_type": str(type(result).__name__),
            "execution_id": str(execution_id),
            "wrapped_at": datetime.now(timezone.utc)
        }
        
        WrapperEntity = create_dynamic_entity_class(
            "WrapperEntity",
            wrapper_fields
        )
        
        return WrapperEntity()
```

### 3. StrategyAnalyzer
**Responsibility**: Determine unpacking strategy (pure strategy, no data processing)
**Contract**: `Any × bool → str`

```python
class StrategyAnalyzer:
    """Determine unpacking strategy without processing data."""
    
    @classmethod
    def determine_strategy(cls, result: Any, force_unpack: bool = False) -> str:
        """
        Determine strategy based only on type patterns.
        
        Returns:
            'unpack_entities': Unpack to individual entities
            'wrap_complete_result': Wrap entire result in single entity
        """
        # Pure tuple of entities - safe to unpack
        if isinstance(result, tuple) and all(isinstance(item, Entity) for item in result):
            return "unpack_entities"
        
        # Force unpack requested for entity containers
        if force_unpack:
            if isinstance(result, (list, dict)) and cls._contains_only_entities(result):
                return "unpack_entities"
        
        # Everything else gets wrapped
        return "wrap_complete_result"
    
    @classmethod
    def _contains_only_entities(cls, container: Any) -> bool:
        """Check if container contains only Entity objects."""
        if isinstance(container, list):
            return all(isinstance(item, Entity) for item in container)
        elif isinstance(container, dict):
            return all(isinstance(value, Entity) for value in container.values())
        return False
```

### 4. TypeSafeUnpacker
**Responsibility**: Orchestrate extraction/wrapping with guaranteed type safety
**Contract**: `Any × str × UUID → List[Entity]`

```python
class TypeSafeUnpacker:
    """Type-safe unpacker that always returns List[Entity]."""
    
    @classmethod
    def process(cls, result: Any, strategy: str, execution_id: UUID) -> List[Entity]:
        """
        Process result according to strategy.
        
        Returns:
            List[Entity]: Always returns entities, never raw data
        """
        if strategy == "unpack_entities":
            # Extract entities and return them individually
            entities = PureEntityExtractor.extract_entities(result)
            if not entities:
                # Fallback: wrap if no entities found
                wrapped = DataWrapper.wrap_complete_result(result, execution_id)
                return [wrapped]
            return entities
            
        elif strategy == "wrap_complete_result":
            # Wrap entire result in single entity
            wrapped = DataWrapper.wrap_complete_result(result, execution_id)
            return [wrapped]
            
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
```

## Integration with Existing System

### Backward-Compatible Integration Point

```python
# In entity_unpacker.py - replace the broken unpack_with_signature_analysis method
@classmethod
def unpack_with_signature_analysis(
    cls,
    result: Any,
    return_analysis_metadata: Dict[str, Any],
    output_entity_class: Optional[type] = None,
    execution_id: Optional[UUID] = None
) -> UnpackingResult:
    """Type-safe unpacking with guaranteed Entity output."""
    
    if execution_id is None:
        execution_id = uuid4()
    
    # Get force_unpack from registration metadata
    force_unpack = return_analysis_metadata.get('supports_unpacking', False)
    
    # Use type-safe strategy determination
    strategy = StrategyAnalyzer.determine_strategy(result, force_unpack)
    
    # Use type-safe processing (guaranteed List[Entity] output)
    entities = TypeSafeUnpacker.process(result, strategy, execution_id)
    
    # Build metadata for audit trail
    metadata = {
        **return_analysis_metadata,
        "execution_id": str(execution_id),
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        "force_unpack_effective": force_unpack,
        "strategy_used": strategy,
        "entity_count": len(entities),
        "type_safe": True
    }
    
    return UnpackingResult(
        primary_entities=entities,  # Guaranteed all Entity objects
        container_entity=None,      # No separate container needed
        metadata=metadata
    )
```

## Type Safety Guarantees

### 1. Contract Enforcement
- `PureEntityExtractor.extract_entities()` → `List[Entity]` (only Entity objects)
- `DataWrapper.wrap_complete_result()` → `Entity` (single Entity object)
- `TypeSafeUnpacker.process()` → `List[Entity]` (only Entity objects)

### 2. No Raw Data Leakage
- No dictionaries, lists, or primitives in entity pipelines
- Everything is either an Entity or wrapped in an Entity
- Type checking at every boundary

### 3. Defensive Integration
```python
# In callable_registry.py - fix unsafe assumptions
entity_ids = []
for entity in final_entities:
    if isinstance(entity, Entity):  # Defensive check
        entity_ids.append(entity.ecs_id)
    else:
        raise TypeError(f"Expected Entity, got {type(entity)}")
```

## Expected Results

### Current Failing Tests
1. **Test 4 (List[Tuple[Entity, Entity]])**:
   - Strategy: `wrap_complete_result`
   - Result: `[WrapperEntity(wrapped_value=[(assessment, recommendation)])]`
   - Type: `List[Entity]` ✅

2. **Test 6 (Non-entity float)**:
   - Strategy: `wrap_complete_result`
   - Result: `[WrapperEntity(wrapped_value=3.5)]`
   - Type: `List[Entity]` ✅

### All Tests Success Rate: 100% (6/6)

### Benefits
1. **No Type Errors**: Impossible to have raw data in entity pipelines
2. **Predictable Behavior**: Every result is guaranteed to be Entity objects
3. **Easier Debugging**: Type contract violations caught at boundaries
4. **Simpler Code**: No mixed-type handling throughout pipeline

## Implementation Plan

### Phase 1: Build New Components (No Breaking Changes)
1. Create `PureEntityExtractor` class
2. Create `DataWrapper` class  
3. Create `StrategyAnalyzer` class
4. Create `TypeSafeUnpacker` class
5. Test all components in isolation

### Phase 2: Safe Integration (Backward Compatible)
1. Replace `unpack_with_signature_analysis` implementation
2. Keep same external API signature
3. Add defensive type checking to unsafe areas
4. Test with current failing cases

### Phase 3: Validation (Confirm Success)
1. Run full test suite - expect 100% success rate
2. Validate no raw data in entity pipelines
3. Confirm type safety throughout

### Phase 4: Cleanup (Optional)
1. Remove old redundant code
2. Simplify now-unnecessary complexity
3. Update documentation

This architecture eliminates the root cause of the failures by design: **raw data can never enter the entity pipeline because everything is guaranteed to be wrapped in Entity objects**.