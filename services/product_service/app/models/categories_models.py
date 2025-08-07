from __future__ import annotations
from odmantic import Model, Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID


class SemiconChildCategory(Model):
    #id: UUID
    semicon_child_category_id: Optional[str] = None
    semicon_child_parent_id: Optional[str] = None
    digikey_child_category_id:  Optional[int] = None
    digikey_child_name: Optional[str] = None
    digikey_parent_id: Optional[str] = None
    product_count: int = 0
    child_categories: List["SemiconChildCategory"] = Field(default_factory=list)  # ✅ No Optional
    created_by:  Optional[str] = None
    modified_by: Optional[str] = None
    created_date: datetime
    modified_date: datetime
    status: bool = True

# ✅ Rebuild forward refs
SemiconChildCategory.model_rebuild()


class SemiconCategory(Model):
    #id: UUID
    semicon_category_id: str
    semicon_parent_id: Optional[str] = None
    digikey_category_id: int
    digikey_name: str
    digikey_parent_id: str
    product_count: int = 0
    child_categories: List[SemiconChildCategory] = Field(default_factory=list)
    created_by: str
    modified_by: str
    created_date: datetime
    modified_date: datetime
    status: bool = True

    model_config = {
        "collection": "semicon_categories"
    }

SemiconCategory.model_rebuild()
