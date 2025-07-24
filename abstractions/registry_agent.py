"""
Pydantic-AI Integration for Abstractions Entity Framework

This module provides a complete natural language interface to the Abstractions
Entity Framework using pydantic-ai agents. Features include:

- Execute registered functions with string addressing support
- Explore entity lineages and version history  
- Enhanced error handling with impressive debugging help
- Natural language access to the entity registry

The integration is entirely external to the abstractions package.
"""

from typing import Any, Dict, Optional, Tuple, List, Union
from uuid import UUID
from dataclasses import dataclass
from pydantic import BaseModel, Field, create_model, model_validator

from pydantic_ai import Agent
from pydantic_ai.toolsets.function import FunctionToolset

# Direct imports from abstractions - leveraging singleton architecture
from abstractions.ecs.callable_registry import CallableRegistry
from abstractions.ecs.entity import EntityRegistry, Entity
from abstractions.ecs.ecs_address_parser import (
    ECSAddressParser, 
    InputPatternClassifier,
    EntityReferenceResolver,
    get
)
from abstractions.events.events import (
    Event, CreatedEvent, ProcessingEvent, ProcessedEvent,
    on, emit, get_event_bus
)

from dotenv import load_dotenv
load_dotenv()

# Pydantic models for tool responses
class ExecutionResult(BaseModel):
    success: bool
    function_name: str
    result_type: str
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None
    entity_count: Optional[int] = None
    error_message: Optional[str] = None
    debug_info: Optional[Dict[str, Any]] = None


class FunctionInfo(BaseModel):
    name: str
    signature: str
    docstring: Optional[str]
    is_async: bool
    input_entity_class: Optional[str]
    output_entity_class: str


class FunctionList(BaseModel):
    total_functions: int
    functions: List[str]
    function_info: Dict[str, FunctionInfo]


class EntityInfo(BaseModel):
    ecs_id: str
    lineage_id: str
    root_ecs_id: str
    entity_type: str
    is_root: bool
    ancestry_path: List[str]
    attributes: Dict[str, str]


class LineageInfo(BaseModel):
    lineage_id: str
    latest_ecs_id: str
    entity_type: str
    total_versions: int
    version_history: List[str]


class LineageList(BaseModel):
    total_lineages: int
    lineages: Dict[str, LineageInfo]


# Error handling for tools
class ToolError(BaseModel):
    """Structured error response for tools."""
    success: bool = False
    error_type: str
    error_message: str
    suggestions: List[str] = Field(default_factory=list)
    debug_info: Optional[Dict[str, Any]] = None





# ============================================================================
# POLYMORPHIC GOAL SYSTEM
# ============================================================================

class GoalError(BaseModel):
    """Clean error model for goal failures."""
    error_type: str
    error_message: str
    suggestions: List[str] = Field(default_factory=list)
    debug_info: Dict[str, Any] = Field(default_factory=dict)


class BaseGoal(BaseModel):
    """Base goal with ECS address-based typed result loading."""
    
    model_config = {"validate_assignment": True, "revalidate_instances": "always"}
    
    goal_type: str
    goal_completed: bool = False
    summary: str
    
    # Agent sets this ECS address string
    typed_result_ecs_address: Optional[str] = None
    
    # Gets overridden in dynamic subclasses with proper types
    typed_result: Optional[Entity] = None
    
    # Optional separate error model
    error: Optional[GoalError] = None
    
    @model_validator(mode='after')
    def load_and_validate_typed_result(self):
        """Load typed result and validate required fields."""
        if self.typed_result_ecs_address and not self.typed_result:
            # Load from ECS address
            self.typed_result = get(self.typed_result_ecs_address)
        
        # Validation: Must have (string OR entity) OR error
        has_string = bool(self.typed_result_ecs_address)
        has_entity = bool(self.typed_result)
        has_error = bool(self.error)
        
        if not (has_string or has_entity or has_error):
            raise ValueError("Must provide typed_result_ecs_address, typed_result, or error")
        
        return self


