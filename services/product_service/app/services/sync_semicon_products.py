# from datetime import datetime
# from uuid import UUID
# import uuid

# from app.models.categories_models import SemiconCategory, SemiconChildCategory
# from app.models.manufacturers_models import SemiconManufacturer
# from app.models.semicon_products import SemiconProduct as SemiconProductListing, Parameter as ListingParameter
# from app.models.semicon_products_details import (
#     SemiconProduct as SemiconProductDetails,
#     BaseProductNumber, Series, Classifications, Manufacturer, Category, ProductStatus
# )
# from app.models.variant_pricing_models import SemiconProductVariantPricing, PricingTier
# from app.models.vendors_product_variant_parameters import VendorProductVariantParameter
# from app.models.product_varianants import VendorProduct as VendorProductVariant, Supplier as VariantSupplier
# from app.models.vendor_product_variants_models import VendorProduct
# from app.autogenerate import (
#     get_next_category_counter,
#     get_next_manufacturer_counter,
#     get_next_product_counter,
#     get_next_vendor_product_counter,
#     get_next_variant_counter,
#     get_next_pricing_counter,
#     get_next_parameter_counter
# )
# from app.database import engine


# def parse_manufacturer(manu_raw):
#     """Parse manufacturer data into (id, name) safely."""
#     if isinstance(manu_raw, dict):
#         return (
#             manu_raw.get("Id") or manu_raw.get("id"),
#             manu_raw.get("Name") or manu_raw.get("name")
#         )
#     elif isinstance(manu_raw, str):
#         return None, manu_raw
#     return None, None


# async def fetch_and_sync_semicon_product(digikey_data: dict):
#     db = engine

#     # -------- CATEGORY --------
#     if "categoryDetails" in digikey_data:
#         category_info = digikey_data["categoryDetails"]
#     elif "Category" in digikey_data:
#         category_info = {
#             "categoryId": digikey_data["Category"].get("CategoryId"),
#             "name": digikey_data["Category"].get("Name"),
#             "parentId": digikey_data["Category"].get("ParentId")
#         }
#     else:
#         category_info = None

#     if not category_info:
#         raise ValueError("No category details found in Digikey data")

#     category = await db.find_one(
#         SemiconCategory,
#         SemiconCategory.digikey_category_id == category_info.get("categoryId")
#     )
#     if not category:
#         semicon_category_id = f"SCID-{await get_next_category_counter(db)}"
#         category = SemiconCategory(
#             id=uuid.uuid4(),
#             semicon_category_id=semicon_category_id,
#             semicon_parent_id=None,
#             digikey_category_id=category_info.get("categoryId"),
#             digikey_name=category_info.get("name"), # type: ignore
#             digikey_parent_id=str(category_info.get("parentId", "")),
#             product_count=0,
#             child_categories=[],
#             created_by="admin",
#             modified_by="admin",
#             created_date=datetime.utcnow(),
#             modified_date=datetime.utcnow(),
#             status=True
#         )
#         await db.save(category)

#     # -------- MANUFACTURER --------
#     manu_id, manu_name = parse_manufacturer(digikey_data.get("Manufacturer") or digikey_data.get("manufacturer"))
#     manufacturer = await db.find_one(
#         SemiconManufacturer,
#         SemiconManufacturer.digikey_manufacturer_id == manu_id
#     )
#     if not manufacturer:
#         semicon_manufacturer_id = f"SMID-{await get_next_manufacturer_counter(db)}"
#         manufacturer = SemiconManufacturer(
#             semicon_manufacturer_id=semicon_manufacturer_id,
#             digikey_manufacturer_id=manu_id or 0,  # Fallback to 0 if manu_id is None
#             digikey_name=manu_name or "",
#             created_by="admin",
#             modified_by="admin",
#             created_date=datetime.utcnow(),
#             modified_date=datetime.utcnow(),
#             status=True
#         )  # type: ignore
#         await db.save(manufacturer)

#     # --- CHILD CATEGORY ---
#     child_cat = None
#     first_child = (category_info.get("childCategories") or [None])[0]
#     if first_child:
#         child_cat = await db.find_one(
#             SemiconChildCategory,
#             SemiconChildCategory.digikey_child_category_id == first_child.get("categoryId")
#         )

