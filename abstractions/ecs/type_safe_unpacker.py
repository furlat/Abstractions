"""
Type-Safe Entity Unpacker: Guaranteed Entity-Only Pipeline

This module implements a type-safe architecture that eliminates raw data leakage
by ensuring every object in the entity pipeline is guaranteed to be an Entity.

Core Design Principle:
- Every component MUST only deal with Entity objects
- No raw data structures allowed in entity pipelines
- Type safety enforced at every boundary
"""

from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4
from datetime import datetime, timezone
from dataclasses import dataclass

from abstractions.ecs.entity import Entity, create_dynamic_entity_class


@dataclass
class TypeSafeUnpackingResult:
    """Type-safe unpacking result with guaranteed Entity-only content."""
    primary_entities: List[Entity]  # Guaranteed all Entity objects
    metadata: Dict[str, Any]        # Analysis and audit metadata


class PureEntityExtractor:
    """Extract only Entity objects from any data structure."""
    
    @classmethod
    def extract_entities(cls, result: Any) -> List[Entity]:
        """
        Recursively find all Entity objects in any data structure.
        
        Args:
            result: Any data structure that may contain entities
            
        Returns:
            List[Entity]: All entities found, flattened (guaranteed Entity objects only)
        """
        entities = []
        cls._recursive_extract(result, entities)
        return entities
    
    @classmethod
    def _recursive_extract(cls, obj: Any, entities: List[Entity]) -> None:
        """
        Recursively extract entities into the entities list.
        
        This function only collects Entity objects and ignores everything else,
        ensuring no raw data structures can leak into the entity pipeline.
        """
        if isinstance(obj, Entity):
            entities.append(obj)
        elif isinstance(obj, (list, tuple)):
            for item in obj:
                cls._recursive_extract(item, entities)
        elif isinstance(obj, dict):
            for value in obj.values():
                cls._recursive_extract(value, entities)
        # Ignore all non-Entity objects (int, str, float, etc.)


