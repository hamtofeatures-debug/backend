from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from config import Config
from extensions import db
from models import User, Question, ExpertRating, Announcement, AnnouncementReaction, Business, Articles
from sqlalchemy import func
import os

# Explicitly import the blueprints directly from their route files
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.expert import expert_bp
from routes.farmer import farmer_bp
from routes.business import business_bp

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(expert_bp, url_prefix='/expert')
app.register_blueprint(farmer_bp, url_prefix='/farmer')
app.register_blueprint(business_bp, url_prefix='/business')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login')
def login_page():
    return render_template('login.html')


@app.route('/register')
def register_page():
    return render_template('register.html')


# =====================================================================
# DASHBOARD VIEW ROUTES (one per role, separate templates)
# =====================================================================

@app.route('/admin/dashboard')
def admin_dashboard_page():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))

    user = User.query.get(session['user_id'])

    stats = {
        'users': User.query.count(),
        'farmers': User.query.filter_by(role='farmer').count(),
        'experts': User.query.filter_by(role='expert').count(),
        'questions': Question.query.count(),
        'pending': Question.query.filter_by(status='pending').count(),
        'published': Question.query.filter_by(is_published=True).count(),
    }

    return render_template('admin_dashboard.html', current_user=user, stats=stats)


@app.route('/farmer/dashboard')
def farmer_dashboard_page():
    if session.get('role') != 'farmer':
        return redirect(url_for('index'))

    user = User.query.get(session['user_id'])

    my_questions = Question.query.filter_by(farmer_id=user.id).all()
    stats = {
        'questions': len(my_questions),
        'answered': len([q for q in my_questions if q.answer_verified]),
        'pending': len([q for q in my_questions if not q.answer_verified]),
    }

    return render_template('farmer_dashboard.html', current_user=user, stats=stats)


@app.route('/farmer/public-qa')
def farmer_public_qa_page():
    if session.get('role') != 'farmer':
        return redirect(url_for('index'))

    user = User.query.get(session['user_id'])

    public_qa = (Question.query
                  .filter_by(answer_verified=True)
                  .order_by(Question.answered_at.desc())
                  .all())

    return render_template(
        'farmer_public_qa.html',
        current_user=user,
        public_qa=public_qa,
        community_posts=[]
    )


@app.route('/expert/dashboard')
def expert_dashboard_page():
    if session.get('role') != 'expert':
        return redirect(url_for('index'))

    user = User.query.get(session['user_id'])

    my_articles = Articles.query.filter_by(expert_id=user.id).order_by(Articles.id.desc()).all()

    return render_template(
        'expert_dashboard.html',
        current_user=user,
        my_articles=my_articles,
        business_posts=[]
    )


@app.route('/business/dashboard')
def business_dashboard_page():
    if session.get('role') != 'business':
        return redirect(url_for('index'))

    user = User.query.get(session['user_id'])
    business = Business.query.filter_by(user_id=user.id).first()

    stats = {
        'total_posts': 0,
        'total_likes': 0,
        'total_views': 0,
    }

    return render_template(
        'business_dashboard.html',
        current_user=user,
        business=business,
        stats=stats,
        my_posts=[]
    )


# =====================================================================
# PUBLIC ENGAGEMENT & KNOWLEDGE BASE APIs
# =====================================================================

@app.route('/api/public-feed', methods=['GET'])
def get_universal_knowledge_feed():
    """
    Fetches all questions that have been answered by experts and verified
    by an admin, accompanied by compiled engagement scores.
    """
    public_questions = Question.query.filter_by(answer_verified=True).order_by(Question.id.desc()).all()

    feed_data = []
    for q in public_questions:
        farmer = User.query.get(q.farmer_id)
        expert = User.query.get(q.assigned_expert_id) if q.assigned_expert_id else None

        avg_stars = db.session.query(func.avg(ExpertRating.stars)).filter(ExpertRating.question_id == q.id).scalar() or 0

        feed_data.append({
            "id": q.id,
            "category": q.category,
            "question": q.question,
            "farmer_name": farmer.fullname if farmer else "Anonymous Farmer",
            "expert_name": expert.fullname if expert else "Agrosphere Expert",
            "answer": q.answer,
            "rating_avg": round(float(avg_stars), 1),
            "answered_at": q.answered_at.strftime("%d %b %Y, %H:%M") if q.answered_at else "Recent"
        })

    return jsonify(feed_data), 200


@app.route('/api/rate/<int:qid>', methods=['POST'])
def rate_answer(qid):
    """ Allows users to drop a 1 to 5 star rating on an answer. """
    data = request.get_json() or {}
    stars = int(data.get('stars', 0))
    rater_id = data.get('user_id') or session.get('user_id')

    if stars < 1 or stars > 5:
        return jsonify({"error": "Ratings must be between 1 and 5 stars"}), 400

    q = Question.query.get(qid)
    if not q:
        return jsonify({"error": "Question not found"}), 404

    existing_rating = ExpertRating.query.filter_by(question_id=qid, rater_id=rater_id).first()
    if existing_rating:
        existing_rating.stars = stars
    else:
        new_rating = ExpertRating(
            expert_id=q.assigned_expert_id,
            rater_id=rater_id,
            question_id=qid,
            stars=stars
        )
        db.session.add(new_rating)

    db.session.commit()
    return jsonify({"message": "Rating recorded successfully!"}), 200


@app.route('/api/expert-leaderboard', methods=['GET'])
def get_expert_leaderboard():
    """ Ranks experts by verified answers volume and average rating. """
    experts = User.query.filter_by(role='expert').all()
    leaderboard = []

    for exp in experts:
        verified_qs = Question.query.filter_by(assigned_expert_id=exp.id, answer_verified=True).all()
        total_answers = len(verified_qs)

        if total_answers > 0:
            q_ids = [q.id for q in verified_qs]
            avg_rating = db.session.query(func.avg(ExpertRating.stars)).filter(ExpertRating.question_id.in_(q_ids)).scalar() or 0
        else:
            avg_rating = 0.0

        leaderboard.append({
            "fullname": exp.fullname,
            "total_answers": total_answers,
            "rating_score": round(float(avg_rating), 1)
        })

    leaderboard.sort(key=lambda x: (x['total_answers'], x['rating_score']), reverse=True)
    return jsonify(leaderboard), 200


@app.route('/register-business')
def register_business_page():
    return render_template('register_business.html')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("Database created!")
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)