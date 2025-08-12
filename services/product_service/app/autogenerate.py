# app/utils/counters.py
from app.models.categories_models import SemiconCategory
from app.models.manufacturers_models import SemiconManufacturer
from app.models.semicon_products import SemiconProduct
from app.models.product_varianants import VendorProduct
from app.models.variant_pricing_models import SemiconProductVariantPricing
from app.models.vendors_product_variant_parameters import VendorProductVariantParameter
from app.models.product_varianants import VendorProduct as SemiconProductVariant
from app.models.vendor_product_variants_models import VendorProduct as VendorProductModel
from app.database import engine


async def get_next_category_counter(db=engine) -> int:
    docs = await db.find(SemiconCategory)
    max_id = 0
    for doc in docs:
        try:
            if doc.semicon_category_id is not None:
                current = int(doc.semicon_category_id.split("-")[1])
                max_id = max(max_id, current)
        except Exception:
            continue
    return max_id + 1


async def get_next_manufacturer_counter(db=engine) -> int:
    docs = await db.find(SemiconManufacturer)
    max_id = 0
    for doc in docs:
        try:
            if doc.semicon_manufacturer_id is not None:
                current = int(doc.semicon_manufacturer_id.split("-")[1])
                max_id = max(max_id, current)
        except Exception:
            continue
    return max_id + 1


async def get_next_product_counter(db=engine) -> int:
    docs = await db.find(SemiconProduct)
    max_id = 0
    for doc in docs:
        try:
            current = int(doc.semicon_product_id.split("-")[1])
            max_id = max(max_id, current)
        except Exception:
            continue
    return max_id + 1


async def get_next_vendor_product_counter(db=engine) -> int:
    docs = await db.find(VendorProduct)
    max_id = 0
    for doc in docs:
        try:
            current = int(doc.vendor_product_number.split("-")[1])
            max_id = max(max_id, current)
        except Exception:
            continue
    return max_id + 1


async def get_next_variant_counter(db=engine) -> int:
    docs = await db.find(SemiconProductVariant)
    max_id = 0
    for doc in docs:
        try:
            if doc.semicon_product_variant_id is not None:
                current = int(doc.semicon_product_variant_id.split("-")[1])
                max_id = max(max_id, current)
        except Exception:
            continue
    return max_id + 1


async def get_next_pricing_counter(db=engine) -> int:
    docs = await db.find(SemiconProductVariantPricing)
    max_id = 0
    for doc in docs:
        try:
            current = int(doc.semicon_product_variant_pricing_id.split("-")[1])
            max_id = max(max_id, current)
        except Exception:
            continue
    return max_id + 1


async def get_next_parameter_counter(db=engine) -> int:
    docs = await db.find(VendorProductVariantParameter)
    max_id = 0
    for doc in docs:
        try:
            current = int(doc.semicon_parameter_id.split("-")[1])
            max_id = max(max_id, current)
        except Exception:
            continue
    return max_id + 1

async def get_vendor_id(db=engine) -> int:
    docs = await db.find(VendorProductModel)
    max_id = 0
    for doc in docs:
        try:
            if doc.semicon_vendor_id is not None:
                current = int(doc.semicon_vendor_id.split("-")[1])
                max_id = max(max_id, current)
        except Exception:
            continue
    return max_id + 1