"""
Return Type Analyzer: Output Pattern Detection for Callable Registry

This module provides sophisticated analysis of function return values to classify
output patterns and determine appropriate unpacking strategies for multi-entity returns.

Features:
- Classify function returns into 7 patterns (B1-B7)
- Detect entity vs non-entity content in complex containers
- Support for nested structures and mixed content
- Integration with callable registry semantic detection
"""

from typing import Any, Dict, List, Tuple, Union, Optional, Set
from enum import Enum
import inspect
from collections.abc import Sequence, Mapping

from abstractions.ecs.entity import Entity


class ReturnPattern(str, Enum):
    """Classification of function return patterns."""
    SINGLE_ENTITY = "single_entity"           # B1: Single Entity return
    TUPLE_ENTITIES = "tuple_entities"         # B2: Tuple of entities
    LIST_ENTITIES = "list_entities"           # B3: List of entities  
    DICT_ENTITIES = "dict_entities"           # B4: Dict of entities
    MIXED_CONTAINER = "mixed_container"       # B5: Mixed entities + values
    NESTED_STRUCTURE = "nested_structure"    # B6: Nested containers
    NON_ENTITY = "non_entity"                 # B7: Non-entity return (needs wrapping)


class ReturnAnalysis:
    """Complete analysis result for a function return."""
    
    def __init__(
        self,
        pattern: ReturnPattern,
        entity_count: int,
        entities: List[Entity],
        non_entity_data: Dict[str, Any],
        unpacking_strategy: str,
        container_metadata: Dict[str, Any],
        sibling_groups: List[List[int]]  # Groups of entity indices that are siblings
    ):
        self.pattern = pattern
        self.entity_count = entity_count
        self.entities = entities
        self.non_entity_data = non_entity_data
        self.unpacking_strategy = unpacking_strategy
        self.container_metadata = container_metadata
        self.sibling_groups = sibling_groups


