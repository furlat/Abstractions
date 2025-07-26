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

from typing import Any, Dict, Optional, Tuple, List, Union, Literal
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
from abstractions.events.events import (
    Event, EventPhase, emit_events, on, get_event_bus,
    ProcessingEvent, ProcessedEvent
)

from dotenv import load_dotenv
load_dotenv()

# Type definitions for union types and model selection
ResultEntityInput = Union[type[Entity], List[type[Entity]]]

# Model type for better type safety (RIP Claude 3 Haiku 🪦)
ModelName = Literal[
    'anthropic:claude-sonnet-4-20250514',
    'anthropic:claude-3-5-sonnet-20241022',
    'anthropic:claude-3-5-haiku-20241022',  # The successor to the beloved original
    'openai:gpt-4o',
    'openai:gpt-4o-mini'
]

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
You have 2 options for responses:

1. SUCCESS WITH ECS ADDRESS:
   - Set typed_result_ecs_address to point to result entity
   - Never set typed_result directly - it loads automatically
   - Set goal_completed=true

2. FAILURE:
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


def build_goal_system_prompt(
    goal_type: str,
    result_entity_classes: ResultEntityInput,
    custom_examples: Optional[str] = None
) -> str:
    """Build system prompt supporting single or union result entity types."""
    
    components = SystemPromptComponents()
    
    # Normalize to list (NEW SWITCH CASE)
    if isinstance(result_entity_classes, list):
        class_list = result_entity_classes
    else:
        class_list = [result_entity_classes]
    
    # TARGET RESULT ENTITIES section (NEW SWITCH CASE)
    if len(class_list) == 1:
        # Single type (PRESERVES CURRENT BEHAVIOR)
        result_class = class_list[0]
        result_docstring = result_class.__doc__ or f"Result entity for {goal_type} operations."
        target_section = f"""
TARGET RESULT ENTITY:
The result entity should be type {result_class.__name__}.

{result_docstring}
"""
    else:
        # Union types (NEW CASE)
        target_section = "TARGET RESULT ENTITIES (choose the most appropriate):\n\n"
        for i, result_class in enumerate(class_list, 1):
            result_docstring = result_class.__doc__ or f"Result entity for operations."
            target_section += f"""
{i}. {result_class.__name__}:
{result_docstring}

"""
        target_section += "Choose the result type that best fits the specific task requirements.\n"
    
    # Use custom examples if provided, otherwise use default examples (UNCHANGED)
    examples_section = custom_examples if custom_examples else components.parameter_passing_examples
    
    prompt = f"""
You are handling {goal_type} goals for the Abstractions Entity Framework.

{components.framework_context}

{components.response_options}

{target_section}

{components.available_capabilities}

{examples_section}

{components.addressing_examples}

{components.key_rules}

You MUST provide either typed_result_ecs_address, typed_result, or error.
"""
    
    return prompt


