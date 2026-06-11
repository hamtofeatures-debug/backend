from flask import Blueprint, request, jsonify, render_template
from extensions import db
from models import Question, User

farmer_bp = Blueprint('farmer', __name__)

@farmer_bp.route('/')
def home():
    return render_template('farmer_dashboard.html')

# ==========================================
# 1. FARMER SUBMITS A NEW QUESTION
# ==========================================
@farmer_bp.route('/ask-question', methods=['POST'])
def ask_question():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    user_id = data.get('user_id')  # ID of the logged-in user
    question_text = data.get('question')
    category = data.get('category', 'General') # Defaults to 'General' if left empty

    if not user_id or not question_text:
        return jsonify({"error": "Missing required fields (user_id or question)"}), 400

    # Verify the user exists and is actually a farmer
    user = User.query.filter_by(id=user_id, role='farmer').first()
    if not user:
        return jsonify({"error": "Farmer account not found"}), 404

    # Create the question entry mapping accurately to your models.py properties
    new_question = Question(
        farmer_id=user.id,        # Matches ForeignKey('user.id')
        question=question_text,   # Matches db.Column(db.Text)
        category=category,        # Matches db.Column(db.String)
        status="PENDING"          # FIX: Uppercase "PENDING" to keep database status unified
    )

    db.session.add(new_question)
    db.session.commit()

    return jsonify({"message": "Question submitted successfully!", "id": new_question.id}), 201


# ==========================================
# 2. NEW EDIT: FETCH HISTORY FOR FARMER DASHBOARD
# ==========================================
@farmer_bp.route('/my-questions/<int:farmer_id>', methods=['GET'])
def get_farmer_questions(farmer_id):
    # Fetch all questions submitted by this specific farmer
    questions = Question.query.filter_by(farmer_id=farmer_id).order_by(Question.id.desc()).all()
    
    result = []
    for q in questions:
        # Normalize status to uppercase safely
        norm_status = q.status.toUpperCase() if q.status else "PENDING"
        
        result.append({
            "id": q.id,
            "question": q.question,
            "category": q.category,
            "status": norm_status,
            # If the expert answered it, display the live answer text right here
            "answer": q.answer if q.answer else None,
            "is_verified": getattr(q, 'is_verified', False),
            "created_at": q.created_at.strftime("%d %b %Y, %H:%M") if q.created_at else ""
        })
        
    return jsonify(result), 200