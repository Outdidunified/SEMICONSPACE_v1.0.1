from fastapi import APIRouter, HTTPException, Query, Request, Path
from typing import Optional, List
import httpx
import re
import uuid
from urllib.parse import quote
from odmantic import query
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
import asyncio
router = APIRouter(prefix="/product")

DIGIKEY_BASE_URL = "http://172.232.110.10:8000/api/digikey"  # change to your DigiKey proxy URL

# ======= EXISTING ENDPOINTS =======@router.post("/sync/digikey")
@router.post("/sync/digikey")
async def sync_digikey_product(payload: dict):
    query = payload.get("query")
    if not query:
        raise HTTPException(status_code=400, detail={"status": "failure", "message": "Query is required"})

    async with httpx.AsyncClient(timeout=180) as client:
        search_url = f"{DIGIKEY_BASE_URL}/search/keyword"
        search_resp = await client.post(search_url, json={"query": query})
        if search_resp.status_code != 200:
            raise HTTPException(status_code=500, detail={"status": "failure", "message": "Search API failed"})

        search_data = search_resp.json()
        if not search_data.get("success") or not search_data.get("products"):
            raise HTTPException(status_code=404, detail={"status": "failure", "message": "No products found in search"})

        synced = 0
        skipped = 0
        result_main = []

        for product_basic in search_data["products"]:
            digi_part_number = product_basic["digiKeyPartNumber"]
            manufacturer_part_number = product_basic.get("manufacturerPartNumber", "")
            semicon_part_number = f"SPNID-{manufacturer_part_number}"

            # Check if product already exists
            existing = await engine.find_one(SemiconProduct, SemiconProduct.semicon_part_number == semicon_part_number)
            if existing:
                skipped += 1
                continue

            # Fetch product details
            details_url = f"{DIGIKEY_BASE_URL}/products/{digi_part_number}/productdetails"
            details_resp = await client.get(details_url)
            if details_resp.status_code != 200:
                # Could log this or raise; here we just skip
                skipped += 1
                continue

            details_data = details_resp.json()
            if not details_data.get("success"):
                skipped += 1
                continue

            merged_data = {**product_basic, **details_data["product"]}
            result= await fetch_and_sync_semicon_product(merged_data)
            synced += 1
            result_main.append(result)
           # print(f"Synced product: {merged_data}")
    return {
        "status": "success",
        "message": f"Sync completed: {synced} products synced, {skipped} products skipped (already exists or failed).",
        "returned_data": result_main
    }



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
        # Try to find product by UUID or semicon_part_number
        product = None
        try:
            product_uuid = UUID(product_id)
            product = await engine.find_one(SemiconProduct, SemiconProduct.id == product_uuid)
        except ValueError:
            product = await engine.find_one(SemiconProduct, SemiconProduct.semicon_part_number == product_id)

        if not product:
            print(f"Prodppppppp found for product_id: {product_id}")
            raise HTTPException(status_code=404, detail="Product not found")

        collection = engine.get_collection(SemiconProduct)

        # Use direct queries to build product details (Atlas-compatible approach)
        print(f"🔍 Building product details for: {product.semicon_part_number}")
        
        db = collection.database
        
        # Step 1: Get product details from semicon_product_details collection
        product_details_doc = await db.semicon_product_details.find_one({
            "semicon_part_number": product.semicon_part_number
        })
        
        # Step 2: Get vendor products
        vendor_products = await db.vendor_products.find({
            "semicon_part_number": product.semicon_part_number
        }).to_list(length=None)
        
        print(f"📦 Found {len(vendor_products)} vendor products")
        
        # Step 3: Get product variants
        product_variants = []
        if vendor_products:
            # Collect all variant IDs from vendor products
            all_variant_ids = []
            for vp in vendor_products:
                variant_ids = vp.get('product_variants', [])
                all_variant_ids.extend(variant_ids)
            
            print(f"🔍 Looking for {len(all_variant_ids)} product variants: {all_variant_ids}")
            
            if all_variant_ids:
                # Get product variants
                variants = await db.product_variants.find({
                    "semicon_product_variant_id": {"$in": all_variant_ids}
                }).to_list(length=None)
                
                print(f"✅ Found {len(variants)} product variants")
                
                # Step 4: Get pricing details for each variant
                for variant in variants:
                    pricing_ids = variant.get('semicon_product_variant_pricing_id', [])
                    if pricing_ids:
                        pricing_docs = await db.variant_pricing.find({
                            "semicon_product_variant_pricing_id": {"$in": pricing_ids}
                        }).to_list(length=None)
                        
                        # Add pricing details to variant
                        variant['pricing_details'] = pricing_docs[0] if pricing_docs else None
                
                product_variants = variants
        
        # Step 5: Construct the final result structure (matching JavaScript output)
        result_doc = {
            "_id": product.id,
            "semicon_part_number": product.semicon_part_number,
            "name": product.name,
            "description": product.description,
            "image_url": product.image_url,
            "datasheet_url": product.datasheet_url,
            "quantity_available": product.quantity_available,
            "UnitPrice": product.UnitPrice,
            "currency": product.currency,
            "status": product.status,
            "manufacturerPartNumber": product.manufacturerPartNumber,
            "manufacturer_name": product.manufacturer_name,
            "created_by": product.created_by,
            "created_date": product.created_date,
            "modified_by": product.modified_by,
            "modified_date": product.modified_date,
            
            # Add structured data from lookups
            "Category": product_details_doc.get("Category") if product_details_doc else None,
            "Description": {
                "ProductDescription": product.description,
                "DetailedDescription": product_details_doc.get("DetailedDescription") if product_details_doc else None
            },
            "Manufacturer": {
                "Name": product.manufacturer_name,
                "PartNumber": product.manufacturerPartNumber
            },
            "ProductDetails": {
                "UnitPrice": product_details_doc.get("UnitPrice") if product_details_doc else product.UnitPrice,
                "ProductUrl": product_details_doc.get("ProductUrl") if product_details_doc else None,
                "BackOrderNotAllowed": product_details_doc.get("BackOrderNotAllowed") if product_details_doc else None,
                "NormallyStocking": product_details_doc.get("NormallyStocking") if product_details_doc else None,
                "Discontinued": product_details_doc.get("Discontinued") if product_details_doc else None,
                "EndOfLife": product_details_doc.get("EndOfLife") if product_details_doc else None,
                "Ncnr": product_details_doc.get("Ncnr") if product_details_doc else None,
                "ManufacturerLeadWeeks": product_details_doc.get("ManufacturerLeadWeeks") if product_details_doc else None,
                "Series": product_details_doc.get("Series") if product_details_doc else None,
                "Classifications": product_details_doc.get("Classifications") if product_details_doc else None,
                "OtherNames": product_details_doc.get("OtherNames", []) if product_details_doc else [],
                "ProductStatus": product_details_doc.get("ProductStatus") if product_details_doc else None
            },
            "VendorProducts": vendor_products,
            "ProductVariants": product_variants
        }
        
        product_details = [result_doc]
        print(f"✅ Product details built successfully - VendorProducts: {len(vendor_products)}, ProductVariants: {len(product_variants)}")

        if not product_details:
            print(f"No detailed data found for semicon_part_number: {product.semicon_part_number}")
            return {
                "error": False,
                "message": "Product retrieved successfully",
                "data": {
                    "id": str(product.id),
                    "name": product.name,
                    "semicon_part_number": product.semicon_part_number,
                    "vendor_details": getattr(product, "vendor_details", []),
                    "semicon_category_id": getattr(product, "semicon_category_id", None),
                    "semicon_child_category_id": getattr(product, "semicon_child_category_id", None),
                    "created_by": product.created_by,
                    "created_date": product.created_date,
                    "modified_by": product.modified_by,
                    "modified_date": product.modified_date,
                    "status": product.status,
                    "detailed_info": {
                        "Category": None,
                        "Description": {
                            "ProductDescription": product.description,
                            "DetailedDescription": None
                        },
                        "Manufacturer": {
                            "Name": getattr(product, "manufacturer_name", None),
                            "PartNumber": getattr(product, "manufacturerPartNumber", None)
                        },
                        "ProductDetails": {
                            "UnitPrice": None,
                            "ProductUrl": None,
                            "BackOrderNotAllowed": None,
                            "NormallyStocking": None,
                            "Discontinued": None,
                            "EndOfLife": None,
                            "Ncnr": None,
                            "ManufacturerLeadWeeks": None,
                            "Series": None,
                            "Classifications": None,
                            "OtherNames": [],
                            "ProductStatus": None
                        },
                        "VendorProducts": [],
                        "ProductVariants": []
                    }
                }
            }

        details = product_details[0]
        
        # Handle empty vendor products and product variants
        vendor_products = details.get("VendorProducts", [])
        product_variants = details.get("ProductVariants", [])
        
        # Filter out null values from the sets
        vendor_products = [vp for vp in vendor_products if vp is not None]
        product_variants = [pv for pv in product_variants if pv is not None]
        
        print(f"🔧 Final counts - VendorProducts: {len(vendor_products)}, ProductVariants: {len(product_variants)}")

        return {
            "error": False,
            "message": "Product retrieved successfully",
            "data": {
                "id": str(product.id),
                "name": details.get("name"),
                "semicon_part_number": details.get("semicon_part_number"),
                "vendor_details": getattr(product, "vendor_details", []),
                "semicon_category_id": getattr(product, "semicon_category_id", None),
                "semicon_child_category_id": getattr(product, "semicon_child_category_id", None),
                "created_by": details.get("created_by"),
                "created_date": details.get("created_date"),
                "modified_by": details.get("modified_by"),
                "modified_date": details.get("modified_date"),
                "status": details.get("status"),
                "detailed_info": {
                    "Category": details.get("Category"),
                    "Description": details.get("Description"),
                    "Manufacturer": details.get("Manufacturer"),
                    "ProductDetails": details.get("ProductDetails"),
                    "VendorProducts": vendor_products,
                    "ProductVariants": product_variants
                }
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching product {product_id}: {str(e)}")
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
@router.get("/analytics/count/totalproducts")
async def get_total_products():
    try:
        count = await engine.count(SemiconProduct)
        return {
            "error": False,
            "message": "Total products count retrieved successfully",
            "total_products": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error counting products: {str(e)}")
# Fetch details for one product with URL-encoding
async def fetch_details(part_number: str, client: httpx.AsyncClient):
    encoded_part_number = quote(part_number)
    details_url = f"http://172.232.110.10:8003/product/{encoded_part_number}/productdetails"
    try:
        resp = await client.get(details_url, timeout=httpx.Timeout(180.0, connect=5.0))  # 10s total timeout, 5s connect
        resp.raise_for_status()
        data = resp.json()
      #  print(f"Fetched details for {part_number}: {data}")  # Log actual data returned
        return data
    except httpx.TimeoutException as e:
        print(f"[WARN] Timeout fetching details for {part_number}: {e}")
        return {"semicon_part_number": part_number, "error": "Timeout"}
    except Exception as e:
        print(f"[WARN] Failed to fetch details for {part_number}: {repr(e)}")
        return {"semicon_part_number": part_number, "error": str(e)}

async def safe_fetch_details(part_number: str, client: httpx.AsyncClient):
    try:
        data = await fetch_details(part_number, client)
        if not data:
            print(f"[WARN] Empty data returned for {part_number}")
        return data
    except Exception as e:
        print(f"[WARN] Failed to fetch details for {part_number}: {repr(e)}")
        return {"semicon_part_number": part_number, "error": str(e)}
@router.get("/search/{query}")
async def search_and_get_details(query: str):
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=5.0)) as client:
            # 1. Search in Mongo
            search_query = {
                "$or": [
                    {"name": {"$regex": query, "$options": "i"}},
                    {"Manufacturer.Name": {"$regex": query, "$options": "i"}},
                    {"Category.ChildCategories.Name": {"$regex": query, "$options": "i"}},
                    {"Category.Name": {"$regex": query, "$options": "i"}},
                    {"manufacturer_part_number": {"$regex": query, "$options": "i"}},
                ]
            }

            collection = engine.get_collection(SemiconProductDetails)
            mongo_matches = await collection.find(search_query).to_list(length=None)

            mongo_part_numbers = {
                doc.get("semicon_part_number")
                for doc in mongo_matches if doc.get("semicon_part_number")
            }

            # 2. Get details for Mongo matches
            mongo_details = await asyncio.gather(
                *(safe_fetch_details(pn, client) for pn in mongo_part_numbers),
                return_exceptions=False
            )

            # 3. DigiKey sync
            digi_url = "http://172.232.110.10:8003/product/sync/digikey"
            digi_products = []

            digi_resp = await client.post(digi_url, json={"query": query})

            if digi_resp.status_code == 404:
                print(f"[INFO] DigiKey: No products found for query '{query}'")
            elif digi_resp.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"DigiKey sync failed ({digi_resp.status_code}): {digi_resp.text}"
                )
            else:
                try:
                    digi_data = digi_resp.json()
                except ValueError:
                    raise HTTPException(
                        status_code=502,
                        detail=f"DigiKey returned non-JSON: {digi_resp.text[:200]}"
                    )

                products = digi_data.get("products", [])
                if isinstance(products, list):
                    digi_products = products
                else:
                    print("[WARN] DigiKey returned invalid product list")

            digi_part_numbers = {
                p.get("semicon_part_number")
                for p in digi_products if p.get("semicon_part_number")
            }

            # 4. Only fetch DigiKey products that aren't in Mongo
            new_part_numbers = digi_part_numbers - mongo_part_numbers

            # 5. Get details for DigiKey products
            digi_details = await asyncio.gather(
                *(safe_fetch_details(pn, client) for pn in new_part_numbers),
                return_exceptions=False
            )

            # 6. Merge results
            all_results = mongo_details + digi_details
            all_results = [r for r in all_results if r]  # remove None

            if not all_results:
                raise HTTPException(status_code=404, detail="No products found")

            return {
                "message": "Products retrieved successfully",
                "count": len(all_results),
                "data": all_results
            }

    except httpx.ConnectError as e:
        raise HTTPException(status_code=502, detail=f"Connection failed: {str(e)}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Request error: {str(e)}")
