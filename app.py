from flask import Flask, g, render_template, jsonify, request, redirect, url_for, session, abort, flash
from config import Config
from extensions import db, limiter
from models import User, Question, ExpertRating, Announcement, AnnouncementReaction, Business, Articles, BusinessPost, Post, Message, Payment, SupportMessage
from sqlalchemy import func
import os
from flask_login import LoginManager, current_user, login_required, login_user
import requests
from flask_talisman import Talisman
from flask_limiter import Limiter           
from flask_limiter.util import get_remote_address
import uuid
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from chats_routes import chat_bp
from dotenv import load_dotenv
load_dotenv()
from bs4 import BeautifulSoup
import re
from flask_cors import CORS
from flask_migrate import Migrate
import requests as http_requests

UGANDA_DISTRICTS = {
    "Gulu": (2.7724, 32.2881),
    "Kampala": (0.3476, 32.5825),
    "Mbarara": (-0.6072, 30.6545),
    "Jinja": (0.4244, 33.2042),
    "Mbale": (1.0827, 34.1751),
    "Arua": (3.0201, 30.9111),
    "Lira": (2.2350, 32.9100),
    "Masaka": (-0.3308, 31.7341),
    "Fort Portal": (0.6710, 30.2747),
    "Soroti": (1.7146, 33.6113),
    "Kabale": (-1.2486, 29.9897),
    "Hoima": (1.4357, 31.3528),
    "Mbarara City": (-0.6072, 30.6545),
    "Entebbe": (0.0512, 32.4637),
    "Tororo": (0.6928, 34.1808),
    "Moroto": (2.5346, 34.6647),
    "Kasese": (0.1833, 30.0833),
    "Kitgum": (3.2783, 32.8867),
    "Mubende": (0.5891, 31.3942),
    "Iganga": (0.6075, 33.4686),
}

# Explicitly import the blueprints directly from their route files
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.expert import expert_bp
from routes.farmer import farmer_bp
from routes.business import business_bp
from routes.support import support_bp

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
CORS(app)
migrate = Migrate(app, db)

# Security headers
csp = {
    'default-src': "'self'",
    'style-src': ["'self'", "'unsafe-inline'"],
    'script-src': ["'self'", "'unsafe-inline'"],
    'img-src': ["'self'", "data:", "https:"],
}
Talisman(app, force_https=False, content_security_policy=csp)

# Rate limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

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
app.register_blueprint(support_bp, url_prefix='/support')
app.register_blueprint(chat_bp)


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
    if session.get('role') != 'admin' or not session.get('user_id'):
        return redirect(url_for('login_page'))

    user = User.query.get(session['user_id'])

    # SAFETY SHIELD: If the session ID doesn't match an actual user record anymore, clear session and redirect
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

    # Make sure it uses an underscore (_) and NOT a single word
    support_messages = SupportMessage.query.order_by(SupportMessage.created_at.desc()).all()

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
        article.author_verified = bool(expert.blue_tick) if expert else False

    # =========================
    # BUSINESS POSTS
    # =========================
    business_posts = BusinessPost.query.order_by(
        BusinessPost.id.desc()
    ).all()

    for p in business_posts:
        biz_user = User.query.get(p.business_id)
        p.business_name = biz_user.fullname if biz_user else "Unknown"
        p.author_name = p.business_name
        p.author_verified = bool(biz_user.blue_tick) if biz_user else False

    # =========================
    # COMMUNITY POSTS
    # =========================
    community_posts = Post.query.order_by(
        Post.id.desc()
    ).all()

    for p in community_posts:
        farmer = User.query.get(p.farmer_id)
        p.farmer_name = farmer.fullname if farmer else "Unknown"
        p.author_name = p.farmer_name
        p.author_verified = bool(farmer.blue_tick) if farmer else False

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
        article.author_verified = bool(expert.blue_tick) if expert else False

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
        p.author_verified = bool(farmer.blue_tick) if farmer else False

    # Business Posts
    business_posts = BusinessPost.query.order_by(
        BusinessPost.id.desc()
    ).all()

    for p in business_posts:
        biz_user = User.query.get(p.business_id)
        p.business_name = biz_user.fullname if biz_user else "Unknown"
        p.author_name = p.business_name
        p.author_verified = bool(biz_user.blue_tick) if biz_user else False

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
        p.author_verified = bool(farmer.blue_tick) if farmer else False

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
        p.author_name = p.business_name
        p.author_verified = bool(biz_user.blue_tick) if biz_user else False

    # Community posts
    community_posts = Post.query.order_by(
        Post.id.desc()
    ).all()

    for p in community_posts:
        farmer = User.query.get(p.farmer_id)
        p.author_name = farmer.fullname if farmer else "Unknown"
        p.author_verified = bool(farmer.blue_tick) if farmer else False

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
        a.author_verified = bool(expert.blue_tick) if expert else False

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
        p.author_verified = bool(farmer.blue_tick) if farmer else False

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

