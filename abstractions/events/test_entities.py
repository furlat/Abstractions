"""
Fake Entity Classes for Event System Testing

Simple BaseModel classes that simulate different types of entities
for testing the event system in isolation from the real ECS.
"""

from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from enum import Enum


class EntityStatus(str, Enum):
    """Status enum for fake entities"""
    ACTIVE = "active"
    INACTIVE = "inactive" 
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FakeEntity(BaseModel):
    """
    Simple entity for basic event testing.
    
    Simulates a basic entity with ID, name, and status.
    """
    id: UUID = Field(default_factory=uuid4, description="Entity identifier")
    name: str = Field(default="test_entity", description="Entity name")
    status: EntityStatus = Field(default=EntityStatus.ACTIVE, description="Entity status")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    def update_status(self, new_status: EntityStatus, reason: Optional[str] = None):
        """Update entity status (useful for state transition events)"""
        old_status = self.status
        self.status = new_status
        if reason:
            self.metadata['last_status_change_reason'] = reason
        self.metadata['previous_status'] = old_status.value
        return old_status, new_status


class FakeDocument(BaseModel):
    """
    Document entity for testing complex data operations.
    
    Simulates a document with title, content, and metadata.
    """
    id: UUID = Field(default_factory=uuid4, description="Document identifier")
    title: str = Field(default="untitled", description="Document title")
    content: str = Field(default="", description="Document content")
    author: str = Field(default="anonymous", description="Document author")
    tags: List[str] = Field(default_factory=list, description="Document tags")
    word_count: int = Field(default=0, description="Word count")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp"
    )
    modified_at: Optional[datetime] = Field(default=None, description="Last modification")
    
    def update_content(self, new_content: str):
        """Update document content (useful for modification events)"""
        old_content = self.content
        old_word_count = self.word_count
        
        self.content = new_content
        self.word_count = len(new_content.split()) if new_content else 0
        self.modified_at = datetime.now(timezone.utc)
        
        return {
            'content': (old_content, new_content),
            'word_count': (old_word_count, self.word_count)
        }
    
    def add_tag(self, tag: str):
        """Add a tag (useful for relationship events)"""
        if tag not in self.tags:
            self.tags.append(tag)
            return True
        return False


class FakeUser(BaseModel):
    """
    User entity for testing relationship operations.
    
    Simulates a user that can have relationships with documents.
    """
    id: UUID = Field(default_factory=uuid4, description="User identifier")
    username: str = Field(description="Username")
    email: str = Field(description="User email")
    created_documents: List[UUID] = Field(default_factory=list, description="Documents created by user")
    favorite_documents: List[UUID] = Field(default_factory=list, description="User's favorite documents")
    profile: Dict[str, Any] = Field(default_factory=dict, description="User profile data")
    
    def create_document(self, document: FakeDocument):
        """Create a relationship with a document"""
        if document.id not in self.created_documents:
            self.created_documents.append(document.id)
            document.author = self.username
            return True
        return False
    
    def favorite_document(self, document_id: UUID):
        """Add document to favorites"""
        if document_id not in self.favorite_documents:
            self.favorite_documents.append(document_id)
            return True
        return False


class FakeProcessingTask(BaseModel):
    """
    Processing task entity for testing workflow operations.
    
    Simulates a task that processes inputs and produces outputs.
    """
    id: UUID = Field(default_factory=uuid4, description="Task identifier")
    name: str = Field(description="Task name")
    task_type: str = Field(description="Type of processing task")
    input_ids: List[UUID] = Field(default_factory=list, description="Input entity IDs")
    output_ids: List[UUID] = Field(default_factory=list, description="Output entity IDs")
    status: EntityStatus = Field(default=EntityStatus.ACTIVE, description="Task status")
    started_at: Optional[datetime] = Field(default=None, description="Task start time")
    completed_at: Optional[datetime] = Field(default=None, description="Task completion time")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    progress: float = Field(default=0.0, description="Task progress (0.0 to 1.0)")
    
    def start_processing(self):
        """Start the processing task"""
        self.status = EntityStatus.PROCESSING
        self.started_at = datetime.now(timezone.utc)
        self.progress = 0.0
    
    def update_progress(self, progress: float):
        """Update task progress"""
        self.progress = max(0.0, min(1.0, progress))
        if self.progress >= 1.0:
            self.complete_processing()
    
    def complete_processing(self, output_ids: Optional[List[UUID]] = None):
        """Complete the processing task"""
        self.status = EntityStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        self.progress = 1.0
        if output_ids:
            self.output_ids.extend(output_ids)
    
    def fail_processing(self, error: str):
        """Mark task as failed"""
        self.status = EntityStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)
        self.error_message = error


