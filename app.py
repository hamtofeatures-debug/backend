from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from config import Config
from extensions import db
from models import User, Question, ExpertRating, Announcement, AnnouncementReaction, Business, Articles, BusinessPost, Post
from sqlalchemy import func
import os
from flask_login import LoginManager
import requests

# Explicitly import the blueprints directly from their route files
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.expert import expert_bp
from routes.farmer import farmer_bp
from routes.business import business_bp

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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


@app.route('/admin/dashboard')
def admin_dashboard_page():
    if session.get('role') != 'admin'or not session.get('user_id'):
        return redirect(url_for('login_page'))

    user = User.query.get(session['user_id'])
    
    # SAFETY SHEILD: If the session ID doesnt match an actual user record anymore, clear session and redirrect
    if not user:
        session.clear()
        return redirect(url_for('login_page'))

    stats = {
        'users': User.query.count(),
        'farmers': User.query.filter_by(role='farmer').count(),
        'experts': User.query.filter_by(role='expert').count(),
        'questions': Question.query.count(),
        'pending': Question.query.filter_by(status='pending').count(),
        'published': Question.query.filter_by(is_published=True).count(),
    }

    def fmt_q(q):
        farmer = User.query.get(q.farmer_id)
        expert = User.query.get(q.assigned_expert_id) if q.assigned_expert_id else None

        return {
            "id": q.id,
            "question": q.question,
            "category": q.category,
            "status": q.status,
            "farmer_name": farmer.fullname if farmer else "Unknown",
            "assigned_expert": expert.fullname if expert else None,
            "answer": q.answer,
            "answered_at": q.answered_at,
        }

    all_users = User.query.all()

    all_questions = [
        fmt_q(q) for q in Question.query.order_by(Question.id.desc()).all()
    ]

    pending_review = [
        fmt_q(q) for q in Question.query.filter_by(status='pending_review')
        .order_by(Question.id.desc()).all()
    ]

    experts = User.query.filter_by(role='expert').all()

    announcements = Announcement.query.order_by(
        Announcement.id.desc()
    ).all()

    # =========================
    # EXPERT RANKINGS
    # =========================
    expert_rankings = []

    for e in experts:
        answered = Question.query.filter_by(
            assigned_expert_id=e.id,
            status='answered',
            answer_verified=True
        ).count()

        ratings = ExpertRating.query.filter_by(expert_id=e.id).all()

        avg_rating = (
            round(sum(r.stars for r in ratings) / len(ratings), 1)
            if ratings else 0
        )

        expert_rankings.append({
            "fullname": e.fullname,
            "answered": answered,
            "avg_rating": avg_rating,
            "rating_count": len(ratings),
            "score": (answered * 10) + (avg_rating * 20)
        })

    expert_rankings.sort(key=lambda x: x['score'], reverse=True)

    for i, e in enumerate(expert_rankings):
        e['rank'] = i + 1

    public_qa = [
        fmt_q(q)
        for q in Question.query.filter_by(
            status='answered',
            answer_verified=True
        ).order_by(Question.id.desc()).all()
    ]

    businesses = Business.query.order_by(
        Business.id.desc()
    ).all()

    # =========================
    # EXPERT ARTICLES
    # =========================
    pending_articles = Articles.query.filter_by(
        is_approved=False
    ).order_by(
        Articles.id.desc()
    ).all()

    approved_articles = Articles.query.filter_by(
        is_approved=True
    ).order_by(
        Articles.id.desc()
    ).all()

    for article in pending_articles + approved_articles:
        expert = User.query.get(article.expert_id)
        article.expert_name = expert.fullname if expert else "Unknown"

    # =========================
    # BUSINESS POSTS
    # =========================
    business_posts = BusinessPost.query.order_by(
        BusinessPost.id.desc()
    ).all()

    for p in business_posts:
        biz_user = User.query.get(p.business_id)
        p.business_name = biz_user.fullname if biz_user else "Unknown"

    # =========================
    # COMMUNITY POSTS
    # =========================
    community_posts = Post.query.order_by(
        Post.id.desc()
    ).all()

    for p in community_posts:
        farmer = User.query.get(p.farmer_id)
        p.farmer_name = farmer.fullname if farmer else "Unknown"

    return render_template(
        'admin_dashboard.html',
        current_user=user,
        stats=stats,
        all_users=all_users,
        all_questions=all_questions,
        pending_review=pending_review,
        experts=experts,
        announcements=announcements,
        expert_rankings=expert_rankings,
        public_qa=public_qa,
        businesses=businesses,
        pending_articles=pending_articles,
        approved_articles=approved_articles,
        business_posts=business_posts,
        community_posts=community_posts
    )


