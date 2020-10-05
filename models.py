import json

from app import db
from flask_seeder import Seeder, Faker, generator


class Blacklist(db.Model):
    __tablename__ = 'blacklist'

    id = db.Column(db.Integer, primary_key=True)
    spotify_id = db.Column(db.String(), unique=True)
    id_type = db.Column(db.String())

    def __init__(self, spotify_id, id_type):
        self.spotify_id = spotify_id
        self.id_type = id_type

    def __repr__(self):
        return '<id {}>'.format(self.id)

    def serialize(self):
        return {
            'id': self.id,
            'spotify_id': self.spotify_id,
            'id_type': self.id_type
        }


class BlacklistSeeder(Seeder):
    def run(self):
        with open('seeds/blacklist.json') as blacklist_file:
            blacklist = json.load(blacklist_file)

            for item in blacklist:
                self.db.session.add(Faker(cls=Blacklist, init=item).create(1))
