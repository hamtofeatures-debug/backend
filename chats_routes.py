from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for
from extensions import db
from models import User, ChatMessage
from datetime import datetime

chat_bp = Blueprint('chat', __name__)


# ── Chat page (the HTML you already have) ──
@chat_bp.route('/chat')
def chat_page():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    current_user = User.query.get(user_id)

    # Only verified users can access chat
    if not current_user.blue_tick:
        return redirect(f'/{current_user.role}/dashboard')

    # Show all OTHER verified users in the sidebar
    verified_users = User.query.filter(
        User.blue_tick == True,
        User.id != user_id
    ).order_by(User.fullname).all()

    return render_template('chat.html',
                           current_user=current_user,
                           verified_users=verified_users)


# ── Get messages between current user and another user ──
@chat_bp.route('/api/messages/<int:other_user_id>')
def get_messages(other_user_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    # Mark messages from the other user as read
    ChatMessage.query.filter_by(
        sender_id=other_user_id,
        receiver_id=user_id,
        is_read=False
    ).update({'is_read': True})
    db.session.commit()

    # Fetch the full conversation
    messages = ChatMessage.query.filter(
        db.or_(
            db.and_(ChatMessage.sender_id == user_id,
                    ChatMessage.receiver_id == other_user_id),
            db.and_(ChatMessage.sender_id == other_user_id,
                    ChatMessage.receiver_id == user_id)
        )
    ).order_by(ChatMessage.created_at.asc()).all()

    return jsonify([{
        'id':         m.id,
        'sender_id':  m.sender_id,
        'content':    m.content,
        'is_read':    m.is_read,
        'created_at': m.created_at.strftime('%d %b %Y, %H:%M')
    } for m in messages])


# ── Send a message ──
@chat_bp.route('/api/messages/send', methods=['POST'])
def send_message():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    data        = request.get_json()
    receiver_id = data.get('receiver_id')
    content     = data.get('content', '').strip()

    if not receiver_id or not content:
        return jsonify({'error': 'Missing receiver_id or content'}), 400

    receiver = User.query.get(receiver_id)
    if not receiver or not receiver.blue_tick:
        return jsonify({'error': 'Recipient not found or not verified'}), 404

    msg = ChatMessage(
        sender_id=user_id,
        receiver_id=receiver_id,
        content=content
    )
    db.session.add(msg)
    db.session.commit()

    return jsonify({'message': 'Sent', 'id': msg.id}), 201


# ── Unread counts for sidebar badges ──
@chat_bp.route('/api/messages/unread-counts')
def unread_counts():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({}), 401

    rows = db.session.query(
        ChatMessage.sender_id,
        db.func.count(ChatMessage.id).label('cnt')
    ).filter_by(
        receiver_id=user_id,
        is_read=False
    ).group_by(ChatMessage.sender_id).all()

    return jsonify({str(row.sender_id): row.cnt for row in rows})