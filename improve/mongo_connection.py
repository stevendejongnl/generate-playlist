from dotenv import load_dotenv

from mongo_authentication import MongoAuthentication

load_dotenv()

client = MongoAuthentication()
collection = client.connect()
blacklist_collection = collection.blacklist

blacklist = [
    {
        "spotify_id": "6rDf9PafRIMPaS76EAqKBY",
        "id_type": "track",
        "title": "Elle e(s)t moi",
        "artist": "Orian"
    },
    {
        "spotify_id": "1NtF3uHCJ2MyhKvqdFm2T9",
        "id_type": "track",
        "title": "Poedersneeuw 4.0",
        "artist": "Never Surrender"
    }
]

# blacklist_collection.insert_many(blacklist)

blacklist_collection.read_many()