@dataclass
class SystemPromptComponents:
    """Modular components for building agent system prompts."""
    
    framework_context: str = """
The Abstractions Entity Framework is a functional data processing system where:
- Entities are immutable data units with global identity (ecs_id)
- Functions transform entities and are tracked in a registry
- All operations maintain complete provenance and lineage
- String addressing allows distributed data access (@uuid.field syntax)
"""
    
    response_options: str = """
You have 3 options for responses:

1. SUCCESS WITH ECS ADDRESS:
   - Set typed_result_ecs_address to point to result entity
   - Never set typed_result directly - it loads automatically
   - Set goal_completed=true

2. SUCCESS WITH DIRECT ENTITY:
   - Set typed_result directly to entity
   - Set goal_completed=true

3. FAILURE:
   - Set error with GoalError object
   - Set goal_completed=false
"""
    
    available_capabilities: str = """
Available capabilities:
- execute_function(function_name, **kwargs) - Execute registered functions
- list_functions() - Show available functions with metadata
- get_all_lineages() - Show entity lineages
- get_entity() - Get specific entity details
"""
    
    parameter_passing_examples: str = """
CRITICAL: How to pass parameters to execute_function:

Example 1 - Function expects primitive parameters, extract from entity fields:
Function: send_email(recipient: str, subject: str, body: str) -> EmailResult
Entity: NotificationConfig with ecs_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890" and fields: recipient_email, email_subject, message_body
Correct call: execute_function("send_email", recipient="@a1b2c3d4-e5f6-7890-abcd-ef1234567890.recipient_email", subject="@a1b2c3d4-e5f6-7890-abcd-ef1234567890.email_subject", body="@a1b2c3d4-e5f6-7890-abcd-ef1234567890.message_body")

Example 2 - Function expects entity object directly:
Function: analyze_customer(customer: Customer) -> AnalysisResult  
Entity: Customer with ecs_id="b2c3d4e5-f6g7-8901-bcde-f23456789012"
Correct call: execute_function("analyze_customer", customer="@b2c3d4e5-f6g7-8901-bcde-f23456789012")
"""
    
    addressing_examples: str = """
STRING ADDRESSING EXAMPLES:

Success with ECS address:
typed_result_ecs_address = "@f1e2d3c4-b5a6-9870-fedc-ba9876543210"

Failure handling:
error = GoalError(
    error_type="FunctionExecutionFailed",
    error_message="Could not execute function due to missing parameters",
    suggestions=["Check function signature", "Verify entity field names"]
)
"""
    
    key_rules: str = """
KEY RULES:
- Use @uuid.field to extract primitive values from entity fields
- Use @uuid (without .field) to pass entire entity objects
- Always check function signature with get_function_signature() to understand parameter types
- Match entity field types to function parameter types (str to str, int to int, etc.)
- Functions CREATE the result entities - you reference them with typed_result_ecs_address
"""


def build_goal_system_prompt(goal_type: str, result_entity_class) -> str:
    """Build complete system prompt for specific goal type."""
    
    components = SystemPromptComponents()
    result_docstring = result_entity_class.__doc__ or f"Result entity for {goal_type} operations."
    
    prompt = f"""
You are handling {goal_type} goals for the Abstractions Entity Framework.

{components.framework_context}

{components.response_options}

TARGET RESULT ENTITY:
The result entity should be type {result_entity_class.__name__}.

{result_docstring}

{components.available_capabilities}

{components.parameter_passing_examples}

{components.addressing_examples}

{components.key_rules}

You MUST provide either typed_result_ecs_address, typed_result, or error.
"""
    
    return prompt


