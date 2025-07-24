from abstractions.ecs.registry_agent import registry_agent


import asyncio
from typing import Tuple, List
from pydantic import Field
from abstractions.ecs.entity import Entity
from abstractions.ecs.callable_registry import CallableRegistry
from abstractions.ecs.registry_agent import registry_agent
from abstractions.ecs.functional_api import get

from datetime import datetime, timezone
from typing import Dict, Optional

from abstractions.events.events import (
    Event, CreatedEvent, ProcessingEvent, ProcessedEvent,
    on, emit, get_event_bus
)

from abstractions.events.entity_events import (
    EntityRegistrationEvent, EntityRegisteredEvent,
    EntityVersioningEvent, EntityVersionedEvent,
    EntityPromotionEvent, EntityPromotedEvent,
    EntityDetachmentEvent, EntityDetachedEvent,
    EntityAttachmentEvent, EntityAttachedEvent,
    DataBorrowingEvent, DataBorrowedEvent,
    IDUpdateEvent, IDUpdatedEvent,
    TreeBuildingEvent, TreeBuiltEvent,
    ChangeDetectionEvent, ChangesDetectedEvent
)

# Domain entities for reactive order processing system
class Customer(Entity):
    """Customer entity with profile information."""
    customer_id: str
    name: str
    email: str
    tier: str = "standard"  # standard, premium, vip
    total_spending: float = 0.0
    order_count: int = 0
    last_order_date: Optional[datetime] = None

class Product(Entity):
    """Product entity with inventory and pricing."""
    product_id: str
    name: str
    category: str
    price: float
    stock_quantity: int
    low_stock_threshold: int = 10
    popularity_score: float = 0.0
    total_sold: int = 0

class Order(Entity):
    """Order entity linking customers and products."""
    order_id: str
    customer_id: str
    product_id: str
    quantity: int
    unit_price: float
    total_amount: float
    status: str = "pending"  # pending, confirmed, shipped, delivered, cancelled
    order_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class InventoryAlert(Entity):
    """Alert generated when inventory runs low."""
    product_id: str
    current_stock: int
    threshold: int
    severity: str  # warning, critical
    alert_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = False

class CustomerTierUpdate(Entity):
    """Customer tier change notification."""
    customer_id: str
    old_tier: str
    new_tier: str
    reason: str
    benefits: List[str] = Field(default_factory=list)
    effective_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class RecommendationEngine(Entity):
    """Product recommendation based on customer behavior."""
    customer_id: str
    recommended_products: List[str] = Field(default_factory=list)
    recommendation_scores: Dict[str, float] = Field(default_factory=dict)
    strategy_used: str  # "popularity", "category_affinity", "tier_based"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

@on(EntityRegistrationEvent)
async def handle_entity_registration(event: EntityRegistrationEvent):
    """Handle entity registration events."""
    print(f"Entity registered: {event.subject_id}")
    # Additional logic can be added here if needed

@on(EntityPromotionEvent)
async def handle_entity_promotion(event: EntityPromotionEvent):
    """Handle entity promotion events."""
    print(f"Entity promoted: {event.subject_id} to root")
    # Additional logic can be added here if needed

def create_test_data() -> Tuple[List[Customer], List[Product], List[Order]]:
    """Create test data for reactive cascade testing."""
    
    customers = [
        Customer(customer_id="CUST001", name="Alice Johnson", email="alice@email.com", tier="standard", total_spending=0.0, order_count=0),
        Customer(customer_id="CUST002", name="Bob Smith", email="bob@email.com", tier="standard", total_spending=450.0, order_count=4),
        Customer(customer_id="CUST003", name="Charlie Brown", email="charlie@email.com", tier="premium", total_spending=1200.0, order_count=15)
    ]
    
    products = [
        Product(product_id="PROD001", name="Laptop", category="Electronics", price=800.0, stock_quantity=15, low_stock_threshold=5, popularity_score=25.0, total_sold=100),
        Product(product_id="PROD002", name="Coffee Mug", category="Home", price=15.0, stock_quantity=3, low_stock_threshold=10, popularity_score=10.0, total_sold=50),
        Product(product_id="PROD003", name="Gaming Chair", category="Furniture", price=200.0, stock_quantity=8, low_stock_threshold=3, popularity_score=15.0, total_sold=30),
        Product(product_id="PROD004", name="Smartphone", category="Electronics", price=600.0, stock_quantity=20, low_stock_threshold=5, popularity_score=30.0, total_sold=150),
        Product(product_id="PROD005", name="Desk Lamp", category="Home", price=25.0, stock_quantity=12, low_stock_threshold=5, popularity_score=8.0, total_sold=40)
    ]
    
    orders = [
        Order(order_id="ORD001", customer_id="CUST001", product_id="PROD001", quantity=1, unit_price=800.0, total_amount=800.0),
        Order(order_id="ORD002", customer_id="CUST002", product_id="PROD004", quantity=1, unit_price=600.0, total_amount=600.0),
        Order(order_id="ORD003", customer_id="CUST003", product_id="PROD002", quantity=2, unit_price=15.0, total_amount=30.0)
    ]
    
    return customers, products, orders


if __name__ == "__main__":
    customers, products, orders = create_test_data()
    #record all data to the registry
    for customer in customers:
        customer.promote_to_root()
    for product in products:
        product.promote_to_root()
    for order in orders:
        order.promote_to_root()
