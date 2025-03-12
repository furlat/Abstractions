from abstractions.ecs.entity import Entity, Base, create_cold_snapshot
from typing import Protocol, runtime_checkable
from uuid import UUID, uuid4
from typing import Any, Dict, List, Optional, Type, Union, Callable
from datetime import timezone, datetime
import logging
from copy import deepcopy
import importlib
from abstractions.ecs.entity import EntityStorage


class InMemoryEntityStorage(EntityStorage):
    """
    In-memory storage using Python's object references.
    """
    def __init__(self) -> None:
        self._logger = logging.getLogger("InMemoryEntityStorage")
        self._registry: Dict[UUID, Entity] = {}
        self._entity_class_map: Dict[UUID, Type[Entity]] = {}
        self._lineages: Dict[UUID, List[UUID]] = {}
        self._inference_orchestrator: Optional[object] = None
        
    def merge_entity(self, entity: Entity, session: Any = None) -> Entity:
        """
        For in-memory storage, merge is the same as register.
        This implementation ensures compatibility with the EntityStorage protocol.
        
        Args:
            entity: Entity to merge
            session: Ignored in in-memory storage
            
        Returns:
            The registered entity
        """
        result = self.register(entity)
        if result is None:
            raise ValueError(f"Failed to merge entity {entity.ecs_id}")
        return result

    def has_entity(self, entity_id: UUID) -> bool:
        """Check if entity exists in storage."""
        return entity_id in self._registry

    def get_cold_snapshot(self, entity_id: UUID) -> Optional[Entity]:
        """Get the cold (stored) version of an entity."""
        return self._registry.get(entity_id)

    def register(self, entity_or_id: Union[Entity, UUID]) -> Optional[Entity]:
        """Register an entity or retrieve it by ID."""
        if isinstance(entity_or_id, UUID):
            return self.get(entity_or_id, None)

        entity = entity_or_id
            
        # Check if entity already exists
        if self.has_entity(entity.ecs_id):
            # Get existing version
            existing = self.get_cold_snapshot(entity.ecs_id)
            if existing and entity.has_modifications(existing):
                # Fork the entity and all its nested entities
                entity = entity.fork()
        
        # Collect all entities that need to be stored
        entities_to_store: Dict[UUID, Entity] = {}
        
        def collect_entities(e: Entity) -> None:
            if e.ecs_id not in entities_to_store:
                # Create a cold snapshot for storage
                snap = create_cold_snapshot(e)
                entities_to_store[e.ecs_id] = snap
                # Collect nested entities
                for sub in e.get_sub_entities():
                    collect_entities(sub)
        
        # Collect all entities in the tree
        collect_entities(entity)
        
        # Store all entities
        for e in entities_to_store.values():
            self._store_cold_snapshot(e)
            
        return entity

    def get(self, entity_id: UUID, expected_type: Optional[Type[Entity]] = None) -> Optional[Entity]:
        """
        Get an entity by ID with optional type checking.
        
        Args:
            entity_id: The UUID of the entity to retrieve
            expected_type: Optional type to check against
            
        Returns:
            A warm copy of the entity if found and type matches, otherwise None
            
        Note:
            Type checking compares class names rather than using isinstance() directly,
            to handle cases where the same class is imported from different modules.
        """
        ent = self._registry.get(entity_id)
        if not ent:
            self._logger.debug(f"Entity with ID {entity_id} not found in registry")
            return None
            
        # For type checking, we use the class name rather than isinstance()
        # This handles cases where the same class is imported from different modules
        if expected_type:
            actual_type = type(ent)
            # Check class names match
            if actual_type.__name__ != expected_type.__name__:
                # Fall back to isinstance for subtypes
                if not isinstance(ent, expected_type):
                    self._logger.error(f"Type mismatch: got {actual_type.__name__}, expected {expected_type.__name__}")
                    return None
            
        # Create a warm copy
        warm_copy = deepcopy(ent)
        warm_copy.live_id = uuid4()
        warm_copy.from_storage = True  # Mark as coming from storage
        
        return warm_copy

    def list_by_type(self, entity_type: Type[Entity]) -> List[Entity]:
        """List all entities of a specific type."""
        return [
            deepcopy(e)
            for e in self._registry.values()
            if isinstance(e, entity_type)
        ]

    def get_many(self, entity_ids: List[UUID], expected_type: Optional[Type[Entity]] = None) -> List[Entity]:
        """Get multiple entities by ID."""
        return [e for eid in entity_ids if (e := self.get(eid, expected_type)) is not None]

    def get_registry_status(self) -> Dict[str, Any]:
        """Get status information about the registry."""
        return {
            "storage": "in_memory",
            "in_memory": True,
            "entity_count": len(self._registry),
            "lineage_count": len(self._lineages)
        }

    def set_inference_orchestrator(self, orchestrator: object) -> None:
        """Set an inference orchestrator."""
        self._inference_orchestrator = orchestrator

    def get_inference_orchestrator(self) -> Optional[object]:
        """Get the current inference orchestrator."""
        return self._inference_orchestrator

    def clear(self) -> None:
        """Clear all data from storage."""
        self._registry.clear()
        self._entity_class_map.clear()
        self._lineages.clear()

    def get_lineage_entities(self, lineage_id: UUID) -> List[Entity]:
        """Get all entities with a specific lineage ID."""
        return [e for e in self._registry.values() if e.lineage_id == lineage_id]

    def has_lineage_id(self, lineage_id: UUID) -> bool:
        """Check if a lineage ID exists."""
        return any(e for e in self._registry.values() if e.lineage_id == lineage_id)

    def get_lineage_ids(self, lineage_id: UUID) -> List[UUID]:
        """Get all entity IDs with a specific lineage ID."""
        return [e.ecs_id for e in self._registry.values() if e.lineage_id == lineage_id]

    def _store_cold_snapshot(self, entity: Entity) -> None:
        """Store a cold snapshot of an entity and all its sub-entities."""
        stored = set()
        
        def store_recursive(e: Entity) -> None:
            if e in stored:  # Using new hash/eq
                return
                
            stored.add(e)
            snap = create_cold_snapshot(e)
            self._registry[e.ecs_id] = snap
            
            # Update lineage tracking
            if e.lineage_id not in self._lineages:
                self._lineages[e.lineage_id] = []
            if e.ecs_id not in self._lineages[e.lineage_id]:
                self._lineages[e.lineage_id].append(e.ecs_id)
                
            # Store all sub-entities
            for sub in e.get_sub_entities():
                store_recursive(sub)
                
        store_recursive(entity)


