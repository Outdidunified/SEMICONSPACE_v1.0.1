from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal
from uuid import UUID
from datetime import datetime


class ProductPricingSchema(BaseModel):
    product_id: int
    currency: str
    price: Decimal
    min_quantity: int
    # Don't accept this from user; it’s copied from Product
    available_quantity: Optional[int] = None


class ProductPricingResponseSchema(BaseModel):
    id: UUID
    product_pricing_id: int
    product_id: int
    currency: str
    price: float
    min_quantity: int
    available_quantity: int
    last_updated: datetime
    created_by: str
    created_date: datetime
    modified_by: str
    modified_date: datetime
    status: bool


class ProductPricingUpdateRequest(BaseModel):
    product_pricing_id: int
    product_id: int
    currency: Optional[str] = None
    price: Optional[Decimal] = None
    min_quantity: Optional[int] = None
    available_quantity: Optional[int] = None
    status: Optional[bool] = None


class ProductPricingStatusToggleRequest(BaseModel):
    product_id: int