#     # -------- PRODUCT LISTING --------
#     spid = f"SPID-{await get_next_product_counter(db)}"
#     listing_product = SemiconProductListing(
#         semicon_product_id=spid,
#         name=digikey_data.get("name", ""),
#         description=digikey_data.get("description", ""),
#         image_url=digikey_data.get("photoUrl"),
#         datasheet_url=digikey_data.get("datasheetUrl"),
#         package_type=(digikey_data.get("productVariations") or [{}])[0].get("PackageType", {}).get("name"),
#         quantity_available=digikey_data.get("quantityAvailable", 0),
#         unitprice=float(
#             (digikey_data.get("productVariations") or [{}])[0]
#             .get("standardPricing", [{}])[0]
#             .get("unitPrice", 0.0)
#         ),
#         manufacturer_part_number=digikey_data.get("manufacturerPartNumber", ""),
#         vendors=[],
#         semicon_part_number=f"SPNID-{digikey_data.get('manufacturerPartNumber', 'UNKNOWN')}",
#         semicon_category_id=category.semicon_category_id,
#         semicon_child_category_id=child_cat.semicon_child_category_id if child_cat else None,
#         created_by="admin",
#         modified_by="admin",
#         status="active"
#     )

#     # -------- PRODUCT DETAILS --------
#     details = SemiconProductDetails(
#         semicon_part_number=listing_product.semicon_part_number or "",
#         productId=UUID(digikey_data.get("productId")),
#         UnitPrice=listing_product.unitprice or 0,
#         ProductUrl=digikey_data.get("productUrl"),
#         DatasheetUrl=digikey_data.get("datasheetUrl"),
#         PhotoUrl=digikey_data.get("photoUrl"),
#         BackOrderNotAllowed=str(digikey_data.get("backOrderNotAllowed", "")),
#         NormallyStocking=str(digikey_data.get("normallyStocking", "")),
#         Discontinued=str(digikey_data.get("discontinued", "")),
#         EndOfLife=str(digikey_data.get("endOfLife", "")),
#         Ncnr=str(digikey_data.get("ncnr", "")),
#         PrimaryVideoUrl=digikey_data.get("primaryVideoUrl") or None,
#         BaseProductNumber=BaseProductNumber(**digikey_data.get("baseProductNumber", {})),
#         ManufacturerLeadWeeks=digikey_data.get("manufacturerLeadWeeks"),
#         ManufacturerPublicQuantity=digikey_data.get("quantityAvailable"), # pyright: ignore[reportArgumentType]
#         Series=Series(**digikey_data["series"]) if digikey_data.get("series") else None,
#         Classifications=Classifications(**{
#             "ReachStatus": digikey_data.get("classifications", {}).get("ReachStatus") or digikey_data.get("classifications", {}).get("reachStatus"),
#             "RohsStatus": digikey_data.get("classifications", {}).get("RohsStatus") or digikey_data.get("classifications", {}).get("rohsStatus"),
#             "MoistureSensitivityLevel": digikey_data.get("classifications", {}).get("MoistureSensitivityLevel") or digikey_data.get("classifications", {}).get("moistureSensitivityLevel"),
#             "ExportControlClassNumber": digikey_data.get("classifications", {}).get("ExportControlClassNumber") or digikey_data.get("classifications", {}).get("eccn"),
#             "HtsusCode": digikey_data.get("classifications", {}).get("HtsusCode") or digikey_data.get("classifications", {}).get("htsusCode")
#         }),
#         categoryHierarchy=digikey_data.get("categoryHierarchy", []),
#         Manufacturer=Manufacturer(Id=manu_id, Name=manu_name), # type: ignore
#         Category=Category(
#             CategoryId=category_info.get("categoryId"),
#             ParentId=category_info.get("parentId", 0),
#             Name=category_info.get("name", ""),
#             ProductCount=category_info.get("productCount", 0),
#             NewProductCount=category_info.get("newProductCount", 0),
#             ImageUrl=category_info.get("imageUrl", ""),
#             SeoDescription=category_info.get("seoDescription", ""),
#             ChildCategories=category_info.get("childCategories", [])
#         ),
#         OtherNames=digikey_data.get("otherNames", []),
#         ProductStatus=ProductStatus(**digikey_data.get("productStatus", {})),
#         modified_by="admin",
#         status="active"
#     )
#     await db.save(details)

