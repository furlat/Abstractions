import asyncio
from typing import Tuple, List
from pydantic import Field
from abstractions.ecs.entity import Entity
from abstractions.ecs.callable_registry import CallableRegistry
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
    print(f"🎯 ASYNC EVENT HANDLER: Entity registered: {event.subject_id}")
    print(f"   Entity type: {event.entity_type}")
    print(f"   Is root: {event.is_root_entity}")

@on(EntityPromotionEvent)
async def handle_entity_promotion(event: EntityPromotionEvent):
    """Handle entity promotion events."""
    print(f"🎯 ASYNC EVENT HANDLER: Entity promoted: {event.subject_id} to root")
    print(f"   Was orphan: {event.was_orphan}")
    print(f"   Promotion reason: {event.promotion_reason}")

@on(EntityRegisteredEvent)
async def handle_entity_registered(event: EntityRegisteredEvent):
    """Handle entity registered completion events."""
    print(f"🎯 ASYNC EVENT HANDLER: Entity registration completed: {event.subject_id}")
    print(f"   Registration successful: {event.registration_successful}")

@on(EntityPromotedEvent)
async def handle_entity_promoted(event: EntityPromotedEvent):
    """Handle entity promoted completion events."""
    print(f"🎯 ASYNC EVENT HANDLER: Entity promotion completed: {event.subject_id}")
    print(f"   New root ID: {event.new_root_id}")
    print(f"   Promotion successful: {event.promotion_successful}")

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


async def main():
    """Main async function to test event handling."""
    print("🚀 Starting ASYNC Event Bus Test")
    print("=" * 50)
    
    # Get and start the event bus
    bus = get_event_bus()
    await bus.start()
    
    print("✅ Event bus started")
    print("🎪 Event handlers registered:")
    print("   - handle_entity_registration")
    print("   - handle_entity_promotion") 
    print("   - handle_entity_registered")
    print("   - handle_entity_promoted")
    print()
    
    # Create test data
    customers, products, orders = create_test_data()
    
    print("📦 Created test entities, now promoting to root...")
    print()
    
    # Promote entities to root (this should trigger events)
    for i, customer in enumerate(customers):
        print(f"🔄 Promoting customer {i+1}: {customer.name}")
        customer.promote_to_root()
        # Give time for async event processing
        await asyncio.sleep(0.1)
    
    print()
    for i, product in enumerate(products):
        print(f"🔄 Promoting product {i+1}: {product.name}")
        product.promote_to_root()
        # Give time for async event processing
        await asyncio.sleep(0.1)
    
    print()
    for i, order in enumerate(orders):
        print(f"🔄 Promoting order {i+1}: {order.order_id}")
        order.promote_to_root()
        # Give time for async event processing
        await asyncio.sleep(0.1)
    
    # Give final time for all events to process
    print()
    print("⏳ Waiting for all events to complete...")
    await asyncio.sleep(1.0)
    
    # Check bus statistics
    stats = bus.get_statistics()
    print()
    print("📊 Event Bus Statistics:")
    print(f"   Total events: {stats['total_events']}")
    print(f"   Event counts: {stats['event_counts']}")
    print(f"   Queue size: {stats['queue_size']}")
    print(f"   Subscriptions: {stats['subscriptions']}")
    
    print()
    print("🎉 ASYNC Event Bus Test Complete!")
    
    # Stop the bus
    await bus.stop()


if __name__ == "__main__":
    asyncio.run(main())