# from uuid import uuid4
# from datetime import datetime
# from faker import Faker
# from typing import Dict, Any
# import random

# faker = Faker()

# def get_random_id():
#     return random.randint(1000, 9999)


# def generate_random_product():
#     random_id = get_random_id()
#     manufacturer_id = get_random_id()
#     category_id = get_random_id()
#     sub_category_id = get_random_id()
#     digikey_number = f"P{random_id}-ND"
#     mpn = f"MPN-{faker.bothify(text='????????').upper()}"

#     return {
#         "Manufacturer": {
#             "Id": manufacturer_id,
#             "Name": faker.company()
#         },
#         "ManufacturerProductNumber": mpn,
#         "UnitPrice": round(random.uniform(0.5, 10), 2),
#         "ProductUrl": faker.url(),
#         "DatasheetUrl": faker.url(),
#         "PhotoUrl": "https://www.digikey.com//media.digikey.com/Photos/Maxwell%20Technologies%20Photos/BCAP0350%20E270%20T11.JPG",
#         "ProductVariations": [{
#             "DigiKeyProductNumber": digikey_number,
#             "PackageType": {
#                 "Id": random.randint(1, 5),
#                 "Name": random.choice(["Bulk", "Cut Tape", "Tape & Reel"])
#             },
#             "StandardPricing": [
#                 {"BreakQuantity": 1, "UnitPrice": 1.03, "TotalPrice": 1.03},
#                 {"BreakQuantity": 10, "UnitPrice": 0.79, "TotalPrice": 7.90}
#             ],
#             "MyPricing": [
#                 {"BreakQuantity": 1, "UnitPrice": 0.74, "TotalPrice": 0.74}
#             ],
#             "MarketPlace": faker.boolean(),
#             "TariffActive": faker.boolean(),
#             "Supplier": {
#                 "Id": manufacturer_id,
#                 "Name": faker.company()
#             },
#             "QuantityAvailableforPackageType": random.randint(0, 1000),
#             "MaxQuantityForDistribution": random.randint(0, 10000),
#             "MinimumOrderQuantity": 1,
#             "StandardPackage": random.randint(10, 1000),
#             "DigiReelFee": round(random.uniform(0, 10), 2)
#         }],
#         "QuantityAvailable": random.randint(0, 10000),
#         "ProductStatus": {
#             "Id": 0,
#             "Status": "Active"
#         },
#         "Parameters": [
#             {
#                 "ParameterId": 3,
#                 "ParameterText": "Tolerance",
#                 "ParameterType": "String",
#                 "ValueId": "1900",
#                 "ValueText": "±20%"
#             }
#         ],
#         "Category": {
#             "CategoryId": category_id,
#             "ParentId": 0,
#             "Name": "Capacitors",
#             "ImageUrl": "https://www.digikey.com//media.digikey.com/Photos/Maxwell%20Technologies%20Photos/BCAP0350%20E270%20T11.JPG",
#             "SeoDescription": faker.text(max_nb_chars=100),
#             "ChildCategories": [{
#                 "CategoryId": sub_category_id,
#                 "ParentId": category_id,
#                 "Name": "Aluminum Electrolytic Capacitors",
#                 "ImageUrl": "https://www.digikey.com//media.digikey.com/photos/Nichicon%20Photos/VX-Series-5x12mm.JPG",
#                 "SeoDescription": faker.text(max_nb_chars=100)
#             }]
#         },
#         "Series": {
#             "Id": random.randint(1, 500),
#             "Name": faker.word()
#         },
#         "Description": {
#             "ProductDescription": faker.catch_phrase(),
#             "DetailedDescription": faker.text(max_nb_chars=150)
#         },
#         "ShippingInfo": {
#             "Weight": f"{round(random.uniform(0.01, 1.0), 2)} kg",
#             "Dimensions": f"{random.randint(1, 10)}x{random.randint(1, 10)}x{random.randint(1, 10)} cm"
#         },
#         "Classifications": {
#             "ECCN": "EAR99",
#             "UNSPSC": "32121500"
#         },
#         "OtherNames": [
#             faker.word(),
#             faker.word()
#         ]
#     }
# #print(generate_random_product())
# def process_digikey_product(digikey_data):
#     if not digikey_data.get("Manufacturer"):
#         digikey_data["Manufacturer"] = {"Id": 0, "Name": "Unknown Manufacturer"}
#     elif not digikey_data["Manufacturer"].get("Id"):
#         digikey_data["Manufacturer"]["Id"] = 0

#     now = datetime.utcnow()
#     semicon_product_id = f"SPID-{digikey_data.get('ManufacturerProductNumber')}"
#     variation = digikey_data.get("ProductVariations", [{}])[0]

#     manufacturer = {
#         "_id": str(uuid4()),
#         "manufacturer_id": f"SMID-{digikey_data['Manufacturer']['Id']}",
#         "name": digikey_data["Manufacturer"].get("Name", "Unknown Manufacturer"),
#         "status": True,
#         "created_by": "system@digikey.com",
#         "created_date": now,
#         "modified_by": "system@digikey.com",
#         "modified_date": now
#     }