@app.route('/api/districts')
def get_districts():
    return jsonify(sorted(UGANDA_DISTRICTS.keys()))


"""
Add these two routes to your appropriate blueprint (e.g. farmer.py, or a shared routes file).
They fetch and parse data server-side and return clean JSON to the frontend.
"""


HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}


# ══════════════════════════════════════════════
#  ROUTE 1 — Uganda Weather Forecast
#  Source: https://www.mwe.go.ug/public/index.php/weather
# ══════════════════════════════════════════════
@app.route('/api/weather-info')
@login_required
def get_weather_info():
    try:
        session = requests.Session()
        resp = session.get(
            'https://www.mwe.go.ug/public/index.php/weather',
            headers=HEADERS,
            timeout=10
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'lxml')

        # ── Overview text ──────────────────────
        overview = ''
        outlook = ''
        for p in soup.find_all('p'):
            txt = p.get_text(strip=True)
            if 'country' in txt.lower() or 'conditions' in txt.lower():
                overview = txt
            if 'outlook' in txt.lower() or 'next' in txt.lower():
                outlook = txt

        # ── Date ──────────────────────────────
        date_str = ''
        for tag in soup.find_all(['h2', 'p', 'span', 'div']):
            txt = tag.get_text(strip=True)
            if re.search(r'\d{1,2}\s+\w+\s+\d{4}', txt) or 'Jun' in txt or 'Jul' in txt:
                date_str = txt[:40]
                break

        # ── City forecasts ─────────────────────
        # MWE page: each city is an <h3> followed by img (condition) + temp text
        cities = []
        known_cities = [
            'Arua', 'Entebbe', 'Gulu', 'Kabale', 'Kampala',
            'Kasese', 'Masindi', 'Mbarara', 'Soroti', 'Tororo'
        ]

        for h3 in soup.find_all('h3'):
            city_name = h3.get_text(strip=True)
            if city_name not in known_cities:
                continue

            condition = ''
            today_temp = ''
            tomorrow_temp = ''

            # Walk siblings to collect condition image alt + temp strings
            sib = h3.next_sibling
            text_chunks = []
            img_alt = ''
            steps = 0

            while sib and steps < 20:
                if hasattr(sib, 'name'):
                    if sib.name == 'h3':  # reached next city
                        break
                    if sib.name == 'img' and not img_alt:
                        img_alt = sib.get('alt', '')
                    inner = sib.get_text(separator=' ', strip=True)
                    if inner:
                        text_chunks.append(inner)
                else:
                    raw = str(sib).strip()
                    if raw:
                        text_chunks.append(raw)
                sib = sib.next_sibling
                steps += 1

            condition = img_alt or (text_chunks[0] if text_chunks else '')
            full_text = ' '.join(text_chunks)

            # Extract temperatures — pattern like "30° / 19°C"
            temp_matches = re.findall(r'\d+°\s*/\s*\d+°C', full_text)
            if temp_matches:
                today_temp = temp_matches[0]
            if len(temp_matches) > 1:
                tomorrow_temp = temp_matches[1]

            # Extract day labels
            today_label = ''
            tomorrow_label = ''
            day_matches = re.findall(r'(Today|Tomorrow)\s*·\s*[\d\w\s]+', full_text)
            if day_matches:
                today_label = day_matches[0].strip()
            if len(day_matches) > 1:
                tomorrow_label = day_matches[1].strip()

            cities.append({
                'city': city_name,
                'condition': condition,
                'today': {'label': today_label or 'Today', 'temp': today_temp},
                'tomorrow': {'label': tomorrow_label or 'Tomorrow', 'temp': tomorrow_temp},
            })

        return jsonify({
            'success': True,
            'date': date_str,
            'overview': overview,
            'outlook': outlook,
            'cities': cities
        })

    except requests.RequestException as e:
        return jsonify({'success': False, 'error': f'Network error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': f'Parse error: {str(e)}'}), 500


