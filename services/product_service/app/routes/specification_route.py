# from fastapi import APIRouter, HTTPException
# from datetime import datetime
# import logging
# from typing import Optional
# from random import randint

# from app.models.specifications_models import ProductSpecification
# from app.schemas.specifications_schema import (
#     ProductSpecificationCreate,
#     ProductSpecificationUpdate,
#     ProductSpecificationResponse
# )
# from app.database import engine
# from app.kafka.kafka_producer import send_event




# router = APIRouter(prefix="/specification", tags=["Specifications"])
# logger = logging.getLogger(__name__)

# def success_response(data, message: Optional[str] = None):
#     return {
#         "status": "success",
#         "data": data,
#         **({"message": message} if message else {})
#     }
# @router.post("/add")
# async def add_specification(spec_data: ProductSpecificationCreate):
#     try:
#         # Generate unique parameter_id like "SPSID-1234"
#         while True:
#             parameter_id = f"SPSID-{randint(1000, 9999)}"
#             existing_spec = await engine.find_one(ProductSpecification, ProductSpecification.parameter_id == parameter_id)
#             if not existing_spec:
#                 break

#         spec = ProductSpecification(
#             **spec_data.model_dump(),
#             parameter_id=parameter_id,
#             created_date=datetime.utcnow(),
#             modified_date=datetime.utcnow()
#         )
#         await send_event("specification.created", {
#             "parameter_id": spec.parameter_id,
#             "parameter_text": spec.parameter_text,
#             "parameter_type": spec.parameter_type,
#             "created_by": spec.created_by,
#             "created_date": str(spec.created_date)
#         })
        
#         await engine.save(spec)

#         return success_response(
#             ProductSpecificationResponse.model_validate(spec, from_attributes=True),
#             message="Specification added"
#         )

#     except Exception as e:
#         logger.error(f"Failed to add specification: {e}")
#         raise HTTPException(status_code=500, detail={"status": "failure", "message": "Internal server error"})
# @router.get("/get/{parameter_id}")
# async def get_specs_by_product_id(parameter_id: str):
#     specs = await engine.find(ProductSpecification, ProductSpecification.parameter_id == parameter_id)
#     if not specs:
#         raise HTTPException(status_code=404, detail="No specifications found")
#     return success_response([ProductSpecificationResponse.model_validate(s, from_attributes=True) for s in specs])

# @router.put("/update")
# async def update_specification(data: ProductSpecificationUpdate):
#     spec = await engine.find_one(ProductSpecification, ProductSpecification.parameter_id == data.parameter_id)
#     if not spec:
#         raise HTTPException(status_code=404, detail="Specification not found")

#     if data.parameter_text is not None:
#         spec.parameter_text = data.parameter_text
#     if data.parameter_type is not None:
#         spec.parameter_type = data.parameter_type
#     if data.status is not None:
#         spec.status = data.status
#     if data.modified_by is not None:
#         spec.modified_by = data.modified_by

#     spec.modified_date = datetime.utcnow()
#     await engine.save(spec)
#     return success_response(ProductSpecificationResponse.model_validate(spec, from_attributes=True), message="Specification updated")

