from odmantic import Model, EmbeddedModel, Field
from typing import List, Optional
from datetime import datetime
from uuid import uuid4, UUID

class Parameter(EmbeddedModel):
    parameter_id: Optional[str] = None  # Generated as SPSID-1234
    value_id:  Optional[str] = None  # Generated as VAL-1234
    value_text: Optional[str] = None
    parameter_text: Optional[str] = None
    parameter_type: Optional[str] = None

class SemiconProduct(Model):
    id: UUID = Field(default_factory=uuid4, primary_field=True)
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    semicon_product_id: str = Field(unique=True)
    datasheet_url: Optional[str] = None
    package_type: Optional[str] = None
    quantity_available: Optional[int] = None
    unitprice: Optional[float] = None
    currency: Optional[str] = None
    manufacturer_part_number: Optional[str] = None
    vendors: List[str] = Field(default_factory=list)
    semicon_part_number: Optional[str] = None
    semicon_category_id: Optional[str] = None
    semicon_child_category_id: Optional[str] = None
    created_by: Optional[str] = None
    created_date: datetime = Field(default_factory=datetime.utcnow)
    modified_by: Optional[str] = None
    modified_date: datetime = Field(default_factory=datetime.utcnow)
    status: Optional[str] = None
    model_config = {
        "collection": "semicon_products"
    }