# ══════════════════════════════════════════════
#  ROUTE 2 — Agricultural Market Prices
#  Source: https://agric-care.com/regional-market
# ══════════════════════════════════════════════
@app.route('/api/market-prices')
@login_required
def get_market_prices():
    try:
        session = requests.Session()
        # First visit homepage to get cookies (bypasses some bot checks)
        session.get('https://agric-care.com/', headers=HEADERS, timeout=8)

        resp = session.get(
            'https://agric-care.com/regional-market',
            headers={**HEADERS, 'Referer': 'https://agric-care.com/'},
            timeout=12
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'lxml')

        categories = []

        # ── Strategy 1: Look for tables ────────
        for table in soup.find_all('table'):
            rows = table.find_all('tr')
            if not rows:
                continue

            # Try to get a category heading above the table
            prev = table.find_previous(['h2', 'h3', 'h4'])
            cat_name = prev.get_text(strip=True) if prev else 'Price List'

            headers_row = rows[0].find_all(['th', 'td'])
            col_headers = [h.get_text(strip=True) for h in headers_row]

            items = []
            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                if not cells:
                    continue
                cell_texts = [c.get_text(strip=True) for c in cells]
                if any(cell_texts):
                    item = {}
                    for i, txt in enumerate(cell_texts):
                        key = col_headers[i] if i < len(col_headers) else f'col{i}'
                        item[key] = txt
                    items.append(item)

            if items:
                categories.append({
                    'category': cat_name,
                    'columns': col_headers,
                    'items': items
                })

        # ── Strategy 2: Look for price list divs ─
        if not categories:
            for section in soup.find_all(['section', 'div'], class_=re.compile(
                r'price|market|product|item|list', re.I
            )):
                heading = section.find(['h2', 'h3', 'h4'])
                cat_name = heading.get_text(strip=True) if heading else ''
                if not cat_name:
                    continue

                items = []
                # Look for name + price pairs
                rows = section.find_all(['li', 'tr', 'div'], class_=re.compile(r'row|item|entry', re.I))
                for row in rows:
                    texts = [t.strip() for t in row.stripped_strings]
                    if len(texts) >= 2:
                        items.append({'name': texts[0], 'price': texts[1]})

                if items:
                    categories.append({'category': cat_name, 'columns': ['Name', 'Price'], 'items': items})

        # ── Strategy 3: Generic text extraction ──
        if not categories:
            # Pull all text that looks like "Product ... UGX X,XXX"
            full_text = soup.get_text(separator='\n')
            lines = [l.strip() for l in full_text.split('\n') if l.strip()]
            items = []
            for line in lines:
                if re.search(r'ugx|ush|shs|\d{3,}', line, re.I) and len(line) < 120:
                    items.append({'entry': line})
            if items:
                categories.append({
                    'category': 'Market Prices',
                    'columns': ['Entry'],
                    'items': items[:60]
                })

        return jsonify({'success': True, 'categories': categories})

    except requests.RequestException as e:
        return jsonify({'success': False, 'error': f'Network error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': f'Parse error: {str(e)}'}), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({"error": "Too many requests. Please try again later."}), 429    


# Create tables on startup (works for both `python app.py` and gunicorn)
with app.app_context():
    db.create_all()

@app.route('/chat')
def chat_page():
    if not session.get('user_id'):
        return redirect(url_for('login_page'))

    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login_page'))

    # Admins don't use chat
    if user.role == 'admin':
        return redirect(url_for('admin_dashboard_page'))

    # Must be verified (blue tick) to access chat
    if not user.blue_tick:
        dashboard_map = {
            'farmer': 'farmer_dashboard_page',
            'expert': 'expert_dashboard_page',
            'business': 'business_dashboard_page',
        }
        return redirect(url_for(dashboard_map.get(user.role, 'index')))

    # Load verified non-admin users to chat with (excluding self and admins)
    verified_users = User.query.filter(
        User.blue_tick == True,
        User.role != 'admin',
        User.id != user.id,
        User.is_suspended == False
    ).all()

    return render_template('chat.html', current_user=user, verified_users=verified_users)

