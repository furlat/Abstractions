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


@CallableRegistry.register("process_order_placement")
async def process_order_placement(order: Order, customer: Customer, product: Product) -> Tuple[Order, Customer, Product]:
    """Process new order """
    # Simulate async order processing
    
    # Update order status
    updated_order = Order(
        order_id=order.order_id,
        customer_id=order.customer_id,
        product_id=order.product_id,
        quantity=order.quantity,
        unit_price=order.unit_price,
        total_amount=order.total_amount,
        status="confirmed",
        order_date=order.order_date
    )
    
    # Update customer statistics
    updated_customer = Customer(
        customer_id=customer.customer_id,
        name=customer.name,
        email=customer.email,
        tier=customer.tier,
        total_spending=customer.total_spending + order.total_amount,
        order_count=customer.order_count + 1,
        last_order_date=datetime.now(timezone.utc)
    )
    
    # Update product inventory and statistics
    updated_product = Product(
        product_id=product.product_id,
        name=product.name,
        category=product.category,
        price=product.price,
        stock_quantity=product.stock_quantity - order.quantity,
        low_stock_threshold=product.low_stock_threshold,
        popularity_score=product.popularity_score + 1.0,
        total_sold=product.total_sold + order.quantity
    )
    
    return updated_order, updated_customer, updated_product

@CallableRegistry.register("check_inventory_levels")
async def check_inventory_levels(product: Product) -> Optional[InventoryAlert]:
    """Check if product inventory requires attention."""
    
    if product.stock_quantity <= 0:
        return InventoryAlert(
            product_id=product.product_id,
            current_stock=product.stock_quantity,
            threshold=product.low_stock_threshold,
            severity="critical"
        )
    elif product.stock_quantity <= product.low_stock_threshold:
        return InventoryAlert(
            product_id=product.product_id,
            current_stock=product.stock_quantity,
            threshold=product.low_stock_threshold,
            severity="warning"
        )
    
    return None

@CallableRegistry.register("evaluate_customer_tier")
async def evaluate_customer_tier(customer: Customer) -> Optional[CustomerTierUpdate]:
    """Evaluate if customer tier should be updated."""
    
    current_tier = customer.tier
    new_tier = current_tier
    
    # Tier upgrade logic
    if customer.total_spending >= 1000 and customer.order_count >= 10:
        new_tier = "vip"
    elif customer.total_spending >= 500 and customer.order_count >= 5:
        new_tier = "premium"
    else:
        new_tier = "standard"
    
    if new_tier != current_tier:
        benefits = []
        if new_tier == "premium":
            benefits = ["5% discount on all orders", "Priority customer support"]
        elif new_tier == "vip":
            benefits = ["10% discount on all orders", "Free shipping", "Exclusive products access"]
        
        return CustomerTierUpdate(
            customer_id=customer.customer_id,
            old_tier=current_tier,
            new_tier=new_tier,
            reason=f"Spending: ${customer.total_spending:.2f}, Orders: {customer.order_count}",
            benefits=benefits
        )
    
    return None

@CallableRegistry.register("generate_recommendations")
async def generate_recommendations(customer: Customer, products: List[Product]) -> RecommendationEngine:
    """Generate product recommendations based on customer profile."""
    
    strategy = "popularity"
    if customer.tier == "premium":
        strategy = "category_affinity"
    elif customer.tier == "vip":
        strategy = "tier_based"
    
    # Simple recommendation logic
    recommended_products = []
    recommendation_scores = {}
    
    if strategy == "popularity":
        # Recommend most popular products
        sorted_products = sorted(products, key=lambda p: p.popularity_score, reverse=True)
        recommended_products = [p.product_id for p in sorted_products[:3]]
        recommendation_scores = {p.product_id: p.popularity_score for p in sorted_products[:3]}
    
    elif strategy == "category_affinity":
        # Recommend based on category diversity
        categories = set(p.category for p in products)
        for category in list(categories)[:3]:
            category_products = [p for p in products if p.category == category]
            if category_products:
                best_in_category = max(category_products, key=lambda p: p.popularity_score)
                recommended_products.append(best_in_category.product_id)
                recommendation_scores[best_in_category.product_id] = best_in_category.popularity_score
    
    elif strategy == "tier_based":
        # Recommend premium products for VIP customers
        premium_products = [p for p in products if p.price >= 50.0]
        if premium_products:
            sorted_premium = sorted(premium_products, key=lambda p: p.popularity_score, reverse=True)
            recommended_products = [p.product_id for p in sorted_premium[:3]]
            recommendation_scores = {p.product_id: p.popularity_score for p in sorted_premium[:3]}
    
    return RecommendationEngine(
        customer_id=customer.customer_id,
        recommended_products=recommended_products,
        recommendation_scores=recommendation_scores,
        strategy_used=strategy
    )

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


@on(EntityPromotionEvent)
async def handle_entity_promotion(event: EntityPromotionEvent):
    """Handle entity promotion events."""
    print(f"Entity promoted: {event.subject_id} to root")
    # Additional logic can be added here if needed

if __name__ == "__main__":
    customers, products, orders = create_test_data()
    #record all data to the registry
    for customer in customers:
        customer.promote_to_root()
    for product in products:
        product.promote_to_root()
    for order in orders:
        order.promote_to_root()

    first_customer_order = orders[0].ecs_id
    first_product = products[0].ecs_id 
    first_customer = customers[0].ecs_id

    # processed_entities = CallableRegistry.execute(
    #     "process_order_placement",
    #     order=f"@{str(first_customer_order)}",
    #     customer=f"@{str(first_customer)}",
    #     product=f"@{str(first_product)}"
    # )    
    # print(f"proessed_entities: {processed_entities}")
    # print(f"Processed Entities: {get(f"@{str(first_customer)}")}")

    # print(f"Processed Entities: {get(f"@{str(first_customer)}.name")}")
    # # results = registry_agent.run_sync("What functions are available?")
    # print(f"Available functions: {results.output}")

    # results = registry_agent.run_sync("What entities are in thesystem?")
    # print(f"Available entities: {results.output}")

    results = registry_agent.run_sync(f"can you process an orders  placement with the available entities you cna choose which entities to use by yourself? First request from teh registry the available entities then choose any valid combination and process the order placement")
    print(f"processed order: {results.output}")

    print(f"all messages: {results.all_messages()}")