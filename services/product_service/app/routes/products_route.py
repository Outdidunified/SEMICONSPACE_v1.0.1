from fastapi import APIRouter, HTTPException, Query, Request, Path
from typing import Optional, List
import httpx
import uuid
from app.services.sync_semicon_products import fetch_and_sync_semicon_product
from app.database import engine
from app.models.semicon_products import SemiconProduct
from app.models.semicon_products_details import SemiconProduct as SemiconProductDetails
from odmantic.query import QueryExpression
from uuid import UUID
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional
from bson import ObjectId
from app.kafka.kafka_producer import send_event
router = APIRouter(prefix="/product")

DIGIKEY_BASE_URL = "http://172.232.110.10:8000/api/digikey"  # change to your DigiKey proxy URL

# ======= EXISTING ENDPOINTS =======
@router.post("/sync/digikey")
async def sync_digikey_product(payload: dict):
    query = payload.get("query")
    if not query:
        raise HTTPException(status_code=400, detail={"status": "failure", "message": "Query is required"})

    async with httpx.AsyncClient(timeout=30) as client:
        # Search API
        search_url = f"{DIGIKEY_BASE_URL}/search/keyword"
        search_resp = await client.post(search_url, json={"query": query})
        if search_resp.status_code != 200:
            raise HTTPException(status_code=500, detail={"status": "failure", "message": "Search API failed"})

        search_data = search_resp.json()
        if not search_data.get("success") or not search_data.get("products"):
            raise HTTPException(status_code=404, detail={"status": "failure", "message": "Product not found in search"})

        product_basic = search_data["products"][0]
        digi_part_number = product_basic["digiKeyPartNumber"]

        # Check if product already exists in DB
        existing = await engine.find_one(SemiconProduct, SemiconProduct.semicon_part_number == f"SPNID-{product_basic.get('manufacturerPartNumber', '')}")
        if existing:
            return {"status": "success", "message": f"Product {query} already synced"}

        # Product details API
        details_url = f"{DIGIKEY_BASE_URL}/products/{digi_part_number}/productdetails"
        details_resp = await client.get(details_url)
        if details_resp.status_code != 200:
            raise HTTPException(status_code=500, detail={"status": "failure", "message": "Product details API failed"})

        details_data = details_resp.json()
        if not details_data.get("success"):
            raise HTTPException(status_code=500, detail={"status": "failure", "message": "Invalid product details response"})

    merged_data = {**product_basic, **details_data["product"]}
    print(f"Merged Data: {merged_data}")
    await fetch_and_sync_semicon_product(merged_data)

    return {"status": "success", "message": f"Product {query} synced successfully"}