#     # -------- VENDOR PRODUCT --------
#     vpid = f"VPID-{await get_next_vendor_product_counter(db)}"
#     vendor_product = VendorProduct(
#         vendor_name="digikey",
#         vendor_product_number=vpid,
#         product_variants=[],
#         semicon_part_number=listing_product.semicon_part_number or "",
#         created_by="admin",
#         modified_by="admin",
#         status="active"
#     )
#     await db.save(vendor_product)
#     listing_product.vendors.append(vpid)
#     await db.save(listing_product)

#     # -------- PRODUCT VARIANTS & PRICING --------
#     for variation in digikey_data.get("productVariations", []):
#         spvid = f"SPVID-{await get_next_variant_counter(db)}"
#         vendor_part_number = variation.get("digiKeyProductNumber") or variation.get("DigiKeyProductNumber") or variation.get("productNumber") or "UNKNOWN"

#         # Use Supplier from variation instead of manufacturer
#         supplier_id, supplier_name = parse_manufacturer(variation.get("Supplier") or digikey_data.get("Manufacturer"))

#         variant_doc = VendorProductVariant(
#             vendor_part_number=vendor_part_number,
#             digikey_product_number=vendor_part_number,
#             marketplace=variation.get("marketPlace", False),
#             tariff_active=variation.get("tariffActive", False),
#             supplier=VariantSupplier(id=supplier_id or 0, name=supplier_name or ""),  # Fallback to 0 if supplier_id is None
#             quantity_available_for_package_type=variation.get("quantityAvailableForPackageType", 0),
#             max_quantity_for_distribution=variation.get("maxQuantityForDistribution", 0),
#             standard_package=variation.get("standardPackage", 0),
#             digireel_fee=variation.get("digireelFee", 0),
#             created_by="admin",
#             modified_by="admin",
#             status="active",
#             parameters=[],
#             semicon_product_variant_pricing_id=[]
#         )
#         await db.save(variant_doc)
#         vendor_product.product_variants.append(spvid)

#         spvpid = f"SPVPID-{await get_next_pricing_counter(db)}"
#         package_type = (variation.get("packageType") or {}).get("name") or "Unknown"
#         pricing_doc = SemiconProductVariantPricing(
#             package_type=package_type,
#             minimum_order_quantity=variation.get("minimumOrderQuantity", 0),
#             pricing=[PricingTier(**p) for p in variation.get("standardPricing", [])],
#             created_by="admin",
#             modified_by="admin",
#             status="active",
#             semicon_product_variant_pricing_id=spvpid,
#             semicon_product_variant_id=spvid
#         )
#         await db.save(pricing_doc)
#         variant_doc.semicon_product_variant_pricing_id.append(spvpid)
#         await db.save(variant_doc)

#     await db.save(vendor_product)

#     # -------- PARAMETERS --------
#     parameter_counter = await get_next_parameter_counter(db)
#     for idx, param in enumerate(digikey_data.get("parameters", [])):
#         spara_id = f"SPARAID-{parameter_counter + idx}"
        
#         param_doc = VendorProductVariantParameter(
#             semicon_parameter_id=spara_id,
#             digikey_parameter_id=param.get("id"),
#             parameter_text=param.get("text") or "Unknown",
#             parameter_type="string",
#             created_by="admin",
#             modified_by="admin",
#             status="active"
#         )
#         await db.save(param_doc)

#         listing_product.parameters.append(ListingParameter(
#             parameter_id=spara_id,
#             value_id=param.get("valueId"),
#             value_text=param.get("value") or "Unknown",
#             parameter_text=param.get("text") or "Unknown",
#             parameter_type="string"
#         ))

#     await db.save(listing_product)