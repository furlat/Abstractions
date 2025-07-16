# RFC-XXXX: Abstractions: A Typed Entity Storage System for LLM Agents

- **RFC Number**: XXXX
- **Title**: Abstractions: A Fully Traced, Typed, and Persistent Entity Storage for LLM Agents
- **Author**: Tommaso Furlanello
- **Created**: 2025-04-22
- **Status**: Draft

## Summary

Abstractions is a Python library that provides a fully versioned hierarchical entity storage connected to an asynchronous sandboxed function calling engine. At the core of the project is an optimized `Entity` class built on Pydantic, specifically constructed to manage deeply nested object models. Entities in our system have all the functionalities of Pydantic BaseModels but additionally track relationships between sub-entities through a typed hierarchical tree representation.

This secondary tree view enables greedy diffing of Entities, allowing for pervasive versioning of any entity that gets processed by our function calling engine. The system automatically creates immutable snapshots whenever modifications are detected, maintaining a complete history of all entity transformations without requiring explicit version management by developers.

## Motivation

Modern LLM agents frequently need to maintain, modify, and reason about complex hierarchies of structured data. Current approaches to entity management in agent systems face several key limitations:

1. **No Automatic Versioning**: Developers must manually manage versions of objects as they change, leading to inconsistencies and lost history.

2. **Fragmented Object Relationships**: Standard object models don't track the relationships between nested objects, making it difficult to understand how data elements relate to each other.

3. **Inconsistent Mutation**: Without a standardized approach to object modification, it's difficult to maintain a clean lineage of changes.

4. **Poor Integration with Function Calling**: There's often a disconnect between data models and the functions that process them, leading to error-prone code and difficulty tracing the provenance of data transformations.

5. **Limited Diffing Capabilities**: Most systems lack efficient mechanisms to detect exactly what changed within deeply nested object structures.

Abstractions addresses these shortcomings by providing a unified system that automatically tracks entity relationships, versions objects based on changes, and integrates seamlessly with a sandboxed function calling engine.

## Detailed Proposal

### Core Components

The Abstractions system consists of three primary components:

1. **Entity System**: A Pydantic-based entity framework with built-in versioning and relationship tracking ✅
2. **Entity Registry**: A global versioned storage system for entities ✅
3. **Callable Registry**: A function registry with execution sandboxing and entity tracing ✅

#### 1. Entity System

The entity system provides an `Entity` base class that extends Pydantic's `BaseModel` with:

- Unique identity via `ecs_id` (persistent) and `live_id` (runtime) ✅
- Lineage tracking via `lineage_id` and history references ✅
- Hierarchical relationship tracking through tree representation ✅
- Automatic diffing and versioning when entities are modified ✅

Key classes include:
- `Entity`: The base class for all versioned objects ✅
- `EntityTree`: The relationship graph for tracking entity hierarchies ✅
- `EntityEdge`: Represents relationships between entities ✅

```python
class Entity(BaseModel):
    ecs_id: UUID = Field(default_factory=uuid4, description="Unique persistent identifier")
    live_id: UUID = Field(default_factory=uuid4, description="Runtime identifier")
    lineage_id: UUID = Field(default_factory=uuid4, description="Lineage tracking ID")
    root_ecs_id: Optional[UUID] = Field(default=None, description="Root entity reference")
    root_live_id: Optional[UUID] = Field(default=None, description="Live root reference")
    # Additional fields for version tracking...
```

#### 2. Entity Registry

The `EntityRegistry` provides:

- Global access to versioned entities ✅
- Storage indexed by multiple keys (root entity, lineage, type) ✅
- Automatic versioning of modified entities ✅
- Tree-based diffing to detect changes efficiently ✅
- In-memory snapshot storage with potential for persistence ✅

```python
class EntityRegistry():
    """A registry for entities, maintaining a versioned collection of all entities in the system"""
    tree_registry: Dict[UUID, EntityTree]
    lineage_registry: Dict[UUID, List[UUID]]
    live_id_registry: Dict[UUID, Entity]
    type_registry: Dict[Type[Entity], List[UUID]]
```

#### 3. Callable Registry

The `CallableRegistry` provides:

- Registration of typed functions with input/output schemas ✅
- Execution sandboxing for functions ❓
- Automatic entity tracing and versioning ❓
- Asynchronous execution capabilities ✅