@app.route('/farmer/dashboard')
def farmer_dashboard_page():
    if session.get('role') != 'farmer':
        return redirect(url_for('index'))

    user = User.query.get(session['user_id'])

    my_questions = Question.query.filter_by(
        farmer_id=user.id
    ).order_by(
        Question.id.desc()
    ).all()

    stats = {
        'questions': len(my_questions),
        'answered': len([q for q in my_questions if q.answer_verified]),
        'pending': len([q for q in my_questions if not q.answer_verified]),
    }

    announcements = Announcement.query.order_by(
        Announcement.id.desc()
    ).all()

    # Expert Articles
    articles = Articles.query.filter_by(
        is_approved=True
    ).order_by(
        Articles.id.desc()
    ).all()

    for article in articles:
        expert = User.query.get(article.expert_id)
        article.expert_name = expert.fullname if expert else "Unknown"

    experts = User.query.filter_by(role='expert').all()

    expert_rankings = []
    for e in experts:
        answered = Question.query.filter_by(
            assigned_expert_id=e.id,
            status='answered',
            answer_verified=True
        ).count()

        ratings = ExpertRating.query.filter_by(
            expert_id=e.id
        ).all()

        avg_rating = round(
            sum(r.stars for r in ratings) / len(ratings), 1
        ) if ratings else 0

        expert_rankings.append({
            "fullname": e.fullname,
            "answered": answered,
            "avg_rating": avg_rating,
            "score": (answered * 10) + (avg_rating * 20)
        })

    expert_rankings.sort(key=lambda x: x['score'], reverse=True)

    for i, e in enumerate(expert_rankings):
        e['rank'] = i + 1

    def fmt_q(q):
        expert = User.query.get(q.assigned_expert_id) if q.assigned_expert_id else None

        return {
            "id": q.id,
            "question": q.question,
            "category": q.category,
            "farmer_name": user.fullname,
            "assigned_expert": expert.fullname if expert else None,
            "answer": q.answer,
        }

    public_qa = [
        fmt_q(q)
        for q in Question.query.filter_by(
            status='answered',
            answer_verified=True
        ).order_by(
            Question.id.desc()
        ).all()
    ]

    # Community Posts
    community_posts = Post.query.order_by(
        Post.id.desc()
    ).all()

    for p in community_posts:
        farmer = User.query.get(p.farmer_id)
        p.author_name = farmer.fullname if farmer else "Unknown"

    # Business Posts
    business_posts = BusinessPost.query.order_by(
        BusinessPost.id.desc()
    ).all()

    for p in business_posts:
        biz_user = User.query.get(p.business_id)
        p.business_name = biz_user.fullname if biz_user else "Unknown"

    return render_template(
        'farmer_dashboard.html',
        current_user=user,
        stats=stats,
        my_questions=my_questions,
        community_posts=community_posts,
        announcements=announcements,
        expert_rankings=expert_rankings,
        public_qa=public_qa,
        business_posts=business_posts,
        articles=articles
    )


@app.route('/farmer/public-qa')
def farmer_public_qa_page():
    if session.get('role') != 'farmer':
        return redirect(url_for('index'))

    user = User.query.get(session['user_id'])

    public_qa = (Question.query
                  .filter_by(answer_verified=True)
                  .order_by(Question.answered_at.desc())
                  .all())

    community_posts = Post.query.order_by(Post.id.desc()).all()
    for p in community_posts:
        farmer = User.query.get(p.farmer_id)
        p.author_name = farmer.fullname if farmer else "Unknown"

    return render_template(
        'farmer_public_qa.html',
        current_user=user,
        public_qa=public_qa,
        community_posts=community_posts
    )


