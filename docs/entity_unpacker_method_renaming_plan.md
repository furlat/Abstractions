# Entity Unpacker Method Renaming Plan

## Problem Statement
The `entity_unpacker.py` file contains methods with "_enhanced" suffixes that need to be renamed to remove unprofessional naming conventions. Both method definitions and method calls need to be updated consistently.

## Current State Analysis

### Method Definitions (that need renaming):
- `_handle_single_entity_enhanced` (line 396) → `_handle_single_entity_with_metadata`
- `_handle_sequence_unpack_enhanced` (line 414) → `_handle_sequence_unpack_with_metadata`  
- `_handle_dict_unpack_enhanced` (line 441) → `_handle_dict_unpack_with_metadata`
- `_handle_mixed_unpack_enhanced` (line 469) → `_handle_mixed_unpack_with_metadata`
- `_handle_nested_unpack_enhanced` (line 500) → `_handle_nested_unpack_with_metadata`
- `_handle_non_entity_enhanced` (line 528) → `_handle_non_entity_with_metadata`

### Method Calls (that reference the old names):
- Line 374: `cls._handle_single_entity_enhanced(...)`
- Line 377: `cls._handle_sequence_unpack_enhanced(...)`
- Line 380: `cls._handle_dict_unpack_enhanced(...)`
- Line 383: `cls._handle_mixed_unpack_enhanced(...)`
- Line 386: `cls._handle_nested_unpack_enhanced(...)`
- Line 389: `cls._handle_non_entity_enhanced(...)`

## Execution Plan

### Step 1: Rename Method Definitions
Update each method definition to use semantic names instead of "_enhanced":

1. `_handle_single_entity_enhanced` → `_handle_single_entity_with_metadata`
2. `_handle_sequence_unpack_enhanced` → `_handle_sequence_unpack_with_metadata`
3. `_handle_dict_unpack_enhanced` → `_handle_dict_unpack_with_metadata`  
4. `_handle_mixed_unpack_enhanced` → `_handle_mixed_unpack_with_metadata`
5. `_handle_nested_unpack_enhanced` → `_handle_nested_unpack_with_metadata`
6. `_handle_non_entity_enhanced` → `_handle_non_entity_with_metadata`

### Step 2: Update Method Calls
Update all method calls in lines 374-389 to use the new method names.

### Step 3: Verify Consistency
Ensure no references to old "_enhanced" method names remain anywhere in the codebase.

## Naming Rationale
- `_with_metadata` suffix indicates these methods provide enhanced functionality through comprehensive metadata tracking
- Removes unprofessional "_enhanced" terminology 
- Maintains semantic clarity about what makes these methods different from base versions

## Risk Assessment
- **Low Risk**: This is purely internal refactoring with no external API changes
- **Isolated Impact**: Only affects `entity_unpacker.py` 
- **Easy Rollback**: Simple search-and-replace operation if issues arise

## Success Criteria
1. All method definitions use semantic names without "_enhanced"
2. All method calls reference the correct renamed methods
3. No pylance errors or broken references
4. Code functions identically to before (pure refactoring)