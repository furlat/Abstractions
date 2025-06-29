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
import hashlib
from functools import partial

from abstractions.ecs.entity import Entity, EntityRegistry, build_entity_tree, find_modified_entities, FunctionExecution, ConfigEntity
from abstractions.ecs.ecs_address_parser import EntityReferenceResolver, InputPatternClassifier  
from abstractions.ecs.functional_api import create_composite_entity, resolve_data_with_tracking, create_composite_entity_with_pattern_detection
import concurrent.futures


def is_top_level_config_entity(param_type: Optional[Type]) -> bool:
    """Detect ConfigEntity only at function signature top-level."""
    if param_type is None:
        return False
    return ConfigEntity.is_config_entity_type(param_type)


class FunctionSignatureCache:
    """Separate caches for input and output models to prevent collisions."""
    
    _input_cache: Dict[str, Tuple[Optional[Type[Entity]], str]] = {}   # input_hash → (input_model, pattern)
    _output_cache: Dict[str, Tuple[Type[Entity], str]] = {}            # output_hash → (output_model, pattern)
    
    @classmethod
    def get_or_create_input_model(cls, func: Callable, function_name: str) -> Tuple[Optional[Type[Entity]], str]:
        """Cache input signature → input entity model + execution pattern."""
        input_hash = cls._hash_input_signature(func)
        
        if input_hash in cls._input_cache:
            return cls._input_cache[input_hash]
        
        # Create input model with ConfigEntity exclusion
        input_model = create_entity_from_function_signature_enhanced(func, "Input", function_name)
        
        # Determine if this function uses ConfigEntity pattern
        sig = signature(func)
        type_hints = get_type_hints(func)
        has_config_entity = any(
            is_top_level_config_entity(type_hints.get(param.name, Any))
            for param in sig.parameters.values()
        )
        
        pattern = "config_entity_pattern" if has_config_entity else "standard_pattern"
        
        # Handle case where all parameters are ConfigEntity (no input model needed)
        if not input_model.model_fields or all(
            field_name in ['ecs_id', 'live_id', 'created_at', 'forked_at', 
                          'previous_ecs_id', 'lineage_id', 'old_ids', 'old_ecs_id',
                          'root_ecs_id', 'root_live_id', 'from_storage', 
                          'untyped_data', 'attribute_source']
            for field_name in input_model.model_fields.keys()
        ):
            input_model = None  # No input entity needed for pure ConfigEntity functions
        
        cls._input_cache[input_hash] = (input_model, pattern)
        return input_model, pattern
    
    @classmethod  
    def get_or_create_output_model(cls, func: Callable, function_name: str) -> Tuple[Type[Entity], str]:
        """Cache output signature → output entity model + return pattern."""
        output_hash = cls._hash_output_signature(func)
        
        if output_hash in cls._output_cache:
            return cls._output_cache[output_hash]
        
        output_model = create_entity_from_function_signature_enhanced(func, "Output", function_name)
        
        # Analyze return type for pattern classification
        type_hints = get_type_hints(func)
        return_type = type_hints.get('return', Any)
        
        pattern = cls._classify_return_pattern(return_type)
        
        cls._output_cache[output_hash] = (output_model, pattern)
        return output_model, pattern
    
    @classmethod
    def _hash_input_signature(cls, func: Callable) -> str:
        """Create hash of input signature for caching."""
        sig = signature(func)
        type_hints = get_type_hints(func)
        
        # Include parameter names, types, and defaults
        sig_parts = []
        for param in sig.parameters.values():
            param_type = type_hints.get(param.name, 'Any')
            default = 'NO_DEFAULT' if param.default is param.empty else str(param.default)
            sig_parts.append(f"{param.name}:{param_type}:{default}")
        
        signature_str = '|'.join(sorted(sig_parts))
        return hashlib.md5(signature_str.encode()).hexdigest()
    
    @classmethod
    def _hash_output_signature(cls, func: Callable) -> str:
        """Create hash of output signature for caching."""
        type_hints = get_type_hints(func)
        return_type = type_hints.get('return', 'Any')
        return hashlib.md5(str(return_type).encode()).hexdigest()
    
    @classmethod
    def _classify_return_pattern(cls, return_type: Type) -> str:
        """Classify return pattern for output processing."""
        # Basic classification - can be enhanced with ReturnTypeAnalyzer integration
        if hasattr(return_type, '__origin__') and return_type.__origin__ is tuple:
            return "tuple_return"
        elif hasattr(return_type, '__origin__') and return_type.__origin__ in [list, List]:
            return "list_return"
        elif hasattr(return_type, '__origin__') and return_type.__origin__ in [dict, Dict]:
            return "dict_return"
        else:
            return "single_return"
    
    @classmethod
    def clear_cache(cls):
        """Clear both caches (useful for testing)."""
        cls._input_cache.clear()
        cls._output_cache.clear()
    
    @classmethod
    def get_cache_stats(cls) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "input_cache_size": len(cls._input_cache),
            "output_cache_size": len(cls._output_cache),
            "total_cached_functions": len(set(cls._input_cache.keys()) | set(cls._output_cache.keys()))
        }


