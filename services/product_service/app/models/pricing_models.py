from odmantic import Model, Field
from datetime import datetime, timezone
from uuid import UUID, uuid4


class ProductPricing(Model):
    id: UUID = Field(primary_field=True, default_factory=uuid4)
    product_pricing_id: int  # Auto-increment field
    product_id: int
    currency: str
    price: float
    min_quantity: int
    available_quantity: int
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str
    created_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    modified_by: str
    modified_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: bool

    # ✅ ODMantic way to define collection name
    model_config = {"collection": "product_pricings"}
