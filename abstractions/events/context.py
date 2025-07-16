"""
Event Context Management for Automatic Nesting

This module provides thread-safe and async-safe context management for automatic
event parent-child relationship tracking. Uses contextvars for proper isolation
across async tasks and threads.

Key Features:
- Automatic parent-child event linking
- Thread-safe and async-safe context isolation
- Minimal performance overhead
- Proper cleanup and memory management
- Debug and monitoring capabilities
"""

import contextvars
from typing import List, Optional, Callable
from uuid import UUID
import logging
from pydantic import BaseModel

# Configure logging
logger = logging.getLogger(__name__)

# Context variable for event nesting stack
# Each async task/thread gets its own isolated stack
_event_context_stack: contextvars.ContextVar[List[BaseModel]] = contextvars.ContextVar(
    'event_context_stack',
    default=[]
)

# Context variable for performance monitoring
_context_stats: contextvars.ContextVar[dict] = contextvars.ContextVar(
    'context_stats',
    default={'push_count': 0, 'pop_count': 0, 'max_depth': 0}
)

def get_current_parent_event() -> Optional[BaseModel]:
    """
    Get the current parent event from the context stack.
    
    Returns the most recently pushed event that should be the parent
    of any new events created in the current context.
    
    Returns:
        Optional[BaseModel]: The current parent event, or None if no parent exists
    """
    stack = _event_context_stack.get()
    return stack[-1] if stack else None

def push_event_context(event: BaseModel) -> None:
    """
    Push an event onto the context stack, making it the current parent.
    
    This should be called when a decorated method starts executing
    and creates its starting event. The event becomes the parent
    for any events created by nested method calls.
    
    Args:
        event: The event to push as the new parent context
    """
    current_stack = _event_context_stack.get()
    new_stack = current_stack + [event]
    _event_context_stack.set(new_stack)
    
    # Update statistics
    stats = _context_stats.get()
    stats['push_count'] += 1
    stats['max_depth'] = max(stats['max_depth'], len(new_stack))
    _context_stats.set(stats)
    
    logger.debug(f"Pushed event {getattr(event, 'id', 'unknown')} to context stack (depth: {len(new_stack)})")

def pop_event_context() -> Optional[BaseModel]:
    """
    Pop the current event from the context stack.
    
    This should be called when a decorated method completes execution,
    restoring the previous parent context.
    
    Returns:
        Optional[BaseModel]: The popped event, or None if stack was empty
    """
    current_stack = _event_context_stack.get()
    if not current_stack:
        logger.warning("Attempted to pop from empty context stack")
        return None
    
    popped_event = current_stack[-1]
    new_stack = current_stack[:-1]
    _event_context_stack.set(new_stack)
    
    # Update statistics
    stats = _context_stats.get()
    stats['pop_count'] += 1
    _context_stats.set(stats)
    
    logger.debug(f"Popped event {getattr(popped_event, 'id', 'unknown')} from context stack (depth: {len(new_stack)})")
    return popped_event

def get_context_depth() -> int:
    """
    Get the current nesting depth of the context stack.
    
    Returns:
        int: Number of events currently in the context stack
    """
    return len(_event_context_stack.get())

def get_context_stack() -> List[BaseModel]:
    """
    Get a copy of the current context stack.
    
    Useful for debugging and monitoring. Returns a copy to prevent
    external modification of the context.
    
    Returns:
        List[BaseModel]: Copy of the current context stack
    """
    return _event_context_stack.get().copy()

def get_root_event() -> Optional[BaseModel]:
    """
    Get the root event from the context stack.
    
    The root event is the first event in the stack, representing
    the top-level operation that started the current execution chain.
    
    Returns:
        Optional[BaseModel]: The root event, or None if stack is empty
    """
    stack = _event_context_stack.get()
    return stack[0] if stack else None

def clear_context() -> None:
    """
    Clear the current context stack.
    
    This is primarily used for testing and debugging. In normal
    operation, context should be managed through push/pop operations.
    """
    _event_context_stack.set([])
    _context_stats.set({'push_count': 0, 'pop_count': 0, 'max_depth': 0})
    logger.debug("Context stack cleared")

