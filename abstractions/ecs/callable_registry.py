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
import time
from uuid import UUID, uuid4
import hashlib
from functools import partial

from abstractions.ecs.entity import Entity, EntityRegistry, build_entity_tree, find_modified_entities, FunctionExecution, ConfigEntity, create_dynamic_entity_class, EntityFactory
from abstractions.ecs.ecs_address_parser import EntityReferenceResolver, InputPatternClassifier, ECSAddressParser
from abstractions.ecs.functional_api import create_composite_entity, resolve_data_with_tracking, create_composite_entity_with_pattern_detection, borrow_from_address
from abstractions.ecs.return_type_analyzer import ReturnTypeAnalyzer, QuickPatternDetector
from abstractions.ecs.entity_unpacker import EntityUnpacker, ContainerReconstructor
import concurrent.futures

def extract_entity_uuids(kwargs: Dict[str, Any]) -> Tuple[List[UUID], List[str]]:
    """Extract UUIDs and types from kwargs for event tracking."""
    entity_ids = []
    entity_types = []
    
    for param_name, value in kwargs.items():
        if isinstance(value, Entity):
            entity_ids.append(value.ecs_id)
            entity_types.append(type(value).__name__)
        elif isinstance(value, str) and value.startswith('@'):
            # Extract UUID from address format
            try:
                uuid_part = value[1:].split('.')[0]
                entity_ids.append(UUID(uuid_part))
                entity_types.append("AddressReference")
            except (ValueError, IndexError):
                pass
    
    return entity_ids, entity_types

def extract_config_entity_uuids(config_entities: List[Any]) -> List[UUID]:
    """Extract UUIDs from config entities."""
    return [ce.ecs_id for ce in config_entities if hasattr(ce, 'ecs_id')]

def generate_execution_context() -> Dict[str, Any]:
    """Generate execution context with UUID tracking."""
    execution_id = uuid4()
    execution_start_time = time.time()
    
    return {
        'execution_id': execution_id,
        'start_time': execution_start_time,
        'entity_tracking': {
            'input_entities': [],
            'created_entities': [],
            'modified_entities': [],
            'config_entities': []
        }
    }

def propagate_execution_context(context: Dict[str, Any], event_data: Dict[str, Any]):
    """Propagate execution context to events."""
    event_data['execution_id'] = context['execution_id']
    event_data['execution_duration_ms'] = (time.time() - context['start_time']) * 1000
    
    # Merge entity tracking
    event_data.update(context['entity_tracking'])

# Event system imports for automatic event emission
from abstractions.events.events import emit_events, ProcessingEvent, ProcessedEvent
from abstractions.events.callable_events import (
    FunctionExecutionEvent, FunctionExecutedEvent,
    StrategyDetectionEvent, StrategyDetectedEvent,
    InputPreparationEvent, InputPreparedEvent,
    SemanticAnalysisEvent, SemanticAnalyzedEvent,
    UnpackingEvent, UnpackedEvent,
    ResultFinalizationEvent, ResultFinalizedEvent,
    ConfigEntityCreationEvent, ConfigEntityCreatedEvent,
    PartialExecutionEvent, PartialExecutedEvent,
    TransactionalExecutionEvent, TransactionalExecutedEvent,
    ValidationEvent, ValidatedEvent
)


def is_top_level_config_entity(param_type: Optional[Type]) -> bool:
    """Detect ConfigEntity only at function signature top-level."""
    if param_type is None:
        return False
    return ConfigEntity.is_config_entity_type(param_type)


class FunctionSignatureCache:
    """Separate caches for input and output models to prevent collisions."""
    
    _input_cache: Dict[str, Tuple[Optional[Type[Entity]], str]] = {}   # input_hash → (input_model, pattern)
    _output_cache: Dict[str, Tuple[Type[Entity], str, Dict[str, Any]]] = {}  # output_hash → (output_model, pattern, analysis)
    
    @classmethod
    def get_or_create_input_model(cls, func: Callable, function_name: str) -> Tuple[Optional[Type[Entity]], str]:
        """Cache input signature → input entity model + execution pattern."""
        input_hash = cls._hash_input_signature(func)
        
        if input_hash in cls._input_cache:
            return cls._input_cache[input_hash]
        
        # Create input model with ConfigEntity exclusion
        input_model = create_entity_from_function_signature(func, "Input", function_name)
        
        # Determine if this function uses ConfigEntity pattern
        sig = signature(func)
        type_hints = get_type_hints(func)
        has_config_entity = any(
            is_top_level_config_entity(type_hints.get(param.name, None))
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
    def get_or_create_output_model(cls, func: Callable, function_name: str) -> Tuple[Type[Entity], str, Dict[str, Any]]:
        """Cache output signature → output entity model + comprehensive return analysis."""
        
        output_hash = cls._hash_output_signature(func)
        
        if output_hash in cls._output_cache:
            # Cache hit - return cached 3-tuple result
            return cls._output_cache[output_hash]
        
        output_model = create_entity_from_function_signature(func, "Output", function_name)
        
        # Use Phase 2 return analysis
        type_hints = get_type_hints(func)
        return_type = type_hints.get('return', None)
        if return_type is None:
            raise ValueError(
                f"Function '{func.__name__}' missing return type annotation. "
                f"All registered functions must have proper type hints for return values. "
                f"Please add a return type annotation like '-> Entity' or '-> List[Entity]'."
            )
        analysis = QuickPatternDetector.analyze_type_signature(return_type)
        
        # Extract pattern from analysis (always present)
        pattern = analysis["pattern"]
        
        result = (output_model, pattern, analysis)
        cls._output_cache[output_hash] = result
        return result
    
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
    def clear_cache(cls):
        """Clear both caches to ensure consistent format."""
        cls._input_cache.clear()
        cls._output_cache.clear()
        print("🔄 Cache cleared - enforcing consistent 3-tuple format")
    
    @classmethod
    def get_cache_stats(cls) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "input_cache_size": len(cls._input_cache),
            "output_cache_size": len(cls._output_cache),
            "total_cached_functions": len(set(cls._input_cache.keys()) | set(cls._output_cache.keys()))
        }


