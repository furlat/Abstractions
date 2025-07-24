"""
ECS Address Parser: String-based Entity Addressing

This module provides parsing and resolution for ECS entity address strings
in @uuid.field.subfield format, enabling string-based entity references
for the callable registry system.

Features:
- Parse @uuid.field syntax into entity ID and field path
- Resolve addresses to actual values from EntityRegistry
- Validate address format and entity existence
- Support for nested field paths (field.subfield.etc)
"""

import re
import functools
from typing import Tuple, List, Optional, Any, Dict
from uuid import UUID
from abstractions.ecs.entity import Entity, EntityRegistry


class ECSAddressParser:
    """Parser for ECS entity address strings in @uuid.field.subfield format."""
    
    # Pattern: @uuid.field.subfield.etc
    ADDRESS_PATTERN = re.compile(r'^@([a-f0-9\-]{36})\.(.+)$')
    # Pattern for entity-only addresses: @uuid
    ENTITY_ONLY_PATTERN = re.compile(r'^@([a-f0-9\-]{36})$')
    
    # @classmethod
    # def parse_address(cls, address: str) -> Tuple[UUID, List[str]]:
    #     """
    #     Parse an ECS address string into entity ID and field path.
        
    #     Args:
    #         address: String like "@uuid.field.subfield"
            
    #     Returns:
    #         Tuple of (entity_ecs_id, field_path_list)
            
    #     Raises:
    #         ValueError: If address format is invalid
        
    #     Examples:
    #         "@f65cf3bd-9392-499f-8f57-dba701f5069c.name" 
    #         -> (UUID('f65cf3bd-9392-499f-8f57-dba701f5069c'), ['name'])
            
    #         "@f65cf3bd-9392-499f-8f57-dba701f5069c.record.gpa"
    #         -> (UUID('f65cf3bd-9392-499f-8f57-dba701f5069c'), ['record', 'gpa'])
    #     """
    #     if not isinstance(address, str) or not address.startswith('@'):
    #         raise ValueError(f"Invalid ECS address format: {address}")
        
    #     match = cls.ADDRESS_PATTERN.match(address)
    #     if not match:
    #         raise ValueError(f"Invalid ECS address format: {address}")
        
    #     uuid_str, field_path = match.groups()
        
    #     try:
    #         entity_id = UUID(uuid_str)
    #     except ValueError as e:
    #         raise ValueError(f"Invalid UUID in address {address}: {e}")
        
    #     # Split field path on dots
    #     field_parts = field_path.split('.')
        
    #     return entity_id, field_parts
    
    @classmethod
    def parse_address(cls, address: str) -> Tuple[UUID, List[str]]:
        """
        Parse address supporting entity-only format.
        
        Examples:
            "@uuid" → (uuid, [])
            "@uuid.field" → (uuid, ["field"])
            "@uuid.field.subfield" → (uuid, ["field", "subfield"])
        """
        if not isinstance(address, str) or not address.startswith('@'):
            raise ValueError(f"Invalid ECS address format: {address}")
        
        address_content = address[1:]  # Remove @
        
        # Split on first dot to separate UUID from field path
        parts = address_content.split('.', 1)
        
        try:
            entity_id = UUID(parts[0])
        except ValueError as e:
            raise ValueError(f"Invalid UUID in address {address}: {e}")
        
        # Field path (empty if no dots)
        field_path = parts[1].split('.') if len(parts) > 1 else []
        
        return entity_id, field_path
    
    @classmethod
    def resolve_with_tree_navigation(cls, address: str, entity_tree=None) -> Any:
        """
        Enhanced resolution using EntityTree navigation when available.
        
        Args:
            address: ECS address string
            entity_tree: Optional EntityTree for efficient navigation
            
        Returns:
            Resolved value with improved performance
        """
        entity_id, field_path = cls.parse_address(address)
        
        if entity_tree and entity_id in entity_tree.nodes:
            # Use tree navigation for better performance
            entity = entity_tree.nodes[entity_id]
            if entity:
                try:
                    return functools.reduce(getattr, field_path, entity)
                except AttributeError as e:
                    raise ValueError(f"Field path '{'.'.join(field_path)}' not found: {e}")
        
        # Fallback to registry-based resolution
        return cls.resolve_address(address)
    
    @classmethod
    def resolve_address_advanced(cls, address: str) -> Tuple[Any, str]:
        """
        Enhanced address resolution supporting entity and sub-entity references.
        
        Returns:
            Tuple of (resolved_value, resolution_type)
            resolution_type: "entity" | "field_value" | "sub_entity"
        """
        entity_id, field_path = cls.parse_address(address)
        
        # Get root entity
        root_ecs_id = EntityRegistry.ecs_id_to_root_id.get(entity_id)
        if not root_ecs_id:
            raise ValueError(f"Entity {entity_id} not found in registry")
        
        entity = EntityRegistry.get_stored_entity(root_ecs_id, entity_id)
        if not entity:
            raise ValueError(f"Could not retrieve entity {entity_id}")
        
        # Case 1: No field path - return entire entity
        if not field_path:
            return entity, "entity"
        
        # Case 2: Navigate field path
        current_value = entity
        for field_part in field_path:
            if hasattr(current_value, field_part):
                current_value = getattr(current_value, field_part)
            else:
                # Try container navigation
                current_value = cls._navigate_container(current_value, field_part)
                if current_value is None:
                    raise ValueError(f"Cannot navigate to {field_part}")
        
        # Determine resolution type
        if isinstance(current_value, Entity):
            return current_value, "sub_entity"
        else:
            return current_value, "field_value"
    
    @classmethod
    def _navigate_container(cls, container, key_or_index: str) -> Any:
        """Navigate into containers using key or index."""
        # Handle list/tuple indices
        if key_or_index.isdigit() and isinstance(container, (list, tuple)):
            index = int(key_or_index)
            return container[index] if 0 <= index < len(container) else None
        
        # Handle dict keys
        elif isinstance(container, dict):
            return container.get(key_or_index)
        
        return None
    
    @classmethod
    def resolve_address(cls, address: str) -> Any:
        """
        Resolve an ECS address to the actual value.
        
        Args:
            address: String like "@uuid.field.subfield"
            
        Returns:
            The resolved value
            
        Raises:
            ValueError: If entity not found or field access fails
            
        Examples:
            "@f65cf3bd-9392-499f-8f57-dba701f5069c.name" -> "Alice Johnson"
            "@f65cf3bd-9392-499f-8f57-dba701f5069c.record.gpa" -> 3.90
        """
        
        entity_id, field_path = cls.parse_address(address)
        
        # Get entity from registry
        root_ecs_id = EntityRegistry.ecs_id_to_root_id.get(entity_id)
        if not root_ecs_id:
            raise ValueError(f"Entity {entity_id} not found in registry")
        
        entity = EntityRegistry.get_stored_entity(root_ecs_id, entity_id)
        if not entity:
            raise ValueError(f"Could not retrieve entity {entity_id}")
        
        # Navigate field path
        try:
            return functools.reduce(getattr, field_path, entity)
        except AttributeError as e:
            raise ValueError(f"Field path '{'.'.join(field_path)}' not found in entity: {e}")
    
    @classmethod
    def is_ecs_address(cls, value: str) -> bool:
        """
        Check if a string is an ECS address.
        
        Args:
            value: String to check
            
        Returns:
            True if the string is a valid ECS address format
            
        Examples:
            "@f65cf3bd-9392-499f-8f57-dba701f5069c.name" -> True
            "@f65cf3bd-9392-499f-8f57-dba701f5069c" -> True
            "regular_string" -> False
            "@invalid-uuid.field" -> False
        """
        if not isinstance(value, str) or not value.startswith('@'):
            return False
        
        # Check if it matches field address pattern or entity-only pattern
        return bool(cls.ADDRESS_PATTERN.match(value)) or bool(cls.ENTITY_ONLY_PATTERN.match(value))
    
    @classmethod
    def batch_resolve_addresses(cls, addresses: List[str]) -> Dict[str, Any]:
        """
        Resolve multiple ECS addresses efficiently.
        
        Args:
            addresses: List of ECS address strings
            
        Returns:
            Dictionary mapping addresses to resolved values
            
        Raises:
            ValueError: If any address cannot be resolved
        """
        results = {}
        for address in addresses:
            results[address] = cls.resolve_address(address)
        return results
    
    @classmethod
    def validate_address_format(cls, address: str) -> bool:
        """
        Validate address format without resolving.
        
        Args:
            address: ECS address string to validate
            
        Returns:
            True if format is valid (doesn't check if entity exists)
        """
        try:
            cls.parse_address(address)
            return True
        except ValueError:
            return False


