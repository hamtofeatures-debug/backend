from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for
from extensions import db
from models import User, ChatMessage, encrypt_message, decrypt_message
from datetime import datetime
from sqlalchemy import or_, and_

chat_bp = Blueprint('chat', __name__)


def get_verified_user():
    """Returns current user only if logged in AND verified. Else None."""
    user_id = session.get('user_id')
    if not user_id:
        return None
    user = User.query.get(user_id)
    if not user or not user.blue_tick:
        return None
    return user


# ── Chat page ──
@chat_bp.route('/chat')
def chat_page():
    user = get_verified_user()
    if not user:
        # Not verified — send back to their dashboard
        role = session.get('role', 'farmer')
        return redirect(f'/{role}/dashboard')

    # Only other verified users, excluding admin
    verified_users = User.query.filter(
        User.blue_tick == True,
        User.id        != user.id,
        User.role      != 'admin'          # admin excluded
    ).order_by(User.fullname).all()

    return render_template('chat.html',
                           current_user  = user,
                           verified_users = verified_users)


# ── Get messages — only between the two participants ──
@chat_bp.route('/api/messages/<int:other_id>')
def get_messages(other_id):
    user = get_verified_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    # Verify the other person is also verified and not admin
    other = User.query.get(other_id)
    if not other or not other.blue_tick or other.role == 'admin':
        return jsonify({'error': 'Invalid recipient'}), 403

    # Mark messages from other person as read
    ChatMessage.query.filter_by(
        sender_id   = other_id,
        receiver_id = user.id,
        is_read     = False
    ).update({'is_read': True})
    db.session.commit()

    # Fetch ONLY messages between these two users — no one else
    messages = ChatMessage.query.filter(
        or_(
            and_(ChatMessage.sender_id   == user.id,
                 ChatMessage.receiver_id == other_id),
            and_(ChatMessage.sender_id   == other_id,
                 ChatMessage.receiver_id == user.id)
        )
    ).order_by(ChatMessage.created_at.asc()).all()

    return jsonify([{
        'id':         m.id,
        'sender_id':  m.sender_id,
        'content':    decrypt_message(m.content),   # decrypt on the way out
        'is_read':    m.is_read,
        'created_at': m.created_at.strftime('%d %b %Y, %H:%M')
    } for m in messages])


# ── Send a message ──
@chat_bp.route('/api/messages/send', methods=['POST'])
def send_message():
    user = get_verified_user()
    if not user:
        return jsonify({'error': 'Unauthorized — must be verified'}), 401

    data        = request.get_json(silent=True) or {}
    receiver_id = data.get('receiver_id')
    content     = data.get('content', '').strip()

    if not receiver_id or not content:
        return jsonify({'error': 'Missing receiver or message'}), 400

    # Receiver must be verified and not admin
    receiver = User.query.get(receiver_id)
    if not receiver:
        return jsonify({'error': 'Recipient not found'}), 404
    if not receiver.blue_tick:
        return jsonify({'error': 'Recipient is not verified'}), 403
    if receiver.role == 'admin':
        return jsonify({'error': 'Cannot message admin'}), 403
    if receiver.id == user.id:
        return jsonify({'error': 'Cannot message yourself'}), 400

    # Encrypt before saving
    msg = ChatMessage(
        sender_id   = user.id,
        receiver_id = receiver_id,
        content     = encrypt_message(content)   # stored encrypted in DB
    )
    db.session.add(msg)
    db.session.commit()

    return jsonify({'message': 'Sent', 'id': msg.id}), 201


# ── Unread counts — only from verified non-admin users ──
@chat_bp.route('/api/messages/unread-counts')
def unread_counts():
    user = get_verified_user()
    if not user:
        return jsonify({}), 401

    rows = db.session.query(
        ChatMessage.sender_id,
        db.func.count(ChatMessage.id).label('cnt')
    ).join(
        User, User.id == ChatMessage.sender_id
    ).filter(
        ChatMessage.receiver_id == user.id,
        ChatMessage.is_read     == False,
        User.blue_tick          == True,
        User.role               != 'admin'
    ).group_by(ChatMessage.sender_id).all()

    return jsonify({str(row.sender_id): row.cnt for row in rows})