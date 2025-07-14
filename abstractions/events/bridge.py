"""
Event Bridge Functions - Simple event emission for any BaseModel objects

This module provides simple functions to emit events for BaseModel objects
without requiring decorators or complex instrumentation. Used for testing
and validation of the event system before ECS integration.
"""

from typing import List, Dict, Any, Optional, Type
from uuid import UUID, uuid4
from pydantic import BaseModel
import asyncio
import time

from abstractions.events.events import (
    Event, EventPhase, get_event_bus,
    CreatingEvent, CreatedEvent,
    ModifyingEvent, ModifiedEvent,
    ProcessingEvent, ProcessedEvent,
    DeletingEvent, DeletedEvent,
    ValidatingEvent, ValidatedEvent,
    StateTransitionEvent
)


async def emit_creation_events(obj: BaseModel, operation_name: str = "create") -> None:
    """
    Emit creation events for any BaseModel object.
    
    Args:
        obj: The object being created
        operation_name: Name of the operation (for metadata)
    """
    bus = get_event_bus()
    
    # Get object ID (try common ID fields)
    obj_id = getattr(obj, 'id', None) or getattr(obj, 'ecs_id', None) or uuid4()
    
    # Create creating event
    creating = CreatingEvent(
        subject_type=type(obj),
        subject_id=obj_id,
        metadata={
            'operation': operation_name,
            'object_class': obj.__class__.__name__
        }
    )
    
    # Create completion generator
    async def complete_creation():
        return CreatedEvent(
            subject_type=type(obj),
            subject_id=obj_id,
            created_id=obj_id,
            lineage_id=creating.lineage_id,
            metadata={
                'operation': operation_name,
                'object_class': obj.__class__.__name__
            }
        )
    
    # Use parent-child pattern
    await bus.emit_with_children(creating, [complete_creation])


async def emit_modification_events(
    obj: BaseModel, 
    fields: List[str],
    old_values: Optional[Dict[str, Any]] = None,
    operation_name: str = "modify"
) -> None:
    """
    Emit modification events for any BaseModel object.
    
    Args:
        obj: The object being modified
        fields: List of field names being modified
        old_values: Dictionary of old values (optional)
        operation_name: Name of the operation
    """
    bus = get_event_bus()
    
    # Get object ID
    obj_id = getattr(obj, 'id', None) or getattr(obj, 'ecs_id', None) or uuid4()
    
    # Get current values
    new_values = {}
    for field in fields:
        if hasattr(obj, field):
            new_values[field] = getattr(obj, field)
    
    # Create modifying event
    modifying = ModifyingEvent(
        subject_type=type(obj),
        subject_id=obj_id,
        fields=fields,
        metadata={
            'operation': operation_name,
            'object_class': obj.__class__.__name__
        }
    )
    
    # Create completion generator
    async def complete_modification():
        return ModifiedEvent(
            subject_type=type(obj),
            subject_id=obj_id,
            fields=fields,
            old_values=old_values or {},
            new_values=new_values,
            lineage_id=modifying.lineage_id,
            metadata={
                'operation': operation_name,
                'object_class': obj.__class__.__name__
            }
        )
    
    # Use parent-child pattern
    await bus.emit_with_children(modifying, [complete_modification])


