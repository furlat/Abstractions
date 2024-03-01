from typing import List, Optional
from pydantic import BaseModel, Field
from uuid import UUID, uuid4

class Word(BaseModel):
    """A Pydantic model representing a word in the text.

    Attributes:
        id (UUID): A unique identifier for the word.
        content (str): The actual content of the word.
        length (int): The number of characters in the word.
    """
    id: UUID = Field(default_factory=uuid4)
    content: str
    length: int = len(content)

class Sentence(BaseModel):
    """A Pydantic model representing a sentence in the text.

    Attributes:
        id (UUID): A unique identifier for the sentence.
        words (List[Word]): The list of words that make up this sentence.
        length (int): The number of characters in the sentence.
    """
    id: UUID = Field(default_factory=uuid4)
    words: List[Word]
    length: int = sum([word.length for word in words])

class Paragraph(BaseModel):
    """A Pydantic model representing a paragraph in the text.

    Attributes:
        id (UUID): A unique identifier for the paragraph.
        sentences (List[Sentence]): The list of sentences that make up this paragraph.
        length (int): The number of characters in the paragraph.
    """
    id: UUID = Field(default_factory=uuid4)
    sentences: List[Sentence]
    length: int = sum([sentence.length for sentence in sentences])
