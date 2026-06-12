from flask import Blueprint, request, jsonify
from extensions import db
from models import Question, User

farmer_bp = Blueprint('farmer', __name__)


# ==========================================
# 1. FARMER SUBMITS A NEW QUESTION
# ==========================================
@farmer_bp.route('/ask-question', methods=['POST'])
def ask_question():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    user_id = data.get('user_id')
    question_text = data.get('question')
    category = data.get('category', 'General')

    if not user_id or not question_text:
        return jsonify({"error": "Missing required fields (user_id or question)"}), 400

    user = User.query.filter_by(id=user_id, role='farmer').first()
    if not user:
        return jsonify({"error": "Farmer account not found"}), 404

    new_question = Question(
        farmer_id=user.id,
        question=question_text,
        category=category,
        status="pending"
    )
    db.session.add(new_question)
    db.session.commit()
    return jsonify({"message": "Question submitted successfully!", "id": new_question.id}), 201


# ==========================================
# 2. FETCH HISTORY FOR FARMER DASHBOARD
# ==========================================
@farmer_bp.route('/my-questions/<int:farmer_id>', methods=['GET'])
def get_farmer_questions(farmer_id):
    questions = Question.query.filter_by(farmer_id=farmer_id).order_by(Question.id.desc()).all()

    result = []
    for q in questions:
        # FIX: Python uses .upper(), not JS-style .toUpperCase()
        norm_status = q.status.upper() if q.status else "PENDING"

        result.append({
            "id": q.id,
            "question": q.question,
            "category": q.category,
            "status": norm_status,
            "answer": q.answer if q.answer else None,
            "answer_verified": q.answer_verified,
            "created_at": q.created_at.strftime("%d %b %Y, %H:%M") if q.created_at else ""
        })

    return jsonify(result), 200