class GoalFactory:
    """Create Goal subclasses with proper typed result fields using create_model."""
    
    @classmethod
    def create_goal_class(cls, result_entity_class: type[Entity]):
        """Create Goal subclass with properly typed result field from entity class."""
        
        # Validate input
        if not (isinstance(result_entity_class, type) and issubclass(result_entity_class, Entity)):
            raise ValueError(f"result_entity_class must be an Entity subclass, got {result_entity_class}")
        
        # Derive goal type from class name
        goal_type = cls._derive_goal_type_from_class(result_entity_class)
        
        # Create dynamic goal class name
        dynamic_class_name = f"{result_entity_class.__name__.replace('Result', '')}Goal"
        
        # Create the dynamic goal class using create_model
        DynamicGoal = create_model(
            dynamic_class_name,
            __base__=BaseGoal,
            __module__=__name__,
            # This is the key - typed_result field with proper type
            typed_result=(Optional[result_entity_class], None),
        )
        
        return DynamicGoal
    
    @classmethod
    def _derive_goal_type_from_class(cls, result_entity_class: type[Entity]) -> str:
        """Derive goal type string from result entity class name."""
        import re
        
        class_name = result_entity_class.__name__
        
        # Remove 'Result' suffix if present
        if class_name.endswith('Result'):
            class_name = class_name[:-6]  # Remove 'Result'
        
        # Convert CamelCase to snake_case
        goal_type = re.sub('([A-Z]+)', r'_\1', class_name).lower().lstrip('_')
        
        return goal_type


class TypedAgentFactory:
    """Create agents with specific goal types."""
    
    @classmethod
    def create_agent(cls, result_entity_class: type[Entity]):
        """Create agent for specific result entity class."""
        
        goal_class = GoalFactory.create_goal_class(result_entity_class)
        goal_type = GoalFactory._derive_goal_type_from_class(result_entity_class)
        
        system_prompt = build_goal_system_prompt(goal_type, result_entity_class)
        
        agent = Agent(
            'anthropic:claude-sonnet-4-20250514',
            output_type=goal_class,
            toolsets=[registry_toolset],
            system_prompt=system_prompt
        )
        
        return agent


# ============================================================================
# END POLYMORPHIC GOAL SYSTEM
# ============================================================================


