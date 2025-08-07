from fastapi import APIRouter, HTTPException
import httpx
from app.services.sync_semicon_products import fetch_and_sync_semicon_product

router = APIRouter()

DIGIKEY_BASE_URL = "http://172.232.110.10:8000/api/digikey"  # change to your DigiKey proxy URL

@router.post("/sync/digikey")
async def sync_digikey_product(payload: dict):
    query = payload.get("query")
    if not query:
        raise HTTPException(status_code=400, detail={"status": "failure", "message": "Query is required"})

    async with httpx.AsyncClient(timeout=30) as client:
        # 1️⃣ Search API
        search_url = f"{DIGIKEY_BASE_URL}/search/keyword"
        search_resp = await client.post(search_url, json={"query": query})
        if search_resp.status_code != 200:
            raise HTTPException(status_code=500, detail={"status": "failure", "message": "Search API failed"})
        
        search_data = search_resp.json()
        if not search_data.get("success") or not search_data.get("products"):
            raise HTTPException(status_code=404, detail={"status": "failure", "message": "Product not found in search"})

        product_basic = search_data["products"][0]
        digi_part_number = product_basic["digiKeyPartNumber"]

        # 2️⃣ Product details API
        details_url = f"{DIGIKEY_BASE_URL}/products/{digi_part_number}/productdetails"
        details_resp = await client.get(details_url)
        if details_resp.status_code != 200:
            raise HTTPException(status_code=500, detail={"status": "failure", "message": "Product details API failed"})

        details_data = details_resp.json()
        if not details_data.get("success"):
            raise HTTPException(status_code=500, detail={"status": "failure", "message": "Invalid product details response"})

    # 3️⃣ Merge data (priority to details)
    merged_data = {**product_basic, **details_data["product"]}
    print(f"Merged Data: {merged_data}")

    # 4️⃣ Store in DB
    await fetch_and_sync_semicon_product(merged_data)

    return {"status": "success", "message": f"Product {query} synced successfully"}
