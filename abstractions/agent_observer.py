"""
All Agent Execution Patterns Test - Clean Generic Implementation

This file demonstrates all 9 agent execution patterns with completely generic
ASCII formatting that works for any function - no hardcoded entity searches.

Based on the proven approach from event_tracking_test.py.
"""

import asyncio
from typing import Any, Dict, Optional, List, Tuple
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime

# Import event system
from abstractions.events.events import (
    Event, EventPhase, emit_events, on, get_event_bus,
    ProcessingEvent, ProcessedEvent
)

# Import entity system components
from abstractions.ecs.entity import Entity
from abstractions.ecs.callable_registry import CallableRegistry

# Import the original execution result model and new event classes
from abstractions.registry_agent import (
    ExecutionResult, AgentFunctionCallStartEvent, AgentFunctionCallCompletedEvent,
    AgentListFunctionsCompletedEvent, AgentGetFunctionSignatureCompletedEvent,
    AgentGetAllLineagesCompletedEvent, AgentGetLineageHistoryCompletedEvent,
    AgentGetEntityCompletedEvent
)


# ============================================================================
# GENERIC ASCII FORMATTER - NO HARDCODED SEARCHES
# ============================================================================

class GenericASCIIFormatter:
    """Generic ASCII formatter that works for any function execution."""
    
    def extract_entity_type_from_completion_event(self, completion_event) -> str:
        """
        Generic entity type extraction from ExecutionResult data.
        No hardcoded event searches - works for any function.
        """
        # Check if completion event has entity_type directly
        if hasattr(completion_event, 'entity_type') and completion_event.entity_type:
            return completion_event.entity_type
            
        # For single entity results, try to get the type from the EntityRegistry
        entity_id = getattr(completion_event, 'entity_id', None)
        if entity_id:
            try:
                from abstractions.ecs.entity import EntityRegistry
                from uuid import UUID
                
                # Convert string to UUID if needed
                if isinstance(entity_id, str):
                    entity_uuid = UUID(entity_id)
                else:
                    entity_uuid = entity_id
                
                # Get root_ecs_id for this entity
                root_ecs_id = EntityRegistry.ecs_id_to_root_id.get(entity_uuid)
                if root_ecs_id:
                    # Query the actual entity to get its type
                    actual_entity = EntityRegistry.get_stored_entity(root_ecs_id, entity_uuid)
                    if actual_entity:
                        return type(actual_entity).__name__
            except Exception:
                pass  # Fall back if EntityRegistry query fails
        
        # For multi-entity results
        if hasattr(completion_event, 'result_type') and completion_event.result_type == "entity_list":
            return "MultipleEntities"
        
        return "Entity"  # Fallback


formatter = GenericASCIIFormatter()





