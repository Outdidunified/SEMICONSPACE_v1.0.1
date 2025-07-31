import logging
from typing import Dict, Any
from app.models.products_models import Product
from app.database import engine

logger = logging.getLogger(__name__)


async def reduce_product_stock(event: Dict[str, Any]):
    product_id = event.get("product_id")
    quantity = event.get("quantity", 1)

    if not product_id:
        logger.warning("⚠️ product_id missing in event")
        return

    # Fetch product
    product = await engine.find_one(Product, Product.product_id == product_id)
    if not product:
        logger.warning(f"❌ Product {product_id} not found")
        return

    # Stock check
    if product.quantity is None:
        logger.warning(
            f"⚠️ Product {product_id} has no quantity set, skipping update"
        )
        return

    if product.quantity < quantity:
        logger.warning(
            f"⚠️ Not enough stock for product {product_id} "
            f"(Available: {product.quantity}, Requested: {quantity})"
        )
        return

    product.quantity -= quantity
    await engine.save(product)

    logger.info(
        f"✅ Product {product_id} stock reduced by {quantity}. "
        f"New quantity = {product.quantity}"
    )
