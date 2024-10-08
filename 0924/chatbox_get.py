# chatbox_get.py

from flask import Blueprint, jsonify

def get_blueprint(messages):
    bp = Blueprint('get_blueprint', __name__)

    @bp.route('/get_messages', methods=['GET'])
    def get_messages():
        return jsonify({'messages': messages})

    return bp
