from fastapi import APIRouter, Depends, HTTPException, Query
from odmantic import ObjectId
from datetime import datetime
from typing import Optional
from app.database import engine, client
from app.models.manufacturers_models import SemiconManufacturer
from app.models.semicon_products_details import SemiconProduct
from app.schemas.manufacturers_schema import (
    SemiconManufacturerCreateSchema,
    SemiconManufacturerUpdateSchema,
)
from app.autogenerate import get_next_manufacturer_counter
from fastapi.encoders import jsonable_encoder
import logging

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/product")


def transform_mongo_doc(doc):
    """Transform MongoDB document to standard API response format"""
    doc_dict = doc.dict()
    
    # Create ordered dictionary with _id first
    ordered_dict = {
        "created_by": doc_dict.get("created_by"),
        "created_date": doc_dict.get("created_date").isoformat().replace("+00:00", "Z") if doc_dict.get("created_date") else None,
        "digikey_manufacturer_id": doc_dict.get("digikey_manufacturer_id"),
        "digikey_name": doc_dict.get("digikey_name"),
        "modified_by": doc_dict.get("modified_by"),
        "modified_date": doc_dict.get("modified_date").isoformat().replace("+00:00", "Z") if doc_dict.get("modified_date") else None,
        "semicon_manufacturer_id": doc_dict.get("semicon_manufacturer_id"),
        "status": doc_dict.get("status")
    }
    
    return ordered_dict


@router.get("/manufacturer/all", tags=["Semicon Manufacturer"])
async def get_all_manufacturers():
    """Get all manufacturers with standardized response format"""
    try:
        raw_data = await engine.find(SemiconManufacturer)
        cleaned_data = [transform_mongo_doc(doc) for doc in raw_data]
        
        return {
            "error": False,
            "message": "Manufacturers fetched successfully",
            "data": jsonable_encoder(cleaned_data)
        }
    except Exception as e:
        logger.error(f"Error fetching manufacturers: {str(e)}")
        # Fallback to raw MongoDB query if ODMantic validation fails
        raw_docs = await engine.find(SemiconManufacturer, limit=1000)
        cleaned_data = []

        for doc in raw_docs:
            try:
                manufacturer = SemiconManufacturer.model_validate(doc)
                cleaned_data.append(transform_mongo_doc(manufacturer))
            except Exception as e:
                logger.warning(f"Skipping invalid manufacturer document: {e}")

        return {
            "error": False,
            "message": "Manufacturers fetched successfully (some invalid documents may have been skipped)",
            "data": jsonable_encoder(cleaned_data)
        }


@router.get("/manufacturer/{manufacturer_id}/products", tags=["Products by Manufacturer"])
async def get_products_by_manufacturer(
    manufacturer_id: str,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return")
):
    """
    Get all products for a specific manufacturer
    
    Args:
        manufacturer_id: The manufacturer ID from semicon_products_details collection
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
    
    Returns:
        List of products associated with the manufacturer
    """
    try:
        # Clean and validate manufacturer_id
        manufacturer_id = str(manufacturer_id).strip()
        if not manufacturer_id:
            raise HTTPException(
                status_code=400,
                detail={"error": True, "message": "Manufacturer ID cannot be empty or just whitespace"}
            )
        
        # Check if manufacturer exists
        manufacturer_doc = await engine.find_one(
            SemiconManufacturer,
            SemiconManufacturer.semicon_manufacturer_id == str(manufacturer_id)
        )
        if not manufacturer_doc:
            raise HTTPException(
                status_code=404,
                detail={"error": True, "message": f"Manufacturer with ID '{manufacturer_id}' not found in manufacturer table"}
            )
        
        # Get all products for this manufacturer
        products = await engine.find(
            SemiconProduct,
            SemiconProduct.Manufacturer.semicon_manufacturer_id == str(manufacturer_id),
            limit=limit,
            skip=skip
        )
        
        # Transform products to response format
        response_data = [jsonable_encoder(product) for product in products]
        
        # Get total count for pagination
        total_count = await engine.count(
            SemiconProduct,
            SemiconProduct.Manufacturer.semicon_manufacturer_id == str(manufacturer_id)
        )
        
        logger.info(f"Retrieved {len(response_data)} products for manufacturer '{manufacturer_id}'")
        
        return {
            "error": False,
            "message": f"Successfully retrieved {len(response_data)} products for manufacturer '{manufacturer_id}'",
            "data": jsonable_encoder(response_data),
            "pagination": {
                "total": total_count,
                "skip": skip,
                "limit": limit
            }
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions (400, 404, etc.)
        raise
    except Exception as e:
        logger.error(f"Error retrieving products for manufacturer '{manufacturer_id}': {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": True, "message": f"Internal server error while retrieving products"}
        )


@router.get("/manufacturer/{manufacturer_id}/products/count", tags=["Products by Manufacturer"])
async def get_products_count_by_manufacturer(manufacturer_id: str):
    """
    Get count of products for a specific manufacturer
    
    Args:
        manufacturer_id: The manufacturer ID from semicon_products_details collection
    
    Returns:
        Count of products associated with the manufacturer
    """
    try:
        # Clean and validate manufacturer_id
        manufacturer_id = str(manufacturer_id).strip()
        if not manufacturer_id:
            raise HTTPException(
                status_code=400,
                detail={"error": True, "message": "Manufacturer ID cannot be empty or just whitespace"}
            )
        
        # Count products for this manufacturer
        count = await engine.count(
            SemiconProduct,
            SemiconProduct.Manufacturer.semicon_manufacturer_id == str(manufacturer_id)
        )
        
        logger.info(f"Counted {count} products for manufacturer '{manufacturer_id}'")
        
        return {
            "error": False,
            "message": f"Successfully counted products for manufacturer '{manufacturer_id}'",
            "data": {"count": count}
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions (400, 404, etc.)
        raise
    except Exception as e:
        logger.error(f"Error counting products for manufacturer '{manufacturer_id}': {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": True, "message": f"Internal server error while counting products"}
        )
@router.get("/analytics/count/manufacturers", tags=["Analytics"])
async def get_manufacturer_counts():
    """Get counts of active manufacturers with details"""
    try:
        # Access the raw MongoDB collection to bypass odmantic validation
        collection = engine.get_collection(SemiconManufacturer)
        
        # Fetch all manufacturers
        manufacturers = await collection.find({"status": True}).to_list(None)
        
        total_active_manufacturers = len(manufacturers)
        
        manufacturers_data = []
        
        for manufacturer in manufacturers:
            manufacturer_info = {
                "name": manufacturer.get("digikey_name", "Unknown"),
                "manufacturer_id": manufacturer.get("semicon_manufacturer_id", ""),
            }
            
            manufacturers_data.append(manufacturer_info)
        
        return {
            "error": False,
            "message": "Manufacturer counts retrieved successfully",
            "data": {
                "total_active_manufacturers": total_active_manufacturers,
                "manufacturers": manufacturers_data
            }
        }
        
    except Exception as e:
        logger.error(f"Error counting manufacturers: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": True,
                "message": f"Failed to count manufacturers: {str(e)}",
                "data": []
            }
        )