@app.route('/api/messages/send', methods=['POST'])
def send_message():
    if not session.get('user_id'):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    receiver_id = data.get('receiver_id')
    content = data.get('content', '').strip()

    if not receiver_id or not content:
        return jsonify({"error": "Missing receiver or content"}), 400

    sender = User.query.get(session['user_id'])
    receiver = User.query.get(receiver_id)

    # Security checks
    if not sender or not receiver:
        return jsonify({"error": "User not found"}), 404
    if not sender.blue_tick or not receiver.blue_tick:
        return jsonify({"error": "Both users must be verified"}), 403
    if receiver.role == 'admin' or sender.role == 'admin':
        return jsonify({"error": "Admins cannot participate in chat"}), 403
    if sender.is_suspended or receiver.is_suspended:
        return jsonify({"error": "Suspended users cannot chat"}), 403

    msg = Message(
        sender_id=sender.id,
        receiver_id=receiver_id,
        content=content
    )
    db.session.add(msg)
    db.session.commit()

    return jsonify({
        "id": msg.id,
        "sender_id": msg.sender_id,
        "receiver_id": msg.receiver_id,
        "content": msg.content,
        "created_at": msg.created_at.strftime("%H:%M"),
        "is_read": msg.is_read
    }), 201


@app.before_request
def enforce_unverified_limits():
    """
    Runs before every request.
    Blocks unverified users from submitting more than 1 action per 6 hours.
    """

    # Only intercept POST requests to these specific endpoints
    restricted_endpoints = {
        'farmer.ask_question': ('question', Question, 'farmer_id'),
        'farmer.create_post':  ('post',     Post,     'farmer_id'),
        'expert.publish_article': ('article', Articles, 'expert_id'),
    }

    if request.method != 'POST':
        return  # only block POST submissions, never GET

    endpoint = request.endpoint
    if endpoint not in restricted_endpoints:
        return  # not a restricted route, carry on

    user_id = session.get('user_id')
    if not user_id:
        return  # not logged in, let the route handle it

    user = User.query.get(user_id)
    if not user or user.blue_tick:
        return  # verified users — no restriction

    # ── User is unverified — check their recent activity ──
    action_label, Model, owner_field = restricted_endpoints[endpoint]
    six_hours_ago = datetime.utcnow() - timedelta(hours=6)

    recent = Model.query.filter(
        getattr(Model, owner_field) == user_id,
        Model.created_at >= six_hours_ago
    ).order_by(Model.created_at.desc()).first()

    if recent:
        next_allowed = recent.created_at + timedelta(hours=6)
        wait         = next_allowed - datetime.utcnow()
        total_mins   = max(1, int(wait.total_seconds() / 60))
        hours        = total_mins // 60
        mins         = total_mins % 60
        wait_str     = f"{hours}h {mins}m" if hours else f"{mins}m"

        session['limit_error'] = (
            f"You can only submit 1 {action_label} every 6 hours. "
            f"Try again in {wait_str}. "
            f"Get verified for unlimited access."
        )

        # Redirect back to whichever dashboard they came from
        role = user.role  # 'farmer', 'expert', etc.
        return redirect(f'/{role}/dashboard')

@app.route('/api/messages/<int:other_user_id>', methods=['GET'])
def get_messages(other_user_id):
    if not session.get('user_id'):
        return jsonify({"error": "Unauthorized"}), 401

    current_id = session['user_id']
    current = User.query.get(current_id)
    other = User.query.get(other_user_id)

    if not current or not other:
        return jsonify({"error": "User not found"}), 404

    # Only the two participants can see their messages
    if not (current.blue_tick and other.blue_tick):
        return jsonify({"error": "Both users must be verified"}), 403

    messages = Message.query.filter(
        db.or_(
            db.and_(
                Message.sender_id == current_id,
                Message.receiver_id == other_user_id
            ),
            db.and_(
                Message.sender_id == other_user_id,
                Message.receiver_id == current_id
            )
        )
    ).order_by(Message.created_at.asc()).all()

    # Mark unread messages as read
    Message.query.filter_by(
        sender_id=other_user_id,
        receiver_id=current_id,
        is_read=False
    ).update({"is_read": True})
    db.session.commit()

    return jsonify([{
        "id": m.id,
        "sender_id": m.sender_id,
        "content": m.content,
        "created_at": m.created_at.strftime("%H:%M"),
        "is_read": m.is_read
    } for m in messages]), 200