def create_entity_from_function_signature_enhanced(
    func: Callable,
    entity_type: str,  # "Input" or "Output"
    function_name: str
) -> Type[Entity]:
    """Enhanced to exclude top-level ConfigEntity parameters from input entity creation."""
    
    sig = signature(func)
    type_hints = get_type_hints(func)
    field_definitions: Dict[str, Any] = {}
    
    if entity_type == "Input":
        type_hints.pop('return', None)
        
        for param in sig.parameters.values():
            param_type = type_hints.get(param.name, Any)
            
            # NEW: Skip ONLY top-level ConfigEntity parameters
            if is_top_level_config_entity(param_type):
                continue  # Exclude from auto-generated input entity
                
            # Include everything else (including nested ConfigEntities)
            if param.default is param.empty:
                field_definitions[param.name] = (param_type, ...)
            else:
                field_definitions[param.name] = (param_type, param.default)
    
    elif entity_type == "Output":
        # Handle return type (unchanged)
        return_type = type_hints.get('return', Any)
        if isinstance(return_type, type) and issubclass(return_type, BaseModel):
            for field_name, field_info in return_type.model_fields.items():
                field_type = return_type.__annotations__.get(field_name, Any)
                if hasattr(field_info, 'default') and field_info.default is not ...:
                    field_definitions[field_name] = (field_type, field_info.default)
                else:
                    field_definitions[field_name] = (field_type, ...)
        else:
            field_definitions['result'] = (return_type, ...)
    
    # Create Entity subclass using create_model
    entity_class_name = f"{function_name}{entity_type}Entity"
    EntityClass = create_model(
        entity_class_name,
        __base__=Entity,
        __module__=func.__module__,
        **field_definitions
    )
    EntityClass.__qualname__ = f"{function_name}.{entity_class_name}"
    return EntityClass


