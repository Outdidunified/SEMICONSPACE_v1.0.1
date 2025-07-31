from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional, Union
from datetime import datetime, timezone
import logging

from app.models.categories_models import Category
from app.schemas.categories_schema import (
    CategorySchema, CategoryResponseSchema,
    CategoryUpdateRequest, CategoryStatusToggleRequest
)
from app.database import engine
from app.auth_utils import get_current_user
from app.kafka.kafka_producer import send_event

router = APIRouter(tags=["Categories"], prefix="/product/category")
logger = logging.getLogger("category_logger")

def success_response(data: Union[dict, list], message: Optional[str] = None):
    response = {
        "error" : "false",
        "data": data
    }
    if message:
        response["message"] = message
    return response
@router.get("/get/list")
async def get_all_categories():
    categories = await engine.find(Category)
    logger.info("Fetched all active categories")
    return success_response([category.model_dump() for category in categories])


@router.get("/get/{category_id}")
async def get_category_by_id(category_id: int):
    category = await engine.find_one(Category, (Category.category_id == category_id))
    if not category:
        logger.warning(f"Category with ID {category_id} not found or inactive")
        raise HTTPException(status_code=404, detail="Category not found")
    logger.info(f"Fetched category with ID: {category_id}")
    return success_response(category.model_dump())

@router.post("/add")
async def create_category(
    category: CategorySchema, current_user: str = Depends(get_current_user)
):
    existing = await engine.find_one(Category, Category.category_id == category.category_id)
    if existing:
        logger.warning(f"Category with ID {category.category_id} already exists")
        raise HTTPException(status_code=400, detail="Category with this ID already exists")

    now = datetime.now(timezone.utc)
    new_cat = Category(
        **category.model_dump(),
        created_by=current_user,
        modified_by=current_user,
        created_date=now,
        modified_date=now,
        #status=True
    )
    await engine.save(new_cat)
    logger.info(f"New category created: {new_cat.category_name} by {current_user}")

    try:
        await send_event("category.created", {
            "category_id": new_cat.category_id,
            "category_name": new_cat.category_name,
            "created_by": current_user,
            "created_date": new_cat.created_date.isoformat()
        })
    except Exception as e:
        logger.error(f"Kafka error while sending category.created: {e}")

    return success_response(new_cat.model_dump(), message="Category created successfully")


@router.put("/update")
async def update_category_by_body(
    update_data: CategoryUpdateRequest,
    current_user: str = Depends(get_current_user)
):
    category = await engine.find_one(Category, Category.category_id == update_data.category_id)
    if not category:
        logger.error(f"❌ Attempt to update non-existent category ID: {update_data.category_id}")
        raise HTTPException(status_code=404, detail="Category not found")

    # Extract only provided fields except category_id
    update_fields = update_data.model_dump(exclude_unset=True, exclude={"category_id"})

    # Only update status if it is explicitly provided
    if "status" in update_fields:
        category.status = update_fields.pop("status")

    # Update remaining fields
    for key, value in update_fields.items():
        setattr(category, key, value)

    category.modified_by = current_user
    category.modified_date = datetime.now(timezone.utc)

    await engine.save(category)

    logger.info(f"✅ Category {category.category_id} updated by {current_user}")

    try:
        await send_event("category.updated", {
            "category_id": category.category_id,
            "category_name": category.category_name,
            "modified_by": current_user,
            "modified_date": category.modified_date.isoformat()
        })
    except Exception as e:
        logger.error(f"⚠️ Kafka error while sending category.updated: {e}")

    return success_response(category.model_dump(), message=f"Category {update_data.category_id} updated successfully")

# @router.put("/update")
# async def update_category_by_body(
#     update_data: CategoryUpdateRequest,
#     current_user: str = Depends(get_current_user)
# ):
#     category = await engine.find_one(Category, Category.category_id == update_data.category_id)
#     if not category:
#         logger.error(f"❌ Attempt to update non-existent category ID: {update_data.category_id}")
#         raise HTTPException(status_code=404, detail="Category not found")

#     for key, value in update_data.model_dump(exclude={"category_id"}).items():
#         if value is not None:
#             setattr(category, key, value)

#     category.modified_by = current_user
#     category.modified_date = datetime.now(timezone.utc)

#     await engine.save(category)

#     logger.info(f"✅ Category {category.category_id} updated by {current_user}")

#     try:
#         await send_event("category.updated", {
#             "category_id": category.category_id,
#             "category_name": category.category_name,
#             "modified_by": current_user,
#             "modified_date": category.modified_date.isoformat()
#         })
#     except Exception as e:
#         logger.error(f"⚠️ Kafka error while sending category.updated: {e}")

#     return success_response(category.model_dump(), message=f"Category {update_data.category_id} updated successfully")


# @router.post("/status")
# async def toggle_category_status_by_body(
#     request: CategoryStatusToggleRequest,
#     current_user: str = Depends(get_current_user)
# ):
#     category = await engine.find_one(Category, Category.category_id == request.category_id)
#     if not category:
#         logger.error(f"❌ Attempt to toggle status of non-existent category ID: {request.category_id}")
#         raise HTTPException(status_code=404, detail="Category not found")

#     previous_status = category.status
#     category.status = not previous_status
#     category.modified_by = current_user
#     category.modified_date = datetime.now(timezone.utc)

#     await engine.save(category)

#     logger.info(
#         f"🔁 Category {request.category_id} status toggled from {previous_status} to {category.status} by {current_user}"
#     )

#     try:
#         await send_event("category.activate_deactivate", {
#             "action": "activate" if category.status else "deactivate",
#             "category": category.model_dump(),
#             "toggled_by": current_user,
#         })
#     except Exception as e:
#         logger.error(f"⚠️ Kafka error while sending category.activate_deactivate: {e}")
   
#     return success_response(
#     category.model_dump(),
#     message=f"Category {request.category_id} {'activated' if category.status else 'deactivated'} successfully"
#     )
