from fastapi import APIRouter, HTTPException, Query, status
from app.services.sync_semicon_categories import fetch_and_sync_semicon_categories
from app.schemas.categories_schema import SemiconCategoryCreateSchema, SemiconCategoryUpdateSchema
from app.models.categories_models import SemiconCategory
from app.database import engine
from typing import List, Optional
from datetime import datetime
from fastapi.encoders import jsonable_encoder
from odmantic.query import QueryExpression

router = APIRouter(prefix="/product")

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

def transform_category_doc(doc):
    """Transform raw MongoDB document to standard API response format"""
    def transform_child_category(child):
        """Transform nested child category objects, excluding _id"""
        return {
            "semicon_child_category_id": child.get("semicon_child_category_id"),
            "semicon_child_parent_id": child.get("semicon_child_parent_id"),
            "digikey_child_category_id": child.get("digikey_child_category_id"),
            "digikey_child_name": child.get("digikey_child_name"),
            "digikey_parent_id": child.get("digikey_parent_id"),
            "product_count": child.get("product_count", 0),
            "created_by": child.get("created_by"),
            "created_date": child.get("created_date"),
            "modified_by": child.get("modified_by"),
            "modified_date": child.get("modified_date"),
            "status": child.get("status", True),
            "child_categories": [transform_child_category(grandchild) for grandchild in child.get("child_categories", [])]
        }
    return {
        "_id": str(doc["_id"]) if "_id" in doc else None,
        "semicon_category_id": doc.get("semicon_category_id"),
        "semicon_parent_id": doc.get("semicon_parent_id"),
        "digikey_category_id": doc.get("digikey_category_id"),
        "digikey_name": doc.get("digikey_name"),
        "digikey_parent_id": doc.get("digikey_parent_id"),
        "product_count": doc.get("product_count", 0),
        "created_by": doc.get("created_by"),
        "created_date": doc.get("created_date"),
        "modified_by": doc.get("modified_by"),
        "modified_date": doc.get("modified_date"),
        "status": doc.get("status", True),
        "child_categories": [transform_child_category(child) for child in doc.get("child_categories", [])]
    }
@router.get("/categories/all", tags=["Semicon Categories"])
async def get_all_semicon_categories():
    """Get all categories with standardized response format"""
    try:
        # Access the raw MongoDB collection to bypass odmantic validation
        collection = engine.get_collection(SemiconCategory)
        categories = await collection.find().to_list(None)  # Fetch all documents

        # Transform raw documents to the standardized format
        cleaned_data = [transform_category_doc(doc) for doc in categories]
        
        return {
            "error": False,
            "message": "Categories fetched successfully",
            "data": jsonable_encoder(cleaned_data)
        }
    except Exception as e:
        print(f"Error fetching categories: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": True,
                "message": f"Failed to fetch categories: {str(e)}",
                "data": []
            }
        )
@router.get("/categories/{category_id}", tags=["Semicon Categories"])
async def get_category_by_id(category_id: str):
    """Get a specific category by ID"""
    try:
        # Access the raw MongoDB collection to bypass odmantic validation
        collection = engine.get_collection(SemiconCategory)
        category = await collection.find_one({"semicon_category_id": category_id})
        
        if not category:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": True,
                    "message": f"Category with ID {category_id} not found",
                    "data": []
                }
            )
        
        # Transform the raw document to the standardized format
        transformed_category = transform_category_doc(category)
        
        return {
            "error": False,
            "message": "Category fetched successfully",
            "data": jsonable_encoder(transformed_category)
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching category: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": True,
                "message": f"Failed to fetch category: {str(e)}",
                "data": []
            }
        )