class DataWrapper:
    """Wrap any data structure in a WrapperEntity."""
    
    @classmethod
    def wrap_complete_result(cls, result: Any, execution_id: UUID) -> Entity:
        """
        Wrap the entire result structure in a WrapperEntity.
        
        This preserves the original structure while making it Entity-compatible,
        ensuring everything in the pipeline is an Entity object.
        
        Args:
            result: Any data structure to wrap
            execution_id: Execution ID for tracking
            
        Returns:
            Entity: WrapperEntity containing the original structure
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


class StrategyAnalyzer:
    """Determine unpacking strategy without processing data."""
    
    @classmethod
    def determine_strategy(cls, result: Any, force_unpack: bool = False) -> str:
        """
        Determine strategy based only on type patterns.
        
        This function only analyzes types and patterns without creating any
        data structures, eliminating the source of raw data leakage.
        
        Args:
            result: The function return value to analyze
            force_unpack: If True, force unpacking for entity containers
            
        Returns:
            str: 'unpack_entities' or 'wrap_complete_result'
        """
        # Pure tuple of entities - safe to unpack by default
        if isinstance(result, tuple) and all(isinstance(item, Entity) for item in result):
            return "unpack_entities"
        
        # Force unpack requested for entity containers
        if force_unpack:
            if isinstance(result, (list, dict)) and cls._contains_only_entities(result):
                return "unpack_entities"
        
        # Everything else gets wrapped (safe default)
        return "wrap_complete_result"
    
    @classmethod
    def _contains_only_entities(cls, container: Any) -> bool:
        """
        Check if container contains only Entity objects.
        
        This is used for force unpacking validation - we only unpack
        containers that contain pure entities.
        """
        if isinstance(container, list):
            return len(container) > 0 and all(isinstance(item, Entity) for item in container)
        elif isinstance(container, dict):
            return len(container) > 0 and all(isinstance(value, Entity) for value in container.values())
        return False


class TypeSafeUnpacker:
    """Type-safe unpacker that always returns List[Entity]."""
    
    @classmethod
    def process(cls, result: Any, strategy: str, execution_id: UUID) -> List[Entity]:
        """
        Process result according to strategy.
        
        This is the core type-safe processing function that guarantees
        only Entity objects are returned, eliminating raw data leakage.
        
        Args:
            result: The function return value
            strategy: 'unpack_entities' or 'wrap_complete_result'
            execution_id: Execution ID for tracking
            
        Returns:
            List[Entity]: Always returns entities, never raw data
        """
        if strategy == "unpack_entities":
            # Extract entities and return them individually
            entities = PureEntityExtractor.extract_entities(result)
            if not entities:
                # Fallback: wrap if no entities found (should not happen with current strategy logic)
                wrapped = DataWrapper.wrap_complete_result(result, execution_id)
                return [wrapped]
            return entities
            
        elif strategy == "wrap_complete_result":
            # Wrap entire result in single entity
            wrapped = DataWrapper.wrap_complete_result(result, execution_id)
            return [wrapped]
            
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
    
    @classmethod
    def unpack_with_type_safety(
        cls,
        result: Any,
        force_unpack: bool = False,
        execution_id: Optional[UUID] = None
    ) -> TypeSafeUnpackingResult:
        """
        Complete type-safe unpacking with metadata.
        
        This is the main entry point for type-safe unpacking that replaces
        the broken unpack_with_signature_analysis method.
        
        Args:
            result: The function return value
            force_unpack: If True, force unpacking for entity containers
            execution_id: Optional execution ID for tracking
            
        Returns:
            TypeSafeUnpackingResult: Guaranteed Entity-only result
        """
        if execution_id is None:
            execution_id = uuid4()
        
        # Determine strategy using pure type analysis
        strategy = StrategyAnalyzer.determine_strategy(result, force_unpack)
        
        # Process with guaranteed type safety
        entities = cls.process(result, strategy, execution_id)
        
        # Build comprehensive metadata
        metadata = {
            "execution_id": str(execution_id),
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "force_unpack_effective": force_unpack,
            "strategy_used": strategy,
            "entity_count": len(entities),
            "type_safe": True,
            "original_type": str(type(result).__name__),
            "unpacking_type": "type_safe_guaranteed"
        }
        
        # Add strategy-specific metadata
        if strategy == "unpack_entities":
            metadata["unpacked_entity_types"] = [type(e).__name__ for e in entities]
        else:
            metadata["wrapped_in_entity"] = True
            metadata["wrapper_entity_type"] = type(entities[0]).__name__
        
        return TypeSafeUnpackingResult(
            primary_entities=entities,  # Guaranteed all Entity objects
            metadata=metadata
        )


# Backward compatibility adapter for existing integration
class TypeSafeContainerReconstructor:
    """
    Type-safe replacement for ContainerReconstructor.unpack_with_signature_analysis.
    
    This maintains the same external API while providing type safety guarantees.
    """
    
    @classmethod
    def unpack_with_signature_analysis(
        cls,
        result: Any,
        return_analysis_metadata: Dict[str, Any],
        output_entity_class: Optional[type] = None,
        execution_id: Optional[UUID] = None
    ):
        """
        Type-safe replacement for the broken signature analysis method.
        
        This maintains backward compatibility while eliminating raw data leakage.
        """
        print(f"🔧 TYPE-SAFE UNPACKER CALLED: {type(result).__name__}")
        if execution_id is None:
            execution_id = uuid4()
        
        # Get force_unpack from registration metadata (safe default: False)
        force_unpack = return_analysis_metadata.get('supports_unpacking', False)
        
        # Use type-safe unpacking
        type_safe_result = TypeSafeUnpacker.unpack_with_type_safety(
            result, force_unpack, execution_id
        )
        
        # Combine metadata for audit trail
        combined_metadata = {
            **return_analysis_metadata,  # Registration-time analysis
            **type_safe_result.metadata,  # Type-safe analysis
            "migration_status": "type_safe_implementation"
        }
        
        # Return in expected format for backward compatibility
        # Import here to avoid circular dependency
        from abstractions.ecs.entity_unpacker import UnpackingResult
        
        return UnpackingResult(
            primary_entities=type_safe_result.primary_entities,  # Guaranteed Entity objects
            container_entity=None,  # No separate container needed with type-safe approach
            metadata=combined_metadata
        )