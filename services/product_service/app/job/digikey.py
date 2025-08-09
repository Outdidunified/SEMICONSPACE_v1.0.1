# import sys
# import os
# import asyncio
# from pprint import pprint

# # Adjust Python path to find modules from the root
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

# # Import ODMantic models
# from app.models.manufacturers_models import Manufacturer
# from app.models.categories_models import Category
# from app.models.sub_categorie_model import SubCategory
# from app.models.products_models import SemiconProduct
# from app.models.specifications_models import ProductSpecification
# from app.models.vendor_product_model import VendorProduct
# from app.models.pricing_models import VendorBulkPricing

# # Database engine
# from app.database import engine

# # Data generation & processing functions
# from app.job.generator import generate_random_product, process_digikey_product


# async def save_digikey_product_to_db():
#     # Step 1: Generate mock data and process it
#     raw_data = generate_random_product()
#     processed = process_digikey_product(raw_data)
#     # Step 2: Create or reuse ODMantic model instances

#     # Check for existing manufacturer
#     existing_manufacturer = await engine.find_one(
#         Manufacturer, Manufacturer.manufacturer_id == processed["manufacturer"]["manufacturer_id"]
#     )
#     manufacturer = existing_manufacturer or Manufacturer(**processed["manufacturer"])

#     # Check for existing category
#     existing_category = await engine.find_one(
#         Category, Category.category_id == processed["category"]["category_id"]
#     )
#     category = existing_category or Category(**processed["category"])

#     # Check for existing subcategories (could be multiple)
#     sub_categories = []
#     for sub_cat_data in processed["sub_category"]:
#         existing_sub = await engine.find_one(
#             SubCategory, SubCategory.id == sub_cat_data["subcategory_id"]  # or match on subcategory name + category_id
#         )
#         sub_categories.append(existing_sub or SubCategory(**sub_cat_data))

#     # Always create new SemiconProduct (assume unique product)
#     semicon_product = SemiconProduct(**processed["semicon_product"])

#     # Always create specifications (they're unique per product)
#     product_spec_list = [ProductSpecification(**spec) for spec in processed["product_specifications"]]

#     # Always create vendor product & pricing
#     vendor_product = VendorProduct(**processed["vendor_product"])
#     vendor_bulk = VendorBulkPricing(**processed["vendor_bulk_pricing"])


#     # Step 3: Save all documents to MongoDB
#     await engine.save(manufacturer)
#     await engine.save(category)
#     for sub_category in sub_categories:
#         await engine.save(sub_category)

#     await engine.save(semicon_product)
#     for spec in product_spec_list:
#         await engine.save(spec)

#     await engine.save(vendor_product)
#     await engine.save(vendor_bulk)

#     print("✔ Data saved to MongoDB")


# # Entry point
# if __name__ == "__main__":
#     asyncio.run(save_digikey_product_to_db())
