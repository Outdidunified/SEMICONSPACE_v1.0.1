from odmantic import Model, Field
from datetime import datetime, timezone
from uuid import UUID, uuid4


class ProductSpecification(Model):
    id: UUID = Field(primary_field=True, default_factory=uuid4)
    spec_id: int
    product_id: int
    parameter_name: str
    parameter_value: str
    created_by: str
    created_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    modified_by: str
    modified_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    status: bool
    model_config = {"collection": "product_specifications"}