class FakeConfiguration(BaseModel):
    """
    Configuration entity for testing system events.
    
    Simulates system configuration that can trigger system-wide events.
    """
    id: UUID = Field(default_factory=uuid4, description="Configuration identifier")
    name: str = Field(description="Configuration name")
    settings: Dict[str, Any] = Field(default_factory=dict, description="Configuration settings")
    version: str = Field(default="1.0.0", description="Configuration version")
    active: bool = Field(default=True, description="Whether configuration is active")
    applied_at: Optional[datetime] = Field(default=None, description="When configuration was applied")
    
    def apply_configuration(self):
        """Apply the configuration"""
        self.active = True
        self.applied_at = datetime.now(timezone.utc)
    
    def update_setting(self, key: str, value: Any):
        """Update a configuration setting"""
        old_value = self.settings.get(key)
        self.settings[key] = value
        return old_value, value


# Complex nested entity for testing hierarchical operations
class FakeProject(BaseModel):
    """
    Project entity containing multiple related entities.
    
    Simulates a complex entity with nested relationships.
    """
    id: UUID = Field(default_factory=uuid4, description="Project identifier")
    name: str = Field(description="Project name")
    description: str = Field(default="", description="Project description")
    owner: FakeUser = Field(description="Project owner")
    documents: List[FakeDocument] = Field(default_factory=list, description="Project documents")
    tasks: List[FakeProcessingTask] = Field(default_factory=list, description="Project tasks")
    settings: FakeConfiguration = Field(default_factory=lambda: FakeConfiguration(name="default_settings"), description="Project settings")
    collaborators: List[UUID] = Field(default_factory=list, description="Collaborator user IDs")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp"
    )
    
    def add_document(self, document: FakeDocument):
        """Add a document to the project"""
        if document not in self.documents:
            self.documents.append(document)
            # Create relationship
            self.owner.create_document(document)
            return True
        return False
    
    def add_task(self, task: FakeProcessingTask):
        """Add a task to the project"""
        if task not in self.tasks:
            self.tasks.append(task)
            return True
        return False
    
    def add_collaborator(self, user_id: UUID):
        """Add a collaborator to the project"""
        if user_id not in self.collaborators:
            self.collaborators.append(user_id)
            return True
        return False


# Factory functions for creating test entities
def create_test_entity(name: Optional[str] = None, status: EntityStatus = EntityStatus.ACTIVE) -> FakeEntity:
    """Create a test entity with optional parameters"""
    return FakeEntity(
        name=name or f"test_entity_{uuid4().hex[:8]}",
        status=status
    )


def create_test_document(title: Optional[str] = None, content: Optional[str] = None) -> FakeDocument:
    """Create a test document with optional parameters"""
    return FakeDocument(
        title=title or f"Test Document {uuid4().hex[:8]}",
        content=content or "This is test content for the document."
    )


def create_test_user(username: Optional[str] = None, email: Optional[str] = None) -> FakeUser:
    """Create a test user with optional parameters"""
    base_name = username or f"testuser_{uuid4().hex[:8]}"
    return FakeUser(
        username=base_name,
        email=email or f"{base_name}@example.com"
    )


def create_test_task(name: Optional[str] = None, task_type: str = "processing") -> FakeProcessingTask:
    """Create a test processing task"""
    return FakeProcessingTask(
        name=name or f"Test Task {uuid4().hex[:8]}",
        task_type=task_type
    )


def create_test_project(name: Optional[str] = None, owner: Optional[FakeUser] = None) -> FakeProject:
    """Create a test project with optional parameters"""
    if owner is None:
        owner = create_test_user()
    
    return FakeProject(
        name=name or f"Test Project {uuid4().hex[:8]}",
        description="A test project for event system validation",
        owner=owner
    )


# Scenario builders for complex testing
def create_document_workflow_scenario():
    """
    Create a complete document workflow scenario for testing.
    
    Returns:
        Tuple of (user, document, task, project) representing a complete workflow
    """
    # Create entities
    user = create_test_user("workflow_user", "workflow@test.com")
    document = create_test_document("Workflow Document", "Initial content")
    task = create_test_task("Process Document", "document_processing")
    project = create_test_project("Workflow Project", user)
    
    # Set up relationships
    user.create_document(document)
    task.input_ids.append(document.id)
    project.add_document(document)
    project.add_task(task)
    
    return user, document, task, project


def create_collaboration_scenario():
    """
    Create a collaboration scenario with multiple users and shared documents.
    
    Returns:
        Tuple of (owner, collaborator, shared_document, project)
    """
    # Create entities
    owner = create_test_user("project_owner", "owner@test.com")
    collaborator = create_test_user("collaborator", "collab@test.com")
    shared_document = create_test_document("Shared Document", "Collaborative content")
    project = create_test_project("Collaboration Project", owner)
    
    # Set up relationships
    owner.create_document(shared_document)
    collaborator.favorite_document(shared_document.id)
    project.add_document(shared_document)
    project.add_collaborator(collaborator.id)
    
    return owner, collaborator, shared_document, project