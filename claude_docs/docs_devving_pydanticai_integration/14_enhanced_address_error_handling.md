# Enhanced Address Error Handling for Pydantic-AI Integration

## Key Discovery: Rich Error Handling System

The `ecs_address_parser.py` provides sophisticated debugging capabilities that we should integrate into our pydantic-ai tools to give users **impressive debugging help** when they make address syntax mistakes.

## ECS Address Parser Capabilities

### 1. Address Validation and Parsing
```python
from abstractions.ecs.ecs_address_parser import ECSAddressParser

# Multiple parsing methods with different capabilities
ECSAddressParser.parse_address(address)           # Basic parsing
ECSAddressParser.parse_address_flexible(address)  # Supports @uuid only
ECSAddressParser.validate_address_format(address) # Format validation only
ECSAddressParser.is_ecs_address(address)         # Quick format check
```

### 2. Advanced Resolution with Type Detection
```python
# Returns (value, resolution_type) where type is:
# "entity" | "field_value" | "sub_entity"
value, resolution_type = ECSAddressParser.resolve_address_advanced(address)
```

### 3. Input Pattern Classification  
```python
from abstractions.ecs.ecs_address_parser import InputPatternClassifier

# Classify user input patterns
pattern_type, classifications = InputPatternClassifier.classify_kwargs_advanced(kwargs)
# pattern_type: "pure_borrowing" | "pure_transactional" | "mixed" | "direct"
```

### 4. Dependency Tracking
```python
from abstractions.ecs.ecs_address_parser import EntityReferenceResolver

resolver = EntityReferenceResolver()
resolved_data, entity_ids = resolver.resolve_references(data)
summary = resolver.get_dependency_summary()
```

## Enhanced Error Wrapper Implementation

```python
import json
from typing import Any, Dict, Optional, Tuple
from abstractions.ecs.ecs_address_parser import (
    ECSAddressParser, 
    InputPatternClassifier,
    EntityReferenceResolver
)
from abstractions.ecs.entity import EntityRegistry
from uuid import UUID

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
            entity_id, field_path = ECSAddressParser.parse_address_flexible(address)
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
                "Use list_lineages() to see available entities"
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

def create_enhanced_error_response(error_type: str, base_error: str, debug_info: Dict[str, Any]) -> str:
    """Create a comprehensive error response for the agent."""
    response = {
        "success": False,
        "error_type": error_type,
        "error_message": base_error,
        "debug_info": debug_info,
        "helpful_commands": [
            "list_functions() - See available functions",
            "get_all_lineages() - See available entities", 
            "get_function_signature(function_name) - See parameter requirements"
        ]
    }
    
    return json.dumps(response, indent=2, default=str)
```

## Enhanced Execute Function Tool

```python
@registry_toolset.tool
async def execute_function(function_name: str, **kwargs) -> str:
    """
    Execute a registered function with enhanced address debugging.
    
    Provides comprehensive error analysis when address syntax is incorrect.
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
            return create_enhanced_error_response(
                "address_validation_error",
                f"Address validation failed for {len(failed_addresses)} parameter(s)",
                {
                    "function_name": function_name,
                    "failed_addresses": failed_addresses,
                    "parameter_analysis": param_analysis
                }
            )
        
        # If validation passed, execute the function
        result = CallableRegistry.execute(function_name, **kwargs)
        
        return json.dumps({
            "success": True,
            "function_name": function_name,
            "result": serialize_entity_result(result),
            "parameter_analysis": param_analysis  # Include for reference
        }, default=str)
        
    except Exception as e:
        # Even for non-address errors, provide helpful context
        return create_enhanced_error_response(
            "execution_error",
            str(e),
            {
                "function_name": function_name,
                "parameters": list(kwargs.keys()),
                "suggestion": "Use get_function_signature() to see expected parameters"
            }
        )
```

## Example Enhanced Error Responses

### Invalid Address Format
```json
{
  "success": false,
  "error_type": "address_validation_error",
  "debug_info": {
    "address": "@invalid-uuid.name",
    "validation_steps": ["✓ Starts with @"],
    "error_type": "invalid_address_format",
    "error_message": "Invalid ECS address format",
    "suggestions": [
      "Check UUID format: @xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx.field",
      "Ensure no special characters except hyphens in UUID part"
    ]
  }
}
```

### Entity Not Found
```json
{
  "success": false,
  "error_type": "address_validation_error", 
  "debug_info": {
    "address": "@f65cf3bd-9392-499f-8f57-dba701f50000.name",
    "validation_steps": [
      "✓ Starts with @",
      "✓ Valid ECS address format", 
      "✓ Parsed: UUID=f65cf3bd-9392-499f-8f57-dba701f50000"
    ],
    "error_type": "entity_not_found",
    "suggestions": [
      "Verify the UUID is correct",
      "Use list_lineages() to see available entities",
      "Similar entities found: ['f65cf3bd-9392-499f-8f57-dba701f5069c']"
    ]
  }
}
```

### Field Not Found
```json
{
  "success": false,
  "error_type": "address_validation_error",
  "debug_info": {
    "validation_steps": [
      "✓ Starts with @",
      "✓ Valid ECS address format",
      "✓ Parsed: UUID=f65cf3bd-9392-499f-8f57-dba701f5069c, fields=[naem]",
      "✓ Entity exists in root f65cf3bd-9392-499f-8f57-dba701f5069c"
    ],
    "error_type": "resolution_error",
    "available_fields": ["name", "gpa", "age", "status"],
    "suggestions": ["Similar fields available: ['name']"]
  }
}
```

This enhanced error handling will provide users with **impressive debugging help** that guides them to correct their address syntax mistakes with specific, actionable suggestions!