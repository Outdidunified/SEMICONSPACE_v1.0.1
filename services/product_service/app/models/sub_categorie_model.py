from odmantic import Model, Field
from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4
class SubCategory(Model):
    id: UUID = Field(default_factory=uuid4, primary_field=True)
    category_id: str
    subcategory_id: str = Field(unique=True)
    name: str
    imageUrl: Optional[str] = None
    SeoDescription: Optional[str] = None
    status: bool = True
    created_by: Optional[str] = None
    created_date: Optional[datetime] = Field(default_factory=datetime.utcnow)
    modified_by: Optional[str] = None
    modified_date: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    model_config = {
        "collection": "sub_categories"
    }