def format_from_bus_queries(start_event: Event, completion_event: Event, entity_type: str, bus) -> str:
    """Generic formatting using EventBus queries - no hardcoded patterns."""
    
    # Extract data directly from events
    function_name = getattr(start_event, 'function_name', 'unknown')
    raw_parameters = getattr(start_event, 'raw_parameters', {})
    start_time = start_event.timestamp
    
    # Extract timing
    end_time = completion_event.timestamp
    total_ms = (end_time - start_time).total_seconds() * 1000
    
    # Extract result info
    result_type = getattr(completion_event, 'result_type', 'unknown')
    entity_id = getattr(completion_event, 'entity_id', None)
    entity_count = getattr(completion_event, 'entity_count', None)
    
    # Find function execution duration from siblings
    execution_ms = 0.0
    siblings = bus.get_siblings(completion_event.id)
    for sibling in siblings:
        if (hasattr(sibling, 'process_name') and 
            sibling.process_name == "function_execution" and 
            sibling.phase.value == "completed"):
            execution_ms = getattr(sibling, 'duration_ms', 0.0) or 0.0
            break
    
    resolution_ms = max(0.0, total_ms - execution_ms)
    
    # Build the ASCII display
    lines = []
    
    # Header
    lines.append(f"⏱️  START: {start_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z")
    lines.append("")
    
    # Function signature - get REAL signature from CallableRegistry and clean it
    try:
        function_info = CallableRegistry.get_function_info(function_name)
        if function_info and 'signature' in function_info:
            # Use the actual function signature and clean __main__ references
            real_signature = function_info['signature']
            clean_signature = real_signature.replace('__main__.', '')
            lines.append(f"🚀 {clean_signature}")
        else:
            # Fallback if function not found in registry
            lines.append(f"🚀 {function_name}(...) -> {entity_type}")
    except Exception as e:
        # Final fallback
        lines.append(f"🚀 {function_name}(...) -> {entity_type}")
    lines.append("")
    
    # Raw tool call
    lines.append("📝 RAW TOOL CALL: {")
    for param_name, param_value in raw_parameters.items():
        if hasattr(param_value, 'ecs_id'):
            lines.append(f'   "{param_name}": "@{param_value.ecs_id}",')
        else:
            lines.append(f'   "{param_name}": {repr(param_value)},')
    lines.append("}")
    lines.append("")
    
    # Resolution steps - resolve actual values through EntityRegistry
    if raw_parameters:
        lines.append("🔍 RESOLVING:")
        for param_name, param_value in raw_parameters.items():
            if isinstance(param_value, str) and param_value.startswith('@'):
                # String address - resolve through EntityRegistry to get real types and values
                lines.append(f"   {param_name}: \"{param_value}\"")
                try:
                    from abstractions.ecs.ecs_address_parser import ECSAddressParser
                    from abstractions.ecs.entity import EntityRegistry
                    from uuid import UUID
                    
                    if '.' in param_value:
                        # Field borrowing: @uuid.field - resolve to actual value
                        resolved_value = ECSAddressParser.resolve_address(param_value)
                        entity_uuid, field_path = ECSAddressParser.parse_address(param_value)
                        field_name = field_path[0]
                        
                        # Get actual entity type
                        root_ecs_id = EntityRegistry.ecs_id_to_root_id.get(entity_uuid)
                        if root_ecs_id:
                            entity = EntityRegistry.get_stored_entity(root_ecs_id, entity_uuid)
                            if entity:
                                entity_type_name = type(entity).__name__
                                full_id = str(entity_uuid)
                                lines.append(f"   → @{entity_type_name}|{full_id} : {field_name} = {repr(resolved_value)}")
                            else:
                                full_id = str(entity_uuid)
                                lines.append(f"   → @Entity|{full_id} : {field_name} = {repr(resolved_value)}")
                        else:
                            full_id = str(entity_uuid)
                            lines.append(f"   → @Entity|{full_id} : {field_name} = {repr(resolved_value)}")
                    else:
                        # Direct entity reference: @uuid - get actual entity type
                        entity_uuid = UUID(param_value[1:])  # Remove @ and convert to UUID
                        root_ecs_id = EntityRegistry.ecs_id_to_root_id.get(entity_uuid)
                        if root_ecs_id:
                            entity = EntityRegistry.get_stored_entity(root_ecs_id, entity_uuid)
                            if entity:
                                entity_type_name = type(entity).__name__
                                full_id = str(entity_uuid)
                                lines.append(f"   → @{entity_type_name}|{full_id} [direct entity reference]")
                            else:
                                full_id = str(entity_uuid)
                                lines.append(f"   → @Entity|{full_id} [direct entity reference]")
                        else:
                            full_id = str(entity_uuid)
                            lines.append(f"   → @Entity|{full_id} [direct entity reference]")
                except Exception:
                    # Fallback to generic display
                    if '.' in param_value:
                        parts = param_value.split('.')
                        entity_part = parts[0][1:]
                        field_part = parts[1]
                        lines.append(f"   → @Entity|{entity_part} : {field_part} = <unresolved>")
                    else:
                        entity_id = param_value[1:]
                        lines.append(f"   → @Entity|{entity_id} [direct entity reference]")
                lines.append("")
            elif hasattr(param_value, 'ecs_id') and not isinstance(param_value, str):
                # Direct entity reference
                entity_type_name = type(param_value).__name__
                full_id = str(param_value.ecs_id)
                lines.append(f"   {param_name}: \"@{param_value.ecs_id}\"")
                lines.append(f"   → @{entity_type_name}|{full_id} [direct entity reference]")
                lines.append("")
    
    # Function call - show actual resolved values and entity types
    call_params = []
    for param_name, param_value in raw_parameters.items():
        if isinstance(param_value, str) and param_value.startswith('@'):
            try:
                from abstractions.ecs.ecs_address_parser import ECSAddressParser
                from abstractions.ecs.entity import EntityRegistry
                from uuid import UUID
                
                if '.' in param_value:
                    # Field borrowing - show actual resolved value
                    resolved_value = ECSAddressParser.resolve_address(param_value)
                    call_params.append(f"{param_name}={repr(resolved_value)}")
                else:
                    # Direct entity reference - show actual entity type
                    entity_uuid = UUID(param_value[1:])  # Remove @
                    root_ecs_id = EntityRegistry.ecs_id_to_root_id.get(entity_uuid)
                    if root_ecs_id:
                        entity = EntityRegistry.get_stored_entity(root_ecs_id, entity_uuid)
                        if entity:
                            entity_type_name = type(entity).__name__
                            full_id = str(entity_uuid)
                            call_params.append(f"{param_name}={entity_type_name}|{full_id}")
                        else:
                            full_id = str(entity_uuid)
                            call_params.append(f"{param_name}=Entity|{full_id}")
                    else:
                        full_id = str(entity_uuid)
                        call_params.append(f"{param_name}=Entity|{full_id}")
            except Exception:
                # Fallback
                if '.' in param_value:
                    call_params.append(f"{param_name}=<unresolved>")
                else:
                    entity_id = param_value[1:]
                    call_params.append(f"{param_name}=Entity|{entity_id}")
        elif hasattr(param_value, 'ecs_id') and not isinstance(param_value, str):
            # Direct entity reference
            entity_type_name = type(param_value).__name__
            full_id = str(param_value.ecs_id)
            call_params.append(f"{param_name}={entity_type_name}|{full_id}")
        else:
            call_params.append(f"{param_name}={repr(param_value)}")
    
    call_signature = f"{function_name}({', '.join(call_params)})"
    lines.append(f"📥 FUNCTION CALL: {call_signature}")
    lines.append("")
    
    # Output - handle both single and multi-entity using entity_ids
    entity_ids = getattr(completion_event, 'entity_ids', [])
    
    if entity_ids and len(entity_ids) > 0:
        # Multi-entity case - show proper entity information
        if len(entity_ids) == 1:
            lines.append(f"📤 OUTPUT: {entity_type}#{entity_ids[0]}")
            lines.append(f"   ├─ entity_type: \"{entity_type}\"")
            lines.append(f"   ├─ result_type: \"{result_type}\"")
            lines.append(f"   ├─ success: true")
            lines.append("")
        else:
            first_id = entity_ids[0]
            lines.append(f"📤 OUTPUT: {len(entity_ids)} entities (first: {entity_type}#{first_id})")
            lines.append(f"   ├─ entity_count: {len(entity_ids)}")
            lines.append(f"   ├─ entity_type: \"{entity_type}\"")
            lines.append(f"   ├─ result_type: \"{result_type}\"")
            lines.append(f"   ├─ success: true")
            lines.append("")
    elif entity_id:
        # Single entity case
        if entity_count and entity_count > 1:
            lines.append(f"📤 OUTPUT: {entity_count} entities (first: {entity_type}#{entity_id})")
            lines.append(f"   ├─ entity_count: {entity_count}")
            lines.append(f"   ├─ result_type: \"{result_type}\"")
            lines.append(f"   ├─ success: true")
            lines.append("")
        else:
            lines.append(f"📤 OUTPUT: {entity_type}#{entity_id}")
            lines.append(f"   ├─ entity_type: \"{entity_type}\"")
            lines.append(f"   ├─ result_type: \"{result_type}\"")
            lines.append(f"   ├─ success: true")
            lines.append("")
    
    # Entity flow - show actual entity types from EntityRegistry
    input_entities = []
    for param_name, param_value in raw_parameters.items():
        if isinstance(param_value, str) and param_value.startswith('@'):
            try:
                from abstractions.ecs.entity import EntityRegistry
                from uuid import UUID
                
                # Extract entity UUID from string address
                if '.' in param_value:
                    # Field borrowing: @uuid.field -> just the entity
                    entity_uuid = UUID(param_value.split('.')[0][1:])  # Remove @ and get UUID
                else:
                    # Direct entity: @uuid
                    entity_uuid = UUID(param_value[1:])  # Remove @
                
                # Get actual entity type from EntityRegistry
                root_ecs_id = EntityRegistry.ecs_id_to_root_id.get(entity_uuid)
                if root_ecs_id:
                    entity = EntityRegistry.get_stored_entity(root_ecs_id, entity_uuid)
                    if entity:
                        entity_type_name = type(entity).__name__
                        input_entities.append(f"{entity_type_name}|{str(entity_uuid)}")
                    else:
                        input_entities.append(f"Entity|{str(entity_uuid)}")
                else:
                    input_entities.append(f"Entity|{str(entity_uuid)}")
            except Exception:
                # Fallback to generic entity display
                if '.' in param_value:
                    entity_id_str = param_value.split('.')[0][1:]
                else:
                    entity_id_str = param_value[1:]
                input_entities.append(f"Entity|{entity_id_str}")
        elif hasattr(param_value, 'ecs_id') and not isinstance(param_value, str):
            # Direct entity reference
            entity_type_name = type(param_value).__name__
            full_id = str(param_value.ecs_id)
            input_entities.append(f"{entity_type_name}|{full_id}")
    
    # Output entities - handle single and multi-entity cases using entity_ids
    output_entities = []
    
    # Check if completion_event has entity_ids (multi-entity case)
    entity_ids = getattr(completion_event, 'entity_ids', [])
    
    if entity_ids and len(entity_ids) > 0:
        # Multi-entity case - get ACTUAL entity types from EntityRegistry for each entity
        output_entities = []
        for eid in entity_ids:
            try:
                from abstractions.ecs.entity import EntityRegistry
                from uuid import UUID
                
                # Convert string to UUID if needed
                entity_uuid = UUID(eid) if isinstance(eid, str) else eid
                
                # Get root_ecs_id for this entity
                root_ecs_id = EntityRegistry.ecs_id_to_root_id.get(entity_uuid)
                if root_ecs_id:
                    # Query the actual entity to get its real type
                    actual_entity = EntityRegistry.get_stored_entity(root_ecs_id, entity_uuid)
                    if actual_entity:
                        actual_type = type(actual_entity).__name__
                        output_entities.append(f"{actual_type}|{eid}")
                    else:
                        output_entities.append(f"Entity|{eid}")
                else:
                    output_entities.append(f"Entity|{eid}")
            except Exception:
                # Fallback - use the generic entity_type from the event
                output_entities.append(f"{entity_type}|{eid}")
    elif entity_id:
        # Single entity case - use entity_id field
        if entity_count and entity_count > 1:
            # Fallback: show count
            output_entities.append(f"{entity_count} {entity_type} entities")
        else:
            output_entities.append(f"{entity_type}|{entity_id}")
    
    # Remove duplicates from input entities while preserving order
    seen = set()
    unique_input_entities = []
    for entity in input_entities:
        if entity not in seen:
            unique_input_entities.append(entity)
            seen.add(entity)
    input_entities = unique_input_entities
    
    if not input_entities:
        input_entities = ["No entities"]
    if not output_entities:
        output_entities = ["No entities"]
    
    # Entity flow with REAL function name and REAL execution UUID (FULL UUID)
    execution_id = str(completion_event.id) if hasattr(completion_event, 'id') else "unknown"
    flow_line = f"[{', '.join(input_entities)}] ---> [{function_name}|{execution_id}] ---> [{', '.join(output_entities)}]"
    lines.append(flow_line)
    lines.append("")
    
    # Timing breakdown
    lines.append(f"⏱️  END: {end_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z")
    if resolution_ms > 0:
        lines.append(f"🔍 RESOLUTION: {resolution_ms:.1f}ms")
    lines.append(f"📥 EXECUTION: {execution_ms:.1f}ms")
    lines.append(f"✅ TOTAL: {total_ms:.1f}ms")
    
    return "\n".join(lines)

