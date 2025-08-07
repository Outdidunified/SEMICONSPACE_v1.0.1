from __future__ import annotations
from odmantic import Model
from datetime import datetime

class SemiconManufacturer(Model):
    semicon_manufacturer_id: str
    digikey_manufacturer_id: int
    digikey_name: str
    created_by: str
    modified_by: str
    created_date: datetime
    modified_date: datetime
    status: bool

    model_config = {
        "collection": "semicon_manufacturer"
    }

