# CallableRegistry Implementation Plan: Entity-Native Function Execution

## Phase 4: Godly Implementation from First Principles

Based on the complete ECS foundation we've built, this plan implements the design document's vision of **entity-native function execution** using our proven patterns.

## Core Architecture: Pure Entity System Integration

### 1. Function Metadata Storage (No Entity Inheritance)

```python
@dataclass
class FunctionMetadata:
    """Clean metadata storage - leverages our proven dataclass patterns."""
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
```

### 2. Entity Factory with create_model (Leverages Pydantic's Power)

```python
def create_entity_from_function_signature(
    func: Callable,
    entity_type: str,  # "Input" or "Output"  
    function_name: str
) -> Type[Entity]:
    """
    Entity factory using create_model - our proven dynamic class creation pattern.
    
    This leverages:
    - Pydantic's create_model for robust dynamic class creation
    - Our Entity base class for full versioning/registry integration
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
```

### 3. Enhanced Entity Reference Resolution (Uses Our Proven Patterns)

```python
class CallableEntityResolver:
    """
    Enhanced resolver that leverages our complete entity addressing system.
    
    Integrates:
    - ECS address parser (@uuid.field syntax)
    - Entity borrowing with borrow_from_address()
    - Composite entity creation patterns
    - Dependency tracking via EntityReferenceResolver
    """
    
    def __init__(self):
        self.base_resolver = EntityReferenceResolver()
        self.referenced_entities: Set[UUID] = set()
    
    def create_input_entity_with_borrowing(
        self, 
        input_entity_class: Type[Entity],
        kwargs: Dict[str, Any]
    ) -> Entity:
        """
        Create input entity using our proven borrowing patterns.
        
        This leverages:
        - create_composite_entity() from functional_api.py
        - borrow_from_address() from entity.py
        - Automatic attribute_source tracking
        """
        
        # Use our proven composite entity creation
        input_entity = create_composite_entity(
            entity_class=input_entity_class,
            field_mappings=kwargs,
            register=False  # We'll register it properly below
        )
        
        # Track dependencies (leverages EntityReferenceResolver)
        _, dependencies = resolve_data_with_tracking(kwargs)
        self.referenced_entities.update(dependencies)
        
        return input_entity
```

### 4. Entity-Native Execution Engine (Pure Entity System Integration)

```python
class CallableExecutor:
    """
    Pure entity system integration - leverages ALL our proven patterns.
    
    This implements the design document's revolutionary approach:
    - Functions become native participants in entity graphs
    - Automatic dependency discovery via build_entity_tree()
    - Immutable execution boundaries via get_stored_entity()
    - Complete provenance via attribute_source
    - Natural versioning through entity lifecycle
    """
    
    @classmethod
    def execute(cls, function_name: str, **kwargs) -> Entity:
        """
        Execute function with complete entity system integration.
        
        This leverages our proven patterns:
        1. Composite entity creation
        2. Automatic tree building and registration
        3. Immutable execution boundaries
        4. Provenance tracking
        5. Output entity creation with proper lineage
        """
        
        # Step 1: Get function metadata
        metadata = CallableRegistry.get_metadata(function_name)
        if not metadata:
            raise ValueError(f"Function '{function_name}' not registered")
        
        # Step 2: Create input entity with borrowing (proven pattern)
        resolver = CallableEntityResolver()
        input_entity = resolver.create_input_entity_with_borrowing(
            metadata.input_entity_class, kwargs
        )
        
        # Step 3: Register input entity (leverages build_entity_tree)
        # This automatically discovers ALL nested entity dependencies
        input_entity.promote_to_root()
        
        # Step 4: Get dependency information (automatic via entity system)
        input_tree = input_entity.get_tree()
        all_dependencies = list(input_tree.nodes.keys()) if input_tree else []
        
        # Step 5: Create isolated execution copy (proven immutability)
        execution_entity = EntityRegistry.get_stored_entity(
            input_entity.root_ecs_id, input_entity.ecs_id
        )
        
        if not execution_entity:
            raise ValueError("Failed to create isolated execution environment")
        
        # Step 6: Execute function with entity boundaries
        function_args = execution_entity.model_dump(exclude={
            'ecs_id', 'live_id', 'created_at', 'forked_at', 
            'previous_ecs_id', 'lineage_id', 'old_ids', 'old_ecs_id',
            'root_ecs_id', 'root_live_id', 'from_storage', 
            'untyped_data', 'attribute_source'
        })
        
        try:
            if metadata.is_async:
                result = asyncio.run(metadata.original_function(**function_args))
            else:
                result = metadata.original_function(**function_args)
        except Exception as e:
            cls._record_execution_failure(input_entity, function_name, str(e))
            raise
        
        # Step 7: Create output entity with proper provenance
        output_entity = cls._create_output_entity_with_provenance(
            result, metadata.output_entity_class, input_entity, function_name
        )
        
        # Step 8: Register output entity (automatic versioning)
        output_entity.promote_to_root()
        
        # Step 9: Record function execution relationship
        cls._record_function_execution(input_entity, output_entity, function_name)
        
        return output_entity
    
    @classmethod
    def _create_output_entity_with_provenance(
        cls,
        result: Any,
        output_entity_class: Type[Entity],
        input_entity: Entity,
        function_name: str
    ) -> Entity:
        """
        Create output entity with complete provenance tracking.
        
        Leverages our attribute_source system for full audit trails.
        """
        
        # Handle different result types
        if isinstance(result, dict):
            output_entity = output_entity_class(**result)
        elif isinstance(result, BaseModel):
            output_entity = output_entity_class(**result.model_dump())
        else:
            # Single return value
            output_entity = output_entity_class(result=result)
        
        # Set up complete provenance tracking
        for field_name in output_entity.model_fields:
            if field_name not in {'ecs_id', 'live_id', 'created_at', 'forked_at', 
                                 'previous_ecs_id', 'lineage_id', 'old_ids', 'old_ecs_id',
                                 'root_ecs_id', 'root_live_id', 'from_storage', 
                                 'untyped_data', 'attribute_source'}:
                
                field_value = getattr(output_entity, field_name)
                
                # Container-aware provenance (leverages our proven patterns)
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
    def _record_function_execution(
        cls,
        input_entity: Entity,
        output_entity: Entity, 
        function_name: str
    ):
        """Record function execution in entity lineage."""
        # Future enhancement: Create FunctionExecution entity
        # For now, provenance is handled through attribute_source
        pass
    
    @classmethod
    def _record_execution_failure(
        cls,
        input_entity: Entity,
        function_name: str,
        error_message: str
    ):
        """Record execution failure for audit trails."""
        # Future enhancement: Create FailedExecution entity
        pass
```

