from fastapi import APIRouter, Depends, HTTPException
from odmantic import ObjectId
from datetime import datetime
from app.database import engine
from app.models.manufacturers_models import SemiconManufacturer
from app.schemas.manufacturers_schema import (
    SemiconManufacturerCreateSchema,
    SemiconManufacturerUpdateSchema,
)
from app.autogenerate import get_next_manufacturer_counter
from fastapi.encoders import jsonable_encoder
router = APIRouter(prefix="/product")

@router.post("/manufacturer/add", tags=["Semicon Manufacturer"])
async def add_manufacturer(payload: SemiconManufacturerCreateSchema):
    db = engine
    existing = await db.find_one(SemiconManufacturer, SemiconManufacturer.digikey_manufacturer_id == payload.digikey_manufacturer_id)
    if existing:
        raise HTTPException(status_code=400, detail={"status": "failure", "message": "Manufacturer already exists."})

    semi=await get_next_manufacturer_counter()
    semicon_manufacturer_id=f"SMID-{semi+1}"

    new_manufacturer = SemiconManufacturer(
        semicon_manufacturer_id=semicon_manufacturer_id,
        digikey_manufacturer_id=payload.digikey_manufacturer_id,
        digikey_name=payload.digikey_name,
        created_by="admin",
        modified_by="admin",
        created_date=datetime.utcnow(),
        modified_date=datetime.utcnow(),
        status=True
    ) # type: ignore
    await db.save(new_manufacturer)
    return {"status": "success", "message": "Manufacturer added successfully", "data": semicon_manufacturer_id}


@router.put("/manufacturer/update", tags=["Semicon Manufacturer"])
async def update_manufacturer(payload: SemiconManufacturerUpdateSchema):
    db = engine
    existing = await db.find_one(SemiconManufacturer, SemiconManufacturer.semicon_manufacturer_id == payload.semicon_manufacturer_id)
    if not existing:
        raise HTTPException(status_code=404, detail={"status": "failure", "message": "Manufacturer not found."})

    if payload.digikey_name:
        existing.digikey_name = payload.digikey_name

    existing.modified_by = "admin"
    existing.modified_date = datetime.utcnow()

    await db.save(existing)
    return {"status": "success", "message": "Manufacturer updated successfully"}
def transform_mongo_doc(doc):
    doc = doc.dict() if hasattr(doc, "dict") else dict(doc)
    doc["id"] = str(doc.get("id") or doc.get("_id"))  # normalize ID field
    if "_id" in doc:
        del doc["_id"]
    return doc
@router.get("/manufacturer/all", tags=["Semicon Manufacturer"])
async def get_all_manufacturers():
    raw_data = await engine.find(SemiconManufacturer)
    cleaned_data = [transform_mongo_doc(doc) for doc in raw_data]
    return {
        "status": "success",
        "data": jsonable_encoder(cleaned_data)
    }
