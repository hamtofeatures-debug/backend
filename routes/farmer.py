from flask import Blueprint, request, jsonify, session, redirect, url_for
from extensions import db
from models import Question, User, QuestionPhoto, Post, PostPhoto
from werkzeug.utils import secure_filename
import os

farmer_bp = Blueprint('farmer', __name__)


# ==========================================
# 1. FARMER SUBMITS A QUESTION OR A COMMUNITY POST
# ==========================================
@farmer_bp.route('/ask-question', methods=['POST'])
def ask_question():
    if session.get('role') != 'farmer':
        return redirect(url_for('index'))

    user_id = session['user_id']
    data = request.form

    # --- Handle "Ask an Expert" form ---
    if data.get('question_text'):
        question_text = data.get('question_text', '').strip()
        category = data.get('category', 'General')

        if not question_text:
            return redirect(url_for('farmer_dashboard_page'))

        new_question = Question(
            farmer_id=user_id,
            question=question_text,
            category=category,
            status="pending"
        )
        db.session.add(new_question)
        db.session.flush()

        for photo in request.files.getlist('photos'):
            if photo and photo.filename:
                filename = secure_filename(f"q{new_question.id}_{photo.filename}")
                filepath = os.path.join('static', 'uploads', 'questions', filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                photo.save(filepath)
                db.session.add(QuestionPhoto(
                    question_id=new_question.id,
                    url=f"/static/uploads/questions/{filename}"
                ))

        db.session.commit()
        return redirect(url_for('farmer_dashboard_page'))

    # --- Handle "Create a Post" form ---
    elif data.get('post_text'):
        text = data.get('post_text', '').strip()

        if not text:
            return redirect(url_for('farmer_dashboard_page'))

        new_post = Post(farmer_id=user_id, text=text)
        db.session.add(new_post)
        db.session.flush()

        for photo in request.files.getlist('photos'):
            if photo and photo.filename:
                filename = secure_filename(f"post{new_post.id}_{photo.filename}")
                filepath = os.path.join('static', 'uploads', 'posts', filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                photo.save(filepath)
                db.session.add(PostPhoto(
                    post_id=new_post.id,
                    url=f"/static/uploads/posts/{filename}"
                ))

        db.session.commit()
        return redirect(url_for('farmer_dashboard_page'))

    # --- Neither field was provided ---
    return redirect(url_for('farmer_dashboard_page'))


# ==========================================
# 2. FETCH HISTORY FOR FARMER DASHBOARD
# ==========================================
@farmer_bp.route('/my-questions/<int:farmer_id>', methods=['GET'])
def get_farmer_questions(farmer_id):
    questions = Question.query.filter_by(farmer_id=farmer_id).order_by(Question.id.desc()).all()
    result = []
    for q in questions:
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