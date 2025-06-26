"""
Entity-Native Callable Registry: Pure Entity System Integration

This implements the design document's vision of entity-native function execution
using all our proven patterns:
- Entity factories with create_model
- String addressing via @uuid.field syntax
- Entity borrowing with borrow_from_address()
- Automatic dependency discovery via build_entity_tree()
- Immutable execution via get_stored_entity()
- Complete provenance via attribute_source
"""

from typing import Dict, Any, Callable, Optional, List, Union, get_type_hints, Type, Set, Tuple
from pydantic import create_model, BaseModel
from inspect import signature, iscoroutinefunction, getdoc
from dataclasses import dataclass, field
from datetime import datetime, timezone
import asyncio
from uuid import UUID, uuid4

from abstractions.ecs.entity import Entity, EntityRegistry, build_entity_tree, find_modified_entities
from abstractions.ecs.ecs_address_parser import EntityReferenceResolver  
from abstractions.ecs.functional_api import create_composite_entity, resolve_data_with_tracking
import concurrent.futures


@dataclass
class FunctionMetadata:
    """Clean metadata storage - leverages proven dataclass patterns."""
    name: str
    signature_str: str
    docstring: Optional[str]
    is_async: bool
    original_function: Callable
    
    # Dynamic Entity classes created with create_model
    input_entity_class: Type[Entity]
    output_entity_class: Type[Entity]
    
    # For future Modal Sandbox integration
    serializable_signature: Dict[str, Any]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def create_entity_from_function_signature(
    func: Callable,
    entity_type: str,  # "Input" or "Output"  
    function_name: str
) -> Type[Entity]:
    """
    Entity factory using create_model - proven dynamic class creation pattern.
    
    Leverages:
    - Pydantic's create_model for robust dynamic class creation
    - Entity base class for full versioning/registry integration
    - Proper field type preservation (no Any type degradation)
    """
    
    # Step 1: Extract function signature
    sig = signature(func)
    type_hints = get_type_hints(func)
    
    # Step 2: Build field definitions for create_model
    field_definitions: Dict[str, Any] = {}
    
    if entity_type == "Input":
        # Remove return type for input entity
        type_hints.pop('return', None)
        
        for param in sig.parameters.values():
            param_type = type_hints.get(param.name, Any)
            
            if param.default is param.empty:
                # Required field
                field_definitions[param.name] = (param_type, ...)
            else:
                # Optional field with default
                field_definitions[param.name] = (param_type, param.default)
                
    elif entity_type == "Output":
        # Handle return type
        return_type = type_hints.get('return', Any)
        
        if isinstance(return_type, type) and issubclass(return_type, BaseModel):
            # If return type is already a Pydantic model, extract its fields
            for field_name, field_info in return_type.model_fields.items():
                field_type = return_type.__annotations__.get(field_name, Any)
                if hasattr(field_info, 'default') and field_info.default is not ...:
                    field_definitions[field_name] = (field_type, field_info.default)
                else:
                    field_definitions[field_name] = (field_type, ...)
        else:
            # Simple return type
            field_definitions['result'] = (return_type, ...)
    
    # Step 3: Create Entity subclass using create_model
    entity_class_name = f"{function_name}{entity_type}Entity"
    
    EntityClass = create_model(
        entity_class_name,
        __base__=Entity,  # Inherit from our Entity system
        __module__=func.__module__,
        **field_definitions
    )
    
    # Step 4: Set proper qualname for debugging
    EntityClass.__qualname__ = f"{function_name}.{entity_class_name}"
    
    return EntityClass




