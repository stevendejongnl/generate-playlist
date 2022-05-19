import os
from dataclasses import dataclass
from pymongo import MongoClient


@dataclass
class MongoAuthentication:
    client: MongoClient = None
    username: str = os.getenv("MONGO_USERNAME")
    password: str = os.getenv("MONGO_PASSWORD")
    host: str = os.getenv("MONGO_HOST")
    database: str = os.getenv("MONGO_DATABASE")

    def string(self):
        return f"mongodb+srv://{self.username}:{self.password}@{self.host}/{self.database}?retryWrites=true&w=majority"

    def connect(self):
        self.client = MongoClient(self.string())
        return self.client.playlistgenerator