@dataclass
class FunctionMetadata:
    """Enhanced metadata with ConfigEntity and caching support."""
    name: str
    signature_str: str
    docstring: Optional[str]
    is_async: bool
    original_function: Callable
    
    # Entity classes (input may be None for pure ConfigEntity functions)
    input_entity_class: Optional[Type[Entity]]
    output_entity_class: Type[Entity]
    
    # NEW: Pattern classifications from separate caches
    input_pattern: str   # "config_entity_pattern" | "standard_pattern"
    output_pattern: str  # "single_return" | "tuple_return" | etc.
    
    # For future Modal Sandbox integration
    serializable_signature: Dict[str, Any]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # NEW: ConfigEntity support flags
    uses_config_entity: bool = field(init=False)
    config_entity_types: List[Type[ConfigEntity]] = field(default_factory=list, init=False)
    
    def __post_init__(self):
        """Initialize ConfigEntity support flags."""
        self.uses_config_entity = self.input_pattern == "config_entity_pattern"
        
        if self.uses_config_entity:
            # Extract ConfigEntity types from function signature
            sig = signature(self.original_function)
            type_hints = get_type_hints(self.original_function)
            
            for param in sig.parameters.values():
                param_type = type_hints.get(param.name, Any)
                if is_top_level_config_entity(param_type):
                    self.config_entity_types.append(param_type)


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
        """Enhanced registration with separate signature caching."""
        
        def decorator(func: Callable) -> Callable:
            # Validate function has proper type hints
            type_hints = get_type_hints(func)
            if 'return' not in type_hints:
                raise ValueError(f"Function {func.__name__} must have return type hint")
            
            # Use separate signature caching
            input_entity_class, input_pattern = FunctionSignatureCache.get_or_create_input_model(func, name)
            output_entity_class, output_pattern = FunctionSignatureCache.get_or_create_output_model(func, name)
            
            # Store enhanced metadata
            metadata = FunctionMetadata(
                name=name,
                signature_str=str(signature(func)),
                docstring=getdoc(func),
                is_async=iscoroutinefunction(func),
                original_function=func,
                input_entity_class=input_entity_class,  # May be None for pure ConfigEntity functions
                output_entity_class=output_entity_class,
                input_pattern=input_pattern,              # NEW: Input pattern classification
                output_pattern=output_pattern,            # NEW: Output pattern classification
                serializable_signature=cls._create_serializable_signature(func)
            )
            
            cls._functions[name] = metadata
            
            print(f"✅ Registered '{name}' with ConfigEntity-aware caching (input_pattern: {input_pattern}, output_pattern: {output_pattern})")
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
        input_entity_class: Optional[Type[Entity]],
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
        if input_entity_class is None:
            raise ValueError("Cannot create input entity: input_entity_class is None (pure ConfigEntity function)")
        
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
    def _detect_execution_strategy(cls, kwargs: Dict[str, Any], metadata: FunctionMetadata) -> str:
        """Detect execution strategy based on input composition."""
        
        sig = signature(metadata.original_function)
        type_hints = get_type_hints(metadata.original_function)
        
        # Count parameter types
        entity_params = []
        config_params = []
        primitive_params = {}
        
        # First, classify provided kwargs
        for param_name, value in kwargs.items():
            param_type = type_hints.get(param_name)
            
            if is_top_level_config_entity(param_type):
                config_params.append(param_name)
            elif isinstance(value, Entity) and not isinstance(value, ConfigEntity):
                entity_params.append(param_name)
            else:
                primitive_params[param_name] = value
        
        # Check if function expects ConfigEntity parameters that weren't provided directly
        # but could be created from primitive parameters
        function_expects_config_entity = any(
            is_top_level_config_entity(type_hints.get(param.name))
            for param in sig.parameters.values()
        )
        
        # Strategy determination
        if function_expects_config_entity and (primitive_params or config_params):
            return "single_entity_with_config"  # Use functools.partial approach (works for 1+ entities)
        elif len(entity_params) == 1 and (primitive_params or config_params):
            return "single_entity_with_config"  # Use functools.partial approach
        elif len(entity_params) > 1 and not function_expects_config_entity:
            return "multi_entity_composite"     # Traditional composite entity (no ConfigEntity involved)
        elif len(entity_params) == 1:
            return "single_entity_direct"       # Direct entity processing
        else:
            return "pure_borrowing"             # Address-based borrowing
    
    @classmethod
    async def _execute_async(cls, func_name: str, **kwargs) -> Entity:
        """Execute function with enhanced strategy detection."""
        # Step 1: Get function metadata
        metadata = cls.get_metadata(func_name)
        if not metadata:
            raise ValueError(f"Function '{func_name}' not registered")
        
        # Step 2: Detect execution strategy based on ConfigEntity pattern
        strategy = cls._detect_execution_strategy(kwargs, metadata)
        
        # Step 3: Route to appropriate execution strategy
        if strategy == "single_entity_with_config":
            return await cls._execute_with_partial(metadata, kwargs)
        elif strategy in ["multi_entity_composite", "single_entity_direct"]:
            # Use pattern classification for existing logic
            pattern_type, classification = InputPatternClassifier.classify_kwargs(kwargs)
            if pattern_type in ["pure_transactional", "mixed"]:
                return await cls._execute_transactional(metadata, kwargs, classification)
            else:
                return await cls._execute_borrowing(metadata, kwargs, classification)
        else:  # pure_borrowing
            pattern_type, classification = InputPatternClassifier.classify_kwargs(kwargs)
            return await cls._execute_borrowing(metadata, kwargs, classification)
    
    @classmethod
    async def _execute_with_partial(cls, metadata: FunctionMetadata, kwargs: Dict[str, Any]) -> Entity:
        """Execute using functools.partial for single_entity_with_config pattern."""
        
        # Step 1: Separate entity and config parameters
        sig = signature(metadata.original_function)
        type_hints = get_type_hints(metadata.original_function)
        
        entity_params = {}
        config_params = {}
        primitive_params = {}
        
        for param_name, value in kwargs.items():
            param_type = type_hints.get(param_name)
            
            if is_top_level_config_entity(param_type):
                config_params[param_name] = value
            elif isinstance(value, Entity) and not isinstance(value, ConfigEntity):
                entity_params[param_name] = value
            else:
                primitive_params[param_name] = value
        
        # Step 2: Create or resolve ConfigEntity
        config_entities = {}
        for param_name, param_type in [(p.name, type_hints.get(p.name)) for p in sig.parameters.values()]:
            if is_top_level_config_entity(param_type):
                if param_name in config_params:
                    # Use provided ConfigEntity
                    config_entity = config_params[param_name]
                else:
                    # Create ConfigEntity using the factory pattern
                    config_entity = cls.create_config_entity_from_primitives(
                        metadata.name,
                        primitive_params,
                        expected_config_type=param_type
                    )
                    
                    # Register ConfigEntity in ECS
                    config_entity.promote_to_root()
                
                config_entities[param_name] = config_entity
        
        # Step 3: Create partial function with ConfigEntity
        partial_func = partial(metadata.original_function, **config_entities)
        
        # Step 4: Execute with entities using transactional path
        if entity_params:
            if len(entity_params) == 1:
                # Single entity case - use direct execution with partial
                entity_name, entity_obj = next(iter(entity_params.items()))
                
                # Create temporary metadata for the partial function
                partial_metadata = FunctionMetadata(
                    name=f"{metadata.name}_partial",
                    signature_str=str(signature(partial_func)),
                    docstring=metadata.docstring,
                    is_async=metadata.is_async,
                    original_function=partial_func,
                    input_entity_class=type(entity_obj),
                    output_entity_class=metadata.output_entity_class,
                    input_pattern="single_entity_direct",
                    output_pattern=metadata.output_pattern,
                    serializable_signature={}
                )
                
                return await cls._execute_transactional(partial_metadata, {entity_name: entity_obj}, None)
            else:
                # Multiple entities + ConfigEntity case:
                # 1. Create composite entity from multiple entities
                # 2. Use functools.partial with ConfigEntity
                # 3. Execute partial function with composite entity
                
                # Create composite input entity from multiple entities
                if metadata.input_entity_class:
                    composite_input = await cls._create_input_entity_with_borrowing(
                        metadata.input_entity_class, entity_params, None
                    )
                else:
                    # If no input entity class (pure ConfigEntity function), create a simple wrapper
                    from abstractions.ecs.entity import create_dynamic_entity_class
                    CompositeClass = create_dynamic_entity_class(
                        f"{metadata.name}CompositeInput",
                        {name: (type(entity), entity) for name, entity in entity_params.items()}
                    )
                    composite_input = CompositeClass(**entity_params)
                
                # Register composite entity
                composite_input.promote_to_root()
                
                # Create metadata for partial function with composite input
                partial_metadata = FunctionMetadata(
                    name=f"{metadata.name}_partial",
                    signature_str=str(signature(partial_func)),
                    docstring=metadata.docstring,
                    is_async=metadata.is_async,
                    original_function=partial_func,
                    input_entity_class=type(composite_input),
                    output_entity_class=metadata.output_entity_class,
                    input_pattern="single_entity_direct",
                    output_pattern=metadata.output_pattern,
                    serializable_signature={}
                )
                
                return await cls._execute_transactional(partial_metadata, entity_params, None)
        else:
            # Pure ConfigEntity function - execute directly
            try:
                if metadata.is_async:
                    result = await partial_func()
                else:
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, partial_func)
            except Exception as e:
                await cls._record_execution_failure(None, metadata.name, str(e))
                raise
            
            # Create output entity
            if isinstance(result, Entity):
                output_entity = result
                output_entity.promote_to_root()
            else:
                # Determine the correct field name from the output entity class
                field_names = list(metadata.output_entity_class.model_fields.keys())
                # Exclude entity system fields
                data_fields = [f for f in field_names if f not in {'ecs_id', 'live_id', 'created_at', 'forked_at', 
                                                                  'previous_ecs_id', 'lineage_id', 'old_ids', 'old_ecs_id',
                                                                  'root_ecs_id', 'root_live_id', 'from_storage', 
                                                                  'untyped_data', 'attribute_source'}]
                if data_fields:
                    # Use the first available data field
                    output_entity = metadata.output_entity_class(**{data_fields[0]: result})
                else:
                    raise ValueError(f"No data fields available in output entity class {metadata.output_entity_class.__name__}")
                output_entity.promote_to_root()
            
            # Record execution with ConfigEntity tracking
            await cls._record_function_execution_with_config(
                None, output_entity, metadata.name, list(config_entities.values())
            )
            
            return output_entity
    
    @classmethod
    def create_config_entity_from_primitives(
        cls,
        function_name: str,
        primitive_params: Dict[str, Any],
        expected_config_type: Optional[Type[ConfigEntity]] = None
    ) -> ConfigEntity:
        """Create ConfigEntity dynamically from primitive parameters."""
        from abstractions.ecs.functional_api import borrow_from_address
        
        if expected_config_type:
            # Function expects specific ConfigEntity type - use it directly
            config_data = {}
            for param_name, param_value in primitive_params.items():
                if param_name in expected_config_type.model_fields:
                    if isinstance(param_value, str) and param_value.startswith('@'):
                        # Create the entity first, then borrow
                        config_entity = expected_config_type()
                        borrow_from_address(config_entity, param_value, param_name)
                        return config_entity
                    else:
                        config_data[param_name] = param_value
            return expected_config_type(**config_data)
        else:
            # Create dynamic ConfigEntity class for this function
            class_name = f"{function_name}Config"
            
            # Build field definitions from primitive parameters
            field_definitions = {}
            for param_name, param_value in primitive_params.items():
                param_type = type(param_value)
                field_definitions[param_name] = (param_type, param_value)
            
            # Create ConfigEntity subclass using factory
            ConfigClass = ConfigEntity.create_config_entity_class(
                class_name,
                field_definitions,
                module_name="__callable_registry__"
            )
            
            # Create instance
            return ConfigClass(**primitive_params)
    
    @classmethod
    async def _record_function_execution_with_config(
        cls,
        input_entity: Optional[Entity],
        output_entity: Entity,
        function_name: str,
        config_entities: List[ConfigEntity]
    ) -> None:
        """Record function execution with ConfigEntity tracking."""
        execution_record = FunctionExecution(
            function_name=function_name,
            input_entity_id=input_entity.ecs_id if input_entity else None,
            output_entity_id=output_entity.ecs_id
        )
        execution_record.mark_as_completed("creation")
        execution_record.promote_to_root()
    
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
        
        # Type validation (handle functools.partial objects)
        if hasattr(metadata.original_function, '__annotations__'):
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
        
        # Handle non-entity results - wrap in output entity
        if isinstance(result, dict):
            output_entity = metadata.output_entity_class(**result)
        elif isinstance(result, BaseModel):
            # Extract fields from BaseModel (like AnalysisResult)
            output_entity = metadata.output_entity_class(**result.model_dump())
        else:
            # For primitive results, wrap in a "result" field
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
            'input_entity_class': metadata.input_entity_class.__name__ if metadata.input_entity_class else None,
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