##############################
# 6) SQL Storage Integration
##############################

from sqlalchemy import (
    Column, String, Integer, DateTime, JSON, ForeignKey, Table,
    create_engine, inspect, or_, text, select as sa_select, Uuid as SQLAUuid
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship,
    Session, sessionmaker, joinedload, registry as sa_registry
)
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
import importlib
from datetime import timezone
from typing import Tuple, Dict, List, Any, Optional, Type, ClassVar, Set, Union, cast

# Base class for all SQL models
class Base(DeclarativeBase):
    """SQLAlchemy declarative base class."""
    pass

def dynamic_import(path_str: str) -> Type[Entity]:
    """Import a class dynamically by its dotted path."""
    try:
        mod_name, cls_name = path_str.rsplit(".", 1)
        mod = importlib.import_module(mod_name)
        return getattr(mod, cls_name)
    except (ImportError, AttributeError) as e:
        raise ImportError(f"Failed to import {path_str}: {e}")

# Association table helper function
def create_association_table(table_name: str, left_id: str, right_id: str) -> Table:
    """
    Create a SQLAlchemy association table for many-to-many relationships.
    
    Args:
        table_name: Name for the association table
        left_id: Column name for the left side foreign key
        right_id: Column name for the right side foreign key
        
    Returns:
        SQLAlchemy Table object for the association
    """
    return Table(
        table_name,
        Base.metadata,
        Column(f"{left_id}_id", Integer, ForeignKey(f"{left_id}.id"), primary_key=True),
        Column(f"{right_id}_id", Integer, ForeignKey(f"{right_id}.id"), primary_key=True)
    )
    

# Import needed for SQLAlchemy
from sqlalchemy import (
    Column, String, Integer, DateTime, JSON, ForeignKey, Table,
    create_engine, inspect, or_, text, select as sa_select, Uuid as SQLAUuid
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship,
    Session, sessionmaker, joinedload, registry as sa_registry
)
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID

