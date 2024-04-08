# error.py

from typing import List, Optional, Dict, Any, Type
from pydantic import BaseModel
from abstractions.goap.nodes import AmbiguousEntityError




class ActionConversionError(BaseModel):
    """
    Represents an error that occurs during the conversion of an action payload.
    Attributes:
        message (str): The error message.
        source_entity_error (Optional[AmbiguousEntityError]): The error related to the source entity, if any.
        target_entity_error (Optional[AmbiguousEntityError]): The error related to the target entity, if any.
    """
    message: str
    source_entity_error: Optional[AmbiguousEntityError] = None
    target_entity_error: Optional[AmbiguousEntityError] = None

    def get_error_message(self) -> str:
        error_message = self.message
        if self.source_entity_error:
            error_message += f"\nSource Entity Error: {self.source_entity_error.get_error_message()}"
        if self.target_entity_error:
            error_message += f"\nTarget Entity Error: {self.target_entity_error.get_error_message()}"
        return error_message