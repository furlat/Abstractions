# Docstring and Reference Consistency Fixes

## Overview
After implementing EntityFactory consolidation and method renaming, several references and docstrings need to be updated to reflect the current architecture.

## Issues Found and Required Fixes

### 1. CRITICAL: References to Removed Functions

#### 1.1 callable_registry.py - `create_entity_from_function_signature` References
**Status**: BROKEN - Function was removed but still referenced

**Locations**:
- Line 55: `input_model = create_entity_from_function_signature(func, "Input", function_name)`
- Line 90: `output_model = create_entity_from_function_signature(func, "Output", function_name)`
- Line 151: Function definition that was removed
- Line 157: Docstring describing the removed function

**Fix Required**:
```python
# OLD (BROKEN):
input_model = create_entity_from_function_signature(func, "Input", function_name)

# NEW (CORRECT):
input_model = EntityFactory.create_entity_class(...)  # Use EntityFactory pattern
```

**Impact**: High - These calls will cause runtime errors

### 2. Outdated "Enhanced" Method References

#### 2.1 entity_unpacker.py - Method Name Mismatches
**Status**: BROKEN - Methods were renamed but calls not updated

**Locations**:
- Line 374: `cls._handle_single_entity_enhanced()`
- Line 377: `cls._handle_sequence_unpack_enhanced()`
- Line 380: `cls._handle_dict_unpack_enhanced()`
- Line 383: `cls._handle_mixed_unpack_enhanced()`
- Line 386: `cls._handle_nested_unpack_enhanced()`
- Line 389: `cls._handle_non_entity_enhanced()`

**Current Method Names** (renamed in earlier work):
- `_handle_single_entity_enhanced` → `_handle_single_entity`
- `_handle_sequence_unpack_enhanced` → `_handle_sequence_unpack`
- `_handle_dict_unpack_enhanced` → `_handle_dict_unpack`
- `_handle_mixed_unpack_enhanced` → `_handle_mixed_unpack`
- `_handle_nested_unpack_enhanced` → `_handle_nested_unpack`
- `_handle_non_entity_enhanced` → `_handle_non_entity`

**Fix Required**: Remove `_enhanced` suffix from all method calls

**Impact**: High - These calls will cause AttributeError at runtime

### 3. Outdated Documentation References

#### 3.1 callable_registry.py - "Enhanced" Documentation
**Status**: INCONSISTENT - Documentation refers to old "enhanced" terminology

**Locations**:
- Line 82: `"""Cache output signature → output entity model + enhanced return analysis."""`
- Line 312: `# ✅ ENHANCED: Use enhanced signature caching with Phase 2 analysis`
- Line 328: `# Store enhanced metadata`
- Line 346: `print(f"✅ Registered '{name}' with enhanced return analysis...")`
- Line 370: `Create input entity using enhanced borrowing patterns.`
- Line 444: `"""Execute function with enhanced strategy detection."""`
- Line 698: `# Create input entity with borrowing (enhanced pattern)`
- Line 743: `# Use enhanced result processing for multi-entity returns`
- Line 769: `This implements the enhanced pattern with object identity-based semantic analysis:`
- Line 1138: `execution_record.execution_pattern = "enhanced_unified"`
- Line 1145: `execution_record.mark_as_completed("enhanced_execution")`

**Fix Required**: Replace "enhanced" terminology with semantic descriptors:
- "enhanced return analysis" → "comprehensive return analysis"
- "enhanced signature caching" → "signature caching with return analysis"
- "enhanced borrowing patterns" → "entity borrowing patterns"
- "enhanced strategy detection" → "strategy detection"
- "enhanced pattern" → "unified execution pattern"
- "enhanced_unified" → "unified_execution"
- "enhanced_execution" → "semantic_execution"

**Impact**: Medium - Documentation clarity and consistency

#### 3.2 entity.py - Outdated create_model References
**Status**: INCONSISTENT - Comments refer to old patterns

**Locations**:
- Line 16: `from pydantic import create_model` (still imported but now only used by EntityFactory)
- Line 2024: `Consolidates duplicate create_model() patterns...` (comment about EntityFactory)

**Fix Required**:
- Line 16: Keep import (EntityFactory still uses it internally)
- Line 2024: Update comment to reflect that EntityFactory encapsulates create_model usage

**Impact**: Low - Documentation clarity

### 4. Method Names in Documentation

#### 4.1 return_type_analyzer.py - Acceptable "Enhanced" Reference
**Status**: ACCEPTABLE - This is future improvement documentation

**Location**:
- Line 344: `This could be enhanced to be more sophisticated based on structure analysis`

**Fix Required**: None - This is appropriate future improvement language

**Impact**: None

## Implementation Plan

### Phase 1: Critical Runtime Fixes (HIGH PRIORITY)
1. **Fix callable_registry.py function calls**:
   - Replace `create_entity_from_function_signature` calls with EntityFactory patterns
   - Update function signature caching to use EntityFactory

2. **Fix entity_unpacker.py method calls**:
   - Remove `_enhanced` suffix from all method calls in lines 374-389

### Phase 2: Documentation Consistency (MEDIUM PRIORITY)  
3. **Update callable_registry.py documentation**:
   - Replace all "enhanced" terminology with semantic equivalents
   - Update docstrings to reflect current architecture

4. **Clean up entity.py comments**:
   - Update EntityFactory documentation to reflect encapsulation

### Phase 3: Verification (LOW PRIORITY)
5. **Search for remaining inconsistencies**:
   - Verify no other "enhanced" references exist
   - Verify all method calls are consistent
   - Test that all changes work correctly

## Expected Files Modified
- `abstractions/ecs/callable_registry.py` (critical fixes + documentation)
- `abstractions/ecs/entity_unpacker.py` (critical method name fixes)  
- `abstractions/ecs/entity.py` (minor documentation updates)

## Risk Assessment
- **High Risk**: callable_registry.py and entity_unpacker.py have runtime-breaking issues
- **Medium Risk**: Documentation inconsistencies may confuse future developers
- **Low Risk**: Minor documentation cleanup

## Success Criteria
1. All code executes without AttributeError or NameError
2. No references to removed functions
3. Consistent terminology throughout codebase
4. Method names match their definitions
5. Documentation accurately reflects current architecture