class EntityBase(Base):
    """
    Base SQLAlchemy model for all entity tables.
    
    Provides common columns and functionality that all entity tables will share.
    """
    __abstract__ = True
    
    # Primary key (auto-incrementing integer)
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Entity versioning fields
    ecs_id: Mapped[UUID] = mapped_column(SQLAUuid, index=True)
    lineage_id: Mapped[UUID] = mapped_column(SQLAUuid, index=True)
    parent_id: Mapped[Optional[UUID]] = mapped_column(SQLAUuid, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    old_ids: Mapped[List[UUID]] = mapped_column(JSON)
    
    # Table name derivation - using string literal to avoid declared_attr issues
    __tablename__: str = ""  # Will be overridden by subclasses
    
    # Common methods to convert between SQL model and Pydantic entity
    def to_entity(self) -> Entity:
        """Convert SQLAlchemy model to Pydantic Entity."""
        raise NotImplementedError("Subclasses must implement to_entity")
    
    @classmethod
    def from_entity(cls, entity: Entity) -> 'EntityBase':
        """Convert Pydantic Entity to SQLAlchemy model."""
        raise NotImplementedError("Subclasses must implement from_entity")
    
    def handle_relationships(self, entity: Entity, session: Session, orm_objects: Dict[UUID, Any]) -> None:
        """Handle entity relationships for this model."""
        pass

class BaseEntitySQL(EntityBase):
    """
    SQLAlchemy model for generic entity storage.
    
    This is a concrete implementation that serves as a fallback storage
    for entities without specific SQL models.
    """
    __tablename__ = "base_entity"
    
    # Additional fields needed for storing any entity
    class_name = mapped_column(String(255), nullable=False)
    data = mapped_column(JSON, nullable=True)
    entity_type = mapped_column(String(50), nullable=False, default="base_entity")
    
    __mapper_args__ = {
        "polymorphic_identity": "base_entity",
    }
    
    # Ensure base_entity table is created when Base.metadata.create_all is called
    metadata = Base.metadata
    
    @classmethod
    def from_entity(cls, entity: Entity) -> 'BaseEntitySQL':
        """Convert from Entity to SQL model."""
        # Convert UUID objects to strings for JSON serialization
        str_old_ids = [str(uid) for uid in entity.old_ids] if entity.old_ids else []
        
        return cls(
            ecs_id=entity.ecs_id,
            lineage_id=entity.lineage_id,
            parent_id=entity.parent_id,
            created_at=entity.created_at,
            old_ids=str_old_ids,
            class_name=f"{entity.__class__.__module__}.{entity.__class__.__name__}",
            data=entity.entity_dump(),
            entity_type="base_entity"
        )
    
    def to_entity(self) -> Entity:
        """Convert from SQL model to Entity."""
        uuid_old_ids = []
        if self.old_ids:
            for old_id in self.old_ids:
                if isinstance(old_id, str):
                    uuid_old_ids.append(UUID(old_id))
                elif isinstance(old_id, UUID):
                    uuid_old_ids.append(old_id)
        
        # Merge versioning fields + data
        combined = {
            "ecs_id": self.ecs_id,
            "lineage_id": self.lineage_id,
            "parent_id": self.parent_id,
            "created_at": self.created_at,
            "old_ids": uuid_old_ids,
            "from_storage": True,
            **(self.data or {})
        }
        
        # Import dynamically to avoid circular imports
        cls_obj = dynamic_import(self.class_name)
        return cls_obj(**combined)

class SqlEntityStorage(EntityStorage):
    """
    SQLAlchemy-based entity storage implementation.
    
    Features:
    - Pure SQLAlchemy ORM instead of SQLModel
    - Proper relationship handling with association tables
    - Type-safe conversion between entities and database models
    - Optimized querying with proper joins
    """
    def __init__(
        self,
        session_factory: Callable[[], Session],
        entity_to_orm_map: Dict[Type[Entity], Type[EntityBase]]
    ) -> None:
        """
        Initialize SQL storage with session factory and entity mappings.
        
        Args:
            session_factory: Factory function to create SQLAlchemy sessions
            entity_to_orm_map: Mapping from entity types to their SQLAlchemy models
        """
        self._logger = logging.getLogger("SqlEntityStorage")
        self._session_factory = session_factory
        self._entity_to_orm_map = entity_to_orm_map
        self._inference_orchestrator: Optional[object] = None
        
        # If BaseEntitySQL is available, use it as fallback
        if Entity not in self._entity_to_orm_map:
            # Use cast to tell type checker this is compatible
            self._entity_to_orm_map[Entity] = cast(Type[EntityBase], BaseEntitySQL)
            self._logger.info("Added BaseEntitySQL as fallback ORM mapping")
        
        # Cache to avoid repeated lookups
        self._entity_class_map: Dict[UUID, Type[Entity]] = {}
        self._entity_orm_cache: Dict[Type[Entity], Type[EntityBase]] = {}
        self._logger.info(f"Initialized SQL storage with {len(entity_to_orm_map)} entity mappings")
    
    def get_session(self, existing_session: Optional[Session] = None) -> Tuple[Session, bool]:
        """
        Get a session - either the provided one or a new one.
        
        Args:
            existing_session: Optional existing session to reuse
                
        Returns:
            Tuple of (session, should_close_when_done)
        """
        if existing_session is not None:
            self._logger.debug("Reusing provided session")
            return existing_session, False
                
        self._logger.debug("Creating new session")
        return self._session_factory(), True
    
    def has_entity(self, entity_id: UUID, session: Optional[Session] = None) -> bool:
        """
        Check if an entity exists in storage.
        
        Args:
            entity_id: UUID of the entity to check
            session: Optional session to reuse
                
        Returns:
            True if the entity exists, False otherwise
        """
        session, should_close = self.get_session(session)
        try:
            # Check if the entity ID is cached
            if entity_id in self._entity_class_map:
                entity_type = self._entity_class_map[entity_id]
                orm_class = self._get_orm_class(entity_type)
                exists = session.query(orm_class).filter(orm_class.ecs_id == entity_id).first() is not None
                return exists
            
            # If not cached, check all possible tables
            for orm_class in self._entity_to_orm_map.values():
                exists = session.query(orm_class).filter(orm_class.ecs_id == entity_id).first() is not None
                if exists:
                    return True
            return False
        finally:
            if should_close:
                session.close()
    
    def register(self, entity_or_id: Union[Entity, UUID], session: Optional[Session] = None) -> Optional[Entity]:
        """
        Register an entity and all its sub-entities in a single transaction.
        
        Uses the dependency graph to determine the correct processing order,
        ensuring that dependencies are processed before dependent entities.
        
        Args:
            entity_or_id: Entity to register or UUID to retrieve
            session: Optional session to reuse
                
        Returns:
            The registered entity, or None if registration failed
        """
        # Handle UUID case - just retrieve the entity
        if isinstance(entity_or_id, UUID):
            return self.get(entity_or_id, None, session)
        
        entity = entity_or_id
        
        # Create a new session if needed
        own_session = session is None
        if own_session:
            session = self._session_factory()
        
        try:
            # Check if entity already exists and has modifications
            if self.has_entity(entity.ecs_id, session):
                existing = self.get_cold_snapshot(entity.ecs_id, session)
                if existing and entity.has_modifications(existing)[0]:
                    # Entity exists but has changed - fork it
                    self._logger.info(f"Entity {entity.ecs_id} has modifications, forking")
                    entity = entity.fork()
            
            # Initialize dependency graph if needed
            if entity.deps_graph is None:
                entity.initialize_deps_graph()
                
            # Get all entities in topological order (dependencies first)
            # Check if deps_graph exists to satisfy type checker
            if entity.deps_graph is None:
                sorted_entities = [entity]  # Fallback if no dependency graph
            else:
                sorted_entities = entity.deps_graph.get_topological_sort()
                
            self._logger.info(f"Processing {len(sorted_entities)} entities in topological order")
            
            # Track processed entities and their ORM objects
            orm_objects = {}
            
            # Phase 1: Create/update all entities
            for curr_entity in sorted_entities:
                # Check if this entity already exists in the database
                existing_orm = None
                if self.has_entity(curr_entity.ecs_id, session):
                    # Find which table contains this entity
                    for orm_class in self._entity_to_orm_map.values():
                        existing_orm = session.query(orm_class).filter(
                            orm_class.ecs_id == curr_entity.ecs_id
                        ).first()
                        if existing_orm:
                            self._logger.debug(f"Found existing entity {curr_entity.ecs_id} in {orm_class.__name__}")
                            orm_objects[curr_entity.ecs_id] = existing_orm
                            break
                
                if existing_orm is None:
                    # Create new ORM object for this entity
                    orm_class = self._get_orm_class(curr_entity)
                    self._logger.debug(f"Creating new ORM object for {curr_entity.ecs_id} using {orm_class.__name__}")
                    orm_obj = orm_class.from_entity(curr_entity)
                    session.add(orm_obj)
                    orm_objects[curr_entity.ecs_id] = orm_obj
                
                # Cache entity type for future lookups
                self._entity_class_map[curr_entity.ecs_id] = type(curr_entity)
            
            # Flush to ensure all objects have IDs
            session.flush()
            
            # Phase 2: Handle relationships after all entities exist
            for curr_entity in sorted_entities:
                ecs_id = curr_entity.ecs_id
                if ecs_id in orm_objects and hasattr(orm_objects[ecs_id], 'handle_relationships'):
                    self._logger.debug(f"Handling relationships for {ecs_id}")
                    orm_objects[ecs_id].handle_relationships(curr_entity, session, orm_objects)
            
            # Commit if using our own session
            if own_session:
                session.commit()
                
            return entity
        except Exception as e:
            # Roll back if using our own session
            if own_session:
                session.rollback()
            self._logger.error(f"Error registering entity: {str(e)}")
            raise
        finally:
            # Close if using our own session
            if own_session:
                session.close()
    
    def get_cold_snapshot(self, entity_id: UUID, session: Optional[Session] = None) -> Optional[Entity]:
        """
        Get the stored version of an entity.
        
        Args:
            entity_id: UUID of the entity to retrieve
            session: Optional session to reuse
                
        Returns:
            The stored entity, or None if not found
        """
        session, should_close = self.get_session(session)
        try:
            # If we know the entity type, query the specific table
            if entity_id in self._entity_class_map:
                entity_type = self._entity_class_map[entity_id]
                orm_class = self._get_orm_class(entity_type)
                
                orm_entity = session.query(orm_class).filter(orm_class.ecs_id == entity_id).first()
                if orm_entity:
                    entity = orm_entity.to_entity()
                    entity.from_storage = True
                    return entity
            
            # Otherwise, search all tables
            for orm_class in self._entity_to_orm_map.values():
                orm_entity = session.query(orm_class).filter(orm_class.ecs_id == entity_id).first()
                if orm_entity:
                    entity = orm_entity.to_entity()
                    entity.from_storage = True
                    # Cache the entity type for future lookups
                    self._entity_class_map[entity_id] = type(entity)
                    return entity
            
            return None
        finally:
            if should_close:
                session.close()
    
    def get(self, entity_id: UUID, expected_type: Optional[Type[Entity]] = None, 
            session: Optional[Session] = None) -> Optional[Entity]:
        """
        Get an entity by ID with optional type checking.
        
        Args:
            entity_id: UUID of the entity to retrieve
            expected_type: Optional type to check against
            session: Optional session to reuse
                
        Returns:
            The entity, or None if not found or type mismatch
        """
        session, should_close = self.get_session(session)
        try:
            # Get the cold snapshot
            entity = self.get_cold_snapshot(entity_id, session)
            if not entity:
                return None
            
            # Check the type if requested
            if expected_type:
                actual_type = type(entity)
                # Use class name comparison instead of strict isinstance 
                # to handle cases where the same class is imported from different modules
                if actual_type.__name__ != expected_type.__name__:
                    # Fall back to isinstance for subtypes
                    if not isinstance(entity, expected_type):
                        self._logger.error(f"Type mismatch: {actual_type.__name__} is not a {expected_type.__name__}")
                        return None
            
            # Create a warm copy with a new live_id
            warm_copy = deepcopy(entity)
            warm_copy.live_id = uuid4()
            warm_copy.from_storage = True
            
            return warm_copy
        finally:
            if should_close:
                session.close()
    
    def list_by_type(self, entity_type: Type[Entity], session: Optional[Session] = None) -> List[Entity]:
        """
        List all entities of a specific type.
        
        Args:
            entity_type: Type of entities to list
            session: Optional session to reuse
                
        Returns:
            List of entities of the specified type
        """
        session, should_close = self.get_session(session)
        try:
            results = []
            
            # Find all ORM classes that could map to this entity type
            if entity_type in self._entity_to_orm_map:
                # Direct mapping
                orm_class = self._entity_to_orm_map[entity_type]
                orm_entities = session.query(orm_class).all()
                for orm_entity in orm_entities:
                    entity = orm_entity.to_entity()
                    entity.from_storage = True
                    
                    # Cache entity type for future lookups
                    self._entity_class_map[entity.ecs_id] = type(entity)
                    
                    # Add to results if type matches
                    if isinstance(entity, entity_type):
                        results.append(entity)
            
            # Also check for subtypes in the generic table if we're using a fallback
            if Entity in self._entity_to_orm_map:
                base_orm = self._entity_to_orm_map[Entity]
                # Base ORM might be used for generic entities
                try:
                    # Get a sample instance to check if it has the class_name attribute
                    sample = session.query(base_orm).limit(1).first()
                    if sample and hasattr(sample, 'class_name'):
                        class_name = f"{entity_type.__module__}.{entity_type.__qualname__}"
                        # Use getattr to access the class_name attribute safely for type checking
                        class_name_attr = getattr(base_orm, 'class_name', None)
                        if class_name_attr is not None:
                            orm_entities = session.query(base_orm).filter(class_name_attr == class_name).all()
                        else:
                            orm_entities = []
                    else:
                        # Skip if no class_name attribute or no instances
                        orm_entities = []
                except Exception as e:
                    self._logger.warning(f"Error checking generic table: {str(e)}")
                    orm_entities = []
                for orm_entity in orm_entities:
                    entity = orm_entity.to_entity()
                    entity.from_storage = True
                    
                    # Cache entity type for future lookups
                    self._entity_class_map[entity.ecs_id] = type(entity)
                    
                    # Add to results if type matches
                    if isinstance(entity, entity_type):
                        results.append(entity)
            
            return results
        finally:
            if should_close:
                session.close()
    
    def get_many(self, entity_ids: List[UUID], expected_type: Optional[Type[Entity]] = None,
                session: Optional[Session] = None) -> List[Entity]:
        """
        Get multiple entities by ID.
        
        Args:
            entity_ids: List of UUIDs to retrieve
            expected_type: Optional type to check against
            session: Optional session to reuse
                
        Returns:
            List of entities matching the IDs and type
        """
        if not entity_ids:
            return []
            
        session, should_close = self.get_session(session)
        try:
            results = []
            
            # Group IDs by entity type if we can determine them from cache
            type_groups: Dict[Type[Entity], List[UUID]] = {}
            unknown_ids = []
            
            for entity_id in entity_ids:
                if entity_id in self._entity_class_map:
                    entity_type = self._entity_class_map[entity_id]
                    if entity_type not in type_groups:
                        type_groups[entity_type] = []
                    type_groups[entity_type].append(entity_id)
                else:
                    unknown_ids.append(entity_id)
            
            # Process known types in batches
            for known_type, ids in type_groups.items():
                # Skip if expected_type is specified and doesn't match
                if expected_type and not issubclass(known_type, expected_type):
                    continue
                    
                # Get the ORM class for this type
                orm_class = self._get_orm_class(known_type)
                
                # Use IN clause for more efficient querying
                orm_entities = session.query(orm_class).filter(orm_class.ecs_id.in_(ids)).all()
                
                # Convert to entities
                for orm_entity in orm_entities:
                    entity = orm_entity.to_entity()
                    entity.from_storage = True
                    
                    # Create warm copy
                    warm_copy = deepcopy(entity)
                    warm_copy.live_id = uuid4()
                    warm_copy.from_storage = True
                    
                    results.append(warm_copy)
            
            # Process unknown IDs individually
            for entity_id in unknown_ids:
                entity = self.get(entity_id, expected_type, session)
                if entity:
                    results.append(entity)
            
            return results
        finally:
            if should_close:
                session.close()
    
    def get_registry_status(self) -> Dict[str, Any]:
        """Get status information about the registry."""
        return {
            "storage": "sql",
            "known_ids_in_cache": len(self._entity_class_map)
        }
    
    def set_inference_orchestrator(self, orchestrator: object) -> None:
        """Set an inference orchestrator."""
        self._inference_orchestrator = orchestrator
    
    def get_inference_orchestrator(self) -> Optional[object]:
        """Get the current inference orchestrator."""
        return self._inference_orchestrator
    
    def clear(self) -> None:
        """Clear cached data (doesn't affect database)."""
        self._entity_class_map.clear()
        self._logger.warning("SqlEntityStorage.clear() only clears caches, not database data")
    
    def get_lineage_entities(self, lineage_id: UUID, session: Optional[Session] = None) -> List[Entity]:
        """
        Get all entities with a specific lineage ID.
        
        Args:
            lineage_id: Lineage ID to query
            session: Optional session to reuse
                
        Returns:
            List of entities with the specified lineage ID
        """
        session, should_close = self.get_session(session)
        try:
            results = []
            
            # Query all tables for entities with the given lineage ID
            for orm_class in self._entity_to_orm_map.values():
                # Use efficiently indexed query for lineage_id
                orm_entities = session.query(orm_class).filter(orm_class.lineage_id == lineage_id).all()
                
                for orm_entity in orm_entities:
                    entity = orm_entity.to_entity()
                    entity.from_storage = True
                    
                    # Cache entity type for future lookups
                    self._entity_class_map[entity.ecs_id] = type(entity)
                    
                    results.append(entity)
            
            return results
        finally:
            if should_close:
                session.close()
    
    def has_lineage_id(self, lineage_id: UUID, session: Optional[Session] = None) -> bool:
        """
        Check if a lineage ID exists.
        
        Args:
            lineage_id: Lineage ID to check
            session: Optional session to reuse
                
        Returns:
            True if the lineage ID exists, False otherwise
        """
        entities = self.get_lineage_entities(lineage_id, session=session)
        return len(entities) > 0
    
    def get_lineage_ids(self, lineage_id: UUID, session: Optional[Session] = None) -> List[UUID]:
        """
        Get all entity IDs with a specific lineage ID.
        
        Args:
            lineage_id: Lineage ID to query
            session: Optional session to reuse
                
        Returns:
            List of entity IDs with the specified lineage ID
        """
        return [entity.ecs_id for entity in self.get_lineage_entities(lineage_id, session=session)]
    
    def _get_orm_class(self, entity_or_type: Union[Entity, Type[Entity]]) -> Type[EntityBase]:
        """
        Get the appropriate ORM class for an entity or entity type.
        Uses class hierarchy to find the most specific match.
        
        Args:
            entity_or_type: Entity instance or class to find ORM mapping for
                
        Returns:
            ORM class for the entity
        """
        # Get the actual type
        entity_type: Type[Entity]
        if isinstance(entity_or_type, type):
            entity_type = entity_or_type
        else:
            entity_type = type(entity_or_type)
        
        # Check cache first
        if entity_type in self._entity_orm_cache:
            return self._entity_orm_cache[entity_type]
        
        # Find the most specific match in the class hierarchy
        for cls in entity_type.__mro__:
            if cls in self._entity_to_orm_map:
                # Cache the result for future lookups
                self._entity_orm_cache[entity_type] = self._entity_to_orm_map[cls]
                return self._entity_to_orm_map[cls]
        
        # If no match found, use the base Entity mapping as fallback
        if Entity in self._entity_to_orm_map:
            fallback = self._entity_to_orm_map[Entity]
            self._entity_orm_cache[entity_type] = fallback
            self._logger.warning(f"Using fallback mapping for {entity_type.__name__}")
            return fallback
        
        raise ValueError(f"No ORM mapping found for {entity_type.__name__}")
    
    def _safe_merge_entity(self, entity: Entity, session: Session) -> Any:
        """
        Safely merge an entity without session conflicts by always creating a fresh ORM object.
        This avoids the "already attached to session" errors by never reusing ORM objects.
        
        Args:
            entity: Entity to merge
            session: Current session
            
        Returns:
            Merged ORM object
        """
        # Get ORM class for entity
        orm_class = self._get_orm_class(entity)
        
        # Always create a fresh ORM object to avoid session conflicts
        orm_obj = orm_class.from_entity(entity)
        
        # Use merge to handle any session issues
        try:
            merged = session.merge(orm_obj)
            return merged
        except Exception as e:
            self._logger.error(f"Error during safe merge of {entity.ecs_id}: {str(e)}")
            # Try an alternative approach - expunge and add
            session.expunge_all()  # Detach all objects
            session.add(orm_obj)   # Add fresh object
            session.flush()        # Flush to database
            return orm_obj

    def _store_entity_tree(self, entity: Entity, session: Session) -> None:
        """
        Store an entire entity tree in a single database transaction.
        
        Uses the dependency graph to find all sub-entities and register them
        in the correct order. This ensures that all sub-entities are properly
        stored, even if they're not marked as sql_root=True.
        
        Args:
            entity: Root entity of the tree
            session: Session to use
        """
        # Initialize dependency graph if needed
        if entity.deps_graph is None:
            entity.initialize_deps_graph()
        
        # Track processed entities to avoid duplicates
        processed_ids = set()
        orm_objects = {}
        
        # Find all entities to store using dependency graph
        entities_to_store = {entity.ecs_id: entity}
        for sub in entity.get_sub_entities():
            entities_to_store[sub.ecs_id] = sub
            
        self._logger.info(f"Storing {len(entities_to_store)} entities in tree")
        
        # Phase 1: Store all entities first (without relationships)
        for ecs_id, curr_entity in entities_to_store.items():
            # Skip if already processed or already being registered elsewhere
            if ecs_id in processed_ids or curr_entity.is_being_registered:
                self._logger.debug(f"Skipping entity {ecs_id} - already processed or being registered")
                continue
            
            # Mark as being registered to prevent recursive registration
            curr_entity.is_being_registered = True
            
            try:
                # Check if entity already exists in database
                existing = session.query(BaseEntitySQL).filter(
                    BaseEntitySQL.ecs_id == curr_entity.ecs_id
                ).first()
                
                if existing:
                    self._logger.debug(f"Entity {ecs_id} already exists in database, retrieving")
                    # If entity exists, get its ORM object which should already be in session
                    orm_class = self._get_orm_class(curr_entity)
                    orm_obj = session.query(orm_class).filter(
                        orm_class.ecs_id == curr_entity.ecs_id
                    ).first()
                else:
                    self._logger.debug(f"Creating new entity {ecs_id} of type {type(curr_entity).__name__}")
                    # Create a fresh ORM object for a new entity
                    orm_obj = self._safe_merge_entity(curr_entity, session)
                
                # Add to tracking collections
                orm_objects[ecs_id] = orm_obj
                
                # Cache entity type
                self._entity_class_map[ecs_id] = type(curr_entity)
                processed_ids.add(ecs_id)
            finally:
                # Reset flag to allow future registrations
                curr_entity.is_being_registered = False
        
        # Flush to ensure all objects have IDs
        session.flush()
        
        # Phase 2: Handle relationships in dependency order (bottom-up)
        # Process entities in topological order if possible
        sorted_entities = []
        if entity.deps_graph:
            try:
                # Get entities in topological order (dependencies first)
                sorted_entities = entity.deps_graph.get_topological_sort()
            except Exception as e:
                self._logger.warning(f"Error getting topological sort: {str(e)}")
                # Fall back to entities_to_store order
                sorted_entities = list(entities_to_store.values())
        else:
            # Fall back to entities_to_store order
            sorted_entities = list(entities_to_store.values())
            
        # Process relationships in dependency order
        for curr_entity in sorted_entities:
            ecs_id = curr_entity.ecs_id
            if ecs_id in orm_objects and hasattr(orm_objects[ecs_id], 'handle_relationships'):
                try:
                    self._logger.debug(f"Handling relationships for {ecs_id}")
                    # Use the relationship handling method
                    orm_objects[ecs_id].handle_relationships(curr_entity, session, orm_objects)
                except Exception as e:
                    self._logger.error(f"Error handling relationships for {ecs_id}: {str(e)}")
                    raise
        
        # Flush again to update relationships
        session.flush()

# End of SqlEntityStorage implementation

    def merge_entity(self, entity: Entity, session: Optional[Session] = None) -> Entity:
        """
        Merge an entity into a session, creating a fresh ORM object to avoid session conflicts.
        This method simply delegates to register as it now handles conflicts properly.
        
        Args:
            entity: Entity to merge
            session: Optional session to use (will create one if not provided)
            
        Returns:
            The merged entity
        """
        self._logger.debug(f"Merging entity {entity.ecs_id} of type {type(entity).__name__}")
        
        # Simply use the register method which now handles entities in dependency order
        # and avoids session conflicts by design
        result = self.register(entity, session)
        # Cast to satisfy type checker (register can return None but merge_entity promises Entity)
        if result is None:
            raise ValueError(f"Failed to merge entity {entity.ecs_id}")
        return result