class CallableRegistry:
    """
    Clean registry using proven dataclass patterns.
    
    No Entity inheritance - pure separation of concerns.
    Leverages all entity system capabilities without over-engineering.
    """
    
    _functions: Dict[str, FunctionMetadata] = {}
    
    @classmethod
    def register(cls, name: str) -> Callable:
        """Register function with entity factory integration."""
        
        def decorator(func: Callable) -> Callable:
            # Validate function has proper type hints
            type_hints = get_type_hints(func)
            if 'return' not in type_hints:
                raise ValueError(f"Function {func.__name__} must have return type hint")
            
            # Create Entity classes using proven factory
            input_entity_class = create_entity_from_function_signature(
                func, "Input", name
            )
            output_entity_class = create_entity_from_function_signature(
                func, "Output", name
            )
            
            # Store clean metadata
            metadata = FunctionMetadata(
                name=name,
                signature_str=str(signature(func)),
                docstring=getdoc(func),
                is_async=iscoroutinefunction(func),
                original_function=func,
                input_entity_class=input_entity_class,
                output_entity_class=output_entity_class,
                serializable_signature=cls._create_serializable_signature(func)
            )
            
            cls._functions[name] = metadata
            
            print(f"✅ Registered '{name}' with entity-native execution")
            return func
        
        return decorator
    
    @classmethod
    def execute(cls, func_name: str, **kwargs) -> Entity:
        """Execute function using entity-native patterns (sync wrapper)."""
        return asyncio.run(cls.aexecute(func_name, **kwargs))
    
    @classmethod
    async def aexecute(cls, func_name: str, **kwargs) -> Entity:
        """Execute function using entity-native patterns (async)."""
        return await cls._execute_async(func_name, **kwargs)
    
    @classmethod
    async def _create_input_entity_with_borrowing(
        cls,
        input_entity_class: Type[Entity],
        kwargs: Dict[str, Any]
    ) -> Entity:
        """
        Create input entity using proven borrowing patterns.
        
        Leverages:
        - create_composite_entity() from functional_api.py
        - borrow_from_address() from entity.py
        - Automatic attribute_source tracking
        """
        
        # Use proven composite entity creation
        input_entity = create_composite_entity(
            entity_class=input_entity_class,
            field_mappings=kwargs,
            register=False  # We'll register it properly below
        )
        
        # Track dependencies (leverages EntityReferenceResolver)
        _, dependencies = resolve_data_with_tracking(kwargs)
        
        return input_entity
    
    @classmethod
    async def _execute_async(cls, func_name: str, **kwargs) -> Entity:
        """
        Execute function with complete entity system integration.
        
        Supports two execution modes:
        1. Borrowing pattern: Uses @uuid.field syntax for data composition
        2. Direct entities: Transactional execution with entity inputs/outputs
        """
        
        # Step 1: Get function metadata
        metadata = cls.get_metadata(func_name)
        if not metadata:
            raise ValueError(f"Function '{func_name}' not registered")
        
        # Step 2: Detect execution mode
        has_entity_inputs = cls._has_direct_entity_inputs(kwargs)
        
        if has_entity_inputs:
            # Use transactional entity execution
            return await cls._execute_transactional(metadata, kwargs)
        else:
            # Use borrowing pattern execution
            return await cls._execute_borrowing(metadata, kwargs)
    
    @classmethod
    def _has_direct_entity_inputs(cls, kwargs: Dict[str, Any]) -> bool:
        """Check if kwargs contain direct Entity objects (not UUID references)."""
        for value in kwargs.values():
            if isinstance(value, Entity):
                return True
        return False
    
    @classmethod
    async def _execute_borrowing(cls, metadata: FunctionMetadata, kwargs: Dict[str, Any]) -> Entity:
        """Execute using borrowing pattern (data composition)."""
        
        # Create input entity with borrowing (proven pattern)
        input_entity = await cls._create_input_entity_with_borrowing(
            metadata.input_entity_class, kwargs
        )
        
        # Register input entity (leverages build_entity_tree)
        input_entity.promote_to_root()
        
        # Create isolated execution copy (proven immutability)
        if not input_entity.root_ecs_id:
            raise ValueError("Input entity missing root_ecs_id")
            
        execution_entity = EntityRegistry.get_stored_entity(
            input_entity.root_ecs_id, input_entity.ecs_id
        )
        
        if not execution_entity:
            raise ValueError("Failed to create isolated execution environment")
        
        # Execute function with entity boundaries
        function_args = execution_entity.model_dump(exclude={
            'ecs_id', 'live_id', 'created_at', 'forked_at', 
            'previous_ecs_id', 'lineage_id', 'old_ids', 'old_ecs_id',
            'root_ecs_id', 'root_live_id', 'from_storage', 
            'untyped_data', 'attribute_source'
        })
        
        try:
            if metadata.is_async:
                result = await metadata.original_function(**function_args)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: metadata.original_function(**function_args))
        except Exception as e:
            await cls._record_execution_failure(input_entity, metadata.name, str(e))
            raise
        
        # Create output entity with proper provenance
        output_entity = await cls._create_output_entity_with_provenance(
            result, metadata.output_entity_class, input_entity, metadata.name
        )
        
        # Register output entity (automatic versioning)
        output_entity.promote_to_root()
        
        # Record function execution relationship
        await cls._record_function_execution(input_entity, output_entity, metadata.name)
        
        return output_entity
    
    @classmethod
    async def _execute_transactional(cls, metadata: FunctionMetadata, kwargs: Dict[str, Any]) -> Entity:
        """
        Execute with transactional entity semantics for direct Entity inputs/outputs.
        
        This implements the pattern described in containerized_callables.md:
        1. Check if input entities have diverged from storage
        2. Create isolated copies for execution
        3. Execute function with full mutation freedom
        4. Validate return type constraints
        5. Register valid results atomically
        """
        
        # Step 1: Pre-execution entity validation and copying
        execution_kwargs, input_entities = await cls._prepare_transactional_inputs(kwargs)
        
        # Step 2: Execute function in isolated environment
        try:
            if metadata.is_async:
                result = await metadata.original_function(**execution_kwargs)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: metadata.original_function(**execution_kwargs))
        except Exception as e:
            await cls._record_execution_failure(None, metadata.name, str(e))
            raise
        
        # Step 3: Post-execution validation and registration
        return await cls._finalize_transactional_result(result, metadata, input_entities)
    
    @classmethod
    async def _prepare_transactional_inputs(cls, kwargs: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Entity]]:
        """
        Prepare inputs for transactional execution.
        
        Returns:
            Tuple of (execution_kwargs, original_input_entities)
        """
        execution_kwargs = {}
        input_entities = []
        
        for param_name, value in kwargs.items():
            if isinstance(value, Entity):
                # Check if entity has diverged from storage
                await cls._check_entity_divergence(value)
                
                # Create isolated copy for execution
                if value.root_ecs_id:
                    execution_copy = EntityRegistry.get_stored_entity(value.root_ecs_id, value.ecs_id)
                    if not execution_copy:
                        # Entity not in storage, use direct copy
                        execution_copy = value.model_copy(deep=True)
                        execution_copy.live_id = uuid4()
                else:
                    # Orphan entity, use direct copy
                    execution_copy = value.model_copy(deep=True)
                    execution_copy.live_id = uuid4()
                
                execution_kwargs[param_name] = execution_copy
                input_entities.append(value)  # Keep original for lineage
            else:
                # Non-entity values pass through directly
                execution_kwargs[param_name] = value
        
        return execution_kwargs, input_entities
    
    @classmethod
    async def _check_entity_divergence(cls, entity: Entity) -> None:
        """
        Check if entity has diverged from its stored version.
        
        If diverged, automatically version the entity to maintain consistency.
        """
        if not entity.root_ecs_id:
            # Orphan entity, no stored version to compare
            return
        
        stored_entity = EntityRegistry.get_stored_entity(entity.root_ecs_id, entity.ecs_id)
        if not stored_entity:
            # Entity not in storage, register it
            if entity.is_root_entity():
                EntityRegistry.register_entity(entity)
            return
        
        # Compare with stored version
        current_tree = build_entity_tree(entity)
        stored_tree = EntityRegistry.get_stored_tree(entity.root_ecs_id)
        
        if stored_tree:
            modified_entities = find_modified_entities(current_tree, stored_tree)
            if modified_entities:
                # Entity has diverged, trigger versioning
                if entity.is_root_entity():
                    EntityRegistry.version_entity(entity)
    
    @classmethod
    async def _finalize_transactional_result(
        cls, 
        result: Any, 
        metadata: FunctionMetadata, 
        input_entities: List[Entity]
    ) -> Entity:
        """
        Finalize transactional execution result.
        
        Validates return type and registers result entity.
        """
        
        # Step 1: Type validation
        return_type = metadata.original_function.__annotations__.get('return')
        if return_type and not isinstance(result, return_type):
            raise TypeError(
                f"Function {metadata.name} returned {type(result)}, "
                f"expected {return_type}"
            )
        
        # Step 2: Handle entity results
        if isinstance(result, Entity):
            # Set up lineage from input entities
            for input_entity in input_entities:
                # Track that result was derived from these inputs
                # This could be enhanced with more sophisticated lineage tracking
                pass
            
            # Register result entity
            if not result.is_root_entity():
                result.promote_to_root()
            else:
                EntityRegistry.register_entity(result)
            
            return result
        
        # Step 3: Wrap non-entity results in entity
        # Create output entity using the pattern from borrowing execution
        output_entity = metadata.output_entity_class(**{"result": result})
        output_entity.promote_to_root()
        
        return output_entity
    
    @classmethod
    async def _create_output_entity_with_provenance(
        cls,
        result: Any,
        output_entity_class: Type[Entity],
        input_entity: Entity,
        function_name: str
    ) -> Entity:
        """
        Create output entity with complete provenance tracking.
        
        Leverages attribute_source system for full audit trails.
        """
        
        # Handle different result types
        if isinstance(result, dict):
            output_entity = output_entity_class(**result)
        elif isinstance(result, BaseModel):
            output_entity = output_entity_class(**result.model_dump())
        else:
            # Single return value - determine the correct field name from the output entity class
            field_names = list(output_entity_class.model_fields.keys())
            # Exclude entity system fields
            data_fields = [f for f in field_names if f not in {'ecs_id', 'live_id', 'created_at', 'forked_at', 
                                                                'previous_ecs_id', 'lineage_id', 'old_ids', 'old_ecs_id',
                                                                'root_ecs_id', 'root_live_id', 'from_storage', 
                                                                'untyped_data', 'attribute_source'}]
            if data_fields:
                # Use the first available data field
                output_entity = output_entity_class(**{data_fields[0]: result})
            else:
                raise ValueError(f"No data fields available in output entity class {output_entity_class.__name__}")
        
        # Set up complete provenance tracking
        for field_name in output_entity.model_fields:
            if field_name not in {'ecs_id', 'live_id', 'created_at', 'forked_at', 
                                 'previous_ecs_id', 'lineage_id', 'old_ids', 'old_ecs_id',
                                 'root_ecs_id', 'root_live_id', 'from_storage', 
                                 'untyped_data', 'attribute_source'}:
                
                field_value = getattr(output_entity, field_name)
                
                # Container-aware provenance (leverages proven patterns)
                if isinstance(field_value, list):
                    output_entity.attribute_source[field_name] = [
                        input_entity.ecs_id for _ in field_value
                    ]
                elif isinstance(field_value, dict):
                    output_entity.attribute_source[field_name] = {
                        str(k): input_entity.ecs_id for k in field_value.keys()
                    }
                else:
                    output_entity.attribute_source[field_name] = input_entity.ecs_id
        
        return output_entity
    
    @classmethod
    async def _record_function_execution(
        cls,
        input_entity: Entity,
        output_entity: Entity, 
        function_name: str
    ) -> None:
        """Record function execution in entity lineage."""
        # Future enhancement: Create FunctionExecution entity
        # For now, provenance is handled through attribute_source
        pass
    
    @classmethod
    async def _record_execution_failure(
        cls,
        input_entity: Optional[Entity],
        function_name: str,
        error_message: str
    ) -> None:
        """Record execution failure for audit trails."""
        # Future enhancement: Create FailedExecution entity
        pass
    
    @classmethod
    async def execute_batch(cls, executions: List[Dict[str, Any]]) -> List[Entity]:
        """Execute multiple functions concurrently."""
        async def execute_single(execution_config: Dict[str, Any]) -> Entity:
            func_name = execution_config.pop('func_name')
            return await cls.aexecute(func_name, **execution_config)
        
        tasks = [execute_single(config.copy()) for config in executions]
        return await asyncio.gather(*tasks)
    
    @classmethod
    def execute_batch_sync(cls, executions: List[Dict[str, Any]]) -> List[Entity]:
        """Execute multiple functions concurrently (sync wrapper)."""
        return asyncio.run(cls.execute_batch(executions))
    
    @classmethod
    def get_metadata(cls, name: str) -> Optional[FunctionMetadata]:
        """Get function metadata."""
        return cls._functions.get(name)
    
    @classmethod
    def list_functions(cls) -> List[str]:
        """List all registered functions."""
        return list(cls._functions.keys())
    
    @classmethod
    def get_function_info(cls, name: str) -> Optional[Dict[str, Any]]:
        """Get detailed function information."""
        metadata = cls._functions.get(name)
        if not metadata:
            return None
            
        return {
            'name': metadata.name,
            'signature': metadata.signature_str,
            'docstring': metadata.docstring,
            'is_async': metadata.is_async,
            'created_at': metadata.created_at,
            'input_entity_class': metadata.input_entity_class.__name__,
            'output_entity_class': metadata.output_entity_class.__name__
        }
    
    @classmethod
    def _create_serializable_signature(cls, func: Callable) -> Dict[str, Any]:
        """Create serializable signature for Modal Sandbox preparation."""
        sig = signature(func)
        type_hints = get_type_hints(func)
        
        return {
            'parameters': {
                param.name: {
                    'type': str(type_hints.get(param.name, 'Any')),
                    'default': str(param.default) if param.default is not param.empty else None,
                    'kind': param.kind.name
                }
                for param in sig.parameters.values()
            },
            'return_type': str(type_hints.get('return', 'Any'))
        }
