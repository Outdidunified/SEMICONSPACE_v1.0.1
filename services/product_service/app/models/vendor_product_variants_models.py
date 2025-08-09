import uuid
from typing import List
from odmantic import Model, Field
from datetime import datetime


class VendorProduct(Model):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_field=True)
    vendor_name: str
    vendor_product_number: str
    created_by: str
    created_date: datetime = Field(default_factory=datetime.utcnow)
    modified_by: str
    modified_date: datetime = Field(default_factory=datetime.utcnow)
    status: str
    product_variants: List[str]  # list of SPVID-xxx
    semicon_part_number: str

    model_config = {
        "collection" :"vendor_products"
     }