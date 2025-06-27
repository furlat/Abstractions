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


class ECSAddressParser:
    """Parser for ECS entity address strings in @uuid.field.subfield format."""
    
    # Pattern: @uuid.field.subfield.etc
    ADDRESS_PATTERN = re.compile(r'^@([a-f0-9\-]{36})\.(.+)$')
    
    @classmethod
    def parse_address(cls, address: str) -> Tuple[UUID, List[str]]:
        """
        Parse an ECS address string into entity ID and field path.
        
        Args:
            address: String like "@uuid.field.subfield"
            
        Returns:
            Tuple of (entity_ecs_id, field_path_list)
            
        Raises:
            ValueError: If address format is invalid
        
        Examples:
            "@f65cf3bd-9392-499f-8f57-dba701f5069c.name" 
            -> (UUID('f65cf3bd-9392-499f-8f57-dba701f5069c'), ['name'])
            
            "@f65cf3bd-9392-499f-8f57-dba701f5069c.record.gpa"
            -> (UUID('f65cf3bd-9392-499f-8f57-dba701f5069c'), ['record', 'gpa'])
        """
        if not isinstance(address, str) or not address.startswith('@'):
            raise ValueError(f"Invalid ECS address format: {address}")
        
        match = cls.ADDRESS_PATTERN.match(address)
        if not match:
            raise ValueError(f"Invalid ECS address format: {address}")
        
        uuid_str, field_path = match.groups()
        
        try:
            entity_id = UUID(uuid_str)
        except ValueError as e:
            raise ValueError(f"Invalid UUID in address {address}: {e}")
        
        # Split field path on dots
        field_parts = field_path.split('.')
        
        return entity_id, field_parts
    
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
        from .entity import EntityRegistry
        
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
            "regular_string" -> False
            "@invalid-uuid.field" -> False
        """
        return isinstance(value, str) and value.startswith('@') and bool(cls.ADDRESS_PATTERN.match(value))
    
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
    """Enhanced resolver that handles entity reference resolution with tracking."""
    
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
    def is_ecs_address(cls, value: str) -> bool:
        """Check if string is ECS address format."""
        return ECSAddressParser.is_ecs_address(value)