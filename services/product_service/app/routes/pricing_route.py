# # app/routes/vendor_bulk_pricing_routes.py

# from fastapi import APIRouter, Depends, HTTPException
# from datetime import datetime, timezone
# from typing import List, Optional
# import logging
# from uuid import UUID
# from random import randint

# from app.database import engine
# from app.models.pricing_models import VendorBulkPricing, PricingTier
# from app.schemas.pricing_schema import (
#     VendorBulkPricingCreate,
#     VendorBulkPricingUpdate,
#     VendorBulkPricingResponse,
#     PricingTierSchema as pricing_tier
# )

# from app.auth_utils import get_current_user
# #from app.kafka.kafka_producer import send_event

# router = APIRouter(tags=["Vendor Bulk Pricing"], prefix="/vendor/pricing")
# logger = logging.getLogger("vendor_bulk_pricing")


# def success_response(data, message: Optional[str] = None):
#     return {
#         "error": "false",
#         "data": data,
#         "message": message or "Success"
#     }

# @router.post("/add")
# async def create_bulk_pricing(
#     data: VendorBulkPricingCreate,
#     current_user: str = Depends(get_current_user)
# ):
#     import uuid
#     now = datetime.now(timezone.utc)

#     # Generate random IDs instead of relying on request data
#     generated_pricing_record_id = f'SPRID-{str(randint(1000, 9999))}'

#     new_record = VendorBulkPricing(
#         vendor_product_id=data.vendor_product_id,
#         pricing_record_id=generated_pricing_record_id,
#         standard_pricing=[            PricingTier(
#                 break_quantity=item.quantity,
#                 unit_price=item.price,
#                 total_price=item.quantity * item.price
#             )
#             for item in data.standard_pricing
#         ],
#         my_pricing=[            PricingTier(
#                 break_quantity=item.quantity,
#                 unit_price=item.price,
#                 total_price=item.quantity * item.price
#             )
#             for item in data.my_pricing
#         ],
#         status=True,
#         created_by=current_user,
#         created_date=now,
#         modified_by=current_user,
#         modified_date=now
#     )

#     await engine.save(new_record)

#     try:
#         pass
#         #await send_event("vendor.bulk_pricing.created", new_record.model_dump())
#     except Exception as e:
#         logger.error(f"Kafka error: {e}")

#     return success_response(
#         VendorBulkPricingResponse.model_validate(new_record, from_attributes=True).model_dump(),
#         message="Vendor bulk pricing created successfully"
#     )


# @router.get("/get/{pricing_record_id}")
# async def get_vendor_bulk_pricing(pricing_record_id: str):
#     record = await engine.find_one(VendorBulkPricing, VendorBulkPricing.pricing_record_id == pricing_record_id)
#     if not record:
#         raise HTTPException(status_code=404, detail="Record not found")

#     return success_response(
#         VendorBulkPricingResponse.model_validate(record, from_attributes=True).model_dump()
#     )


# @router.put("/update")
# async def update_vendor_bulk_pricing(
#     update_data: VendorBulkPricingUpdate,
#     current_user: str = Depends(get_current_user)
# ):
#     record = await engine.find_one(VendorBulkPricing, VendorBulkPricing.pricing_record_id == update_data.pricing_record_id)
#     if not record:
#         raise HTTPException(status_code=404, detail="Record not found")

#     update_fields = update_data.model_dump(exclude_unset=True, exclude={"id"})

#     for key, value in update_fields.items():
#         setattr(record, key, value)

#     record.modified_by = current_user
#     record.modified_date = datetime.now(timezone.utc)

#     await engine.save(record)

#     try:
#         pass
#         #await send_event("vendor.bulk_pricing.updated", record.model_dump())
#     except Exception as e:
#         logger.error(f"Kafka error: {e}")

#     return success_response(
#         VendorBulkPricingResponse.model_validate(record, from_attributes=True).model_dump(),
#         message="Vendor bulk pricing updated successfully"
#     )


# @router.get("/list")
# async def list_all_bulk_pricings():
#     records = await engine.find(VendorBulkPricing)
#     return success_response([
#         VendorBulkPricingResponse.model_validate(r, from_attributes=True).model_dump()
#         for r in records
#     ])
