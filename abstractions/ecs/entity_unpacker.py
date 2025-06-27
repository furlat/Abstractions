"""
Entity Unpacker: Multi-Entity Return Processing (Simplified)

This module provides unpacking logic for functions that return multiple entities,
focusing on core functionality without unnecessary complexity.

Features:
- Unpack complex return structures into separate entities
- Preserve container metadata for reconstruction
- Simple tracking through FunctionExecution entity
- Handle mixed entity/non-entity containers
"""

from typing import Any, Dict, List, Tuple, Union, Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone
from dataclasses import dataclass

from abstractions.ecs.entity import Entity, EntityRegistry, create_dynamic_entity_class
from abstractions.ecs.return_type_analyzer import ReturnAnalysis, ReturnPattern


@dataclass
class UnpackingResult:
    """Result of unpacking a function return."""
    primary_entities: List[Entity]      # Main entities to register
    container_entity: Optional[Entity]  # Optional container entity for complex structures
    metadata: Dict[str, Any]            # Unpacking metadata for audit trails


class EntityUnpacker:
    """Simplified unpacker for multi-entity function returns."""
    
    @classmethod
    def unpack_return(
        cls, 
        result: Any, 
        analysis: ReturnAnalysis,
        execution_id: Optional[UUID] = None
    ) -> UnpackingResult:
        """
        Unpack function return into separate entities.
        
        Args:
            result: The function return value
            analysis: Complete return analysis from ReturnTypeAnalyzer
            execution_id: Optional execution ID for tracking
            
        Returns:
            UnpackingResult with entities and metadata
        """
        if execution_id is None:
            execution_id = uuid4()
        
        # Route to appropriate unpacking strategy
        if analysis.unpacking_strategy == "none":
            return cls._handle_single_entity(result, analysis, execution_id)
        elif analysis.unpacking_strategy == "sequence_unpack":
            return cls._handle_sequence_unpack(result, analysis, execution_id)
        elif analysis.unpacking_strategy == "dict_unpack":
            return cls._handle_dict_unpack(result, analysis, execution_id)
        elif analysis.unpacking_strategy == "mixed_unpack":
            return cls._handle_mixed_unpack(result, analysis, execution_id)
        elif analysis.unpacking_strategy == "nested_unpack":
            return cls._handle_nested_unpack(result, analysis, execution_id)
        elif analysis.unpacking_strategy == "wrap_in_entity":
            return cls._handle_wrap_in_entity(result, analysis, execution_id)
        else:
            raise ValueError(f"Unknown unpacking strategy: {analysis.unpacking_strategy}")
    
    @classmethod
    def _handle_single_entity(
        cls, 
        result: Any, 
        analysis: ReturnAnalysis, 
        execution_id: UUID
    ) -> UnpackingResult:
        """Handle single entity returns."""
        return UnpackingResult(
            primary_entities=[result],
            container_entity=None,
            metadata={
                "unpacking_type": "single_entity",
                "execution_id": str(execution_id),
                "original_pattern": analysis.pattern.value
            }
        )
    
    @classmethod
    def _handle_sequence_unpack(
        cls, 
        result: Any, 
        analysis: ReturnAnalysis, 
        execution_id: UUID
    ) -> UnpackingResult:
        """Handle tuple/list unpacking."""
        entities = analysis.entities
        
        return UnpackingResult(
            primary_entities=entities,
            container_entity=None,
            metadata={
                "unpacking_type": "sequence",
                "sequence_type": "tuple" if isinstance(result, tuple) else "list",
                "length": len(entities),
                "execution_id": str(execution_id),
                "positions": list(range(len(entities))),
                "original_pattern": analysis.pattern.value
            }
        )
    
    @classmethod
    def _handle_dict_unpack(
        cls, 
        result: Any, 
        analysis: ReturnAnalysis, 
        execution_id: UUID
    ) -> UnpackingResult:
        """Handle dictionary unpacking with key preservation."""
        entities = analysis.entities
        container_metadata = analysis.container_metadata
        
        return UnpackingResult(
            primary_entities=entities,
            container_entity=None,
            metadata={
                "unpacking_type": "dict",
                "keys": container_metadata.get("keys", []),
                "key_entity_mapping": container_metadata.get("key_entity_mapping", {}),
                "execution_id": str(execution_id),
                "original_pattern": analysis.pattern.value
            }
        )
    
    @classmethod
    def _handle_mixed_unpack(
        cls, 
        result: Any, 
        analysis: ReturnAnalysis, 
        execution_id: UUID
    ) -> UnpackingResult:
        """Handle mixed entity/non-entity containers."""
        entities = analysis.entities
        non_entity_data = analysis.non_entity_data
        container_metadata = analysis.container_metadata
        
        # Create a container entity to hold non-entity data
        container_entity = None
        if non_entity_data:
            container_entity = cls._create_container_entity(
                non_entity_data, container_metadata, execution_id
            )
        
        return UnpackingResult(
            primary_entities=entities,
            container_entity=container_entity,
            metadata={
                "unpacking_type": "mixed",
                "container_type": container_metadata.get("container_type"),
                "entity_count": len(entities),
                "non_entity_count": len(non_entity_data),
                "execution_id": str(execution_id),
                "original_pattern": analysis.pattern.value
            }
        )
    
    @classmethod
    def _handle_nested_unpack(
        cls, 
        result: Any, 
        analysis: ReturnAnalysis, 
        execution_id: UUID
    ) -> UnpackingResult:
        """Handle nested structure unpacking."""
        entities = analysis.entities
        non_entity_data = analysis.non_entity_data
        
        # Create container entity to preserve structure
        container_entity = cls._create_nested_container_entity(
            analysis, execution_id
        )
        
        return UnpackingResult(
            primary_entities=entities,
            container_entity=container_entity,
            metadata={
                "unpacking_type": "nested",
                "structure_depth": cls._calculate_structure_depth(result),
                "entity_count": len(entities),
                "execution_id": str(execution_id),
                "original_pattern": analysis.pattern.value
            }
        )
    
    @classmethod
    def _handle_wrap_in_entity(
        cls, 
        result: Any, 
        analysis: ReturnAnalysis, 
        execution_id: UUID
    ) -> UnpackingResult:
        """Handle non-entity returns by wrapping in an entity."""
        # Create a wrapper entity for the non-entity result
        wrapper_entity = cls._create_wrapper_entity(result, execution_id)
        
        return UnpackingResult(
            primary_entities=[wrapper_entity],
            container_entity=None,
            metadata={
                "unpacking_type": "wrapped_non_entity",
                "original_type": str(type(result).__name__),
                "execution_id": str(execution_id),
                "original_pattern": analysis.pattern.value
            }
        )
    
    @classmethod
    def _create_container_entity(
        cls, 
        non_entity_data: Dict[str, Any], 
        container_metadata: Dict[str, Any], 
        execution_id: UUID
    ) -> Entity:
        """Create a container entity to hold non-entity data."""
        # Create simple fields for the container
        container_fields = {**non_entity_data, "execution_id": str(execution_id)}
        
        ContainerEntity = create_dynamic_entity_class(
            "ContainerEntity",
            container_fields
        )
        
        container_entity = ContainerEntity()
        return container_entity
    
    @classmethod
    def _create_nested_container_entity(
        cls, 
        analysis: ReturnAnalysis, 
        execution_id: UUID
    ) -> Entity:
        """Create entity to preserve nested structure metadata."""
        # Create entity to hold structure metadata
        structure_fields = {
            "entity_count": len(analysis.entities),
            "execution_id": str(execution_id),
            "structure_type": "nested"
        }
        
        StructureEntity = create_dynamic_entity_class(
            "NestedStructureEntity",
            structure_fields
        )
        
        structure_entity = StructureEntity()
        return structure_entity
    
    @classmethod
    def _create_wrapper_entity(cls, result: Any, execution_id: UUID) -> Entity:
        """Create wrapper entity for non-entity results."""
        # Create dynamic entity class for the wrapper
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
        
        wrapper_entity = WrapperEntity()
        return wrapper_entity
    
    @classmethod
    def _calculate_structure_depth(cls, obj: Any, current_depth: int = 0) -> int:
        """Calculate the maximum depth of nested structures."""
        if current_depth > 20:  # Prevent infinite recursion
            return current_depth
        
        if isinstance(obj, (list, tuple)):
            if not obj:
                return current_depth
            return max(cls._calculate_structure_depth(item, current_depth + 1) for item in obj)
        elif isinstance(obj, dict):
            if not obj:
                return current_depth
            return max(cls._calculate_structure_depth(value, current_depth + 1) for value in obj.values())
        else:
            return current_depth


class ContainerReconstructor:
    """Utility to reconstruct original container structures from unpacked entities."""
    
    @classmethod
    def reconstruct_from_metadata(
        cls, 
        entities: List[Entity], 
        metadata: Dict[str, Any]
    ) -> Any:
        """Reconstruct original container structure from entities and metadata."""
        unpacking_type = metadata.get("unpacking_type")
        
        if unpacking_type == "single_entity":
            return entities[0] if entities else None
        
        elif unpacking_type == "sequence":
            sequence_type = metadata.get("sequence_type", "list")
            if sequence_type == "tuple":
                return tuple(entities)
            else:
                return list(entities)
        
        elif unpacking_type == "dict":
            keys = metadata.get("keys", [])
            return {keys[i]: entities[i] for i in range(min(len(keys), len(entities)))}
        
        elif unpacking_type in ["mixed", "nested"]:
            # For complex structures, return entities as-is (reconstruction would be complex)
            return entities
        
        elif unpacking_type == "wrapped_non_entity":
            # Extract original value from wrapper
            if entities and hasattr(entities[0], 'wrapped_value'):
                return getattr(entities[0], 'wrapped_value', entities[0])
            return entities[0] if entities else None
        
        else:
            return entities