from flask import Blueprint, request, jsonify, session
from extensions import db
from models import SupportMessage

support_bp = Blueprint('support', __name__)

@support_bp.route('/support/send', methods=['POST'])
def send_support_message():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "No data received"
        }), 400

    new_message = SupportMessage(
        user_id=session['user_id'],
        message=data['message']
    )

    db.session.add(new_message)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Message sent successfully"
    })