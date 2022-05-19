from dataclasses import dataclass
from typing import Optional

from flask import request, jsonify, abort

from lib.mongo import MongoAuthentication


@dataclass
class SpotifyBlacklistDTO:
    id: str
    type: str
    title: str
    artist: Optional[str]


class Blacklist:
    def get(self, id_type=None):
        try:
            client = MongoAuthentication()
            collection = client.connect()
            blacklist_collection = collection.blacklist

            blacklist = blacklist_collection.find({
                "id_type": id_type
            } if id_type else {})

            return [
                SpotifyBlacklistDTO(
                    id=item['spotify_id'],
                    type=item['id_type'],
                    title=item['title'],
                    artist=item['artist']
                ) for item in blacklist
            ]
        except Exception as error:
            return str(error)

    def post(self):
        spotify_id = request.json.get('spotify_id')
        id_type = request.json.get('id_type')
        title = request.json.get('title')
        artist = request.json.get('artist')

        if not request.json or not spotify_id and not id_type:
            abort(400)

        try:
            client = MongoAuthentication()
            collection = client.connect()
            blacklist_collection = collection.blacklist

            existing = blacklist_collection.find_one({
                'spotify_id': spotify_id,
                'id_type': id_type
            })

            if existing:
                return jsonify({
                    "message": f"Song with id {spotify_id} and type {id_type} already exists in blacklist"
                })

            blacklist_collection.insert_one({
                'spotify_id': spotify_id,
                'id_type': id_type,
                'title': title,
                'artist': artist
            })

            return jsonify({
                'spotify_id': spotify_id,
                'id_type': id_type,
                'title': title,
                'artist': artist
            }), 201
        except Exception as error:
            return jsonify({
                "message": str(error)
            }), 500
