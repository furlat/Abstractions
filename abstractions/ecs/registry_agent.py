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

from typing import Any, Dict, Optional, Tuple, List
from uuid import UUID
from pydantic import BaseModel, Field

from pydantic_ai import Agent
from pydantic_ai.toolsets.function import FunctionToolset

# Direct imports from abstractions - leveraging singleton architecture
from abstractions.ecs.callable_registry import CallableRegistry
from abstractions.ecs.entity import EntityRegistry, Entity
from abstractions.ecs.ecs_address_parser import (
    ECSAddressParser, 
    InputPatternClassifier,
    EntityReferenceResolver
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


# Agent response model
class GoalAchieved(BaseModel):
    """
    Structured response indicating the agent has completed the user's request.
    
    This provides typed, structured responses instead of unstructured text,
    making the agent output more reliable and easier to process programmatically.
    """
    goal_completed: bool
    primary_action: str  # "function_execution", "data_retrieval", "error_handling", etc.
    summary: str  # Brief summary of what was accomplished
    data: Optional[Dict[str, Any]] = None  # Structured data results
    recommendations: List[str] = Field(default_factory=list)  # Next steps or suggestions
    errors: List[str] = Field(default_factory=list)  # Any errors encountered
    entity_ids_referenced: List[str] = Field(default_factory=list)  # UUIDs mentioned/used
    functions_used: List[str] = Field(default_factory=list)  # Functions called


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
def get_function_signature(function_name: str) -> FunctionInfo:
    """Get detailed function signature and type information."""
    info = CallableRegistry.get_function_info(function_name)
    if not info:
        raise ValueError(f"Function '{function_name}' not found")
    
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
def get_lineage_history(lineage_id: str) -> LineageInfo:
    """Get complete version history for a specific lineage."""
    lineage_uuid = UUID(lineage_id)
    root_ids = EntityRegistry.lineage_registry.get(lineage_uuid, [])
    
    if not root_ids:
        raise ValueError(f"Lineage {lineage_id} not found")
    
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
        raise ValueError(f"Unable to retrieve entity data for lineage {lineage_id}")


@registry_toolset.tool
def get_entity(root_ecs_id: str, ecs_id: str) -> EntityInfo:
    """Retrieve specific entity with complete details."""
    root_uuid = UUID(root_ecs_id)
    entity_uuid = UUID(ecs_id)
    
    entity = EntityRegistry.get_stored_entity(root_uuid, entity_uuid)
    if not entity:
        raise ValueError(f"Entity {ecs_id} not found in root {root_ecs_id}")
    
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


# Create the agent with comprehensive system prompt
registry_agent = Agent(
    'anthropic:claude-sonnet-4-20250514',
    output_type=GoalAchieved,
    toolsets=[registry_toolset],
    system_prompt="""
    You are an assistant for the Abstractions Entity Framework that returns structured GoalAchieved responses.
    
    The framework is a functional data processing system where:
    - Entities are immutable data units with global identity
    - Functions transform entities and are tracked in a registry
    - All operations maintain complete provenance and lineage
    - String addressing allows distributed data access (@uuid.field syntax)
    
    Available capabilities:
    - execute_function(function_name, **kwargs) - Execute registered functions with enhanced error handling
    - list_functions() - Show available functions with metadata  
    - get_function_signature(function_name) - Get function type information
    - get_all_lineages() - Show all entity lineages and versions
    - get_lineage_history(lineage_id) - Get version history for specific lineage
    - get_entity(root_ecs_id, ecs_id) - Get specific entity details
    
    IMPORTANT: You must always return a GoalAchieved response with:
    - goal_completed: true if the user's request was fulfilled, false if errors occurred
    - primary_action: the main type of action performed ("function_execution", "data_retrieval", "exploration", "error_handling")
    - summary: a clear, concise summary of what was accomplished
    - data: structured results from tools (if any)
    - recommendations: helpful next steps for the user
    - errors: any errors encountered
    - entity_ids_referenced: list of UUIDs mentioned or accessed
    - functions_used: list of functions that were called
    
    For function execution, you can use @uuid.field syntax. The system provides impressive debugging
    help for address syntax errors. Always provide actionable recommendations and track all entity
    IDs and functions used in your structured response.
    """
)


if __name__ == "__main__":
    # Example usage
    
    result = registry_agent.run_sync(
        "List all available functions and show me the entity lineages"
    )
    print("Agent Response:")
    print(result.output)