#     category = digikey_data.get("Category", {})
#     category_doc = {
#         "_id": str(uuid4()),
#         "category_id": f"SCID-{category.get('CategoryId')}",
#         "name": category.get("Name"),
#         "image_url": category.get("ImageUrl"),
#         "seo_description": category.get("SeoDescription"),
#         "created_by": "system@digikey.com",
#         "created_date": now,
#         "modified_by": "system@digikey.com",
#         "modified_date": now
#     }
    
#     child_categories = category.get("ChildCategories", [])
#     sub_category_docs = []
#     for child_category in child_categories:
#         if "CategoryId" not in child_category:
#             continue
#         sub_category_docs.append({
#             "_id": str(uuid4()),
#             "category_id": category_doc["category_id"],
#             "subcategory_id": f"SSCID-{child_category['CategoryId']}",
#             "status": digikey_data.get("ProductStatus", {}).get("Status", "").lower() == "active",
#             "name": child_category.get("Name", "Default SubCategory"),
#             "image_url": child_category.get("ImageUrl") or "https://default.image.url/placeholder.jpg",
#             "seo_description": child_category.get("SeoDescription", ""),
#             "created_by": "system@digikey.com",
#             "created_date": now,
#             "modified_by": "system@digikey.com",
#             "modified_date": now
#             })

#     # ✅ Use first subcategory for semicon_product
#     first_sub_category_id = sub_category_docs[0]["subcategory_id"] if sub_category_docs else None

#     semicon_product_doc = {
#         "_id": str(uuid4()),
#         "semicon_product_id": semicon_product_id,
#         "manufacturer_id": manufacturer["manufacturer_id"],
#         "category_id": category_doc["category_id"],
#         "sub_category_id":first_sub_category_id,
#         "series": digikey_data.get("Series", {}).get("Name", "Default"),
#         "status": digikey_data.get("ProductStatus", {}).get("Status", "").lower() == "active",
#         "description_short": digikey_data.get("Description", {}).get("ProductDescription", ""),
#         "description_detailed": digikey_data.get("Description", {}).get("DetailedDescription", ""),
#         "package_type": variation.get("PackageType", {}).get("Name", "Unknown"),
#         "image": digikey_data.get("PhotoUrl"),
#         "created_by": "system@digikey.com",
#         "created_date": now,
#         "modified_by": "system@digikey.com",
#         "modified_date": now
#     }

#     product_specifications_docs = []
#     for param in digikey_data.get("Parameters", []):
#         product_specifications_docs.append({
#             "_id": str(uuid4()),
#             "parameter_id": str(param.get("ParameterId")),
#             "parameter_text": param.get("ParameterText"),
#             "parameter_type": param.get("ParameterType"),
#             "value_id": param.get("ValueId"),
#             "value_text": param.get("ValueText"),
#             "status": True,
#             "created_by": "system@digikey.com",
#             "created_date": now,
#             "modified_by": "system@digikey.com",
#             "modified_date": now
#         })

#     vendor_product_doc = {
#         "_id": str(uuid4()),
#         "product_id": semicon_product_id,
#         "vendor_product_id": variation.get("DigiKeyProductNumber"),
#         "manufacturer_product_number": digikey_data.get("ManufacturerProductNumber"),
#         "unit_price": digikey_data.get("UnitPrice"),
#         "min_quantity": variation.get("MinimumOrderQuantity"),
#         "product_url": digikey_data.get("ProductUrl"),
#         "vendor": "Digikey",
#         "created_by": "system@digikey.com",
#         "created_date": now,
#         "modified_by": "system@digikey.com",
#         "modified_date": now
#     }

#     vendor_bulk_pricing_doc = {
#         "_id": str(uuid4()),
#         "vendor_product_id": variation.get("DigiKeyProductNumber"),
#         "pricing_record_id": f"SPRID-{uuid4()}",
#         "standard_pricing": [
#             {
#                 "break_quantity": p.get("BreakQuantity"),
#                 "unit_price": p.get("UnitPrice"),
#                 "total_price": p.get("TotalPrice")
#             } for p in variation.get("StandardPricing", [])
#         ],
#         "my_pricing": [
#             {
#                 "break_quantity": p.get("BreakQuantity"),
#                 "unit_price": p.get("UnitPrice"),
#                 "total_price": p.get("TotalPrice")
#             } for p in variation.get("MyPricing", [])
#         ],
#         "created_by": "system@digikey.com",
#         "created_date": now,
#         "modified_by": "system@digikey.com",
#         "modified_date": now
#     }

#     return {
#         "manufacturer": manufacturer,
#         "category": category_doc,
#         "sub_category": sub_category_docs,
#         "semicon_product": semicon_product_doc,
#         "product_specifications": product_specifications_docs,
#         "vendor_product": vendor_product_doc,
#         "vendor_bulk_pricing": vendor_bulk_pricing_doc
#     }