class EntityReferenceResolver:
    """Resolver that handles entity reference resolution with comprehensive tracking."""
    
    def __init__(self):
        self.resolved_entities: set[UUID] = set()
        self.resolution_map: Dict[str, UUID] = {}
    
    def resolve_references(self, data: Any) -> Tuple[Any, set[UUID]]:
        """
        Resolve entity references and return both resolved data and entity IDs.
        
        Args:
            data: Data structure potentially containing @uuid.field references
            
        Returns:
            Tuple of (resolved_data, set_of_entity_ecs_ids_used)
        """
        self.resolved_entities.clear()
        self.resolution_map.clear()
        
        resolved_data = self._resolve_recursive(data)
        return resolved_data, self.resolved_entities.copy()
    
    def _resolve_recursive(self, data: Any) -> Any:
        """Recursively resolve references in nested data structures."""
        if isinstance(data, dict):
            return {k: self._resolve_recursive(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._resolve_recursive(v) for v in data]
        elif isinstance(data, tuple):
            return tuple(self._resolve_recursive(v) for v in data)
        elif isinstance(data, str) and ECSAddressParser.is_ecs_address(data):
            return self._resolve_entity_reference(data)
        else:
            return data
    
    def _resolve_entity_reference(self, reference: str) -> Any:
        """Resolve @uuid.attribute syntax and track usage."""
        try:
            entity_id, field_path = ECSAddressParser.parse_address(reference)
            
            # Track that we used this entity
            self.resolved_entities.add(entity_id)
            self.resolution_map[reference] = entity_id
            
            # Resolve the actual value
            return ECSAddressParser.resolve_address(reference)
            
        except Exception as e:
            raise ValueError(f"Failed to resolve '{reference}': {e}") from e
    
    def get_dependency_summary(self) -> Dict[str, Any]:
        """
        Get summary of resolved dependencies.
        
        Returns:
            Dictionary with resolution statistics and mapping
        """
        return {
            "total_entities_referenced": len(self.resolved_entities),
            "entity_ids": list(self.resolved_entities),
            "resolution_mapping": self.resolution_map.copy()
        }


# Functional API for simple usage
def get(address: str) -> Any:
    """
    Functional API to get a value from an entity using ECS address.
    
    Args:
        address: ECS address like "@uuid.field.subfield"
        
    Returns:
        The resolved value
        
    Example:
        value = get("@f65cf3bd-9392-499f-8f57-dba701f5069c.name")
    """
    return ECSAddressParser.resolve_address(address)


def is_address(value: str) -> bool:
    """
    Check if a string is an ECS address.
    
    Args:
        value: String to check
        
    Returns:
        True if the string is a valid ECS address
        
    Example:
        if is_address(some_string):
            resolved = get(some_string)
    """
    return ECSAddressParser.is_ecs_address(value)


def parse(address: str) -> Tuple[UUID, List[str]]:
    """
    Parse an ECS address into components.
    
    Args:
        address: ECS address string
        
    Returns:
        Tuple of (entity_id, field_path)
        
    Example:
        entity_id, fields = parse("@uuid.record.gpa")
    """
    return ECSAddressParser.parse_address(address)


class InputPatternClassifier:
    """Classify input patterns for callable registry."""
    
    @classmethod
    def classify_kwargs(cls, kwargs: Dict[str, Any]) -> Tuple[str, Dict[str, str]]:
        """
        Classify input pattern types.
        
        Returns:
            Tuple of (pattern_type, field_classifications)
            
        Pattern Types:
            - "pure_borrowing": All @uuid.field strings
            - "pure_transactional": All direct Entity objects  
            - "mixed": Combination of both
            - "direct": Only primitive values
        """
        entity_count = 0
        address_count = 0
        direct_count = 0
        
        classification = {}
        
        for key, value in kwargs.items():
            if hasattr(value, 'ecs_id'):  # Duck typing for Entity
                entity_count += 1
                classification[key] = "entity"
            elif isinstance(value, str) and cls.is_ecs_address(value):
                address_count += 1
                classification[key] = "address"
            else:
                direct_count += 1
                classification[key] = "direct"
        
        # Determine pattern type
        if entity_count > 0 and address_count == 0:
            pattern_type = "pure_transactional"
        elif address_count > 0 and entity_count == 0:
            pattern_type = "pure_borrowing"
        elif entity_count > 0 and address_count > 0:
            pattern_type = "mixed"
        else:
            pattern_type = "direct"
        
        return pattern_type, classification
    
    @classmethod
    def classify_kwargs_advanced(cls, kwargs: Dict[str, Any]) -> Tuple[str, Dict[str, Dict[str, Any]]]:
        """
        Advanced classification with detailed metadata.
        
        Returns:
            Tuple of (pattern_type, field_classifications)
            
        field_classifications format:
        {
            "field_name": {
                "type": "entity" | "entity_address" | "sub_entity" | "sub_entity_address" | "direct",
                "resolution_metadata": {...}
            }
        }
        """
        entity_count = 0
        address_count = 0
        sub_entity_count = 0
        direct_count = 0
        
        classification = {}
        
        for key, value in kwargs.items():
            if hasattr(value, 'ecs_id'):  # Duck typing for Entity
                if cls._is_sub_entity(value):
                    sub_entity_count += 1
                    classification[key] = {
                        "type": "sub_entity",
                        "resolution_metadata": {"root_ecs_id": value.root_ecs_id}
                    }
                else:
                    entity_count += 1
                    classification[key] = {
                        "type": "entity", 
                        "resolution_metadata": {"ecs_id": value.ecs_id}
                    }
            elif isinstance(value, str) and cls.is_ecs_address(value):
                try:
                    resolved_value, resolution_type = ECSAddressParser.resolve_address_advanced(value)
                    address_count += 1
                    
                    if resolution_type == "entity":
                        classification[key] = {
                            "type": "entity_address",
                            "resolution_metadata": {"address": value, "resolves_to": "entity"}
                        }
                    elif resolution_type == "sub_entity":
                        classification[key] = {
                            "type": "sub_entity_address", 
                            "resolution_metadata": {"address": value, "resolves_to": "sub_entity"}
                        }
                    else:
                        classification[key] = {
                            "type": "field_address",
                            "resolution_metadata": {"address": value, "resolves_to": "field_value"}
                        }
                except Exception as e:
                    # Fallback to basic address classification
                    classification[key] = {
                        "type": "address",
                        "resolution_metadata": {"address": value, "error": str(e)}
                    }
            else:
                direct_count += 1
                classification[key] = {
                    "type": "direct",
                    "resolution_metadata": {"value": value}
                }
        
        # Determine overall pattern type
        if entity_count > 0 and address_count == 0:
            pattern_type = "pure_transactional"
        elif address_count > 0 and entity_count == 0:
            pattern_type = "pure_borrowing"
        elif entity_count > 0 and address_count > 0:
            pattern_type = "mixed"
        elif sub_entity_count > 0:
            pattern_type = "sub_entity_transactional" 
        else:
            pattern_type = "direct"
        
        return pattern_type, classification
    
    @classmethod
    def _is_sub_entity(cls, entity: Any) -> bool:
        """Check if entity is a sub-entity (has root_ecs_id != ecs_id)."""
        if not hasattr(entity, 'ecs_id') or not hasattr(entity, 'root_ecs_id'):
            return False
        return entity.root_ecs_id is not None and entity.root_ecs_id != entity.ecs_id
    
    @classmethod
    def is_ecs_address(cls, value: str) -> bool:
        """Check if string is ECS address format."""
        return ECSAddressParser.is_ecs_address(value)