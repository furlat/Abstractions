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

from abstractions.ecs.entity import Entity, EntityRegistry, build_entity_tree, find_modified_entities, FunctionExecution
from abstractions.ecs.ecs_address_parser import EntityReferenceResolver, InputPatternClassifier  
from abstractions.ecs.functional_api import create_composite_entity, resolve_data_with_tracking, create_composite_entity_with_pattern_detection
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
        kwargs: Dict[str, Any],
        classification: Optional[Dict[str, str]] = None
    ) -> Entity:
        """
        Create input entity using enhanced borrowing patterns.
        
        Leverages:
        - create_composite_entity_with_pattern_detection() from functional_api.py
        - Enhanced pattern classification for mixed inputs
        - Automatic dependency tracking
        """
        # Use enhanced composite entity creation
        if classification:
            # Pattern already classified - use existing create_composite_entity
            input_entity = create_composite_entity(
                entity_class=input_entity_class,
                field_mappings=kwargs,
                register=False
            )
        else:
            # Use pattern-aware creation
            input_entity, _ = create_composite_entity_with_pattern_detection(
                entity_class=input_entity_class,
                field_mappings=kwargs,
                register=False
            )
        
        return input_entity
    
    @classmethod
    async def _execute_async(cls, func_name: str, **kwargs) -> Entity:
        """Execute function with enhanced pattern detection."""
        # Step 1: Get function metadata
        metadata = cls.get_metadata(func_name)
        if not metadata:
            raise ValueError(f"Function '{func_name}' not registered")
        
        # Step 2: Detect execution pattern using clean architecture
        pattern_type, classification = InputPatternClassifier.classify_kwargs(kwargs)
        
        # Step 3: Route to appropriate execution strategy
        if pattern_type in ["pure_transactional", "mixed"]:
            return await cls._execute_transactional(metadata, kwargs, classification)
        else:
            return await cls._execute_borrowing(metadata, kwargs, classification)
    
    @classmethod
    def _has_direct_entity_inputs(cls, kwargs: Dict[str, Any]) -> bool:
        """Check if kwargs contain direct Entity objects (not UUID references)."""
        for value in kwargs.values():
            if isinstance(value, Entity):
                return True
        return False
    
    @classmethod
    async def _execute_borrowing(cls, metadata: FunctionMetadata, kwargs: Dict[str, Any], classification: Optional[Dict[str, str]] = None) -> Entity:
        """Execute using borrowing pattern (data composition)."""
        
        # Create input entity with borrowing (enhanced pattern)
        input_entity = await cls._create_input_entity_with_borrowing(
            metadata.input_entity_class, kwargs, classification
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
    async def _execute_transactional(cls, metadata: FunctionMetadata, kwargs: Dict[str, Any], classification: Optional[Dict[str, str]] = None) -> Entity:
        """
        Execute with complete semantic detection.
        
        This implements the enhanced pattern with object identity-based semantic analysis:
        1. Prepare isolated execution environment with object tracking
        2. Execute function with isolated entities
        3. Finalize with semantic detection using object identity
        """
        
        # Step 1: Prepare isolated execution environment with object identity tracking
        execution_kwargs, original_entities, execution_copies, object_identity_map = await cls._prepare_transactional_inputs(kwargs)
        
        # Step 2: Execute function with isolated entities
        try:
            if metadata.is_async:
                result = await metadata.original_function(**execution_kwargs)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: metadata.original_function(**execution_kwargs))
        except Exception as e:
            await cls._record_execution_failure(None, metadata.name, str(e))
            raise
        
        # Step 3: Finalize with semantic detection using object identity
        return await cls._finalize_transactional_result(result, metadata, object_identity_map)
    
    @classmethod
    async def _prepare_transactional_inputs(cls, kwargs: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Entity], List[Entity], Dict[int, Entity]]:
        """
        Prepare inputs for transactional execution with complete isolation.
        
        Returns:
            Tuple of (execution_kwargs, original_entities, execution_copies, object_identity_map)
        """
        execution_kwargs = {}
        original_entities = []
        execution_copies = []
        object_identity_map = {}  # Maps id(execution_copy) -> original_entity
        
        for param_name, value in kwargs.items():
            if isinstance(value, Entity):
                # Check if entity has diverged from storage
                await cls._check_entity_divergence(value)
                
                # Store original for lineage tracking
                original_entities.append(value)
                
                # Create isolated execution copy
                if value.root_ecs_id:
                    copy = EntityRegistry.get_stored_entity(value.root_ecs_id, value.ecs_id)
                    if copy:
                        execution_copies.append(copy)
                        execution_kwargs[param_name] = copy
                        # Track object identity mapping
                        object_identity_map[id(copy)] = value
                    else:
                        # Entity not in storage, use direct copy with new live_id
                        copy = value.model_copy(deep=True)
                        copy.live_id = uuid4()
                        execution_copies.append(copy)
                        execution_kwargs[param_name] = copy
                        object_identity_map[id(copy)] = value
                else:
                    # Orphan entity, create isolated copy
                    copy = value.model_copy(deep=True)
                    copy.live_id = uuid4()
                    execution_copies.append(copy)
                    execution_kwargs[param_name] = copy
                    object_identity_map[id(copy)] = value
            else:
                # Non-entity values pass through
                execution_kwargs[param_name] = value
        
        return execution_kwargs, original_entities, execution_copies, object_identity_map
    
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
    def _detect_execution_semantic(cls, result: Entity, object_identity_map: Dict[int, Entity]) -> Tuple[str, Optional[Entity]]:
        """
        Core semantic detection using Python object identity.
        
        This is the key innovation - deterministic classification using object identity
        instead of unreliable live_id comparison.
        
        Returns:
            Tuple of (semantic_type, original_entity_if_mutation)
        """
        # Check for MUTATION: result is the same Python object as an execution copy
        result_object_id = id(result)
        if result_object_id in object_identity_map:
            original_entity = object_identity_map[result_object_id]
            return "mutation", original_entity
        
        # Check for DETACHMENT: result has same ecs_id as an entity in input trees
        # but is a different Python object (indicating extraction from tree)
        for original_entity in object_identity_map.values():
            if original_entity.root_ecs_id:
                tree = EntityRegistry.get_stored_tree(original_entity.root_ecs_id)
                if tree and result.ecs_id in tree.nodes:
                    # Entity exists in input tree but is different object -> detachment
                    return "detachment", original_entity
        
        # Default: CREATION - result is a completely new entity
        return "creation", None
    
    @classmethod
    async def _finalize_transactional_result(
        cls, 
        result: Any, 
        metadata: FunctionMetadata, 
        object_identity_map: Dict[int, Entity]
    ) -> Entity:
        """
        Enhanced result finalization with object identity-based semantic detection.
        """
        
        # Type validation
        return_type = metadata.original_function.__annotations__.get('return')
        if return_type and not isinstance(result, return_type):
            raise TypeError(f"Function {metadata.name} returned {type(result)}, expected {return_type}")
        
        # Handle entity results with semantic detection
        if isinstance(result, Entity):
            semantic, original_entity = cls._detect_execution_semantic(result, object_identity_map)
            
            if semantic == "mutation":
                # MUTATION: Function modified input entity in-place
                if original_entity:
                    # Preserve lineage, update ecs_id for versioning
                    result.update_ecs_ids()
                    # Register the updated entity (this should NOT conflict)
                    EntityRegistry.register_entity(result)
                    # Version the original entity to maintain history
                    EntityRegistry.version_entity(original_entity)
                else:
                    # Fallback: treat as creation if we can't find original
                    result.promote_to_root()
                    
            elif semantic == "creation":
                # CREATION: Function created completely new entity
                result.promote_to_root()
                
            elif semantic == "detachment":
                # DETACHMENT: Function extracted child from parent tree
                result.detach()
                # Version the parent entity to reflect the change
                if original_entity:
                    EntityRegistry.version_entity(original_entity)
            
            return result
        
        # Wrap non-entity results in output entity
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
        """Record function execution with enhanced tracking."""
        # Create FunctionExecution entity for audit trail
        execution_record = FunctionExecution(
            function_name=function_name,
            input_entity_id=input_entity.ecs_id,
            output_entity_id=output_entity.ecs_id
        )
        execution_record.mark_as_completed("creation")  # Default semantic
        execution_record.promote_to_root()
    
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