def get_context_statistics() -> dict:
    """
    Get statistics about context usage.
    
    Returns performance and usage statistics for monitoring
    and debugging purposes.
    
    Returns:
        dict: Statistics including push/pop counts and max depth
    """
    stats = _context_stats.get()
    current_depth = get_context_depth()
    
    return {
        'current_depth': current_depth,
        'push_count': stats['push_count'],
        'pop_count': stats['pop_count'],
        'max_depth_reached': stats['max_depth'],
        'balance_check': stats['push_count'] - stats['pop_count'] == current_depth
    }

def validate_context_balance() -> bool:
    """
    Validate that push/pop operations are balanced.
    
    In a healthy system, the number of push operations minus
    the number of pop operations should equal the current depth.
    
    Returns:
        bool: True if context operations are balanced, False otherwise
    """
    stats = get_context_statistics()
    is_balanced = stats['balance_check']
    
    if not is_balanced:
        logger.warning(
            f"Context stack imbalance detected: "
            f"push_count={stats['push_count']}, "
            f"pop_count={stats['pop_count']}, "
            f"current_depth={stats['current_depth']}"
        )
    
    return is_balanced

class EventContextManager:
    """
    Context manager for explicit event context management.
    
    This provides a more explicit way to manage event contexts,
    particularly useful for testing and special cases where
    automatic management isn't sufficient.
    
    Example:
        with EventContextManager(parent_event):
            # Code executed here will see parent_event as the current parent
            child_event = create_child_event()
    """
    
    def __init__(self, event: BaseModel):
        """
        Initialize context manager with an event.
        
        Args:
            event: The event to use as parent context
        """
        self.event = event
        self.was_pushed = False
    
    def __enter__(self) -> BaseModel:
        """Enter the context, pushing the event onto the stack."""
        push_event_context(self.event)
        self.was_pushed = True
        return self.event
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context, popping the event from the stack."""
        if self.was_pushed:
            popped = pop_event_context()
            if popped and getattr(popped, 'id', None) != getattr(self.event, 'id', None):
                logger.warning(
                    f"Context manager popped unexpected event: "
                    f"expected {getattr(self.event, 'id', 'unknown')}, got {getattr(popped, 'id', 'unknown')}"
                )

# Utility functions for integration with existing event system

def create_child_event_with_context(event_factory: Callable, *args, **kwargs) -> BaseModel:
    """
    Create an event using a factory function with automatic parent linking.
    
    This is a helper function that creates an event and automatically
    links it to the current parent context if one exists.
    
    Args:
        event_factory: Function that creates the event
        *args: Arguments to pass to the factory
        **kwargs: Keyword arguments to pass to the factory
        
    Returns:
        BaseModel: The created event with parent linkage applied
    """
    # Create the event
    event = event_factory(*args, **kwargs)
    
    # Get current parent and apply linkage
    parent = get_current_parent_event()
    if parent:
        if hasattr(event, 'parent_id') and hasattr(parent, 'id'):
            event.parent_id = getattr(parent, 'id', None)
        if hasattr(event, 'root_id'):
            event.root_id = getattr(parent, 'root_id', None) or getattr(parent, 'id', None)
        if hasattr(event, 'lineage_id') and hasattr(parent, 'lineage_id'):
            event.lineage_id = getattr(parent, 'lineage_id', None)
    else:
        if hasattr(event, 'root_id') and hasattr(event, 'id'):
            event.root_id = event.id
    
    return event

def with_auto_parent_linking(event_factory: Callable) -> Callable:
    """
    Decorator that adds automatic parent linking to event factory functions.
    
    This can be used to wrap existing event factory functions to make
    them automatically respect the current parent context.
    
    Args:
        event_factory: The event factory function to wrap
        
    Returns:
        callable: Wrapped factory function with automatic parent linking
    """
    def wrapped_factory(*args, **kwargs):
        return create_child_event_with_context(event_factory, *args, **kwargs)
    
    return wrapped_factory

# Export the main interface
__all__ = [
    'get_current_parent_event',
    'push_event_context', 
    'pop_event_context',
    'get_context_depth',
    'get_context_stack',
    'get_root_event',
    'clear_context',
    'get_context_statistics',
    'validate_context_balance',
    'EventContextManager',
    'create_child_event_with_context',
    'with_auto_parent_linking'
]