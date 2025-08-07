from odmantic import Model, Field
from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4


class VendorProduct(Model):
    id: UUID = Field(default_factory=uuid4, primary_field=True) 
    product_id: str  # semiconproduvy id
    vendor_product_id: str = Field(unique=True)  # e.g., "Digikey-P5555-ND"

    manufacturer_part_number: Optional[str] = None
    unitprice: Optional[float] = None
    product_url: Optional[str] = None

    vendor: Optional[str] = None
    pricing: Optional[str] = None  # prcing record id

    created_by: Optional[str] = None
    created_date: datetime = Field(default_factory=datetime.utcnow)
    modified_by: Optional[str] = None
    modified_date: datetime = Field(default_factory=datetime.utcnow)

    status: bool = True

    model_config = {
        "collection": "vendor_products"
    }
