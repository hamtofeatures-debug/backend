from flask import Blueprint, request, jsonify
from extensions import db
from models import User, Question, Announcement, AnnouncementReaction, ExpertRating, Articles

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/')
def home():
    return jsonify({"message": "Welcome to Admin Dashboard!"})

# ── USERS ──
@admin_bp.route('/user')
def all_users():
    users = User.query.all()
    return jsonify([{"id": u.id, "fullname": u.fullname, "email": u.email, "role": u.role} for u in users])

@admin_bp.route('/experts')
def get_experts():
    experts = User.query.filter_by(role='expert').all()
    return jsonify([{"id": e.id, "fullname": e.fullname, "email": e.email} for e in experts])

@admin_bp.route('/farmers')
def get_farmers():
    farmers = User.query.filter_by(role='farmer').all()
    return jsonify([{"id": f.id, "fullname": f.fullname, "email": f.email} for f in farmers])

# ── QUESTIONS ──
@admin_bp.route('/questions')
def all_questions():
    questions = Question.query.order_by(Question.id.desc()).all()
    return jsonify([_fmt_q(q) for q in questions])

@admin_bp.route('/public-qa')
def public_qa():
    questions = Question.query.filter_by(status='answered', answer_verified=True).order_by(Question.id.desc()).all()
    return jsonify([_fmt_q(q) for q in questions])

@admin_bp.route('/pending-review')
def pending_review():
    questions = Question.query.filter_by(status='pending_review').order_by(Question.id.desc()).all()
    return jsonify([_fmt_q(q) for q in questions])

def _fmt_q(q):
    farmer = User.query.get(q.farmer_id)
    expert = User.query.get(q.assigned_expert_id) if q.assigned_expert_id else None
    return {
        "id": q.id, "question": q.question, "category": q.category,
        "status": q.status,
        "farmer_name": farmer.fullname if farmer else "Unknown",
        "farmer_id": q.farmer_id,
        "assigned_expert": expert.fullname if expert else None,
        "assigned_expert_id": q.assigned_expert_id,
        "answer": q.answer, "answer_verified": q.answer_verified,
        "admin_note": q.admin_note,
        "created_at": q.created_at.strftime("%d %b %Y, %H:%M") if q.created_at else "",
        "answered_at": q.answered_at.strftime("%d %b %Y, %H:%M") if q.answered_at else None
    }

@admin_bp.route('/questions', methods=['POST'])
def post_question():
    data = request.get_json()
    farmer_id = data.get('farmer_id')
    question_text = data.get('question')
    category = data.get('category', 'General')
    if not farmer_id or not question_text:
        return jsonify({"error": "farmer_id and question required"}), 400
    farmer = User.query.filter_by(id=farmer_id, role='farmer').first()
    if not farmer:
        return jsonify({"error": "Farmer not found"}), 404
    q = Question(farmer_id=farmer_id, question=question_text, category=category, status='pending')
    db.session.add(q)
    db.session.commit()
    return jsonify({"message": "Question posted!", "id": q.id}), 201

@admin_bp.route('/questions/<int:qid>/assign', methods=['POST'])
def assign_question(qid):
    data = request.get_json()
    expert_id = data.get('expert_id')
    expert = User.query.filter_by(id=expert_id, role='expert').first()
    if not expert:
        return jsonify({"error": "Expert not found"}), 404
    q = Question.query.get(qid)
    if not q:
        return jsonify({"error": "Question not found"}), 404
    q.assigned_expert_id = expert_id
    q.status = 'assigned'
    q.admin_note = None
    db.session.commit()
    return jsonify({"message": f"Assigned to {expert.fullname}"}), 200

@admin_bp.route('/questions/<int:qid>/approve', methods=['POST'])
def approve_answer(qid):
    q = Question.query.get(qid)
    if not q:
        return jsonify({"error": "Question not found"}), 404
    q.status = 'answered'
    q.answer_verified = True
    q.admin_note = None
    db.session.commit()
    return jsonify({"message": "Answer approved and published!"}), 200

@admin_bp.route('/questions/<int:qid>/reject', methods=['POST'])
def reject_answer(qid):
    data = request.get_json()
    note = data.get('note', 'Please revise your answer.')
    q = Question.query.get(qid)
    if not q:
        return jsonify({"error": "Question not found"}), 404
    q.status = 'assigned'
    q.answer = None
    q.answer_verified = False
    q.admin_note = note
    db.session.commit()
    return jsonify({"message": "Answer rejected and sent back to expert."}), 200

# ── ANNOUNCEMENTS ──
@admin_bp.route('/announcements')
def get_announcements():
    user_id = request.args.get('user_id', type=int)
    announcements = Announcement.query.order_by(Announcement.id.desc()).all()
    result = []
    for a in announcements:
        admin = User.query.get(a.admin_id)
        user_reaction = None
        if user_id:
            r = AnnouncementReaction.query.filter_by(announcement_id=a.id, user_id=user_id).first()
            if r:
                user_reaction = r.reaction
        result.append({
            "id": a.id, "title": a.title, "body": a.body,
            "category": a.category,
            "likes": a.likes, "dislikes": a.dislikes,
            "posted_by": admin.fullname if admin else "Admin",
            "created_at": a.created_at.strftime("%d %b %Y, %H:%M"),
            "user_reaction": user_reaction
        })
    return jsonify(result)

