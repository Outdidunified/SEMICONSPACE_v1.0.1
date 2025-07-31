import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from odmantic import AIOEngine

load_dotenv()

mongo_url = os.getenv("MONGODB_URL")

client = AsyncIOMotorClient(mongo_url, uuidRepresentation="standard")

engine = AIOEngine(client=client, database="product_service")
