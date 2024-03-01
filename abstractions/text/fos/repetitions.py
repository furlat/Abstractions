"""
Abstractions created following
https://www.masterclass.com/articles/writing-101-what-is-repetition-7-types-of-repetition-in-writing-with-examples#
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict


class Repetition(BaseModel):
    """
    Figure of speech where the same word or group of words are repeated in successive clauses or sentences. There are different types of repetitions: Anaphoras, Epistrophes, ...
    repeated_string: the group of words being repeated, if any
    repetition_sentences: all sentences containing the repeated_string, if a repeated string exists
    If repeated_string is an empty string, repetition_sentences must be an empty list
    """
    repetition_dict: Optional[Dict[str, List[str]]] = Field(
        default=None,
        description="A dictionary with repeated strings as keys and lists of sentences containing these strings as values."
    )

    @validator('repetition_dict')
    def check_repetition_dict(cls, v):
        """
        Validate that each repeated_str in the dictionary occurs more than once across its repetition_sentences.
        """
        for repeated_str, sentences in v.items():
            if not sentences:
                raise ValueError(f"The list of sentences for '{repeated_str}' is empty. Each key must have at least one sentence.")
            
            concatenated_sentences = ' '.join(sentences)
            pattern = re.escape(repeated_str)
            matches = re.findall(pattern, concatenated_sentences)
            
            if len(matches) < 2:
                raise ValueError(f"The string '{repeated_str}' does not occur more than once in its corresponding sentences.")

        return v
    
class AnaphoricExpression(Repetition):
    """
    A type of repetition. Occurs when the same word or group of words 
    is repeated at the beginning of successive clauses or sentences 
    that might have different endings.
    Example text containing this type of repetition.: 'This is what I think. I have a dream that my four little children will not be judged by the color of their skin. I have a dream today.'
    """
    __doc__ = Repetition.__doc__+"\n"+__doc__

class EpistrophicExpression(Repetition):
    """
    A type of repetition. Occurs the last word or phrase across successive phrases, clauses or sentences.
    repeated_string: the group of words being repeated
    container: all sentences containing repeated_string
    Example: "When I was a child, I spoke as a child, I understood as a child, I thought as a child."
    """
    __doc__ = Repetition.__doc__+"\n"+__doc__