@app.route('/api/messages/unread-counts', methods=['GET'])
def unread_counts():
    if not session.get('user_id'):
        return jsonify({}), 401

    current_id = session['user_id']
    results = db.session.query(
        Message.sender_id,
        db.func.count(Message.id).label('count')
    ).filter_by(
        receiver_id=current_id,
        is_read=False
    ).group_by(Message.sender_id).all()

    return jsonify({str(r.sender_id): r.count for r in results}), 200

def initiate_mtn(payment):
    print("MTN called")

def initiate_airtel(payment):
    print("Airtel called")

@app.route('/pay/verification/<provider>/<plan>', methods=['POST'])
def start_payment(provider, plan):

    prices = {
        "farmer": 3000,
        "expert": 5000,
        "business": 10000
    }

    if plan not in prices:
        return {"error": "Invalid plan"}, 400

    if provider not in ["mtn", "airtel"]:
        return {"error": "Invalid provider"}, 400

    payment = Payment(
        user_id=current_user.id,
        amount=prices[plan],
        product_type=plan,
        provider=provider,
        reference=str(uuid.uuid4()),
        status="pending"
    )

    db.session.add(payment)
    db.session.commit()

    # CALL gateway
    if provider == "mtn":
        initiate_mtn(payment)
    else:
        initiate_airtel(payment)

    payment.status = "processing"
    db.session.commit()

    return {
        "reference": payment.reference,
        "amount": payment.amount,
        "provider": provider
    }

@app.route('/payment/webhook', methods=['POST'])
def payment_webhook():

    data = request.json

    reference = data.get("reference")
    status = data.get("status")

    if not reference:
        return {"error": "Missing reference"}, 400

    payment = Payment.query.filter_by(reference=reference).first()

    if not payment:
        return {"error": "Invalid reference"}, 404

    # Prevent double processing (idempotency)
    if payment.status == "paid":
        return {"message": "Already processed"}

    if status not in ["successful", "SUCCESS", "SUCCESSFUL"]:
        payment.status = "failed"
        db.session.commit()
        return {"message": "Payment failed"}

    # mark paid
    payment.status = "paid"

    user = User.query.get(payment.user_id)

    user.role = payment.product_type
    user.verification_expires_at = datetime.utcnow() + timedelta(days=30)

    if payment.product_type == "business":
        user.blue_tick = True

    db.session.commit()

    return {"message": "User verified successfully"}
@app.cli.command("expire-verifications")
def expire_verifications():

    users = User.query.filter(
        User.verification_expires_at != None
    ).all()

    for user in users:

        if user.verification_expires_at < datetime.utcnow():
            user.role = "farmer"
            user.blue_tick = False
            user.verification_expires_at = None

    db.session.commit()

    print("Expired verifications cleaned")


# Ensure you define an upload folder paths somewhere near your app config
UPLOAD_FOLDER = 'static/uploads/verification_docs'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    # 1. Fallback security check using your native login system
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Update to your actual login route endpoint if different
        
    # Using modern Session.get() syntax to eliminate the legacy Query.get() console warnings
    user = db.session.get(User, session['user_id'])
    if not user:
        return redirect(url_for('login'))

    if request.method == 'POST':
        setting_type = request.form.get('setting_type')
        action = request.form.get('action')
        
        if setting_type == 'business' and action == 'initiate_subscription':
            provider = request.form.get('payment_provider')
            phone_number = request.form.get('momo_number')
            
            # Determine correct dynamic tier fees safely
            user_role = user.role.lower().strip() if getattr(user, 'role', None) else "farmer"
            
            if user_role == 'farmer':
                amount = 3000.0
            elif user_role == 'expert':
                amount = 5000.0
            else:
                amount = 10000.0
                
            if provider in ['mtn', 'airtel']:
                formatted_phone = phone_number.strip() if phone_number else ""
                unique_reference = f"AGRO-{uuid.uuid4().hex[:12].upper()}"
                
                # Write to your Payment model
                new_payment = Payment(
                    user_id=user.id,
                    amount=amount,
                    product_type=f"subscription_{user_role}",
                    provider=provider,
                    reference=unique_reference,
                    status='pending',
                    created_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(minutes=15)
                )
                
                db.session.add(new_payment)
                db.session.commit()

            if provider =='mtn':
                status_code = mtn_request_payment(formatted_phone, amount, unique_reference)
                if status_code == 202:
                    flash(f"✅ Payment prompt sent to {formatted_phone}. Enter your MoMo PIN to complete payment of {amount:,.0f} UGX.", "success")
                else:
                    flash("⚠️ Could not reach MTN. Please try again or pay manually using code 51877465.", "danger")
            elif provider == 'airtel':
                flash(f"Airtel integration coming soon. Please pay manually by dialling *185# and using merchant code 7127282.", "info")
                
                flash(f"An instant verification push has been sent to {formatted_phone}. Please enter your MoMo PIN to complete the payment of {amount:,.0f} UGX.", "success")
            else:
                flash("Card transactions are currently down for updates. Please use Mobile Money.", "danger")
                
            return redirect(url_for('settings'))
            
    # Pass 'current_user' as 'user' to maintain template field compatibility 
    return render_template('settings.html', current_user=user)