@router.get("/fetchall")
async def get_all_products(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    search: Optional[str] = Query(None, description="Search term for product name or part number"),
    manufacturer: Optional[str] = Query(None, description="Filter by manufacturer name"),
    category: Optional[str] = Query(None, description="Filter by category name")
):
    try:
        # Log the query parameters
        print(f"Fetching products with skip={skip}, limit={limit}, search={search}, manufacturer={manufacturer}, category={category}")

        # Build query
        query = QueryExpression()
        if search:
            query &= (
                SemiconProduct.name.contains(search, case_sensitive=False) |
                SemiconProduct.semicon_part_number.contains(search, case_sensitive=False) |
                SemiconProduct.manufacturer_part_number.contains(search, case_sensitive=False)
            )
        if manufacturer:
            query &= SemiconProduct.vendor_details.contains(manufacturer)
        if category:
            query &= SemiconProduct.semicon_category_id == category

        # Try fetching with odmantic
        products = await engine.find(SemiconProduct, query, skip=skip, limit=limit)
        print(f"Found {len(products)} products using odmantic query")

        # If no products found, try raw collection to diagnose
        if not products:
            collection = engine.get_collection(SemiconProduct)
            raw_query = {}
            if search:
                raw_query["$or"] = [
                    {"name": {"$regex": search, "$options": "i"}},
                    {"semicon_part_number": {"$regex": search, "$options": "i"}},
                    {"manufacturer_part_number": {"$regex": search, "$options": "i"}}
                ]
            if manufacturer:
                raw_query["vendor_details"] = {"$regex": manufacturer, "$options": "i"}
            if category:
                raw_query["semicon_category_id"] = category

            raw_products = await collection.find(raw_query).skip(skip).limit(limit).to_list(None)
            print(f"Found {len(raw_products)} products using raw collection query")
            if raw_products:
                print("Products found in raw query but not in odmantic query, possible validation issue")
                # Transform raw documents to match SemiconProduct structure
                transformed_products = [{
                    "id": str(doc["_id"]),
                    "name": doc.get("name"),
                    "description": doc.get("description"),
                    "image_url": doc.get("image_url"),
                    "datasheet_url": doc.get("datasheet_url"),
                    "quantity_available": doc.get("quantity_available"),
                    "unit_price": doc.get("UnitPrice"),
                    "currency": doc.get("currency"),
                    "manufacturerPartNumber": doc.get("manufacturerPartNumber"),
                    "vendor_details": doc.get("vendor_details", []),
                    "manufacturer_name": doc.get("manufacturer_name"),
                    "semicon_part_number": doc.get("semicon_part_number"),
                    "semicon_category_id": doc.get("semicon_category_id"),
                    "semicon_child_category_id": doc.get("semicon_child_category_id"),
                    "created_by": doc.get("created_by"),
                    "created_date": doc.get("created_date"),
                    "modified_by": doc.get("modified_by"),
                    "modified_date": doc.get("modified_date"),
                    "status": doc.get("status")
                } for doc in raw_products]
                return transformed_products

        return {
            "error": False,
            "message": f"products fetched successfully",
            "data": products,
        }

    except Exception as e:
        print(f"Error fetching products: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching products: {str(e)}")
    


