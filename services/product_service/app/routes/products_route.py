from fastapi import APIRouter, Depends, HTTPException, Path
from typing import List
from datetime import datetime, timezone
import logging

from app.schemas.products_schema import (
    ProductSchema,
    ProductUpdateWithIDSchema,
    ProductResponseSchema,
    ProductIDRequest
)
from app.models.products_models import Product
from app.models.categories_models import Category
from app.models.manufacturers_models import Manufacturer
from app.models.pricing_models import ProductPricing
from app.database import engine
from app.kafka.kafka_producer import send_event
from app.auth_utils import get_current_user
from typing import Optional, Union
from app.models.specifications_models import ProductSpecification

router = APIRouter(tags=["Products"])
logger = logging.getLogger(__name__)
from typing import Union, Optional
def success_response1(data: Union[dict, list], message: Optional[str] = None):
    response = {
        "status": "success",
        "data": data
    }
    if message:
        response["message"] = message
    return response
def success_response2(data: Union[dict, list], message: Optional[str] = None):
    response = {
        "error" : "false",
        "data": data
    }
    if message:
        response["message"] = message
    return response

@router.get("/list")
async def list_products():
    products = await engine.find(Product)
    result = []
    if not products:
        logger.warning(f"❌ Products not found")
        raise HTTPException(status_code=404, detail="Product not found")
    
    for product in products:
        pricing = await engine.find_one(
            ProductPricing,
            (ProductPricing.product_id == product.product_id) & (ProductPricing.status == True),
        )

        specifications = await engine.find(
            ProductSpecification,
            ProductSpecification.product_id == product.product_id
        )

        result.append({
            "product": product,
            "pricing": pricing,
            "specifications": specifications
        })

    logger.info(f"✅ Listed {len(products)} products with pricing and specifications")
    return success_response1(result)


@router.get("/{product_id}")
async def get_product(product_id: int = Path(...)):
    product = await engine.find_one(Product, Product.product_id == product_id)
    if not product:
        logger.warning(f"❌ Product with ID {product_id} not found")
        raise HTTPException(status_code=404, detail="Product not found")

    if product.quantity <= 0:
        logger.warning(f"⚠️ Product {product_id} is out of stock (quantity={product.quantity})")
        raise HTTPException(status_code=400, detail="Product is out of stock")

    pricing = await engine.find_one(
        ProductPricing,
        (ProductPricing.product_id == product_id) & (ProductPricing.status == True),
    )

    return success_response1({"product": product, "pricing": pricing})


@router.get("/{product_id}/{quantity}")
async def get_product_with_quantity(
    product_id: int = Path(..., description="Product ID"),
    quantity: int = Path(..., description="Requested quantity"),
):
    product = await engine.find_one(Product, Product.product_id == product_id)
    if not product:
        logger.warning(f"❌ Product with ID {product_id} not found")
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

    if product.quantity <= 0:
        logger.warning(f"⚠️ Product {product_id} is out of stock (quantity={product.quantity})")
        raise HTTPException(status_code=400, detail="Product is out of stock")

    if quantity > product.quantity:
        logger.warning(f"⚠️ Requested quantity ({quantity}) exceeds stock ({product.quantity})")
        raise HTTPException(status_code=400, detail=f"Only {product.quantity} items available")

    pricing = await engine.find_one(
        ProductPricing,
        (ProductPricing.product_id == product_id) & (ProductPricing.status == True),
    )

    if not pricing:
        logger.warning(f"❌ No pricing found for product {product_id}")
        raise HTTPException(status_code=404, detail="Product pricing not found")

    logger.info(f"✅ Returning product {product_id} with quantity {quantity} and price {pricing.price}")
    return success_response1({"product": product, "price": pricing.price})


