from flask import request, jsonify

from models import Blacklist
from app import db


def insert():
    spotify_id = request.form.get('id')
    id_type = request.form.get('type')

    if not spotify_id and id_type:
        return jsonify('Data is not correct.')

    try:
        blacklist = Blacklist.query.filter_by(spotify_id=spotify_id)
        blacklist.seed(0)

        if blacklist:
            return jsonify('{} already exists'.format(id_type))

        item = Blacklist(
            spotify_id=spotify_id,
            id_type=id_type
        )
        db.session.add(item)
        db.session.commit()

        return jsonify({
            'id', spotify_id,
            'type', id_type
        })
    except Exception as e:
        return (str(e))