from typing import List, Optional
from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from abstractions.text import Paragraph

class Chapter(BaseModel):
    """A Pydantic model representing a chapter in the text.

    Attributes:
        id (UUID): A unique identifier for the chapter.
        paragraphs (List[Paragraph]): The list of paragraphs that make up this chapter.
        length (int): The number of characters in the chapter.
    """
    id: UUID = Field(default_factory=uuid4)
    paragraphs: List[Paragraph]
    length: int = sum([paragraph.length for paragraph in paragraphs])

class Book(BaseModel):
    """A Pydantic model representing a book.

    Attributes:
        id (UUID): A unique identifier for the book.
        chapters (List[Chapter]): The list of chapters that make up this book.
        length (int): The number of characters in the entire book.
    """
    id: UUID = Field(default_factory=uuid4)
    chapters: List[Chapter]
    length: int = sum([chapter.length for chapter in chapters])