@app.route('/support/send', methods=['POST'])
def send_support_message():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401

    data    = request.get_json(silent=True) or {}
    message = data.get('message', '').strip()

    if not message:
        return jsonify({'error': 'Message is empty'}), 400

    msg = SupportMessage(
        user_id = user_id,
        message = message,
        status  = 'Unread'
    )
    db.session.add(msg)
    db.session.commit()

    return jsonify({'message': 'Message sent!'}), 200



MTN_SUB_KEY = "17287ff3d7744014ae7d153c8d3b6a3d"
MTN_USER_ID = "8ee0fa79-cdc0-4006-a90d-4b3bd02cde71"
MTN_API_KEY = "1705978f576940969a2f405076630d32"
MTN_ENV     = "mtnuganda"
print("SUB KEY:", MTN_SUB_KEY)
print("USER ID:", MTN_USER_ID)
print("API KEY:", MTN_API_KEY)

def mtn_get_token():
    import base64
    try:
        credentials = base64.b64encode(f"{MTN_USER_ID}:{MTN_API_KEY}".encode()).decode()
        res = http_requests.post(
            "https://sandbox.momodeveloper.mtn.com/collection/token/",
            headers={
                "Authorization": f"Basic {credentials}",
                "Ocp-Apim-Subscription-Key": MTN_SUB_KEY
            },
            timeout=10
        )
        print("TOKEN STATUS:", res.status_code)
        print("TOKEN BODY:", res.text)
        return res.json().get('access_token')
    except Exception as e:
        print("TOKEN ERROR:", e)
        return None
def mtn_request_payment(phone, amount, reference):
    try:
        token = mtn_get_token()
        if not token:
            print("No token received")
            return None

        phone = phone.strip().replace(" ", "").replace("+", "")

        phone = phone.strip().replace(" ", "").replace("+", "")
        if phone.startswith("256"):
           formatted = phone
        elif phone.startswith("0"):
           formatted = "256" + phone[1:]
        else:
           formatted = "256" + phone

        print("FORMATTED PHONE:", formatted)

        payload = {
            "amount": str(int(amount)),
            "currency": "UGX",
            "externalId": reference,
            "payer": {
                "partyIdType": "MSISDN",
                "partyId": formatted
            },
            "payerMessage": "AGROSPHERE Subscription",
            "payeeNote": "Monthly subscription payment"
        }
        print("PAYLOAD:", payload)

        res = http_requests.post(
            "https://sandbox.momodeveloper.mtn.com/collection/v1_0/requesttopay",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Reference-Id": reference,
                "X-Target-Environment": MTN_ENV,
                "Ocp-Apim-Subscription-Key": MTN_SUB_KEY,
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=10
        )
        print("PAYMENT STATUS:", res.status_code)
        print("PAYMENT BODY:", res.text)
        return res.status_code
    except Exception as e:
        print("PAYMENT ERROR:", e)
        return None

from datetime import datetime

@app.template_filter('humanize_time')
def humanize_time(value):
    if not value:
        return ""

    now = datetime.utcnow()
    diff = now - value

    seconds = diff.total_seconds()

    if seconds < 60:
        return "Just now"

    if seconds < 3600:
        return f"{int(seconds // 60)} min ago"

    if seconds < 86400:
        return f"{int(seconds // 3600)} hrs ago"

    if seconds < 604800:
        return f"{int(seconds // 86400)} days ago"

    return value.strftime("%d %b %Y")
    
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)