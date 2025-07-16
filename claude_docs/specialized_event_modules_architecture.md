# Specialized Event Modules Architecture

## Overview

This document specifies the new event module architecture that replaces the monolithic `typed_events.py` with specialized modules for each domain.

## Module Structure

### 1. `abstractions/events/entity_events.py`
**Purpose**: Entity-specific events for ECS operations
**Scope**: Entity lifecycle, tree operations, data operations

### 2. `abstractions/events/callable_events.py` 
**Purpose**: Callable registry-specific events
**Scope**: Function execution, strategy detection, result processing

### 3. `abstractions/events/events.py` (existing)
**Purpose**: Base event classes and event bus
**Scope**: Core event infrastructure, base classes

### 4. `abstractions/events/typed_events.py` (to be deleted)
**Purpose**: Temporary - will be removed after migration
**Status**: DELETE after migration complete

## Entity Events Module Design

### Base Event Classes to Import
```python
from abstractions.events.events import (
    ProcessingEvent, ProcessedEvent, 
    StateTransitionEvent, ModifyingEvent, ModifiedEvent
)
```

### Event Categories

#### 1. Entity Lifecycle Events
- `EntityRegistrationEvent` / `EntityRegisteredEvent`
- `EntityVersioningEvent` / `EntityVersionedEvent`

#### 2. Entity Tree Events  
- `TreeBuildingEvent` / `TreeBuiltEvent`
- `ChangeDetectionEvent` / `ChangesDetectedEvent`

#### 3. Entity State Transition Events
- `EntityPromotionEvent` / `EntityPromotedEvent`
- `EntityDetachmentEvent` / `EntityDetachedEvent`
- `EntityAttachmentEvent` / `EntityAttachedEvent`

#### 4. Entity Data Events
- `DataBorrowingEvent` / `DataBorrowedEvent`
- `IDUpdateEvent` / `IDUpdatedEvent`

### Event Field Design Principles

#### 1. Entity-Specific Fields
- `entity_type: str` - Class name for debugging
- `entity_id: UUID` - Entity identifier
- `is_root_entity: bool` - Root status

#### 2. Operation-Specific Fields
- `operation_type: str` - Specific operation being performed
- `operation_successful: bool` - Success status
- `operation_metadata: Dict[str, Any]` - Additional context

#### 3. Tree-Specific Fields
- `tree_node_count: int` - Number of nodes
- `tree_edge_count: int` - Number of edges
- `tree_max_depth: int` - Maximum tree depth

## Callable Events Module Design

### Event Categories

#### 1. Function Execution Events
- `FunctionExecutionEvent` / `FunctionExecutedEvent`
- `StrategyDetectionEvent` / `StrategyDetectedEvent`

#### 2. Input Processing Events
- `InputPreparationEvent` / `InputPreparedEvent`
- `SemanticAnalysisEvent` / `SemanticAnalyzedEvent`

#### 3. Output Processing Events
- `UnpackingEvent` / `UnpackedEvent`
- `ResultFinalizationEvent` / `ResultFinalizedEvent`

### Event Field Design Principles

#### 1. Function-Specific Fields
- `function_name: str` - Function being executed
- `execution_strategy: str` - Strategy used
- `execution_duration_ms: float` - Timing information

#### 2. Input/Output Fields
- `input_entity_count: int` - Number of input entities
- `output_entity_count: int` - Number of output entities
- `semantic_results: List[str]` - Semantic analysis results

## Implementation Strategy

### Phase 1: Create Entity Events Module
1. Create `entity_events.py` with entity-specific events
2. Import base events from `events.py`
3. Design entity-specific metadata fields
4. Create comprehensive event coverage for entity operations

### Phase 2: Create Callable Events Module
1. Create `callable_events.py` with callable registry-specific events
2. Design function execution metadata fields
3. Create events for all callable registry operations

### Phase 3: Update Imports
1. Update `entity.py` to import from `entity_events`
2. Update `callable_registry.py` to import from `callable_events`
3. Update `__init__.py` to export from specialized modules

### Phase 4: Remove Legacy Module
1. Verify all imports updated
2. Delete `typed_events.py`
3. Clean up any remaining references

## Benefits of This Architecture

### 1. Domain Separation
- Entity events are focused on entity operations
- Callable events are focused on function execution
- Clear separation of concerns

### 2. Reduced Complexity
- Smaller, focused modules
- Easier to understand and maintain
- Better IDE support and navigation

### 3. Scalability
- Easy to add new domains (e.g., `registry_events.py`)
- Each module can evolve independently
- Clear boundaries between event types

### 4. Better Type Safety
- More specific event types per domain
- Better autocomplete and validation
- Clearer event hierarchies

## Migration Path

### Step 1: Create entity_events.py
- Copy entity-specific events from typed_events.py
- Enhance with entity-specific metadata
- Test with entity.py integration

### Step 2: Create callable_events.py
- Copy callable-specific events from typed_events.py
- Enhance with callable-specific metadata
- Test with callable_registry.py integration

### Step 3: Update Imports
- Update all imports to use specialized modules
- Test that automatic nesting still works
- Verify no circular dependencies

### Step 4: Clean Up
- Delete typed_events.py
- Update documentation
- Final testing

This architecture provides better organization, clearer boundaries, and easier maintenance while preserving all existing functionality.