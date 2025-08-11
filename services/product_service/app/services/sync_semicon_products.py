from datetime import datetime
from uuid import UUID
import uuid

from app.models.categories_models import SemiconCategory, SemiconChildCategory
from app.models.manufacturers_models import SemiconManufacturer
from app.models.semicon_products import SemiconProduct as SemiconProductListing #Parameter as ListingParameter
from app.models.semicon_products_details import (
    SemiconProduct as SemiconProductDetails,
    BaseProductNumber, Series, Classifications, Manufacturer, Category, ProductStatus
)
from app.models.variant_pricing_models import SemiconProductVariantPricing, PricingTier
from app.models.vendors_product_variant_parameters import VendorProductVariantParameter
from app.models.product_varianants import VendorProduct as VendorProductVariant, Supplier as VariantSupplier, parameter as VariantParameter
from app.models.vendor_product_variants_models import VendorProduct
from app.autogenerate import (
    get_next_category_counter,
    get_next_manufacturer_counter,
    get_next_product_counter,
    get_next_vendor_product_counter,
    get_next_variant_counter,
    get_next_pricing_counter,
    get_next_parameter_counter
)
from app.database import engine
from app.kafka.kafka_producer import send_event

async def gather_full_product_data(db, listing_product, details, vendor_product):
    listing_dict = listing_product.dict()
    details_dict = details.dict()
    vendor_dict = vendor_product.dict()

    expanded_variants = []
    for variant_id in vendor_product.product_variants:
        variant = await db.find_one(VendorProductVariant, VendorProductVariant.semicon_product_variant_id == variant_id)
        if not variant:
            continue
        variant_dict = variant.dict()

        # Expand pricing for this variant
        pricing_expanded = []
        for pricing_id in variant.semicon_product_variant_pricing_id:
            pricing = await db.find_one(SemiconProductVariantPricing, SemiconProductVariantPricing.semicon_product_variant_pricing_id == pricing_id)
            if pricing:
                pricing_dict = pricing.dict()
                pricing_dict['pricing'] = [p.dict() if hasattr(p, 'dict') else p for p in pricing.pricing]
                pricing_expanded.append(pricing_dict)
        variant_dict['pricing_details'] = pricing_expanded

        # Expand parameters for this variant
        parameters_expanded = []
        for param in variant.parameters:
            param_doc = await db.find_one(VendorProductVariantParameter, VendorProductVariantParameter.semicon_parameter_id == param.parameter_id)
            if param_doc:
                param_dict = param_doc.dict()
                param_dict.update({
                    'value_id': param.value_id,
                    'value_text': param.value_text
                })
                parameters_expanded.append(param_dict)
        variant_dict['parameters_expanded'] = parameters_expanded

        expanded_variants.append(variant_dict)

    vendor_dict['variants_expanded'] = expanded_variants

    return {
        'listing_product': listing_dict,
        'product_details': details_dict,
        'vendor_product': vendor_dict,
    }


def parse_manufacturer(manu_raw):
    """Parse manufacturer data into (id, name) safely."""
    if isinstance(manu_raw, dict):
        return (
            manu_raw.get("Id") or manu_raw.get("id"),
            manu_raw.get("Name") or manu_raw.get("name")
        )
    elif isinstance(manu_raw, str):
        return None, manu_raw
    return None, None

async def build_child_category_tree(db, parent_id):
    children = await db.find(
        SemiconChildCategory,
        SemiconChildCategory.digikey_parent_id == parent_id
    )
    child_list = []
    for child in children:
        child_list.append({
            "categoryId": child.digikey_child_category_id,
            "name": child.digikey_name,
            "parentId": child.digikey_parent_id,
            "productCount": getattr(child, "product_count", 0),
            "imageUrl": getattr(child, "image_url", ""),
            "seoDescription": getattr(child, "seo_description", ""),
            "childCategories": await build_child_category_tree(db, child.digikey_child_category_id)
        })
    return child_list