### 5. Clean Registry Implementation (No Entity Inheritance)

```python
class CallableRegistry:
    """
    Clean registry using proven dataclass patterns.
    
    No Entity inheritance - pure separation of concerns.
    Leverages all our entity system capabilities without over-engineering.
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
            
            # Create Entity classes using our proven factory
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
    def execute(cls, name: str, **kwargs) -> Entity:
        """Execute function using entity-native patterns."""
        return CallableExecutor.execute(name, **kwargs)
    
    @classmethod
    def get_metadata(cls, name: str) -> Optional[FunctionMetadata]:
        """Get function metadata."""
        return cls._functions.get(name)
    
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
```

## Usage Pattern: Pure Entity System Integration

```python
# 1. Register function with automatic Entity class creation
@CallableRegistry.register("analyze_student_performance")
def analyze_student_performance(
    name: str, 
    age: int, 
    grades: List[float],
    threshold: float = 3.0
) -> AnalysisResult:
    """Analyze student academic performance."""
    avg_grade = sum(grades) / len(grades)
    status = "excellent" if avg_grade >= threshold else "needs_improvement"
    
    return AnalysisResult(
        student_name=name,
        average_grade=avg_grade,
        status=status,
        total_courses=len(grades)
    )

# 2. Execute with entity borrowing and automatic dependency discovery
result_entity = CallableRegistry.execute("analyze_student_performance",
    name="@student_uuid.name",
    age="@student_uuid.age", 
    grades="@academic_record_uuid.final_grades",
    threshold=3.5
)

# 3. Result is a fully versioned Entity with complete provenance
print(f"Analysis result: {result_entity.ecs_id}")
print(f"Input dependencies: {result_entity.attribute_source}")

# 4. Can be used in further function calls
next_result = CallableRegistry.execute("generate_report",
    analysis="@" + str(result_entity.ecs_id),
    template="@template_uuid.report_format"
)
```

## Implementation Benefits: Leveraging All Our Patterns

### 1. **Type Safety with create_model Power**
- Preserves original field types and validation
- No `Any` type degradation
- Full Pydantic validation performance

### 2. **Entity System Native Integration**
- `promote_to_root()` for automatic dependency discovery
- `get_stored_entity()` for immutable execution boundaries
- `attribute_source` for complete provenance tracking
- Natural versioning through entity lifecycle

### 3. **Proven Pattern Reuse**
- Entity borrowing via `borrow_from_address()`
- Composite entity creation via `create_composite_entity()`
- String addressing via `@uuid.field` syntax
- Dependency tracking via `EntityReferenceResolver`

### 4. **Future-Ready Architecture**
- Clean serialization boundaries for Modal Sandbox
- Complete entity context for remote execution
- Audit trails through entity lineage
- Natural scaling patterns

## Implementation Timeline

### Phase 1: Core Implementation (1-2 days)
1. **FunctionMetadata dataclass** - Clean replacement for CallableFunction
2. **Entity factory with create_model** - Robust dynamic class creation
3. **CallableEntityResolver** - Enhanced borrowing integration
4. **Basic CallableExecutor** - Core execution engine

### Phase 2: Advanced Integration (2-3 days)
1. **Complete provenance tracking** - attribute_source integration
2. **Execution failure handling** - Error entity creation
3. **Function execution entities** - Audit trail enhancement
4. **Performance optimization** - Caching and batching

### Phase 3: Production Features (3-5 days)
1. **Modal Sandbox preparation** - Serializable execution packages
2. **Advanced dependency analysis** - Graph-based optimization
3. **Function composition** - Chaining with entity boundaries
4. **Monitoring and observability** - Entity-based metrics

This implementation achieves the design document's vision of **revolutionary entity-native function execution** by leveraging every proven pattern we've built, creating a unified graph of data and transformations with complete auditability and automatic versioning.