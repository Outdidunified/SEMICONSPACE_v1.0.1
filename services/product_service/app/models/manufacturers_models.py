from odmantic import Model, Field
from uuid import UUID, uuid4
from datetime import datetime, timezone


class Manufacturer(Model):
    id: UUID = Field(primary_field=True, default_factory=uuid4)
    manufacturer_id: int
    name: str
    created_by: str
    created_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    modified_by: str
    modified_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    status: bool

    model_config = {"collection": "manufacturers"}
