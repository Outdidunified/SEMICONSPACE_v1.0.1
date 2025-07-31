from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
import logging
from odmantic.query import desc
from typing import List, Optional, Union

from app.models.specifications_models import ProductSpecification
from app.models.products_models import Product
from app.schemas.specifications_schema import (
    ProductSpecificationSchema,
    ProductSpecificationUpdateRequest,
    ProductSpecificationStatusToggleRequest,
    ProductSpecificationResponseSchema,
)
from app.database import engine
from app.auth_utils import get_current_user
from app.kafka.kafka_producer import send_event

router = APIRouter(prefix="/product/specification", tags=["Product Specifications"])
logger = logging.getLogger("specification_logger")
logging.basicConfig(level=logging.INFO)

# Reusable response formatter
def success_response(data: Union[dict, list], message: Optional[str] = None):
    response = {
        "error" : "false",
        "data": data
    }
    if message:
        response["message"] = message
    return response

@router.get("/get/{product_id}")
async def get_product_specs(product_id: int):
    specs = await engine.find(ProductSpecification, ProductSpecification.product_id == product_id)
    if not specs:
        logger.warning(f"No specs found for product {product_id}")
        raise HTTPException(status_code=404, detail="No specifications found")

    return success_response(
        [ProductSpecificationResponseSchema.model_validate(s, from_attributes=True) for s in specs]
    )

@router.post("/add")
async def create_product_spec(
    spec: ProductSpecificationSchema,
    current_user: str = Depends(get_current_user),
):
    product = await engine.find_one(Product, Product.product_id == spec.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    last_spec = await engine.find_one(
        ProductSpecification,
        ProductSpecification.product_id == spec.product_id,
        sort=desc(ProductSpecification.spec_id),
    )
    next_spec_id = last_spec.spec_id + 1 if last_spec and last_spec.spec_id else 1

    now = datetime.now(timezone.utc)
    new_spec = ProductSpecification(
        **spec.model_dump(exclude={"spec_id", "status"}),
        spec_id=next_spec_id,
        created_by=current_user,
        modified_by=current_user,
        created_date=now,
        modified_date=now,
        status=True,
    )
    await engine.save(new_spec)
    logger.info(f"✅ Spec added for product {spec.product_id} by {current_user}")

    try:
        await send_event("product.specification.added", {
            "product_id": spec.product_id,
            "spec_id": new_spec.spec_id,
            "parameter_name": new_spec.parameter_name,
            "parameter_value": new_spec.parameter_value,
            "created_by": current_user,
            "created_date": now.isoformat()
        })
    except Exception as e:
        logger.error(f"Kafka error: {e}")

    return success_response(
    ProductSpecificationResponseSchema.model_validate(new_spec, from_attributes=True).model_dump(),
    message="Specification added successfully"
)

@router.put("/update")
async def update_spec_for_product(
    update_data: ProductSpecificationUpdateRequest,
    current_user: str = Depends(get_current_user),
):
    spec = await engine.find_one(
        ProductSpecification,
        (ProductSpecification.product_id == update_data.product_id) &
        (ProductSpecification.spec_id == update_data.spec_id)
    )
    if not spec:
        raise HTTPException(status_code=404, detail="Specification not found")

    update_fields = update_data.model_dump(exclude_unset=True, exclude={"product_id", "spec_id"})

    for key, value in update_fields.items():
        setattr(spec, key, value)

    spec.modified_by = current_user
    spec.modified_date = datetime.now(timezone.utc)
    await engine.save(spec)

    logger.info(f"📝 Spec {spec.spec_id} updated for product {spec.product_id} by {current_user}")

    try:
        await send_event("product.specification.updated", {
            "product_id": spec.product_id,
            "spec_id": spec.spec_id,
            "parameter_name": spec.parameter_name,
            "parameter_value": spec.parameter_value,
            "modified_by": current_user,
            "modified_date": spec.modified_date.isoformat(),
        })
    except Exception as e:
        logger.error(f"Kafka error: {e}")

    return success_response(
        ProductSpecificationResponseSchema.model_validate(spec, from_attributes=True).model_dump(),
        message="Specification updated successfully"
    )

# @router.put("/update")
# async def update_spec_for_product(
#     update_data: ProductSpecificationUpdateRequest,
#     current_user: str = Depends(get_current_user),
# ):
#     spec = await engine.find_one(
#         ProductSpecification,
#         (ProductSpecification.product_id == update_data.product_id) &
#         (ProductSpecification.spec_id == update_data.spec_id)
#     )
#     if not spec:
#         raise HTTPException(status_code=404, detail="Specification not found")

#     for key, value in update_data.model_dump(exclude={"product_id", "spec_id"}).items():
#         if value is not None:
#             setattr(spec, key, value)

#     spec.modified_by = current_user
#     spec.modified_date = datetime.now(timezone.utc)
#     await engine.save(spec)

#     logger.info(f"📝 Spec {spec.spec_id} updated for product {spec.product_id} by {current_user}")
#     try:
#         await send_event("product.specification.updated", {
#             "product_id": spec.product_id,
#             "spec_id": spec.spec_id,
#             "parameter_name": spec.parameter_name,
#             "parameter_value": spec.parameter_value,
#             "modified_by": current_user,
#             "modified_date": spec.modified_date.isoformat(),
#         })
#     except Exception as e:
#         logger.error(f"Kafka error: {e}")

#     return success_response(
#     ProductSpecificationResponseSchema.model_validate(spec, from_attributes=True).model_dump(),
#     message="Specification updated successfully"
#     )

# @router.post("/status")
# async def toggle_product_specification_status(
#     req: ProductSpecificationStatusToggleRequest,
#     current_user: str = Depends(get_current_user),
# ):
#     spec = await engine.find_one(
#         ProductSpecification,
#         (ProductSpecification.product_id == req.product_id) &
#         (ProductSpecification.spec_id == req.spec_id)
#     )
#     if not spec:
#         logger.error(f"❌ Spec ID {req.spec_id} for product {req.product_id} not found")
#         raise HTTPException(status_code=404, detail="Specification not found")

#     previous_status = spec.status
#     spec.status = not previous_status
#     spec.modified_by = current_user
#     spec.modified_date = datetime.now(timezone.utc)
#     await engine.save(spec)

#     logger.info(
#         f"🔁 Spec {spec.spec_id} for product {spec.product_id} toggled from {previous_status} to {spec.status} by {current_user}"
#     )

#     try:
#         await send_event("product.specification.activate_deactivate", {
#             "action": "activate" if spec.status else "deactivate",
#             "product_id": spec.product_id,
#             "spec_id": spec.spec_id,
#             "parameter_name": spec.parameter_name,
#             "parameter_value": spec.parameter_value,
#             "status": spec.status,
#             "toggled_by": current_user,
#             "modified_date": spec.modified_date.isoformat()
#         })
#     except Exception as e:
#         logger.error(f"Kafka error while sending toggle: {e}")

#     return success_response(
#         ProductSpecificationResponseSchema.model_validate(spec, from_attributes=True).model_dump()
#         , message=f"Specification {spec.spec_id} for product {spec.product_id} {'activated' if spec.status else 'deactivated'} successfully")
