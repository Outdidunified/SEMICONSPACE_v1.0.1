from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID


class ManufacturerSchema(BaseModel):
    manufacturer_id: Optional[int] = None
    name: Optional[str] = None
    status: Optional[bool] = True


class ManufacturerUpdateSchema(BaseModel):
    name: Optional[str] = None
    status: Optional[bool] = None

class ManufacturerUpdateRequest(BaseModel):
    manufacturer_id: int
    name: Optional[str] = None
    status: Optional[bool] = None


class ManufacturerStatusToggleRequest(BaseModel):
    manufacturer_id: int

class ManufacturerResponseSchema(ManufacturerSchema):
    id: UUID
    created_date: Optional[datetime]
    modified_date: Optional[datetime]

    class Config:
        from_attributes = True
