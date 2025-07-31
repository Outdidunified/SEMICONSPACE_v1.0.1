from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
from typing import List, Optional, Union
import logging
from odmantic.query import desc

from app.models.pricing_models import ProductPricing
from app.models.products_models import Product
from app.schemas.pricing_schema import (
    ProductPricingSchema,
    ProductPricingResponseSchema,
    ProductPricingUpdateRequest,
    ProductPricingStatusToggleRequest,
)
from app.auth_utils import get_current_user
from app.database import engine
from app.kafka.kafka_producer import send_event

router = APIRouter(tags=["Product Pricing"], prefix="/product/pricing")
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def success_response(data: Union[dict, list], message: Optional[str] = None):
    response = {
        "error": "false",
        "data": data
    }
    if message:
        response["message"] = message
    return response


async def get_next_pricing_id() -> int:
    last = await engine.find(ProductPricing, sort=desc(ProductPricing.product_pricing_id), limit=1)
    return (last[0].product_pricing_id + 1) if last else 1


@router.post("/add")
async def add_pricing(
    pricing: ProductPricingSchema,
    current_user: str = Depends(get_current_user)
):
    product = await engine.find_one(Product, Product.product_id == pricing.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # ✅ ALLOW multiple pricing tiers for same product with different min_quantity
    existing = await engine.find_one(
        ProductPricing,
        (ProductPricing.product_id == pricing.product_id) &
        (ProductPricing.min_quantity == pricing.min_quantity)
    )
    if existing:
        raise HTTPException(status_code=400, detail="Pricing tier with this min_quantity already exists for the product")

    now = datetime.now(timezone.utc)
    next_id = await get_next_pricing_id()

    new_pricing = ProductPricing(
        product_pricing_id=next_id,
        product_id=pricing.product_id,
        currency=pricing.currency,
        price=float(pricing.price),
        min_quantity=pricing.min_quantity,
        available_quantity=product.quantity,
        created_by=current_user,
        modified_by=current_user,
        created_date=now,
        modified_date=now,
        last_updated=now,
        status=True,
    )

    await engine.save(new_pricing)

    try:
        await send_event("product.pricing.added", new_pricing.model_dump())
    except Exception as e:
        logger.error(f"Kafka error: {e}")

    return success_response(
        {"pricing": ProductPricingResponseSchema.model_validate(new_pricing, from_attributes=True).model_dump()},
        message="Product pricing tier added successfully"
    )


@router.get("/list/{product_id}")
async def list_pricing_by_product(product_id: int):
    pricing_list = await engine.find(ProductPricing, ProductPricing.product_id == product_id)
    if not pricing_list:
        raise HTTPException(status_code=404, detail="No pricing found for this product")

    return success_response(
        {"pricing": [
            ProductPricingResponseSchema.model_validate(p, from_attributes=True).model_dump()
            for p in pricing_list
        ]},
        message="All pricing tiers retrieved"
    )

@router.put("/update")
async def update_pricing_by_body(
    update_data: ProductPricingUpdateRequest,
    current_user: str = Depends(get_current_user)
):
    pricing = await engine.find_one(ProductPricing, ProductPricing.product_pricing_id == update_data.product_pricing_id)
    if not pricing:
        raise HTTPException(status_code=404, detail="Pricing not found")

    for k, v in update_data.model_dump(exclude={"product_pricing_id"}, exclude_none=True).items():
        setattr(pricing, k, float(v) if k == "price" else v)

    now = datetime.now(timezone.utc)
    pricing.modified_by = current_user
    pricing.modified_date = now
    pricing.last_updated = now

    await engine.save(pricing)

    try:
        await send_event("product.pricing.updated", pricing.model_dump())
    except Exception as e:
        logger.error(f"Kafka error: {e}")

    return success_response(
        {"pricing": ProductPricingResponseSchema.model_validate(pricing, from_attributes=True).model_dump()},
        message="Product pricing updated successfully"
    )

# @router.put("/update")
# async def update_pricing_by_body(
#     update_data: ProductPricingUpdateRequest,
#     current_user: str = Depends(get_current_user)
# ):
#     pricing = await engine.find_one(ProductPricing, ProductPricing.product_pricing_id == update_data.product_pricing_id)
#     if not pricing:
#         raise HTTPException(status_code=404, detail="Pricing not found")

#     for k, v in update_data.model_dump(exclude={"product_pricing_id"}, exclude_none=True).items():
#         setattr(pricing, k, float(v) if k == "price" else v)

#     now = datetime.now(timezone.utc)
#     pricing.modified_by = current_user
#     pricing.modified_date = now
#     pricing.last_updated = now

#     await engine.save(pricing)

#     try:
#         await send_event("product.pricing.updated", pricing.model_dump())
#     except Exception as e:
#         logger.error(f"Kafka error: {e}")

#     return success_response(
#         {"pricing": ProductPricingResponseSchema.model_validate(pricing, from_attributes=True).model_dump()},
#         message="Product pricing updated successfully"
#     )


# @router.post("/status")
# async def toggle_pricing_status_by_body(
#     request: ProductPricingStatusToggleRequest,
#     current_user: str = Depends(get_current_user)
# ):
#     pricing = await engine.find_one(ProductPricing, ProductPricing.product_pricing_id == request.product_pricing_id)
#     if not pricing:
#         raise HTTPException(status_code=404, detail="Pricing not found")

#     pricing.status = not pricing.status
#     pricing.modified_by = current_user
#     pricing.modified_date = datetime.now(timezone.utc)

#     await engine.save(pricing)

#     try:
#         await send_event("product.pricing.activate_deactivate", {
#             "action": "activate" if pricing.status else "deactivate",
#             "pricing": pricing.model_dump(),
#             "toggled_by": current_user,
#         })
#     except Exception as e:
#         logger.error(f"Kafka error while sending pricing toggle event: {e}")

#     return success_response(
#         {"pricing": ProductPricingResponseSchema.model_validate(pricing, from_attributes=True).model_dump()},
#         message=f"Pricing for product {pricing.product_id} {'activated' if pricing.status else 'deactivated'} successfully"
#     )
