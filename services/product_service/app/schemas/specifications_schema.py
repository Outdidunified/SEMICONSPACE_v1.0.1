from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID


class ProductSpecificationSchema(BaseModel):
    product_id: int
    parameter_name: Optional[str] = None
    parameter_value: Optional[str] = None
    status: Optional[bool] = True


class ProductSpecificationUpdateRequest(ProductSpecificationSchema):
    spec_id: int


class ProductSpecificationStatusToggleRequest(BaseModel):
    product_id: int
    spec_id: int


class ProductSpecificationResponseSchema(ProductSpecificationSchema):
    spec_id: int
    id: UUID
    created_date: Optional[datetime]
    modified_date: Optional[datetime]

    class Config:
        from_attributes = True
        json_encoders = {UUID: lambda u: str(u)}