def create_entity_from_function_signature(
    func: Callable,
    entity_type: str,  # "Input" or "Output"
    function_name: str
) -> Type[Entity]:
    """
    Entity factory using create_model with ConfigEntity exclusion.
    
    Leverages:
    - Pydantic's create_model for robust dynamic class creation
    - Entity base class for full versioning/registry integration
    - Proper field type preservation (no Any type degradation)
    - ConfigEntity exclusion for proper separation of concerns
    """
    
    sig = signature(func)
    type_hints = get_type_hints(func)
    field_definitions: Dict[str, Any] = {}
    
    if entity_type == "Input":
        type_hints.pop('return', None)
        
        for param in sig.parameters.values():
            param_type = type_hints.get(param.name, None)
            if param_type is None:
                raise ValueError(
                    f"Function '{func.__name__}' parameter '{param.name}' missing type annotation. "
                    f"All registered functions must have complete type hints."
                )
            
            # Skip ONLY top-level ConfigEntity parameters
            if is_top_level_config_entity(param_type):
                continue  # Exclude from auto-generated input entity
                
            # Include everything else (including nested ConfigEntities)
            if param.default is param.empty:
                field_definitions[param.name] = (param_type, ...)
            else:
                field_definitions[param.name] = (param_type, param.default)
    
    elif entity_type == "Output":
        # Handle return type (unchanged)
        return_type = type_hints.get('return', None)
        if return_type is None:
            raise ValueError(
                f"Function '{func.__name__}' missing return type annotation. "
                f"All registered functions must have proper type hints for return values."
            )
        if isinstance(return_type, type) and issubclass(return_type, BaseModel):
            for field_name, field_info in return_type.model_fields.items():
                field_type = return_type.__annotations__.get(field_name, Any)
                if hasattr(field_info, 'default') and field_info.default is not ...:
                    field_definitions[field_name] = (field_type, field_info.default)
                else:
                    field_definitions[field_name] = (field_type, ...)
        else:
            field_definitions['result'] = (return_type, ...)
    
    # Create Entity subclass using EntityFactory
    entity_class_name = f"{function_name}{entity_type}Entity"
    EntityClass = EntityFactory.create_entity_class(
        entity_class_name,
        field_definitions,
        base_class=Entity,
        module_name=func.__module__,
        qualname_parent=function_name
    )
    return EntityClass


@dataclass
class FunctionMetadata:
    """Function metadata with ConfigEntity and Phase 2 return analysis support."""
    name: str
    signature_str: str
    docstring: Optional[str]
    is_async: bool
    original_function: Callable
    
    # Entity classes (input may be None for pure ConfigEntity functions)
    input_entity_class: Optional[Type[Entity]]
    output_entity_class: Type[Entity]
    
    # Pattern classifications from separate caches
    input_pattern: str   # "config_entity_pattern" | "standard_pattern"
    output_pattern: str  # "single_return" | "tuple_return" | etc.
    
    # Phase 2 return analysis integration
    return_analysis: Dict[str, Any] = field(default_factory=dict)        # Full Phase 2 analysis metadata
    supports_unpacking: bool = False                                     # Unpacking capability flag
    expected_output_count: int = 1                                       # Expected entity count
    
    # For future Modal Sandbox integration
    serializable_signature: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # ConfigEntity support flags
    uses_config_entity: bool = field(init=False)
    config_entity_types: List[Type[ConfigEntity]] = field(default_factory=list, init=False)
    
    def __post_init__(self):
        """Initialize ConfigEntity support flags and Phase 2 analysis metadata."""
        self.uses_config_entity = self.input_pattern == "config_entity_pattern"
        
        # Initialize ConfigEntity types
        if self.uses_config_entity:
            # Extract ConfigEntity types from function signature
            sig = signature(self.original_function)
            type_hints = get_type_hints(self.original_function)
            
            for param in sig.parameters.values():
                param_type = type_hints.get(param.name, None)
                if param_type is None:
                    raise ValueError(
                        f"Function '{self.original_function.__name__}' parameter '{param.name}' missing type annotation. "
                        f"All registered functions must have complete type hints."
                    )
                if is_top_level_config_entity(param_type):
                    self.config_entity_types.append(param_type)
        
        # Initialize Phase 2 return analysis fields
        if self.return_analysis:
            self.supports_unpacking = self.return_analysis.get('supports_unpacking', False)
            expected_count = self.return_analysis.get('expected_entity_count', 1)
            # Handle -1 (unknown count) by defaulting to 1
            self.expected_output_count = max(expected_count, 1) if expected_count != -1 else 1