async def emit_processing_events(
    process_name: str,
    inputs: Optional[List[BaseModel]] = None,
    outputs: Optional[List[BaseModel]] = None,
    subject: Optional[BaseModel] = None
) -> None:
    """
    Emit processing events for any operation.
    
    Args:
        process_name: Name of the process being executed
        inputs: List of input objects (optional)
        outputs: List of output objects (optional) 
        subject: Main subject of the processing (optional)
    """
    bus = get_event_bus()
    
    # Extract input IDs
    input_ids = []
    if inputs:
        for inp in inputs:
            inp_id = getattr(inp, 'id', None) or getattr(inp, 'ecs_id', None)
            if inp_id:
                input_ids.append(inp_id)
    
    # Determine subject
    subject_type = None
    subject_id = None
    if subject:
        subject_type = type(subject)
        subject_id = getattr(subject, 'id', None) or getattr(subject, 'ecs_id', None)
    elif inputs:
        # Use first input as subject
        subject_type = type(inputs[0])
        subject_id = getattr(inputs[0], 'id', None) or getattr(inputs[0], 'ecs_id', None)
    
    # Create processing event
    processing = ProcessingEvent(
        subject_type=subject_type,
        subject_id=subject_id,
        process_name=process_name,
        input_ids=input_ids,
        metadata={
            'input_count': len(inputs) if inputs else 0,
            'process_type': 'functional'
        }
    )
    
    # Create completion generator
    async def complete_processing():
        # Extract output IDs
        output_ids = []
        if outputs:
            for out in outputs:
                out_id = getattr(out, 'id', None) or getattr(out, 'ecs_id', None)
                if out_id:
                    output_ids.append(out_id)
        
        return ProcessedEvent(
            subject_type=subject_type,
            subject_id=subject_id,
            process_name=process_name,
            output_ids=output_ids,
            lineage_id=processing.lineage_id,
            result_summary={
                'input_count': len(inputs) if inputs else 0,
                'output_count': len(outputs) if outputs else 0,
                'success': True
            },
            metadata={
                'process_type': 'functional'
            }
        )
    
    # Use parent-child pattern
    await bus.emit_with_children(processing, [complete_processing])


async def emit_deletion_events(obj: BaseModel, operation_name: str = "delete") -> None:
    """
    Emit deletion events for any BaseModel object.
    
    Args:
        obj: The object being deleted
        operation_name: Name of the operation
    """
    bus = get_event_bus()
    
    # Get object ID
    obj_id = getattr(obj, 'id', None) or getattr(obj, 'ecs_id', None) or uuid4()
    
    # Create deleting event
    deleting = DeletingEvent(
        subject_type=type(obj),
        subject_id=obj_id,
        metadata={
            'operation': operation_name,
            'object_class': obj.__class__.__name__
        }
    )
    
    # Create completion generator
    async def complete_deletion():
        return DeletedEvent(
            subject_type=type(obj),
            subject_id=obj_id,
            lineage_id=deleting.lineage_id,
            metadata={
                'operation': operation_name,
                'object_class': obj.__class__.__name__
            }
        )
    
    # Use parent-child pattern
    await bus.emit_with_children(deleting, [complete_deletion])


async def emit_validation_events(
    obj: BaseModel, 
    validation_type: str = "schema",
    is_valid: bool = True,
    errors: Optional[List[str]] = None
) -> None:
    """
    Emit validation events for any BaseModel object.
    
    Args:
        obj: The object being validated
        validation_type: Type of validation being performed
        is_valid: Whether validation passed
        errors: List of validation errors (if any)
    """
    bus = get_event_bus()
    
    # Get object ID
    obj_id = getattr(obj, 'id', None) or getattr(obj, 'ecs_id', None) or uuid4()
    
    # Create validating event
    validating = ValidatingEvent(
        subject_type=type(obj),
        subject_id=obj_id,
        validation_type=validation_type,
        metadata={
            'object_class': obj.__class__.__name__
        }
    )
    
    # Create completion generator
    async def complete_validation():
        return ValidatedEvent(
            subject_type=type(obj),
            subject_id=obj_id,
            validation_type=validation_type,
            is_valid=is_valid,
            validation_errors=errors or [],
            lineage_id=validating.lineage_id,
            metadata={
                'object_class': obj.__class__.__name__
            }
        )
    
    # Use parent-child pattern
    await bus.emit_with_children(validating, [complete_validation])


# Convenience functions for common patterns