async def fetch_and_sync_semicon_product(digikey_data: dict):
    db = engine

    # -------- CATEGORY --------
    if "categoryDetails" in digikey_data:
        category_info = digikey_data["categoryDetails"]
    elif "Category" in digikey_data:
        category_info = {
            "categoryId": digikey_data["Category"].get("CategoryId"),
            "name": digikey_data["Category"].get("Name"),
            "parentId": digikey_data["Category"].get("ParentId"),
            "childCategories": digikey_data["Category"].get("ChildCategories", [])
        }
    else:
        category_info = None

    if not category_info:
        raise ValueError("No category details found in Digikey data")
    #print(f"Category Info: {category_info}")

    category = await db.find_one(
        SemiconCategory,
        SemiconCategory.digikey_category_id == category_info.get("categoryId")
    )
    if not category:
        semicon_category_id = f"SCID-{await get_next_category_counter(db)}"
        category = SemiconCategory(
            semicon_category_id=semicon_category_id,
            semicon_parent_id=None,
            digikey_category_id=category_info.get("categoryId") if category_info.get("categoryId") is not None else 0,
            digikey_name=category_info.get("name"), # type: ignore
            digikey_parent_id=str(category_info.get("parentId", "")),
            product_count=0,
            child_categories=[],
            created_by="admin",
            modified_by="admin",
            created_date=datetime.utcnow(),
            modified_date=datetime.utcnow(),
            status=True
        )
        await db.save(category)

    # -------- MANUFACTURER --------
    manu_id, manu_name = parse_manufacturer(digikey_data.get("Manufacturer") or digikey_data.get("manufacturer"))
    manufacturer = await db.find_one(
        SemiconManufacturer,
        SemiconManufacturer.digikey_manufacturer_id == manu_id
    )
    manu_s_id = manufacturer.semicon_manufacturer_id if manufacturer else None
    if not manufacturer:
        semicon_manufacturer_id = f"SMID-{await get_next_manufacturer_counter(db)}"
        manufacturer = SemiconManufacturer(
            semicon_manufacturer_id=semicon_manufacturer_id,
            digikey_manufacturer_id=manu_id or 0,
            digikey_name=manu_name or "",
            created_by="admin",
            modified_by="admin",
            created_date=datetime.utcnow(),
            modified_date=datetime.utcnow(),
            status=True
        )  # type: ignore
        await db.save(manufacturer)

    # --- CHILD CATEGORY ---
    child_cat = None
    semicon_child_category_id = None
    child_categories_data = []
    target_child_id = category_info.get("childCategories", [{}])[0].get("CategoryId")
    semicon_child_category_id = None
    for cat in category.child_categories:
        if cat.digikey_child_category_id == target_child_id:
            semicon_child_category_id = cat.semicon_child_category_id
            break
    print(f"Found child category ID: {semicon_child_category_id}")


    first_child = (category_info.get("childCategories") or [None])[0]
    if first_child:
        child_cat = await db.find_one(
            SemiconChildCategory,
            SemiconChildCategory.digikey_child_category_id == first_child.get("categoryId")
        )
        if child_cat:
            semicon_child_category_id = child_cat.semicon_child_category_id
            child_categories_data = await build_child_category_tree(
                db,
                category_info.get("categoryId")  # Start from main category
            )
        else:
            child_categories_data = category_info.get("childCategories", [])
    else:
        child_categories_data = category_info.get("childCategories", [])

    first_variation = digikey_data['productVariations'][0]  # first product variation
    first_price_tier = first_variation['StandardPricing'][0]  # first price tier

    first_unit_price = first_price_tier['UnitPrice']
    # -------- PRODUCT LISTING --------
    spid = f"SPID-{await get_next_product_counter(db)}"
    listing_product = SemiconProductListing(
        #semicon_product_id=spid,
        name=digikey_data.get("name", ""),
        description=digikey_data.get("description", ""),
        image_url=digikey_data.get("photoUrl"),
        datasheet_url=digikey_data.get("datasheetUrl"),
        #package_type=(digikey_data.get("productVariations") or [{}])[0].get("PackageType", {}).get("name"),
        quantity_available=digikey_data.get("quantityAvailable", 0),
        UnitPrice= first_unit_price or 0.0,
        manufacturerPartNumber=digikey_data.get("manufacturerPartNumber", ""),
        manufacturer_name=digikey_data.get("manufacturer", ""),
        semicon_manufacturer_id=manu_s_id,
        vendor_details=[],
        semicon_part_number=f"SPNID-{digikey_data.get('manufacturerPartNumber', 'UNKNOWN')}",
        semicon_category_id=category.semicon_category_id,
        semicon_child_category_id=semicon_child_category_id,
        
        created_by="admin",
        modified_by="admin",
        status=True
    )


    # -------- PRODUCT DETAILS --------
    details = SemiconProductDetails(
        name=listing_product.name,
        semicon_part_number=listing_product.semicon_part_number or "",
        productId=UUID(digikey_data.get("productId")),
        UnitPrice=listing_product.UnitPrice or 0,
        ProductUrl=digikey_data.get("productUrl"),
        DatasheetUrl=digikey_data.get("datasheetUrl"),
        PhotoUrl=digikey_data.get("photoUrl"),
        BackOrderNotAllowed=str(digikey_data.get("backOrderNotAllowed", "")),
        NormallyStocking=str(digikey_data.get("normallyStocking", "")),
        Discontinued=str(digikey_data.get("discontinued", "")),
        EndOfLife=str(digikey_data.get("endOfLife", "")),
        Ncnr=str(digikey_data.get("ncnr", "")),
        PrimaryVideoUrl=digikey_data.get("primaryVideoUrl") or None,
        BaseProductNumber=BaseProductNumber(**digikey_data.get("baseProductNumber", {})),
        ManufacturerLeadWeeks=digikey_data.get("manufacturerLeadWeeks"),
        ManufacturerPublicQuantity=int(digikey_data.get("quantityAvailable") or 0),
        Series=Series(**digikey_data["series"]) if digikey_data.get("series") else None,
        Classifications=Classifications(**{
            "ReachStatus": digikey_data.get("classifications", {}).get("ReachStatus") or digikey_data.get("classifications", {}).get("reachStatus"),
            "RohsStatus": digikey_data.get("classifications", {}).get("RohsStatus") or digikey_data.get("classifications", {}).get("rohsStatus"),
            "MoistureSensitivityLevel": digikey_data.get("classifications", {}).get("MoistureSensitivityLevel") or digikey_data.get("classifications", {}).get("moistureSensitivityLevel"),
            "ExportControlClassNumber": digikey_data.get("classifications", {}).get("ExportControlClassNumber") or digikey_data.get("classifications", {}).get("eccn"),
            "HtsusCode": digikey_data.get("classifications", {}).get("HtsusCode") or digikey_data.get("classifications", {}).get("htsusCode")
        }),
        categoryHierarchy=digikey_data.get("categoryHierarchy", []),
        Manufacturer=Manufacturer(Id=manu_id, Name=manu_name, semicon_manufacturer_id=manu_s_id), # type: ignore
        Category=Category(
            CategoryId=category_info.get("categoryId"),
            ParentId=category_info.get("parentId", 0),
            Name=category_info.get("name", ""),
            ProductCount=category_info.get("productCount", 0),
            NewProductCount=category_info.get("newProductCount", 0),
            ImageUrl=category_info.get("imageUrl", ""),
            SeoDescription=category_info.get("seoDescription", ""),
            ChildCategories=child_categories_data
        ),
        OtherNames=digikey_data.get("otherNames", []),
        ProductStatus=ProductStatus(**digikey_data.get("productStatus", {})),
        modified_by="admin",
        status=True
    )
    #print(f"Product Details: {details}")
    await db.save(details)

    # -------- VENDOR PRODUCT --------
    vpid = f"VPID-{await get_next_vendor_product_counter(db)}"
    vendor_product = VendorProduct(
        semicon_vendor_id=vpid,
        vendor_name="digikey",
        vendor_product_number=vpid,
        product_variants=[],
        semicon_part_number=listing_product.semicon_part_number or "",
        created_by="admin",
        modified_by="admin",
        status=True
    )
    listing_product.vendor_details.append(vpid)
    await db.save(listing_product)
    variant_ids = []
    # -------- PRODUCT VARIANTS & PARAMETERS & PRICING --------
    
    parameter_counter = await get_next_parameter_counter(db)
    variant_counter = await get_next_variant_counter(db)
    for variation_idx, variation in enumerate(digikey_data.get("productVariations", [])):
        # Create parameters specific to this variant
       
        variant_params = []
        for idx, param in enumerate(variation.get("parameters", digikey_data.get("parameters", []))):
            spara_id = f"SPARAID-{parameter_counter}"
            parameter_counter += 1

            # Save the parameter document for reference
            param_doc = VendorProductVariantParameter(
                semicon_parameter_id=spara_id,
                digikey_parameter_id=param.get("ParameterId"),
                parameter_text=param.get("ParameterText") or "Unknown",
                parameter_type="ParameterType",
                created_by="admin",
                modified_by="admin",
                status=True
            )
            await db.save(param_doc)

            # Create the embedded parameter for the variant
            variant_param = VariantParameter(
                parameter_id=spara_id,
                value_id=str(param.get("ValueId", "")),
                value_text=param.get("ValueText") or "Unknown"
            )
            variant_params.append(variant_param)

            # key = param.get("text") or f"Unknown-{variation_idx}-{idx}"
            # listing_product.parameters[key] = ListingParameter(
            #     parameter_id=spara_id,
            #     value_id=param.get("valueId"),
            #     value_text=param.get("value") or "Unknown",
            #     parameter_text=param.get("text") or "Unknown",
            #     parameter_type="string"
            # )
        await db.save(listing_product)
        ssidk = f"SPVID-{variant_counter}"
        variant_counter += 1 

        # Create variant document
        ssidk=f"SPVID-{ssidk}"
        vendor_part_number = variation.get("digiKeyProductNumber") or variation.get("DigiKeyProductNumber") or variation.get("productNumber") or "UNKNOWN"
        supplier_id, supplier_name = parse_manufacturer(variation.get("Supplier") or digikey_data.get("Manufacturer"))
        variant_doc = VendorProductVariant(
            semicon_product_variant_id=ssidk,
            vendor_part_number=vendor_part_number,
            digikey_product_number=vendor_part_number,
            marketplace=variation.get("marketPlace", False),
            tariff_active=variation.get("tariffActive", False),
            supplier=VariantSupplier(id=supplier_id or 0, name=supplier_name or ""),
            quantity_available_for_package_type=variation.get("quantityAvailableForPackageType", 0),
            max_quantity_for_distribution=variation.get("maxQuantityForDistribution", 0),
            standard_package=variation.get("standardPackage", 0),
            digireel_fee=variation.get("digireelFee", 0),
            created_by="admin",
            modified_by="admin",
            status=True,
            parameters=variant_params,
            semicon_product_variant_pricing_id=[]
        )
        
        variant_ids.append(ssidk)

        # Create pricing for variant
        spvpid = f"SPVPID-{await get_next_pricing_counter(db)}"
        package_type = (variation.get("packageType") or {}).get("name") or "Unknown"
        pricing_doc = SemiconProductVariantPricing(
            package_type=package_type,
            minimum_order_quantity=variation.get("minimumOrderQuantity", 0),
            pricing=[PricingTier(**p) for p in variation.get("StandardPricing", [])],
            created_by="admin",
            modified_by="admin",
            status=True,
            semicon_product_variant_pricing_id=spvpid,
            semicon_product_variant_id=ssidk
        )
        await db.save(pricing_doc)
        variant_doc.semicon_product_variant_pricing_id.append(spvpid)
        await db.save(variant_doc)
    vendor_product.product_variants = list(set(vendor_product.product_variants + variant_ids))
    await db.save(vendor_product)
    sb= None
    if details.Category.ChildCategories:
        sb = details.Category.ChildCategories[0].Name
    all_data_dict = {
        "productname": listing_product.name,
        "category": details.Category.Name,
        "manufacturer": manu_name,
        "subcategory": sb,
        "semicon_part_number": listing_product.semicon_part_number,
     }

    await send_event(topic="product.added", value=all_data_dict)
    return listing_product 
