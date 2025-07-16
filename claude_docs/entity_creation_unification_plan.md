# Entity Creation Unification Plan

## 🎯 **Objective**
Consolidate 5+ different entity creation patterns into a single, unified factory method to eliminate code duplication and ensure consistent behavior across the entire codebase.

## 📊 **Current State Assessment**

### **Duplication Inventory**

| **File** | **Method** | **Lines** | **Usage Count** | **Risk Level** |
|----------|------------|-----------|-----------------|----------------|
| `callable_registry.py` | Direct `create_model()` | 211-233 | ~10 locations | 🟡 Medium |
| `entity.py` | `create_dynamic_entity_class()` | 2097-2127 | ~5 locations | 🟢 Low |
| `entity.py` | `ConfigEntity.create_config_entity_class()` | 2057-2094 | ~3 locations | 🟡 Medium |
| `entity_unpacker.py` | `_create_container_entity()` | 218-235 | ~3 locations | 🟢 Low |
| `entity_unpacker.py` | `_create_wrapper_entity()` | 259-275 | ~3 locations | 🟢 Low |
| `entity_unpacker.py` | `_create_nested_container_entity()` | 237-256 | ~2 locations | 🟢 Low |

### **Inconsistency Matrix**

| **Aspect** | **CallableRegistry** | **Entity** | **ConfigEntity** | **EntityUnpacker** |
|------------|---------------------|------------|------------------|-------------------|
| **Module Assignment** | `func.__module__` | `"__main__"` | `module_name` param | None |
| **Qualname Setting** | ✅ Set correctly | ❌ Not set | ✅ Set correctly | ❌ Not set |
| **Base Class** | `Entity` | `Entity` | `ConfigEntity` | `Entity` |
| **Field Validation** | ✅ Complex validation | ⚠️ Basic validation | ✅ Complex validation | ❌ Minimal validation |
| **Error Handling** | ✅ Detailed errors | ⚠️ Basic errors | ✅ Detailed errors | ❌ Poor errors |

## 🔧 **Unification Strategy**

### **Phase 1: Design Unified Factory**

#### **Target Architecture**
```python
class EntityFactory:
    """Unified factory for all entity class creation across the system."""
    
    @staticmethod
    def create_entity_class(
        class_name: str,
        field_definitions: Dict[str, Any],
        base_class: Type[Entity] = Entity,
        module_name: Optional[str] = None,
        purpose: str = "general",  # "function_io", "config", "container", "wrapper"
        execution_id: Optional[UUID] = None,  # For container entities
        qualname_parent: Optional[str] = None  # For nested class names
    ) -> Type[Entity]:
        """
        Unified entity class creation with consistent behavior.
        
        Args:
            class_name: Name for the dynamic class
            field_definitions: Dict mapping field names to (type, default) tuples  
            base_class: Base Entity class (Entity, ConfigEntity, etc.)
            module_name: Module name for the created class (auto-detected if None)
            purpose: Creation purpose for specialized handling
            execution_id: For container entities that need execution tracking
            qualname_parent: For nested qualname construction
            
        Returns:
            Dynamic Entity subclass with consistent metadata
            
        Raises:
            EntityCreationError: For validation failures
            TypeError: For invalid field definitions
        """
```

#### **Features of Unified Factory**
1. **Consistent Metadata**: Always sets module, qualname, and docstring
2. **Smart Defaults**: Auto-detects module from call stack when needed
3. **Validation**: Validates field definitions and base class compatibility
4. **Purpose-Aware**: Handles special cases (config, container, wrapper)
5. **Error Handling**: Uniform error types and messages
6. **Performance**: Caching for repeated class definitions

### **Phase 2: Implementation Plan**

#### **Step 1: Create Core Factory (Week 1)**

**Location**: `abstractions/ecs/entity.py` (add to existing file)

**Implementation Order**:
1. **Core factory method** with full validation
2. **Purpose-specific handlers** for different use cases
3. **Comprehensive error classes** 
4. **Field definition validation** utilities
5. **Module auto-detection** logic

