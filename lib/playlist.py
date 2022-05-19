from dataclasses import dataclass
from flask import request, jsonify, abort

from lib.mongo import MongoAuthentication


@dataclass
class PlaylistDTO:
    id: str
    creator: str
    title: str


class Playlist:
    def get(self, creator=None):
        try:
            client = MongoAuthentication()
            collection = client.connect()
            playlist_collection = collection.playlist

            playlists = playlist_collection.find({
                "creator": creator
            } if creator else {})

            return [
                PlaylistDTO(
                    id=playlist['spotify_id'],
                    creator=playlist['creator'],
                    title=playlist['title']
                ) for playlist in playlists
            ]
        except Exception as error:
            return str(error)

    def post(self):
        spotify_id = request.json.get('spotify_id')
        creator = request.json.get('creator')
        title = request.json.get('title')

        if not request.json or not spotify_id:
            abort(400)

        try:
            client = MongoAuthentication()
            collection = client.connect()
            playlist_collection = collection.playlist

            existing = playlist_collection.find_one({
                'spotify_id': spotify_id
            })

            if existing:
                return jsonify({
                    "message": f"Playlist with id {spotify_id} already exists"
                })

            playlist_collection.insert_one({
                'spotify_id': spotify_id,
                'creator': creator,
                'title': title
            })

            return jsonify({
                'spotify_id': spotify_id,
                'creator': creator,
                'title': title
            }), 201
        except Exception as error:
            return jsonify({
                "message": str(error)
            }), 500
