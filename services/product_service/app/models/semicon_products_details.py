import uuid
from typing import List, Optional
from odmantic import Model, Field, EmbeddedModel
from datetime import datetime


# ======= Nested Models =======

class BaseProductNumber(EmbeddedModel):
    Id: int
    Name: str


class Series(EmbeddedModel):
    Id: int
    Name: str


class Classifications(EmbeddedModel):
    ReachStatus: Optional[str]
    RohsStatus: Optional[str]
    MoistureSensitivityLevel: Optional[str]
    ExportControlClassNumber: Optional[str]
    HtsusCode: Optional[str]


class Manufacturer(EmbeddedModel):
    Id: int
    Name: str


class PackageType(EmbeddedModel):
    Id: int
    Name: str


class Supplier(EmbeddedModel):
    Id: int
    Name: str


class StandardPricing(EmbeddedModel):
    BreakQuantity: int
    UnitPrice: float
    TotalPrice: float


class ProductVariation(EmbeddedModel):
    DigiKeyProductNumber: str
    PackageType: PackageType
    StandardPricing: List[StandardPricing]
    MarketPlace: bool
    TariffActive: bool
    Supplier: Supplier
    QuantityAvailableforPackageType: int
    MaxQuantityForDistribution: int
    MinimumOrderQuantity: int
    StandardPackage: int
    DigiReelFee: float


class Parameter(EmbeddedModel):
    ParameterId: int
    ParameterText: str
    ParameterType: str
    ValueId: str
    ValueText: str


class ChildCategory(EmbeddedModel):
    CategoryId: int
    ParentId: int
    Name: str
    ProductCount: int
    NewProductCount: int
    ImageUrl: Optional[str]
    SeoDescription: Optional[str]
    ChildCategories: List["ChildCategory"]


class Category(EmbeddedModel):
    CategoryId: int
    ParentId: int
    Name: str
    ProductCount: int
    NewProductCount: int
    ImageUrl: Optional[str]
    SeoDescription: Optional[str]
    ChildCategories: List[ChildCategory]


class ProductStatus(EmbeddedModel):
    Id: int
    Status: str


# ======= Main Model =======

class SemiconProduct(Model):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_field=True)

    semicon_part_number: str
    productId: uuid.UUID
    UnitPrice: float
    ProductUrl: Optional[str] = None
    DatasheetUrl: Optional[str] = None
    PhotoUrl: Optional[str] = None

    BackOrderNotAllowed: str
    NormallyStocking: str
    Discontinued: str
    EndOfLife: str
    Ncnr: str
    PrimaryVideoUrl: Optional[str] = None

    BaseProductNumber: BaseProductNumber
    DateLastBuyChance: Optional[datetime] = None
    ManufacturerLeadWeeks: Optional[str] = None
    ManufacturerPublicQuantity: int
    Series: Optional[Series] = Field(default=None) # type: ignore
    ShippingInfo: Optional[str] = None
    Classifications: Classifications
    categoryHierarchy: List[str] = []
    Manufacturer: Manufacturer
    Category: Category
    OtherNames: List[str] = []
    ProductStatus: ProductStatus
    modified_at: datetime = Field(default_factory=datetime.utcnow)
    modified_by: str
    status: str = "active"

    model_config = {
        "collection": "semicon_products_details",
        "arbitrary_types_allowed": True
    }