async def emit_simple_event(
    event_type: str,
    obj: Optional[BaseModel] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Emit a simple standalone event.
    
    Args:
        event_type: Type identifier for the event
        obj: Subject object (optional)
        metadata: Additional metadata
    """
    bus = get_event_bus()
    
    subject_type = None
    subject_id = None
    
    if obj:
        subject_type = type(obj)
        subject_id = getattr(obj, 'id', None) or getattr(obj, 'ecs_id', None)
    
    event = Event(
        type=event_type,
        phase=EventPhase.COMPLETED,
        subject_type=subject_type,
        subject_id=subject_id,
        metadata=metadata or {}
    )
    
    await bus.emit(event)


async def emit_timed_operation(
    operation_name: str,
    operation_func,
    obj: Optional[BaseModel] = None,
    *args, **kwargs
) -> Any:
    """
    Wrap any operation with timing events.
    
    Args:
        operation_name: Name of the operation
        operation_func: Function to execute
        obj: Subject object (optional)
        *args, **kwargs: Arguments for the operation function
        
    Returns:
        Result of the operation function
    """
    bus = get_event_bus()
    
    subject_type = None
    subject_id = None
    
    if obj:
        subject_type = type(obj)
        subject_id = getattr(obj, 'id', None) or getattr(obj, 'ecs_id', None)
    
    # Create starting event
    start_event = Event(
        type=f"{operation_name}.started",
        phase=EventPhase.STARTED,
        subject_type=subject_type,
        subject_id=subject_id,
        metadata={
            'operation': operation_name,
            'timed': True
        }
    )
    
    start_time = time.time()
    result = None  # Store result to avoid double execution
    
    # Create completion generator
    async def complete_operation():
        nonlocal result
        try:
            # Execute the operation ONCE
            if asyncio.iscoroutinefunction(operation_func):
                result = await operation_func(*args, **kwargs)
            else:
                result = operation_func(*args, **kwargs)
            
            # Create completion event
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            
            return Event(
                type=f"{operation_name}.completed",
                phase=EventPhase.COMPLETED,
                subject_type=subject_type,
                subject_id=subject_id,
                duration_ms=duration_ms,
                lineage_id=start_event.lineage_id,
                metadata={
                    'operation': operation_name,
                    'timed': True,
                    'success': True
                }
            )
            
        except Exception as e:
            # Create failure event
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            
            failure_event = Event(
                type=f"{operation_name}.failed",
                phase=EventPhase.FAILED,
                subject_type=subject_type,
                subject_id=subject_id,
                duration_ms=duration_ms,
                lineage_id=start_event.lineage_id,
                error=str(e),
                metadata={
                    'operation': operation_name,
                    'timed': True,
                    'success': False
                }
            )
            
            # Return the failure event and re-raise the exception
            await bus.emit(failure_event)
            raise
    
    # Use parent-child pattern
    await bus.emit_with_children(start_event, [complete_operation])
    
    # Return the stored result (no double execution!)
    return result


async def emit_state_transition_events(
    obj: BaseModel,
    from_state: str,
    to_state: str,
    transition_reason: Optional[str] = None
) -> None:
    """
    Emit state transition events with parent-child coordination.
    
    Args:
        obj: The object undergoing state transition
        from_state: The previous state
        to_state: The new state
        transition_reason: Reason for the transition (optional)
    """
    bus = get_event_bus()
    
    # Get object ID
    obj_id = getattr(obj, 'id', None) or getattr(obj, 'ecs_id', None) or uuid4()
    
    # Create transitioning event
    transitioning = Event(
        type="state.transitioning",
        phase=EventPhase.STARTED,
        subject_type=type(obj),
        subject_id=obj_id,
        metadata={
            'from_state': from_state,
            'to_state': to_state,
            'transition_reason': transition_reason,
            'object_class': obj.__class__.__name__
        }
    )
    
    # Create completion generator
    async def complete_transition():
        return StateTransitionEvent(
            subject_type=type(obj),
            subject_id=obj_id,
            from_state=from_state,
            to_state=to_state,
            transition_reason=transition_reason,
            lineage_id=transitioning.lineage_id,
            metadata={
                'object_class': obj.__class__.__name__
            }
        )
    
    # Use parent-child pattern
    await bus.emit_with_children(transitioning, [complete_transition])