from flask import Blueprint, jsonify, make_response

from lib.blacklist import Blacklist

api_blacklist_blueprint = Blueprint('api_blacklist', __name__, url_prefix='/api')


@api_blacklist_blueprint.route('/blacklist')
def blacklist():
    return make_response(jsonify(Blacklist().get()), 200)


@api_blacklist_blueprint.route('/blacklist', methods=['POST'])
def blacklist_post():
    return Blacklist().post()
