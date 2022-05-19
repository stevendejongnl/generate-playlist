from mongo_authentication import MongoAuthentication

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

cursor = blacklist_collection.find({})

for item in cursor:
    print(item['spotify_id'])


# blacklist_collection.insert_many(blacklist)
#
# for x in blacklist_collection.find():
#     print(x)
