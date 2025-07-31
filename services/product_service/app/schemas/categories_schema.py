from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional


class CategorySchema(BaseModel):
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    status: Optional[bool] = True


class CategoryResponseSchema(CategorySchema):
    id: UUID
    status: Optional[bool] = True
    created_date: Optional[datetime]
    modified_date: Optional[datetime]

    class Config:
        from_attributes = True
        json_encoders = {UUID: lambda u: str(u)}

class CategoryUpdateRequest(BaseModel):
    category_id: int
    category_name: Optional[str] = None
    status: Optional[bool] = None


class CategoryStatusToggleRequest(BaseModel):
    category_id: int