@router.get("/{product_id}/productdetails")
async def get_product_by_id(product_id: str):
    try:
        # Check if product_id is a UUID or semicon_part_number
        product = None
        try:
            product_uuid = UUID(product_id)
            product = await engine.find_one(SemiconProduct, SemiconProduct.id == product_uuid)
        except ValueError:
            product = await engine.find_one(SemiconProduct, SemiconProduct.semicon_part_number == product_id)

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Get product details using the existing engine
        collection = engine.get_collection(SemiconProduct)
        
        # Aggregation pipeline adapted from renderProductFrame
        aggregation_pipeline = [
    {"$match": {"semicon_part_number": product.semicon_part_number}},

    # Lookup product details
    {
        "$lookup": {
            "from": "semicon_product_details",
            "localField": "semicon_part_number",
            "foreignField": "semicon_part_number",
            "as": "product_details"
        }
    },

    # Lookup vendor products matching vendor_details
    {
        "$lookup": {
            "from": "vendor_products",
            "let": {"vendor_ids": "$vendor_details"},
            "pipeline": [
                {"$match": {"$expr": {"$in": ["$vendor_product_number", "$$vendor_ids"]}}}
            ],
            "as": "vendor_products"
        }
    },

    # For each vendor product, lookup full product variants documents
    {
        "$unwind": {
            "path": "$vendor_products",
            "preserveNullAndEmptyArrays": True
        }
    },

    {
        "$lookup": {
            "from": "product_variants",
            "localField": "vendor_products.product_variants",
            "foreignField": "semicon_product_variant_id",
            "as": "vendor_products.full_variants"
        }
    },

    # For each variant, lookup pricing and parameters
    {
        "$unwind": {
            "path": "$vendor_products.full_variants",
            "preserveNullAndEmptyArrays": True
        }
    },

    {
        "$lookup": {
            "from": "variant_pricing",
            "localField": "vendor_products.full_variants.semicon_product_variant_pricing_id",
            "foreignField": "semicon_product_variant_pricing_id",
            "as": "vendor_products.full_variants.pricing_details"
        }
    },

    {
        "$lookup": {
            "from": "vendors_product_variant_parameters",
            "localField": "vendor_products.full_variants.semicon_product_variant_id",
            "foreignField": "semicon_parameter_id",
            "as": "vendor_products.full_variants.parameters"
        }
    },

    # Merge pricing details as single object (first element)
    {
        "$addFields": {
            "vendor_products.full_variants.pricing_details": {
                "$arrayElemAt": ["$vendor_products.full_variants.pricing_details", 0]
            }
        }
    },

    # Group back variants into array under each vendor_product
    {
        "$group": {
            "_id": {
                "product_id": "$_id",
                "vendor_product_id": "$vendor_products._id"
            },
            "vendor_product": {"$first": "$vendor_products"},
            "variants": {"$push": "$vendor_products.full_variants"},
            "product_root": {"$first": "$$ROOT"}
        }
    },

    {
        "$addFields": {
            "vendor_product.product_variants": "$variants"
        }
    },

    # Group back vendor_products into array under the product
    {
        "$group": {
            "_id": "$_id.product_id",
            "vendor_products": {"$push": "$vendor_product"},
            "product_root": {"$first": "$product_root"}
        }
    },

    # Replace root document, but with vendor_products replaced with fully populated ones
    {
        "$replaceRoot": {
            "newRoot": {
                "$mergeObjects": [
                    "$product_root",
                    {"vendor_products": "$vendor_products"}
                ]
            }
        }
    },

    # Final grouping and projection (your original)
    {
        "$group": {
            "_id": "$_id",
            "semicon_part_number": {"$first": "$semicon_part_number"},
            "name": {"$first": "$name"},
            "description": {"$first": "$description"},
            "image_url": {"$first": "$image_url"},
            "datasheet_url": {"$first": "$datasheet_url"},
            "quantity_available": {"$first": "$quantity_available"},
            "unit_price": {"$first": "$unit_price"},
            "currency": {"$first": "$currency"},
            "status": {"$first": "$status"},
            "created_by": {"$first": "$created_by"},
            "created_date": {"$first": "$created_date"},
            "modified_by": {"$first": "$modified_by"},
            "modified_date": {"$first": "$modified_date"},
            "product_details": {"$first": "$product_details"},
            "vendor_products": {"$first": "$vendor_products"}
        }
    },

    {
        "$project": {
            "semicon_part_number": 1,
            "name": 1,
            "image_url": 1,
            "datasheet_url": 1,
            "quantity_available": 1,
            "unit_price": 1,
            "currency": 1,
            "status": 1,
            "created_by": 1,
            "created_date": 1,
            "modified_by": 1,
            "modified_date": 1,
            "Category": {"$ifNull": [{"$arrayElemAt": ["$product_details.Category", 0]}, None]},
            "Description": {
                "ProductDescription": "$description",
                "DetailedDescription": {"$ifNull": [{"$arrayElemAt": ["$product_details.DetailedDescription", 0]}, None]}
            },
            "Manufacturer": {
                "Name": {"$ifNull": [{"$arrayElemAt": ["$product_details.Manufacturer.Name", 0]}, None]},
                "PartNumber": {"$ifNull": [{"$arrayElemAt": ["$product_details.manufacturerPartNumber", 0]}, None]}
            },
            "ProductDetails": {
                "UnitPrice": {"$ifNull": [{"$arrayElemAt": ["$product_details.UnitPrice", 0]}, None]},
                "ProductUrl": {"$ifNull": [{"$arrayElemAt": ["$product_details.ProductUrl", 0]}, None]},
                "BackOrderNotAllowed": {"$ifNull": [{"$arrayElemAt": ["$product_details.BackOrderNotAllowed", 0]}, None]},
                "NormallyStocking": {"$ifNull": [{"$arrayElemAt": ["$product_details.NormallyStocking", 0]}, None]},
                "Discontinued": {"$ifNull": [{"$arrayElemAt": ["$product_details.Discontinued", 0]}, None]},
                "EndOfLife": {"$ifNull": [{"$arrayElemAt": ["$product_details.EndOfLife", 0]}, None]},
                "Ncnr": {"$ifNull": [{"$arrayElemAt": ["$product_details.Ncnr", 0]}, None]},
                "ManufacturerLeadWeeks": {"$ifNull": [{"$arrayElemAt": ["$product_details.ManufacturerLeadWeeks", 0]}, None]},
                "Series": {"$ifNull": [{"$arrayElemAt": ["$product_details.Series", 0]}, None]},
                "Classifications": {"$ifNull": [{"$arrayElemAt": ["$product_details.Classifications", 0]}, None]},
                "OtherNames": {"$ifNull": [{"$arrayElemAt": ["$product_details.OtherNames", 0]}, []]},
                "ProductStatus": {"$ifNull": [{"$arrayElemAt": ["$product_details.ProductStatus", 0]}, None]}
            },
            "VendorProducts": 1
        }
    },

    {"$limit": 1}
]


        # Execute the aggregation using existing engine
        product_details = await collection.aggregate(aggregation_pipeline).to_list(length=1)
        
        if not product_details:
            return {
                "error": False,
                "message": "Product retrieved successfully",
                "data": {
                    "basic_info": {
                        "id": str(product.id),
                        "semicon_part_number": product.semicon_part_number,
                        "vendor_details": product.vendor_details,
                        "semicon_category_id": product.semicon_category_id,
                        "semicon_child_category_id": product.semicon_child_category_id,
                        "created_by": product.created_by,
                        "created_date": product.created_date,
                        "modified_by": product.modified_by,
                        "modified_date": product.modified_date,
                        "status": product.status
                    },
                    "detailed_info": {
                        "Category": None,
                        "Description": {
                            "ProductDescription": product.description,
                            "DetailedDescription": None
                        },
                        "Manufacturer": {
                            "Name": product.manufacturer_name,
                            "PartNumber": product.manufacturerPartNumber
                        },
                        "ProductDetails": None,
                        "VendorProducts": [],
                        "ProductVariants": []
                    }
                }
            }

        # Format response
        details = product_details[0]

