from flask import Blueprint, request, jsonify
from extensions import db
from models import BusinessPost, BusinessPostMedia, Business

business_bp = Blueprint('business', __name__)


@business_bp.route('/profile/<int:user_id>')
def profile(user_id):
    business = Business.query.filter_by(user_id=user_id).first()
    if not business:
        return jsonify({"error": "Business profile not found"}), 404
    return jsonify({
        "id": business.id,
        "business_name": business.business_name,
        "services": business.services,
        "location": business.location,
        "description": business.description,
        "status": business.status,
        "verification_status": business.verification_status,
        "blue_tick": business.blue_tick,
        "payment_status": business.payment_status
    })


@business_bp.route('/my-posts/<int:business_user_id>')
def my_posts(business_user_id):
    posts = BusinessPost.query.filter_by(business_id=business_user_id).order_by(BusinessPost.id.desc()).all()
    result = []
    for p in posts:
        result.append({
            "id": p.id,
            "title": p.title,
            "description": p.description,
            "likes_count": p.likes_count,
            "views_count": p.views_count,
            "created_at": p.created_at.strftime("%d %b %Y, %H:%M"),
            "media": [{"url": m.url, "type": m.type} for m in p.media]
        })
    return jsonify(result)

from flask import Blueprint, jsonify, request

business_bp = Blueprint('business', __name__)

@business_bp.route('/')
def home():
    return jsonify({"message": "Business home"})


@business_bp.route('/create-post', methods=['POST'])
def create_post():
    return jsonify({"message": "Business post created"})