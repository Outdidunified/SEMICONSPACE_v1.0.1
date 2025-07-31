from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Union
from datetime import datetime, timezone
import logging

from app.models.manufacturers_models import Manufacturer
from app.schemas.manufacturers_schema import (
    ManufacturerSchema,
    ManufacturerResponseSchema,
    ManufacturerUpdateRequest,
    ManufacturerStatusToggleRequest,
)
from app.database import engine
from app.kafka.kafka_producer import send_event
from app.auth_utils import get_current_user

router = APIRouter(prefix="/product/manufacturer", tags=["Manufacturer"])
logger = logging.getLogger(__name__)

def success_response(data: Union[dict, list], message: Optional[str] = None):
    response = {
        "error" : "false",
        "data": data
    }
    if message:
        response["message"] = message
    return response

@router.get("/get/list")
async def get_all_manufacturers():
    logger.info("Fetching all manufacturers")
    manufacturers = await engine.find(Manufacturer, Manufacturer.status == True)
    return success_response(
        [ManufacturerResponseSchema.model_validate(m, from_attributes=True).model_dump() for m in manufacturers],
        message="All active manufacturers fetched"
    )


@router.get("/get/{manufacturer_id}")
async def get_manufacturer_by_id(manufacturer_id: int):
    logger.info(f"🔍 Fetching manufacturer by ID: {manufacturer_id}")
    manufacturer = await engine.find_one(Manufacturer, Manufacturer.manufacturer_id == manufacturer_id)
    if not manufacturer:
        logger.warning(f"❌ Manufacturer not found: {manufacturer_id}")
        raise HTTPException(status_code=404, detail="Manufacturer not found")
    return success_response(
        ManufacturerResponseSchema.model_validate(manufacturer, from_attributes=True).model_dump(),
        message=f"Manufacturer {manufacturer_id} found"
    )


@router.post("/add")
async def create_manufacturer(
    manufacturer: ManufacturerSchema,
    current_user: str = Depends(get_current_user)
):
    logger.info(f"➕ Adding new manufacturer: {manufacturer.name}")
    existing = await engine.find_one(Manufacturer, Manufacturer.manufacturer_id == manufacturer.manufacturer_id)
    if existing:
        logger.warning(f"⚠️ Manufacturer already exists: {manufacturer.manufacturer_id}")
        raise HTTPException(status_code=400, detail="Manufacturer already exists")

    now = datetime.now(timezone.utc)
    new_manufacturer = Manufacturer(
        **manufacturer.model_dump(),
        created_by=current_user,
        modified_by=current_user,
        created_date=now,
        modified_date=now,
        #status=True
    )
    await engine.save(new_manufacturer)

    await send_event("manufacturer.created", {
        "action": "manufacturer_added",
        "manufacturer": new_manufacturer.model_dump(),
    })

    return success_response(
        ManufacturerResponseSchema.model_validate(new_manufacturer, from_attributes=True).model_dump(),
        message="Manufacturer created successfully"
    )


@router.put("/update")
async def update_manufacturer(
    update_data: ManufacturerUpdateRequest,
    current_user: str = Depends(get_current_user)
):
    manufacturer_id = update_data.manufacturer_id
    logger.info(f"Updating manufacturer ID: {manufacturer_id}")

    manufacturer = await engine.find_one(Manufacturer, Manufacturer.manufacturer_id == manufacturer_id)
    if not manufacturer:
        logger.warning(f"❌ Manufacturer not found: {manufacturer_id}")
        raise HTTPException(status_code=404, detail="Manufacturer not found")

    # Extract only provided fields excluding manufacturer_id
    update_fields = update_data.model_dump(exclude_unset=True, exclude={"manufacturer_id"})

    # Only update status if explicitly provided
    if "status" in update_fields:
        manufacturer.status = update_fields.pop("status")

    for key, value in update_fields.items():
        setattr(manufacturer, key, value)

    manufacturer.modified_by = current_user
    manufacturer.modified_date = datetime.now(timezone.utc)

    await engine.save(manufacturer)

    await send_event("manufacturer.updated", {
        "action": "manufacturer_updated",
        "manufacturer": manufacturer.model_dump(),
    })

    return success_response(
        ManufacturerResponseSchema.model_validate(manufacturer, from_attributes=True).model_dump(),
        message="Manufacturer updated successfully"
    )

# @router.put("/update")
# async def update_manufacturer(
#     update_data: ManufacturerUpdateRequest,
#     current_user: str = Depends(get_current_user)
# ):
#     manufacturer_id = update_data.manufacturer_id
#     logger.info(f"Updating manufacturer ID: {manufacturer_id}")

#     manufacturer = await engine.find_one(Manufacturer, Manufacturer.manufacturer_id == manufacturer_id)
#     if not manufacturer:
#         logger.warning(f"❌ Manufacturer not found: {manufacturer_id}")
#         raise HTTPException(status_code=404, detail="Manufacturer not found")

#     for key, value in update_data.model_dump(exclude={"manufacturer_id"}, exclude_none=True).items():
#         setattr(manufacturer, key, value)

#     manufacturer.modified_by = current_user
#     manufacturer.modified_date = datetime.now(timezone.utc)

#     await engine.save(manufacturer)

#     await send_event("manufacturer.updated", {
#         "action": "manufacturer_updated",
#         "manufacturer": manufacturer.model_dump(),
#     })

#     return success_response(
#         ManufacturerResponseSchema.model_validate(manufacturer, from_attributes=True).model_dump(),
#         message="Manufacturer updated successfully"
#     )


# @router.post("/status")
# async def toggle_manufacturer_status(
#     request: ManufacturerStatusToggleRequest,
#     current_user: str = Depends(get_current_user)
# ):
#     manufacturer_id = request.manufacturer_id
#     logger.info(f"🔄 Toggling status for manufacturer ID: {manufacturer_id}")

#     manufacturer = await engine.find_one(Manufacturer, Manufacturer.manufacturer_id == manufacturer_id)
#     if not manufacturer:
#         logger.warning(f"❌ Manufacturer ID {manufacturer_id} not found for status toggle.")
#         raise HTTPException(status_code=404, detail="Manufacturer not found")

#     previous_status = manufacturer.status
#     manufacturer.status = not previous_status
#     manufacturer.modified_by = current_user
#     manufacturer.modified_date = datetime.now(timezone.utc)

#     await engine.save(manufacturer)

#     logger.info(
#         f"🔁 Manufacturer {manufacturer_id} toggled from {previous_status} to {manufacturer.status} by {current_user}"
#     )

#     await send_event("manufacturer.activate_deactivate", {
#         "action": "activate" if manufacturer.status else "deactivate",
#         "manufacturer": manufacturer.model_dump(),
#         "toggled_by": current_user,
#     })

#     return success_response(
#         manufacturer.model_dump(),
#         message=f"Manufacturer {manufacturer_id} {'activated' if manufacturer.status else 'deactivated'} successfully",
#     )