**Key Components**:
```python
class EntityCreationError(Exception):
    """Base exception for entity creation failures."""
    pass

class FieldValidationError(EntityCreationError):
    """Raised when field definitions are invalid."""
    pass

class EntityFactory:
    _class_cache: Dict[str, Type[Entity]] = {}  # Performance caching
    
    @staticmethod
    def create_entity_class(...) -> Type[Entity]:
        # Implementation here
        
    @staticmethod
    def _validate_field_definitions(field_defs: Dict[str, Any]) -> None:
        # Validation logic
        
    @staticmethod
    def _detect_caller_module() -> str:
        # Auto-detect calling module
        
    @staticmethod
    def _build_qualname(class_name: str, parent: Optional[str]) -> str:
        # Construct proper qualname
```

#### **Step 2: Replace CallableRegistry Usage (Week 2)**

**Target Files**: `abstractions/ecs/callable_registry.py`

**Current Code** (lines 211-233):
```python
EntityClass = create_model(
    entity_class_name,
    __base__=Entity,
    __module__=func.__module__,
    **field_definitions
)
EntityClass.__qualname__ = f"{function_name}.{entity_class_name}"
```

**Replacement**:
```python
# EntityFactory is now in entity.py, so import from there
from abstractions.ecs.entity import EntityFactory

EntityClass = EntityFactory.create_entity_class(
    class_name=entity_class_name,
    field_definitions=field_definitions,
    base_class=Entity,
    module_name=func.__module__,
    purpose="function_io",
    qualname_parent=function_name
)
```

**Impact**: ~10 locations to update

#### **Step 3: Replace Entity.py Usage (Week 2)**

**Target Method**: `create_dynamic_entity_class()` (lines 2097-2127)

**Strategy**: 
1. **Keep existing method signature** for backwards compatibility
2. **Replace implementation** to use unified factory
3. **Add deprecation warning** for external usage
4. **Update internal usage** to use factory directly

**Implementation**:
```python
def create_dynamic_entity_class(class_name: str, field_definitions: Dict[str, Any]) -> Type[Entity]:
    """
    DEPRECATED: Use EntityFactory.create_entity_class() instead.
    
    This method is maintained for backwards compatibility.
    """
    import warnings
    warnings.warn(
        "create_dynamic_entity_class() is deprecated. Use EntityFactory.create_entity_class() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    from abstractions.ecs.entity import EntityFactory
    return EntityFactory.create_entity_class(
        class_name=class_name,
        field_definitions=field_definitions,
        purpose="general"
    )
```

#### **Step 4: Replace ConfigEntity Usage (Week 3)**

**Target Method**: `ConfigEntity.create_config_entity_class()` (lines 2057-2094)

**Strategy**:
1. **Replace implementation** to use unified factory with ConfigEntity base
2. **Maintain exact same interface** for compatibility
3. **Add enhanced validation** for config-specific patterns

**Implementation**:
```python
@classmethod
def create_config_entity_class(
    cls,
    class_name: str,
    field_definitions: Dict[str, Any],
    module_name: str = "__main__"
) -> Type['ConfigEntity']:
    """Enhanced config entity creation using unified factory."""
    
    from abstractions.ecs.entity import EntityFactory
    return EntityFactory.create_entity_class(
        class_name=class_name,
        field_definitions=field_definitions,
        base_class=cls,  # ConfigEntity
        module_name=module_name,
        purpose="config",
        qualname_parent="ConfigEntity"
    )
```

#### **Step 5: Replace EntityUnpacker Usage (Week 3)**

**Target Methods**: 
- `_create_container_entity()` (lines 218-235)
- `_create_wrapper_entity()` (lines 259-275)  
- `_create_nested_container_entity()` (lines 237-256)

**Strategy**:
1. **Replace all three methods** with unified factory calls
2. **Maintain execution_id tracking** for container entities
3. **Preserve purpose-specific metadata**

**Replacements**:
```python
@classmethod
def _create_container_entity(cls, non_entity_data: Dict[str, Any], container_metadata: Dict[str, Any], execution_id: UUID) -> Entity:
    """Create container entity using unified factory."""
    
    container_fields = {"data": (Dict[str, Any], non_entity_data)}
    container_fields.update(container_metadata)
    
    from abstractions.ecs.entity_factory import EntityFactory
    return EntityFactory.create_entity_class(
        class_name="ContainerEntity",
        field_definitions=container_fields,
        purpose="container",
        execution_id=execution_id
    )(**container_fields)
```