@router.post("/add")
async def create_product(
    product: ProductSchema, current_user: str = Depends(get_current_user)
):
    now = datetime.now(timezone.utc)

    if product.quantity < 0:
        logger.warning(f"❌ Attempted to create product with negative quantity: {product.quantity}")
        raise HTTPException(status_code=400, detail="Quantity cannot be negative")

    category = await engine.find_one(Category, Category.category_id == product.category_id)
    if not category:
        category = Category(
            category_id=product.category_id,
            category_name=product.category,
            created_by=current_user,
            modified_by=current_user,
            created_date=now,
            modified_date=now,
            status=True,
        )
        await engine.save(category)

    manufacturer = await engine.find_one(Manufacturer, Manufacturer.manufacturer_id == product.manufacturer_id)
    if not manufacturer:
        manufacturer = Manufacturer(
            manufacturer_id=product.manufacturer_id,
            name=product.supplier,
            created_by=current_user,
            modified_by=current_user,
            created_date=now,
            modified_date=now,
            status=True,
        )
        await engine.save(manufacturer)

    db_product = Product(
        **product.model_dump(exclude={"last_fetched_at"}),
        created_by=current_user,
        modified_by=current_user,
        created_date=now,
        modified_date=now,
        last_fetched_at=now,
        status=True,
    )
    await engine.save(db_product)

    await send_event("product.created", {
        "action": "product_added",
        "product": db_product.model_dump(),
        "created_by": current_user,
    })

    return success_response2(db_product.model_dump(),
                            message="Product created successfully")



@router.put("/update")
async def update_product_by_body(
    update: ProductUpdateWithIDSchema,
    current_user: str = Depends(get_current_user),
):
    product_id = update.product_id
    existing = await engine.find_one(Product, Product.product_id == product_id)
    if not existing:
        logger.warning(f"❌ Product with ID {product_id} not found")
        raise HTTPException(status_code=404, detail="Product not found")

    # Extract only fields that were actually provided, excluding product_id
    update_data = update.model_dump(exclude_unset=True, exclude={"product_id"})

    # Handle quantity validation
    if "quantity" in update_data and update_data["quantity"] < 0:
        raise HTTPException(status_code=400, detail="Quantity cannot be negative")

    # Only update status if it's explicitly provided
    if "status" in update_data:
        existing.status = update_data.pop("status")

    # Update all other provided fields
    for field, value in update_data.items():
        setattr(existing, field, value)

    # Set audit fields
    existing.modified_by = current_user
    existing.modified_date = datetime.now(timezone.utc)

    await engine.save(existing)

    await send_event("product.updated", {
        "action": "product_updated",
        "product": existing.model_dump(),
        "modified_by": current_user,
    })

    return success_response2(existing.model_dump(), message=f"Product {product_id} Updated successfully")


# @router.put("/update")
# async def update_product_by_body(
#     update: ProductUpdateWithIDSchema,
#     current_user: str = Depends(get_current_user),
# ):
#     product_id = update.product_id
#     existing = await engine.find_one(Product, Product.product_id == product_id)
#     if not existing:
#         logger.warning(f"❌ Product with ID {product_id} not found")
#         raise HTTPException(status_code=404, detail="Product not found")

#     update_data = update.model_dump(exclude_unset=True)
#     update_data.pop("product_id", None)

#     if "quantity" in update_data and update_data["quantity"] < 0:
#         raise HTTPException(status_code=400, detail="Quantity cannot be negative")

#     for field, value in update_data.items():
#         setattr(existing, field, value)

#     existing.modified_by = current_user
#     existing.modified_date = datetime.now(timezone.utc)
#     await engine.save(existing)

#     await send_event("product.updated", {
#         "action": "product_updated",
#         "product": existing.model_dump(),
#         "modified_by": current_user,
#     })

#     return success_response2(existing.model_dump(),message=f"Product {product_id} Updated successfully")

# @router.post("/status")
# async def toggle_product_status_by_body(
#     request: ProductIDRequest,
#     current_user: str = Depends(get_current_user),
# ):
#     product_id = request.product_id
#     product = await engine.find_one(Product, Product.product_id == product_id)
#     if not product:
#         logger.warning(f"❌ Product with ID {product_id} not found")
#         raise HTTPException(status_code=404, detail="Product not found")

#     product.status = not product.status
#     await engine.save(product)

#     await send_event("product.activate_deactivate", {
#         "action": "activate" if product.status else "deactivate",
#         "product": product.model_dump(),
#         "toggled_by": current_user,
#     })

#     logger.info(f"🔁 Product {product_id} status changed to {product.status} by {current_user}")
#     return success_response2(
#     product.model_dump(),
#     message=f"Product {product_id} is now {'Active' if product.status else 'Inactive'}"
#     )