class GoalFactory:
    """Create Goal subclasses with proper typed result fields using create_model."""
    
    @classmethod
    def create_goal_class(cls, result_entity_classes: ResultEntityInput):
        """Create Goal subclass supporting single or union result types."""
        
        # Normalize input to list (NEW SWITCH CASE)
        if isinstance(result_entity_classes, list):
            # Union types case
            class_list = result_entity_classes
        else:
            # Single type case (PRESERVES CURRENT BEHAVIOR)
            class_list = [result_entity_classes]
        
        # Validate all are Entity subclasses
        for result_class in class_list:
            if not (isinstance(result_class, type) and issubclass(result_class, Entity)):
                raise ValueError(f"All classes must be Entity subclasses, got {result_class}")
        
        # Goal type derivation (NEW SWITCH CASE)
        if len(class_list) == 1:
            # Single type (PRESERVES CURRENT BEHAVIOR)
            goal_type = cls._derive_goal_type_from_class(class_list[0])
            dynamic_class_name = f"{class_list[0].__name__.replace('Result', '')}Goal"
        else:
            # Union types (NEW CASE)
            class_names = [cls._derive_goal_type_from_class(c) for c in class_list]
            goal_type = "_or_".join(class_names)
            dynamic_class_name = f"Multi{len(class_list)}PathGoal"
        
        # Typed result field creation (NEW SWITCH CASE)
        if len(class_list) == 1:
            # Single type (PRESERVES CURRENT BEHAVIOR)
            result_type_annotation = Optional[class_list[0]]
        else:
            # Union types (NEW CASE)
            result_type_annotation = Optional[Union[tuple(class_list)]]
        
        # Create dynamic goal class (UNCHANGED)
        DynamicGoal = create_model(
            dynamic_class_name,
            __base__=BaseGoal,
            __module__=__name__,
            # This is the key - typed_result field with proper type
            typed_result=(result_type_annotation, None),
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
    """Create agents with specific goal types and model selection."""
    
    DEFAULT_MODEL = 'anthropic:claude-sonnet-4-20250514'
    
    @classmethod
    def create_agent(
        cls,
        result_entity_classes: ResultEntityInput,
        custom_examples: Optional[str] = None,
        model: Optional[str] = None,
        output_retries: int = 2
    ):
        """Create agent supporting single/union result types with model selection."""
        
        # Use default model if none specified (NEW PARAMETER)
        model_name = model or cls.DEFAULT_MODEL
        
        # Create goal class (handles both single and union types)
        goal_class = GoalFactory.create_goal_class(result_entity_classes)
        
        # Derive goal type (NEW SWITCH CASE)
        if isinstance(result_entity_classes, list):
            if len(result_entity_classes) == 1:
                goal_type = GoalFactory._derive_goal_type_from_class(result_entity_classes[0])
            else:
                class_names = [GoalFactory._derive_goal_type_from_class(c) for c in result_entity_classes]
                goal_type = "_or_".join(class_names)
        else:
            # Single type case (PRESERVES CURRENT BEHAVIOR)
            goal_type = GoalFactory._derive_goal_type_from_class(result_entity_classes)
        
        # Build system prompt (handles both single and union types)
        system_prompt = build_goal_system_prompt(goal_type, result_entity_classes, custom_examples)
        
        # Create agent with specified model (NEW PARAMETER)
        agent = Agent(
            model_name,
            output_type=goal_class,
            toolsets=[registry_toolset],
            system_prompt=system_prompt,
            output_retries=output_retries
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

class AgentFunctionCallStartEvent(ProcessingEvent):
    """Event emitted when agent tool call begins."""
    type: str = "agent.tool_call.start"
    phase: EventPhase = EventPhase.STARTED
    
    # Agent-specific data
    function_name: str = Field(description="Function being called")
    raw_parameters: Dict[str, Any] = Field(default_factory=dict, description="Raw tool parameters")
    pattern_classification: Optional[str] = Field(default=None, description="Input pattern type")
    parameter_count: int = Field(default=0, description="Number of parameters")


class AgentFunctionCallCompletedEvent(ProcessedEvent):
    """Event emitted when agent tool call completes successfully."""
    type: str = "agent.tool_call.completed"
    phase: EventPhase = EventPhase.COMPLETED
    
    # Agent-specific data
    function_name: str = Field(description="Function that was called")
    result_type: str = Field(description="Type of result returned")
    entity_id: Optional[str] = Field(default=None, description="ID of result entity (single entity)")
    entity_type: Optional[str] = Field(default=None, description="Type of result entity")
    entity_count: Optional[int] = Field(default=None, description="Number of entities returned")
    entity_ids: List[str] = Field(default_factory=list, description="All entity IDs (multi-entity)")
    success: bool = Field(default=True, description="Whether execution succeeded")


class AgentFunctionCallFailedEvent(ProcessingEvent):
    """Event emitted when agent tool call fails."""
    type: str = "agent.tool_call.failed"
    phase: EventPhase = EventPhase.FAILED
    
    # Agent-specific data  
    function_name: str = Field(description="Function that failed")
    error_type: str = Field(description="Type of error")
    failed_parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters that caused failure")


class AgentListFunctionsEvent(CreatedEvent):
    """Event emitted when agent lists available functions."""
    type: str = "agent.list_functions"
    phase: EventPhase = EventPhase.STARTED
    
class AgentListFunctionsCompletedEvent(ProcessedEvent):
    """Event emitted when agent successfully lists functions."""
    type: str = "agent.list_functions.completed"
    phase: EventPhase = EventPhase.COMPLETED
    
    # Agent-specific data
    total_functions: int = Field(default=0, description="Total number of functions listed")
    function_list: FunctionList = Field(description="List of available functions with metadata")


@registry_toolset.tool
@emit_events(
    creating_factory=lambda function_name, **kwargs: AgentFunctionCallStartEvent(
        process_name="execute_function",
        function_name=function_name,
        raw_parameters=kwargs,
        parameter_count=len(kwargs)
    ),
    created_factory=lambda result, function_name, **kwargs: AgentFunctionCallCompletedEvent(
        process_name="execute_function",
        function_name=function_name,
        result_type=result.result_type if hasattr(result, 'result_type') else "unknown",
        entity_id=result.entity_id if hasattr(result, 'entity_id') else None,
        entity_type=result.entity_type if hasattr(result, 'entity_type') else None,
        entity_count=result.entity_count if hasattr(result, 'entity_count') else None,
        entity_ids=(
            result.debug_info.get('entity_ids', [])
            if hasattr(result, 'debug_info') and isinstance(result.debug_info, dict)
            else []
        ),
        success=result.success if hasattr(result, 'success') else True,
        output_ids=(
            result.debug_info.get('entity_ids', [])
            if hasattr(result, 'debug_info') and isinstance(result.debug_info, dict)
            else []
        )
    ),
    failed_factory=lambda error, function_name, **kwargs: AgentFunctionCallFailedEvent(
        process_name="execute_function",
        function_name=function_name,
        error_type=type(error).__name__,
        failed_parameters=kwargs,
        error=str(error)
    )
)
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


