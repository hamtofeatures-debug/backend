from flask import Blueprint, request, jsonify
from extensions import db
from models import User, Farmer, Expert, Question
from datetime import datetime

expert_bp = Blueprint('expert', __name__)

@expert_bp.route('/')
def home():
    return jsonify({"message": "Welcome to Expert Dashboard!"})

@expert_bp.route('/my-questions/<int:expert_id>')
def my_questions(expert_id):
    questions = Question.query.filter_by(assigned_expert_id=expert_id).order_by(Question.id.desc()).all()
    result = []
    for q in questions:
        farmer = User.query.get(q.farmer_id)
        result.append({
            "id": q.id, "question": q.question, "category": q.category,
            "status": q.status,
            "farmer_name": farmer.fullname if farmer else "Unknown",
            "farmer_id": q.farmer_id,
            "answer": q.answer,
            "answer_verified": q.answer_verified,
            "admin_note": q.admin_note,
            "created_at": q.created_at.strftime("%d %b %Y, %H:%M") if q.created_at else "",
            "answered_at": q.answered_at.strftime("%d %b %Y, %H:%M") if q.answered_at else None
        })
    return jsonify(result)

@expert_bp.route('/answer/<int:qid>', methods=['POST'])
def answer_question(qid):
    data = request.get_json()
    answer = data.get('answer', '').strip()
    expert_id = data.get('expert_id')
    if not answer:
        return jsonify({"error": "Answer is required"}), 400
    q = Question.query.get(qid)
    if not q:
        return jsonify({"error": "Question not found"}), 404
    if q.assigned_expert_id != int(expert_id):
        return jsonify({"error": "Not authorized to answer this question"}), 403
    q.answer = answer
    q.status = 'pending_review'
    q.answer_verified = False
    q.answered_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"message": "Answer submitted for admin review!"}), 200

@expert_bp.route('/profile/<int:user_id>')
def profile(user_id):
    user = User.query.filter_by(id=user_id, role='expert').first()
    if not user:
        return jsonify({"error": "Expert not found"}), 404
    expert = Expert.query.filter_by(user_id=user.id).first()
    return jsonify({
        "fullname": user.fullname, "email": user.email, "phone": user.phone,
        "specialization": expert.specialization if expert else "",
        "qualification": expert.qualification if expert else "",
        "experience": expert.experience if expert else 0
    })