```python
class CallableRegistry(BaseRegistry[Callable]):
    """Global registry for callable functions with entity tracing"""
    _registry: Dict[str, Callable]
    
    @classmethod
    def register(cls, name: str, func: Callable) -> None:
        """Register a new callable with validation and automatic entity tracing"""
```

### Key Features

#### Entity References in Function Arguments

Functions registered in the `CallableRegistry` can accept references to entities or their specific fields using a special syntax:

```json
{
  "student_age": "@f65cf3bd-9392-499f-8f57-dba701f5069c.age",
  "bonus_amount": 100.5
}
```

The system will:
1. Parse the reference ❓
2. Fetch the entity ❓
3. Extract the referenced field value ❓
4. Replace the reference with the actual value ❓
5. Validate the input with Pydantic ✅

#### Automatic Entity Tracing

All functions registered in the `CallableRegistry` are automatically wrapped with entity tracing functionality that:

1. Checks if entity arguments have changed from their stored versions ❓
2. Forks changed entities with new IDs ✅
3. Executes the function ✅
4. Checks for changes after execution ❓
5. Automatically registers new or modified entities ✅

#### Isolated Function Execution

Functions can be executed in isolated environments with:

1. No access to the global registry state ❓
2. Type enforcement on inputs and outputs ✅
3. Automatic versioning of entities that cross the execution boundary ❓
4. Clean entity lineage tracking ✅

### Diffing and Versioning Approach

One of the key innovations in Abstractions is its approach to entity diffing:

1. **Tree-Based Structure**: Entities maintain a hierarchical tree representation that mirrors their object relationships ✅
2. **Greedy Diffing**: When checking for changes, the system performs a greedy diff that walks the tree ✅
3. **Path-Based Updates**: Changed entities are tracked along with their full path from the root ✅
4. **Automatic Versioning**: When changes are detected, the system automatically creates new versions of affected entities ✅

The diffing algorithm efficiently identifies:
- Added entities ✅
- Removed entities ✅
- Modified attributes ✅
- Structural changes (moved entities within the hierarchy) ✅

### Entity Tree Implementation

The `EntityTree` class maintains:

- A complete collection of entity nodes ✅
- Edge relationships between entities ✅
- Ancestry paths from each entity to the root ✅
- Root entity information ✅

This enables:
- Efficient traversal of entity relationships ✅
- Path-based diffing for detecting changes ✅
- Hierarchical ancestry tracking ✅
- Support for complex nested structures ✅

## Rationale and Alternatives

### Why This Approach?

We've chosen this approach for several key reasons:

1. **Built on Pydantic**: By extending Pydantic, we leverage its robust validation, serialization, and schema generation while adding versioning and relationship tracking.

2. **Automatic Versioning**: Automatic detection and versioning of changes means developers don't need to think about version management—it just works.

3. **Hierarchical Representation**: The explicit tree representation enables efficient diffing and relationship tracking that wouldn't be possible with standard object models.

4. **Function Integration**: The tight integration between entities and functions creates a complete system for tracking data transformations.

5. **Immutable Versioning**: By creating new versions rather than modifying existing ones, we maintain a complete history without complexity.

### Alternatives Considered



### Design Decisions


## Impact and Trade-offs

### Positive Impacts

1. **Simplified Development**: Developers can focus on the business logic rather than version management.

2. **Complete History**: All entity changes are automatically tracked, providing a complete audit trail.

3. **Type Safety**: Integration with Pydantic ensures type safety throughout the system.

4. **Robust Relationships**: Explicit relationship tracking improves understanding of data structures.

5. **Clean Function Integration**: Seamless integration with callable functions creates a unified system.

### Trade-offs

1. **Memory Usage**: Maintaining multiple versions of entities increases memory usage compared to in-place updates.

2. **Learning Curve**: The system introduces new concepts (like the distinction between `ecs_id` and `live_id`) that developers need to understand.



### Compatibility



## Unresolved Questions

1. **Persistence Strategy**: What is the best approach for persisting the entity registry to disk or database?

2. **Circular References**: How should we handle circular references between entities in a way that maintains the hierarchical structure?

3. **Performance Optimization**: What optimizations can be made to improve diffing performance for very large entity hierarchies?

6. **Pluggable Storage Backends**: Should we provide a pluggable interface for different storage implementations?

## References