"""
Functional API: High-level Entity Data Access

This module provides functional API methods for entity data access,
building on the ECS address parser and borrow functionality.

Features:
- get/put operations using @uuid.field syntax
- Entity creation from mixed value/address mappings
- Batch operations for multiple references
- Integration with borrowing and provenance tracking
"""

from typing import Any, Dict, List, Optional, Union, Type
from .entity import Entity, EntityRegistry
from .ecs_address_parser import ECSAddressParser, EntityReferenceResolver


def get(address: str) -> Any:
    """
    Functional API to get a value from an entity using ECS address.
    
    Args:
        address: ECS address like "@uuid.field.subfield"
        
    Returns:
        The resolved value
        
    Example:
        student_name = get("@f65cf3bd-9392-499f-8f57-dba701f5069c.name")
        gpa = get("@f65cf3bd-9392-499f-8f57-dba701f5069c.record.gpa")
    """
    return ECSAddressParser.resolve_address(address)


def put(address: str, value: Any, borrow: bool = True) -> None:
    """
    Functional API to set a value in an entity using ECS address.
    
    Args:
        address: ECS address like "@uuid.field"
        value: Value to set
        borrow: If True, create borrowing relationship for entity values
        
    Example:
        put("@f65cf3bd-9392-499f-8f57-dba701f5069c.name", "New Name")
        put("@f65cf3bd-9392-499f-8f57-dba701f5069c.gpa", 3.95, borrow=False)
    """
    entity_id, field_path = ECSAddressParser.parse_address(address)
    
    # Get entity from registry  
    root_ecs_id = EntityRegistry.ecs_id_to_root_id.get(entity_id)
    if not root_ecs_id:
        raise ValueError(f"Entity {entity_id} not found in registry")
    
    entity = EntityRegistry.get_live_entity_by_ecs_id(entity_id)  # Get live version for modification
    if not entity:
        raise ValueError(f"Could not retrieve live entity {entity_id}")
    
    # For now, support only single field (first in path)
    field_name = field_path[0]
    
    if borrow and isinstance(value, Entity):
        # Create borrowing relationship
        entity.borrow_attribute_from(value, field_name, field_name)
    else:
        # Direct assignment
        setattr(entity, field_name, value)
        
        # Update attribute_source for provenance
        if isinstance(value, Entity):
            entity.attribute_source[field_name] = value.ecs_id
        else:
            entity.attribute_source[field_name] = None  # New data


def create_entity_from_mapping(entity_class: Type[Entity], mapping: Dict[str, Any]) -> Entity:
    """
    Factory to create entity from mixed value/address mapping.
    
    Args:
        entity_class: Entity class to create
        mapping: Dict with field names and values/addresses
        
    Returns:
        Created entity with borrowed/assigned values
        
    Example:
        analysis_input = create_entity_from_mapping(AnalysisInputEntity, {
            "name": "@student_uuid.name",
            "age": "@student_uuid.age",
            "threshold": 85.0  # Direct value
        })
    """
    instance = entity_class()
    
    for field_name, value in mapping.items():
        if isinstance(value, str) and ECSAddressParser.is_ecs_address(value):
            # Borrow from address
            instance.borrow_from_address(value, field_name)
        else:
            # Direct assignment
            setattr(instance, field_name, value)
            instance.attribute_source[field_name] = None  # New data
    
    return instance


def batch_get(addresses: List[str]) -> Dict[str, Any]:
    """
    Get multiple values using batch resolution.
    
    Args:
        addresses: List of ECS addresses
        
    Returns:
        Dictionary mapping addresses to resolved values
        
    Example:
        results = batch_get([
            "@student_uuid.name",
            "@student_uuid.age", 
            "@record_uuid.gpa"
        ])
    """
    return ECSAddressParser.batch_resolve_addresses(addresses)


def resolve_data_with_tracking(data: Any) -> tuple[Any, set]:
    """
    Resolve entity references in nested data with dependency tracking.
    
    Args:
        data: Data structure potentially containing @uuid.field references
        
    Returns:
        Tuple of (resolved_data, set_of_referenced_entity_ids)
        
    Example:
        input_data = {
            "name": "@student_uuid.name",
            "grades": ["@grade1_uuid.score", "@grade2_uuid.score"],
            "threshold": 85.0
        }
        resolved, dependencies = resolve_data_with_tracking(input_data)
    """
    resolver = EntityReferenceResolver()
    return resolver.resolve_references(data)


