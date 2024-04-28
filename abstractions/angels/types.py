from typing import List, Optional
from pydantic import BaseModel, Field


class Language(BaseModel):
    name: str = Field(..., description="The name of the language.")
    family: Optional[str] = Field(None, description="The language family.")
    origin: Optional[str] = Field(None, description="The origin of the language.")



class HistoricalEvent(BaseModel):
    name: str = Field(..., description="The name of the historical event.")
    year: int = Field(..., description="The year the event occurred.")
    description: Optional[str] = Field(None, description="A brief description of the event.")


class PoliticalSystem(BaseModel):
    name: str = Field(..., description="The name of the political system.")
    description: Optional[str] = Field(None, description="A brief description of the political system.")


class EconomicSystem(BaseModel):
    name: str = Field(..., description="The name of the economic system.")
    description: Optional[str] = Field(None, description="A brief description of the economic system.")


class SocialStructure(BaseModel):
    name: str = Field(..., description="The name of the social structure.")
    description: Optional[str] = Field(None, description="A brief description of the social structure.")


class CulturalMovement(BaseModel):
    name: str = Field(..., description="The name of the cultural movement.")
    description: Optional[str] = Field(None, description="A brief description of the cultural movement.")


class HistoricalContext(BaseModel):
    period: str = Field(..., description="The historical period.")
    start_year: Optional[int] = Field(None, description="The start year of the historical period.")
    end_year: Optional[int] = Field(None, description="The end year of the historical period.")
    key_events: List[HistoricalEvent] = Field([], description="The key events during the historical period.")
    political_systems: List[PoliticalSystem] = Field([], description="The political systems during the historical period.")
    economic_systems: List[EconomicSystem] = Field([], description="The economic systems during the historical period.")
    social_structures: List[SocialStructure] = Field([], description="The social structures during the historical period.")
    cultural_movements: List[CulturalMovement] = Field([], description="The cultural movements during the historical period.")
    intellectual_trends: List[str] = Field([], description="The intellectual trends during the historical period.")
    technological_advancements: List[str] = Field([], description="The technological advancements during the historical period.")
    artistic_styles: List[str] = Field([], description="The artistic styles prevalent during the historical period.")
    religious_beliefs: List[str] = Field([], description="The religious beliefs and practices during the historical period.")
    
class Author(BaseModel):
    name: str = Field(..., description="The name of the author.")
    birth_year: Optional[int] = Field(None, description="The birth year of the author.")
    death_year: Optional[int] = Field(None, description="The death year of the author.")
    nationality: Optional[str] = Field(None, description="The nationality of the author.")
    literary_period: Optional[str] = Field(None, description="The literary period the author belongs to.")
    philosophical_views: List[str] = Field([], description="The philosophical views held by the author.")
    political_affiliations: List[str] = Field([], description="The political affiliations of the author.")
    historical_context: HistoricalContext = Field(..., description="The historical context in which the author lived.")
    influences: List[str] = Field([], description="The influences on the author's work.")
    influenced: List[str] = Field([], description="The authors or works influenced by this author.")
    themes: List[str] = Field([], description="The common themes in the author's works.")
    style: Optional[str] = Field(None, description="The distinctive style of the author.")
    works: List['LiteraryProduction'] = Field([], description="The literary works produced by the author.")

class LiteraryProduction(BaseModel):
    title: str = Field(..., description="The title of the literary work.")
    publication_year: Optional[int] = Field(None, description="The year the literary work was published.")
    genre: Optional[str] = Field(None, description="The genre of the literary work.")
    original_language: Language = Field(..., description="The original language of the literary work.")
    chapters: List['Chapter'] = Field([], description="The chapters of the literary work.")


class Chapter(BaseModel):
    number: int = Field(..., description="The chapter number.")
    title: Optional[str] = Field(None, description="The title of the chapter.")
    paragraphs: List['Paragraph'] = Field([], description="The paragraphs in the chapter.")


class Paragraph(BaseModel):
    number: int = Field(..., description="The paragraph number.")
    sentences: List['Sentence'] = Field([], description="The sentences in the paragraph.")


class Sentence(BaseModel):
    text: str = Field(..., description="The text of the sentence.")
    lines: List['Line'] = Field([], description="The lines in the sentence.")
    clauses: List['Clause'] = Field([], description="The clauses in the sentence.")


class Line(BaseModel):
    number: int = Field(..., description="The line number.")
    text: str = Field(..., description="The text of the line.")


class Clause(BaseModel):
    text: str = Field(..., description="The text of the clause.")
    type: Optional[str] = Field(None, description="The type of the clause.")