import uuid
from typing import List, Optional
from odmantic import Model, Field
from datetime import datetime


class SupplierInfo(Model):
    id: int
    name: str

    class Config:
        collection = None  # Embedded document, no separate collection


class ProductVariant(Model):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_field=True)
    vendor_part_number: str
    digikey_product_number: str
    marketplace: bool = False
    tariff_active: bool = False

    supplier: SupplierInfo

    quantity_available_for_package_type: int
    max_quantity_for_distribution: int
    standard_package: int
    digireel_fee: int

    created_by: str
    created_date: datetime = Field(default_factory=datetime.utcnow)
    modified_by: Optional[str] = None
    modified_date: datetime = Field(default_factory=datetime.utcnow)
    status: str = "active"

    parameters: List[str]  # if array of strings, or list of dict if complex
    semicon_product_variant_id: str
    semicon_product_variant_pricing_id: List[str]  # multiple pricing IDs

    class Config:
        collection = "product_variants"