@on(AgentFunctionCallCompletedEvent)
async def format_and_display_execution(event: AgentFunctionCallCompletedEvent):
    """Generic detector using ExecutionResult - works for any function!"""
    print(f"\n🎨 AGENT TOOL: Detected completed agent tool call for function call with name: {event.function_name}")
    
    try:
        # Get EventBus and use history to find related events
        bus = get_event_bus()
        
        # Get recent history to find related events by lineage_id or function_name
        history = bus.get_history(limit=100)
        
        # Find start event by function_name and recent timing
        start_event = None
        for hist_event in reversed(history):  # Recent events first
            if (hist_event.type == "agent.tool_call.start" and
                isinstance(hist_event, AgentFunctionCallStartEvent) and
                hist_event.function_name == event.function_name):
                # Check if it's reasonably recent (within last 10 seconds)
                time_diff = (event.timestamp - hist_event.timestamp).total_seconds()
                if time_diff < 10:
                    start_event = hist_event
                    break
        
        if not start_event:
            print("⚠️  Could not find start event in recent history")
            return
        
        # ✅ GENERIC: Use ExecutionResult-based extraction instead of event searches
        entity_type = formatter.extract_entity_type_from_completion_event(event)
        print(f"🎯 Entity type extracted from ExecutionResult: {entity_type}")
        
        # Format directly using the generic approach
        ascii_display = format_from_bus_queries(start_event, event, entity_type, bus)
        
        print(f"\n{'='*60}")
        print(f"🎯EXECUTION TRACE")
        print(f"{'='*60}")
        print(ascii_display)
        print(f"{'='*60}")
            
    except Exception as e:
        print(f"❌ Error in ASCII formatting: {e}")
        import traceback
        traceback.print_exc()