@admin_bp.route('/announcements', methods=['POST'])
def post_announcement():
    data = request.get_json()
    admin_id = data.get('admin_id')
    title = data.get('title', '').strip()
    body = data.get('body', '').strip()
    category = data.get('category', 'General')
    if not title or not body:
        return jsonify({"error": "Title and body are required"}), 400
    a = Announcement(admin_id=admin_id, title=title, body=body, category=category)
    db.session.add(a)
    db.session.commit()
    return jsonify({"message": "Announcement posted!", "id": a.id}), 201

@admin_bp.route('/announcements/<int:aid>/react', methods=['POST'])
def react_announcement(aid):
    data = request.get_json()
    user_id = data.get('user_id')
    reaction = data.get('reaction')  # 'like' or 'dislike'
    if not user_id or reaction not in ['like', 'dislike']:
        return jsonify({"error": "Invalid request"}), 400
    a = Announcement.query.get(aid)
    if not a:
        return jsonify({"error": "Announcement not found"}), 404
    existing = AnnouncementReaction.query.filter_by(announcement_id=aid, user_id=user_id).first()
    if existing:
        if existing.reaction == reaction:
            # Undo reaction
            if reaction == 'like': a.likes = max(0, a.likes - 1)
            else: a.dislikes = max(0, a.dislikes - 1)
            db.session.delete(existing)
            db.session.commit()
            return jsonify({"message": "Reaction removed", "likes": a.likes, "dislikes": a.dislikes, "user_reaction": None}), 200
        else:
            # Switch reaction
            if existing.reaction == 'like': a.likes = max(0, a.likes - 1)
            else: a.dislikes = max(0, a.dislikes - 1)
            existing.reaction = reaction
            if reaction == 'like': a.likes += 1
            else: a.dislikes += 1
            db.session.commit()
            return jsonify({"message": "Reaction updated", "likes": a.likes, "dislikes": a.dislikes, "user_reaction": reaction}), 200
    # New reaction
    r = AnnouncementReaction(announcement_id=aid, user_id=user_id, reaction=reaction)
    db.session.add(r)
    if reaction == 'like': a.likes += 1
    else: a.dislikes += 1
    db.session.commit()
    return jsonify({"message": "Reaction recorded", "likes": a.likes, "dislikes": a.dislikes, "user_reaction": reaction}), 200

@admin_bp.route('/announcements/<int:aid>', methods=['DELETE'])
def delete_announcement(aid):
    a = Announcement.query.get(aid)
    if not a:
        return jsonify({"error": "Not found"}), 404
    AnnouncementReaction.query.filter_by(announcement_id=aid).delete()
    db.session.delete(a)
    db.session.commit()
    return jsonify({"message": "Deleted"}), 200

# ── EXPERT RANKINGS ──
@admin_bp.route('/expert-rankings')
def expert_rankings():
    experts = User.query.filter_by(role='expert').all()
    result = []
    for e in experts:
        answered = Question.query.filter_by(assigned_expert_id=e.id, status='answered', answer_verified=True).count()
        ratings = ExpertRating.query.filter_by(expert_id=e.id).all()
        avg_rating = round(sum(r.stars for r in ratings) / len(ratings), 1) if ratings else 0
        rating_count = len(ratings)
        result.append({
            "id": e.id, "fullname": e.fullname, "email": e.email,
            "answered": answered,
            "avg_rating": avg_rating,
            "rating_count": rating_count,
            "score": (answered * 10) + (avg_rating * 20)
        })
    result.sort(key=lambda x: x['score'], reverse=True)
    for i, e in enumerate(result):
        e['rank'] = i + 1
    return jsonify(result)

@admin_bp.route('/rate-expert', methods=['POST'])
def rate_expert():
    data = request.get_json()
    expert_id = data.get('expert_id')
    rater_id = data.get('rater_id')
    stars = data.get('stars')
    question_id = data.get('question_id')
    if not expert_id or not rater_id or not stars:
        return jsonify({"error": "Missing fields"}), 400
    if not (1 <= int(stars) <= 5):
        return jsonify({"error": "Stars must be 1-5"}), 400
    existing = ExpertRating.query.filter_by(expert_id=expert_id, rater_id=rater_id, question_id=question_id).first()
    if existing:
        existing.stars = stars
    else:
        r = ExpertRating(expert_id=expert_id, rater_id=rater_id, stars=stars, question_id=question_id)
        db.session.add(r)
    db.session.commit()
    return jsonify({"message": "Rating submitted!"}), 200

@admin_bp.route('/publish-question/<int:question_id>', methods=['POST'])
def publish_question(question_id):
    question = Question.query.get_or_404(question_id)
    question.is_published = True
    db.session.commit()
    return jsonify({"message": "Question published successfully!"}), 200



@admin_bp.route('/admin/pending-articles', methods=['GET'])
def get_pending_articles():
    # Use 'Question' instead of 'Articles'
    pending = Question.query.filter_by(is_approved=False).all() 
    return jsonify([{'id': q.id, 'title': q.question, 'expert_id': q.assigned_expert_id} for q in pending])

@admin_bp.route('/admin/articles/<int:id>/approve', methods=['POST'])
def approve_article(id):
    # Use 'Question' instead of 'Articles'
    question = Question.query.get_or_404(id)
    question.is_approved = True
    db.session.commit()
    return jsonify({'message': 'Article approved and now visible to farmers!'}), 200