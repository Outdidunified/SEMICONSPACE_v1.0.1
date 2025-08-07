from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class SemiconChildCategorySchema(BaseModel):
    semicon_child_category_id: Optional[str] = None
    semicon_child_parent_id: Optional[str] = None
    digikey_child_category_id: Optional[int] = None
    digikey_child_name: Optional[str] = None
    digikey_parent_id: Optional[str] = None
    product_count: Optional[int] = 0
    created_by: Optional[str] = None
    modified_by: Optional[str] = None
    created_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None
    status: Optional[bool] = True
    child_categories: Optional[List["SemiconChildCategorySchema"]] = []

    class Config:
        orm_mode = True


SemiconChildCategorySchema.model_rebuild()


class SemiconCategoryCreateSchema(BaseModel):
    semicon_category_id: Optional[str] = None
    semicon_parent_id: Optional[str] = None
    digikey_category_id: Optional[int] = None
    digikey_name: Optional[str] = None
    digikey_parent_id: Optional[str] = None
    product_count: Optional[int] = 0
    created_by: Optional[str] = None
    modified_by: Optional[str] = None
    created_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None
    status: Optional[bool] = True
    child_categories: Optional[List[SemiconChildCategorySchema]] = []

    class Config:
        orm_mode = True

class SemiconChildCategoryUpdateSchema(BaseModel):
    semicon_child_category_id: str
    semicon_child_parent_id: Optional[str] = None
    digikey_child_category_id: Optional[int] = None
    digikey_child_name: Optional[str] = None
    digikey_parent_id: Optional[str] = None
    product_count: Optional[int] = 0
    status: Optional[bool] = True
    modified_by: Optional[str] = "admin"


class SemiconCategoryUpdateSchema(BaseModel):
    semicon_category_id: str
    semicon_parent_id: Optional[str] = None
    digikey_category_id: Optional[int] = None
    digikey_name: Optional[str] = None
    digikey_parent_id: Optional[str] = None
    product_count: Optional[int] = 0
    status: Optional[bool] = True
    modified_by: Optional[str] = "admin"
    child_categories: Optional[List[SemiconChildCategoryUpdateSchema]] = None