@app.route('/expert/dashboard')
def expert_dashboard_page():
    if session.get('role') != 'expert':
        return redirect(url_for('index'))

    user = User.query.get(session['user_id'])

    def fmt_q(q):
        farmer = User.query.get(q.farmer_id)
        expert = User.query.get(q.assigned_expert_id) if q.assigned_expert_id else None
        return {
            "id": q.id,
            "question": q.question,
            "category": q.category,
            "status": q.status,
            "farmer_name": farmer.fullname if farmer else "Unknown",
            "assigned_expert": expert.fullname if expert else None,
            "answer": q.answer,
            "admin_note": q.admin_note,
        }

    my_questions = [
        fmt_q(q)
        for q in Question.query.filter_by(
            assigned_expert_id=user.id
        ).order_by(Question.id.desc()).all()
    ]

    my_articles = Articles.query.filter_by(
        expert_id=user.id
    ).order_by(Articles.id.desc()).all()

    announcements = Announcement.query.order_by(
        Announcement.id.desc()
    ).all()

    experts = User.query.filter_by(role='expert').all()

    expert_rankings = []
    for e in experts:
        answered = Question.query.filter_by(
            assigned_expert_id=e.id,
            status='answered',
            answer_verified=True
        ).count()

        ratings = ExpertRating.query.filter_by(
            expert_id=e.id
        ).all()

        avg_rating = round(
            sum(r.stars for r in ratings) / len(ratings), 1
        ) if ratings else 0

        expert_rankings.append({
            "fullname": e.fullname,
            "answered": answered,
            "avg_rating": avg_rating,
            "rating_count": len(ratings),
            "score": (answered * 10) + (avg_rating * 20)
        })

    expert_rankings.sort(key=lambda x: x['score'], reverse=True)

    for i, e in enumerate(expert_rankings):
        e['rank'] = i + 1

    public_qa = [
        fmt_q(q)
        for q in Question.query.filter_by(
            status='answered',
            answer_verified=True
        ).order_by(Question.id.desc()).all()
    ]

    # Business posts
    business_posts = BusinessPost.query.order_by(
        BusinessPost.id.desc()
    ).all()

    for p in business_posts:
        biz_user = User.query.get(p.business_id)
        p.business_name = biz_user.fullname if biz_user else "Unknown"

    # Community posts
    community_posts = Post.query.order_by(
        Post.id.desc()
    ).all()

    for p in community_posts:
        farmer = User.query.get(p.farmer_id)
        p.author_name = farmer.fullname if farmer else "Unknown"

    return render_template(
        'expert_dashboard.html',
        current_user=user,
        my_questions=my_questions,
        my_articles=my_articles,
        business_posts=business_posts,
        community_posts=community_posts,
        announcements=announcements,
        expert_rankings=expert_rankings,
        public_qa=public_qa
    )


@app.route('/business/dashboard')
def business_dashboard_page():
    if session.get('role') != 'business':
        return redirect(url_for('index'))

    user = User.query.get(session['user_id'])
    business = Business.query.filter_by(user_id=user.id).first()

    my_posts = BusinessPost.query.filter_by(
        business_id=user.id
    ).order_by(
        BusinessPost.created_at.desc()
    ).all()

    stats = {
        'total_posts': len(my_posts),
        'total_likes': sum(p.likes_count for p in my_posts),
        'total_views': sum(p.views_count for p in my_posts),
    }

    # Approved expert articles
    articles = Articles.query.filter_by(
        is_approved=True
    ).order_by(
        Articles.id.desc()
    ).all()

    for a in articles:
        expert = User.query.get(a.expert_id)
        a.expert_name = expert.fullname if expert else "Unknown"

    # Announcements
    announcements = Announcement.query.order_by(
        Announcement.id.desc()
    ).all()

    # Public Q&A
    def fmt_q(q):
        farmer = User.query.get(q.farmer_id)
        expert = User.query.get(q.assigned_expert_id) if q.assigned_expert_id else None

        return {
            "id": q.id,
            "question": q.question,
            "category": q.category,
            "farmer_name": farmer.fullname if farmer else "Unknown",
            "assigned_expert": expert.fullname if expert else "Unknown",
            "answer": q.answer,
        }

    public_qa = [
        fmt_q(q)
        for q in Question.query.filter_by(
            status='answered',
            answer_verified=True
        ).order_by(
            Question.id.desc()
        ).all()
    ]

    # Community posts from farmers
    community_posts = Post.query.order_by(
        Post.id.desc()
    ).all()

    for p in community_posts:
        farmer = User.query.get(p.farmer_id)
        p.author_name = farmer.fullname if farmer else "Unknown"

    return render_template(
        'business_dashboard.html',
        current_user=user,
        business=business,
        stats=stats,
        my_posts=my_posts,
        announcements=announcements,
        public_qa=public_qa,
        articles=articles,
        community_posts=community_posts
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


@app.route('/api/weather')
def get_weather():
    lat = request.args.get('lat', 2.7724, type=float)   # default: Gulu, Uganda
    lon = request.args.get('lon', 32.2881, type=float)

    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current_weather": True,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode",
                "timezone": "auto"
            },
            timeout=5
        )
        data = resp.json()
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("Database created!")
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)