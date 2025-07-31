from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID


class ProductSchema(BaseModel):
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
    category_id: int


class ProductIDRequest(BaseModel):
    product_id: int

class ProductUpdateWithIDSchema(BaseModel):
    product_id: int
    external_product_id: Optional[str] = None
    name: Optional[str] = None
    quantity: Optional[int] = None
    supplier: Optional[str] = None
    status: Optional[bool] = None
    category: Optional[str] = None
    category_id: Optional[int] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    datasheet_url: Optional[str] = None
    manufacturer_part_number: Optional[str] = None
    manufacturer_id: Optional[int] = None
    package_type: Optional[str] = None
    last_fetched_at: Optional[datetime] = None
class ProductResponseSchema(ProductSchema):
    id: UUID
    created_by: str
    modified_by: str
    status: bool
    created_date: Optional[datetime]
    modified_date: Optional[datetime]

    class Config:
        from_attributes = True
        json_encoders = {UUID: lambda u: str(u)}
