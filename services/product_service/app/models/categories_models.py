from odmantic import Model, Field
from uuid import uuid4, UUID
from typing import Optional
from datetime import datetime, timezone


class Category(Model):
    id: UUID = Field(default_factory=uuid4, primary_field=True)
    category_id: int
    category_name: str
    parent_id: Optional[int] = None
    created_by: str
    created_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    modified_by: str
    modified_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    status: bool

    model_config = {"collection": "categories"}