class ReturnTypeAnalyzer:
    """Sophisticated analyzer for function return patterns."""
    
    @classmethod
    def analyze_return(cls, result: Any) -> ReturnAnalysis:
        """
        Analyze function return and determine comprehensive unpacking strategy.
        
        Args:
            result: The function return value to analyze
            
        Returns:
            ReturnAnalysis with complete classification and unpacking strategy
        """
        # Step 1: Initial pattern classification
        pattern = cls.classify_return_pattern(result)
        
        # Step 2: Extract entities and metadata
        entities, non_entity_data, container_metadata = cls._extract_entities_and_metadata(result, pattern)
        
        # Step 3: Determine unpacking strategy
        unpacking_strategy = cls._determine_unpacking_strategy(pattern, len(entities), result)
        
        # Step 4: Identify sibling groups (entities that should be linked)
        sibling_groups = cls._identify_sibling_groups(result, entities, pattern)
        
        return ReturnAnalysis(
            pattern=pattern,
            entity_count=len(entities),
            entities=entities,
            non_entity_data=non_entity_data,
            unpacking_strategy=unpacking_strategy,
            container_metadata=container_metadata,
            sibling_groups=sibling_groups
        )
    
    @classmethod
    def classify_return_pattern(cls, result: Any) -> ReturnPattern:
        """
        Classify the return pattern according to B1-B7 classification.
        
        Args:
            result: Function return value
            
        Returns:
            ReturnPattern enum value
        """
        # B1: Single Entity
        if isinstance(result, Entity):
            return ReturnPattern.SINGLE_ENTITY
        
        # B7: Non-entity primitives
        if cls._is_primitive_type(result):
            return ReturnPattern.NON_ENTITY
        
        # B2: Tuple of entities
        if isinstance(result, tuple):
            if all(isinstance(item, Entity) for item in result):
                return ReturnPattern.TUPLE_ENTITIES
            elif any(isinstance(item, Entity) for item in result):
                return ReturnPattern.MIXED_CONTAINER
            else:
                return ReturnPattern.NON_ENTITY
        
        # B3: List of entities
        if isinstance(result, list):
            if len(result) == 0:  # Empty list is non-entity
                return ReturnPattern.NON_ENTITY
            elif all(isinstance(item, Entity) for item in result):
                return ReturnPattern.LIST_ENTITIES
            elif any(isinstance(item, Entity) for item in result):
                return ReturnPattern.MIXED_CONTAINER
            else:
                return ReturnPattern.NON_ENTITY
        
        # B4: Dict of entities
        if isinstance(result, dict):
            if len(result) == 0:  # Empty dict is non-entity
                return ReturnPattern.NON_ENTITY
            values = list(result.values())
            if all(isinstance(value, Entity) for value in values):
                return ReturnPattern.DICT_ENTITIES
            elif any(isinstance(value, Entity) for value in values):
                return ReturnPattern.MIXED_CONTAINER
            else:
                return ReturnPattern.NON_ENTITY
        
        # B6: Nested structures - check for nested containers with entities
        if cls._has_nested_entities(result):
            return ReturnPattern.NESTED_STRUCTURE
        
        # Default: treat as non-entity
        return ReturnPattern.NON_ENTITY
    
    @classmethod
    def _extract_entities_and_metadata(
        cls, 
        result: Any, 
        pattern: ReturnPattern
    ) -> Tuple[List[Entity], Dict[str, Any], Dict[str, Any]]:
        """
        Extract all entities and preserve container metadata.
        
        Returns:
            Tuple of (entities_list, non_entity_data, container_metadata)
        """
        entities = []
        non_entity_data = {}
        container_metadata: Dict[str, Any] = {}
        
        if pattern == ReturnPattern.SINGLE_ENTITY:
            entities = [result]
            container_metadata = {"type": "single", "position": 0}
            
        elif pattern == ReturnPattern.TUPLE_ENTITIES:
            entities = list(result)
            container_metadata = {
                "type": "tuple",
                "length": len(result),
                "positions": list(range(len(result)))
            }
            
        elif pattern == ReturnPattern.LIST_ENTITIES:
            entities = list(result)
            container_metadata = {
                "type": "list", 
                "length": len(result),
                "positions": list(range(len(result)))
            }
            
        elif pattern == ReturnPattern.DICT_ENTITIES:
            entities = list(result.values())
            container_metadata = {
                "type": "dict",
                "keys": list(result.keys()),
                "key_entity_mapping": {k: i for i, k in enumerate(result.keys())}
            }
            
        elif pattern == ReturnPattern.MIXED_CONTAINER:
            entities, non_entity_data, container_metadata = cls._extract_from_mixed_container(result)
            
        elif pattern == ReturnPattern.NESTED_STRUCTURE:
            entities, non_entity_data, container_metadata = cls._extract_from_nested_structure(result)
            
        elif pattern == ReturnPattern.NON_ENTITY:
            # No entities to extract
            non_entity_data = {"value": result, "type": str(type(result).__name__)}
            container_metadata = {"type": "primitive"}
        
        return entities, non_entity_data, container_metadata
    
    @classmethod
    def _extract_from_mixed_container(cls, result: Any) -> Tuple[List[Entity], Dict[str, Any], Dict[str, Any]]:
        """Extract entities and non-entities from mixed containers."""
        entities = []
        non_entity_data = {}
        container_metadata: Dict[str, Any] = {"type": "mixed"}
        
        if isinstance(result, (list, tuple)):
            container_metadata["container_type"] = "sequence"
            container_metadata["length"] = len(result)
            entity_positions: List[int] = []
            non_entity_positions: List[int] = []
            
            for i, item in enumerate(result):
                if isinstance(item, Entity):
                    entities.append(item)
                    entity_positions.append(i)
                else:
                    non_entity_data[f"position_{i}"] = item
                    non_entity_positions.append(i)
            
            container_metadata["entity_positions"] = entity_positions
            container_metadata["non_entity_positions"] = non_entity_positions
                    
        elif isinstance(result, dict):
            container_metadata["container_type"] = "mapping"
            entity_keys: List[Any] = []
            non_entity_keys: List[Any] = []
            
            for key, value in result.items():
                if isinstance(value, Entity):
                    entities.append(value)
                    entity_keys.append(key)
                else:
                    non_entity_data[f"key_{key}"] = value
                    non_entity_keys.append(key)
            
            container_metadata["entity_keys"] = entity_keys
            container_metadata["non_entity_keys"] = non_entity_keys
        
        return entities, non_entity_data, container_metadata
    
    @classmethod
    def _extract_from_nested_structure(cls, result: Any) -> Tuple[List[Entity], Dict[str, Any], Dict[str, Any]]:
        """Extract entities from deeply nested structures."""
        entities = []
        non_entity_data = {}
        container_metadata = {"type": "nested", "structure": cls._analyze_nested_structure(result)}
        
        def _recursive_extract(obj, path=""):
            if isinstance(obj, Entity):
                entities.append(obj)
                return f"entity_{len(entities)-1}"
            elif isinstance(obj, (list, tuple)):
                return [_recursive_extract(item, f"{path}[{i}]") for i, item in enumerate(obj)]
            elif isinstance(obj, dict):
                return {k: _recursive_extract(v, f"{path}.{k}") for k, v in obj.items()}
            else:
                # Store non-entity data with path
                key = f"data_{path}" if path else f"data_{len(non_entity_data)}"
                non_entity_data[key] = obj
                return f"ref_{key}"
        
        container_metadata["extracted_structure"] = _recursive_extract(result)
        return entities, non_entity_data, container_metadata
    
    @classmethod
    def _determine_unpacking_strategy(cls, pattern: ReturnPattern, entity_count: int, original_result: Any = None) -> str:
        """Determine the appropriate unpacking strategy."""
        if pattern == ReturnPattern.SINGLE_ENTITY:
            return "none"  # No unpacking needed
        elif pattern in [ReturnPattern.TUPLE_ENTITIES, ReturnPattern.LIST_ENTITIES]:
            return "sequence_unpack"
        elif pattern == ReturnPattern.DICT_ENTITIES:
            return "dict_unpack"
        elif pattern == ReturnPattern.MIXED_CONTAINER:
            return "mixed_unpack"
        elif pattern == ReturnPattern.NESTED_STRUCTURE:
            return "nested_unpack"
        elif pattern == ReturnPattern.NON_ENTITY and original_result is not None:
            # Handle empty containers as their container type, not wrapped
            if isinstance(original_result, (list, tuple)):
                return "sequence_unpack"
            elif isinstance(original_result, dict):
                return "dict_unpack"
            else:
                return "wrap_in_entity"
        else:
            return "wrap_in_entity"  # Non-entity results get wrapped
    
    @classmethod
    def _identify_sibling_groups(
        cls, 
        result: Any, 
        entities: List[Entity], 
        pattern: ReturnPattern
    ) -> List[List[int]]:
        """
        Identify groups of entities that should be marked as siblings.
        
        Returns:
            List of lists, where each inner list contains indices of entities that are siblings
        """
        if len(entities) <= 1:
            return []
        
        # For most patterns, all entities returned together are siblings
        if pattern in [
            ReturnPattern.TUPLE_ENTITIES,
            ReturnPattern.LIST_ENTITIES, 
            ReturnPattern.DICT_ENTITIES,
            ReturnPattern.MIXED_CONTAINER
        ]:
            return [list(range(len(entities)))]
        
        # For nested structures, analyze the structure to group siblings
        elif pattern == ReturnPattern.NESTED_STRUCTURE:
            return cls._analyze_nested_siblings(result, entities)
        
        return []
    
    @classmethod
    def _analyze_nested_siblings(cls, result: Any, entities: List[Entity]) -> List[List[int]]:
        """Analyze nested structures to identify sibling groups."""
        # For now, simple implementation: entities at the same nesting level are siblings
        # This could be enhanced to be more sophisticated based on structure analysis
        return [list(range(len(entities)))]
    
    @classmethod
    def _is_primitive_type(cls, value: Any) -> bool:
        """Check if value is a primitive type."""
        return isinstance(value, (int, float, str, bool, type(None)))
    
    @classmethod
    def _has_nested_entities(cls, result: Any) -> bool:
        """Check if result contains entities in nested structures using ECS pattern."""
        def _check_recursive(obj, depth=0):
            if depth > 10:  # Same limit as existing ECS code
                return False
            if isinstance(obj, Entity):
                return depth > 0  # Entity at depth > 0 means nested structure
            elif isinstance(obj, (list, tuple)):
                return any(_check_recursive(item, depth+1) for item in obj)
            elif isinstance(obj, dict):
                return any(_check_recursive(value, depth+1) for value in obj.values())
            return False
        
        return _check_recursive(result)
    
    @classmethod
    def _analyze_nested_structure(cls, result: Any) -> Dict[str, Any]:
        """Analyze the structure of nested containers."""
        def _structure_analysis(obj, depth=0):
            if depth > 10:
                return {"type": "max_depth_reached"}
            
            if isinstance(obj, Entity):
                return {"type": "entity", "class": obj.__class__.__name__}
            elif isinstance(obj, list):
                return {
                    "type": "list",
                    "length": len(obj),
                    "items": [_structure_analysis(item, depth+1) for item in obj[:3]]  # Sample first 3
                }
            elif isinstance(obj, tuple):
                return {
                    "type": "tuple", 
                    "length": len(obj),
                    "items": [_structure_analysis(item, depth+1) for item in obj[:3]]
                }
            elif isinstance(obj, dict):
                sample_keys = list(obj.keys())[:3]
                return {
                    "type": "dict",
                    "size": len(obj),
                    "sample_items": {k: _structure_analysis(obj[k], depth+1) for k in sample_keys}
                }
            else:
                return {"type": "primitive", "python_type": str(type(obj).__name__)}
        
        return _structure_analysis(result)


class QuickPatternDetector:
    """Fast pattern detection for common cases."""
    
    @classmethod
    def quick_classify(cls, result: Any) -> Optional[ReturnPattern]:
        """Quick classification for common patterns."""
        if isinstance(result, Entity):
            return ReturnPattern.SINGLE_ENTITY
        elif isinstance(result, tuple) and all(isinstance(x, Entity) for x in result):
            return ReturnPattern.TUPLE_ENTITIES
        elif isinstance(result, list) and all(isinstance(x, Entity) for x in result):
            return ReturnPattern.LIST_ENTITIES
        elif isinstance(result, dict) and all(isinstance(v, Entity) for v in result.values()):
            return ReturnPattern.DICT_ENTITIES
        elif ReturnTypeAnalyzer._is_primitive_type(result):
            return ReturnPattern.NON_ENTITY
        else:
            return None  # Needs full analysis