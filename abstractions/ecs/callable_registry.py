"""
Registry module for managing callable tools as versioned entities.

This module provides a global registry for managing callable functions. When a 
function is registered, it is wrapped in a `CallableFunction` entity, which 
stores its signature and derived JSON schemas. This entity is then registered with
the main `EntityRegistry`, making the function's definition itself a versioned
artifact in the system.
"""

from typing import Dict, Any, Callable, Optional, List, Union, get_type_hints, Type, Tuple, cast
from pydantic import create_model, BaseModel
from inspect import signature, iscoroutinefunction, getdoc
import functools
import asyncio
import json
from uuid import UUID

from ecs.entity import Entity, EntityRegistry, build_entity_tree

# --- Schema Derivation Helpers ---

def derive_input_model(func: Callable) -> Type[BaseModel]:
    """Derive a Pydantic model from function type hints for input validation."""
    type_hints = get_type_hints(func)
    sig = signature(func)
    
    # Remove return type for input model
    if 'return' in type_hints:
        del type_hints['return']

    # Create a Pydantic model from the function's arguments
    input_fields: Dict[str, Tuple[Any, Any]] = {
        param.name: (type_hints.get(param.name, Any), param.default if param.default is not param.empty else ...)
        for param in sig.parameters.values()
    }
    
    InputModel = create_model(f"{func.__name__}Input", **cast(Any, input_fields), __module__=func.__module__)
    return InputModel

def derive_output_model(func: Callable) -> Type[BaseModel]:
    """Derive a Pydantic model from function return type for output validation."""
    type_hints = get_type_hints(func)
    
    if 'return' not in type_hints:
        raise ValueError(f"Function {func.__name__} must have a return type hint")
    
    output_type = type_hints['return']
    if isinstance(output_type, type) and issubclass(output_type, BaseModel):
        OutputModel = output_type
    else:
        output_fields: Dict[str, Tuple[Any, Any]] = {"result": (output_type, ...)}
        OutputModel = create_model(f"{func.__name__}Output", **cast(Any, output_fields), __module__=func.__module__)
    
    return OutputModel

# --- Entity Model for Functions ---

class CallableFunction(Entity):
    """An Entity that represents a registered callable function."""
    name: str
    signature_str: str
    docstring: Optional[str] = None
    input_model_json_schema: Dict[str, Any] # Store the JSON schema for persistence
    output_model_json_schema: Dict[str, Any] # Store the JSON schema for persistence
    is_async: bool

    # These will be set at runtime after deserialization or during registration
    _input_model: Optional[Type[BaseModel]] = None
    _output_model: Optional[Type[BaseModel]] = None

    def __init__(self, **data: Any):
        super().__init__(**data)
        # Reconstruct models if schemas are present and models are not already set
        if self.input_model_json_schema and self._input_model is None:
            input_fields_from_schema: Dict[str, Tuple[Any, Any]] = {
                k: (Any, ...) for k in self.input_model_json_schema.get("properties", {}).keys()
            }
            self._input_model = create_model(
                f"{self.name}Input", 
                **cast(Any, input_fields_from_schema),
                __module__=self.__module__
            )
        if self.output_model_json_schema and self._output_model is None:
            output_fields_from_schema: Dict[str, Tuple[Any, Any]] = {
                k: (Any, ...) for k in self.output_model_json_schema.get("properties", {}).keys()
            }
            self._output_model = create_model(
                f"{self.name}Output", 
                **cast(Any, output_fields_from_schema),
                __module__=self.__module__
            )

    @property
    def input_model(self) -> Type[BaseModel]:
        if self._input_model is None:
            raise ValueError("Input model not initialized. This should happen during registration or deserialization.")
        return self._input_model

    @property
    def output_model(self) -> Type[BaseModel]:
        if self._output_model is None:
            raise ValueError("Output model not initialized. This should happen during registration or deserialization.")
        return self._output_model

# --- Entity Reference Resolution (from previous step) ---

