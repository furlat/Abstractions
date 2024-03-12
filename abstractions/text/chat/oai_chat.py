from typing import Any, Dict, List, Optional, get_args, get_origin, get_type_hints, Union, Annotated
from pydantic import BaseModel, ValidationError, validator , model_validator, field_validator
from pydantic.fields import Field
from pydantic.functional_validators import AfterValidator



class Author(BaseModel):
    role: str
    name: Optional[str] = None
    metadata: Dict[str, Any] = {}

class Content(BaseModel):
    content_type: str
    parts: Optional[Union[List[Union[str, Dict[str, Any]]], Dict[str, Any]]] = None
    language: Optional[str] = None
    text: Optional[str] = None

    @field_validator('parts', mode= 'before')
    def validate_parts(cls, v):
        if isinstance(v, dict):
            return [v]  # Wrap in a list if it's a dict
        return v
    def get_message_content(self):
    # Check if text is provided
        content = self
        if content.text:
            return content.text
        # If text is None, try to get content from parts
        elif content.parts:
            # If parts is a list, we concatenate items or get the text from dict
            if isinstance(content.parts, list):
                # Concatenate list items if they are strings, or stringify them if they are dicts
                return ' '.join(str(part) if isinstance(part, dict) else part for part in content.parts)
            # If parts is a dict, we convert it to string
            elif isinstance(content.parts, dict):
                return str(content.parts)
        return 'No message'

class Message(BaseModel):
    id: str
    author: Optional[Author] = None
    create_time: Optional[float] = None
    update_time: Optional[float] = None
    content: Optional[Content] = None
    status: str
    end_turn: Optional[bool] = None
    weight: float
    metadata: Dict[str, Any] = {}
    recipient: str


from typing import List, Optional
from pydantic import BaseModel



class Node(BaseModel):
    id: str
    message: Optional[Message] = None
    parent: Optional[str] = None
    children: List[str] = []

    def is_leaf(self) -> bool:
        return len(self.children) == 0

    def is_root(self) -> bool:
        return self.parent is None

    def is_linear(self) -> bool:
        return len(self.children) <= 1 and (self.parent is None or self.parent.children == 1)

class Conversation(BaseModel):
    title: str
    create_time: float
    update_time: float
    mapping: Dict[str, Node]
    moderation_results: List[Any] = []
    current_node: str
    plugin_ids: Optional[Any] = None
    conversation_id: str
    conversation_template_id: Optional[Any] = None
    gizmo_id: Optional[Any] = None
    is_archived: bool
    safe_urls: List[Any] = []
    id: str

    def extract_all_linearized_conversations(self) -> List['LinearConversation']:
        def build_linear_conversations(node_id: str, current_path: Dict[str, Node], depth=0):
            node = self.mapping[node_id]
            new_node = node.model_copy(deep=True)
            new_node.children = new_node.children[:1]  # Keep only the first child to ensure linearity

            # Update the current path with the new linear node
            new_path = {**current_path, new_node.id: new_node}

            if not new_node.children:
                # Leaf node, store the current path as a linear conversation
                linear_conversations.append(LinearConversation(**{**self.model_dump(), "mapping": new_path}))
            else:
                # Recursively build the conversation for the next node in the path
                build_linear_conversations(new_node.children[0], new_path, depth + 1)

            # If the original node had multiple children, start new paths for each
            if len(node.children) > 1:
                for child_id in node.children[1:]:
                    build_linear_conversations(child_id, current_path, depth + 1)

        linear_conversations = []
        for node_id, node in self.mapping.items():
            if not node.parent:
                build_linear_conversations(node_id, {})

        return linear_conversations
    
    def visualize_conversation(self, filename: str = 'conversation_graph'):
        try:
            from graphviz import Digraph

            graph = Digraph(comment=self.title)
        except ImportError:
            raise ImportError("Could not import the graphviz library. Please install it using `pip install graphviz` after having installed graphviz")

        def add_nodes_and_edges(node_id: str):
            node = self.mapping[node_id]
            if node.message and node.message.author:
                author_role = node.message.author.role  # User or Assistant
                # Use the get_message_content method to retrieve the message content
                message_content = node.message.content.get_message_content() if node.message.content else "No content"
                label = f"{author_role}: {message_content}"
            else:
                label = "No message"

            graph.node(node_id, label=label)

            for child_id in node.children:
                graph.edge(node_id, child_id)
                add_nodes_and_edges(child_id)

        for node_id, node in self.mapping.items():
            if node.is_root():
                add_nodes_and_edges(node_id)

        graph.render(filename, view=True, format='png')

    
def validate_single_child_node(node: Node) -> Node:
    if len(node.children) > 1:
        raise ValueError("Node has multiple children, not suitable for LinearConversation.")
    return node

NodeWithSingleChild = Annotated[Node, AfterValidator(validate_single_child_node)]

class LinearConversation(Conversation):
    mapping: Dict[str, NodeWithSingleChild]

    def __init__(self, **data: Any):
        super().__init__(**data)