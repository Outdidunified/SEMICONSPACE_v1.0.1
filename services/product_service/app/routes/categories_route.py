from fastapi import APIRouter, HTTPException
from app.services.sync_semicon_categories import fetch_and_sync_semicon_categories
from app.schemas.categories_schema import SemiconCategoryCreateSchema, SemiconChildCategorySchema, SemiconCategoryUpdateSchema
from app.models.categories_models import SemiconCategory, SemiconChildCategory
from app.database import engine
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/product")

# 🚀 Sync categories
@router.get("/sync/categories", tags=["Sync"])
async def sync_semicon_categories():
    result = await fetch_and_sync_semicon_categories()
    if result["status"] == "success":
        return {
            "status": "success",
            "message": f"Synced {result.get('saved_count', 0)} categories."
        }
    else:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "failure",
                "message": "Failed to sync categories.",
                "error": result.get("detail")
            }
        )

# 📦 Get all categories
@router.get("/all/categories", response_model=List[SemiconCategoryCreateSchema])
async def get_all_semicon_categories():
    categories = await engine.find(SemiconCategory)
    return categories
# 🔢 Get next category ID
async def get_next_semicon_category_counter():
    docs = await engine.find(SemiconCategory)
    max_id = 0
    for doc in docs:
        try:
            current = int(doc.semicon_category_id.split("-")[1])
            max_id = max(max_id, current)
        except:
            continue
    return max_id + 1


# 🔁 Recursive child saving
async def save_child_recursive(child: SemiconChildCategorySchema, parent_id: str, prefix: str, index: int) -> SemiconChildCategory:
    child_id = child.semicon_child_category_id or f"{prefix}-{index}"
    created = SemiconChildCategory(
        semicon_child_category_id=child_id,
        semicon_child_parent_id=parent_id,
        digikey_child_category_id=child.digikey_child_category_id,
        digikey_child_name=child.digikey_child_name,
        digikey_parent_id=child.digikey_parent_id,
        product_count=child.product_count or 0,
        created_by=child.created_by or "system",
        modified_by=child.modified_by or "system",
        created_date=child.created_date or datetime.utcnow(),
        modified_date=child.modified_date or datetime.utcnow(),
        status=child.status if child.status is not None else True,
        child_categories=[]  # will fill after recursive call
    ) # type: ignore

    # Save this node first
    await engine.save(created)

    # Recursively save children
    for i, grandchild in enumerate(child.child_categories or []):
        saved_grandchild = await save_child_recursive(grandchild, child_id, f"{child_id}-C", i + 1)
        created.child_categories.append(saved_grandchild)

    # Save updated node with child_categories
    await engine.save(created)
    return created


# ➕ Add categories with nested children
@router.post("/add/categories", response_model=List[SemiconCategoryCreateSchema])
async def add_semicon_categories(categories: List[SemiconCategoryCreateSchema]):
    added = []
    counter = await get_next_semicon_category_counter()

    for cat in categories:
        semicon_id = cat.semicon_category_id or f"SCID-{counter}"
        counter += 1

        new_cat = SemiconCategory(
            semicon_category_id=semicon_id,
            semicon_parent_id=cat.semicon_parent_id,
            digikey_category_id=cat.digikey_category_id,
            digikey_name=cat.digikey_name,
            digikey_parent_id=cat.digikey_parent_id,
            product_count=cat.product_count or 0,
            created_by=cat.created_by or "system",
            modified_by=cat.modified_by or "system",
            created_date=cat.created_date or datetime.utcnow(),
            modified_date=cat.modified_date or datetime.utcnow(),
            status=cat.status if cat.status is not None else True,
            child_categories=[]
        ) # type: ignore

        # Save parent category
        await engine.save(new_cat)

        # Save each top-level child recursively
        for idx, child in enumerate(cat.child_categories or []):
            saved_child = await save_child_recursive(child, new_cat.semicon_category_id, f"SCCID-{cat.digikey_category_id}", idx + 1)
            new_cat.child_categories.append(saved_child)

        # Save updated parent with children
        await engine.save(new_cat)
        added.append(new_cat)

    return added

@router.put("/category/update")
async def update_semicon_category(payload: SemiconCategoryUpdateSchema):
    existing_category = await engine.find_one(
        SemiconCategory, SemiconCategory.semicon_category_id == payload.semicon_category_id
    )

    if not existing_category:
        raise HTTPException(
            status_code=404,
            detail={"status": "failure", "message": "SemiconCategory not found"}
        )

    # Update top-level fields
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field != "child_categories":
            setattr(existing_category, field, value)

    # Optional: update child_categories
    if payload.child_categories:
        updated_children = []
        for child in payload.child_categories:
            existing_child = next(
                (c for c in existing_category.child_categories if c.semicon_child_category_id == child.semicon_child_category_id),
                None
            )
            if existing_child:
                for key, val in child.model_dump(exclude_unset=True).items():
                    setattr(existing_child, key, val)
                existing_child.modified_date = datetime.utcnow()
                updated_children.append(existing_child)
            else:
                new_child = SemiconChildCategory(
                    **child.model_dump(),
                    created_date=datetime.utcnow(),
                    modified_date=datetime.utcnow()
                )
                updated_children.append(new_child)
        existing_category.child_categories = updated_children
    
    existing_category.modified_date = datetime.utcnow()

    await engine.save(existing_category)
    return {"status": "success", "message": "Category updated successfully"}