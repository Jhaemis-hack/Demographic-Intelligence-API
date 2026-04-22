from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from functools import lru_cache
from core import config


@lru_cache
def get_settings():
    return config.Settings()

setting = get_settings()

uri = setting.mongo_db

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))

db = client["hng14_1"]
collection = db["users"]