class AddressErrorHandler:
    """Provides impressive debugging help for ECS address errors."""
    
    @classmethod
    def validate_and_resolve_address(cls, address: str) -> Tuple[bool, Any, Dict[str, Any]]:
        """
        Validate and resolve address with comprehensive error information.
        
        Returns:
            (success, resolved_value_or_none, debug_info)
        """
        debug_info = {
            "address": address,
            "validation_steps": [],
            "suggestions": [],
            "error_type": None,
            "error_message": None
        }
        
        # Step 1: Basic format validation
        if not isinstance(address, str):
            debug_info["error_type"] = "invalid_input_type"
            debug_info["error_message"] = f"Address must be string, got {type(address).__name__}"
            debug_info["suggestions"].append("Ensure the address parameter is a string")
            return False, None, debug_info
        
        if not address.startswith('@'):
            debug_info["error_type"] = "missing_at_symbol"
            debug_info["error_message"] = "ECS addresses must start with '@'"
            debug_info["suggestions"].extend([
                f"Try: '@{address}' if this is a UUID",
                "ECS address format: @uuid.field.subfield"
            ])
            return False, None, debug_info
        
        debug_info["validation_steps"].append("✓ Starts with @")
        
        # Step 2: Check if it's a valid ECS address format
        if not ECSAddressParser.is_ecs_address(address):
            debug_info["error_type"] = "invalid_address_format"
            debug_info["error_message"] = "Invalid ECS address format"
            
            # Try to provide specific guidance
            if len(address) == 37 and address.count('-') == 4:  # Looks like @uuid
                debug_info["suggestions"].append("This looks like a UUID-only address. Add a field: @uuid.fieldname")
            elif '.' not in address[1:]:
                debug_info["suggestions"].append("Missing field path. Use format: @uuid.field.subfield")
            else:
                debug_info["suggestions"].extend([
                    "Check UUID format: @xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx.field",
                    "Ensure no special characters except hyphens in UUID part"
                ])
            return False, None, debug_info
        
        debug_info["validation_steps"].append("✓ Valid ECS address format")
        
        # Step 3: Parse the address
        try:
            entity_id, field_path = ECSAddressParser.parse_address(address)
            debug_info["validation_steps"].append(f"✓ Parsed: UUID={entity_id}, fields={field_path}")
        except ValueError as e:
            debug_info["error_type"] = "parse_error"
            debug_info["error_message"] = str(e)
            debug_info["suggestions"].append("Check UUID format - must be valid UUID v4")
            return False, None, debug_info
        
        # Step 4: Check if entity exists in registry
        root_ecs_id = EntityRegistry.ecs_id_to_root_id.get(entity_id)
        if not root_ecs_id:
            debug_info["error_type"] = "entity_not_found"
            debug_info["error_message"] = f"Entity {entity_id} not found in registry"
            debug_info["suggestions"].extend([
                "Verify the UUID is correct",
                "Check if the entity has been registered",
                "Use get_all_lineages() to see available entities"
            ])
            
            # Check if there are similar UUIDs
            similar_ids = cls._find_similar_entity_ids(entity_id)
            if similar_ids:
                debug_info["suggestions"].append(f"Similar entities found: {similar_ids[:3]}")
            
            return False, None, debug_info
        
        debug_info["validation_steps"].append(f"✓ Entity exists in root {root_ecs_id}")
        
        # Step 5: Try to resolve the address
        try:
            resolved_value, resolution_type = ECSAddressParser.resolve_address_advanced(address)
            debug_info["validation_steps"].append(f"✓ Resolved as {resolution_type}")
            debug_info["resolution_type"] = resolution_type
            debug_info["resolved_value_type"] = type(resolved_value).__name__
            return True, resolved_value, debug_info
            
        except Exception as e:
            debug_info["error_type"] = "resolution_error"
            debug_info["error_message"] = str(e)
            
            # Try to provide field-specific guidance
            entity = EntityRegistry.get_stored_entity(root_ecs_id, entity_id)
            if entity and field_path:
                available_fields = [f for f in dir(entity) if not f.startswith('_')]
                debug_info["available_fields"] = available_fields[:10]  # Limit output
                
                # Check for similar field names
                similar_fields = [f for f in available_fields if any(part in f.lower() for part in field_path)]
                if similar_fields:
                    debug_info["suggestions"].append(f"Similar fields available: {similar_fields[:5]}")
                else:
                    debug_info["suggestions"].append(f"Available fields: {available_fields[:5]}")
            
            return False, None, debug_info
    
    @classmethod
    def _find_similar_entity_ids(cls, target_id: UUID, max_results: int = 5) -> list[str]:
        """Find entity IDs that are similar to the target (for debugging help)."""
        similar = []
        target_str = str(target_id)
        
        # Check first few characters for similar UUIDs
        for existing_id in EntityRegistry.ecs_id_to_root_id.keys():
            existing_str = str(existing_id)
            if existing_str[:8] == target_str[:8]:  # Same first 8 chars
                similar.append(existing_str)
            if len(similar) >= max_results:
                break
        
        return similar
    
    @classmethod
    def analyze_function_parameters(cls, function_name: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze function parameters and provide debugging info for address usage.
        """
        analysis = {
            "function_name": function_name,
            "total_parameters": len(kwargs),
            "address_analysis": {},
            "pattern_classification": None,
            "suggestions": []
        }
        
        # Classify the input pattern
        try:
            pattern_type, classifications = InputPatternClassifier.classify_kwargs_advanced(kwargs)
            analysis["pattern_classification"] = {
                "pattern_type": pattern_type,
                "classifications": classifications
            }
        except Exception as e:
            analysis["pattern_classification"] = {"error": str(e)}
        
        # Analyze each parameter that looks like an address
        address_params = []
        for param_name, param_value in kwargs.items():
            if isinstance(param_value, str) and param_value.startswith('@'):
                success, resolved, debug_info = cls.validate_and_resolve_address(param_value)
                analysis["address_analysis"][param_name] = {
                    "success": success,
                    "debug_info": debug_info
                }
                if not success:
                    address_params.append(param_name)
        
        # Generate overall suggestions
        if address_params:
            analysis["suggestions"].extend([
                f"Address errors found in parameters: {address_params}",
                "Check the address_analysis section for detailed debugging info",
                "Use get_all_lineages() to see available entities"
            ])
        
        return analysis


# Create the toolset
registry_toolset = FunctionToolset()


@registry_toolset.tool
async def execute_function(function_name: str, **kwargs) -> ExecutionResult:
    """
    Execute a registered function with enhanced address debugging.
    
    Provides comprehensive error analysis when address syntax is incorrect.
    Supports @uuid.field syntax for entity references in parameters.
    """
    try:
        # Pre-execution parameter analysis
        param_analysis = AddressErrorHandler.analyze_function_parameters(function_name, kwargs)
        
        # Check if any address parameters failed validation
        failed_addresses = []
        for param_name, analysis in param_analysis["address_analysis"].items():
            if not analysis["success"]:
                failed_addresses.append({
                    "parameter": param_name,
                    "debug_info": analysis["debug_info"]
                })
        
        if failed_addresses:
            return ExecutionResult(
                success=False,
                function_name=function_name,
                result_type="error",
                error_message=f"Address validation failed for {len(failed_addresses)} parameter(s)",
                debug_info={
                    "failed_addresses": failed_addresses,
                    "parameter_analysis": param_analysis
                }
            )
        
        # If validation passed, execute the function
        result = await CallableRegistry.aexecute(function_name, **kwargs)
        
        # Process result
        if hasattr(result, 'ecs_id') and isinstance(result, Entity):  # Single entity
            return ExecutionResult(
                success=True,
                function_name=function_name,
                result_type="single_entity",
                entity_id=str(result.ecs_id),
                entity_type=type(result).__name__,
                entity_count=1
            )
        elif isinstance(result, list):
            entity_ids = [str(e.ecs_id) for e in result if hasattr(e, 'ecs_id')]
            return ExecutionResult(
                success=True,
                function_name=function_name,
                result_type="entity_list",
                entity_count=len(entity_ids),
                debug_info={"entity_ids": entity_ids}
            )
        else:
            return ExecutionResult(
                success=True,
                function_name=function_name,
                result_type="other",
                debug_info={"value": str(result)}
            )
        
    except Exception as e:
        return ExecutionResult(
            success=False,
            function_name=function_name,
            result_type="error",
            error_message=str(e),
            debug_info={
                "parameters": list(kwargs.keys()),
                "suggestion": "Use get_function_signature() to see expected parameters"
            }
        )


@registry_toolset.tool
def list_functions() -> FunctionList:
    """List all available functions with metadata."""
    functions = CallableRegistry.list_functions()
    function_info = {}
    
    for func_name in functions:
        info = CallableRegistry.get_function_info(func_name)
        if info:
            function_info[func_name] = FunctionInfo(
                name=info['name'],
                signature=info['signature'],
                docstring=info['docstring'],
                is_async=info['is_async'],
                input_entity_class=info['input_entity_class'],
                output_entity_class=info['output_entity_class']
            )
    
    return FunctionList(
        total_functions=len(functions),
        functions=functions,
        function_info=function_info
    )


@registry_toolset.tool
def get_function_signature(function_name: str) -> Union[FunctionInfo, ToolError]:
    """Get detailed function signature and type information."""
    info = CallableRegistry.get_function_info(function_name)
    if not info:
        return ToolError(
            error_type="function_not_found",
            error_message=f"Function '{function_name}' not found",
            suggestions=[
                "Use list_functions() to see all available functions",
                "Check the function name spelling",
                "Ensure the function has been registered"
            ]
        )
    
    return FunctionInfo(
        name=info['name'],
        signature=info['signature'],
        docstring=info['docstring'],
        is_async=info['is_async'],
        input_entity_class=info['input_entity_class'],
        output_entity_class=info['output_entity_class']
    )


@registry_toolset.tool
def get_all_lineages() -> LineageList:
    """Show all entity lineages with version history."""
    lineages = {}
    
    for lineage_id, root_ids in EntityRegistry.lineage_registry.items():
        if root_ids:
            latest_root_id = root_ids[-1]
            tree = EntityRegistry.get_stored_tree(latest_root_id)
            
            if tree and tree.root_ecs_id in tree.nodes:
                root_entity = tree.nodes[tree.root_ecs_id]
                lineages[str(lineage_id)] = LineageInfo(
                    lineage_id=str(lineage_id),
                    latest_ecs_id=str(latest_root_id),
                    entity_type=type(root_entity).__name__,
                    total_versions=len(root_ids),
                    version_history=[str(rid) for rid in root_ids]
                )
    
    return LineageList(
        total_lineages=len(lineages),
        lineages=lineages
    )


@registry_toolset.tool
def get_lineage_history(lineage_id: str) -> Union[LineageInfo, ToolError]:
    """Get complete version history for a specific lineage."""
    try:
        lineage_uuid = UUID(lineage_id)
    except ValueError:
        return ToolError(
            error_type="invalid_uuid",
            error_message=f"Invalid UUID format: {lineage_id}",
            suggestions=[
                "Ensure the lineage_id is a valid UUID",
                "Use get_all_lineages() to see available lineage IDs"
            ]
        )
    
    root_ids = EntityRegistry.lineage_registry.get(lineage_uuid, [])
    
    if not root_ids:
        return ToolError(
            error_type="lineage_not_found",
            error_message=f"Lineage {lineage_id} not found",
            suggestions=[
                "Use get_all_lineages() to see available lineages",
                "Check the lineage_id spelling and format",
                "Ensure entities have been created and registered"
            ]
        )
    
    latest_root_id = root_ids[-1]
    tree = EntityRegistry.get_stored_tree(latest_root_id)
    
    if tree and tree.root_ecs_id in tree.nodes:
        root_entity = tree.nodes[tree.root_ecs_id]
        return LineageInfo(
            lineage_id=lineage_id,
            latest_ecs_id=str(latest_root_id),
            entity_type=type(root_entity).__name__,
            total_versions=len(root_ids),
            version_history=[str(rid) for rid in root_ids]
        )
    else:
        return ToolError(
            error_type="entity_data_unavailable",
            error_message=f"Unable to retrieve entity data for lineage {lineage_id}",
            suggestions=[
                "The lineage exists but entity data is corrupted or missing",
                "Try using get_all_lineages() to see overall status",
                "Contact system administrator if this persists"
            ],
            debug_info={
                "latest_root_id": str(latest_root_id),
                "tree_available": tree is not None,
                "nodes_count": len(tree.nodes) if tree else 0
            }
        )


@registry_toolset.tool
def get_entity(root_ecs_id: str, ecs_id: str) -> Union[EntityInfo, ToolError]:
    """Retrieve specific entity with complete details."""
    try:
        root_uuid = UUID(root_ecs_id)
    except ValueError:
        return ToolError(
            error_type="invalid_root_uuid",
            error_message=f"Invalid root UUID format: {root_ecs_id}",
            suggestions=[
                "Ensure the root_ecs_id is a valid UUID",
                "Use get_all_lineages() to see available root entity IDs"
            ]
        )
    
    try:
        entity_uuid = UUID(ecs_id)
    except ValueError:
        return ToolError(
            error_type="invalid_entity_uuid",
            error_message=f"Invalid entity UUID format: {ecs_id}",
            suggestions=[
                "Ensure the ecs_id is a valid UUID",
                "Check the entity ID spelling and format"
            ]
        )
    
    entity = EntityRegistry.get_stored_entity(root_uuid, entity_uuid)
    if not entity:
        return ToolError(
            error_type="entity_not_found",
            error_message=f"Entity {ecs_id} not found in root {root_ecs_id}",
            suggestions=[
                "Verify both UUIDs are correct",
                "Use get_all_lineages() to find available entities",
                "Check if the entity exists in a different root tree",
                "Ensure the entity has been registered"
            ],
            debug_info={
                "root_ecs_id": root_ecs_id,
                "entity_ecs_id": ecs_id,
                "root_exists": EntityRegistry.get_stored_tree(root_uuid) is not None
            }
        )
    
    # Get entity tree for relationship context
    tree = EntityRegistry.get_stored_tree(root_uuid)
    ancestry_path = tree.get_ancestry_path(entity_uuid) if tree else []
    
    return EntityInfo(
        ecs_id=str(entity.ecs_id),
        lineage_id=str(entity.lineage_id),
        root_ecs_id=str(entity.root_ecs_id),
        entity_type=type(entity).__name__,
        is_root=entity.is_root_entity(),
        ancestry_path=[str(uid) for uid in ancestry_path],
        attributes={
            k: str(v) for k, v in entity.__dict__.items()
            if not k.startswith('_') and k not in [
                'ecs_id', 'live_id', 'root_ecs_id', 'root_live_id',
                'lineage_id', 'created_at', 'forked_at'
            ]
        }
    )