### **Phase 3: Testing & Validation (Week 4)**

#### **Testing Strategy**

**1. Unit Tests for EntityFactory**
- Field definition validation
- Module auto-detection
- Qualname construction
- Error handling
- Caching behavior
- Purpose-specific logic

**2. Integration Tests**
- CallableRegistry function creation
- Entity dynamic class creation
- ConfigEntity creation
- EntityUnpacker container creation
- Cross-file compatibility

**3. Backwards Compatibility Tests**
- Existing entity creation still works
- No behavioral changes for end users
- Deprecation warnings function correctly
- External API compatibility maintained

**4. Performance Tests**
- Class creation speed comparison
- Memory usage validation
- Caching effectiveness
- Large-scale entity creation

#### **Validation Checklist**

- [ ] All existing tests pass without modification
- [ ] New unified factory tests achieve 100% coverage
- [ ] No performance regression in entity creation
- [ ] Memory usage remains stable or improves
- [ ] All deprecation warnings function correctly
- [ ] External API compatibility verified
- [ ] Cross-file integration works seamlessly

### **Phase 4: Cleanup & Documentation (Week 5)**

#### **Code Cleanup**
1. **Remove duplicate implementations** after migration complete
2. **Clean up import statements** across all files
3. **Update type hints** to use unified factory types
4. **Standardize error handling** across all usage points

#### **Documentation Updates**
1. **Entity creation guide** using unified factory
2. **Migration guide** for external users
3. **API documentation** for all factory methods
4. **Best practices** for different entity purposes

#### **Final Validation**
1. **Full system test** with all features
2. **Performance benchmark** vs. original implementation
3. **Memory profiling** to ensure no leaks
4. **Integration test** with real workloads

## 📋 **Implementation Timeline**

| **Week** | **Phase** | **Deliverables** | **Risk Level** |
|----------|-----------|------------------|----------------|
| **Week 1** | Core Factory | `EntityFactory` class, validation, error handling | 🟢 Low |
| **Week 2** | CallableRegistry | Replace all `create_model()` usage | 🟡 Medium |
| **Week 2** | Entity.py | Replace `create_dynamic_entity_class()` | 🟢 Low |
| **Week 3** | ConfigEntity | Replace config entity creation | 🟡 Medium |
| **Week 3** | EntityUnpacker | Replace all container creation methods | 🟢 Low |
| **Week 4** | Testing | Comprehensive test suite, validation | 🟡 Medium |
| **Week 5** | Cleanup | Documentation, final cleanup | 🟢 Low |

## 🚨 **Risk Mitigation**

### **High-Risk Areas**
1. **CallableRegistry changes** - Core function creation logic
2. **ConfigEntity compatibility** - Existing config pattern usage
3. **Cross-file dependencies** - Import chain modifications

### **Mitigation Strategies**
1. **Incremental migration** - One file at a time
2. **Backwards compatibility** - Keep old methods during transition
3. **Comprehensive testing** - Test each migration step thoroughly
4. **Rollback plan** - Easy revert mechanism for each phase

### **Success Metrics**
- ✅ **Zero test failures** during migration
- ✅ **No performance regression** (< 5% slower acceptable)
- ✅ **Memory usage stable** or improved
- ✅ **All deprecation warnings** function correctly
- ✅ **External API compatibility** maintained

## 🎯 **Expected Benefits**

### **Immediate Benefits**
- **~50 lines of duplicate code eliminated**
- **Consistent entity creation behavior**
- **Unified error handling and validation**
- **Better debugging with proper qualnames**

### **Long-term Benefits**
- **Easier maintenance** - single point of change
- **Better type safety** - centralized validation
- **Performance improvements** - caching opportunities
- **Cleaner architecture** - single responsibility

### **Quality Improvements**
- **Consistent module handling** across all entity creation
- **Proper qualname setting** for all dynamic classes
- **Standardized error messages** and types
- **Better test coverage** of entity creation logic

This plan follows the exact same successful pattern we used for consolidating callable_registry.py issues, ensuring minimal risk and maximum benefit.