# ============================================================================
# SIMPLE EVENT OBSERVERS FOR REGISTRY AGENT TOOLS
# ============================================================================

@on(AgentListFunctionsCompletedEvent)
async def on_list_functions_completed(event: AgentListFunctionsCompletedEvent):
    """Simple observer for list_functions completion."""
    print(f"\n🎨 AGENT TOOL: Detected completed agent tool call for list_functions")
    print(f"📋 Listed {event.total_functions} functions")


@on(AgentGetFunctionSignatureCompletedEvent)
async def on_get_function_signature_completed(event: AgentGetFunctionSignatureCompletedEvent):
    """Simple observer for get_function_signature completion."""
    print(f"\n🎨 AGENT TOOL: Detected completed agent tool call for get_function_signature")
    if event.signature_found:
        print(f"📝 Found signature for function: {event.function_name}")
    else:
        print(f"❌ Function not found: {event.function_name}")


@on(AgentGetAllLineagesCompletedEvent)
async def on_get_all_lineages_completed(event: AgentGetAllLineagesCompletedEvent):
    """Simple observer for get_all_lineages completion."""
    print(f"\n🎨 AGENT TOOL: Detected completed agent tool call for get_all_lineages")
    print(f"🌳 Found {event.total_lineages} lineages")


@on(AgentGetLineageHistoryCompletedEvent)
async def on_get_lineage_history_completed(event: AgentGetLineageHistoryCompletedEvent):
    """Simple observer for get_lineage_history completion."""
    print(f"\n🎨 AGENT TOOL: Detected completed agent tool call for get_lineage_history")
    if event.history_found:
        versions = event.total_versions or 0
        print(f"📈 Found lineage history: {event.target_lineage_id} ({versions} versions)")
    else:
        print(f"❌ Lineage not found: {event.target_lineage_id}")


@on(AgentGetEntityCompletedEvent)
async def on_get_entity_completed(event: AgentGetEntityCompletedEvent):
    """Simple observer for get_entity completion."""
    print(f"\n🎨 AGENT TOOL: Detected completed agent tool call for get_entity")
    if event.entity_found:
        entity_type = event.entity_type or "Entity"
        print(f"🎯 Found entity: {entity_type}#{event.ecs_id}")
    else:
        print(f"❌ Entity not found: {event.ecs_id} in root {event.root_ecs_id}")