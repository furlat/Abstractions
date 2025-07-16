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
from typing import get_origin, get_args
import typing
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
        sibling_groups: List[List[int]],  # Groups of entity indices that are siblings
        force_unpack: bool = False  # Whether force unpacking was used
    ):
        self.pattern = pattern
        self.entity_count = entity_count
        self.entities = entities
        self.non_entity_data = non_entity_data
        self.unpacking_strategy = unpacking_strategy
        self.container_metadata = container_metadata
        self.sibling_groups = sibling_groups
        self.force_unpack = force_unpack


class ReturnTypeAnalyzer:
    """Sophisticated analyzer for function return patterns."""
    
    @classmethod
    def analyze_return(cls, result: Any, force_unpack: bool = False) -> ReturnAnalysis:
        """
        Analyze function return and determine comprehensive unpacking strategy.
        
        Args:
            result: The function return value to analyze
            force_unpack: If True, force unpacking for containers (default: False)
            
        Returns:
            ReturnAnalysis with complete classification and unpacking strategy
        """
        # Step 1: Initial pattern classification
        pattern = cls.classify_return_pattern(result)
        
        # Step 2: Extract entities and metadata
        entities, non_entity_data, container_metadata = cls._extract_entities_and_metadata(result, pattern)
        
        # Step 3: Determine unpacking strategy
        unpacking_strategy = cls._determine_unpacking_strategy(pattern, len(entities), result, force_unpack)
        
        # Step 4: Identify sibling groups (entities that should be linked)
        sibling_groups = cls._identify_sibling_groups(result, entities, pattern)
        
        return ReturnAnalysis(
            pattern=pattern,
            entity_count=len(entities),
            entities=entities,
            non_entity_data=non_entity_data,
            unpacking_strategy=unpacking_strategy,
            container_metadata=container_metadata,
            sibling_groups=sibling_groups,
            force_unpack=force_unpack
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
            # Check for nested entities first
            elif cls._has_nested_entities(result):
                return ReturnPattern.NESTED_STRUCTURE
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
            # Check for nested entities first
            elif cls._has_nested_entities(result):
                return ReturnPattern.NESTED_STRUCTURE
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
                extracted_items = []
                for i, item in enumerate(obj):
                    extracted_items.append(_recursive_extract(item, f"{path}[{i}]"))
                return extracted_items
            elif isinstance(obj, dict):
                extracted_dict = {}
                for k, v in obj.items():
                    extracted_dict[k] = _recursive_extract(v, f"{path}.{k}")
                return extracted_dict
            else:
                # Store non-entity data with path
                key = f"data_{path}" if path else f"data_{len(non_entity_data)}"
                non_entity_data[key] = obj
                return f"ref_{key}"
        
        container_metadata["extracted_structure"] = _recursive_extract(result)
        return entities, non_entity_data, container_metadata
    
    @classmethod
    def _determine_unpacking_strategy(cls, pattern: ReturnPattern, entity_count: int, original_result: Any = None, force_unpack: bool = False) -> str:
        """
        Determine the appropriate unpacking strategy.
        
        Args:
            pattern: The return pattern classification
            entity_count: Number of entities in the result
            original_result: The original result value
            force_unpack: If True, force unpacking for containers (default: False)
            
        Returns:
            String indicating the unpacking strategy
            
        Design:
            - Default behavior: Only unpack Tuple[Entity, Entity] (safe by default)
            - Force unpacking: Allow explicit unpacking of containers when requested
            - Core principle: Never unpack to atomic data, only to pure entities
        """
        if pattern == ReturnPattern.SINGLE_ENTITY:
            return "none"  # No unpacking needed
        elif pattern == ReturnPattern.TUPLE_ENTITIES:
            # Only tuple of pure entities gets unpacked by default
            return "sequence_unpack"
        elif force_unpack and pattern in [ReturnPattern.LIST_ENTITIES, ReturnPattern.DICT_ENTITIES, ReturnPattern.NESTED_STRUCTURE]:
            # Explicit force unpacking for containers
            if pattern == ReturnPattern.LIST_ENTITIES:
                return "sequence_unpack"
            elif pattern == ReturnPattern.DICT_ENTITIES:
                return "dict_unpack"
            elif pattern == ReturnPattern.NESTED_STRUCTURE:
                return "nested_unpack"
        elif pattern == ReturnPattern.NON_ENTITY and original_result is not None:
            # Handle empty containers - wrap them instead of unpacking
            return "wrap_in_entity"
        else:
            # Default: wrap everything else in container entities
            # This includes: LIST_ENTITIES, DICT_ENTITIES, MIXED_CONTAINER, NESTED_STRUCTURE
            return "wrap_in_entity"
    
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
        """Check if result contains entities in nested structures (containers within containers)."""
        def _check_for_nested_containers(obj, depth=0):
            if depth > 10:  # Same limit as existing ECS code
                return False
            
            if isinstance(obj, (list, tuple)):
                # Check if any item in this container is also a container that contains entities
                for item in obj:
                    if isinstance(item, (list, tuple, dict)):
                        if _has_entities_inside(item):
                            return True
                    # Also check recursively for deeper nesting
                    if _check_for_nested_containers(item, depth + 1):
                        return True
            elif isinstance(obj, dict):
                # Check if any value in this dict is a container that contains entities
                for value in obj.values():
                    if isinstance(value, (list, tuple, dict)):
                        if _has_entities_inside(value):
                            return True
                    # Also check recursively for deeper nesting
                    if _check_for_nested_containers(value, depth + 1):
                        return True
            
            return False
        
        def _has_entities_inside(container):
            """Check if a container directly contains entities."""
            if isinstance(container, (list, tuple)):
                return any(isinstance(item, Entity) for item in container)
            elif isinstance(container, dict):
                return any(isinstance(value, Entity) for value in container.values())
            return False
        
        return _check_for_nested_containers(result)
    
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
    
    @classmethod
    def analyze_type_signature(cls, return_type: Any, force_unpack: bool = False) -> Dict[str, Any]:
        """
        Analyze function return type signature for registration-time analysis.
        
        This method analyzes the type annotation at registration time to determine
        unpacking capabilities and expected entity counts.
        
        Args:
            return_type: The function's return type annotation
            force_unpack: If True, force unpacking for containers (default: False)
            
        Returns:
            Dict containing analysis metadata for function registration
        """
        
        
        metadata = {
            "pattern": "unknown",
            "supports_unpacking": False,
            "expected_entity_count": 1,
            "has_entities": False,
            "has_non_entities": False,
            "container_type": None,
            "element_types": [],
            "is_complex": False
        }
        
        # Handle None or Any return types
        if return_type is None or return_type == typing.Any:
            metadata["pattern"] = "non_entity"
            metadata["has_non_entities"] = True
            return metadata
        
        # Get origin and args for generic types
        origin = get_origin(return_type)
        args = get_args(return_type)
        
        # Analyze based on type structure
        if origin is tuple:
            metadata["pattern"] = "tuple_return"
            metadata["container_type"] = "tuple"
            metadata["element_types"] = list(args) if args else []
            metadata["expected_entity_count"] = len(args) if args else 0
            metadata["supports_unpacking"] = len(args) > 1 if args else False
            
            # Analyze tuple elements for entity content
            if args:
                pure_entity_count = 0
                container_count = 0
                non_entity_count = 0
                
                for arg_type in args:
                    if cls._is_entity_type_annotation(arg_type):
                        pure_entity_count += 1
                        metadata["has_entities"] = True
                    elif cls._is_entity_container_type(arg_type):
                        # List[Entity], Dict[str, Entity], etc. are containers - no unpacking
                        container_count += 1
                        metadata["has_entities"] = True
                        metadata["has_non_entities"] = True  # Container is treated as non-entity for unpacking
                    else:
                        non_entity_count += 1
                        metadata["has_non_entities"] = True
                
                # Only unpack if ALL elements are pure entities
                if container_count == 0 and non_entity_count == 0:
                    metadata["expected_entity_count"] = pure_entity_count
                    metadata["supports_unpacking"] = pure_entity_count > 1
                else:
                    # Has containers or non-entities - create unified entity
                    metadata["expected_entity_count"] = 1
                    metadata["supports_unpacking"] = False
                    
                metadata["is_complex"] = (pure_entity_count + container_count) > 0 and (container_count + non_entity_count) > 0
        
        elif origin in (list, typing.List):
            metadata["pattern"] = "list_return"
            metadata["container_type"] = "list"
            metadata["supports_unpacking"] = force_unpack  # Only unpack if explicitly requested
            metadata["expected_entity_count"] = -1 if force_unpack else 1  # Unknown if unpacking, 1 if wrapping
            
            if args:
                element_type = args[0]
                metadata["element_types"] = [element_type]
                
                if cls._is_entity_type_annotation(element_type):
                    metadata["has_entities"] = True
                else:
                    metadata["has_non_entities"] = True
        
        elif origin in (dict, typing.Dict):
            metadata["pattern"] = "dict_return"
            metadata["container_type"] = "dict"
            metadata["supports_unpacking"] = force_unpack  # Only unpack if explicitly requested
            metadata["expected_entity_count"] = -1 if force_unpack else 1  # Unknown if unpacking, 1 if wrapping
            
            if len(args) >= 2:
                key_type, value_type = args[0], args[1]
                metadata["element_types"] = [key_type, value_type]
                
                if cls._is_entity_type_annotation(value_type):
                    metadata["has_entities"] = True
                else:
                    metadata["has_non_entities"] = True
        
        elif origin is Union:
            # Handle Union types (including Optional)
            metadata["pattern"] = "union_return"
            metadata["is_complex"] = True
            
            # Analyze union members
            entity_count = 0
            non_entity_count = 0
            
            for arg_type in args:
                if arg_type == type(None):
                    continue  # Skip None type in Optional
                elif cls._is_entity_type_annotation(arg_type):
                    entity_count += 1
                    metadata["has_entities"] = True
                else:
                    non_entity_count += 1
                    metadata["has_non_entities"] = True
            
            metadata["expected_entity_count"] = max(entity_count, 1)
        
        else:
            # Single return type
            if cls._is_entity_type_annotation(return_type):
                metadata["pattern"] = "single_entity"
                metadata["has_entities"] = True
                metadata["expected_entity_count"] = 1
            else:
                metadata["pattern"] = "non_entity"
                metadata["has_non_entities"] = True
                metadata["expected_entity_count"] = 0
        
        return metadata
    
    @classmethod
    def _is_entity_type_annotation(cls, type_annotation: Any) -> bool:
        """Check if a type annotation represents an Entity type."""
        # Entity is already imported at top level
        
        try:
            # Handle direct Entity subclass
            if (isinstance(type_annotation, type) and 
                issubclass(type_annotation, Entity)):
                return True
            
            # Handle string annotations
            if isinstance(type_annotation, str):
                return "Entity" in type_annotation
            
            # Handle forward references and other complex types
            if hasattr(type_annotation, '__name__'):
                return "Entity" in type_annotation.__name__
            
            return False
        except (TypeError, AttributeError):
            return False

    @classmethod
    def _is_entity_container_type(cls, type_annotation: Any) -> bool:
        """Check if a type annotation represents a container of Entity types (List[Entity], Dict[str, Entity], etc.)."""
        try:
            origin = get_origin(type_annotation)
            args = get_args(type_annotation)
            
            if origin in (list, typing.List):
                # List[Entity] -> check if element type is Entity
                return len(args) > 0 and cls._is_entity_type_annotation(args[0])
            elif origin in (dict, typing.Dict):
                # Dict[str, Entity] -> check if value type is Entity
                return len(args) > 1 and cls._is_entity_type_annotation(args[1])
            elif origin is tuple:
                # Tuple[Entity, ...] -> check if any element is Entity
                return any(cls._is_entity_type_annotation(arg) for arg in args)
            
            return False
        except (TypeError, AttributeError):
            return False