# Get existing vendor_products, default empty list
        vendor_products = details.get("vendor_products", [])

        # Flatten product_variants across vendor_products; default empty if none
        product_variants = [variant for vp in vendor_products for variant in vp.get("product_variants") or []]

        # Prepare detailed_info preserving all existing keys and values
        print(f"Detailed Info: {vendor_products, product_variants}")
        return {
            "error": False,
            "message": "Product retrieved successfully",
            "data": {
                "basic_info": {
                    "id": str(product.id),
                    "semicon_part_number": product.semicon_part_number,
                    "vendor_details": product.vendor_details,
                    "semicon_category_id": product.semicon_category_id,
                    "semicon_child_category_id": product.semicon_child_category_id,
                    "created_by": product.created_by,
                    "created_date": product.created_date,
                    "modified_by": product.modified_by,
                    "modified_date": product.modified_date,
                    "status": product.status
                },
                "detailed_info": {
                    "Category": details.get("Category"),
                    "Description": details.get("Description"),
                    "Manufacturer": details.get("Manufacturer"),
                    "ProductDetails": {
                        "UnitPrice": details["ProductDetails"]["UnitPrice"],
                        "ProductUrl": details["ProductDetails"]["ProductUrl"],
                        "BackOrderNotAllowed": details["ProductDetails"]["BackOrderNotAllowed"],
                        "NormallyStocking": details["ProductDetails"]["NormallyStocking"],
                        "Discontinued": details["ProductDetails"]["Discontinued"],
                        "EndOfLife": details["ProductDetails"]["EndOfLife"],
                        "Ncnr": details["ProductDetails"]["Ncnr"],
                        "ManufacturerLeadWeeks": details["ProductDetails"]["ManufacturerLeadWeeks"],
                        "Series": details["ProductDetails"]["Series"],
                        "Classifications": details["ProductDetails"]["Classifications"],
                        "OtherNames": details["ProductDetails"]["OtherNames"] or [],
                        "ProductStatus": details["ProductDetails"]["ProductStatus"]
                    },
                     "VendorProducts": details.get("VendorProducts", []),
                         "ProductVariants": details.get("ProductVariants", [])
                }
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching product: {str(e)}")
@router.get("/search/advanced")
async def search_products(
    q: Optional[str] = Query(None, description="General search term"),
    manufacturer: Optional[str] = Query(None, description="Manufacturer name"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    category: Optional[str] = Query(None, description="Category ID"),
    in_stock: Optional[bool] = Query(None, description="Filter by stock availability"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200)
):
    try:
        query = QueryExpression()

        if q:
            query &= (
                SemiconProduct.name.contains(q, case_sensitive=False) |
                SemiconProduct.semicon_part_number.contains(q, case_sensitive=False) |
                SemiconProduct.manufacturer_part_number.contains(q, case_sensitive=False) |
                SemiconProduct.description.contains(q, case_sensitive=False)
            )

        if manufacturer:
            query &= SemiconProduct.vendor_details.contains(manufacturer)

        if category:
            query &= SemiconProduct.semicon_category_id == category

        if min_price is not None:
            query &= SemiconProduct.unit_price >= min_price

        if max_price is not None:
            query &= SemiconProduct.unit_price <= max_price

        if in_stock is not None:
            if in_stock:
                query &= SemiconProduct.quantity_available > 0
            else:
                query &= (SemiconProduct.quantity_available == 0) | (SemiconProduct.quantity_available == None)

        products = await engine.find(SemiconProduct, query, skip=skip, limit=limit)
        total_count = await engine.count(SemiconProduct, query)

        return {
            "products": products,
            "total": total_count,
            "skip": skip,
            "limit": limit,
            "message": f"Found {len(products)} products"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching products: {str(e)}")


@router.get("/count/total")
async def get_total_products():
    try:
        count = await engine.count(SemiconProduct)
        return {"total_products": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error counting products: {str(e)}")


@router.get("/quantity/check/{product_id}/{quantity}")
async def check_product_availability(product_id: str, quantity: int = Path(..., ge=1, description="Quantity to check availability for")):
    """
    Check if a product exists and has sufficient quantity available.
    
    Args:
        product_id: The product ID (UUID) or semicon_part_number
        quantity: The requested quantity to check
        
    Returns:
        Product details if available, or error message if not found/insufficient quantity
    """
    try:
        # Validate quantity
        if quantity <= 0:
            raise HTTPException(
                status_code=400, 
                detail={"error": True, "message": "Quantity must be greater than 0"}
            )
        
        # Find product by ID or semicon_part_number
        product = None
        
        # Try as UUID first
        try:
            product_uuid = UUID(product_id)
            product = await engine.find_one(SemiconProduct, SemiconProduct.id == product_uuid)
        except ValueError:
            # If not UUID, try as semicon_part_number
            product = await engine.find_one(SemiconProduct, SemiconProduct.semicon_part_number == product_id)
        
        # Check if product exists
        if not product:
            raise HTTPException(
                status_code=404, 
                detail={
                    "error": True, 
                    "message": "Product not found",
                    "product_id": product_id
                }
            )
        
        # Check if product has quantity information
        if product.quantity_available is None:
            raise HTTPException(
                status_code=400, 
                detail={
                    "error": True, 
                    "message": "Product quantity information not available",
                    "product_id": product_id
                }
            )
        
        # Check if sufficient quantity is available
        if product.quantity_available < quantity:
            raise HTTPException(
                status_code=400, 
                detail={
                    "error": True, 
                    "message": f"Insufficient quantity available. Requested: {quantity}, Available: {product.quantity_available}",
                    "product_id": product_id,
                    "requested_quantity": quantity,
                    "available_quantity": product.quantity_available
                }
            )
        
        # Return product details if available
        return {
            "error": False,
            "message": "Product available",
            "data": {
                "product": {
                    "id": str(product.id),
                    "name": product.name,
                    "semicon_part_number": product.semicon_part_number,
                    "manufacturer_part_number": product.manufacturerPartNumber,
                    "manufacturer_name": product.manufacturer_name,
                    "quantity_available": product.quantity_available,
                    "unit_price": product.UnitPrice,
                    "currency": product.currency,
                    "description": product.description,
                    "image_url": product.image_url,
                    "datasheet_url": product.datasheet_url,
                    "vendor_details": product.vendor_details,
                    "status": product.status
                },
                "requested_quantity": quantity,
                "availability_status": "available"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail={
                "error": True, 
                "message": f"Error checking product availability: {str(e)}",
                "product_id": product_id
            }
        )