def _resolve_entity_references(data: Any) -> Any:
    """Recursively scans a data structure and resolves any entity reference strings."""
    if isinstance(data, dict):
        return {k: _resolve_entity_references(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_resolve_entity_references(v) for v in data]
    elif isinstance(data, str) and data.startswith('@'):
        return _fetch_entity_attribute(data)
    else:
        return data

def _fetch_entity_attribute(reference: str) -> Any:
    """Fetches an entity or its attribute based on a reference string."""
    try:
        ref = reference.lstrip('@')
        path_parts = ref.split('.')
        ecs_id = UUID(path_parts[0])
        attr_path = path_parts[1:]
        
        root_ecs_id = EntityRegistry.ecs_id_to_root_id.get(ecs_id)
        if not root_ecs_id:
            raise ValueError(f"Entity with ecs_id {ecs_id} not found in any registered tree.")

        entity = EntityRegistry.get_stored_entity(root_ecs_id, ecs_id)
        if not entity:
            raise ValueError(f"Could not retrieve entity {ecs_id} from tree {root_ecs_id}")

        if not attr_path:
            return entity
        
        return functools.reduce(getattr, attr_path, entity)

    except (ValueError, AttributeError, KeyError) as e:
        raise ValueError(f"Failed to resolve entity reference '{reference}': {e}") from e

# --- Main CallableRegistry Class ---

class CallableRegistry:
    """A registry for functions that are stored and versioned as Entities."""
    _registry: Dict[str, Callable] = {}

    @classmethod
    def register(cls, name: str) -> Callable:
        """A decorator to register a function, creating a versioned Entity for it."""
        def decorator(func: Callable) -> Callable:
            try:
                # 1. Derive Pydantic models from the function
                input_model = derive_input_model(func)
                output_model = derive_output_model(func)
                
                # 2. Create a CallableFunction entity instance
                func_entity = CallableFunction(
                    name=name,
                    signature_str=str(signature(func)),
                    docstring=getdoc(func),
                    input_model_json_schema=input_model.model_json_schema(),
                    output_model_json_schema=output_model.model_json_schema(),
                    is_async=iscoroutinefunction(func)
                )
                # Manually set the runtime models - this is the key change
                func_entity._input_model = input_model
                func_entity._output_model = output_model

                # This makes the function entity its own root and registers it
                func_entity.promote_to_root()

                # 3. Store the raw callable for execution
                cls._registry[name] = func
                
                print(f"Successfully registered '{name}'.")
                return func

            except Exception as e:
                print(f"Failed to register function '{name}': {e}")
                raise

        return decorator

    @classmethod
    def get_callable(cls, name: str) -> Callable:
        """Gets the raw callable function from the registry."""
        if name not in cls._registry:
            raise ValueError(f"Callable '{name}' not found.")
        return cls._registry[name]

    @classmethod
    def get_function_entity(cls, name: str) -> Optional[CallableFunction]:
        """Retrieves the versioned Entity for a given function name."""
        # This is a simplified lookup. A real implementation would need a more robust
        # way to find the latest version of a function entity by name.
        for tree in EntityRegistry.tree_registry.values():
            root_entity = tree.get_entity(tree.root_ecs_id)
            if isinstance(root_entity, CallableFunction) and root_entity.name == name:
                return root_entity
        return None

    @classmethod
    def execute(cls, name: str, **kwargs: Any) -> Any:
        """Resolves entity references and executes the callable synchronously."""
        func = cls.get_callable(name)
        
        # 1. Resolve any @... references in the input arguments
        resolved_kwargs = _resolve_entity_references(kwargs)

        # 2. Validate input using the stored Pydantic model
        func_entity = cls.get_function_entity(name)
        if not func_entity:
            raise ValueError(f"Function entity for '{name}' not found in registry.")

        try:
            # Use the pre-derived input model for validation
            validated_input = func_entity.input_model.model_validate(resolved_kwargs)
        except Exception as e:
            raise ValueError(f"Input validation failed for '{name}': {e}") from e

        # 3. Execute the function
        response = func(**validated_input.model_dump())
        
        # 4. (Optional) Validate and wrap output
        if isinstance(response, BaseModel):
            return response
        return {"result": response}

    @classmethod
    async def aexecute(cls, name: str, **kwargs: Any) -> Any:
        """Resolves entity references and executes the callable asynchronously."""
        func = cls.get_callable(name)
        
        # 1. Resolve references
        resolved_kwargs = _resolve_entity_references(kwargs)

        # 2. Validate input
        func_entity = cls.get_function_entity(name)
        if not func_entity:
            raise ValueError(f"Function entity for '{name}' not found in registry.")

        try:
            # Use the pre-derived input model for validation
            validated_input = func_entity.input_model.model_validate(resolved_kwargs)
        except Exception as e:
            raise ValueError(f"Input validation failed for '{name}': {e}") from e

        # 3. Execute function (handling both sync and async)
        if iscoroutinefunction(func):
            response = await func(**validated_input.model_dump())
        else:
            response = await asyncio.to_thread(func, **validated_input.model_dump())

        # 4. (Optional) Validate and wrap output
        if isinstance(response, BaseModel):
            return response
        return {"result": response}