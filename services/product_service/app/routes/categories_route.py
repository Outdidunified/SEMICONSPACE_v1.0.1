from fastapi import APIRouter, HTTPException
from app.services.sync_semicon_categories import fetch_and_sync_semicon_categories
from app.schemas.categories_schema import SemiconCategoryCreateSchema
from app.models.categories_models import SemiconCategory
from app.database import engine
from typing import List
from datetime import datetime
from fastapi.encoders import jsonable_encoder

router = APIRouter(prefix="/product")

def transform_category_doc(doc):
    """Transform MongoDB category document to standard API response format"""
    # Access model attributes directly
    ordered_dict = {
        "_id": str(doc.id),
        "semicon_category_id": doc.semicon_category_id,
        "semicon_parent_id": doc.semicon_parent_id,
        "digikey_category_id": doc.digikey_category_id,
        "digikey_name": doc.digikey_name,
        "digikey_parent_id": doc.digikey_parent_id,
        "product_count": doc.product_count,
        "created_by": doc.created_by,
        "created_date": doc.created_date.isoformat().replace("+00:00", "Z") if doc.created_date else None,
        "modified_by": doc.modified_by,
        "modified_date": doc.modified_date.isoformat().replace("+00:00", "Z") if doc.modified_date else None,
        "status": doc.status,
        "child_categories": doc.child_categories
    }
    
    return ordered_dict

# 🚀 Sync categories
@router.get("/sync/categories", tags=["Sync"])
async def sync_semicon_categories():
    result = await fetch_and_sync_semicon_categories()
    if result["status"] == "success":
        return {
            "error": False,
            "message": f"Synced {result.get('saved_count', 0)} categories successfully",
            "data": []
        }
    else:
        raise HTTPException(
            status_code=500,
            detail={
                "error": True,
                "message": "Failed to sync categories",
                "data": []
            }
        )

# 📦 Get all categories with standardized response
@router.get("/categories/all", tags=["Semicon Categories"])
async def get_all_semicon_categories():
    """Get all categories with standardized response format"""
    try:
        categories = await engine.find(SemiconCategory)
        cleaned_data = [transform_category_doc(doc) for doc in categories]
        
        return {
            "error": False,
            "message": "Categories fetched successfully",
            "data": jsonable_encoder(cleaned_data)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": True,
                "message": "Failed to fetch categories",
                "data": []
            }
        )

# 📋 Get category by ID
@router.get("/categories/{category_id}", tags=["Semicon Categories"])
async def get_category_by_id(category_id: str):
    """Get a specific category by ID"""
    try:
        category = await engine.find_one(SemiconCategory, SemiconCategory.semicon_category_id == category_id)
        if not category:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": True,
                    "message": f"Category with ID {category_id} not found",
                    "data": []
                }
            )
        
        return {
            "error": False,
            "message": "Category fetched successfully",
            "data": jsonable_encoder(transform_category_doc(category))
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": True,
                "message": "Failed to fetch category",
                "data": []
            }
        )
