# Complete EntityRegistry API Documentation

## Class Structure

```python
class EntityRegistry():
    """Registry for versioned entity trees with complete lineage tracking."""
    
    # Class attributes (not instance attributes!)
    tree_registry: Dict[UUID, EntityTree] = {}              # root_ecs_id -> EntityTree
    lineage_registry: Dict[UUID, List[UUID]] = {}           # lineage_id -> [root_ecs_ids]
    live_id_registry: Dict[UUID, Entity] = {}               # live_id -> Entity (for navigation)
    ecs_id_to_root_id: Dict[UUID, UUID] = {}               # ecs_id -> root_ecs_id
    type_registry: Dict[Type[Entity], List[UUID]] = {}      # entity_type -> [lineage_ids]
```

## Core Registry Methods

### 1. Entity Registration
```python
@classmethod
def register_entity_tree(cls, entity_tree: EntityTree) -> None:
    """Register a complete entity tree in the registry."""
    
@classmethod  
def register_entity(cls, entity: Entity) -> None:
    """Register a root entity (builds tree automatically)."""
```

### 2. Tree Retrieval (Immutable Copies)
```python
@classmethod
def get_stored_tree(cls, root_ecs_id: UUID) -> Optional[EntityTree]:
    """Get deep copy of tree with new live_ids (immutable)."""
    
@classmethod
def get_stored_tree_from_entity(cls, entity: Entity) -> Optional[EntityTree]:
    """Get tree containing the given entity."""
```

### 3. Entity Retrieval (Immutable Copies)
```python
@classmethod
def get_stored_entity(cls, root_ecs_id: UUID, ecs_id: UUID) -> Optional[Entity]:
    """Get specific entity from tree (immutable copy)."""
```

### 4. Live Entity Access (Current Runtime Objects)
```python
@classmethod
def get_live_entity(cls, live_id: UUID) -> Optional[Entity]:
    """Get live runtime entity by live_id."""
    
@classmethod
def get_live_root_from_entity(cls, entity: Entity) -> Optional[Entity]:
    """Get live root entity from any sub-entity."""
    
@classmethod
def get_live_root_from_live_id(cls, live_id: UUID) -> Optional[Entity]:
    """Get live root entity from live_id."""
```

### 5. Versioning System
```python
@classmethod
def version_entity(cls, entity: Entity, force_versioning: bool = False) -> bool:
    """Version an entity (creates new versions for changed entities)."""
```

## Key Understanding Points

### 1. Class Methods Only
All EntityRegistry methods are `@classmethod` - there are no instance methods. The registry is a singleton-like class with class attributes.

### 2. Immutability System  
- `get_stored_*` methods return **deep copies** with **new live_ids**
- `get_live_*` methods return **current runtime objects**
- This enables safe concurrent access and "what-if" scenarios

### 3. Two Identity Systems
- **Persistent Identity**: `ecs_id`, `root_ecs_id`, `lineage_id` (preserved across copies)
- **Runtime Identity**: `live_id`, `root_live_id` (unique per retrieval)

### 4. Registry Organization
- **tree_registry**: Maps `root_ecs_id` to complete `EntityTree` objects
- **lineage_registry**: Maps `lineage_id` to list of `root_ecs_ids` (version history)
- **live_id_registry**: Maps `live_id` to current runtime entities (for navigation)
- **ecs_id_to_root_id**: Maps any `ecs_id` to its containing `root_ecs_id`
- **type_registry**: Maps entity types to lineage IDs (for type-based queries)

## Entity Tree Structure

```python
class EntityTree(BaseModel):
    root_ecs_id: UUID
    lineage_id: UUID
    nodes: Dict[UUID, Entity]                    # ecs_id -> Entity
    edges: Dict[Tuple[UUID, UUID], EntityEdge]   # (source, target) -> EdgeDetails
    ancestry_paths: Dict[UUID, List[UUID]]       # ecs_id -> path to root
    
    # Utility methods
    def get_entity(self, entity_id: UUID) -> Optional[Entity]
    def get_entity_by_live_id(self, live_id: UUID) -> Optional[Entity]
    def get_ancestry_path(self, entity_id: UUID) -> List[UUID]
```

## Complete Integration Approach

For pydantic-ai integration, we can create a `RegistryDependencies` class that provides clean access:

```python
@dataclass
class RegistryDependencies:
    """Clean wrapper for pydantic-ai tool access to abstractions framework."""
    
    # CallableRegistry access
    def list_functions(self) -> List[str]:
        return CallableRegistry.list_functions()
    
    def execute_function(self, func_name: str, **kwargs) -> Union[Entity, List[Entity]]:
        return CallableRegistry.execute(func_name, **kwargs)
    
    def get_function_metadata(self, func_name: str):
        return CallableRegistry.get_metadata(func_name)
    
    # EntityRegistry access  
    def get_all_lineages(self) -> Dict[str, List[str]]:
        """Get all lineages with their version history."""
        return {
            str(lineage_id): [str(root_id) for root_id in root_ids]
            for lineage_id, root_ids in EntityRegistry.lineage_registry.items()
        }
    
    def get_lineage_history(self, lineage_id: str) -> List[str]:
        """Get version history for specific lineage."""
        lineage_uuid = UUID(lineage_id)
        root_ids = EntityRegistry.lineage_registry.get(lineage_uuid, [])
        return [str(root_id) for root_id in root_ids]
    
    def get_entity_by_ids(self, root_ecs_id: str, ecs_id: str) -> Optional[Entity]:
        """Get entity with immutable copy."""
        return EntityRegistry.get_stored_entity(UUID(root_ecs_id), UUID(ecs_id))
    
    def get_entity_tree(self, root_ecs_id: str) -> Optional[EntityTree]:
        """Get complete entity tree."""
        return EntityRegistry.get_stored_tree(UUID(root_ecs_id))
    
    # Type-based queries
    def get_entities_by_type(self, entity_type_name: str) -> List[str]:
        """Get all lineages for entities of specific type."""
        for entity_type, lineage_ids in EntityRegistry.type_registry.items():
            if entity_type.__name__ == entity_type_name:
                return [str(lineage_id) for lineage_id in lineage_ids]
        return []
```

This provides the complete foundation for our pydantic-ai integration while maintaining clean separation from the abstractions framework.