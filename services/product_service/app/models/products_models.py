from odmantic import Model, Field
from datetime import datetime, timezone
from uuid import UUID, uuid4
from typing import Optional


def generate_64bit_id() -> int:
    return uuid4().int >> 64


class Product(Model):
    id: UUID = Field(primary_field=True, default_factory=uuid4)
    product_id: int
    external_product_id: Optional[str] = None
    supplier: str
    name: str
    description: str
    manufacturer_id: int
    manufacturer_part_number: str
    quantity: int
    category: str
    package_type: str
    datasheet_url: str
    image_url: str
    last_fetched_at: Optional[datetime] = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    category_id: int
    created_by: str
    created_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    modified_by: str
    modified_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    status: bool
    model_config = {"collection": "products"}