def create_composite_entity(
    entity_class: Type[Entity], 
    field_mappings: Dict[str, Union[str, Any]], 
    register: bool = False
) -> Entity:
    """
    Create a composite entity by borrowing from multiple sources with optional registration.
    
    Args:
        entity_class: Entity class to create
        field_mappings: Dict mapping field names to addresses or direct values
        register: If True, promote entity to root and register it
        
    Returns:
        Created composite entity
        
    Example:
        analysis_entity = create_composite_entity(AnalysisInputEntity, {
            "student_name": "@student_uuid.name",
            "student_age": "@student_uuid.age",
            "current_gpa": "@record_uuid.gpa",
            "analysis_date": datetime.now(),
            "threshold": 3.5
        }, register=True)
    """
    # Resolve all address references
    resolved_data, dependencies = resolve_data_with_tracking(field_mappings)
    
    # Create entity with resolved data
    entity = entity_class(**resolved_data)
    
    # Set up proper attribute sources for borrowed fields
    for field_name, original_value in field_mappings.items():
        if isinstance(original_value, str) and ECSAddressParser.is_ecs_address(original_value):
            # Parse to get source entity ID
            entity_id, _ = ECSAddressParser.parse_address(original_value)
            entity.attribute_source[field_name] = entity_id
        else:
            # Direct value
            entity.attribute_source[field_name] = None
    
    # Optionally register the entity
    if register:
        entity.promote_to_root()
    
    return entity


def get_entity_dependencies(entity: Entity) -> Dict[str, Any]:
    """
    Get all entity dependencies for a given entity based on its attribute sources.
    
    Args:
        entity: Entity to analyze
        
    Returns:
        Dictionary with dependency information
        
    Example:
        deps = get_entity_dependencies(analysis_entity)
        # Returns: {
        #     "direct_dependencies": [UUID(...), UUID(...)],
        #     "field_sources": {"name": UUID(...), "age": UUID(...)},
        #     "total_dependencies": 2
        # }
    """
    from uuid import UUID
    
    dependencies = set()
    field_sources = {}
    
    for field_name, source in entity.attribute_source.items():
        if isinstance(source, UUID):
            dependencies.add(source)
            field_sources[field_name] = source
        elif isinstance(source, list):
            for s in source:
                if isinstance(s, UUID):
                    dependencies.add(s)
            field_sources[field_name] = source
        elif isinstance(source, dict):
            for s in source.values():
                if isinstance(s, UUID):
                    dependencies.add(s)
            field_sources[field_name] = source
    
    return {
        "direct_dependencies": list(dependencies),
        "field_sources": field_sources,
        "total_dependencies": len(dependencies)
    }


def validate_addresses(addresses: List[str]) -> Dict[str, bool]:
    """
    Validate multiple ECS addresses without resolving them.
    
    Args:
        addresses: List of addresses to validate
        
    Returns:
        Dictionary mapping addresses to validation results
        
    Example:
        results = validate_addresses([
            "@valid-uuid.field",
            "@invalid-format",
            "@another-valid-uuid.nested.field"
        ])
    """
    results = {}
    for address in addresses:
        results[address] = ECSAddressParser.validate_address_format(address)
    return results


# Convenience functions for common patterns
def borrow_to_new_entity(
    entity_class: Type[Entity], 
    source_address: str, 
    target_field: str
) -> Entity:
    """
    Create a new entity and borrow a single field from an address.
    
    Args:
        entity_class: Class of entity to create
        source_address: ECS address to borrow from
        target_field: Field name in the new entity
        
    Returns:
        New entity with borrowed field
    """
    entity = entity_class()
    entity.borrow_from_address(source_address, target_field)
    return entity


def quick_composite(*address_mappings: Dict[str, str], entity_class: Type[Entity]) -> Entity:
    """
    Quick creation of composite entities with minimal syntax.
    
    Args:
        address_mappings: Field->address mappings
        entity_class: Entity class to create
        
    Returns:
        Composite entity
        
    Example:
        entity = quick_composite(
            {"name": "@student.name", "age": "@student.age"},
            entity_class=AnalysisInputEntity
        )
    """
    combined_mapping = {}
    for mapping in address_mappings:
        combined_mapping.update(mapping)
    
    return create_entity_from_mapping(entity_class, combined_mapping)