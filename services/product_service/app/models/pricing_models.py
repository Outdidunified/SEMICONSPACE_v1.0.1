from odmantic import Model, EmbeddedModel, Field
from typing import List, Optional
from datetime import datetime
from uuid import uuid4, UUID

class PricingTier(EmbeddedModel):
    break_quantity: int = Field(key_name="BreakQuantity")
    unit_price: float = Field(key_name="UnitPrice")
    total_price: float = Field(key_name="TotalPrice")

class VendorBulkPricing(Model):
    id: UUID = Field(default_factory=uuid4, primary_field=True)
    vendor_product_id: str 
    pricing_record_id: str = Field(unique=True)

    # ✅ Map to capitalized DB fields
    standard_pricing: List[PricingTier] = Field(default_factory=list, key_name="StandardPricing")
    my_pricing: List[PricingTier] = Field(default_factory=list, key_name="MyPricing")

    status: Optional[bool] = True
    created_by: Optional[str] = None
    created_date: datetime = Field(default_factory=datetime.utcnow)
    modified_by: Optional[str] = None
    modified_date: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "collection": "vendor_bulk_pricing"
    }
