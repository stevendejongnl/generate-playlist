from app import db


class Blacklist(db.Model):
    __tablename__ = 'blacklist'

    id = db.Column(db.Integer, primary_key=True)
    spotify_id = db.Column(db.String())

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