class CallableRegistry:
    """
    Clean registry using proven dataclass patterns.
    
    No Entity inheritance - pure separation of concerns.
    Leverages all entity system capabilities without over-engineering.
    """
    
    _functions: Dict[str, FunctionMetadata] = {}
    
    # Clear cache on startup to ensure consistent 3-tuple format
    @classmethod
    def _ensure_cache_consistency(cls):
        """Ensure cache uses consistent 3-tuple format only."""
        # Clear any mixed format cache entries from previous versions
        FunctionSignatureCache.clear_cache()
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._ensure_cache_consistency()
    
    @classmethod
    def register(cls, name: str) -> Callable:
        """Register functions with comprehensive signature caching and analysis."""
        
        def decorator(func: Callable) -> Callable:
            # Validate function has proper type hints
            type_hints = get_type_hints(func)
            if 'return' not in type_hints:
                raise ValueError(f"Function {func.__name__} must have return type hint")
            
            # ✅ Use signature caching with Phase 2 return analysis
            input_entity_class, input_pattern = FunctionSignatureCache.get_or_create_input_model(func, name)
            output_entity_class, output_pattern, return_analysis = FunctionSignatureCache.get_or_create_output_model(func, name)
            
            # Extract unpacking metadata from Phase 2 analysis
            supports_unpacking = return_analysis.get('supports_unpacking', False)
            expected_output_count = return_analysis.get('expected_entity_count', 1)
            
            # Fix: Handle -1 (unknown count) properly for multi-entity patterns
            if expected_output_count == -1:
                # For list/tuple/dict patterns, -1 means multiple entities - use 2 to trigger unpacking
                if output_pattern in ['list_return', 'tuple_return', 'dict_return']:
                    expected_output_count = 2  # Trigger multi-entity path
                else:
                    expected_output_count = 1  # Single entity fallback
            
            # Store enhanced metadata
            metadata = FunctionMetadata(
                name=name,
                signature_str=str(signature(func)),
                docstring=getdoc(func),
                is_async=iscoroutinefunction(func),
                original_function=func,
                input_entity_class=input_entity_class,  # May be None for pure ConfigEntity functions
                output_entity_class=output_entity_class,
                input_pattern=input_pattern,              # Input pattern classification
                output_pattern=output_pattern,            # Output pattern classification
                return_analysis=return_analysis,          # Full Phase 2 analysis metadata
                supports_unpacking=supports_unpacking,    # Unpacking capability flag
                expected_output_count=expected_output_count,  # Expected entity count
                serializable_signature=cls._create_serializable_signature(func)
            )
            
            cls._functions[name] = metadata
            
            print(f"Registered '{name}' with return analysis (input_pattern: {input_pattern}, output_pattern: {output_pattern}, unpacking: {supports_unpacking})")
            return func
        
        return decorator
    
    @classmethod
    def execute(cls, func_name: str, **kwargs) -> Union[Entity, List[Entity]]:
        """Execute function using entity-native patterns (sync wrapper)."""
        return asyncio.run(cls.aexecute(func_name, **kwargs))
    
    @classmethod
    @emit_events(
        creating_factory=lambda cls, func_name, **kwargs: FunctionExecutionEvent(
            process_name="function_execution",
            function_name=func_name,
            execution_strategy=None,  # Will be determined during execution
            input_entity_ids=extract_entity_uuids(kwargs)[0],
            input_entity_types=extract_entity_uuids(kwargs)[1],
            input_parameter_count=len(kwargs),
            input_entity_count=len([v for v in kwargs.values() if isinstance(v, Entity)]),
            input_primitive_count=len([v for v in kwargs.values() if not isinstance(v, Entity)]),
            is_async=cls.get_metadata(func_name).is_async if cls.get_metadata(func_name) else False,
            uses_config_entity=cls.get_metadata(func_name).uses_config_entity if cls.get_metadata(func_name) else False,
            expected_output_count=cls.get_metadata(func_name).expected_output_count if cls.get_metadata(func_name) else 1,
            execution_pattern="determining"
        ),
        created_factory=lambda result, cls, func_name, **kwargs: FunctionExecutedEvent(
            process_name="function_execution",
            function_name=func_name,
            execution_successful=True,
            input_entity_ids=extract_entity_uuids(kwargs)[0],
            output_entity_ids=[result.ecs_id] if isinstance(result, Entity) else [e.ecs_id for e in result] if isinstance(result, list) else [],
            created_entity_ids=[],  # Will be populated during execution
            modified_entity_ids=[],  # Will be populated during execution
            config_entity_ids=[],  # Will be populated during execution
            execution_record_id=None,  # Will be populated during execution
            execution_strategy="completed",
            output_entity_count=1 if isinstance(result, Entity) else len(result) if isinstance(result, list) else 0,
            semantic_results=[],  # Will be populated during execution
            execution_duration_ms=0.0,  # Will be calculated during execution
            total_events_generated=0,  # Will be calculated during execution
            execution_id=None  # Will be populated during execution
        )
    )
    async def aexecute(cls, func_name: str, **kwargs) -> Union[Entity, List[Entity]]:
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
    @emit_events(
        creating_factory=lambda cls, kwargs, metadata: StrategyDetectionEvent(
            process_name="strategy_detection",
            function_name=metadata.name,
            input_entity_ids=extract_entity_uuids(kwargs)[0],
            input_entity_types=extract_entity_uuids(kwargs)[1],
            config_entity_ids=[],  # Will be populated during detection
            entity_type_mapping={str(uuid): type_name for uuid, type_name in zip(*extract_entity_uuids(kwargs))},
            input_types={name: type(value).__name__ for name, value in kwargs.items()},
            entity_count=len([v for v in kwargs.values() if isinstance(v, Entity)]),
            config_entity_count=0,  # Will be calculated
            primitive_count=len([v for v in kwargs.values() if not isinstance(v, Entity)]),
            has_metadata=metadata is not None,
            detection_method="signature_analysis"
        ),
        created_factory=lambda result, cls, kwargs, metadata: StrategyDetectedEvent(
            process_name="strategy_detection",
            function_name=metadata.name,
            detection_successful=True,
            input_entity_ids=extract_entity_uuids(kwargs)[0],
            config_entity_ids=[],  # Will be populated
            entity_type_mapping={str(uuid): type_name for uuid, type_name in zip(*extract_entity_uuids(kwargs))},
            detected_strategy=result,
            strategy_reasoning=f"Detected {result} based on input analysis",
            execution_path="determined_from_strategy",
            decision_factors=[],
            confidence_level="high"
        )
    )
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
        
        # Strategy determination based on correct recasting rules
        if len(entity_params) == 1 and not primitive_params and not function_expects_config_entity and not config_params:
            return "single_entity_direct"       # Pure single entity, no recasting needed
        elif len(entity_params) >= 2:
            return "multi_entity_composite"     # 2+ entities (+ anything) → 1 unified entity (highest priority)
        elif function_expects_config_entity or config_params:
            return "single_entity_with_config"  # Config entity handling (after multi-entity check)
        elif len(entity_params) == 1 and primitive_params:
            return "single_entity_with_config"  # 1 entity + primitives → 1 entity + config (primitives become config)
        elif len(entity_params) == 0 and not primitive_params:
            return "no_inputs"                  # No inputs → execute function directly
        else:
            return "pure_borrowing"             # Address-based borrowing and mixed patterns (fallback)
    
    @classmethod
    async def _execute_async(cls, func_name: str, **kwargs) -> Union[Entity, List[Entity]]:
        """Execute function with comprehensive strategy detection and routing."""
        # Step 1: Get function metadata
        metadata = cls.get_metadata(func_name)
        if not metadata:
            raise ValueError(f"Function '{func_name}' not registered")
        
        # Step 2: Detect execution strategy based on ConfigEntity pattern
        strategy = cls._detect_execution_strategy(kwargs, metadata)
        
        # Step 3: Route to appropriate execution strategy
        if strategy == "single_entity_with_config":
            return await cls._execute_with_partial(metadata, kwargs)
        elif strategy == "no_inputs":
            return await cls._execute_no_inputs(metadata)
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
    @emit_events(
        creating_factory=lambda cls, metadata, kwargs: InputPreparationEvent(
            process_name="input_preparation",
            function_name=metadata.name,
            preparation_type="config_creation",
            input_entity_ids=extract_entity_uuids(kwargs)[0],
            entity_count=len([v for v in kwargs.values() if isinstance(v, Entity)]),
            requires_isolation=False,
            requires_config_entity=metadata.uses_config_entity,
            pattern_classification="partial_execution",
            borrowing_operations_needed=0
        ),
        created_factory=lambda result, cls, metadata, kwargs: InputPreparedEvent(
            process_name="input_preparation",
            function_name=metadata.name,
            preparation_successful=True,
            input_entity_ids=extract_entity_uuids(kwargs)[0],
            created_entities=[],  # Will be populated with created entity UUIDs
            config_entities_created=[],  # Will be populated with config entity UUIDs
            execution_copy_ids=[],  # Will be populated with execution copy UUIDs
            borrowed_from_entities=[],  # Will be populated with borrowed entity UUIDs
            object_identity_map_size=0,
            isolation_successful=True,
            borrowing_operations_completed=0,
            preparation_duration_ms=0.0
        )
    )
    async def _execute_with_partial(cls, metadata: FunctionMetadata, kwargs: Dict[str, Any]) -> Union[Entity, List[Entity]]:
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
        
        # Handle explicit ConfigEntity parameters
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
        
        # For "1 entity + primitives" pattern, create dynamic ConfigEntity from primitives
        if len(entity_params) == 1 and primitive_params and not config_entities:
            # Create a dynamic ConfigEntity that includes all primitive parameters
            dynamic_config = cls.create_config_entity_from_primitives(
                metadata.name,
                primitive_params,
                expected_config_type=None  # Will create dynamic ConfigEntity
            )
            dynamic_config.promote_to_root()
            
            # The partial function should include all primitive parameters directly
            config_entities.update(primitive_params)
        
        # Step 3: Create partial function with ConfigEntity only
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
                await cls._record_execution_failure(None, metadata.name, str(e), None, None)
                raise
            
            # Check if Pure ConfigEntity function needs multi-entity processing
            is_multi_entity = (metadata.supports_unpacking and
                              (metadata.expected_output_count > 1 or
                               metadata.output_pattern in ['list_return', 'tuple_return', 'dict_return']))

            if is_multi_entity:
                # Route to multi-entity processing path (same logic as transactional path)
                execution_id = uuid4()
                return await cls._finalize_multi_entity_result(
                    result, metadata, {}, None, execution_id  # Empty object_identity_map for Pure ConfigEntity
                )
            else:
                # Continue with existing single-entity path
                if isinstance(result, Entity):
                    output_entity = result
                    output_entity.promote_to_root()
                else:
                    # Use unified output entity creation method
                    output_entity = cls._create_output_entity_from_result(result, metadata.output_entity_class, metadata.name)
                    output_entity.promote_to_root()
                
                # Record execution with ConfigEntity tracking
                await cls._record_function_execution_with_config(
                    None, output_entity, metadata.name, list(config_entities.values())
                )
                
                return output_entity
    
    @classmethod
    @emit_events(
        creating_factory=lambda cls, function_name, primitive_params, expected_config_type: ConfigEntityCreationEvent(
            process_name="config_entity_creation",
            function_name=function_name,
            source_entity_ids=[],  # Config entities created from primitives
            config_type="dynamic" if expected_config_type is None else "explicit",
            expected_config_class=expected_config_type.__name__ if expected_config_type else None,
            primitive_params_count=len(primitive_params),
            has_expected_type=expected_config_type is not None
        ),
        created_factory=lambda config_entity, cls, function_name, primitive_params, expected_config_type: ConfigEntityCreatedEvent(
            process_name="config_entity_creation",
            function_name=function_name,
            creation_successful=True,
            config_entity_id=config_entity.ecs_id,
            source_entity_ids=[],  # Created from primitives
            config_entity_type=type(config_entity).__name__,
            fields_populated=len(primitive_params),
            registered_in_ecs=True,
            creation_duration_ms=0.0
        )
    )
    def create_config_entity_from_primitives(
        cls,
        function_name: str,
        primitive_params: Dict[str, Any],
        expected_config_type: Optional[Type[ConfigEntity]] = None
    ) -> ConfigEntity:
        """Create ConfigEntity dynamically from primitive parameters."""
        
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
    async def _execute_borrowing(cls, metadata: FunctionMetadata, kwargs: Dict[str, Any], classification: Optional[Dict[str, str]] = None) -> Union[Entity, List[Entity]]:
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
            'untyped_data', 'attribute_source',
            # Phase 4 fields
            'derived_from_function', 'derived_from_execution_id', 
            'sibling_output_entities', 'output_index'
        })
        
        try:
            if metadata.is_async:
                result = await metadata.original_function(**function_args)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: metadata.original_function(**function_args))
        except Exception as e:
            await cls._record_execution_failure(input_entity, metadata.name, str(e), None, None)
            raise
        
        # Check if result needs enhanced processing for multi-entity returns
        is_multi_entity = (metadata.supports_unpacking and 
                          (metadata.expected_output_count > 1 or 
                           metadata.output_pattern in ['list_return', 'tuple_return', 'dict_return']))
        if is_multi_entity:
            # Use enhanced result processing for multi-entity returns
            object_identity_map = {}  # Empty since borrowing path doesn't track object identity the same way
            execution_id = uuid4()
            
            return await cls._finalize_multi_entity_result(
                result, metadata, object_identity_map, input_entity, execution_id
            )
        else:
            # Use traditional single-entity processing
            output_entity = await cls._create_output_entity_with_provenance(
                result, metadata.output_entity_class, input_entity, metadata.name
            )
            
            # Register output entity (automatic versioning)
            output_entity.promote_to_root()
            
            # Record function execution relationship
            await cls._record_basic_execution(input_entity, output_entity, metadata.name)
            
            return output_entity
    
    @classmethod
    @emit_events(
        creating_factory=lambda cls, metadata, kwargs, classification: TransactionalExecutionEvent(
            process_name="transactional_execution",
            function_name=metadata.name,
            isolated_entity_ids=extract_entity_uuids(kwargs)[0],
            execution_copy_ids=[],  # Will be populated during execution
            isolated_entities_count=len([v for v in kwargs.values() if isinstance(v, Entity)]),
            has_object_identity_map=True,
            isolation_successful=True,
            transaction_id=uuid4()
        ),
        created_factory=lambda result, cls, metadata, kwargs, classification: TransactionalExecutedEvent(
            process_name="transactional_execution",
            function_name=metadata.name,
            execution_successful=True,
            isolated_entity_ids=extract_entity_uuids(kwargs)[0],
            output_entity_ids=[result.ecs_id] if isinstance(result, Entity) else [e.ecs_id for e in result] if isinstance(result, list) else [],
            execution_copy_ids=[],  # Will be populated during execution
            output_entities_count=1 if isinstance(result, Entity) else len(result) if isinstance(result, list) else 0,
            semantic_analysis_completed=True,
            transaction_duration_ms=0.0,
            transaction_id=uuid4()
        )
    )
    async def _execute_transactional(cls, metadata: FunctionMetadata, kwargs: Dict[str, Any], classification: Optional[Dict[str, str]] = None) -> Union[Entity, List[Entity]]:
        """
        Enhanced execute with complete semantic detection and Phase 2 unpacking.
        
        This implements the enhanced pattern with object identity-based semantic analysis:
        1. Prepare isolated execution environment with object tracking
        2. Execute function with isolated entities
        3. Finalize with Phase 2 unpacking and semantic detection
        """
        
        # Generate execution ID for tracking
        execution_id = uuid4()
        start_time = time.time()
        
        # Step 1: Prepare isolated execution environment with object identity tracking
        execution_kwargs, original_entities, execution_copies, object_identity_map = await cls._prepare_transactional_inputs(kwargs)
        
        # Extract input entity for tracking (first original entity if available)
        input_entity = original_entities[0] if original_entities else None
        
        # Step 2: Execute function with isolated entities
        try:
            if metadata.is_async:
                result = await metadata.original_function(**execution_kwargs)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: metadata.original_function(**execution_kwargs))
        except Exception as e:
            execution_duration = time.time() - start_time
            await cls._record_execution_failure(input_entity, metadata.name, str(e), execution_id, execution_duration)
            raise
        
        # Step 3: Enhanced finalization with Phase 2 unpacking
        is_multi_entity = (metadata.supports_unpacking and 
                          (metadata.expected_output_count > 1 or 
                           metadata.output_pattern in ['list_return', 'tuple_return', 'dict_return']))
        if is_multi_entity:
            # Use multi-entity result processing for multi-entity returns
            return await cls._finalize_multi_entity_result(
                result, metadata, object_identity_map, input_entity, execution_id
            )
        else:
            # Use single-entity result processing for single-entity returns
            return await cls._finalize_single_entity_result(result, metadata, object_identity_map)
    
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
    @emit_events(
        creating_factory=lambda cls, result, object_identity_map: SemanticAnalysisEvent(
            process_name="semantic_analysis",
            function_name="semantic_analysis",  # Will be passed from context
            input_entity_ids=[e.ecs_id for e in object_identity_map.values()],
            result_entity_ids=[result.ecs_id] if isinstance(result, Entity) else [],
            result_type=type(result).__name__,
            analysis_method="object_identity",
            has_object_identity_map=len(object_identity_map) > 0,
            input_entity_count=len(object_identity_map),
            result_entity_count=1 if isinstance(result, Entity) else 0
        ),
        created_factory=lambda semantic_result, cls, result, object_identity_map: SemanticAnalyzedEvent(
            process_name="semantic_analysis",
            function_name="semantic_analysis",
            analysis_successful=True,
            input_entity_ids=[e.ecs_id for e in object_identity_map.values()],
            result_entity_ids=[result.ecs_id] if isinstance(result, Entity) else [],
            analyzed_entity_ids=[result.ecs_id] if isinstance(result, Entity) else [],
            original_entity_id=semantic_result[1].ecs_id if semantic_result[1] else None,
            semantic_type=semantic_result[0],
            confidence_level="high",
            analysis_duration_ms=0.0,
            entities_analyzed=1
        )
    )
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
    async def _finalize_single_entity_result(
        cls,
        result: Any,
        metadata: FunctionMetadata,
        object_identity_map: Dict[int, Entity]
    ) -> Entity:
        """
        Single-entity result finalization with object identity-based semantic detection.
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
        
        # Handle non-entity results - use unified entity creation method
        output_entity = cls._create_output_entity_from_result(result, metadata.output_entity_class, metadata.name)
        
        output_entity.promote_to_root()
        return output_entity
    
    @classmethod
    @emit_events(
        creating_factory=lambda cls, result, metadata, object_identity_map, input_entity, execution_id: UnpackingEvent(
            process_name="result_unpacking",
            function_name=metadata.name,
            source_entity_ids=[input_entity.ecs_id] if input_entity else [],
            unpacking_pattern=metadata.output_pattern,
            expected_entity_count=metadata.expected_output_count,
            container_type=type(result).__name__,
            supports_unpacking=metadata.supports_unpacking,
            requires_container_entity=True
        ),
        created_factory=lambda unpacked_result, cls, result, metadata, object_identity_map, input_entity, execution_id: UnpackedEvent(
            process_name="result_unpacking",
            function_name=metadata.name,
            unpacking_successful=True,
            source_entity_ids=[input_entity.ecs_id] if input_entity else [],
            unpacked_entity_ids=[e.ecs_id for e in unpacked_result if isinstance(e, Entity)],
            container_entity_id=unpacked_result.container_entity.ecs_id if hasattr(unpacked_result, 'container_entity') and unpacked_result.container_entity else None,
            sibling_entity_ids=[e.ecs_id for e in unpacked_result if isinstance(e, Entity)],
            unpacked_entity_count=len([e for e in unpacked_result if isinstance(e, Entity)]),
            sibling_relationships_created=len([e for e in unpacked_result if isinstance(e, Entity)]) > 1,
            unpacking_duration_ms=0.0
        )
    )
    async def _finalize_multi_entity_result(
        cls,
        result: Any,
        metadata: FunctionMetadata,
        object_identity_map: Dict[int, Entity],
        input_entity: Optional[Entity] = None,
        execution_id: Optional[UUID] = None
    ) -> Union[Entity, List[Entity]]:
        """
        Multi-entity result processing with Phase 2 unpacking integration.
        
        This method integrates the EntityUnpacker to handle multi-entity returns
        while maintaining all existing semantic detection capabilities.
        """
        
        if execution_id is None:
            execution_id = uuid4()
        
        # Step 1: Use EntityUnpacker for sophisticated result analysis
        unpacking_result = ContainerReconstructor.unpack_with_signature_analysis(
            result,
            metadata.return_analysis,
            metadata.output_entity_class,
            execution_id
        )
        
        # Step 2: Process each entity with semantic detection
        final_entities = []
        semantic_results = []
        
        for entity in unpacking_result.primary_entities:
            if isinstance(entity, Entity):
                # Apply semantic detection
                semantic, original_entity = cls._detect_execution_semantic(entity, object_identity_map)
                
                # Apply semantic actions
                processed_entity = await cls._apply_semantic_actions(
                    entity, semantic, original_entity, metadata, execution_id
                )
                
                final_entities.append(processed_entity)
                semantic_results.append(semantic)
            else:
                # Non-entity result, promote to root
                if hasattr(entity, 'promote_to_root'):
                    entity.promote_to_root()
                final_entities.append(entity)
                semantic_results.append("creation")
        
        # Step 3: Handle container entity if unpacking created one
        if unpacking_result.container_entity:
            container = unpacking_result.container_entity
            if hasattr(container, 'promote_to_root'):
                container.promote_to_root()
            # Note: Container is tracking entity, not returned directly
        
        # Step 4: Set up sibling relationships for multi-entity outputs
        if len(final_entities) > 1:
            await cls._setup_sibling_relationships(final_entities, execution_id)
        
        # Step 5: Record multi-entity execution metadata
        await cls._record_multi_entity_execution(
            input_entity, final_entities, metadata.name, execution_id,
            unpacking_result, semantic_results
        )
        
        # Return single entity or list based on unpacking
        return final_entities[0] if len(final_entities) == 1 else final_entities
    
    @classmethod
    async def _apply_semantic_actions(
        cls, 
        entity: Entity, 
        semantic: str, 
        original_entity: Optional[Entity], 
        metadata: FunctionMetadata, 
        execution_id: UUID
    ) -> Entity:
        """Apply semantic actions based on detection result."""
        
        if semantic == "mutation":
            # Handle mutation: preserve lineage, update IDs
            if original_entity:
                entity.update_ecs_ids()
                EntityRegistry.register_entity(entity)
                EntityRegistry.version_entity(original_entity)
            else:
                # Fallback: treat as creation if we can't find original
                entity.promote_to_root()
            
            # Add function execution tracking
            entity.derived_from_function = metadata.name
            entity.derived_from_execution_id = execution_id
            
        elif semantic == "creation":
            # Handle creation: new lineage, function derivation
            entity.derived_from_function = metadata.name
            entity.derived_from_execution_id = execution_id
            entity.promote_to_root()
            
        elif semantic == "detachment":
            # Handle detachment: promote to root, version parent
            entity.detach()
            if original_entity:
                EntityRegistry.version_entity(original_entity)
            
            # Add function execution tracking
            entity.derived_from_function = metadata.name
            entity.derived_from_execution_id = execution_id
        
        return entity
    
    @classmethod
    async def _setup_sibling_relationships(
        cls, 
        entities: List[Entity], 
        execution_id: UUID
    ) -> None:
        """Set up sibling relationships for multi-entity outputs."""
        
        entity_ids = [e.ecs_id for e in entities]
        
        for i, entity in enumerate(entities):
            # Set output index for tuple position tracking
            if hasattr(entity, 'output_index'):
                entity.output_index = i
            
            # Set sibling IDs (all others from same execution)
            if hasattr(entity, 'sibling_output_entities'):
                entity.sibling_output_entities = [
                    eid for j, eid in enumerate(entity_ids) if j != i
                ]
            
            # Ensure derived_from_execution_id is set
            if hasattr(entity, 'derived_from_execution_id'):
                entity.derived_from_execution_id = execution_id
            
            # Re-register entity with updated sibling information
            EntityRegistry.version_entity(entity)
    
    @classmethod
    async def _record_multi_entity_execution(
        cls,
        input_entity: Optional[Entity],
        output_entities: List[Entity],
        function_name: str,
        execution_id: UUID,
        unpacking_result: Any,
        semantic_results: List[str],
        config_entities: Optional[List[Any]] = None,
        execution_duration: float = 0.0
    ) -> FunctionExecution:
        """Record multi-entity function execution with complete Phase 2 metadata."""
        
        execution_record = FunctionExecution(
            ecs_id=execution_id,
            function_name=function_name,
            input_entity_id=input_entity.ecs_id if input_entity else None,
            output_entity_ids=[e.ecs_id for e in output_entities]
        )
        
        # Set enhanced fields after construction
        execution_record.execution_duration = execution_duration
        execution_record.return_analysis = unpacking_result.metadata if hasattr(unpacking_result, 'metadata') else {}
        execution_record.unpacking_metadata = unpacking_result.metadata if hasattr(unpacking_result, 'metadata') else {}
        execution_record.sibling_groups = cls._build_sibling_groups(output_entities)
        execution_record.semantic_classifications = semantic_results
        execution_record.execution_pattern = "enhanced_unified"
        execution_record.was_unpacked = len(output_entities) > 1
        execution_record.original_return_type = str(type(unpacking_result).__name__) if unpacking_result else ""
        execution_record.entity_count_input = 1 if input_entity else 0
        execution_record.entity_count_output = len(output_entities)
        execution_record.config_entity_ids = [c.ecs_id for c in (config_entities or []) if hasattr(c, 'ecs_id')]
        
        execution_record.mark_as_completed("enhanced_execution")
        execution_record.promote_to_root()
        
        # Entity is already registered by promote_to_root()
        
        return execution_record
    
    @classmethod
    def _build_sibling_groups(cls, output_entities: List[Entity]) -> List[List[UUID]]:
        """Build sibling groups for entities from same function execution."""
        
        if len(output_entities) <= 1:
            return []
        
        # For now, all entities from same execution are siblings
        # Future enhancement: Could group by semantic type or return position
        all_ids = [e.ecs_id for e in output_entities]
        
        return [all_ids]  # Single group containing all entities
    
    @classmethod
    def _create_output_entity_from_result(
        cls,
        result: Any,
        output_entity_class: Type[Entity],
        function_name: str = "unknown"
    ) -> Entity:
        """
        Create output entity from function result using consistent field detection logic.
        
        This method consolidates the proven field detection pattern to ensure
        consistent behavior across all execution paths.
        """
        
        # Handle different result types
        if isinstance(result, dict):
            output_entity = output_entity_class(**result)
        elif isinstance(result, BaseModel):
            # Extract fields from BaseModel (like AnalysisResult, UserStats, etc.)
            output_entity = output_entity_class(**result.model_dump())
        else:
            # Single return value - determine the correct field name from the output entity class
            field_names = list(output_entity_class.model_fields.keys())
            # Exclude entity system fields and Phase 4 fields
            data_fields = [f for f in field_names if f not in {'ecs_id', 'live_id', 'created_at', 'forked_at',
                                                                'previous_ecs_id', 'lineage_id', 'old_ids', 'old_ecs_id',
                                                                'root_ecs_id', 'root_live_id', 'from_storage',
                                                                'untyped_data', 'attribute_source',
                                                                'derived_from_function', 'derived_from_execution_id',
                                                                'sibling_output_entities', 'output_index'}]
            if data_fields:
                # Use the first available data field
                output_entity = output_entity_class(**{data_fields[0]: result})
            else:
                raise ValueError(f"No data fields available in output entity class {output_entity_class.__name__}")
        
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
        
        # Quick fix: If result is already an Entity, return it directly with provenance
        if isinstance(result, Entity):
            output_entity = result
            
            # Set Phase 4 provenance fields after entity creation
            if hasattr(output_entity, 'derived_from_function'):
                output_entity.derived_from_function = function_name
            
            # Set up complete provenance tracking only for non-system fields
            for field_name in output_entity.model_fields:
                if field_name not in {'ecs_id', 'live_id', 'created_at', 'forked_at', 
                                     'previous_ecs_id', 'lineage_id', 'old_ids', 'old_ecs_id',
                                     'root_ecs_id', 'root_live_id', 'from_storage', 
                                     'untyped_data', 'attribute_source',
                                     'derived_from_function', 'derived_from_execution_id',
                                     'sibling_output_entities', 'output_index'}:
                    
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
        
        # Use the consolidated method for non-entity results only
        output_entity = cls._create_output_entity_from_result(result, output_entity_class, function_name)
        
        # Set Phase 4 provenance fields after entity creation
        if hasattr(output_entity, 'derived_from_function'):
            output_entity.derived_from_function = function_name
        
        # Set up complete provenance tracking
        for field_name in output_entity.model_fields:
            if field_name not in {'ecs_id', 'live_id', 'created_at', 'forked_at', 
                                 'previous_ecs_id', 'lineage_id', 'old_ids', 'old_ecs_id',
                                 'root_ecs_id', 'root_live_id', 'from_storage', 
                                 'untyped_data', 'attribute_source',
                                 'derived_from_function', 'derived_from_execution_id',
                                 'sibling_output_entities', 'output_index'}:
                
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
    async def _record_basic_execution(
        cls,
        input_entity: Entity,
        output_entity: Entity,
        function_name: str
    ) -> None:
        """Record basic function execution with standard tracking."""
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
        error_message: str,
        execution_id: Optional[UUID] = None,
        execution_duration: Optional[float] = None
    ) -> None:
        """Record execution failure for audit trails."""
        if execution_id is None:
            execution_id = uuid4()
        
        # Create failed execution record
        failed_execution = FunctionExecution(
            function_name=function_name,
            input_entity_id=input_entity.ecs_id if input_entity else None,
            output_entity_id=None,  # No output for failed execution
            error_message=error_message
        )
        # Store the execution_id in untyped_data since execution_id field doesn't exist
        if execution_id:
            failed_execution.untyped_data = f"execution_id:{execution_id}"
        
        # Set additional fields after construction
        failed_execution.execution_duration = execution_duration or 0.0
        failed_execution.succeeded = False
        failed_execution.execution_pattern = "failed"
        
        failed_execution.mark_as_failed(error_message)
        failed_execution.promote_to_root()  # This already calls EntityRegistry.register_entity()
    
    @classmethod
    async def _execute_primitives_only(cls, metadata: FunctionMetadata, kwargs: Dict[str, Any]) -> Union[Entity, List[Entity]]:
        """Execute function with only primitive parameters (no entities)."""
        
        # Create ConfigEntity from all primitive parameters
        config_entity = cls.create_config_entity_from_primitives(
            metadata.name,
            kwargs,
            expected_config_type=None  # Create dynamic ConfigEntity
        )
        config_entity.promote_to_root()
        
        # Create partial function with all parameters
        partial_func = partial(metadata.original_function, **kwargs)
        
        # Execute function (no input entities needed)
        try:
            if metadata.is_async:
                result = await partial_func()
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, partial_func)
        except Exception as e:
            await cls._record_execution_failure(None, metadata.name, str(e), None, None)
            raise
        
        # Create output entity
        if isinstance(result, Entity):
            output_entity = result
            output_entity.promote_to_root()
        else:
            # Handle non-entity result using consistent field detection
            output_entity = cls._create_output_entity_from_result(result, metadata.output_entity_class, metadata.name)
            output_entity.promote_to_root()
        
        # Record execution
        await cls._record_function_execution_with_config(None, output_entity, metadata.name, [config_entity])
        
        return output_entity
    
    @classmethod
    async def _execute_no_inputs(cls, metadata: FunctionMetadata) -> Union[Entity, List[Entity]]:
        """Execute function with no input parameters."""
        
        # Execute function directly
        try:
            if metadata.is_async:
                result = await metadata.original_function()
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, metadata.original_function)
        except Exception as e:
            await cls._record_execution_failure(None, metadata.name, str(e), None, None)
            raise
        
        # Create output entity
        if isinstance(result, Entity):
            output_entity = result
            output_entity.promote_to_root()
        else:
            # Handle non-entity result using consistent field detection
            output_entity = cls._create_output_entity_from_result(result, metadata.output_entity_class, metadata.name)
            output_entity.promote_to_root()
        
        # Record execution (no input entity, no config entity)
        execution_record = FunctionExecution(
            function_name=metadata.name,
            input_entity_id=None,
            output_entity_id=output_entity.ecs_id
        )
        execution_record.mark_as_completed("creation")
        execution_record.promote_to_root()
        
        return output_entity
    
    @classmethod
    async def execute_batch(cls, executions: List[Dict[str, Any]]) -> List[Union[Entity, List[Entity]]]:
        """Execute multiple functions concurrently."""
        async def execute_single(execution_config: Dict[str, Any]) -> Union[Entity, List[Entity]]:
            func_name = execution_config.pop('func_name')
            return await cls.aexecute(func_name, **execution_config)
        
        tasks = [execute_single(config.copy()) for config in executions]
        return await asyncio.gather(*tasks)
    
    @classmethod
    def execute_batch_sync(cls, executions: List[Dict[str, Any]]) -> List[Union[Entity, List[Entity]]]:
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
