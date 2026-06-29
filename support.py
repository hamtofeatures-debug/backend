from flask import Blueprint, request, jsonify, session
from extensions import db
from models import SupportMessage, SupportReply

support_bp = Blueprint('support', __name__)

@support_bp.route('/my-thread', methods=['GET'])
def my_thread():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401

    # Get the latest open thread for this user
    msg = SupportMessage.query.filter_by(
        user_id=user_id, is_closed=False
    ).order_by(SupportMessage.created_at.desc()).first()

    if not msg:
        return jsonify({'thread': None})

    return jsonify({
        'thread': {
            'id': msg.id,
            'message': msg.message,
            'status': msg.status,
            'is_closed': msg.is_closed,
            'created_at': msg.created_at.strftime('%d %b %Y %H:%M'),
            'replies': [
                {
                    'reply': r.reply,
                    'admin': r.admin.fullname,
                    'created_at': r.created_at.strftime('%d %b %Y %H:%M')
                } for r in msg.replies
            ]
        }
    })


@support_bp.route('/send', methods=['POST'])
def send_support_message():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401

    data    = request.get_json(silent=True) or {}
    message = data.get('message', '').strip()
    if not message:
        return jsonify({'error': 'Message is empty'}), 400

    # Check if user already has an open thread
    existing = SupportMessage.query.filter_by(
        user_id=user_id, is_closed=False
    ).first()
    if existing:
        return jsonify({'error': 'You already have an open support thread'}), 400

    msg = SupportMessage(user_id=user_id, message=message, status='Unread')
    db.session.add(msg)
    db.session.commit()
    return jsonify({'message': 'Message sent!', 'id': msg.id}), 200