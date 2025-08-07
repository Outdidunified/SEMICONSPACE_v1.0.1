from odmantic import Model, EmbeddedModel, Field
from typing import List, Optional
from datetime import datetime
from uuid import uuid4, UUID
class ProductSpecification(Model):
    id: UUID = Field(default_factory=uuid4, primary_field=True)
    #semicon_product_id: str
    parameter_id: str = Field(unique=True)
    parameter_text: Optional[str] = Field(key_name="parameterText")
    parameter_type: Optional[str] = Field(key_name="parameterType")
    value_id: Optional[str] = None
    value_text: Optional[str] = None
    status: Optional[bool] = True
    created_by: Optional[str] = None
    created_date: datetime = Field(default_factory=datetime.utcnow)
    modified_by: Optional[str] = None
    modified_date: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "collection": "product_specifications"
    }
